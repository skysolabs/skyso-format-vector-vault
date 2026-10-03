"""Version 1 SKY0 container reader and writer."""
import hashlib
import json
import mimetypes
import struct
import zipfile
from io import BytesIO

from compression.zstd import ZstdCompression
from core.integrity import sha256
from core.processor import safe_filename

MAGIC = b"SKY0"
VERSION = 1
HEADER = struct.Struct(">4sHHI")  # magic, version, flags, manifest byte length
FOOTER_SIZE = 32  # SHA-256 of header + manifest + payload area
MAX_FILES = 1000
MAX_CONTAINER_BYTES = 250 * 1024 * 1024
MAX_FILE_BYTES = 250 * 1024 * 1024
zstd = ZstdCompression()


class ContainerError(ValueError):
    pass


def build_container(records: list[tuple[str, bytes]]) -> bytes:
    if not records or len(records) > MAX_FILES:
        raise ContainerError("A Skyso file must contain between 1 and 1000 files.")
    entries, payloads, names = [], [], set()
    for name, original in records:
        try:
            name = safe_filename(name)
        except ValueError as exc:
            raise ContainerError(str(exc)) from exc
        if name.casefold() in names:
            raise ContainerError("Files must have unique names to preserve them safely.")
        names.add(name.casefold())
        if len(original) > MAX_FILE_BYTES:
            raise ContainerError("A file exceeds the 250 MB limit.")
        compressed = zstd.compress(original)
        method, payload = ("zstd", compressed) if len(compressed) < len(original) else ("raw", original)
        entries.append({"name": name, "size": len(original), "compressed_size": len(payload), "sha256": sha256(original), "compression": method})
        payloads.append(payload)

    # Offsets are relative to the first payload byte.
    offset = 0
    for entry, payload in zip(entries, payloads):
        entry["offset"] = offset
        offset += len(payload)
    manifest = json.dumps({"files": entries}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    header = HEADER.pack(MAGIC, VERSION, 0, len(manifest))
    body = header + manifest + b"".join(payloads)
    result = body + hashlib.sha256(body).digest()
    if len(result) > MAX_CONTAINER_BYTES:
        raise ContainerError("The resulting container exceeds the 250 MB limit.")
    return result


def _parse(data: bytes):
    if len(data) < HEADER.size + FOOTER_SIZE or len(data) > MAX_CONTAINER_BYTES:
        raise ContainerError("The container size is invalid or exceeds 250 MB.")
    magic, version, flags, manifest_len = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ContainerError("This is not a valid Skyso container (invalid magic bytes).")
    if version != VERSION or flags != 0:
        raise ContainerError("This Skyso format version is not supported.")
    manifest_start = HEADER.size
    payload_start = manifest_start + manifest_len
    footer_start = len(data) - FOOTER_SIZE
    if payload_start > footer_start:
        raise ContainerError("The manifest is truncated.")
    if not hashlib.sha256(data[:footer_start]).digest() == data[footer_start:]:
        raise ContainerError("Container integrity verification failed.")
    try:
        manifest = json.loads(data[manifest_start:payload_start].decode("utf-8"))
        files = manifest["files"]
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
            raise ValueError
    except (UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise ContainerError("The Skyso manifest is invalid.") from exc
    payload_area_size = footer_start - payload_start
    spans, names = [], set()
    for entry in files:
        try:
            original_name = entry["name"]
            name = safe_filename(original_name)
            if name != original_name or name.casefold() in names:
                raise ValueError
            names.add(name.casefold())
            size, length, offset = entry["size"], entry["compressed_size"], entry["offset"]
            method, digest = entry["compression"], entry["sha256"]
            if not all(isinstance(n, int) and n >= 0 for n in (size, length, offset)) or size > MAX_FILE_BYTES:
                raise ValueError
            if method not in {"raw", "zstd"} or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError
            if offset + length > payload_area_size:
                raise ValueError
            spans.append((offset, offset + length))
        except (KeyError, TypeError, ValueError) as exc:
            raise ContainerError("The Skyso manifest contains an unsafe or invalid file entry.") from exc
    ordered_spans = sorted(spans)
    if any(a[1] > b[0] for a, b in zip(ordered_spans, ordered_spans[1:])):
        raise ContainerError("The Skyso manifest contains overlapping payloads.")
    return files, data, payload_start


def inspect_container(data: bytes) -> dict:
    files, _, _ = _parse(data)
    return {"format": "SKY0", "version": VERSION, "file_count": len(files), "container_size": len(data), "integrity": "valid", "files": [{"name": f["name"], "size": f["size"], "compressed_size": f["compressed_size"], "compression": f["compression"], "sha256": f["sha256"]} for f in files]}


def restore_container(data: bytes, selected: list[str] | None = None):
    files, data, payload_start = _parse(data)
    if selected is not None and not selected:
        raise ContainerError("Select at least one file to restore.")
    chosen = set(selected) if selected is not None else None
    restored = []
    for entry in files:
        if chosen is not None and entry["name"] not in chosen:
            continue
        start = payload_start + entry["offset"]
        payload = data[start:start + entry["compressed_size"]]
        try:
            original = zstd.decompress(payload) if entry["compression"] == "zstd" else payload
        except Exception as exc:
            raise ContainerError(f"Could not decompress {entry['name']}.") from exc
        if len(original) != entry["size"] or sha256(original) != entry["sha256"]:
            raise ContainerError(f"Integrity verification failed for {entry['name']}.")
        restored.append((entry["name"], original))
    if chosen is not None and len(restored) != len(chosen):
        raise ContainerError("The selection contains a file that is not in this container.")
    if not restored:
        raise ContainerError("There are no files to restore.")
    if len(restored) == 1:
        name, contents = restored[0]
        return contents, name, mimetypes.guess_type(name)[0] or "application/octet-stream"
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, contents in restored:
            zf.writestr(name, contents)
    return archive.getvalue(), "restored_files.zip", "application/zip"
