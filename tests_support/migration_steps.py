"""The states one Snapmaker source file passes through while the base layer takes it over.

The migration is three moves and each one has to be provable on its own. The outgoing plugin takes
its own fragments back off the live file, which is the only way to get Snapmaker's own bytes back
from a printer that has been patched for months. The base package keeps those bytes as the file's
stock original. Then the base package applies its own fragments to them. Getting the order wrong, or
letting a step succeed on a file it cannot prove, is how a printer ends up holding a "stock" copy
that is really some plugin's output, and that copy is the user's only way back.
"""

from functools import cache
from pathlib import Path

from field_printers import (
    Handover,
    base_fragments,
    base_patch_dir,
    field_patch_dir,
    handovers_the_field_holds,
    klipper_path,
)
from firmware_stock import FIRMWARE_RELEASES, apply_fragments, reverse_fragments, stock_text

WHAT_A_USER_LEAVES_BEHIND = "  # a user was here"
SHORTEST_LINE_WORTH_EDITING = 12


@cache
def live_file(handover: Handover, release: str) -> str | None:
    """The file as it sits on a printer running this Snapmaker source release with the released
    plugin installed: Snapmaker's own source with that plugin's fragments on it, in its manifest's
    order. None when the plugin does not fit that source, which is a printer that cannot exist."""
    stock = stock_text(klipper_path(handover), release)
    return apply_fragments(stock, field_patch_dir(handover), handover.plugin_fragments)


@cache
def recovered_stock(handover: Handover, release: str) -> str | None:
    """Move one: the outgoing plugin takes its own fragments back off the live file, so the base
    layer is handed Snapmaker's bytes rather than the plugin's output. None when they do not come
    off, which is the plugin refusing to vouch for a file it cannot prove it produced."""
    live = live_file(handover, release)
    if live is None:
        return None
    return reverse_fragments(live, field_patch_dir(handover), handover.plugin_fragments)


def base_output(source: str, handover: Handover, release: str) -> str | None:
    """Move three: what the base package writes when it patches `source`, or None when its fragments
    do not fit it."""
    return apply_fragments(source, base_patch_dir(handover), base_fragments(handover, release))


def hand_edited(live: str, handover: Handover) -> str:
    """The live file after somebody has been in there with an editor, changing a line the plugin's
    own diff depends on."""
    edited_line = _line_the_diff_depends_on(live, handover)
    return live.replace(edited_line + "\n", edited_line + WHAT_A_USER_LEAVES_BEHIND + "\n", 1)


def printers_the_field_can_hold() -> tuple[tuple[Handover, str], ...]:
    """Every file-and-source-release pair a real printer can be in. The plugin that owns the file
    today has to fit that source for such a printer to exist at all."""
    return tuple(
        (handover, release)
        for handover in handovers_the_field_holds()
        for release in FIRMWARE_RELEASES
        if live_file(handover, release) is not None
    )


def _line_the_diff_depends_on(live: str, handover: Handover) -> str:
    candidates = (
        line
        for fragment in handover.plugin_fragments
        for line in _context_lines(field_patch_dir(handover) / fragment)
        if live.count(line + "\n") == 1
    )
    found = next(candidates, None)
    if found is None:
        raise LookupError(
            f"{handover.plugin} has no context line unique in {handover.klipper_name}"
        )
    return found


def _context_lines(patch_file: Path) -> list[str]:
    """The unchanged lines a fragment carries to prove where it belongs. Editing one of these is
    what makes a patch stop fitting."""
    return [
        line[1:]
        for line in patch_file.read_text().splitlines()
        if line.startswith(" ") and len(line.strip()) > SHORTEST_LINE_WORTH_EDITING
    ]
