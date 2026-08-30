# U1 Base: print task config

Opens two doors in the U1's print task settings so other plugins can use them. On its own it
changes nothing: with no plugin holding a door open, the printer behaves exactly as it does today.

> **Version-sensitive.** This patches Klipper source files on the printer. It ships one fragment per
> firmware generation and the daemon picks the one that matches yours.

## What it patches

`klippy/extras/print_task_config.py`, the object that owns the printer's print preferences and the
start-of-print pressure advance reset.

## The doors it opens

| Door | What a plugin does with it |
| --- | --- |
| `suppress_pressure_advance_reset(owner)` | Holds off the start-of-print pressure advance reset while the plugin needs its own value to stand |
| `resume_pressure_advance_reset(owner)` | Lets that hold go |
| `allow_force_preference_param(owner)` | Allows `FORCE=1` on `SET_PRINT_PREFERENCES`, so a preference can be changed while a print is running |
| `disallow_force_preference_param(owner)` | Takes that allowance back |

Each door is a set of owners, not a switch. Several plugins can hold the same door open at once, and
it closes only when the last one lets go, so one plugin uninstalling never pulls the door shut under
another.

## Using it

Install the plugin you actually want; it asks for this one. Klipper restarts and the doors are
there. Nothing to configure.

## Notes

- Patches `/home/lava/klipper/klippy/extras/print_task_config.py`; reverted on uninstall and
  re-applied after an OTA firmware update.
- Snapmaker U1. Fits firmware 1.3.0, 1.4.0 and 1.5.0.
