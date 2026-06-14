# Pico Controller Tester

Use `Start-ControllerTester.bat` to launch the app.

Do not open `index.html` directly. The app uses browser modules and Web Serial, so it needs to run from `http://127.0.0.1:5173`.

## Pico I2C wiring

Pico shared I2C bus:

```text
Pico 3V3(OUT) -> HW-617 VCC
Pico GND      -> HW-617 GND
Pico GP1      -> HW-617 SCL
Pico GP0      -> HW-617 SDA
```

Sensors through the HW-617:

```text
HW-617 SC0/SD0 -> UL53LDK #0 SCL/SDA
HW-617 SC1/SD1 -> UL53LDK #1 SCL/SDA (top)
HW-617 SC2/SD2 -> UL53LDK #2 SCL/SDA (right side)
HW-617 SC3/SD3 -> UL53LDK #3 SCL/SDA (left side)
HW-617 SC4/SD4 -> GY-271 SCL/SDA
HW-617 SC5/SD5 -> ADXL345 SCL/SDA

HW-617 3V3/GND -> each UL53LDK VIN/GND
HW-617 3V3/GND -> GY-271 VCC/GND
HW-617 3V3/GND -> ADXL345 VCC/GND
ADXL345 CS      -> 3V3
ADXL345 SDO     -> GND
```

The Pico code expects the HW-617/TCA9548A at `0x70`, each UL53LDK/VL53L0X at its normal `0x29` address on channels `0..3`, the GY-271 on channel `4`, and the ADXL345 at `0x53` on channel `5`.
