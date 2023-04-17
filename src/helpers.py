from Crypto.Cipher import AES
import os
import socket
import secrets

P = int('''fca682ce_8e12caba_26efccf7_110e526d_b078b05e_decbcd1e_b4a208f3_\
ae1617ae_01f35b91_a47e6df6_3413c5e1_2ed0899b_cd132acd_50d99151_\
bdc43ee7_37592e17''', base=16)

G = int('''678471b2_7a9cf44e_e91a49c5_147db1a9_aaf244f0_5a434d64_86931d2d_\
14271b9e_35030b71_fd73da17_9069b32e_2935630e_1c206235_4d0da20a_\
6c416e50_be794ca4''', base=16)


def get_private_and_public_keys(path) -> (int, int):
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            contents = f.read()
            return map(lambda x: int.from_bytes(x, 'little'),
                       (contents[:64], contents[64:]))

    with open(path, 'wb') as f:
        private_key = secrets.randbits(512)
        public_key = pow(G, private_key, P)
        f.write(private_key.to_bytes(64, 'little') +
                public_key.to_bytes(64, 'little'))
        return (private_key, public_key)


class MySocket():
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b''
        self.encryptor = None
        self.decryptor = None

    def enable_encryption(self, their_public_key, our_secret_key):
        common_secret_key = pow(
            their_public_key, our_secret_key, P).to_bytes(64, 'little')[:32]
        self.encryptor = AES.new(common_secret_key, AES.MODE_ECB)
        self.decryptor = AES.new(common_secret_key, AES.MODE_ECB)

    def encrypt(self, msg):
        if self.encryptor:
            lm = len(msg) % 16
            if lm:
                msg += bytes(16 - lm)
            return self.encryptor.encrypt(msg)
        else:
            return msg

    def decrypt(self, msg):
        if self.decryptor:
            return self.decryptor.decrypt(msg).rstrip(b'\0')
        else:
            return msg

    def sendall(self, data: bytes):
        data = self.encrypt(data)
        self.sock.sendall('{:04}'.format(len(data)).encode() + data)

    def recv(self, bufsize: int = 1024) -> bytes:
        if not self.buffer:
            self.buffer = self.sock.recv(bufsize)
            if not self.buffer:
                return None
        msg_len = int(self.buffer[:4].decode())
        data = self.decrypt(self.buffer[4:4 + msg_len])
        self.buffer = self.buffer[4 + msg_len:]
        return data

    def accept(self):
        (sock, addr) = self.sock.accept()
        return (MySocket(sock), addr)

    def bind(self, address):
        self.sock.bind(address)

    def listen(self):
        self.sock.listen()

    def getsockname(self):
        return self.sock.getsockname()

    def settimeout(self, value):
        self.sock.settimeout(value)

    def setblocking(self, flag):
        self.sock.setblocking(flag)

    def connect(self, address):
        self.sock.connect(address)

    def close(self):
        self.sock.close()


DEFAULT_PORT = 9090


def get_port() -> int:
    port = input(f'server port ({DEFAULT_PORT}): ')
    if not port:
        return DEFAULT_PORT
    else:
        return int(port)
