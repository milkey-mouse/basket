# Firmware

This code runs on the ESP32 inside each of the [Bluetooth egg cups](../hw/cup). It drives the servo and exposes a single BLE service `Servo` with a single characteristic `Angle` that can be set to a single-byte value between 0 and 180 degrees (theoretically; some servos have a slightly lower or higher range of motion, or different pulse widths). (See the [server source](https://github.com/milkey-mouse/basket/blob/258ce027d863400e539d3bcdd0c3469c505ceb4b/sw/basket/worker.py#L33-L340).)

# Building/Flashing

This is an [ESP-IDF](https://github.com/espressif/esp-idf) project; accordingly, to build it, you must first [set up an ESP-IDF enviroment](https://docs.espressif.com/projects/esp-idf/en/latest/get-started/#setup-toolchain)

Once ESP-IDF is installed and your PATH variable is correctly set up, simply plug in your ESP32 and run `make flash`.
