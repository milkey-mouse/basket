# Basket Case

This is a case for a Raspberry Pi, ostensibly running Basket.

![Picture of the first Basket Case](case.jpg)

The case was designed in [Fusion 360](https://www.autodesk.com/products/fusion-360/overview). A `.f3d` file is included for editing in Fusion and a STEP file is included for editing elsewhere. STLs are also included for 3d printing without modification.

# Parts

To assemble the Basket Case, you will need:

- a Raspberry Pi (version 3 or 3B recommended)
- an [official](https://www.amazon.com/dp/B01ER2SKFS) or [unofficial](https://www.amazon.com/dp/B00N1YJKFS) (recommended) Pi Camera
- one of each [3D printed part](printable/)
- M4 mounting hardware
  - 4x low-profile black-oxide M4x20 machine screws (McMaster part #[93070A107](https://www.mcmaster.com/#93070A107))
  - 4x black-oxide M4 hex nuts (McMaster part #[98676A600](https://www.mcmaster.com/#98676A600))
- 40mmx10mm Noctua fan ([on Amazon.com](https://www.amazon.com/dp/B00NEMGCIA))

The exact types of screws and nuts used are fungible; we chose the fancy black screws to match the case and to (arguably) make it more stealthy.

So is the brand of fan: although I would highly recommend the Noctua fan linked above (it's very quiet, and comes with special rubber mounting hardware), it's about twice as expensive as any other 40mm fan. **If you use another fan, you will need 4 more M4 screws and 4 more M4 nuts to mount it**, as shown in the Fusion 360 model.

A USB webcam would work as a substitute to the Pi Camera, but will not have a convenient way of mounting. A GoPro may work instead of a Pi Camera; the hinge on the end of the arm is a GoPro mount. This is untested, however.

# License

Unlike the source code for the Basket software, the hardware is licensed under a [Creative Commons Attribution-Non-Commercial-ShareAlike 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0) license in order to comply with the licenses of [other designs](CREDITS.md) this case is a derivative of.
