import socket
import threading

import numpy as np

from arinc429 import ARINC429


class Calculator:

    def __init__(self):
        self.state = ARINC429.ON_GROUND
        self.altitude = 0
        self.power = 0
        self.desired_power = 0
        self.climb = 0
    """Simple calculator class that supports basic operations."""

    def process_label_001(self, label_out, sdi, ssm, out) -> list:
        desired_altitude, state = out
        if state is None:
            return [ARINC429.encode(label_out, sdi, None, None)]

        if desired_altitude is None:
            return [ARINC429.encode(label_out, sdi, None, state)]

        if self.power != self.desired_power:
            diff = self.desired_power - self.power
            if diff < 0:
                self.power += max(diff/2, -5)
            else:
                self.power += min(diff/2, 5)

        V = self.power * 0.6 /3.6*3.28084

        # Calcul of the rate of climb and the rise angle
        if abs(desired_altitude - self.altitude) > 1:
            diff = desired_altitude - self.altitude
            if diff < 0:
                angle = max(diff/100, -16)
            else:
                angle = min(diff/100, 16)
            angle = np.deg2rad(angle)
            climb_rate = V * np.sin(angle)

            if climb_rate < 0:
                climb_rate = max(climb_rate, -800/60)
                climb_rate = max(climb_rate, self.climb - 0.05)
            else:
                climb_rate = min(climb_rate, 800/60)
                climb_rate = min(climb_rate, self.climb + 0.05)

            self.climb = climb_rate

            if V != 0:
                angle = np.arcsin(climb_rate/V)

            new_altitude = self.altitude + climb_rate
            climb_rate *= 60
            self.altitude = new_altitude
            new_state = ARINC429.ALTITUDE_CHANGE
            angle = np.rad2deg(angle)
        else:
            if abs(self.altitude) < 1:
                new_state = ARINC429.ON_GROUND
                new_altitude = 0
                self.altitude = 0
            else:
                new_state = ARINC429.CRUISE
                new_altitude = desired_altitude
                self.altitude = new_altitude

            climb_rate = 0
            angle = 0

        self.state = new_state

        return [ARINC429.encode(label_out, sdi, new_altitude, new_state), ARINC429.encode(2, sdi, climb_rate), ARINC429.encode(3, sdi, angle), ARINC429.encode(4, sdi, self.power)]


    def process_label_002(self, label_out, sdi, ssm, out) -> list:
        # Shouldn't process this label in calculator class
        return [ARINC429.encode(label_out, sdi, None)]

    def process_label_003(self, label_out, sdi, ssm, out) -> list:
        # Shouldn't process this label in calculator class
        return [ARINC429.encode(label_out, sdi, None)]

    def process_label_004(self, label_out, sdi, ssm, out) -> list:
        self.desired_power = out
        return [ARINC429.encode(label_out, sdi, self.power)]

    def error(self) -> list:
        return [ARINC429.encode(0, 0, None)]

    def process_data(self, data) -> list:
        """Process a request string and return the result."""
        result = ARINC429.decode(data)
        if result == [None]:
            print("No data")
            return self.error()
        label_out, sdi, ssm, out = result

        match label_out:
            case 1:
                return self.process_label_001(label_out, sdi, ssm, out)
            case 2:
                return self.process_label_002(label_out, sdi, ssm, out)
            case 3:
                return self.process_label_003(label_out, sdi, ssm, out)
            case 4:
                return self.process_label_004(label_out, sdi, ssm, out)
            case _:
                return self.error()



class CalculatorServer:
    """Socket server to handle multiple clients concurrently."""

    def __init__(self, host="127.0.0.1", port=65432):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)  # Allow up to 5 clients in queue
        print(f"Server started on {self.host}:{self.port}")

    def handle_client(self, client_socket, address, calculator):
        """Handle a single client connection."""
        print(f"Client connected: {address}")

        while True:
            try:
                word = int(client_socket.recv(64).decode('utf-8').strip())
                if not word:
                    break

                # print(f"Received from {address}: {word}")

                response = calculator.process_data(word)
                for res in response:
                    client_socket.sendall(str(res).encode()+"\n".encode())

            except Exception as e:
                print(f"Error with client {address}: {str(e)}")
                break

        print(f"Client disconnected: {address}")
        client_socket.close()

    def start(self):
        """Start the server and accept multiple clients concurrently."""
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                calculator = Calculator()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address, calculator))
                client_thread.start()
        except KeyboardInterrupt:
            print("Shutting down server...")
        finally:
            self.server_socket.close()


if __name__ == "__main__":
    server = CalculatorServer()
    server.start()
