# Attributions - u1-base-print-task-config

**Plugin author:** Bespok3d

The patch in this package is the Bespok3d project's own work. It is applied to Snapmaker's Klipper
fork, which is GPL-3.0, so the patch is GPL-3.0-only as well.

The idea of a `FORCE` parameter that overrides the printer's mid-print refusal came from paxx12's
Extended Firmware overlay `36-feature-print-preferences` (GPL-3.0). None of that overlay's code
ships here: the guard is expressed differently, through a registration a plugin holds, so that
more than one plugin can ask for it at once. The credit is for the idea, and it is recorded here
because this is where the change to Snapmaker's file now lives.

| Upstream project | Author | Licence | Needed at runtime | Code ships in this package |
| --- | --- | --- | --- | --- |
| Snapmaker's Klipper fork | Snapmaker and the Klipper contributors | GPL-3.0 | yes | no |

