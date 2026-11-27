import socket
from threading import Thread

from communication import Communication


ADDRESS = ("127.0.0.1", 9000)


def reader(comm: Communication) -> None:
    while True:
        try:
            msg = comm.recv()
        except (OSError, ConnectionError, UnicodeDecodeError, ValueError) as error:
            print(f"Connection ended: {error}")
            break
        if msg is None:
            print("Server closed the connection")
            break
        print(msg)


def writer(comm: Communication) -> None:
    while True:
        try:
            msg = input("")
            comm.send(msg)
        except (EOFError, OSError, ConnectionError, ValueError):
            break


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(ADDRESS)
        print("Connected")
        comm = Communication(sock)
        reader_thread = Thread(target=reader, args=(comm,), daemon=True)
        reader_thread.start()
        writer(comm)
        comm.close()
        reader_thread.join(timeout=1)
    except OSError as error:
        print(f"Could not connect to server: {error}")
        sock.close()


if __name__ == "__main__":
    main()
