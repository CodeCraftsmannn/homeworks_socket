import socket
import struct
from dataclasses import dataclass
from datetime import datetime


HEADER_FORMAT = "!I"  # 4-byte unsigned length in network byte order
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024


@dataclass
class Task:
    text: str
    created_at: datetime
    deadline: datetime


class Server:
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen()
        self.tasks: list[Task] = []
        print(f"Started listening on {(host, port)}")

    @staticmethod
    def recv_exact(sock: socket.socket, size: int) -> bytes | None:
        """Read exactly size bytes; return None for a clean close before any bytes."""
        chunks = bytearray()
        while len(chunks) < size:
            chunk = sock.recv(size - len(chunks))
            if not chunk:
                if not chunks:
                    return None
                raise ConnectionError("Connection closed in the middle of a message")
            chunks.extend(chunk)
        return bytes(chunks)

    @classmethod
    def recvdata(cls, sock: socket.socket) -> str | None:
        header = cls.recv_exact(sock, HEADER_SIZE)
        if header is None:
            return None
        (message_size,) = struct.unpack(HEADER_FORMAT, header)
        if message_size > MAX_MESSAGE_SIZE:
            raise ValueError("Message is too large")
        payload = cls.recv_exact(sock, message_size)
        if payload is None:
            raise ConnectionError("Connection closed before the message payload arrived")
        return payload.decode("utf-8")

    @staticmethod
    def senddata(sock: socket.socket, text: str) -> None:
        payload = text.encode("utf-8")
        if len(payload) > MAX_MESSAGE_SIZE:
            raise ValueError("Message is too large")
        header = struct.pack(HEADER_FORMAT, len(payload))
        sock.sendall(header + payload)

    @staticmethod
    def split_command(message: str) -> tuple[str | None, str | None]:
        if not message.startswith("/"):
            return None, None
        command, separator, argument = message.partition(" ")
        return command, argument if separator else None

    def add_task(self, argument: str | None) -> str:
        if not argument:
            return "Usage: /add task description YYYY-MM-DD"
        try:
            text, deadline_text = argument.rsplit(" ", 1)
            deadline = datetime.strptime(deadline_text, "%Y-%m-%d")
        except (ValueError, TypeError):
            return "Invalid date. Usage: /add task description YYYY-MM-DD"
        if not text.strip():
            return "Task description cannot be empty"
        self.tasks.append(Task(text=text.strip(), created_at=datetime.now(), deadline=deadline))
        return "Task was added"

    def remove_task(self, text: str | None) -> str:
        if not text:
            return "Usage: /remove task description"
        for task in self.tasks:
            if task.text == text:
                self.tasks.remove(task)
                return "Task was deleted"
        return "Task was not found"

    def list_tasks(self) -> str:
        if not self.tasks:
            return "No tasks"
        today = datetime.now().date()
        lines = []
        for index, task in enumerate(self.tasks, start=1):
            days_left = (task.deadline.date() - today).days
            lines.append(
                f"{index}. {task.text} | deadline: {task.deadline:%Y-%m-%d} "
                f"| days left: {days_left} | created: {task.created_at:%Y-%m-%d %H:%M:%S}"
            )
        return "\n".join(lines)

    def handle(self, message: str) -> tuple[str, bool]:
        command, argument = self.split_command(message)
        if command == "/add":
            return self.add_task(argument), False
        if command == "/remove":
            return self.remove_task(argument), False
        if command == "/list":
            return self.list_tasks(), False
        if command == "/quit":
            return "Exit done", True
        if command == "/help":
            return "Commands: /add description YYYY-MM-DD, /list, /remove description, /quit", False
        return "Unknown command. Type /help", False

    def serve_client(self, client_sock: socket.socket, client_addr) -> None:
        print(f"Connected from: {client_addr}")
        with client_sock:
            while True:
                try:
                    message = self.recvdata(client_sock)
                    if message is None:
                        break
                    response, should_quit = self.handle(message)
                    self.senddata(client_sock, response)
                    if should_quit:
                        break
                except (ConnectionError, UnicodeDecodeError, ValueError) as error:
                    print(f"Client connection ended: {error}")
                    break
        print(f"Disconnected: {client_addr}")

    def serve(self) -> None:
        print("Waiting for a client...")
        try:
            while True:
                client_sock, client_addr = self.sock.accept()
                self.serve_client(client_sock, client_addr)
        except KeyboardInterrupt:
            print("Server stopped")
        finally:
            self.sock.close()


if __name__ == "__main__":
    Server("0.0.0.0", 9000).serve()
