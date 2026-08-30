"""Every fragment fits exactly the firmware releases the plugin's variant table claims, and the
source it produces still starts, still holds every door open, and still refuses mid print.

The fit is proved at the printer's own strictness and against every firmware a printer can be
running, not only the one each fragment was written for: a variant covers a firmware floor with no
ceiling, so a newer printer takes the newest fragment regardless. The source a printer runs and the
strictness it applies both come from `tests_support/firmware_stock`.
"""

from pathlib import Path

import pytest
from firmware_stock import FIRMWARE_RELEASES, apply_fragments, fitting_releases, stock_text

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = PLUGIN_ROOT / "files" / "patches"
KLIPPER_PATH = "klippy/extras/print_task_config.py"

FRAGMENT_FITS = {
    "print_task_config-v1.3.patch": {"1.3.0.168"},
    "print_task_config-v1.4.patch": {"1.4.0.246"},
    "print_task_config-v1.4.1.patch": {"1.4.1.6"},
    "print_task_config-v1.6.patch": {"1.5.0.344", "1.5.1.2", "1.5.2.13", "1.6.0.267"},
}

# Snapmaker rewrote the mid print check in 1.4.0 and has not touched it since, so one line stands
# for every release from there on.
PRINT_UNDERWAY_SINCE_1_4 = (
    "        if print_stats is not None and print_stats.state in ['printing', 'paused']"
)

IS_PRINTING_BEFORE_1_4 = "        if is_printing"
FIRMWARE_BEFORE_THE_REWRITE = "1.3.0.168"

MID_PRINT_GUARDS = {
    release: PRINT_UNDERWAY_SINCE_1_4 if release != FIRMWARE_BEFORE_THE_REWRITE
    else IS_PRINTING_BEFORE_1_4
    for release in FIRMWARE_RELEASES
}

DOORS = (
    "def suppress_pressure_advance_reset(self, owner):",
    "def resume_pressure_advance_reset(self, owner):",
    "def allow_force_preference_param(self, owner):",
    "def disallow_force_preference_param(self, owner):",
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


def test_every_firmware_a_printer_runs_is_covered_by_some_fragment() -> None:
    """A firmware no fragment fits is a printer this package is refused on."""
    covered = {release for releases in FRAGMENT_FITS.values() for release in releases}
    assert set(FIRMWARE_RELEASES) - covered == set()


@pytest.mark.parametrize("fragment", sorted(FRAGMENT_FITS))
def test_fragment_fits_the_releases_the_variant_table_claims(fragment: str) -> None:
    assert fitting_releases(KLIPPER_PATH, PATCH_DIR, (fragment,)) == FRAGMENT_FITS[fragment]


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_patched_source_still_starts(fragment: str, release: str) -> None:
    compile(patched_source(fragment, release), KLIPPER_PATH, "exec")


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_patched_source_carries_every_door(fragment: str, release: str) -> None:
    patched = patched_source(fragment, release)
    assert [door for door in DOORS if door not in patched] == []


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_pressure_advance_reset_is_guarded_never_removed(fragment: str, release: str) -> None:
    stock = stock_text(KLIPPER_PATH, release)
    assert patched_source(fragment, release).count("FLOW_RESET_K") == stock.count("FLOW_RESET_K")


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_mid_print_refusal_stands_unless_a_plugin_allows_force(fragment: str, release: str) -> None:
    guard = MID_PRINT_GUARDS[release]
    refusal = f"{guard} and not self._force_preference_honoured(gcmd):"
    assert refusal in patched_source(fragment, release)


@pytest.mark.parametrize("fragment", sorted(FRAGMENT_FITS))
def test_fragment_has_no_carriage_returns(fragment: str) -> None:
    assert "\r" not in (PATCH_DIR / fragment).read_text()


STALE_HUNK = ("@@ -364,3 +381,7 @@\n", "@@ -362,5 +379,9 @@\n \n         if is_clear == False:\n")
NEWEST_RELEASE = FIRMWARE_RELEASES[-1]


def test_the_hunk_that_rolled_the_bench_migration_back_is_not_a_fit(tmp_path: Path) -> None:
    """The packaged fragment once carried this hunk: two context lines the newest firmware no longer
    has. GNU and BSD patch fuzz them away, BusyBox on the printer fails the hunk and the install."""
    fixed, stale = STALE_HUNK
    fragment = "print_task_config-v1.6.patch"
    original = (PATCH_DIR / fragment).read_text(encoding="utf-8")
    assert fixed in original
    (tmp_path / fragment).write_text(original.replace(fixed, stale), encoding="utf-8")
    stock = stock_text(KLIPPER_PATH, NEWEST_RELEASE)
    assert apply_fragments(stock, PATCH_DIR, (fragment,)) is not None
    assert apply_fragments(stock, tmp_path, (fragment,)) is None
