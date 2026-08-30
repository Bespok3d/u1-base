# U1 Base: shaper calibrate

Updates the U1's input shaper calculation so very low frequency noise in a measurement no longer
skews the result.

> **Version-sensitive.** This patches Klipper source files on the printer. It ships one fragment per
> upstream change and the daemon applies them in order.

## What it patches

`klippy/extras/shaper_calibrate.py`, the object that turns a resonance measurement into a recommended input shaper.

## What it changes

| Change | What you get |
| --- | --- |
| Low frequency damping | Frequencies below the useful range are damped before a shaper is chosen, so calibration picks one that matches how the printer really moves |

## Using it

Install the plugin you actually want; it asks for this one. Klipper restarts and the newer code is
in. Nothing to configure.

## Notes

- Patches `/home/lava/klipper/klippy/extras/shaper_calibrate.py`; reverted on uninstall and re-applied after an OTA
  firmware update.
- These fragments used to be applied by the `klipper-motion` plugin. They live here now, so a plugin
  that needs this file asks for this service instead of patching it itself.
- Snapmaker U1. Fits firmware 1.3.0, 1.4.0 and 1.5.0.
