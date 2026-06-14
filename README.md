# Pico Flight Controller

Raspberry Pi Pico receiver and sensor testbed for a flight-controller-style build.

## Contents

- `main.py` - MicroPython firmware currently focused on reading an R8EF receiver PPM signal on Pico `GP15`.
- `vl53l0x.py` - VL53L0X / UL53LDK distance sensor driver used by earlier sensor builds.
- `ControllerTester/` - Vite + Three.js browser dashboard for Web Serial display of receiver and sensor readings.
- `QMC5883P.pdf` - Compass sensor reference sheet.
- `RPI_PICO-20260406-v1.28.0.uf2` - MicroPython UF2 used for Pico setup.

## Receiver Wiring

```text
R8EF CH2 signal -> Pico GP15
R8EF VCC        -> Pico 3V3
R8EF GND        -> Pico GND
```

The R8EF needs SBUS/PPM mode for CH2 to output a combined PPM stream.

## Browser Viewer

```powershell
cd ControllerTester
npm install
npm run dev -- --port 5173
```

Then open `http://127.0.0.1:5173` in Chrome or Edge and connect to the Pico over Web Serial.
