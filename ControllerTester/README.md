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
HW-617 SC5/SD5 -> MPU-6050 SCL/SDA
HW-617 SC7/SD7 -> PCA9685 SCL/SDA

HW-617 3V3/GND -> each UL53LDK VIN/GND
HW-617 3V3/GND -> GY-271 VCC/GND
HW-617 3V3/GND -> MPU-6050 VCC/GND
Pico 3V3/GND    -> PCA9685 VCC/GND
External BEC +  -> PCA9685 V+
External BEC GND -> PCA9685 GND
```

The Pico code expects the HW-617/TCA9548A at `0x70`, each UL53LDK/VL53L0X at its normal `0x29` address on channels `0..3`, the GY-271 on channel `4`, the MPU-6050 at `0x68` or `0x69` on channel `5`, and the PCA9685 at its normal `0x40` address on channel `7` when servo output firmware is added.

## Flight modes

The viewer shows the active flight mode from the Pico serial stream. RC5 low is `flightmode1` / plane mode, RC5 middle is `flightmode2` / transition mode, and RC5 high is `flightmode3` / hover mode. In plane mode, RC4 controls the rudder servo. In transition mode, RC4 controls both the rudder servo and rear mount yaw tilt. In hover mode, RC4 tilts the rear mount pair for yaw while the rudder servo centers.
