# Attributions - u1-base-toolhead

**Plugin author:** Kevin O'Connor and Dmitry Butyugin (upstream Klipper commits) and paxx12 (Extended Firmware overlay `11-patch-klipper`), packaged by Bespok3d

Upstream Klipper motion planner fixes the stock firmware predates.

| Upstream project | Author | Licence | Needed at runtime | Code ships in this package |
| --- | --- | --- | --- | --- |
| Klipper | Kevin O'Connor and the Klipper contributors | GPL-3.0 | yes | yes |
| toolhead cornering and lookahead commits | Kevin O'Connor and Dmitry Butyugin | GPL-3.0 | yes | yes |
| Extended Firmware overlay `11-patch-klipper` | paxx12 | GPL-3.0 | no | yes |

These fragments come from the Extended Firmware overlay `11-patch-klipper`, GPL-3.0-only, and stay
under that licence. The licence text and the provenance note are in `vendor/klipper-motion-patches/`
at the root of this repository. They were carried here unchanged from the `klipper-motion` plugin,
which used to apply them itself.

Upstream: https://github.com/Klipper3d/klipper

