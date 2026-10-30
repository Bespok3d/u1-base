# Changelog

## 0.1.1 - 2026-10-29

- Fits Snapmaker firmware 2.1.0. That firmware moved the startup spool check onto a timer, which
  added lines where this plugin's door sits, so 0.1.0 refused to install on it and every RFID plugin
  that needs the door went down with it. A printer on 2.1.0 or newer now takes its own fragment; the
  door is the same, and with no plugin registered detection still behaves exactly as stock.
- Proved against the 2.1.0 beta (build 157), copied off a U1 running it, and against 2.0.0
  (build 205), extracted from Snapmaker's upgrade image.

## 0.1.0 - 2026-08-22

- First release. Opens the doors described in `README.md`. With no plugin registered against them,
  the printer behaves exactly as it did before.
