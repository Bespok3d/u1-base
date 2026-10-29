# Changelog

## 0.1.1 - 2026-10-29

- Fits Snapmaker firmware 2.1.0. That firmware rewrote how `TEST_RESONANCES` picks its
  accelerometer and now resolves the chips at the start of every test, so 0.1.0 refused to install
  on it. A printer on 2.1.0 or newer now takes its own versions of the first two fragments.
- On 2.1.0 the upstream chip lookup is left out: Snapmaker's own lookup already finds a chip by its
  exact name, falls back to the `adxl345` prefix, understands the new accelerometer wrapper and
  reports an unknown chip. `ACCEL_PER_HZ`, the sweeping vibrations test and the frequency range fix
  are applied exactly as before.
- Proved against the 2.1.0 beta (build 157), copied off a U1 running it.
- Now requires U1 Base: toolhead. The sweeping vibrations test calls a toolhead method that only
  that package adds, so with this package installed alone `TEST_RESONANCES` stopped on its first
  move with an internal error and shut the printer down, on every firmware. The two used to be
  applied together by `klipper-motion`; the split into one package per file lost that link.
- Now also requires U1 Base: shaper calibrate. It carries the rest of the same upstream change as
  the sweeping test: it damps the low-frequency energy the sweep itself adds, so
  `SHAPER_CALIBRATE` does not pick a shaper from it.

## 0.1.0 - 2026-08-24

- First release. Carries the three motion fragments that the `klipper-motion` plugin used to apply to
  `klippy/extras/resonance_tester.py`, unchanged.
