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
        self.start_time = time.time()

        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

        self.create_widgets()
        self.connect_thread = threading.Thread(target=self.connect_loop, daemon=True)
        self.connect_thread.start()

    def create_widgets(self):
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(frame, text="Altitude desired:").grid(row=0, column=0, sticky="w")
        self.altitude_entry = ttk.Entry(frame)
        self.altitude_entry.grid(row=0, column=1)
        self.altitude_entry.bind("<Return>", self.handle_altitude_input)

        ttk.Label(frame, text="Power of motor:").grid(row=1, column=0, sticky="w")
        self.power_entry = ttk.Entry(frame)
        self.power_entry.grid(row=1, column=1)
        self.power_entry.bind("<Return>", self.handle_power_input)

        self.status_label = ttk.Label(self, text="Connecting...", foreground="orange")
        self.status_label.pack(pady=(5, 0))

        tk.Label(self, text="Current Altitude:").pack(padx=10)
        tk.Label(self, textvariable=self.altitude_var).pack(padx=10)

        tk.Label(self, text="Current Power:").pack(padx=10)
        tk.Label(self, textvariable=self.power_var).pack(padx=10)

        tk.Label(self, text="Current rise rate:").pack(padx=10)
        tk.Label(self, textvariable=self.rise_var).pack(padx=10)

        tk.Label(self, text="Current angle:").pack(padx=10)
        tk.Label(self, textvariable=self.angle_var).pack(padx=10)

        tk.Label(self, text="Current state:").pack(padx=10)
        tk.Label(self, textvariable=self.status_var).pack(padx=10)

        fig = Figure(figsize=(5, 2), dpi=100)
        self.ax = fig.add_subplot(111)
        self.altitude_line, = self.ax.plot([], [], label="Altitude (ft)")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Altitude")
        self.ax.set_title("Altitude vs Time")

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.get_tk_widget().pack()
        self.canvas.draw()

    def update_altitude_plot(self):
        if self.altitude_var.get() is None:
            return
        current_time = time.time() - self.start_time
        self.time_history.append(current_time)
        self.altitude_history.append(float(self.altitude_var.get()))

        # Keep last 100 points for performance
        self.time_history = self.time_history[-100:]
        self.altitude_history = self.altitude_history[-100:]

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
            power = int(self.power_entry.get())

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
                words = self.socket.recv(64).decode('utf-8').strip().split("\n")
                if not words:
                    break
                for word in words:
                    if not word:
                        continue
                    data = int(word)
                    decoded = ARINC429.decode(data)
                    if decoded == [None]:
                        print("No data")
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
