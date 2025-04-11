import socket
import threading
from arinc429 import ARINC429


class Calculator:
    """Simple calculator class that supports basic operations."""

    def process_label_001(self, label_out, sdi, ssm, out) -> list:
        altitude, state = out
        if state is None:
            return [ARINC429.encode(label_out, sdi, None, None)]

        if altitude is None:
            return [ARINC429.encode(label_out, sdi, None, state)]

        # Calcul of the rate of climb and the rise angle
        new_altitude = 0
        new_state = 0
        climb_rate = 0
        rise_rate = 0

        return [ARINC429.encode(label_out, sdi, new_altitude, new_state), ARINC429.encode(2, sdi, climb_rate), ARINC429.encode(3, sdi, rise_rate)]


    def process_label_002(self, label_out, sdi, ssm, out) -> list:
        # Shouldn't process this label in calculator class
        return [ARINC429.encode(label_out, sdi, None)]

    def process_label_003(self, label_out, sdi, ssm, out) -> list:
        # Shouldn't process this label in calculator class
        return [ARINC429.encode(label_out, sdi, None)]

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
            case _:
                return self.error()



class CalculatorServer:
    """Socket server to handle multiple clients concurrently."""

    def __init__(self, host="127.0.0.1", port=65432):
        self.host = host
        self.port = port
        self.calculator = Calculator()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)  # Allow up to 5 clients in queue
        print(f"Server started on {self.host}:{self.port}")

    def handle_client(self, client_socket, address):
        """Handle a single client connection."""
        print(f"Client connected: {address}")

        while True:
            try:
                word = int(client_socket.recv(32).decode('utf-8').strip())
                if not word:
                    break

                print(f"Received from {address}: {word}")

                response = self.calculator.process_data(word)
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
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
        except KeyboardInterrupt:
            print("Shutting down server...")
        finally:
            self.server_socket.close()


if __name__ == "__main__":
    server = CalculatorServer()
    server.start()
