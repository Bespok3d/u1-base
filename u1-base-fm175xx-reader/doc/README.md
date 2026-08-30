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
| `read_nfc_type2_pages(start_page, count)` | Reads NTAG pages through the printer's own reader |
| `read_mifare_classic(key_type, sector, key, uid, blocks)` | Reads MIFARE Classic blocks |
| `mifare_authenticate(key_type, sector, key, uid)` | Authenticates a MIFARE Classic sector |
| `transceive(send_bytes, recv_max, ...)` | Sends a raw command to the card |
| `reactivate_card()` | Re-selects the card after a failed exchange |
| `selected_card_uid()`, `selected_card_sak()`, `selected_card_atqa()` | Reads what the reader found |

The claim door is a list of handlers, not a switch. Several plugins can offer to claim a card at
once, and with none registered the reader takes the stock path unchanged.

## Using it

Install the plugin you actually want; it asks for this one. Klipper restarts and the doors are
there. Nothing to configure.

## Notes

- Patches `/home/lava/klipper/klippy/extras/fm175xx_reader.py`; reverted on uninstall and re-applied
  after an OTA firmware update.
- Snapmaker U1. Fits firmware 1.3.0, 1.4.0 and 1.5.0.
- See `ATTRIBUTIONS.md`: part of this patch comes from the Extended Firmware overlay.
