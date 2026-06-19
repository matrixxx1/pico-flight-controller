# Pico Flight Controller

Raspberry Pi Pico receiver and sensor testbed for a flight-controller-style build.

## Contents

- `main.py` - MicroPython firmware that reads the R8EF PPM signal on Pico `GP15` and drives the PCA9685 outputs through the HW-617 mux.
- `vl53l0x.py` - VL53L0X / UL53LDK distance sensor driver used by earlier sensor builds.
- `ControllerTester/` - Vite + Three.js browser dashboard for Web Serial display of receiver and sensor readings.
- `simulator/` - Local browser simulator that generates Pico-shaped serial lines for drift, RC input, and fault testing.
- `QMC5883P.pdf` - Compass sensor reference sheet.
- `RPI_PICO-20260406-v1.28.0.uf2` - MicroPython UF2 used for Pico setup.

## Hardware Used

- Raspberry Pi Pico running MicroPython.
- Radiolink R8EF receiver, powered from the Pico `3V3` rail for bench testing.
- Radiolink transmitter bound to the R8EF.
- Radiolink Gens Ace 7.4V 2S LiPo battery powering the transmitter.
- HW-617 / TCA9548A I2C multiplexer.
- Five UL53LDK / VL53L0X time-of-flight distance sensors.
- Four VL53L1X time-of-flight distance sensors ordered for longer-range indoor altitude/range sensing.
- GY-271 compass module with QMC5883P / HP5883 magnetometer.
- MPU-6050 accelerometer/gyroscope module.
- PCA9685 16-channel 12-bit I2C PWM servo driver.
- Four 60A ESCs for the main motors.
- Four X2807 1300KV brushless motors.
- FEICHAO 8A UBEC regulating the PCA9685 `V+` servo rail to 6V.
- MG995 55g metal-gear servo motors for mount/control-surface outputs.
- Four Hooyu RDS3225 25kg waterproof high-torque digital servos with full metal gears and dual shafts.
- MEUS Racing AUX RC light remote controller switch with LTVystore 5mm 5V prewired LED bulbs.
- Six Ovonic 1000mAh 6S 100C LiPo batteries with XT60 plugs.
- ISDT 60BAC 8A / 200W LiPo balance charger for the main 6S batteries.
- Radiolink CM210 charger for the transmitter battery.
- USB cable from the Pico to the Windows laptop.

## Battery Plan

Current battery inventory:

- `6x` Ovonic 1000mAh 6S 100C LiPo batteries with XT60 plugs.
- `1x` Radiolink Gens Ace 7.4V 2S LiPo battery for the transmitter.
- ISDT 60BAC 8A / 200W LiPo balance charger for the main 6S packs.
- Radiolink CM210 charger for the transmitter battery.

Intended battery assignment:

| Battery | Intended Load | Notes |
|---|---|---|
| 1 | Left front motor / ESC | 6S pack feeds the ESC motor power input. |
| 2 | Right front motor / ESC | 6S pack feeds the ESC motor power input. |
| 3 | Left rear motor / ESC | 6S pack feeds the ESC motor power input. |
| 4 | Right rear motor / ESC | 6S pack feeds the ESC motor power input. |
| 5 | Pico + receiver + HW-617 + sensors | Must go through a regulator/BEC before the Pico; do not connect 6S directly to Pico power pins. |
| 6 | FEICHAO 8A UBEC -> PCA9685 `V+` servo rail | 6S pack feeds the UBEC input; regulated 6V UBEC output feeds PCA9685 `V+`. |

Safety note: a 6S LiPo is `22.2V` nominal and `25.2V` fully charged. The Pico, HW-617, sensors, receiver, PCA9685 logic, and PCA9685 `V+` rail cannot take raw 6S voltage directly. The FEICHAO UBEC sits between the 6S pack and PCA9685 `V+` to cap that rail at 6V.

## Wiring Diagram

Current firmware reads the R8EF PPM stream on `GP15`, then sends flight-control output pulses to the PCA9685 on HW-617 channel 7.

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

Pico 3V3 ---------------------------- PCA9685 VCC
Pico GND ---------------------------- PCA9685 GND
FEICHAO 8A UBEC 6V OUT + ------------ PCA9685 V+
FEICHAO 8A UBEC GND ----------------- PCA9685 GND

HW-617 CH0: SC0/SCL + SD0/SDA ------- UL53LDK / VL53L0X #0
HW-617 CH1: SC1/SCL + SD1/SDA ------- UL53LDK / VL53L0X #1
HW-617 CH2: SC2/SCL + SD2/SDA ------- UL53LDK / VL53L0X #2
HW-617 CH3: SC3/SCL + SD3/SDA ------- UL53LDK / VL53L0X #3
HW-617 CH4: SC4/SCL + SD4/SDA ------- GY-271 compass
HW-617 CH5: SC5/SCL + SD5/SDA ------- MPU-6050 IMU
HW-617 CH6: SC6/SCL + SD6/SDA ------- Forward TOF5 / UL53LDK / VL53L0X
HW-617 CH7: SC7/SCL + SD7/SDA ------- PCA9685 PWM servo driver
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
| PCA9685 | SDA | HW-617 `SD7` | I2C data through mux channel 7. |
| PCA9685 | SCL | HW-617 `SC7` | I2C clock through mux channel 7. |
| PCA9685 | VCC | Pico `3V3` | Logic power; keeps I2C pullups Pico-safe. |
| PCA9685 | GND | Pico `GND` and FEICHAO UBEC GND | Common ground for logic and servo power. |
| PCA9685 | V+ | FEICHAO 8A UBEC regulated 6V output + | Servo/ESC power rail only; do not connect to Pico `3V3` or raw 6S. |
| ESC servo extension leads | Signal + GND only | PCA9685 `CH1`, `CH3`, `CH5`, `CH7` | Disconnect / remove the red wire from each ESC servo extension cable to prevent voltage backfeed into the PCA9685 rail. |
| MG995 55g metal-gear servos | Signal/V+/GND | PCA9685 servo outputs | Servo outputs are powered from the FEICHAO-regulated 6V `V+` rail. |
| Hooyu RDS3225 25kg servos | Signal/V+/GND | Available PCA9685 servo outputs | High-torque digital servos; confirm voltage/current draw before running several from the 8A UBEC at once. |
| UL53LDK #0 | SDA/SCL | HW-617 `SD0` / `SC0` | VL53L0X distance sensor. |
| UL53LDK #1 | SDA/SCL | HW-617 `SD1` / `SC1` | VL53L0X distance sensor. |
| UL53LDK #2 | SDA/SCL | HW-617 `SD2` / `SC2` | VL53L0X distance sensor. |
| UL53LDK #3 | SDA/SCL | HW-617 `SD3` / `SC3` | VL53L0X distance sensor. |
| GY-271 | SDA/SCL | HW-617 `SD4` / `SC4` | Compass / magnetometer. |
| MPU-6050 | SDA/SCL | HW-617 `SD5` / `SC5` | Accelerometer/gyro IMU. |
| Forward TOF5 / UL53LDK | SDA/SCL | HW-617 `SD6` / `SC6` | Fifth physical TOF sensor, connected on mux channel 6. |
| PCA9685 | SDA/SCL | HW-617 `SD7` / `SC7` | PWM servo driver, connected on mux channel 7. |
| All I2C sensors | VCC / VIN | Pico `3V3` rail | Use 3.3V-compatible modules. |
| All I2C sensors | GND | Pico `GND` rail | Shared ground. |

Planned upgrade: four VL53L1X ToF sensors have been ordered for longer-range indoor altitude/range sensing. The current firmware and wiring map still target the installed UL53LDK / VL53L0X sensors until those modules are swapped in and the driver is updated.

## PCA9685 Output Labels

The browser viewer labels the 16 PCA9685 outputs as `CH1` through `CH16`. Many PCA9685 boards are silk-screened `0` through `15`; if so, app `CH1` is the board's output `0`, app `CH2` is board output `1`, and so on.

ESC signal leads use servo extension cables into the PCA9685, but the red wire is disconnected/removed on each ESC extension. Only signal and ground are carried through the servo lead so the ESC/BEC side cannot backfeed voltage into the PCA9685 rail.

| App Channel | Output Label |
|---|---|
| CH1 | Left front ESC |
| CH2 | Left Front Mount MG995 servo |
| CH3 | Right front ESC |
| CH4 | Right front Mount MG995 servo |
| CH5 | Left Rear ESC |
| CH6 | Left Rear Mount MG995 servo |
| CH7 | Right Rear ESC |
| CH8 | Right Rear Mount MG995 servo |
| CH9 | Elevator MG995 servo |
| CH10 | Rudder MG995 servo |
| CH11 | Landing Gear MG995 servo |
| CH12 | MEUS Racing AUX RC light switch -> LTVystore 5mm 5V prewired LED bulbs |
| CH13 | Camera Pan MG995 servo |
| CH14 | Camera Tilt MG995 servo |
| CH15 | Spare |
| CH16 | Spare |

## Receiver Control Map

The receiver signal path is:

```text
R8EF CH2 PPM stream -> Pico GP15 -> HW-617 CH7 -> PCA9685 outputs
```

| RC Channel | Transmitter Control | PCA9685 Output |
|---|---|---|
| RC2 | Elevator stick | CH9 / board output 8 |
| RC3 | Speed / throttle | CH1, CH3, CH5, CH7 ESC outputs |
| RC4 | Rudder stick | CH10 / board output 9 |
| RC5 | Flight mode / mount-position switch | Low = `flightmode1` / plane, mid = `flightmode2` / transition, high = `flightmode3` / hover |
| RC7 | MEUS Racing AUX RC light remote controller switch for LTVystore 5mm 5V prewired LED bulbs | CH12 / board output 11 |

RC5 maps the switch positions to both flight mode and the base mount position: low/plane sends `1000us`, middle/transition sends `1500us`, and high/hover sends `2000us` to the mount servos. In `flightmode1`, RC4 controls the rudder servo and RC1 controls the rear engine mounts differentially like ailerons. In `flightmode2`, RC4 controls both the rudder servo and the rear mount yaw tilt. In `flightmode3`, RC4 controls the rear mount yaw tilt while the rudder servo is centered. For rear mount yaw tilt, right rudder drives only the left rear mount away from the RC5 base position, and left rudder drives only the right rear mount away from the RC5 base position; the other rear mount stays at the RC5 base position. If the receiver signal is missing, ESC outputs go to `1000us`, servos center at `1500us`, lights go off, and the mode falls back to `flightmode1`.

Sensor telemetry is lightly smoothed in firmware for steadier display while sitting still. RC channel values are not smoothed before control output, so stick/switch response stays direct.

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
