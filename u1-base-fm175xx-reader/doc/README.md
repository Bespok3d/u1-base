# U1 Base: RFID reader

Opens the U1's RFID reader to other plugins. On its own it changes nothing: with no plugin
registered, the reader behaves exactly as it does today.

> **Version-sensitive.** This patches Klipper source files on the printer. It ships one fragment per
> firmware generation and the daemon picks the one that matches yours.

## What it patches

`klippy/extras/fm175xx_reader.py`, the driver for the FM175xx reader behind each filament channel.

## The doors it opens

| Door | What a plugin does with it |
| --- | --- |
| `register_card_type_handler(sak, handler)` | Handles a card the stock firmware recognises but does not read |
| `register_card_handler(claim, reader_fn)` | Claims a card the stock read failed on, and reads it instead |
| `register_card_session_hook(owner, session_hook)` | Runs before the card handlers and is told the channel; several plugins can hold it at once |
| `unregister_card_session_hook(owner)` | Lets that plugin's hook go; the others keep theirs |
| `read_nfc_type2_pages(start_page, count)` | Reads NTAG pages through the printer's own reader |
| `read_mifare_classic(key_type, sector, key, uid, blocks)` | Reads MIFARE Classic blocks |
| `mifare_authenticate(key_type, sector, key, uid)` | Authenticates a MIFARE Classic sector |
| `transceive(send_bytes, recv_max, ...)` | Sends a raw command to the card |
| `reactivate_card()` | Re-selects the card after a failed exchange |
| `selected_card_uid()`, `selected_card_sak()`, `selected_card_atqa()` | Reads what the reader found |

`session_hook(reader, channel)` runs in the reader thread, before the card handlers, on each read
attempt of a card that reaches a plugin handler (a card type handler or a claim). It is once per read
attempt, not once per card: the reader retries a card whose handler did not return OK, and the hook
runs again on each attempt, so make the hook idempotent across attempts. On the card type path the
card is selected. On the claim path the stock MIFARE Classic read has just failed and the card is back
to idle, so call `reactivate_card()` before talking to the card. The reader thread is not the Klipper
reactor thread: a hook must not touch gcode or reactor objects directly, and must not block for long.
A hook that raises is logged and skipped; the handlers still run. Registering the same owner again
replaces that owner's hook. A card the stock firmware reads itself never reaches it.

The claim door is a list of handlers, not a switch. Several plugins can offer to claim a card at
once, and with none registered the reader takes the stock path unchanged.

## Using it

Install the plugin you actually want; it asks for this one. Klipper restarts and the doors are
there. Nothing to configure.

## Notes

- Patches `/home/lava/klipper/klippy/extras/fm175xx_reader.py`; reverted on uninstall and re-applied
  after an OTA firmware update.
- Snapmaker U1. Fits firmware 1.3.0 to 1.6.0, 2.0.0, and the 2.1.0 beta (build 157).
- See `ATTRIBUTIONS.md`: part of this patch comes from the Extended Firmware overlay.
