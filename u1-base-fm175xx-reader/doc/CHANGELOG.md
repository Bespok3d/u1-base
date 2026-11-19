# Changelog

## 0.2.0 - 2026-11-14

- Opens a card session hook door: `register_card_session_hook(owner, session_hook)` and
  `unregister_card_session_hook(owner)`. A plugin that wants to act on the card on the reader, such as
  one that works on a mounted spool's tag, needs to run in the reader thread and to know which
  channel it is on, without replacing another plugin's handler. The card type door
  holds one handler per SAK and another plugin may own that slot, the claim door only fires after a
  failed MIFARE Classic read, and neither says which channel the card is on. The hook is called as
  `session_hook(reader, channel)`, before the card handlers, once per read attempt, and several plugins can hold it at once.
- Adds to every fragment and changes none of the existing doors. With no plugin registered the
  reader behaves exactly as before.

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
