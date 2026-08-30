# SPDX-FileCopyrightText: Copyright (C) 2026 unlucio and the Bespok3d contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Reaching the Klipper source inside a Snapmaker U1 upgrade image.

The image a printer downloads is a Rockchip update container behind a Snapmaker prefix, and the
root filesystem inside it is a squashfs holding the Klipper tree the printer actually runs. Rather
than parse a container format Snapmaker can change under us, the squashfs is found by its own
superblock and validated by it, so a layout change shows up as "no filesystem found" instead of as
quietly wrong bytes.
"""

import struct
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

SQUASHFS_MAGIC = b"hsqs"
# The squashfs 4.0 superblock, little endian: magic, inode count, build time, block size, fragment
# count, compressor, block log, flags, id count, major, minor, root inode, bytes used.
SUPERBLOCK_LAYOUT = "<4sIIIIHHHHHHQQ"
SUPERBLOCK_SIZE = struct.calcsize(SUPERBLOCK_LAYOUT)
SUPERBLOCK_MAJOR_FIELD = 9
SUPERBLOCK_BYTES_USED_FIELD = 12
READABLE_SQUASHFS_MAJOR = 4
KLIPPER_ROOT_IN_ROOTFS = "home/lava/klipper"


def filesystem_length_at(image: bytes, offset: int) -> int:
    """How many bytes of squashfs start at this offset, or zero if it is not a superblock we read.

    The magic string can occur inside compressed data by chance, so a candidate is only believed
    when its version is one this reads and its own length fits inside the image.
    """
    if len(image) - offset < SUPERBLOCK_SIZE:
        return 0
    superblock = struct.unpack_from(SUPERBLOCK_LAYOUT, image, offset)
    if superblock[SUPERBLOCK_MAJOR_FIELD] != READABLE_SQUASHFS_MAJOR:
        return 0
    bytes_used = int(superblock[SUPERBLOCK_BYTES_USED_FIELD])
    if bytes_used <= SUPERBLOCK_SIZE or offset + bytes_used > len(image):
        return 0
    return bytes_used


def filesystems_in(image: bytes) -> Iterator[tuple[int, int]]:
    """Every squashfs filesystem in the image, as an offset and a length, in the order found."""
    offset = image.find(SQUASHFS_MAGIC)
    while offset != -1:
        length = filesystem_length_at(image, offset)
        if length:
            yield offset, length
        offset = image.find(SQUASHFS_MAGIC, offset + 1)


def carve_filesystem(image: bytes, offset: int, length: int, carved_path: Path) -> Path:
    carved_path.write_bytes(image[offset:offset + length])
    return carved_path


def unpack_klipper_files(carved_path: Path, klipper_names: Sequence[str], into: Path) -> bool:
    """Pull the named Klipper files out of a carved filesystem, and say whether every one arrived.

    A filesystem carved from the wrong offset, or one that is not the root filesystem, unpacks
    nothing and is reported as a miss rather than as an empty success.
    """
    wanted = [f"{KLIPPER_ROOT_IN_ROOTFS}/{name}" for name in klipper_names]
    unpacked = subprocess.run(
        ["unsquashfs", "-q", "-n", "-f", "-d", str(into), str(carved_path), *wanted],
        capture_output=True, check=False,
    )
    if unpacked.returncode != 0:
        return False
    return all((into / KLIPPER_ROOT_IN_ROOTFS / name).is_file() for name in klipper_names)
