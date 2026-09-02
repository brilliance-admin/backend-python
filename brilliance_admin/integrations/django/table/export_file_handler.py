from io import BytesIO
from tempfile import TemporaryFile

from django.core.files import File
from django.core.files.storage import default_storage


class MemoryExportFileHandler:
    def __init__(self):
        self.file = BytesIO()

    def write(self, chunk: bytes) -> None:
        self.file.write(chunk)

    def get_content(self) -> bytes:
        return self.file.getvalue()

    def close(self) -> None:
        self.file.close()


class StorageExportFileHandler:
    def __init__(self):
        self.file = TemporaryFile(mode='w+b')

    def write(self, chunk: bytes) -> None:
        self.file.write(chunk)

    def save(self, filename: str) -> str:
        self.file.seek(0)
        name = default_storage.save(filename, File(self.file, name=filename))
        return default_storage.url(name)

    def close(self) -> None:
        self.file.close()
