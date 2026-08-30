# U1 Base: toolhead

Brings the U1's motion planner up to date with newer Klipper code, so fast moves stay accurate
and a little quieter.

> **Version-sensitive.** This patches Klipper source files on the printer. It ships one fragment per
> upstream change and the daemon applies them in order.

## What it patches

`klippy/toolhead.py`, the object that plans every move the printer makes.

## What it changes

| Change | What you get |
| --- | --- |
| Centripetal force from `delta_v2` | The same cornering limit, computed the newer way |
| Newer junction speed maths | Fast direction changes stay accurate |
| `limit_next_junction_speed` | A move can hold the speed down going into the next corner |
| Shorter lookahead flush | The planner reacts sooner, trimming small stutters on detailed models |

## Using it

Install the plugin you actually want; it asks for this one. Klipper restarts and the newer code is
in. Nothing to configure.

## Notes

- Patches `/home/lava/klipper/klippy/toolhead.py`; reverted on uninstall and re-applied after an OTA
  firmware update.
- These fragments used to be applied by the `klipper-motion` plugin. They live here now, so a plugin
  that needs this file asks for this service instead of patching it itself.
- Snapmaker U1. Fits firmware 1.3.0, 1.4.0 and 1.5.0.
