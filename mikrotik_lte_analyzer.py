import paramiko
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
import time
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import speedtest
from ping3 import ping

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
            'upload_speeds': [],
            'ping': []
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
        style.configure("Accent.TButton", background="#4CAF50", foreground="black")
        style.map("Accent.TButton", background=[("active", "#45a049")])

        self.connect_button = ttk.Button(self.master, text="Connect", command=self.connect_to_router, style="Accent.TButton")
        self.connect_button.pack(pady=10)

        self.clear_button = ttk.Button(self.master, text="Clear All", command=self.clear_all, style="Accent.TButton")
        self.clear_button.pack(pady=10)

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

    def clear_all(self):
        self.tree.delete(*self.tree.get_children())
        self.data = {}

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
            self.tree.insert("", tk.END, values=(phy_cellid, band, earfcn, values["RSRP"], values["RSRQ"], values["AGE"], connections), tags=("colored",))
            self.tree.tag_configure("colored", background=color)

    def get_signal_color(self, rsrp):
        if rsrp > -60:
            return "lightgreen"
        elif rsrp > -80:
            return "lightyellow"
        else:
            return "lightcoral"

    def on_row_double_click(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item, 'values')
        phy_cellid, band, earfcn, rsrp, rsrq, age, connections = values

        # Select the tower
        self.select_tower(phy_cellid, band, earfcn)

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

        # Button to lock on selected tower
        lock_button = ttk.Button(details_window, text="Lock on Selected Tower", command=self.lock_to_tower, style="Accent.TButton")
        lock_button.pack(pady=10)

        # Create a frame for the graphs
        graph_frame = ttk.Frame(details_window)
        graph_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    def select_tower(self, phy_cellid, band, earfcn):
        self.selected_tower = {
            'phy_cellid': phy_cellid,
            'band': band,
            'earfcn': earfcn
        }

    def lock_to_tower(self):
        if self.selected_tower and self.connection_established:
            band = self.selected_tower['band']
            earfcn = self.selected_tower['earfcn']
            command = f"/interface lte set lte1 band={band} earfcn={earfcn} cell-lock=on"
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()
            tk.messagebox.showinfo("Lock Status", f"Lock command output: {output}")

    def run_speed_test(self, details_window):
        details_window.title("Speed Test")

        # Initialize the test data
        self.test_data = {
            'download_speeds': [],
            'upload_speeds': [],
            'ping': []
        }

        # Start the speed test in a separate thread
        threading.Thread(target=self.perform_speed_test, args=(details_window,)).start()

    def perform_speed_test(self, details_window):
        duration = 60  # Duration of speed test in seconds
        start_time = time.time()

        # Use a Tkinter-compatible plotting function
        def plot_data():
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8))
            ax1.set_title('Download Speed Over Time')
            ax2.set_title('Upload Speed Over Time')
            ax3.set_title('Ping Over Time')

            canvas = FigureCanvasTkAgg(fig, master=details_window)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            download_speeds = []
            upload_speeds = []
            ping_times = []
            times = []

            while time.time() - start_time < duration:
                elapsed_time = time.time() - start_time
                times.append(elapsed_time)

                # Real speed test data
                st = speedtest.Speedtest()
                st.get_best_server()

                download_speed = st.download() / 1_000_000  # Convert from bits/s to Mbps
                upload_speed = st.upload() / 1_000_000  # Convert from bits/s to Mbps
                ping_time = st.results.ping

                self.test_data['download_speeds'].append(download_speed)
                self.test_data['upload_speeds'].append(upload_speed)
                self.test_data['ping'].append(ping_time)

                download_speeds.append(download_speed)
                upload_speeds.append(upload_speed)
                ping_times.append(ping_time)

                # Update plots
                ax1.clear()
                ax2.clear()
                ax3.clear()
                ax1.plot(times, download_speeds, label='Download Speed (Mbps)')
                ax2.plot(times, upload_speeds, label='Upload Speed (Mbps)')
                ax3.plot(times, ping_times, label='Ping (ms)')
                ax1.set_title('Download Speed Over Time')
                ax2.set_title('Upload Speed Over Time')
                ax3.set_title('Ping Over Time')
                ax1.set_xlabel('Time (s)')
                ax1.set_ylabel('Download Speed (Mbps)')
                ax2.set_xlabel('Time (s)')
                ax2.set_ylabel('Upload Speed (Mbps)')
                ax3.set_xlabel('Time (s)')
                ax3.set_ylabel('Ping (ms)')
                ax1.legend()
                ax2.legend()
                ax3.legend()

                canvas.draw()
                details_window.update_idletasks()
                time.sleep(1)

        # Plot data in the main thread
        self.master.after(0, plot_data)

if __name__ == "__main__":
    root = tk.Tk()
    app = LTEAnalyzerApp(root)
    root.mainloop()
