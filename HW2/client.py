import socket
import struct


HEADER_FORMAT = "!I"  # 4-byte unsigned length in network byte order
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("Server closed the connection")
        chunks.extend(chunk)
    return bytes(chunks)


def send_message(sock: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError("Message is too large")
    sock.sendall(struct.pack(HEADER_FORMAT, len(payload)) + payload)


def receive_message(sock: socket.socket) -> str:
    header = recv_exact(sock, HEADER_SIZE)
    (message_size,) = struct.unpack(HEADER_FORMAT, header)
    if message_size > MAX_MESSAGE_SIZE:
        raise ValueError("Server message is too large")
    return recv_exact(sock, message_size).decode("utf-8")


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("127.0.0.1", 9000))
        print("Connected. Type /help for commands.")
        while True:
            try:
                message = input("Enter the command: ").strip()
                if not message:
                    continue
                send_message(sock, message)
                print(receive_message(sock))
                if message == "/quit":
                    break
            except (ConnectionError, OSError) as error:
                print(f"Connection ended: {error}")
                break


if __name__ == "__main__":
    main()
