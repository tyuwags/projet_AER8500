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
        self.angle = 0
        self.desired_angle = 0
        self.desired_climb = 0
        self.desired_altitude = 40000
        self.auto = True  # Nouveau flag : True = mode automatique, False = manuel

    def validate_inputs(self):
        if not (0 <= self.desired_power <= 100):
            print("Erreur : puissance invalide")
            self.desired_power = max(0, min(self.desired_power, 100))
        if not (-16 <= self.desired_angle <= 16):
            print("Erreur : angle invalide")
            self.desired_angle = max(-16, min(self.desired_angle, 16))
        if abs(self.desired_climb * 60) > 800:
            print("Erreur : taux de montée dépassé")
            self.desired_climb = max(-800 / 60, min(self.desired_climb, 800 / 60))

    def angle_rise(self) -> list:
        self.validate_inputs()

        # MODE AUTOMATIQUE
        if self.auto:
            if self.power != self.desired_power:
                diff = self.desired_power - self.power
                if diff < 0:
                    self.power += max(diff / 2, -5)
                else:
                    self.power += min(diff / 2, 5)

            V = self.power * 0.6 / 3.6 * 3.28084

            # Calcul of the rate of climb and the rise angle
            if abs(self.desired_altitude - self.altitude) > 0.1:
                diff = self.desired_altitude - self.altitude
                if diff < 0:
                    angle = max(diff / 100, -16)
                else:
                    angle = min(diff / 100, 16)
                angle = np.deg2rad(angle)
                climb_rate = V * np.sin(angle)

                if climb_rate < 0:
                    climb_rate = max(climb_rate, -800 / 60)
                    climb_rate = max(climb_rate, self.climb - 0.05)
                else:
                    climb_rate = min(climb_rate, 800 / 60)
                    climb_rate = min(climb_rate, self.climb + 0.05)

                self.climb = climb_rate

                if V != 0:
                    angle = np.arcsin(climb_rate / V)

                new_altitude = self.altitude + climb_rate
                climb_rate *= 60
                self.altitude = new_altitude
                new_state = ARINC429.ALTITUDE_CHANGE
                self.angle = np.rad2deg(angle)
            else:
                if abs(self.altitude) < 1:
                    new_state = ARINC429.ON_GROUND
                    self.altitude = 0
                else:
                    new_state = ARINC429.CRUISE
                    new_altitude = self.desired_altitude
                    self.altitude = new_altitude

                self.climb = 0
                self.angle = 0

            self.state = new_state

            return [
                ARINC429.encode(1, 0, self.altitude, self.state),
                ARINC429.encode(2, 0, 60 * self.climb),
                ARINC429.encode(3, 0, self.angle),
                ARINC429.encode(4, 0, self.power)
            ]
        # MODE MANUEL
        if self.state == ARINC429.ON_GROUND:
            if self.desired_climb != 0 and self.desired_angle != 0:
                self.state = ARINC429.ALTITUDE_CHANGE
                self.desired_altitude = 40000
            elif abs(self.desired_altitude - self.altitude) > 0.1:
                if self.desired_climb == 0:
                    self.desired_climb = 400 / 60
                if self.desired_angle == 0:
                    self.desired_angle = 10
                self.state = ARINC429.ALTITUDE_CHANGE
            else:
                return [ARINC429.encode(1, 0, 0, ARINC429.ON_GROUND)]

        diff = self.desired_altitude - self.altitude
        if abs(diff) > 0.1:
            factor = min(abs(diff) / 100, 1.0)

            climb_target = self.desired_climb * factor
            if self.desired_climb < 0:
                self.climb = max(climb_target, self.climb - 0.05)
            else:
                self.climb = min(climb_target, self.climb + 0.05)

            self.altitude += self.climb

            if abs(self.desired_angle) > 0.1:
                V = self.climb / np.sin(np.deg2rad(self.desired_angle))
                self.power = max(50, min(V / (0.6 / 3.6 * 3.28084), 100))
                V = self.power * 0.6 / 3.6 * 3.28084
                self.angle = np.rad2deg(np.arcsin(self.climb / V) if V != 0 else 0)
        else:
            self.climb = 0
            self.angle = 0
            self.desired_climb = 0
            self.desired_angle = 0
            self.altitude = round(self.desired_altitude)
            self.state = ARINC429.CRUISE if self.altitude > 0 else ARINC429.ON_GROUND

        return [
            ARINC429.encode(1, 0, self.altitude, self.state),
            ARINC429.encode(2, 0, 60 * self.climb),
            ARINC429.encode(3, 0, self.angle),
            ARINC429.encode(4, 0, self.power)
        ]

    def process_label_001(self, label_out, sdi, ssm, out) -> list:
        desired_altitude, state = out
        if state is None or desired_altitude is None:
            return [ARINC429.encode(label_out, sdi, None, state)]

        self.desired_altitude = desired_altitude
        return self.angle_rise()

    def process_label_002(self, label_out, sdi, ssm, out) -> list:
        self.desired_climb = out / 60
        return self.angle_rise()

    def process_label_003(self, label_out, sdi, ssm, out) -> list:
        self.desired_angle = out
        return self.angle_rise()

    def process_label_004(self, label_out, sdi, ssm, out) -> list:
        self.desired_power = out
        return [ARINC429.encode(label_out, sdi, self.power)]

    def process_label_005(self, label_out, sdi, ssm, out) -> list:
        self.auto = bool(out)
        return [ARINC429.encode(label_out, sdi, self.auto)]

    def error(self) -> list:
        return [ARINC429.encode(0, 0, None)]

    def process_data(self, data) -> list:
        result = ARINC429.decode(data)
        if result == [None]:
            print("Invalid data")
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
            case 5:
                return self.process_label_005(label_out, sdi, ssm, out)
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
                words = client_socket.recv(256).decode('utf-8').strip().split("\n")
                if not words:
                    break
                for word in words:
                # print(f"Received from {address}: {word}")
                    if not word:
                        continue

                    word = int(word)

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
