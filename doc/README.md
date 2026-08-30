# U1 Base Layer

The doors other Bespok3d plugins knock on. On its own it changes nothing you can see.

## What it installs

| Plugin | What it opens |
| --- | --- |
| U1 Base: print task config | Holding off the start-of-print pressure advance reset, and allowing a preference to be changed mid print |
| U1 Base: RFID reader | Claiming and reading a card the stock reader does not understand |
| U1 Base: filament detect | Reading a spool tag the stock firmware does not know, and filling in the filament details |

All three install together with a single service restart.

Every door is a registration set, not a switch: several plugins can hold the same door open at once,
and it closes only when the last one lets go. That is the point of the base layer. Two plugins that
want the same behaviour no longer take it away from each other.

## Read this before you install

- **These plugins replace Klipper program files on the printer.** Uninstalling puts the originals
  back, and they re-apply themselves after a firmware update.
- **Install this because a plugin you want asks for it.** With nothing registered against the doors,
  the printer behaves exactly as it does today.
- **Snapmaker U1 only.** Fits firmware 1.3.0, 1.4.0 and 1.5.0.

## After installing

Nothing to configure.
