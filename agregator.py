import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
from arinc429 import ARINC429

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time


def handle_state(state: int) -> str:
    if state == ARINC429.ON_GROUND:
        return "On ground"
    elif state == ARINC429.CRUISE:
        return "Cruise"
    elif state == ARINC429.ALTITUDE_CHANGE:
        return "Altitude changing"
    else:
        return "Unknown"


class ARINC429GUI(tk.Tk):
    def __init__(self, host="127.0.0.1", port=65432):
        super().__init__()
        self.title("ARINC 429 Interface")
        self.geometry("600x400")
        self.resizable(False, False)

        self.altitude_var = tk.StringVar(value="0")
        self.power_var = tk.StringVar(value="0")
        self.rise_var = tk.StringVar(value="0")
        self.angle_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value=handle_state(ARINC429.ON_GROUND))
        self.status = ARINC429.ON_GROUND
        self.altitude = 0

        self.altitude_history = []
        self.time_history = []
        self.time = 0

        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

        self.create_widgets()
        self.connect_thread = threading.Thread(target=self.connect_loop, daemon=True)
        self.connect_thread.start()

    def create_widgets(self):
        # Configure the main window
        self.geometry("800x400")  # Resize as needed

        # Create main frame with two columns
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left side frame for entries and status
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nw", padx=10)

        # Right side frame for the graph
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10)
        main_frame.columnconfigure(1, weight=1)  # Allow the graph to expand

        # === LEFT SIDE CONTENT ===
        ttk.Label(left_frame, text="Altitude desired:").grid(row=0, column=0, sticky="w")
        self.altitude_entry = ttk.Entry(left_frame)
        self.altitude_entry.grid(row=0, column=1, sticky="ew")
        self.altitude_entry.bind("<Return>", self.handle_altitude_input)

        ttk.Label(left_frame, text="Power of motor:").grid(row=1, column=0, sticky="w")
        self.power_entry = ttk.Entry(left_frame)
        self.power_entry.grid(row=1, column=1, sticky="ew")
        self.power_entry.bind("<Return>", self.handle_power_input)

        self.status_label = ttk.Label(left_frame, text="Connecting...", foreground="orange")
        self.status_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 10))

        # Current state variables
        ttk.Label(left_frame, text="Current Altitude:").grid(row=3, column=0, sticky="w")
        ttk.Label(left_frame, textvariable=self.altitude_var).grid(row=3, column=1, sticky="w")

        ttk.Label(left_frame, text="Current Power:").grid(row=4, column=0, sticky="w")
        ttk.Label(left_frame, textvariable=self.power_var).grid(row=4, column=1, sticky="w")

        ttk.Label(left_frame, text="Current rise rate:").grid(row=5, column=0, sticky="w")
        ttk.Label(left_frame, textvariable=self.rise_var).grid(row=5, column=1, sticky="w")

        ttk.Label(left_frame, text="Current angle:").grid(row=6, column=0, sticky="w")
        ttk.Label(left_frame, textvariable=self.angle_var).grid(row=6, column=1, sticky="w")

        ttk.Label(left_frame, text="Current state:").grid(row=7, column=0, sticky="w")
        ttk.Label(left_frame, textvariable=self.status_var).grid(row=7, column=1, sticky="w")

        # Make entry columns stretch a little
        left_frame.columnconfigure(1, weight=1)

        # === RIGHT SIDE: Matplotlib plot ===
        fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = fig.add_subplot(111)
        self.altitude_line, = self.ax.plot([], [], label="Altitude (ft)")
        self.ax.set_xlabel("Time (min)")
        self.ax.set_ylabel("Altitude (ft)")
        self.ax.set_title("Altitude vs Time")
        self.ax.grid(True)

        fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.draw()

    def update_altitude_plot(self):
        if self.altitude_var.get() is None:
            return
        self.time += 1
        self.time_history.append(self.time/60)
        self.altitude_history.append(float(self.altitude_var.get()))

        # Keep last 100 points for performance
        self.time_history = self.time_history[-200:]
        self.altitude_history = self.altitude_history[-200:]

        self.altitude_line.set_data(self.time_history, self.altitude_history)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()


    def connect_loop(self):
        while True:
            if not self.connected:
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self.host, self.port))
                    self.connected = True
                    self.update_status("Connected", "green")
                    threading.Thread(target=self.listen_to_socket, daemon=True).start()
                except socket.error:
                    self.update_status("Reconnecting...", "orange")
                    time.sleep(3)
            else:
                time.sleep(1)

    def update_status(self, text, color):
        def _update():
            self.status_label.config(text=text, foreground=color)
        self.after(0, _update)

    def handle_altitude_input(self, input):
        try:
            self.altitude = int(self.altitude_entry.get())
            self.handle_altitude()
        except Exception as e:
            messagebox.showerror("Send Error", str(e))

    def handle_altitude(self):
        encoded_altitude = ARINC429.encode(1, 0, self.altitude, self.status)
        self.send_data(encoded_altitude)

    def handle_power_input(self, input):
        try:
            power = float(self.power_entry.get())

            encoded_power = ARINC429.encode(4, 0, power)
            self.send_data(encoded_power)
        except Exception as e:
            messagebox.showerror("Send Error", str(e))

    def send_data(self, data):
        if not self.connected:
            messagebox.showwarning("Not connected", "Currently not connected to the server.")
            return

        self.socket.sendall(str(data).encode())


    def listen_to_socket(self):
        try:
            while self.connected:
                words = self.socket.recv(128).decode('utf-8').strip().split("\n")
                if not words:
                    break
                for word in words:
                    if not word:
                        continue
                    data = int(word)
                    decoded = ARINC429.decode(data)
                    if decoded == [None]:
                        print("No data")
                        print(data)
                        continue

                    label, sdi, ssm, out = decoded
                    if label == 1:
                        altitude, state = out
                        self.altitude_var.set(altitude)
                        self.status = state
                        self.status_var.set(handle_state(state))

                    elif label == 2:
                        self.rise_var.set(out)
                    elif label == 3:
                        self.angle_var.set(out)
                    elif label == 4:
                        self.power_var.set(out)

                self.handle_altitude()
                self.update_altitude_plot()


        except Exception as e:
            print(e)
        finally:
            self.connected = False
            self.update_status("Disconnected", "red")
            try:
                self.socket.close()
            except:
                pass

    def on_close(self):
        self.connected = False
        try:
            if self.socket:
                self.socket.close()
        except:
            pass
        self.destroy()


if __name__ == "__main__":
    app = ARINC429GUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
