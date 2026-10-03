import zstandard

from compression.base import CompressionStrategy


class ZstdCompression(CompressionStrategy):
    name = "zstd"

    def __init__(self):
        self._compressor = zstandard.ZstdCompressor(level=3)
        self._decompressor = zstandard.ZstdDecompressor()

    def compress(self, data: bytes) -> bytes:
        return self._compressor.compress(data)

    def decompress(self, data: bytes) -> bytes:
        return self._decompressor.decompress(data, max_output_size=250 * 1024 * 1024)
