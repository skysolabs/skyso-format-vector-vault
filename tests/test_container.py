import pytest

from core.container import ContainerError, build_container, inspect_container, restore_container


def test_unicode_multi_file_round_trip():
    files = [("കേരളം.pdf", b"pdf\x00data"), ("研究.pdf", b"research"), ("résumé.pdf", b"cv")]
    sky = build_container(files)
    assert inspect_container(sky)["file_count"] == 3
    recovered, _, _ = restore_container(sky)
    import zipfile
    from io import BytesIO
    with zipfile.ZipFile(BytesIO(recovered)) as archive:
        assert [(name, archive.read(name)) for name, _ in files] == files


def test_single_empty_file_round_trip():
    sky = build_container([("empty.txt", b"")])
    assert restore_container(sky)[:2] == (b"", "empty.txt")


def test_selected_restore_returns_original_single_file():
    sky = build_container([("a.txt", b"A"), ("b.txt", b"B")])
    assert restore_container(sky, ["b.txt"])[:2] == (b"B", "b.txt")


def test_rejects_corrupted_container():
    sky = bytearray(build_container([("a.bin", b"bytes")]))
    sky[12] ^= 1
    with pytest.raises(ContainerError, match="integrity"):
        inspect_container(bytes(sky))


def test_rejects_duplicate_and_unsafe_names():
    with pytest.raises(ContainerError, match="unique"):
        build_container([("same.txt", b"a"), ("SAME.txt", b"b")])
    with pytest.raises(ContainerError, match="invalid"):
        build_container([("../escape.txt", b"a")])
