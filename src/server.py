from helpers import get_port, MySocket, get_private_and_public_keys
from errno import EADDRINUSE
from hashlib import pbkdf2_hmac
from base64 import b64encode
from threading import Thread, Event
from os import makedirs
from pathlib import Path
from file_manager import FileManager
import shelve
import secrets
import socket
import toml


class Server:
    def __init__(self):
        self.sock = MySocket(socket.socket())

        try:
            self.sock.bind(('', get_port()))
        except OSError as e:
            if e.errno == EADDRINUSE:
                print('port is not available, using a free port')
                self.sock.bind(('', 0))
            else:
                raise e
        self.log('server started')

        self.sock.listen()
        print(f'listening on port {self.sock.getsockname()[1]}')

        self.passwords_db = shelve.open('passwords')
        self.session_tokens_db = shelve.open('session_tokens')

        config = toml.load('config.toml')
        self.home_dir = Path(config['home_dir']).expanduser().resolve()
        if not self.home_dir.exists():
            makedirs(self.home_dir)

        if self.passwords_db.get('admin') is None:
            self.register('admin', b'supersecretadminpassword37868128593')

        self.private_key, self.public_key = get_private_and_public_keys(
            'server_keys')

    def log(self, *values):
        with open('server.log', 'a') as f:
            print(*values, file=f)

    def create_session(self, name) -> bytes:
        session_token = b64encode(secrets.token_bytes())
        self.session_tokens_db[session_token.decode()] = name
        return session_token

    def register(self, name, password):
        salt = secrets.token_bytes(512 // 8)
        hash = pbkdf2_hmac('sha256', password, salt, 100_000)
        self.passwords_db[name] = (salt, hash)
        self.log(f'registered user {name}')

    def authenticate(self, conn) -> bool:
        def greet(name):
            return b'hello ' + name.encode() + b'\n'

        conn.sendall(b'session token (blank if none): ')
        session_token = conn.recv()
        if session_token:
            session_token = session_token.decode()
            for st, n in self.session_tokens_db.items():
                if session_token == st:
                    name = n
                    self.log('authenticated using session token')
                    conn.sendall(greet(name))
                    return name
            conn.sendall(b'wrong session token!\n')
            self.log('got wrong session token')
        else:
            conn.sendall(b'username: ')
            name = conn.recv().decode()
            if not name.encode().isalnum():
                conn.sendall(b'invalid characters in name!\n')
                self.log('got invalid characters in name')
                return
            conn.sendall(b'password: ')
            password = conn.recv()
            salt_and_hash = self.passwords_db.get(name)
            if salt_and_hash is None:
                self.register(name, password)
                session_token = self.create_session(name)
                conn.sendall(greet(name) +
                             b'your session token is ' + session_token + b'\n')
                return name
            else:
                (salt, hash) = salt_and_hash
                if pbkdf2_hmac('sha256', password, salt, 100_000) == hash:
                    self.log('authenticated using password')
                    session_token = self.create_session(name)
                    conn.sendall(greet(name) + b'your new session token is '
                                 + session_token + b'\n')
                    return name
                else:
                    conn.sendall(b'wrong password!\n')
                    self.log('got wrong password')

    def handle_connection(self, conn, addr):
        client_public_key = int.from_bytes(conn.recv(), 'little')
        new_conn = MySocket(socket.socket())
        new_conn.bind(('', 0))
        conn.sendall(self.public_key.to_bytes(64, 'little'))
        conn.enable_encryption(client_public_key, self.private_key)
        conn.sendall(new_conn.getsockname()[1].to_bytes(16, 'little'))
        conn.close()
        self.log('accepting at new port ' + str(new_conn.getsockname()[1]))
        new_conn.listen()
        conn, addr = new_conn.accept()
        conn.enable_encryption(client_public_key, self.private_key)
        name = self.authenticate(conn)
        if not name:
            return

        conn.settimeout(1)

        file_manager = FileManager(self.home_dir, name)

        timeouted = False
        while not self.exit_event.is_set():
            self.pause_event.wait()
            if not timeouted:
                conn.sendall(b'> ')
            try:
                msg = conn.recv()
            except TimeoutError:
                timeouted = True
                continue
            timeouted = False
            if msg is None:
                self.log(f'disconnected {addr}')
                break
            self.log(f'received {len(msg)} bytes')

            output = file_manager.handle(msg)
            conn.sendall(output.encode() + b'\n')

    def accept_loop(self):
        self.exit_event = Event()
        self.pause_event = Event()
        self.pause_event.set()
        self.sock.settimeout(1)
        while not self.exit_event.is_set():
            self.pause_event.wait()
            try:
                conn, addr = self.sock.accept()
            except TimeoutError:
                continue
            self.log(f'connected client {addr}')
            Thread(target=self.handle_connection,
                   args=[conn, addr]).start()

    def input_loop(self):
        while True:
            command = input('> ')
            if command == 'exit':
                self.exit_event.set()
                return
            elif command == 'pause':
                self.pause_event.clear()
            elif command == 'unpause':
                self.pause_event.set()
            elif command == 'show-logs':
                with open('server.log') as f:
                    print(f.read())
            elif command == 'clear-logs':
                open('server.log', 'w').close()
            elif command == 'clear-credentials':
                self.passwords_db.clear()
                self.session_tokens_db.clear()
            else:
                print('unknown command')


def main():
    server = Server()
    Thread(target=server.accept_loop).start()
    server.input_loop()


if __name__ == '__main__':
    main()
