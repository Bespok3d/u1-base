# Attributions - u1-base-shaper-calibrate

**Plugin author:** Dmitry Butyugin (upstream Klipper commit) and paxx12 (Extended Firmware overlay `11-patch-klipper`), packaged by Bespok3d

An upstream Klipper input shaper fix the stock firmware predates.

| Upstream project | Author | Licence | Needed at runtime | Code ships in this package |
| --- | --- | --- | --- | --- |
| Klipper | Kevin O'Connor and the Klipper contributors | GPL-3.0 | yes | yes |
| shaper_calibrate low frequency damping | Dmitry Butyugin | GPL-3.0 | yes | yes |
| Extended Firmware overlay `11-patch-klipper` | paxx12 | GPL-3.0 | no | yes |

These fragments come from the Extended Firmware overlay `11-patch-klipper`, GPL-3.0-only, and stay
under that licence. The licence text and the provenance note are in `vendor/klipper-motion-patches/`
at the root of this repository. They were carried here unchanged from the `klipper-motion` plugin,
which used to apply them itself.

Upstream: https://github.com/Klipper3d/klipper

