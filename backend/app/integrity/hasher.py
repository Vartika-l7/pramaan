"""Cryptographic hashing utilities for PRAMAAN."""

import hashlib
from pathlib import Path
from typing import BinaryIO, Union


def hash_stream(stream: BinaryIO, chunk_size: int = 1024 * 1024) -> str:
    """Stream a file-like object in 1MB chunks and return its hexadecimal SHA-256 hash."""
    hasher = hashlib.sha256()
    while chunk := stream.read(chunk_size):
        hasher.update(chunk)
    return hasher.hexdigest()


def hash_file(file_path: Union[str, Path], chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 of a local file in 1MB chunks."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for hashing: {file_path}")
    with open(path, "rb") as f:
        return hash_stream(f, chunk_size)


def hash_bytes(data: bytes) -> str:
    """Compute SHA-256 of in-memory bytes."""
    return hashlib.sha256(data).hexdigest()

