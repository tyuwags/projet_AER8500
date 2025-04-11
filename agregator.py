import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import time
from arinc429 import ARINC429  # Update path if needed


class ARINC429GUI(tk.Tk):
    def __init__(self, host="127.0.0.1", port=65432):
        super().__init__()
        self.title("ARINC 429 Interface")
        self.geometry("600x400")
        self.resizable(False, False)

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

        ttk.Label(frame, text="Label:").grid(row=0, column=0, sticky="w")
        self.label_entry = ttk.Entry(frame)
        self.label_entry.grid(row=0, column=1)

        ttk.Label(frame, text="SDI:").grid(row=1, column=0, sticky="w")
        self.sdi_entry = ttk.Entry(frame)
        self.sdi_entry.grid(row=1, column=1)

        ttk.Label(frame, text="Args:").grid(row=2, column=0, sticky="w")
        self.args_entry = ttk.Entry(frame)
        self.args_entry.grid(row=2, column=1)

        self.send_button = ttk.Button(frame, text="Send", command=self.send_data)
        self.send_button.grid(row=3, column=0, columnspan=2, pady=5)

        self.status_label = ttk.Label(self, text="Connecting...", foreground="orange")
        self.status_label.pack(pady=(5, 0))

        ttk.Label(self, text="Received Data:").pack(pady=(10, 0))
        self.output_box = tk.Text(self, height=10, width=70, state='disabled')
        self.output_box.pack(padx=10)

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

    def send_data(self):
        if not self.connected:
            messagebox.showwarning("Not connected", "Currently not connected to the server.")
            return

        try:
            label = int(self.label_entry.get())
            sdi = int(self.sdi_entry.get())
            args = eval(f"({self.args_entry.get()},)")
            encoded = ARINC429.encode(label, sdi, *args)
            self.socket.sendall(str(encoded).encode())
        except Exception as e:
            messagebox.showerror("Send Error", str(e))

    def listen_to_socket(self):
        try:
            while self.connected:
                words = self.socket.recv(32).decode('utf-8').strip().split("\n")
                if not words:
                    break
                for word in words:
                    if not word:
                        continue
                    data = int(word)
                    decoded = ARINC429.decode(int(data))

                    self.output_box.configure(state='normal')
                    self.output_box.insert(tk.END, f"Raw: {data:#010x}\nDecoded: {decoded}\n\n")
                    self.output_box.configure(state='disabled')

        except Exception as e:
            self.output_box.configure(state='normal')
            self.output_box.insert(tk.END, f"Disconnected or error: {e}\n")
            self.output_box.configure(state='disabled')
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
