MAX_UPLOAD_BYTES = 250 * 1024 * 1024


def safe_filename(name: str) -> str:
    # Accept a basename only, preserving every valid filename exactly.
    if (not name or name in {".", ".."} or "/" in name or "\\" in name
            or any(not ch.isprintable() or ch in '<>:"|?*' for ch in name)
            or name.endswith((" ", "."))):
        raise ValueError("A file has an invalid filename.")
    if len(name) > 240:
        raise ValueError("Filenames must be 240 characters or fewer.")
    return name
