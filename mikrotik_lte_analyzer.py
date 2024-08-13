import paramiko
import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests

class LTEAnalyzerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Ashanet LTE Analyzer")
        self.master.state("zoomed")  # Fullscreen window
        self.connection_established = False
        self.ssh_client = None
        self.data = {}
        self.selected_tower = None
        self.test_data = {
            'download_speeds': [],
            'ping': [],
            'signal_quality': []
        }
        
        self.setup_ui()

    def setup_ui(self):
        # Set color theme
        self.master.configure(bg="#f5f5f5")

        # IP, username, and password fields
        self.ip_label = ttk.Label(self.master, text="Router IP:", background="#f5f5f5", font=("Helvetica", 12))
        self.ip_label.pack(pady=5)
        self.ip_entry = ttk.Entry(self.master, font=("Helvetica", 12))
        self.ip_entry.pack(pady=5)

        self.username_label = ttk.Label(self.master, text="Username:", background="#f5f5f5", font=("Helvetica", 12))
        self.username_label.pack(pady=5)
        self.username_entry = ttk.Entry(self.master, font=("Helvetica", 12))
        self.username_entry.pack(pady=5)

        self.password_label = ttk.Label(self.master, text="Password:", background="#f5f5f5", font=("Helvetica", 12))
        self.password_label.pack(pady=5)
        self.password_entry = ttk.Entry(self.master, show="*", font=("Helvetica", 12))
        self.password_entry.pack(pady=5)

        # Define the accent button style
        style = ttk.Style()
        style.configure("Accent.TButton", background="#4CAF50", foreground="white")
        style.map("Accent.TButton", background=[("active", "#45a049")])

        self.connect_button = ttk.Button(self.master, text="Connect", command=self.connect_to_router, style="Accent.TButton")
        self.connect_button.pack(pady=10)

        self.scan_button = ttk.Button(self.master, text="Start Scan", command=self.start_scan, style="Accent.TButton")
        self.scan_button.pack(pady=10)

        self.status_label = ttk.Label(self.master, text="Status: Not Connected", foreground="red", background="#f5f5f5", font=("Helvetica", 12))
        self.status_label.pack(pady=10)

        # Scanning label
        self.scanning_label = ttk.Label(self.master, text="", foreground="blue", background="#f5f5f5", font=("Helvetica", 12))
        self.scanning_label.pack(pady=5)

        # Timer label
        self.timer_label = ttk.Label(self.master, text="Remaining Time: --", foreground="black", background="#f5f5f5", font=("Helvetica", 12))
        self.timer_label.pack(pady=5)

        # GitHub link label
        self.github_label = ttk.Label(self.master, text="Check out the code on GitHub", foreground="#0066cc", background="#f5f5f5", font=("Helvetica", 12, "underline"))
        self.github_label.pack(pady=10)
        self.github_label.bind("<Button-1>", lambda e: self.open_github_link())

        # Table for displaying data
        self.tree = ttk.Treeview(self.master, columns=("PHY-CELLID", "BAND", "EARFCN", "RSRP", "RSRQ", "AGE", "Connections"), show='headings')
        self.tree.heading("PHY-CELLID", text="PHY-CELLID")
        self.tree.heading("BAND", text="BAND")
        self.tree.heading("EARFCN", text="EARFCN")
        self.tree.heading("RSRP", text="RSRP")
        self.tree.heading("RSRQ", text="RSRQ")
        self.tree.heading("AGE", text="AGE")
        self.tree.heading("Connections", text="Connections")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)  # Make the table responsive

        # Bind row click event
        self.tree.bind("<Double-1>", self.on_row_double_click)

        # Load settings if they exist
        self.load_settings()

    def open_github_link(self):
        import webbrowser
        webbrowser.open("https://github.com/ashanet")

    def connect_to_router(self):
        if not self.connection_established:
            ip = self.ip_entry.get()
            username = self.username_entry.get()
            password = self.password_entry.get()

            # Save the settings
            self.save_settings(ip, username, password)

            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                self.ssh_client.connect(hostname=ip, username=username, password=password, look_for_keys=False)
                self.connection_established = True
                self.status_label.config(text="Status: Connected", foreground="green")
            except Exception as e:
                self.status_label.config(text=f"Status: Connection Failed - {str(e)}", foreground="red")

    def save_settings(self, ip, username, password):
        with open("router_settings.txt", "w") as f:
            f.write(f"{ip}\n{username}\n{password}\n")

    def load_settings(self):
        if os.path.exists("router_settings.txt"):
            with open("router_settings.txt", "r") as f:
                lines = f.readlines()
                self.ip_entry.insert(0, lines[0].strip())
                self.username_entry.insert(0, lines[1].strip())
                self.password_entry.insert(0, lines[2].strip())

    def start_scan(self):
        if self.connection_established:
            threading.Thread(target=self.scan_lte_towers).start()

    def scan_lte_towers(self):
        self.scanning_label.config(text="Scanning in progress... Please wait.")
        self.master.update_idletasks()  # Refresh the UI

        duration = 60  # Scan duration in seconds
        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            remaining_time = int(end_time - time.time())
            self.timer_label.config(text=f"Remaining Time: {remaining_time} seconds")
            self.master.update_idletasks()  # Update timer

            command = '/interface lte cell-monitor lte1 duration=5'
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()

            # Save output to file
            with open("lte_scan_output.txt", "a") as file:
                file.write(output + "\n")

            # Update UI with parsed and sorted output
            self.update_table(output)

            time.sleep(5)

        self.scanning_label.config(text="")  # Clear the scanning label
        self.timer_label.config(text="Scan Completed")

    def update_table(self, output):
        # Parse the output and aggregate the data
        for line in output.splitlines():
            if line and not line.startswith("Columns:") and not line.startswith("PHY-CELLID"):
                data = line.split()
                if len(data) == 6:
                    phy_cellid, band, earfcn, rsrp, rsrq, age = data
                    key = (phy_cellid, band, earfcn)
                    if key not in self.data:
                        self.data[key] = {"RSRP": rsrp, "RSRQ": rsrq, "AGE": age, "Connections": 1}
                    else:
                        self.data[key]["Connections"] += 1
                        self.data[key]["RSRP"] = rsrp
                        self.data[key]["RSRQ"] = rsrq
                        self.data[key]["AGE"] = age

        # Sort the data by RSRP (Signal Quality)
        sorted_data = sorted(self.data.items(), key=lambda x: int(x[1]["RSRP"].replace("dBm", "").replace("dB", "").strip()), reverse=True)

        # Clear previous table entries
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Insert sorted data into the table with color coding
        for (phy_cellid, band, earfcn), values in sorted_data:
            rsrp_value = int(values["RSRP"].replace("dBm", "").replace("dB", "").strip())
            connections = values["Connections"]
            color = self.get_signal_color(rsrp_value)
            self.tree.insert("", tk.END, values=(phy_cellid, band, earfcn, values["RSRP"], values["RSRQ"], values["AGE"], connections), tags=("color",))
            self.tree.tag_configure("color", background=color)

    def get_signal_color(self, rsrp_value):
        # Mapping RSRP to color gradient from green (good) to red (bad)
        if rsrp_value >= -80:
            return "#e0f2f1"  # Light green
        elif rsrp_value >= -90:
            return "#b9fbc0"  # Green
        elif rsrp_value >= -100:
            return "#ffebee"  # Light pink
        else:
            return "#ffccbc"  # Red

    def on_row_double_click(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item, 'values')
        phy_cellid, band, earfcn, rsrp, rsrq, age, connections = values

        # Open a new window to display details
        details_window = tk.Toplevel(self.master)
        details_window.title(f"Details for PHY-CELLID {phy_cellid}")
        details_window.geometry("1000x800")

        # Display tower information
        ttk.Label(details_window, text=f"PHY-CELLID: {phy_cellid}").pack(pady=5)
        ttk.Label(details_window, text=f"BAND: {band}").pack(pady=5)
        ttk.Label(details_window, text=f"EARFCN: {earfcn}").pack(pady=5)
        ttk.Label(details_window, text=f"RSRP: {rsrp}").pack(pady=5)
        ttk.Label(details_window, text=f"RSRQ: {rsrq}").pack(pady=5)
        ttk.Label(details_window, text=f"Connections: {connections}").pack(pady=5)

        # Button to run speed test
        speed_test_button = ttk.Button(details_window, text="Run Speed Test", command=lambda: self.run_speed_test(details_window))
        speed_test_button.pack(pady=10)

        # Create a frame for the graphs
        graph_frame = ttk.Frame(details_window)
        graph_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    def run_speed_test(self, details_window):
        # Initialize data collection
        self.test_data = {
            'download_speeds': [],
            'ping': [],
            'signal_quality': []
        }

        # Run speed test in a separate thread
        threading.Thread(target=self.perform_speed_test, args=(details_window,)).start()

    def perform_speed_test(self, details_window, duration=60):
        download_speeds = []
        pings = []
        signal_qualities = []
        start_time = time.time()

        while time.time() - start_time < duration:
            download_speed = self.get_download_speed()
            ping = self.get_ping()
            signal_quality = 100 - (ping / 10)  # Example of signal quality based on ping

            download_speeds.append(download_speed)
            pings.append(ping)
            signal_qualities.append(signal_quality)

            # Update the table with the latest download speed
            self.update_speed_table(download_speed, details_window)

            time.sleep(10)  # Update every 10 seconds

        self.test_data['download_speeds'] = download_speeds
        self.test_data['ping'] = pings
        self.test_data['signal_quality'] = signal_qualities

        # Update the graphs and statistics
        self.update_graphs(details_window)
        self.update_statistics(details_window)

    def get_download_speed(self):
        # Use a different method to measure download speed
        return round(requests.get('https://httpbin.org/stream-bytes/10000').elapsed.total_seconds(), 2)

    def get_ping(self):
        # Use a method to measure ping
        return round(requests.get('https://www.google.com').elapsed.total_seconds() * 1000, 2)

    def update_speed_table(self, speed, details_window, is_average=False):
        # Update the table with the current download speed or average
        if is_average:
            label_text = f"Average Download Speed: {speed:.2f} Mbps"
        else:
            label_text = f"Current Download Speed: {speed:.2f} Mbps"

        # Check if the label already exists
        for widget in details_window.winfo_children():
            if isinstance(widget, ttk.Label) and "Download Speed" in widget.cget("text"):
                widget.config(text=label_text)
                return
        
        ttk.Label(details_window, text=label_text).pack(pady=5)

    def update_graphs(self, details_window):
        # Clear the existing plots
        for widget in details_window.winfo_children():
            if isinstance(widget, tk.Canvas):
                widget.destroy()

        # Create and display new plots in the main thread
        def plot_graphs():
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 6))

            ax1.plot(self.test_data['download_speeds'], label="Download Speed (Mbps)", color='blue')
            ax1.set_title("Download Speed Over Time")
            ax1.set_xlabel("Test Number")
            ax1.set_ylabel("Speed (Mbps)")
            ax1.legend()

            ax2.plot(self.test_data['ping'], label="Ping (ms)", color='green')
            ax2.set_title("Ping Over Time")
            ax2.set_xlabel("Test Number")
            ax2.set_ylabel("Ping (ms)")
            ax2.legend()

            ax3.plot(self.test_data['signal_quality'], label="Signal Quality", color='red')
            ax3.set_title("Signal Quality Over Time")
            ax3.set_xlabel("Test Number")
            ax3.set_ylabel("Quality")
            ax3.legend()

            canvas = FigureCanvasTkAgg(fig, master=details_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Run plotting in the main thread
        self.master.after(0, plot_graphs)

    def update_statistics(self, details_window):
        # Calculate statistics
        avg_download_speed = sum(self.test_data['download_speeds']) / len(self.test_data['download_speeds']) if self.test_data['download_speeds'] else 0
        avg_ping = sum(self.test_data['ping']) / len(self.test_data['ping']) if self.test_data['ping'] else 0
        max_download_speed = max(self.test_data['download_speeds'], default=0)
        min_download_speed = min(self.test_data['download_speeds'], default=0)
        max_ping = max(self.test_data['ping'], default=0)
        min_ping = min(self.test_data['ping'], default=0)

        # Clear previous statistics
        for widget in details_window.winfo_children():
            if isinstance(widget, ttk.Label) and "Statistics" in widget.cget("text"):
                widget.destroy()

        # Create a frame for statistics
        stats_frame = ttk.Frame(details_window)
        stats_frame.pack(pady=10, fill=tk.X)

        # Add labels for statistics
        ttk.Label(stats_frame, text=f"Average Download Speed: {avg_download_speed:.2f} Mbps").pack()
        ttk.Label(stats_frame, text=f"Average Ping: {avg_ping:.2f} ms").pack()
        ttk.Label(stats_frame, text=f"Max Download Speed: {max_download_speed:.2f} Mbps").pack()
        ttk.Label(stats_frame, text=f"Min Download Speed: {min_download_speed:.2f} Mbps").pack()
        ttk.Label(stats_frame, text=f"Max Ping: {max_ping:.2f} ms").pack()
        ttk.Label(stats_frame, text=f"Min Ping: {min_ping:.2f} ms").pack()

    def lock_to_tower(self):
        if self.selected_tower and self.connection_established:
            band = self.selected_tower['band']
            earfcn = self.selected_tower['earfcn']
            command = f"/interface lte set lte1 band={band} earfcn={earfcn} cell-lock=on"
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()
            print(f"Locking command output: {output}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LTEAnalyzerApp(root)
    root.mainloop()
