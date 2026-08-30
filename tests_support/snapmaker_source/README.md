# Snapmaker's own Klipper source, one directory per firmware

Every patch in this repo is a diff against a Snapmaker source file, and a diff only means something
against the exact bytes the printer holds. So the proof that a patch fits is run against Snapmaker's
own file, for every firmware a U1 can be running, and those files are kept here rather than fetched:
the gate needs no network and no second checkout, and a firmware Snapmaker later stops serving stays
proved.

One directory per firmware, named by the build number the printer reports. Inside it, the six files
the base layer takes over, at the paths Klipper puts them:

```text
1.5.0.344/klippy/toolhead.py
1.5.0.344/klippy/extras/{filament_detect,fm175xx_reader,print_task_config,resonance_tester,shaper_calibrate}.py
```

Adding a firmware here is all it takes to widen the proof: the tests read whatever directories are
present.

## Where each one came from

| Firmware | Taken from |
| --- | --- |
| 1.3.0.168 | Snapmaker's own firmware download, linked from their release notes |
| 1.4.0.246 | Snapmaker's own firmware download, linked from their release notes |
| 1.4.1.6 | Snapmaker's own firmware download, linked from their release notes |
| 1.5.0.344 | Snapmaker's own firmware download, linked from their release notes |
| 1.5.1.2 | Snapmaker's own firmware download, linked from their release notes |
| 1.5.2.13 | Snapmaker's own firmware download, linked from their release notes |
| 1.6.0.267 | read off a U1 running it, because Snapmaker's release notes list the 1.6.0 page but serve no download for it yet |

Snapmaker's GitHub mirrors (`Snapmaker/u1-klipper`, `Snapmaker/u1-moonraker`) would be the obvious
source, but they are published late and skip releases, so they cannot be what the proof stands on.
The firmware download is what a printer actually installs, which makes it the honest source.

## Adding the next firmware

When Snapmaker publishes one:

```sh
python3 tools/harvest_snapmaker_source.py
```

It reads their release notes, downloads any firmware image that is not already cached, opens the root
filesystem inside it, and writes the six files here. It needs network and `unsquashfs`
(`brew install squashfs`, `apt-get install squashfs-tools`). It names every release the release notes
list but do not serve a download for yet, so a firmware that is announced before its image is up is
reported rather than passed over.

A firmware their download page does not serve, and that only exists on a printer, is copied off that
printer instead and this table says so.
