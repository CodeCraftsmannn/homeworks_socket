import datetime
import socket
from copy import deepcopy
from dataclasses import dataclass
from queue import Queue
from threading import Thread

from communication import Communication


@dataclass
class Message:
    type: str
    username: str
    date: datetime.datetime
    text: str
    destination_username: str | None = None


class ClientHandler:
    def __init__(self, sock: socket.socket, incoming_queue: Queue):
        self.username: str | None = None
        self.communication = Communication(sock)
        self.incoming_queue: Queue[Message] = incoming_queue
        self.outcoming_queue: Queue[Message] = Queue()

        self.welcome_thread = Thread(target=self.welcome, daemon=True)
        self.writer_thread = Thread(target=self.write, daemon=True)
        self.reader_thread = Thread(target=self.read, daemon=True)

        self.welcome_thread.start()
        self.welcome_thread.join()
        if self.username:
            self.writer_thread.start()
            self.reader_thread.start()

    def welcome(self) -> None:
        while True:
            self.communication.send("Write your username here")
            msg = self.communication.recv()
            if msg is None:
                break
            msg = msg.strip()
            if len(msg) >= 3:
                self.username = msg
                break

    def write(self) -> None:
        while True:
            message: Message = self.outcoming_queue.get()
            text = f"{message.username} [{message.date:%d.%m %H:%M:%S}]: {message.text}"
            try:
                self.communication.send(text)
            except (OSError, ConnectionError):
                break

    def send_system_message(self, text: str) -> None:
        self.outcoming_queue.put(Message(
            type="system",
            username="server",
            date=datetime.datetime.now(),
            text=text,
        ))

    def read(self) -> None:
        while True:
            try:
                text = self.communication.recv()
            except (OSError, ConnectionError, UnicodeDecodeError, ValueError) as error:
                print(f"Client read error: {error}")
                break
            if text is None:
                break

            command, separator, argument = text.partition(" ")
            if not separator:
                argument = ""

            if command == "/private":
                destination, separator, message_text = argument.partition(" ")
                if not separator or not destination or not message_text:
                    self.send_system_message("Usage: /private username message")
                    continue
                message = Message(
                    type=command,
                    username=self.username or "",
                    date=datetime.datetime.now(),
                    text=message_text,
                    destination_username=destination,
                )
            elif command == "/all":
                if not argument:
                    self.send_system_message("Usage: /all message")
                    continue
                message = Message(
                    type=command,
                    username=self.username or "",
                    date=datetime.datetime.now(),
                    text=argument,
                )
            else:
                self.send_system_message("Unknown command. Use /all message or /private username message")
                continue

            # Do not echo the raw command. The dispatcher delivers the message
            # once, which avoids duplicate output for /private to yourself.
            self.incoming_queue.put(message)


class Dispatcher(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.client_handlers: list[ClientHandler] = []
        self.incoming_queue: Queue[Message] = Queue()

    def send_to_all(self, msg: Message) -> None:
        for client_handler in self.client_handlers:
            if msg.username == client_handler.username:
                msg_copy = deepcopy(msg)
                msg_copy.username = "you"
                client_handler.outcoming_queue.put(msg_copy)
            else:
                client_handler.outcoming_queue.put(msg)

    def send_to(self, msg: Message) -> None:
        destination = msg.destination_username
        if not destination:
            return
        recipient = next(
            (handler for handler in self.client_handlers if handler.username == destination),
            None,
        )
        sender = next(
            (handler for handler in self.client_handlers if handler.username == msg.username),
            None,
        )
        if recipient is None:
            if sender is not None:
                sender.send_system_message(f"User '{destination}' was not found")
            return

        if recipient is sender:
            own_message = deepcopy(msg)
            own_message.username = "you"
            recipient.outcoming_queue.put(own_message)
        else:
            recipient.outcoming_queue.put(msg)
            if sender is not None:
                sender.send_system_message(f"Private message sent to {destination}")

    def run(self) -> None:
        while True:
            msg: Message = self.incoming_queue.get()
            if msg.type == "/private":
                self.send_to(msg)
            elif msg.type == "/all":
                self.send_to_all(msg)

    def add(self, handler: ClientHandler) -> None:
        self.client_handlers.append(handler)


class Server:
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen()
        self.dispatcher = Dispatcher()
        self.dispatcher.start()
        print(f"Started listening on {(host, port)}")

    def serve(self) -> None:
        try:
            while True:
                print("Waiting for client to connect...")
                client_sock, client_addr = self.sock.accept()
                print(f"Connected from: {client_addr}")
                client_handler = ClientHandler(client_sock, self.dispatcher.incoming_queue)
                self.dispatcher.add(client_handler)
        except KeyboardInterrupt:
            print("Server stopped")
        finally:
            self.sock.close()


if __name__ == "__main__":
    Server("0.0.0.0", 9000).serve()
