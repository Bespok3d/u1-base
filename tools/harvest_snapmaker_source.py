# SPDX-FileCopyrightText: Copyright (C) 2026 unlucio and the Bespok3d contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Fill this repo's copy of Snapmaker's Klipper source from Snapmaker's own firmware downloads.

Every patch here has to fit Snapmaker's real file on every firmware a printer can be running, and
proving that needs those files. Snapmaker's GitHub mirror is published late and skips releases, so
the source is taken from the firmware image on their wiki instead: the release notes link every
release to its download, the download holds the root filesystem, and the root filesystem holds the
Klipper tree the printer runs.

The images are large and the six files taken out of each one are not, so what this repo keeps is
the files. Run this when Snapmaker publishes a firmware, or when a base package takes over a file
the corpus does not have yet:

    python3 tools/harvest_snapmaker_source.py

It needs network and `unsquashfs` (`brew install squashfs`, `apt-get install squashfs-tools`).
Nothing else in this repo does: the gate reads the harvested files and never the network.
"""

import argparse
import json
import shutil
import sys
import tempfile
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from snapmaker_source.releases import download_per_page
from snapmaker_source.upgrade_image import (
    KLIPPER_ROOT_IN_ROOTFS,
    carve_filesystem,
    filesystems_in,
    unpack_klipper_files,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
# Where the harvest has to land, and how one build number compares to another, are the fit proof's
# own answers. They are taken from it rather than restated here, because a second copy of either is
# a corpus written where nothing reads it, or a release quietly left out of the proof.
sys.path.insert(0, str(REPO_ROOT / "tests_support"))

from firmware_stock import CORPUS_ROOT, KLIPPY_PREFIX, firmware_order  # noqa: E402

IMAGE_CACHE = Path.home() / ".cache" / "bespok3d" / "u1-upgrade-images"
# Every base package declares fw_min 1.3.0, so an older firmware selects no variant of any of them
# and there is nothing about it left to prove.
OLDEST_BUILD_A_BASE_PACKAGE_FITS = "1.3.0"


def owned_klipper_paths() -> list[str]:
    """The Snapmaker files the base layer takes over, read from the manifests that declare them."""
    instruments = [
        entry
        for manifest in sorted(REPO_ROOT.glob("u1-base-*/manifest.json"))
        for entry in json.loads(manifest.read_text())["install"]["instrument"]
    ]
    return sorted({KLIPPY_PREFIX + str(entry["name"]) for entry in instruments})


def cached_image(download_url: str, image_dir: Path) -> Path:
    """The image on this machine, downloaded once and kept, because it is a quarter of a gigabyte
    and a second base package should not cost a second download."""
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / download_url.rsplit("/", 1)[-1]
    if image_path.is_file():
        return image_path
    part_path = image_path.with_suffix(".part")
    urllib.request.urlretrieve(download_url, part_path)  # noqa: S310
    part_path.rename(image_path)
    return image_path


def unpacked_klipper_root(
    image_path: Path, klipper_paths: Sequence[str], workspace: Path
) -> Path | None:
    """The Klipper tree unpacked out of the first filesystem in the image that holds these files."""
    image = image_path.read_bytes()
    for offset, length in filesystems_in(image):
        carved = carve_filesystem(image, offset, length, workspace / "rootfs.squashfs")
        unpacked = workspace / "unpacked"
        if unpack_klipper_files(carved, klipper_paths, unpacked):
            return unpacked / KLIPPER_ROOT_IN_ROOTFS
    return None


def store_klipper_files(klipper_root: Path, klipper_paths: Sequence[str], into: Path) -> None:
    for klipper_path in klipper_paths:
        kept = into / klipper_path
        kept.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(klipper_root / klipper_path, kept)


def harvest_build(build: str, download_url: str, klipper_paths: Sequence[str], corpus: Path,
                  image_dir: Path) -> bool:
    image_path = cached_image(download_url, image_dir)
    with tempfile.TemporaryDirectory() as workspace:
        klipper_root = unpacked_klipper_root(image_path, klipper_paths, Path(workspace))
        if klipper_root is None:
            return False
        store_klipper_files(klipper_root, klipper_paths, corpus / build)
    return True


def wanted_downloads(only: Sequence[str], oldest: str) -> tuple[list[tuple[str, str]], list[str]]:
    """The builds to harvest, and the release notes pages the wiki lists but does not serve yet.

    An unserved page is reported rather than passed over, because a release Snapmaker publishes
    later is a firmware printers will be running that this corpus would silently not cover.
    """
    per_page = download_per_page()
    unpublished = sorted(page_url for page_url, download in per_page.items() if download is None)
    published = [download for download in per_page.values() if download is not None]
    if only:
        return [download for download in published if download[0] in only], unpublished
    wanted = [item for item in published if firmware_order(item[0], oldest) >= 0]
    return wanted, unpublished


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Harvest Snapmaker's Klipper source from firmware."
    )
    parser.add_argument("--build", action="append", default=[],
                        help="harvest only this build number; repeatable")
    parser.add_argument("--oldest", default=OLDEST_BUILD_A_BASE_PACKAGE_FITS,
                        help="the oldest build to harvest when no --build is given")
    parser.add_argument("--corpus", type=Path, default=CORPUS_ROOT)
    parser.add_argument("--image-dir", type=Path, default=IMAGE_CACHE)
    asked = parser.parse_args()

    klipper_paths = owned_klipper_paths()
    downloads, unpublished = wanted_downloads(asked.build, asked.oldest)
    for page_url in unpublished:
        print(f"{page_url}: listed by Snapmaker, no image published yet, harvest again later")
    if not downloads:
        print("Snapmaker's release notes link no download matching what was asked for.")
        return 1
    missed = [
        build
        for build, download_url in downloads
        if not harvest_build(build, download_url, klipper_paths, asked.corpus, asked.image_dir)
    ]
    for build, _ in downloads:
        outcome = "no Klipper source found in the image" if build in missed else "harvested"
        print(f"{build}: {outcome}")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
