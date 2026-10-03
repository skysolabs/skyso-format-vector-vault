import hashlib
import zipfile
from io import BytesIO

from core.container import build_container, restore_container


def test_files_recover_byte_for_byte():
    source = [("notes.txt", b"hello\n"), ("photo.png", bytes(range(256))), ("clip.mp4", b"\x00\xffvideo" * 50)]
    result, _, _ = restore_container(build_container(source))
    with zipfile.ZipFile(BytesIO(result)) as archive:
        for name, data in source:
            assert hashlib.sha256(archive.read(name)).digest() == hashlib.sha256(data).digest()
