"""Every fragment fits every firmware release the plugin's variant table claims, applied in the
order the manifest lists them, and the source it produces still starts and carries every behaviour
this plugin moved out of the klipper-motion plugin. The source is what a printer runs and the
strictness is what a printer applies, both of them from `firmware_stock`."""

from pathlib import Path

import pytest
from firmware_stock import FIRMWARE_RELEASES, apply_fragments, fitting_releases, stock_text

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = PLUGIN_ROOT / "files" / "patches"
KLIPPER_PATH = "klippy/extras/resonance_tester.py"

FRAGMENT_ORDER = (
    "01_resonance_chip_fix.patch",
    "04a_resonance_sweeping.patch",
    "06_resonance_snapmaker_fix.patch",
)

MOVED_BEHAVIOURS = {
    "an accelerometer other than the stock one can be chosen": (
        "chip = self.printer.lookup_object(chip_name.strip())"
    ),
    "the sweeping vibrations test exists": "class VibrationPulseTestGenerator:",
    "the sweep uses the configured frequency range": (
        "freq_start = self.generator.vibration_generator.min_freq"
    ),
}


def patched_source(release: str) -> str:
    patched = apply_fragments(stock_text(KLIPPER_PATH, release), PATCH_DIR, FRAGMENT_ORDER)
    assert patched is not None, f"the fragment chain does not fit firmware {release}"
    return patched


def test_the_chain_fits_every_firmware_a_printer_runs() -> None:
    """A firmware the chain does not fit is a printer this package is refused on. There is one
    chain here and it covers every firmware, so there is no variant table to disagree with."""
    assert fitting_releases(KLIPPER_PATH, PATCH_DIR, FRAGMENT_ORDER) == set(FIRMWARE_RELEASES)


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


@pytest.mark.parametrize("fragment", FRAGMENT_ORDER)
def test_fragment_has_no_carriage_returns(fragment: str) -> None:
    assert "\r" not in (PATCH_DIR / fragment).read_text()
