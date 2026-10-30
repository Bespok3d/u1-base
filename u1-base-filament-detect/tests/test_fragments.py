"""Every fragment fits exactly the firmware releases the plugin's variant table claims, and the
source it produces still starts and still holds every door open. The source is what a printer runs
and the strictness is what a printer applies, both of them from `firmware_stock`."""

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
KLIPPER_PATH = "klippy/extras/filament_detect.py"

# Snapmaker rewrote this driver in 1.4.0 and every firmware up to 2.1.0 took the same fragment, so
# that one is named as everything between the firmware before the rewrite and the 2.1.0 floor.
FIRMWARE_BEFORE_THE_REWRITE = "1.3.0.168"

# 2.1.0 moved the startup spool check onto a timer. The state it adds in `__init__` sits among the
# lines the parser registry is added beside, so 2.1.0 and every later firmware take their own
# fragment. This is the floor the variant table names for it.
STARTUP_DETECT_TIMER_FLOOR = "2.1.0"
FIRMWARE_WITH_STARTUP_DETECT_TIMER = {
    release
    for release in FIRMWARE_RELEASES
    if firmware_order(release, STARTUP_DETECT_TIMER_FLOOR) >= 0
}

FRAGMENT_FITS = {
    "filament_detect-v1.3.patch": {FIRMWARE_BEFORE_THE_REWRITE},
    "filament_detect-v1.4.246.patch": set(FIRMWARE_RELEASES)
    - {FIRMWARE_BEFORE_THE_REWRITE}
    - FIRMWARE_WITH_STARTUP_DETECT_TIMER,
    "filament_detect-v2.1.patch": FIRMWARE_WITH_STARTUP_DETECT_TIMER,
}

DOORS = (
    "def register_card_protocol_parser(self, card_type, parser):",
    "def channel_count(self):",
    "def set_filament_info(self, channel, info, is_clear=False):",
)

FITTING_PAIRS = [
    (fragment, release)
    for fragment, releases in sorted(FRAGMENT_FITS.items())
    for release in sorted(releases)
]


def patched_source(fragment: str, release: str) -> str:
    patched = apply_fragments(stock_text(KLIPPER_PATH, release), PATCH_DIR, (fragment,))
    assert patched is not None, f"{fragment} does not fit firmware {release}"
    return patched


@pytest.mark.parametrize("fragment", sorted(FRAGMENT_FITS))
def test_fragment_fits_the_releases_the_variant_table_claims(fragment: str) -> None:
    assert fitting_releases(KLIPPER_PATH, PATCH_DIR, (fragment,)) == FRAGMENT_FITS[fragment]


def test_every_firmware_a_printer_runs_is_covered_by_some_fragment() -> None:
    """A firmware no fragment fits is a printer this package is refused on."""
    covered = {release for releases in FRAGMENT_FITS.values() for release in releases}
    assert set(FIRMWARE_RELEASES) - covered == set()


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_patched_source_still_starts(fragment: str, release: str) -> None:
    compile(patched_source(fragment, release), KLIPPER_PATH, "exec")


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_patched_source_carries_every_door(fragment: str, release: str) -> None:
    patched = patched_source(fragment, release)
    assert [door for door in DOORS if door not in patched] == []


@pytest.mark.parametrize("fragment", sorted(FRAGMENT_FITS))
def test_fragment_has_no_carriage_returns(fragment: str) -> None:
    assert "\r" not in (PATCH_DIR / fragment).read_text()
