# Changelog

## 0.1.1 - 2026-10-29

- Fits Snapmaker firmware 2.1.0. That firmware added a fail-fast first scan to the reader driver,
  which moved the lines this plugin's doors sit beside, so 0.1.0 refused to install on it ("Hunk 2
  FAILED") and every RFID plugin that needs the doors went down with it. A printer on 2.1.0 or newer
  now takes its own fragment; the doors it opens are the same, and with no plugin registered the
  reader still behaves exactly as stock, including the new first scan.
- Proved against the 2.1.0 beta (build 157), copied off a U1 running it, and against 2.0.0
  (build 205), extracted from Snapmaker's upgrade image.

## 0.1.0 - 2026-08-22

- First release. Opens the doors described in `README.md`. With no plugin registered against them,
  the printer behaves exactly as it did before.
