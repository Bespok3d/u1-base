# u1-base: instructions for AI assistants

You are working in a Bespok3d plugin repo. Bespok3d is a printer-agnostic plugin manager for Klipper
printers that runs on stock firmware, with no custom-firmware flashing. This repo is the U1 base
layer: it publishes the plugins that patch Snapmaker's own Klipper source files and open registration
points (hook doors) in them, as signed `.b3` packages that the Bespok3d desktop app installs onto a
printer through the on-printer daemon. This file is the contract for any LLM or agent that edits this
repo. Contributors here often work with AI assistance, so the rules and the design intent are written
down and enforced in the gate, not left implicit. The human reviewer rejects a PR that ignores them.

If you are a non-Claude tool, `AGENTS.md` points you here.

## What this repo ships

u1-base is the base layer for the Snapmaker U1: each plugin patches exactly one stock
Snapmaker/Klipper source file. Most of them add registration points (doors) to it, and other plugins,
in other repos, register through those doors to add real capability (RFID, filament detection,
print-preference overrides) without ever touching Snapmaker's own files directly. A few carry a
straight replacement of upstream mathematics instead, because an algorithm has no extension point to
expose (ADR-0043, hook shape 3). The base layer ships as a Collection (`kind: "collection"`) of these
plugins so the app installs and updates them together, but each is independently a normal patch-only
plugin: `restart: ["klipper"]`, no config, no placed files.

Plugins:

- **u1-base-print-task-config**: Opens two hook doors in Snapmaker's `print_task_config.py`:
  pressure-advance-reset suppression, and a mid-print FORCE override for SET_PRINT_PREFERENCES. Alone
  it changes nothing: both doors are no-ops until another plugin registers.
- **u1-base-fm175xx-reader**: Opens two hook doors in Snapmaker's `fm175xx_reader.py`: a SAK-keyed
  card-type-handler registry, and a claim-based card-handler registry, so other plugins can add RFID
  card support without editing Snapmaker's driver. Alone it changes nothing.
- **u1-base-filament-detect**: Opens a hook door in Snapmaker's `filament_detect.py`: a
  card-protocol-parser registry, so other plugins can report live filament info without editing
  Snapmaker's driver. Alone it changes nothing.
- **u1-base-resonance-tester**: Carries upstream Klipper's resonance-measurement code into Snapmaker's
  `extras/resonance_tester.py`: accelerometer-chip selection, the sweeping-vibrations test and
  `accel_per_hz`. A behaviour replacement, so it does change what the printer does on its own.
- **u1-base-toolhead**: Carries upstream Klipper's cornering and lookahead code into Snapmaker's
  `toolhead.py`: centripetal junction handling and a tuned lookahead flush time. A behaviour
  replacement.
- **u1-base-shaper-calibrate**: Carries upstream Klipper's low-frequency handling into Snapmaker's
  `extras/shaper_calibrate.py`, so the sweeping-vibrations data is scored correctly. A behaviour
  replacement.

Every plugin here is a patch (a unified diff against one Snapmaker source file) and nothing else: no
config, no Klipper extras of its own, no Python payload.

Read `README.md` for the repo's layout, build, and release mechanics before you change anything.

## The model: a plugin declares WHAT, never HOW

A Bespok3d plugin is declarative. Each plugin's `manifest.json` declares WHAT the printer should end
up with (here, an `install.instrument` entry: a `klipper-source` target name plus a diff, and a
`restart` hook), never a path, a raw shell command, or a setup script that runs on the printer. The
on-printer daemon reads the manifest and realizes it: it fetches the printer's own current copy of the
target file as the pristine baseline, applies the diff, and restarts the named service.

- **A base plugin takes one of the three shapes ADR-0043 names, and no other.** An entry-point hook
  or a suppression hook must never change or remove an existing hook, and must never change stock
  behaviour when nothing is registered against it: for those two, a fragment that changes observable
  behaviour on its own is a defect, not a feature, and that is the test each ships with. The third
  shape, a behaviour replacement, is upstream mathematics swapped in with no API at all; it does
  change what the printer does the moment it is installed, and it exists because an algorithm has no
  extension point to expose. Do not add a fourth shape, and do not turn a hook into a replacement to
  get around writing the door.
- **No plugin scripts.** Do not add a shell script, a `postinstall`, or any code meant to run on the
  printer to do setup. If the daemon cannot express what a plugin needs declaratively, that is a
  daemon or adapter change, not a script smuggled into a plugin.
- **One base plugin owns each Snapmaker file.** `extras/print_task_config.py` is owned by
  `u1-base-print-task-config`, `extras/fm175xx_reader.py` by `u1-base-fm175xx-reader`,
  `extras/filament_detect.py` by `u1-base-filament-detect`, `extras/resonance_tester.py` by
  `u1-base-resonance-tester`, `toolhead.py` by `u1-base-toolhead`, and `extras/shaper_calibrate.py`
  by `u1-base-shaper-calibrate`. A second plugin patching a file one of these six already owns
  reintroduces the double-patch baseline corruption ADR-0043 exists to close; do not add one.
- **The printer is never left broken.** Every change keeps the printer usable. The daemon's
  auto-deactivate safety net peels off a plugin that breaks Klipper or Moonraker; do not defeat it.
- **`manifest.json` is the release contract.** Bump its `version` to cut a release. Do not hand-edit
  `index.json`, the `.atom.json`, `index.json.sig`, or anything under `dist/`: those are generated and
  signed by the `b3-builder` CI Action.

## The non-negotiables

1. **RULE ZERO: no em-dash or en-dash, anywhere** (code, comments, docs, commit messages). Use a comma,
   colon, semicolon, parentheses, or two sentences. A hyphen in a compound word is fine. The gate's
   em-dash guard fails the build on a violation.
2. **Every identifier carries domain meaning.** A name says what the thing *is* in the domain, never its
   type, its position, or a role-free abbreviation. No `a`/`b`, `tmp`, `data`, single letters.
3. **Nesting beyond one level is suspicious.** Flatten by default: guard clauses, early returns, an
   extracted named function, a named lookup instead of a nested ternary.
4. **Rule of three.** The third copy of a block, shape, or constant gets extracted. Duplication is a bug;
   "no premature abstraction" forbids generalizing for one caller, it does not excuse copy-paste.
5. **Extend upstream minimally and additively.** Every plugin here patches Snapmaker's own Klipper
   source. Never delete or rewrite an upstream method; add alongside it (a new function, a new
   registration point), so the change survives a re-vendor of the upstream code and stays a hook door,
   not a rewrite.
6. **Never commit a real secret or a real LAN value.** Tokens, keys, real IP addresses, and real UUIDs
   stay out of the tree. Fixtures are obviously fake.

## How to work a change

1. **Understand first.** Read the plugin's `manifest.json`, its `files/` diff, and its `doc/README.md`.
   Do not invent structure; if the intent is unclear, ask one specific question and stop.
2. **Scope it to a user story.** "As a [role], I want [capability] so that [value]." Implement only what
   the story needs: no speculative features, no defensive code for cases that cannot happen.
3. **Write the change** to the rules above. A new door is an addition to the diff, never an edit to a
   line the diff already touches for a different reason.
4. **Run the gate and make it green:** `cd plugins/u1-base && ./scripts/check.sh`. There is nothing
   to set up and no network: the gate fit-proves every patch against Snapmaker's own source for every
   firmware a printer can be running, and that source is vendored under
   `tests_support/snapmaker_source/` (see its README). The shared detectors come from the
   `lib_bespok3d` submodule, which the gate finds by itself; `B3D_TOOLING` only needs setting if
   yours lives somewhere else.
5. **On a gate failure, fix the cause.** Never hand-wave a real smell away. If a detector is genuinely
   wrong about a line, the fix is a per-instance justified allow at the smell
   (`# gate-allow <metric>: <reason>`, with a reason that survives "why is THIS one ok?"), never a
   blanket mute to make a number go down.
6. **Add a regression test** where the repo has a test layer for the behavior, in the same change: it
   fails on the old behavior and passes on the fix.
7. **Keep the docs current.** If the change alters what a plugin does or how it is configured, update
   that plugin's `doc/README.md` and its `doc/CHANGELOG.md`.

## Hard constraints

- **Never run git.** The maintainer commits. Leave the tree green and hand over exact commands if a git
  action is needed.
- **Never SSH-mutate or reconfigure a live printer** without explicit per-action authorization. A serial
  port or GPIO on a printer may be a live Klipper MCU link; read-only diagnosis is fine, but propose any
  device-changing step and wait for a yes.
- **The gate must be green** before a change is considered done.

## When you are unsure

Ask one specific question and stop. Do not guess and implement, and do not "try something reasonable."
The architecture is the maintainer's; your job is to implement it to the rules above.
