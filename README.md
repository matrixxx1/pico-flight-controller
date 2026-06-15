# Pico Flight Controller

Raspberry Pi Pico receiver and sensor testbed for a flight-controller-style build.

## Contents

- `main.py` - MicroPython firmware currently focused on reading an R8EF receiver PPM signal on Pico `GP15`.
- `vl53l0x.py` - VL53L0X / UL53LDK distance sensor driver used by earlier sensor builds.
- `ControllerTester/` - Vite + Three.js browser dashboard for Web Serial display of receiver and sensor readings.
- `simulator/` - Local browser simulator that generates Pico-shaped serial lines for drift, RC input, and fault testing.
- `QMC5883P.pdf` - Compass sensor reference sheet.
- `RPI_PICO-20260406-v1.28.0.uf2` - MicroPython UF2 used for Pico setup.

## Hardware Used

- Raspberry Pi Pico running MicroPython.
- Radiolink R8EF receiver, powered from the Pico `3V3` rail for bench testing.
- Radiolink transmitter bound to the R8EF.
- HW-617 / TCA9548A I2C multiplexer.
- Five UL53LDK / VL53L0X time-of-flight distance sensors.
- GY-271 compass module with QMC5883P / HP5883 magnetometer.
- ADXL345 accelerometer module.
- PCA9685 16-channel 12-bit I2C PWM servo driver.
- External 5V-6V BEC or servo battery for the PCA9685 `V+` servo rail.
- USB cable from the Pico to the Windows laptop.

## Wiring Diagram

Current receiver-only firmware reads the R8EF on `GP15`. The sensor wiring below documents the full bench layout used by the browser viewer and earlier firmware builds.

```text
                       USB
Windows laptop <---------------- Raspberry Pi Pico
                                      |
                                      | GP15
                                      v
                              R8EF CH2 signal

Pico 3V3 --------------------+-------- R8EF VCC
                             +-------- HW-617 VCC
                             +-------- Sensor VCC/VIN rails

Pico GND --------------------+-------- R8EF GND
                             +-------- HW-617 GND
                             +-------- Sensor GND rails

Pico GP0 / SDA ---------------------- HW-617 SDA
Pico GP1 / SCL ---------------------- HW-617 SCL
Pico GP0 / SDA ---------------------- PCA9685 SDA
Pico GP1 / SCL ---------------------- PCA9685 SCL

Pico 3V3 ---------------------------- PCA9685 VCC
Pico GND ---------------------------- PCA9685 GND
External 5V-6V BEC + ---------------- PCA9685 V+
External BEC GND -------------------- PCA9685 GND

HW-617 CH0: SC0/SCL + SD0/SDA ------- UL53LDK / VL53L0X #0
HW-617 CH1: SC1/SCL + SD1/SDA ------- UL53LDK / VL53L0X #1
HW-617 CH2: SC2/SCL + SD2/SDA ------- UL53LDK / VL53L0X #2
HW-617 CH3: SC3/SCL + SD3/SDA ------- UL53LDK / VL53L0X #3
HW-617 CH4: SC4/SCL + SD4/SDA ------- GY-271 compass
HW-617 CH5: SC5/SCL + SD5/SDA ------- ADXL345 accelerometer
HW-617 CH6: SC6/SCL + SD6/SDA ------- Forward TOF5 / UL53LDK / VL53L0X
```

## Wiring Table

| Device | Pin | Connects To | Notes |
|---|---|---|---|
| R8EF | CH2 signal | Pico `GP15` | PPM input for receiver-only firmware. |
| R8EF | VCC / middle pin | Pico `3V3` | The receiver is marked `3-15V`; `3V3` is for bench testing. |
| R8EF | GND / dark pin | Pico `GND` | Must share ground with the Pico. |
| HW-617 / TCA9548A | SDA | Pico `GP0` | Root I2C bus. |
| HW-617 / TCA9548A | SCL | Pico `GP1` | Root I2C bus. |
| HW-617 / TCA9548A | VCC | Pico `3V3` | Keep I2C logic at Pico-safe voltage. |
| HW-617 / TCA9548A | GND | Pico `GND` | Shared ground. |
| PCA9685 | SDA | Pico `GP0` | Shares the root I2C bus. |
| PCA9685 | SCL | Pico `GP1` | Shares the root I2C bus. |
| PCA9685 | VCC | Pico `3V3` | Logic power; keeps I2C pullups Pico-safe. |
| PCA9685 | GND | Pico `GND` and BEC GND | Common ground for logic and servo power. |
| PCA9685 | V+ | External `5V-6V` BEC / servo battery + | Servo/ESC power rail only; do not connect to Pico `3V3`. |
| UL53LDK #0 | SDA/SCL | HW-617 `SD0` / `SC0` | VL53L0X distance sensor. |
| UL53LDK #1 | SDA/SCL | HW-617 `SD1` / `SC1` | VL53L0X distance sensor. |
| UL53LDK #2 | SDA/SCL | HW-617 `SD2` / `SC2` | VL53L0X distance sensor. |
| UL53LDK #3 | SDA/SCL | HW-617 `SD3` / `SC3` | VL53L0X distance sensor. |
| GY-271 | SDA/SCL | HW-617 `SD4` / `SC4` | Compass / magnetometer. |
| ADXL345 | SDA/SCL | HW-617 `SD5` / `SC5` | Accelerometer. |
| Forward TOF5 / UL53LDK | SDA/SCL | HW-617 `SD6` / `SC6` | Fifth physical TOF sensor, connected on mux channel 6. |
| All I2C sensors | VCC / VIN | Pico `3V3` rail | Use 3.3V-compatible modules. |
| All I2C sensors | GND | Pico `GND` rail | Shared ground. |

## PCA9685 Output Labels

The browser viewer labels the 16 PCA9685 outputs as `CH1` through `CH16`. Many PCA9685 boards are silk-screened `0` through `15`; if so, app `CH1` is the board's output `0`, app `CH2` is board output `1`, and so on.

| App Channel | Output Label |
|---|---|
| CH1 | Left front ESC |
| CH2 | Left Front Mount |
| CH3 | Right front ESC |
| CH4 | Right front Mount |
| CH5 | Left Rear ESC |
| CH6 | Left Rear Mount |
| CH7 | Right Rear ESC |
| CH8 | Right Rear Mount |
| CH9 | Elevator |
| CH10 | Rudder |
| CH11 | Landing Gear |
| CH12 | Lights |
| CH13 | Camera Pan |
| CH14 | Camera Tilt |
| CH15 | Spare |
| CH16 | Spare |

## R8EF Mode

```text
R8EF CH2 signal -> Pico GP15
R8EF VCC        -> Pico 3V3
R8EF GND        -> Pico GND
```

The R8EF needs SBUS/PPM mode for CH2 to output a combined PPM stream.

- Red LED: PWM mode, each channel is a separate PWM output.
- Blue/purple LED: SBUS/PPM mode, where `CH1` is SBUS and `CH2` is PPM.
- Toggle mode by quick-pressing the receiver `ID SET` button twice within 1 second.

## Browser Viewer

```powershell
cd ControllerTester
npm install
npm run dev -- --port 5173
```

Then open `http://127.0.0.1:5173` in Chrome or Edge and connect to the Pico over Web Serial.

## Simulator

```powershell
cd simulator
.\Start-Simulator.ps1
```

Then open the URL printed by the launcher, starting with `http://127.0.0.1:5174`. The simulator can copy generated serial lines into the `ControllerTester` raw/manual parser, run short RC instruction scripts, read a USB transmitter/game-controller through the browser Gamepad API, and read CH340-style serial adapters through Web Serial.
