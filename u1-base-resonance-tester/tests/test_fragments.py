"""Every fragment chain fits exactly the firmware releases the plugin's variant table gives it,
applied in the order the manifest lists the fragments, and the source it produces still starts and
carries every behaviour this plugin moved out of the klipper-motion plugin. The source is what a
printer runs and the strictness is what a printer applies, both of them from `firmware_stock`."""

import json
from pathlib import Path

import pytest
from firmware_stock import (
    FIRMWARE_RELEASES,
    apply_fragments,
    firmware_order,
    fitting_releases,
    stock_text,
)

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = PLUGIN_ROOT / "files" / "patches"
KLIPPER_PATH = "klippy/extras/resonance_tester.py"

# 2.1.0 rewrote the accelerometer lookup and resolves the chips at the start of `_run_test`, so
# 2.1.0 and every later firmware take their own chain. This is the floor the variant table names.
OWN_CHIP_LOOKUP_FLOOR = "2.1.0"
FIRMWARE_WITH_OWN_CHIP_LOOKUP = frozenset(
    release
    for release in FIRMWARE_RELEASES
    if firmware_order(release, OWN_CHIP_LOOKUP_FLOOR) >= 0
)
FIRMWARE_WITH_STOCK_CHIP_LOOKUP = frozenset(FIRMWARE_RELEASES) - FIRMWARE_WITH_OWN_CHIP_LOOKUP

CHAIN_FOR_STOCK_CHIP_LOOKUP = (
    "01_resonance_chip_fix.patch",
    "04a_resonance_sweeping.patch",
    "06_resonance_snapmaker_fix.patch",
)
CHAIN_FOR_OWN_CHIP_LOOKUP = (
    "01_resonance_chip_fix-v2.1.patch",
    "04a_resonance_sweeping-v2.1.patch",
    "06_resonance_snapmaker_fix.patch",
)
CHAIN_FITS: dict[tuple[str, ...], frozenset[str]] = {
    CHAIN_FOR_STOCK_CHIP_LOOKUP: FIRMWARE_WITH_STOCK_CHIP_LOOKUP,
    CHAIN_FOR_OWN_CHIP_LOOKUP: FIRMWARE_WITH_OWN_CHIP_LOOKUP,
}

# What the plugin adds on every firmware.
MOVED_BEHAVIOURS = {
    "the acceleration per hertz can be set from the command": (
        'self.test_accel_per_hz = gcmd.get_float("ACCEL_PER_HZ",'
    ),
    "the sweeping vibrations test exists": "class VibrationPulseTestGenerator:",
    "the sweep uses the configured frequency range": (
        "freq_start = self.generator.vibration_generator.min_freq"
    ),
}

# Before 2.1.0 the plugin also lets a chip other than the stock one be chosen. From 2.1.0
# Snapmaker's own lookup does that, by exact name first, so the plugin leaves it alone.
UPSTREAM_CHIP_LOOKUP = "chip = self.printer.lookup_object(chip_name.strip())"
SNAPMAKER_CHIP_LOOKUP = "lookup_names = [chip_name]"

ALL_FRAGMENTS = sorted({fragment for chain in CHAIN_FITS for fragment in chain})

# The sweeping vibrations test calls into another Snapmaker file that a sibling base package owns.
# klipper-motion applied the whole upstream series at once, so the call always had a target; split
# into one package per file, it only has one when this package requires the owner. Without it the
# first sweep move fails with AttributeError and shuts the printer down.
CALLS_INTO_SIBLING_PACKAGES = {
    "toolhead.limit_next_junction_speed(": "u1-base-toolhead",
}

# The sweeping vibrations test is upstream Klipper commit 6723, which also changed
# shaper_calibrate.py: the sweep's own slow motion puts energy below MIN_FREQ, and that part damps
# it instead of letting it skew which shaper SHAPER_CALIBRATE picks. Nothing calls into it, so
# leaving it out cannot crash, but the results would be scored by maths the sweep was not written
# for.
SIBLING_PACKAGES_THE_SWEEP_IS_SCORED_BY = frozenset({"u1-base-shaper-calibrate"})


def chain_for(release: str) -> tuple[str, ...]:
    return next(chain for chain, releases in CHAIN_FITS.items() if release in releases)


def patched_source(release: str) -> str:
    chain = chain_for(release)
    patched = apply_fragments(stock_text(KLIPPER_PATH, release), PATCH_DIR, chain)
    assert patched is not None, f"the fragment chain does not fit firmware {release}"
    return patched


@pytest.mark.parametrize("chain", sorted(CHAIN_FITS))
def test_each_chain_fits_the_releases_the_variant_table_gives_it(chain: tuple[str, ...]) -> None:
    assert fitting_releases(KLIPPER_PATH, PATCH_DIR, chain) == CHAIN_FITS[chain]


def test_every_firmware_a_printer_runs_is_covered_by_some_chain() -> None:
    """A firmware no chain fits is a printer this package is refused on."""
    covered = {release for releases in CHAIN_FITS.values() for release in releases}
    assert set(FIRMWARE_RELEASES) - covered == set()


@pytest.mark.parametrize("release", sorted(FIRMWARE_RELEASES))
def test_patched_source_still_starts(release: str) -> None:
    compile(patched_source(release), KLIPPER_PATH, "exec")


@pytest.mark.parametrize("release", sorted(FIRMWARE_RELEASES))
def test_patched_source_carries_every_moved_behaviour(release: str) -> None:
    patched = patched_source(release)
    assert [marker for marker in MOVED_BEHAVIOURS.values() if marker not in patched] == []


@pytest.mark.parametrize("release", sorted(FIRMWARE_RELEASES))
def test_stock_source_carries_none_of_them(release: str) -> None:
    stock = stock_text(KLIPPER_PATH, release)
    assert [marker for marker in MOVED_BEHAVIOURS.values() if marker in stock] == []


@pytest.mark.parametrize("release", sorted(FIRMWARE_WITH_STOCK_CHIP_LOOKUP))
def test_before_2_1_the_plugin_brings_the_upstream_chip_lookup(release: str) -> None:
    assert UPSTREAM_CHIP_LOOKUP in patched_source(release)


@pytest.mark.parametrize("release", sorted(FIRMWARE_WITH_OWN_CHIP_LOOKUP))
def test_from_2_1_the_plugin_keeps_snapmakers_own_chip_lookup(release: str) -> None:
    patched = patched_source(release)
    assert SNAPMAKER_CHIP_LOOKUP in patched
    assert UPSTREAM_CHIP_LOOKUP not in patched


@pytest.mark.parametrize("fragment", ALL_FRAGMENTS)
def test_fragment_has_no_carriage_returns(fragment: str) -> None:
    assert "\r" not in (PATCH_DIR / fragment).read_text()


def required_services() -> set[str]:
    manifest = json.loads((PLUGIN_ROOT / "manifest.json").read_text())
    return {requirement["service"] for requirement in manifest["require"]}


@pytest.mark.parametrize("release", sorted(FIRMWARE_RELEASES))
def test_every_sibling_package_the_patched_source_calls_into_is_required(release: str) -> None:
    patched = patched_source(release)
    required = required_services()
    called = {
        owner for call, owner in CALLS_INTO_SIBLING_PACKAGES.items() if call in patched
    }
    assert called - required == set()


def test_the_package_that_scores_the_sweep_is_required() -> None:
    assert SIBLING_PACKAGES_THE_SWEEP_IS_SCORED_BY - required_services() == set()
