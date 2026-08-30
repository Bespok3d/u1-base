# u1-base

[![licence](https://img.shields.io/badge/licence-GPL--3.0-blue)](LICENSE)
[![release](https://img.shields.io/github/v/release/Bespok3d/u1-base)](https://github.com/Bespok3d/u1-base/releases)
![printer](https://img.shields.io/badge/printer-Snapmaker%20U1-informational)
![stock firmware](https://img.shields.io/badge/stock%20firmware-no%20flashing-brightgreen)

This repo is the U1 base layer. Each plugin patches exactly one stock Snapmaker/Klipper source file.
Most of them add registration points (doors) to it and never change existing behaviour by themselves;
other plugins, in other repos, register through those doors to add real capability (RFID, filament
detection, print-preference overrides) without ever touching Snapmaker's own files directly. A few
carry a straight replacement of upstream mathematics instead, because an algorithm has no extension
point to expose (ADR-0043, hook shape 3); those do change what the printer does on their own. The base
layer ships as a Collection (`kind: "collection"`) of these plugins so the app installs and updates
them together, but each is independently a normal patch-only plugin: `restart: ["klipper"]`, no
config, no placed files.

Plugins:

- **u1-base-print-task-config** - Opens two hook doors in Snapmaker's `print_task_config.py`
  (pressure-advance-reset suppression, and a mid-print FORCE override for SET_PRINT_PREFERENCES).
  Alone it changes nothing: both doors are no-ops until another plugin registers.
- **u1-base-fm175xx-reader** - Opens two hook doors in Snapmaker's `fm175xx_reader.py` (a SAK-keyed
  card-type-handler registry, and a claim-based card-handler registry) so other plugins can add RFID
  card support without editing Snapmaker's driver. Alone it changes nothing.
- **u1-base-filament-detect** - Opens a hook door in Snapmaker's `filament_detect.py` (a
  card-protocol-parser registry) so other plugins can report live filament info without editing
  Snapmaker's driver. Alone it changes nothing.
- **u1-base-resonance-tester** - Carries upstream Klipper's resonance-measurement code into
  Snapmaker's `extras/resonance_tester.py`: accelerometer-chip selection, the sweeping-vibrations
  test and `accel_per_hz`. A behaviour replacement.
- **u1-base-toolhead** - Carries upstream Klipper's cornering and lookahead code into Snapmaker's
  `toolhead.py`: centripetal junction handling and a tuned lookahead flush time. A behaviour
  replacement.
- **u1-base-shaper-calibrate** - Carries upstream Klipper's low-frequency handling into Snapmaker's
  `extras/shaper_calibrate.py`, so the sweeping-vibrations data is scored correctly. A behaviour
  replacement.

## Layout

```text
u1-base/
  <plugin-id>/          # one plugin = one dir; its name is the manifest .name
    manifest.json
    files/               # the plugin's diff(s): unified diffs against Snapmaker's own source
    doc/README.md        # rendered in-app; not deployed
  .github/workflows/release.yml
  index.json             # the published sub-list (committed; referenced by main-index lists[])
  dist/                  # build output (gitignored)
```

Three plugins ship here, packaged together as a Collection (`kind: "collection"`) so the app installs
and updates the set in one batch; each is still an independent, normal patch-only plugin underneath.
Each plugin declares an `install.instrument` entry, a `klipper-source` target name plus a diff, never
a raw path or a live edit on the printer; the printer-side adapter fetches the printer's own current
copy of the target file as the pristine baseline and applies the diff over it.

## Build locally

Needs Node.js 20+. Builds run through the shared `Bespok3d/b3-builder` tool:

```sh
npm install github:Bespok3d/b3-builder
npx b3-builder build --source ./u1-base-print-task-config --atom-repo Bespok3d/u1-base
# -> dist/u1-base-print-task-config-<ver>.b3 + dist/u1-base-print-task-config.atom.json
```

Drop `--source` to build every plugin in the repo at once, the Collection included.

Writing a base plugin of your own? Start at
[ADR-0043](https://github.com/Bespok3d/Bespok3d_history/blob/main/doc/decisions/0043-base-layer-owns-patching.md)
for the ownership model, then the plugin documentation:
[Bespok3d/b3-builder/doc](https://github.com/Bespok3d/b3-builder/tree/main/doc).

## Releasing

Bump a plugin's `manifest.json` `version` and push the tag `plugin-<name>-v<version>` naming that
plugin and that exact number. A push to `main` publishes nothing, and the run is refused if the tag
and the manifest disagree. CI runs the `Bespok3d/b3-builder` Action over the whole repo, which packs
each `.b3`, cuts a release per plugin, assembles this repo's `index.json` sub-list as `U1 Base`, and
registers it in `Bespok3d/main-index` (`lists/<repo>.json`). Secrets: `MAIN_INDEX_TOKEN`
(contents:write on main-index) and `REGISTRY_SIGNING_KEY` (the org registry key the `b3-builder`
Action signs each `.b3` and atom with).

## Composition

Bespok3d's own code in this repository is under the repository licence below. No third-party binary
or package is vendored here: each plugin ships only a small unified diff against one of Snapmaker's
own Klipper source files (`extras/print_task_config.py`, `extras/fm175xx_reader.py`,
`extras/filament_detect.py`, `extras/resonance_tester.py`, `toolhead.py`,
`extras/shaper_calibrate.py`), never a copy of that file itself. At install time the daemon fetches
the printer's own current copy of the target file as the pristine baseline and applies the diff over
it, so nothing of Snapmaker's is stored, redistributed, or built in this repository, only the delta a
plugin adds.

The diffs in `u1-base-resonance-tester`, `u1-base-toolhead` and `u1-base-shaper-calibrate` are the
one exception to "Bespok3d's own code": they came from paxx12's Extended Firmware overlay
`11-patch-klipper`, GPL-3.0-only, and carry upstream Klipper commits by Kevin O'Connor, MRX8024 and
Dmitry Butyugin. `vendor/klipper-motion-patches/` holds that licence text and records what, if
anything, Bespok3d changed in them; `REUSE.toml` records their copyright separately from the
repository's own.

A diff against a GPL-3.0-only work is itself a derivative work under that licence, which is why this
repository, like `u1-extras`, is GPL-3.0-only rather than the AGPL-3.0-or-later most of Bespok3d uses.

## Licence

Copyright (C) 2026 unlucio and the Bespok3d contributors

GPL version 3, for the code in this repository written by Bespok3d. See Composition above for how it
relates to Snapmaker's own source.

This program is free software: you can redistribute it and/or modify it under the terms of version 3
of the GNU General Public License as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not,
see <https://www.gnu.org/licenses/>. The full text is in [LICENSE](LICENSE).

Bespok3d's own code elsewhere in the project is AGPL-3.0-or-later. The code here is GPL-3.0-only
instead because it has Extended Firmware lineage, which is GPL-3.0-only, and because a diff against
Snapmaker's own GPL-3.0-only Klipper source is itself a derivative work under that licence. Version 3
of the GPL and version 3 of the AGPL may be combined in a single work, and section 13 of each licence
says so; what cannot happen is code offered under version 3 of the GPL alone being re-offered under
the AGPL.

Bespok3d is a project of the Bespok3d Organisation, which is not a legal entity. Copyright is held by
the individual authors named above.

## Support this project

Every plugin in this repository is Bespok3d's own work: original patches against Snapmaker's stock
Klipper source, not a repackaging of someone else's project.

If this saved you an afternoon, you can [buy me a coffee](https://buymeacoffee.com/unlucio).
