from abc import ABC, abstractmethod


class CompressionStrategy(ABC):
    name: str

    @abstractmethod
    def compress(self, data: bytes) -> bytes: ...

    @abstractmethod
    def decompress(self, data: bytes) -> bytes: ...
