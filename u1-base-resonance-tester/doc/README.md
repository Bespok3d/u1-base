# U1 Base: resonance tester

Brings the U1's resonance measurement up to date with newer Klipper code, so input shaper
calibration measures what the printer really does.

> **Version-sensitive.** This patches Klipper source files on the printer. It ships one fragment per
> upstream change and the daemon applies them in order.

## What it patches

`klippy/extras/resonance_tester.py`, the object that runs `TEST_RESONANCES` and drives the accelerometer.

## What it changes

| Change | What you get |
| --- | --- |
| Accelerometer selection and `ACCEL_PER_HZ` | `TEST_RESONANCES` can use a chip other than the stock one, and its acceleration per hertz can be set from the command |
| Sweeping vibrations test | A gentler sweep runs alongside the pulse test |
| Snapmaker fixup | The sweep uses the frequency range the printer is set up for instead of a fixed one |

## Using it

Install the plugin you actually want; it asks for this one. Klipper restarts and the newer code is
in. Nothing to configure.

## Notes

- Patches `/home/lava/klipper/klippy/extras/resonance_tester.py`; reverted on uninstall and re-applied after an OTA
  firmware update.
- These fragments used to be applied by the `klipper-motion` plugin. They live here now, so a plugin
  that needs this file asks for this service instead of patching it itself.
- Snapmaker U1. Fits firmware 1.3.0, 1.4.0 and 1.5.0.
