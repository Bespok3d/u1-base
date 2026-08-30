"""What the base layer release does to a printer that is already out there.

Every printer the 0.7.0-beta to 0.7.4-beta install base can be is rebuilt here out of the
Snapmaker source it runs and the fragments the patching plugins really released, and the migration
is run on it: the old plugin hands the file back, the base layer keeps what came back as the stock
original, the base layer patches that. The one thing the migration must never do is keep a copy
that is not the file Snapmaker shipped, because that copy is the user's only way back, so a file
that cannot be proved back to stock has to be refused instead of adopted.
"""

from hashlib import sha256
from pathlib import Path

import pytest
from field_printers import (
    BASE_PACKAGE_OWNING,
    DAEMON_A_PRINTER_CAME_WITH,
    Handover,
    base_fragments,
    base_manifest,
    field_patch_dir,
    handovers_the_field_holds,
    klipper_path,
    released_plugins,
    vendored_patch_dir,
)
from firmware_stock import (
    FIRMWARE_RELEASES,
    firmware_order,
    reverse_fragments,
    stock_text,
)
from migration_steps import (
    base_output,
    hand_edited,
    live_file,
    printers_the_field_can_hold,
    recovered_stock,
)

EVERY_FIRMWARE_A_PRINTER_RUNS = frozenset(FIRMWARE_RELEASES)

# The rfid and print-preference fragments were written against 1.4.246 and never fitted anything
# older, so no printer on 1.3.0 is running them and there is nothing to migrate there.
FIRMWARE_OLDER_THAN_THOSE_PLUGINS_EVER_FITTED = frozenset({"1.3.0.168"})

FILES_THE_MOTION_PLUGIN_PATCHES = frozenset(
    {"extras/resonance_tester.py", "toolhead.py", "extras/shaper_calibrate.py"}
)

PRINTERS_THE_FIELD_HOLDS = {
    klipper_name: EVERY_FIRMWARE_A_PRINTER_RUNS
    if klipper_name in FILES_THE_MOTION_PLUGIN_PATCHES
    else EVERY_FIRMWARE_A_PRINTER_RUNS - FIRMWARE_OLDER_THAN_THOSE_PLUGINS_EVER_FITTED
    for klipper_name in BASE_PACKAGE_OWNING
}

# The base layer opens doors the old plugin's patch never opened in these two files, so the printer
# ends the migration carrying more than it carried. Everywhere else the migration is invisible: the
# file the base layer writes is the file the plugin had already produced.
FILES_THE_BASE_LAYER_OPENS_MORE_DOORS_IN = frozenset(
    {"extras/print_task_config.py", "extras/fm175xx_reader.py"}
)

PRINTERS = printers_the_field_can_hold()
PRINTER_NAMES = [f"{handover.klipper_name} on firmware {release}" for handover, release in PRINTERS]

# Every base package against every Snapmaker source a printer can run. This is the pairing the
# variant tables exist to answer, and the one nothing checked before a package reached a printer
# carrying no fragment that fitted it.
BASE_PACKAGES_A_PRINTER_MEETS = tuple(
    (handover, release) for handover in handovers_the_field_holds() for release in FIRMWARE_RELEASES
)
BASE_PACKAGE_NAMES = [
    f"{handover.base_package} on firmware {release}"
    for handover, release in BASE_PACKAGES_A_PRINTER_MEETS
]

RELEASES = released_plugins()
RELEASE_NAMES = [f"{release['plugin']} {release['version']}" for release in RELEASES]


def file_a_printer_runs(handover: Handover, release: str) -> str:
    live = live_file(handover, release)
    assert live is not None, f"{handover.plugin} does not fit {klipper_path(handover)} on {release}"
    return live


def stock_the_printer_gets_back(handover: Handover, release: str) -> str:
    recovered = recovered_stock(handover, release)
    assert recovered is not None, f"{handover.plugin} cannot hand back {klipper_path(handover)}"
    return recovered


def file_the_migration_leaves(handover: Handover, release: str) -> str:
    migrated = base_output(stock_the_printer_gets_back(handover, release), handover, release)
    assert migrated is not None, f"{handover.base_package} does not fit the stock handed back"
    return migrated


@pytest.mark.parametrize("release", RELEASES, ids=RELEASE_NAMES)
def test_the_vendored_fragments_are_the_bytes_the_plugin_released(release: dict) -> None:
    """A migration proved against a fragment nobody shipped proves nothing about a real printer."""
    vendored = vendored_patch_dir(release["plugin"], release["version"])
    on_disk = {patch.name: _digest(patch) for patch in vendored.glob("*.patch")}
    assert on_disk == release["sha256"]


@pytest.mark.parametrize("release", RELEASES, ids=RELEASE_NAMES)
def test_every_fragment_the_released_manifest_names_is_vendored(release: dict) -> None:
    named = {entry["fragment"] for entry in release["instrument"]}
    assert sorted(named - set(release["sha256"])) == []


def test_every_file_the_base_layer_takes_over_is_patched_in_the_field_today() -> None:
    """A file the base layer takes over that nobody patches today needs no migration, and a file
    patched today that the base layer does not take over is a printer left behind."""
    assert {handover.klipper_name for handover in handovers_the_field_holds()} == set(
        BASE_PACKAGE_OWNING
    )


def test_the_printers_this_suite_covers_are_the_printers_the_field_can_hold() -> None:
    covered = {(handover.klipper_name, release) for handover, release in PRINTERS}
    recorded = {
        (klipper_name, release)
        for klipper_name, releases in PRINTERS_THE_FIELD_HOLDS.items()
        for release in releases
    }
    assert covered == recorded


@pytest.mark.parametrize("handover, release", PRINTERS, ids=PRINTER_NAMES)
def test_the_old_plugin_hands_back_the_file_snapmaker_shipped(
    handover: Handover, release: str
) -> None:
    """Byte for byte, not close enough. What comes back is the printer's only way home."""
    assert stock_the_printer_gets_back(handover, release) == stock_text(
        klipper_path(handover), release
    )


@pytest.mark.parametrize("handover, release", PRINTERS, ids=PRINTER_NAMES)
def test_the_file_the_migration_leaves_still_starts(handover: Handover, release: str) -> None:
    migrated = file_the_migration_leaves(handover, release)
    compile(migrated, klipper_path(handover), "exec")


@pytest.mark.parametrize("handover, release", PRINTERS, ids=PRINTER_NAMES)
def test_the_base_layer_does_not_fit_the_file_before_it_is_handed_back(
    handover: Handover, release: str
) -> None:
    """Why the handing back has to come first: on the file the printer is running right now, the
    base layer's own patch does not fit, so a migration that skipped the handover would refuse."""
    assert base_output(file_a_printer_runs(handover, release), handover, release) is None


@pytest.mark.parametrize("handover, release", PRINTERS, ids=PRINTER_NAMES)
def test_handing_the_file_back_twice_is_refused(handover: Handover, release: str) -> None:
    """A migration that runs again on a printer it already migrated cannot cut the plugin's changes
    out of a file that no longer has them."""
    stock = stock_the_printer_gets_back(handover, release)
    assert reverse_fragments(stock, field_patch_dir(handover), handover.plugin_fragments) is None


@pytest.mark.parametrize("handover, release", PRINTERS, ids=PRINTER_NAMES)
def test_a_file_the_user_edited_is_refused_rather_than_kept_as_stock(
    handover: Handover, release: str
) -> None:
    """A user who hand-edited the file on the printer gets a refusal, never a wrong original kept
    as the way back."""
    edited = hand_edited(file_a_printer_runs(handover, release), handover)
    assert reverse_fragments(edited, field_patch_dir(handover), handover.plugin_fragments) is None


@pytest.mark.parametrize("handover, release", PRINTERS, ids=PRINTER_NAMES)
def test_what_the_printer_does_after_the_migration(handover: Handover, release: str) -> None:
    """Four of the six files come out of the migration byte-identical to what the plugin had already
    put there, so those printers keep behaving exactly as they did."""
    migrated = file_the_migration_leaves(handover, release)
    printer_changed = migrated != file_a_printer_runs(handover, release)
    assert printer_changed == (handover.klipper_name in FILES_THE_BASE_LAYER_OPENS_MORE_DOORS_IN)


@pytest.mark.parametrize("app_release", sorted(DAEMON_A_PRINTER_CAME_WITH), ids=str)
def test_every_printer_in_the_install_base_needs_its_daemon_updated_first(app_release: str) -> None:
    """Nobody in the 0.7.0-beta to 0.7.4-beta install base can take the base layer on the daemon
    they have, so the app has to carry the daemon update into the same batch or the user is told no
    with nothing changed."""
    daemon = DAEMON_A_PRINTER_CAME_WITH[app_release]
    already_high_enough = [
        package for package, floor in _daemon_floors().items() if firmware_order(daemon, floor) >= 0
    ]
    assert already_high_enough == []


def _daemon_floors() -> dict[str, str]:
    return {
        handover.base_package: base_manifest(handover)["min_daemon_version"]
        for handover in handovers_the_field_holds()
    }


def _digest(patch: Path) -> str:
    return sha256(patch.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("handover", "release"), BASE_PACKAGES_A_PRINTER_MEETS, ids=BASE_PACKAGE_NAMES
)
def test_the_fragment_the_table_picks_fits_the_printer_it_picks_it_for(
    handover: Handover, release: str
) -> None:
    """The check that was missing when a base package reached a real printer carrying nothing that
    fitted it. The variant table is read exactly as the printer reads it, and whatever it hands back
    is then applied to Snapmaker's own source for that printer. A table that hands back nothing is a
    package silently skipped on that printer, so an empty answer fails here too."""
    picked = base_fragments(handover, release)
    assert picked, f"{handover.base_package} carries nothing for a printer on firmware {release}"
    stock = stock_text(klipper_path(handover), release)
    assert base_output(stock, handover, release) is not None, (
        f"{handover.base_package} picks {list(picked)} on firmware {release} "
        "and they do not fit the source that printer runs"
    )
