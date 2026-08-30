"""What a printer in the field is carrying on the day the base layer arrives.

A printer enrolled by any 0.7 beta has its Snapmaker source files patched by the plugins that own
those files today. The base layer takes them over, and the only honest proof that the handover is
safe is one run against what those printers really carry. So the fragments and the instrument order
of the released plugins are vendored here, straight out of their own release tags, which also keeps
this repo gating with no sibling checkout. `field_artifacts/field-artifacts.json` records where each
one came from and its sha256.

The base layer's side is read from the base packages' own manifests and the variant is picked the
way the printer picks it, so this module never restates a table that lives in a manifest.
"""

import json
from pathlib import Path
from typing import NamedTuple

from firmware_stock import KLIPPY_PREFIX, firmware_order

BASE_LAYER_ROOT = Path(__file__).resolve().parent.parent
FIELD_ARTIFACTS = Path(__file__).resolve().parent / "field_artifacts"

# The app releases a printer can have been enrolled by, and the daemon each of them put on it.
# A printer runs the newest daemon it was ever given, so this is the range the migration must
# survive: nobody in it can take the base layer until the daemon has been brought up first.
DAEMON_A_PRINTER_CAME_WITH = {
    "0.7.0-beta": "0.12.20",
    "0.7.1-beta": "0.12.22",
    "0.7.2-beta": "0.12.22",
    "0.7.3-beta": "0.12.23",
    "0.7.4-beta": "0.12.23",
}

BASE_PACKAGE_OWNING = {
    "extras/print_task_config.py": "u1-base-print-task-config",
    "extras/fm175xx_reader.py": "u1-base-fm175xx-reader",
    "extras/filament_detect.py": "u1-base-filament-detect",
    "extras/resonance_tester.py": "u1-base-resonance-tester",
    "toolhead.py": "u1-base-toolhead",
    "extras/shaper_calibrate.py": "u1-base-shaper-calibrate",
}


class Handover(NamedTuple):
    """One Snapmaker source file, the released plugin that patches it on a field printer today, and
    the base package that takes it over."""

    klipper_name: str
    plugin: str
    plugin_version: str
    plugin_fragments: tuple[str, ...]
    base_package: str


def klipper_path(handover: Handover) -> str:
    """Where the file sits in the Snapmaker source tree, and how its stock copy is looked up."""
    return KLIPPY_PREFIX + handover.klipper_name


def vendored_patch_dir(plugin: str, version: str) -> Path:
    """Where this repo keeps the fragments that plugin release really shipped."""
    return FIELD_ARTIFACTS / f"{plugin}-{version}"


def field_patch_dir(handover: Handover) -> Path:
    return vendored_patch_dir(handover.plugin, handover.plugin_version)


def base_patch_dir(handover: Handover) -> Path:
    return BASE_LAYER_ROOT / handover.base_package / "files" / "patches"


def released_plugins() -> list[dict]:
    return list(json.loads((FIELD_ARTIFACTS / "field-artifacts.json").read_text())["releases"])


def base_manifest(handover: Handover) -> dict:
    return dict(json.loads((BASE_LAYER_ROOT / handover.base_package / "manifest.json").read_text()))


def base_fragments(handover: Handover, release: str) -> tuple[str, ...]:
    """The fragments the base package applies on a printer running this Snapmaker source release,
    chosen the way the printer chooses them: entries in manifest order, and inside an entry the
    first variant whose firmware bounds hold. The vendored source is keyed by the same build number
    a printer reports as its own firmware, which is what the variant tables are written in, so the
    release is read straight into the bounds. `fw_min` is an inclusive floor and `fw_max` an
    inclusive ceiling; an entry no variant matches is skipped, exactly as the daemon skips it."""
    owned = [
        entry
        for entry in base_manifest(handover)["install"]["instrument"]
        if entry["name"] == handover.klipper_name
    ]
    chosen = [_variant_diff(entry, release) for entry in owned]
    return tuple(diff.rsplit("/", 1)[-1] for diff in chosen if diff is not None)


def handovers_the_field_holds() -> tuple[Handover, ...]:
    """Every file a released plugin patches today, one record per file per plugin."""
    return tuple(
        _handover(release, klipper_name)
        for release in released_plugins()
        for klipper_name in _files_patched_by(release)
    )


def _files_patched_by(release: dict) -> list[str]:
    """The files the release patches, in the order its manifest first names each one."""
    return list(dict.fromkeys(entry["name"] for entry in release["instrument"]))


def _handover(release: dict, klipper_name: str) -> Handover:
    fragments = tuple(
        entry["fragment"] for entry in release["instrument"] if entry["name"] == klipper_name
    )
    return Handover(
        klipper_name=klipper_name,
        plugin=release["plugin"],
        plugin_version=release["version"],
        plugin_fragments=fragments,
        base_package=BASE_PACKAGE_OWNING[klipper_name],
    )


def _variant_diff(entry: dict, firmware: str) -> str | None:
    applicable = (
        variant
        for variant in entry["variants"]
        if _firmware_bounds_hold(variant.get("when") or {}, firmware)
    )
    chosen = next(applicable, None)
    return None if chosen is None else str(chosen["diff"])


def _firmware_bounds_hold(bounds: dict, firmware: str) -> bool:
    floor_holds = "fw_min" not in bounds or firmware_order(firmware, bounds["fw_min"]) >= 0
    ceiling_holds = "fw_max" not in bounds or firmware_order(firmware, bounds["fw_max"]) <= 0
    return floor_holds and ceiling_holds
