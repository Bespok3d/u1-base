"""Every fragment fits exactly the firmware releases the plugin's variant table claims, and the
source it produces still starts and still holds every door open. The source is what a printer runs
and the strictness is what a printer applies, both of them from `firmware_stock`."""

from pathlib import Path

import pytest
from firmware_stock import FIRMWARE_RELEASES, apply_fragments, fitting_releases, stock_text

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = PLUGIN_ROOT / "files" / "patches"
KLIPPER_PATH = "klippy/extras/filament_detect.py"

# Snapmaker rewrote this driver in 1.4.0 and every firmware since has taken the same
# fragment, so the newer one is named as everything but the firmware that came before it.
FIRMWARE_BEFORE_THE_REWRITE = "1.3.0.168"

FRAGMENT_FITS = {
    "filament_detect-v1.3.patch": {FIRMWARE_BEFORE_THE_REWRITE},
    "filament_detect-v1.4.246.patch": set(FIRMWARE_RELEASES) - {FIRMWARE_BEFORE_THE_REWRITE},
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
