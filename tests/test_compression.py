from compression.zstd import ZstdCompression
from core.container import build_container, inspect_container, restore_container


def test_zstd_strategy_round_trip():
    data = b"repeat me " * 10000
    strategy = ZstdCompression()
    assert strategy.decompress(strategy.compress(data)) == data


def test_already_compressed_payload_can_use_raw_storage():
    data = bytes(range(256))
    sky = build_container([("binary.bin", data)])
    info = inspect_container(sky)
    assert info["files"][0]["compression"] == "raw"
    assert restore_container(sky)[0] == data
