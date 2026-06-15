# Pico Setup Simulator

This is a local browser simulator for the Pico flight-controller test setup.

It emits the same one-line text shape as `main.py`, for example:

```text
sensor=QMC5883P / HP5883 x=420 y=0 z=0 xuT=0.42 yuT=0.00 zuT=0.00 heading=0.0 tof0=620 tof1=680 tof2=760 tof3=760 tof6=900 adxl=ok ax=0.000 ay=0.000 az=1.000 pitch=0.0 roll=0.0 rc=ppm rc1=1500 rc2=1500 rc3=1500 rc4=1500 rc5=1000 rc6=1500 rc7=1000 rc8=1500
```

Use it to test:

- Wind drift scenarios.
- RC instruction sequences.
- Low-altitude approach behavior.
- TOF, compass, and stale RC failure modes.
- Manual parser testing in `ControllerTester` by copying the generated serial line.
- USB transmitter/game-controller input through the browser Gamepad API.
- USB serial adapters such as CH340 on `COM4` through Web Serial.

## Launch

From PowerShell:

```powershell
.\Start-Simulator.ps1
```

Or double-click:

```text
Start-Simulator.bat
```

The launcher starts at `http://127.0.0.1:5174`. If that port is busy, it picks the next free port and prints the exact URL.

## USB Transmitter Control

Plug in the transmitter, open the simulator from localhost, then click `Use T8FB`.

Browsers only expose gamepads after user interaction. If the status stays on waiting, move a stick, press a transmitter button, or unplug/replug the USB cable while the simulator is open.

Default mapping:

- Axis 0 -> `rc1` yaw.
- Axis 1 -> `rc2` pitch, inverted.
- Axis 2 -> `rc3` throttle, inverted.
- Axis 3 -> `rc4` roll.

The live USB status shows the raw axes and mapped `rc1..rc4` values so the mapping can be adjusted once we see what the T8FB reports on this laptop.

## Serial Adapter Control

If the transmitter cable appears as `USB-SERIAL CH340 (COM4)`, click `Connect COM4` in the simulator and choose that port from the browser picker.

The simulator tries these input shapes:

- Text lines containing `rc1=... rc2=...`.
- Text lines containing at least four PWM-like values from `900` to `2250`.
- FlySky-style iBUS binary frames.
- SBUS binary frames when baud is set to `100000 SBUS 8E2`.

Start with `115200`. If the status only shows changing raw hex bytes and no channel mapping, try `9600`, `57600`, and `100000 SBUS 8E2`.

## Instruction Script

The script box accepts one instruction per line. Values are receiver PWM microseconds unless noted.

```text
scenario=manual throttle=1550 yaw=1500 pitch=1450 roll=1500 wind=0 hold=1.0
scenario=manual throttle=1580 yaw=1500 pitch=1500 roll=1850 wind=45 hold=1.4
scenario=fault tof=err mag=err rc=stale hold=1.0
```

Useful fields:

- `scenario`: `manual`, `drift`, `rc`, `fault`, or `landing`.
- `throttle`: maps to `rc3`.
- `yaw` or `ch1`: maps to `rc1`.
- `pitch` or `ch2`: maps to `rc2`.
- `roll` or `ch4`: maps to `rc4`.
- `wind`: `-100` to `100`, used for drift.
- `hold`: seconds to hold the instruction.
- `tof=err`, `mag=err`, `rc=stale`: simulate fault modes.
