# Changelog

## 0.1.1 - 2026-11-05

- Installs the 0.1.1 releases of U1 Base RFID reader, U1 Base filament detect and U1 Base resonance
  tester, the first that fit Snapmaker firmware 2.1.0. A printer on the 2.1.0 beta refused their
  0.1.0 versions, and the RFID plugins that need the reader and filament detect doors went down
  with them.
- U1 Base resonance tester 0.1.1 also now requires U1 Base toolhead and U1 Base shaper calibrate,
  both already members of this collection: its sweeping vibrations test needs them.
- The collection now lives in its own `u1-base/` folder, like every plugin here. The release builder
  only discovers plugin folders, so from the repository root this collection was never built into the
  published list, and this is its first publication.

## 0.1.0 - 2026-08-22

- First release of the "U1 Base Layer" collection: installs U1 Base print task config, U1 Base RFID
  reader and U1 Base filament detect together, in one batch with a single service restart.
