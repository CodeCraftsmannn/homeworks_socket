import socket
import struct
from threading import Lock


HEADER_FORMAT = "!I"  # 4-byte unsigned payload length, network byte order
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024


class Communication:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._send_lock = Lock()

    def send(self, message: str) -> None:
        message_bytes = message.encode("utf-8")
        if len(message_bytes) > MAX_MESSAGE_SIZE:
            raise ValueError("Message is too large")
        packet = struct.pack(HEADER_FORMAT, len(message_bytes)) + message_bytes
        # A lock prevents two sender threads from interleaving framed packets.
        with self._send_lock:
            self.sock.sendall(packet)

    def recv_all(self, nbytes: int) -> bytes | None:
        """Read exactly nbytes; None means a clean close before any bytes arrived."""
        data = bytearray()
        while len(data) < nbytes:
            packet = self.sock.recv(nbytes - len(data))
            if not packet:
                if not data:
                    return None
                raise ConnectionError("Connection closed in the middle of a frame")
            data.extend(packet)
        return bytes(data)

    def recv(self) -> str | None:
        header = self.recv_all(HEADER_SIZE)
        if header is None:
            return None
        (message_len,) = struct.unpack(HEADER_FORMAT, header)
        if message_len > MAX_MESSAGE_SIZE:
            raise ValueError("Message is too large")
        message_bytes = self.recv_all(message_len)
        if message_bytes is None:
            raise ConnectionError("Connection closed before the message body arrived")
        return message_bytes.decode("utf-8")

    def close(self) -> None:
        self.sock.close()
