# SKY0 container format, version 1

All integer fields use big-endian byte order. A version 1 file is laid out as:

```text
Header (12 bytes) | UTF-8 JSON manifest | payload area | footer (32 bytes)
```

## Header

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | Magic | ASCII `SKY0` |
| 4 | 2 | Version | `1` |
| 6 | 2 | Flags | `0` |
| 8 | 4 | Manifest length | Number of manifest bytes |

The header is encoded with the Python struct format `>4sHHI`.

## Manifest

The manifest is compact UTF-8 JSON. It is an object with a `files` array. Each file object contains:

* `name`: a basename only (no directory components)
* `size`: original byte length
* `compressed_size`: payload byte length
* `sha256`: lowercase hexadecimal SHA-256 of the original bytes
* `compression`: `zstd` or `raw`
* `offset`: byte offset from the beginning of the payload area

Payloads are stored consecutively in manifest order. `raw` means the original bytes are stored unchanged. The writer uses `zstd` only when its payload is smaller than the original.

## Footer and integrity

The final 32 bytes are the binary SHA-256 digest of every preceding byte, from the start of the header through the final payload byte. Readers must verify this digest before trusting the manifest. They must also check each restored file's original size and SHA-256 before returning it.

This checksum detects corruption; it does not authenticate the producer or provide encryption.

## Reader limits and safety

The MVP caps a container at 250 MiB, a restored file at 250 MiB, and a manifest at 1000 files. Readers reject unknown versions and flags, invalid hashes, duplicate or unsafe names, payloads that overlap or exceed the payload area, and any checksum mismatch. Names are treated as basenames when writing a restoration ZIP.
