"""Every fragment fits exactly the firmware releases the plugin's variant table claims, and the
source it produces still starts, still holds every door open, and still takes the stock path when
no plugin has registered. The source is what a printer runs and the strictness is what a printer
applies, both of them from `firmware_stock`."""

import sys
import time
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
KLIPPER_PATH = "klippy/extras/fm175xx_reader.py"

# Snapmaker rewrote this driver in 1.4.0 and every firmware up to 2.1.0 took the same fragment, so
# that one is named as everything between the firmware before the rewrite and the 2.1.0 floor.
FIRMWARE_BEFORE_THE_REWRITE = "1.3.0.168"

# 2.1.0 added a fail-fast first scan to the driver. The flag it sets in `__init__` sits among the
# lines the door registries are added beside, so 2.1.0 and every later firmware take their own
# fragment. This is the floor the variant table names for it.
FIRST_SCAN_FAIL_FAST_FLOOR = "2.1.0"
FIRMWARE_WITH_FIRST_SCAN_FAIL_FAST = {
    release
    for release in FIRMWARE_RELEASES
    if firmware_order(release, FIRST_SCAN_FAIL_FAST_FLOOR) >= 0
}

FRAGMENT_FITS = {
    "fm175xx_reader-v1.3.patch": {FIRMWARE_BEFORE_THE_REWRITE},
    "fm175xx_reader-v1.4.246.patch": set(FIRMWARE_RELEASES)
    - {FIRMWARE_BEFORE_THE_REWRITE}
    - FIRMWARE_WITH_FIRST_SCAN_FAIL_FAST,
    "fm175xx_reader-v2.1.patch": FIRMWARE_WITH_FIRST_SCAN_FAIL_FAST,
}

DOORS = (
    "def register_card_type_handler(self, sak, handler):",
    "def register_card_handler(self, claim, reader_fn):",
    "def read_nfc_type2_pages(self, start_page, count):",
    "def read_mifare_classic(self, key_type, sector, key, uid, blocks):",
    "def mifare_authenticate(self, key_type, sector, key, uid):",
    "def reactivate_card(self):",
    "def selected_card_uid(self):",
    "def selected_card_sak(self):",
    "def selected_card_atqa(self):",
    "def register_card_session_hook(self, owner, session_hook):",
    "def unregister_card_session_hook(self, owner):",
)

CARD_CHANNEL = 2
MIFARE_CLASSIC_SAK = 0x08
PLUGIN_HANDLED_SAK = 0x00
CARD_UID = [0xDE, 0xAD, 0xBE, 0xEF]

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


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_card_claim_runs_only_once_a_plugin_registered(fragment: str, release: str) -> None:
    patched = patched_source(fragment, release)
    assert patched.index("if self._card_claim_handlers:") < patched.index(
        "claim = self._dispatch_card_claim("
    )


@pytest.mark.parametrize("fragment", sorted(FRAGMENT_FITS))
def test_fragment_has_no_carriage_returns(fragment: str) -> None:
    assert "\r" not in (PATCH_DIR / fragment).read_text()


class StopSignal:
    """Stands in for the reader's stop event: never sleeps, and stops the loop once it is set."""

    def __init__(self) -> None:
        self.stopped = False

    def set(self) -> None:
        self.stopped = True

    def is_set(self) -> bool:
        return self.stopped

    def wait(self, timeout: float) -> bool:
        return self.stopped


class MifareReadFailure:
    """What the stock Mifare Classic read returns when the card cannot be read."""

    err_code = 1
    out_param = None


class MifareReadSuccess:
    """What the stock Mifare Classic read returns when the card is read."""

    err_code = 0
    out_param = [0] * 1024


class ReaderWithOneCard:
    """The patched reader, loaded without the printer's hardware, with one activated card of a
    given SAK waiting on `CARD_CHANNEL`. The reader loop is the real one; only the calls that talk
    to the chip are replaced. Firmware before 1.4.0 stops its loop on a shutdown flag and the later
    ones on a stop event, so both are set up. `reports` collects what the loop tells Klipper about
    the card, as (channel, result)."""

    MANGLED = "_FM175XXReader__"

    def __init__(self, patched: str, monkeypatch: pytest.MonkeyPatch, card_sak: int) -> None:
        monkeypatch.setattr(time, "sleep", lambda _seconds: None)
        for hardware_module in ("spidev", "gpiod"):
            monkeypatch.setitem(sys.modules, hardware_module, types.ModuleType(hardware_module))
        namespace: dict[str, Any] = {}
        exec(compile(patched, KLIPPER_PATH, "exec"), namespace)  # noqa: S102
        self.card_sak = card_sak
        self.stop_signal = StopSignal()
        self.picc = namespace["Fm175xxPiccMetaData"]()
        self.reports: list[tuple[int, int]] = []
        self.ok = namespace["FM175XX_OK"]
        self.reader: Any = object.__new__(namespace["FM175XXReader"])
        self._attach_chip_stand_ins(namespace["FM175XX_SELF_TEST_STAGE_STOP"])

    def _attach_chip_stand_ins(self, idle_self_test_stage: int) -> None:
        for name, value in {
            "stop_event": self.stop_signal,
            "need_to_shutdown": False,
            "picc_a": self.picc,
            "self_test_stage": idle_self_test_stage,
            "card_info_read_flag": 1 << CARD_CHANNEL,
            "card_info_clear_flag": 0,
            "card_info_deal_cb": self._report_card,
            "reader_a_activate": self._activate_the_card,
            "reader_a_m1_read_all_data": lambda *_: MifareReadFailure(),
            "select_fm175xx_obj": lambda _: None,
            "select_channel": lambda _: None,
            "hard_reset": lambda: None,
            "register_read": lambda _: 0,
            "reader_a_init": lambda: None,
            "reader_a_halt": lambda: None,
            "set_carrier_wave": lambda _: None,
        }.items():
            setattr(self.reader, self.MANGLED + name, value)
        self.reader._first_scan_fail_fast = False
        self.reader._hkdf_create_key = lambda *_: b""
        self.reader._card_type_handlers = {}
        self.reader._card_claim_handlers = []
        self.reader._card_session_hooks = {}

    def _activate_the_card(self) -> int:
        self.picc.SAK[0] = self.card_sak
        self.picc.UID[0:4] = CARD_UID
        return int(self.ok)

    def _report_card(self, channel: int, op: int, result: int, card_type: int, data: Any) -> None:
        self.reports.append((channel, result))
        self.stop_signal.set()
        setattr(self.reader, self.MANGLED + "need_to_shutdown", True)

    def run_loop(self) -> None:
        getattr(self.reader, self.MANGLED + "bg_thread")()


def a_handler_that_notes_itself(
    order: list[Any], ok: int
) -> Callable[[Any], tuple[int, list[int], int]]:
    def handler(_reader: Any) -> tuple[int, list[int], int]:
        order.append("handler")
        return 0, [], ok

    return handler


def a_hook_that_notes_itself(
    order: list[Any], note: str | None = None
) -> Callable[[Any, int], None]:
    def session_hook(_reader: Any, channel: int) -> None:
        order.append(note if note else ("hook", channel))

    return session_hook


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_card_session_hook_runs_before_the_card_type_handler_with_its_channel(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    order: list[Any] = []
    card.reader.register_card_type_handler(
        PLUGIN_HANDLED_SAK, a_handler_that_notes_itself(order, card.ok)
    )
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order))
    card.run_loop()
    assert order == [("hook", CARD_CHANNEL), "handler"]


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_card_session_hook_runs_before_the_card_claim_with_its_channel(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, MIFARE_CLASSIC_SAK)
    order: list[Any] = []

    def decline_the_card(_reader: Any) -> bool:
        order.append("claim")
        return False

    card.reader.register_card_handler(decline_the_card, lambda _reader: None)
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order))
    card.run_loop()
    assert order == [("hook", CARD_CHANNEL), "claim"]


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_a_raising_session_hook_does_not_stop_the_handler(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    order: list[Any] = []

    def hook_that_fails(_reader: Any, _channel: int) -> None:
        raise RuntimeError("hook went wrong")

    card.reader.register_card_session_hook("broken", hook_that_fails)
    card.reader.register_card_session_hook(
        "working", a_hook_that_notes_itself(order, "working hook")
    )
    card.reader.register_card_type_handler(
        PLUGIN_HANDLED_SAK, a_handler_that_notes_itself(order, card.ok)
    )
    card.run_loop()
    assert order == ["working hook", "handler"]
    assert card.reports == [(CARD_CHANNEL, card.ok)]


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_registering_an_owner_twice_keeps_one_hook(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    order: list[Any] = []
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order, "first"))
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order, "second"))
    card.reader.register_card_type_handler(
        PLUGIN_HANDLED_SAK, a_handler_that_notes_itself([], card.ok)
    )
    card.run_loop()
    assert order == ["second"]


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_unregistering_an_unknown_owner_is_harmless(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    order: list[Any] = []
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order, "hook"))
    card.reader.unregister_card_session_hook("nobody")
    card.reader.register_card_type_handler(
        PLUGIN_HANDLED_SAK, a_handler_that_notes_itself([], card.ok)
    )
    card.run_loop()
    assert order == ["hook"]


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_an_unregistered_owner_no_longer_runs(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    order: list[Any] = []
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order, "hook"))
    card.reader.unregister_card_session_hook("spoolkid")
    card.reader.register_card_type_handler(
        PLUGIN_HANDLED_SAK, a_handler_that_notes_itself([], card.ok)
    )
    card.run_loop()
    assert order == []


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_with_no_session_hook_a_card_handler_runs_as_stock(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    order: list[Any] = []
    card.reader.register_card_type_handler(
        PLUGIN_HANDLED_SAK, a_handler_that_notes_itself(order, card.ok)
    )
    card.run_loop()
    assert order == ["handler"]
    assert card.reports == [(CARD_CHANNEL, card.ok)]


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_the_session_hook_registry_starts_empty(fragment: str, release: str) -> None:
    assert "self._card_session_hooks = {}" in patched_source(fragment, release)


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_session_hook_runs_on_each_read_attempt_of_a_card_whose_handler_is_not_ok(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    hook_calls: list[Any] = []
    handler_calls: list[Any] = []

    def handler_that_is_not_ok(_reader: Any) -> tuple[int, list[int], int]:
        handler_calls.append("handler")
        if len(handler_calls) >= 3:
            card.stop_signal.set()
        return 0, [], card.ok + 1

    card.reader.register_card_type_handler(PLUGIN_HANDLED_SAK, handler_that_is_not_ok)
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(hook_calls))
    card.run_loop()
    assert len(hook_calls) == len(handler_calls)
    assert len(hook_calls) > 1


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_session_hook_never_runs_for_a_card_the_stock_read_succeeds_on(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, MIFARE_CLASSIC_SAK)

    def read_the_card(*_arguments: Any) -> MifareReadSuccess:
        card.stop_signal.set()
        setattr(card.reader, card.MANGLED + "need_to_shutdown", True)
        return MifareReadSuccess()

    setattr(card.reader, card.MANGLED + "reader_a_m1_read_all_data", read_the_card)
    order: list[Any] = []
    card.reader.register_card_handler(lambda _reader: True, lambda _reader: None)
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order))
    card.run_loop()
    assert order == []


@pytest.mark.parametrize(("fragment", "release"), FITTING_PAIRS)
def test_session_hook_never_runs_for_a_card_no_plugin_handler_wants(
    fragment: str, release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ReaderWithOneCard(patched_source(fragment, release), monkeypatch, PLUGIN_HANDLED_SAK)
    order: list[Any] = []
    card.reader.register_card_session_hook("spoolkid", a_hook_that_notes_itself(order))
    card.run_loop()
    assert order == []
