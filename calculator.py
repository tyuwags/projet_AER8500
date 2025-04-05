import socket
import threading
from arinc429 import ARINC429


class Calculator:
    """Simple calculator class that supports basic operations."""

    def process_label_001(self, data):
        altitude, state = data
        if state is None:
            return ARINC429.encode(1, 0, None, None)

        if altitude is None:
            return ARINC429.encode(1, 0, None, state)

        # Calcul of the rate of climb and the rise angle
        new_altitude = 0
        new_state = 0
        climb_rate = 0
        rise_rate = 0

        return ARINC429.encode(1, 0, new_altitude, new_state), ARINC429.encode(2, 0, climb_rate), ARINC429.encode(3, 0, rise_rate)



    def process_label_002(self, data):
        # Shouldn't process this label in calculator class
        return ARINC429.encode(2, 0, None)

    def process_label_003(self, data):
        # Shouldn't process this label in calculator class
        return ARINC429.encode(3, 0, None)

    def error(self):
        return ARINC429.encode(0, 0, None)

    def process_data(self, data):
        """Process a request string and return the result."""
        result = ARINC429.decode(data)
        if result is [None]:
            print("No data")
            return self.error()
        label_out, sdi, ssm, out = result

        match label_out:
            case 1:
                return self.process_label_001(out)
            case 2:
                return self.process_label_002(out)
            case 3:
                return self.process_label_003(out)
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
                data = int(client_socket.recv(32).decode('utf-8').strip())
                if not data:
                    break

                print(f"Received from {address}: {data}")

                response = self.calculator.process_data(data)
                client_socket.sendall(str(response).encode())

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
