from os import makedirs, rmdir, listdir
import os
from pathlib import Path
import shutil

MAX_SIZE = 1024


class FileManager:
    def __init__(self, home_dir: Path, name: str):
        self.working_dir = home_dir.joinpath(name).resolve()
        if not self.working_dir.exists():
            makedirs(self.working_dir)
        self.current_dir = self.working_dir

    def get_size(self) -> int:
        return sum(f.stat().st_size for f in self.working_dir.glob('**/*')
                   if f.is_file())

    def handle(self, input: bytes) -> str:
        for (command, func) in [(b'lsfolder', self.list_folder),
                                (b'mkfolder', self.make_folder),
                                (b'rmfolder', self.remove_folder),
                                (b'chfolder', self.change_folder),
                                (b'mkfile', self.make_file),
                                (b'wrfile', self.write_to_file),
                                (b'shfile', self.show_file),
                                (b'rmfile', self.remove_file),
                                (b'cpfile', self.copy_file),
                                (b'mvfile', self.move_file),
                                (b'rnfile', self.rename_file),
                                (b'ckqt', self.check_quota)]:
            if input.startswith(command):
                try:
                    return func(input[len(command + b' '):])
                except BaseException as err:
                    return str(err)
                break
        else:
            return 'unknown command'

    def check_path(self, path: bytes):
        path = self.current_dir.joinpath(path.decode()).resolve()
        if not path.is_relative_to(self.working_dir):
            raise Exception("cannot exit working directory")
        return path

    def check_quota(self, _) -> str:
        return f'used {self.get_size()}B of {MAX_SIZE}B'

    def list_folder(self, path: bytes) -> str:
        return '\n'.join(listdir(self.check_path(path)))

    def make_folder(self, path: bytes) -> str:
        makedirs(self.check_path(path))
        return ''

    def remove_folder(self, path: bytes) -> str:
        rmdir(self.check_path(path))
        return ''

    def change_folder(self, path: bytes) -> str:
        self.current_dir = self.check_path(path)
        return ''

    def make_file(self, path: bytes) -> str:
        open(self.check_path(path), 'x').close()
        return ''

    def write_to_file(self, args: bytes) -> str:
        [path, text] = args.split(b'\n', 1)
        if self.get_size() + len(text) > MAX_SIZE:
            return 'space limit exceeded!'
        with open(self.check_path(path), 'wb') as f:
            f.write(text)
        return ''

    def show_file(self, path: bytes) -> str:
        with open(self.check_path(path), 'r') as f:
            return f.read()

    def remove_file(self, path: bytes) -> str:
        self.check_path(path).unlink()
        return ''

    def copy_file(self, args: bytes) -> str:
        [src, dst] = map(self.check_path, args.split())
        size_diff = 0
        if src.is_file():
            size_diff += src.stat().st_size
        if dst.is_file():
            size_diff -= dst.stat().st_size
        if self.get_size() + size_diff > MAX_SIZE:
            return 'space limit exceeded!'
        shutil.copy(src, dst)
        return ''

    def move_file(self, args: bytes) -> str:
        [src, dst] = map(self.check_path, args.split())
        shutil.move(src, dst)
        return ''

    def rename_file(self, args: bytes) -> str:
        [src, dst] = map(self.check_path, args.split())
        os.rename(src, dst)
        return ''
