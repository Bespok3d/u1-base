# U1 Base: filament detect

Opens the U1's filament detection to other plugins. On its own it changes nothing: with no plugin
registered, detection behaves exactly as it does today.

> **Version-sensitive.** This patches Klipper source files on the printer. It ships one fragment per
> firmware generation and the daemon picks the one that matches yours.

## What it patches

`klippy/extras/filament_detect.py`, the object that turns a card the reader found into the filament
details the printer shows for that channel.

## The doors it opens

| Door | What a plugin does with it |
| --- | --- |
| `register_card_protocol_parser(card_type, parser)` | Reads a spool tag whose format the stock firmware does not know |
| `channel_count` | Asks how many filament channels this printer has |
| `set_filament_info(channel, info, is_clear=False)` | Fills in, or clears, the filament details for one channel |

The parser door is a registry keyed by card type, not a switch. A card type nobody registered takes
the stock path unchanged.

## Using it

Install the plugin you actually want; it asks for this one. Klipper restarts and the doors are
there. Nothing to configure.

## Notes

- Patches `/home/lava/klipper/klippy/extras/filament_detect.py`; reverted on uninstall and
  re-applied after an OTA firmware update.
- Snapmaker U1. Fits firmware 1.3.0, 1.4.0 and 1.5.0.
