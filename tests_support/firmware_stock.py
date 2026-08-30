"""The stock Snapmaker source a fragment must fit, and the strictness the printer will judge it by.

Every fragment here is a diff against Snapmaker's own Klipper source, and two things have to be true
of it before it ships. Both are proved once here rather than in six near-identical copies.

**The source has to be the source a printer actually runs.** A package declares the firmware a
variant covers as a floor with no ceiling, so a printer on a firmware newer than the one a fragment
was written against takes that fragment regardless. Proving a fragment only against the firmware it
was written for leaves every later firmware unproved, and a printer is where that shows up.

**The strictness has to be the printer's.** The printer carries BusyBox patch, which has no fuzz at
all: a hunk whose context does not match exactly is refused. GNU patch, on a maintainer's Mac and on
CI, defaults to fuzz 2 and will quietly drop context lines to place a hunk. A fragment proved with
the default flags can therefore be turned away by the very printer that has to apply it. That is not
hypothetical: a fragment carrying trailing context Snapmaker had since moved passed here under fuzz
2 and was refused on the bench printer.

These rules mirror `patch_tool.py` in the daemon repo, which is what actually runs on the printer.
They are restated rather than imported because a plugin repo gates without a daemon checkout.

The source itself is vendored, one directory per firmware Snapmaker has published, taken out of
Snapmaker's own firmware download by `tools/harvest_snapmaker_source.py`. It is read from disk and
never fetched, so this gate needs no network and no sibling checkout. See
`snapmaker_source/README.md` for where each firmware came from and how to add the next one.
"""

import itertools
import re
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CORPUS_ROOT = Path(__file__).resolve().parent / "snapmaker_source"
KLIPPY_PREFIX = "klippy/"

# Snapmaker numbers a firmware in four parts, the last being the build: 1.5.0.344.
FIRMWARE_NUMBER_PARTS = 4

# What stops GNU patch guessing and fuzzing, asked for only where they are understood. BusyBox patch
# on the printer has neither behaviour to switch off and exits "invalid option" on -F.
GNU_STRICTNESS = ("-f", "-F0")


def firmware_order(firmware: str, other: str) -> int:
    """Order two firmware numbers the printer's way: a missing trailing part counts as zero, so
    1.4.0 and 1.4.0.0 are the same firmware. Negative, zero or positive, like any comparison."""
    width = max(firmware.count("."), other.count(".")) + 1
    subject, benchmark = _parts(firmware, width), _parts(other, width)
    return (subject > benchmark) - (subject < benchmark)


def _parts(firmware: str, width: int) -> tuple[int, ...]:
    numbered = tuple(int(part) for part in firmware.split("."))
    return numbered + (0,) * (width - len(numbered))


@lru_cache(maxsize=1)
def firmware_releases() -> tuple[str, ...]:
    """Every firmware a fragment is proved against: whatever the vendored source holds, oldest
    first. Harvesting a newly published firmware is all it takes to widen the proof."""
    published = [held.name for held in CORPUS_ROOT.iterdir() if held.is_dir()]
    return tuple(sorted(published, key=lambda firmware: _parts(firmware, FIRMWARE_NUMBER_PARTS)))


FIRMWARE_RELEASES = firmware_releases()


@lru_cache(maxsize=1)
def strictness_flags() -> tuple[str, ...]:
    """The flags that make THIS machine's patch prove a fragment truly fits, asked of the machine
    rather than assumed. GNU patch answers `patch --version` and exits 0; BusyBox does not."""
    version_answer = subprocess.run(["patch", "--version"], capture_output=True, check=False)
    return GNU_STRICTNESS if version_answer.returncode == 0 else ()


def stock_text(klipper_path: str, release: str) -> str:
    """The Snapmaker source of one file as that firmware shipped it.

    A release the packages claim to cover but whose source is not vendored is a failure, never a
    skip. A skipped fit proof reads as a passing one, which is how a fragment that fits no firmware
    a printer runs reached a printer.
    """
    held = CORPUS_ROOT / release / klipper_path
    if not held.is_file():
        raise AssertionError(_no_stock_message(klipper_path, release))
    return held.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _no_stock_message(klipper_path: str, release: str) -> str:
    return (
        f"no stock source for {klipper_path} at firmware {release}. Harvest it from "
        f"Snapmaker's own "
        f"firmware download with `python3 tools/harvest_snapmaker_source.py`, which writes it to "
        f"{CORPUS_ROOT / release / klipper_path}. A fit proof that cannot read the source the "
        f"printer runs must fail, because a skipped one reads as a passing one."
    )


def apply_fragments(stock: str, patch_dir: Path, fragments: tuple[str, ...]) -> str | None:
    """The source that comes out when these fragments are applied in order at printer strictness,
    or None when any one of them does not fit."""
    return _run_fragments(stock, patch_dir, fragments, reverse=False)


def reverse_fragments(patched: str, patch_dir: Path, fragments: tuple[str, ...]) -> str | None:
    """The source that comes back when these fragments are taken off again, or None when any one of
    them does not come off.

    This is the migration's first move: a plugin that stops owning a file takes its own diff back
    off the live file so the base layer can adopt what Snapmaker actually shipped. Fragments come
    off in the opposite order they went on, because a later fragment can sit on lines an earlier
    one wrote.
    Coming off is refused rather than forced for the same reason it is refused going on: a file that
    is not what this plugin produced is a file whose stock original this plugin cannot prove.
    """
    return _run_fragments(patched, patch_dir, tuple(reversed(fragments)), reverse=True)


def _run_fragments(
    source: str, patch_dir: Path, fragments: tuple[str, ...], reverse: bool
) -> str | None:
    with tempfile.TemporaryDirectory() as workdir:
        target = Path(workdir) / "source.py"
        target.write_text(source)
        every_fragment_fits = all(
            _fragment_applies(target, patch_dir / fragment, reverse) for fragment in fragments
        )
        return target.read_text() if every_fragment_fits else None


def _fragment_applies(work_path: Path, patch_file: Path, reverse: bool = False) -> bool:
    if not hunks_apply_the_busybox_way(work_path.read_text(), patch_file.read_text(), reverse):
        return False
    reversal = ("-R",) if reverse else ()
    command = ["patch", *reversal, *strictness_flags(), "--strip=1",
               str(work_path), str(patch_file)]
    result = subprocess.run(command, capture_output=True, check=False)
    reject_path = work_path.parent / (work_path.name + ".rej")
    applied_cleanly = result.returncode == 0 and not reject_path.exists()
    reject_path.unlink(missing_ok=True)
    return applied_cleanly


def fitting_releases(klipper_path: str, patch_dir: Path, fragments: tuple[str, ...]) -> set[str]:
    """Every firmware release these fragments, applied in order, truly fit."""
    return {
        release
        for release in FIRMWARE_RELEASES
        if apply_fragments(stock_text(klipper_path, release), patch_dir, fragments) is not None
    }


HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*$", re.MULTILINE)
IMPLIED_HUNK_COUNT = 1


@dataclass(frozen=True)
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    body: tuple[str, ...]


def hunks_apply_the_busybox_way(source: str, patch_text: str, reverse: bool = False) -> bool:
    """Whether the printer's own patch program takes every hunk of this fragment on this text.

    BusyBox patch streams the file once: each hunk's lines must appear, exactly, somewhere at or
    after the point the previous hunk ended. It never looks back and never fuzzes a context line
    away, and a hunk with fewer trailing than leading context lines is taken to end the file, so it
    only fits there. GNU and BSD patch slide and fuzz, so a fragment they take can still fail on the
    printer (the hunk with two extra leading context lines that rolled a store migration back on the
    bench). Reverse checks the hunk's new side, the way `patch -R` does."""
    source_lines = source.split("\n")
    file_lines = source_lines[:-1] if source_lines[-1] == "" else source_lines
    return _hunks_sit_from(file_lines, _hunks(patch_text), reverse, 0)


def _hunks_sit_from(file_lines: list[str], hunks: list[Hunk], reverse: bool, cursor: int) -> bool:
    if not hunks:
        return True
    expected = _lines_the_file_must_hold(hunks[0], reverse)
    found_at = _first_fit_at_or_after(file_lines, expected, cursor, _must_end_the_file(hunks[0]))
    if found_at is None:
        return False
    return _hunks_sit_from(file_lines, hunks[1:], reverse, found_at + len(expected))


def _first_fit_at_or_after(file_lines: list[str], expected: list[str], cursor: int,
                           must_end_the_file: bool) -> int | None:
    last_start = len(file_lines) - len(expected)
    starts = [last_start] if must_end_the_file else range(cursor, last_start + 1)
    return next(
        (
            start
            for start in starts
            if start >= cursor and file_lines[start : start + len(expected)] == expected
        ),
        None,
    )


def _must_end_the_file(hunk: Hunk) -> bool:
    leading = len(list(itertools.takewhile(_is_context, hunk.body)))
    trailing = len(list(itertools.takewhile(_is_context, reversed(hunk.body))))
    return trailing < leading


def _is_context(line: str) -> bool:
    return line[0] == " "


def _lines_the_file_must_hold(hunk: Hunk, reverse: bool) -> list[str]:
    absent_marker = "-" if reverse else "+"
    return [line[1:] for line in hunk.body if line[0] != absent_marker]


def _hunks(patch_text: str) -> list[Hunk]:
    headers = [match for match in map(HUNK_HEADER.match, patch_text.splitlines()) if match]
    bodies = _hunk_bodies(HUNK_HEADER.split(patch_text))
    return [_hunk(header, body) for header, body in zip(headers, bodies, strict=True)]


def _hunk_bodies(pieces: list[str | None]) -> list[str]:
    group_count = HUNK_HEADER.groups + 1
    return [piece or "" for piece in pieces[group_count::group_count]]


def _hunk(header: re.Match[str], body: str) -> Hunk:
    old_start, old_count, new_start, new_count = (
        IMPLIED_HUNK_COUNT if value is None else int(value) for value in header.groups()
    )
    marked = [line or " " for line in body.removeprefix("\n").split("\n")]
    body_lines = _hunk_body(marked, old_count, new_count)
    return Hunk(old_start, old_count, new_start, new_count, body_lines)


def _hunk_body(marked: list[str], old_count: int, new_count: int) -> tuple[str, ...]:
    body: list[str] = []
    seen_old = seen_new = 0
    for line in marked:
        if seen_old >= old_count and seen_new >= new_count:
            break
        body.append(line)
        seen_old += line[0] != "+"
        seen_new += line[0] != "-"
    return tuple(body)
