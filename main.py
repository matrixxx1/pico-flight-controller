from machine import I2C, Pin, disable_irq, enable_irq
from time import sleep, ticks_diff, ticks_us
import math

try:
    from vl53l0x import VL53L0X
except ImportError:
    VL53L0X = None


I2C_BUS = 0
SDA_PIN = 0
SCL_PIN = 1
FREQ = 100_000

QMC5883L_ADDR = 0x0D
HMC5883L_ADDR = 0x1E
QMC5883P_ADDR = 0x2C
QMC5883P_ALT_ADDR = 0x0C
TCA9548A_ADDR = 0x70
PCA9685_ADDR = 0x40
VL53L0X_ADDR = 0x29
ADXL345_ADDR = 0x53
MPU6050_ADDR_LOW = 0x68
MPU6050_ADDR_HIGH = 0x69

TOF_CHANNELS = (0, 1, 2, 3, 6)
VL53L1X_CHANNELS = (0, 1, 6)
MAG_CHANNEL = 4
ADXL_CHANNEL = 5
PCA9685_MUX_CHANNEL = 7

PCA_FREQ_HZ = 50
PCA_OSC_HZ = 25_000_000
PULSE_MIN_US = 500
PULSE_MID_US = 1500
PULSE_MAX_US = 2500
PULSE_THROW_US = PULSE_MAX_US - PULSE_MID_US
ESC_MIN_US = 1000
ESC_MAX_US = 2000
RC_THROTTLE_MAX_US = 1600
RC_INPUT_MIN_US = 1000
RC_INPUT_MAX_US = 2000
RC_INPUT_MID_US = 1500
RC_INPUT_THROW_US = 500
RC_INPUT_DEADBAND_US = 6
LIGHT_OFF_US = 1000
LIGHT_ON_US = 2000
LIGHT_SWITCH_US = 1500
CONTROL_MODE_SWITCH_US = 1500
MOUNT_LOW_THRESHOLD_US = 1300
MOUNT_HIGH_THRESHOLD_US = 1700
MOUNT_FLIGHT_US = 1580
MOUNT_HOVER_US = 2250
MOUNT_TRANSITION_US = (MOUNT_FLIGHT_US + MOUNT_HOVER_US) // 2
RUDDER_LEFT_THRESHOLD_US = 1300
RUDDER_RIGHT_THRESHOLD_US = 1700
RUDDER_DEADBAND_US = 40

FLIGHT_MODE_1 = "flightmode1"
FLIGHT_MODE_2 = "flightmode2"
FLIGHT_MODE_3 = "flightmode3"
FLIGHT_MODE_LOW_THRESHOLD_US = 1300
FLIGHT_MODE_HIGH_THRESHOLD_US = 1700

ESC_OUTPUTS = (0, 2, 4, 6)
LEFT_FRONT_ESC_OUTPUT = 0
RIGHT_FRONT_ESC_OUTPUT = 2
LEFT_REAR_ESC_OUTPUT = 4
RIGHT_REAR_ESC_OUTPUT = 6
LEFT_ESC_OUTPUTS = (0, 4)
RIGHT_ESC_OUTPUTS = (2, 6)
FRONT_ESC_OUTPUTS = (0, 2)
REAR_ESC_OUTPUTS = (4, 6)
MOUNT_OUTPUTS = (1, 3, 5, 7)
FRONT_MOUNT_OUTPUTS = (1, 3)
LEFT_REAR_MOUNT_OUTPUT = 5
RIGHT_REAR_MOUNT_OUTPUT = 7
ELEVATOR_OUTPUT = 8
RUDDER_OUTPUT = 9
LIGHT_OUTPUT = 11
HOVER_SIDE_ESC_BOOST_US = 150
PITCH_ESC_BOOST_US = 150
HOVER_PITCH_MOUNT_ADJUST_US = 150
REAR_AILERON_AUTHORITY_PERCENT = 50
TRANSITION_REAR_AILERON_AUTHORITY_PERCENT = 25
TRAINER_GAIN_MIN_PERCENT = 25
TRAINER_GAIN_MAX_PERCENT = 100
CONTROL_MODE_RC = "rc"
CONTROL_MODE_PID = "pid"
LIGHT_MODE_SOLID = 0
LIGHT_MODE_SLOW_BLINK = 1
LIGHT_MODE_FAST_BLINK = 2
LIGHT_PULSE_INTERVAL_US = 250_000
PID_OUTPUT_LIMIT_US = 80
PID_LEVEL_KP = 5.0
PID_LEVEL_KI = 0.02
PID_LEVEL_KD = 0.8
PID_HEADING_KP = 1.4
PID_HEADING_KI = 0.01
PID_HEADING_KD = 0.35
PID_ALTITUDE_KP = 0.18
PID_ALTITUDE_KI = 0.005
PID_ALTITUDE_KD = 0.08
PID_COMMAND_PITCH_DEG = 8.0
PID_COMMAND_ROLL_DEG = 8.0
PID_COMMAND_YAW_DEG = 4.0
PID_COMMAND_ALTITUDE_MM = 20.0

PPM_PIN = 15
RC_CHANNELS = 8
PPM_SYNC_US = 3000
PPM_MIN_US = 750
PPM_MAX_US = 2250
PPM_STALE_US = 250_000

REPORT_INTERVAL_S = 0.10
SENSOR_RETRY_US = 5_000_000
MAG_SMOOTH_ALPHA = 0.18
IMU_SMOOTH_ALPHA = 0.22
TOF_SMOOTH_ALPHA = 0.25

VL53L1X_DEFAULT_CONFIGURATION = bytes([
    0x00, 0x00, 0x00, 0x01, 0x02, 0x00, 0x02, 0x08,
    0x00, 0x08, 0x10, 0x01, 0x01, 0x00, 0x00, 0x00,
    0x00, 0xFF, 0x00, 0x0F, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x20, 0x0B, 0x00, 0x00, 0x02, 0x0A, 0x21,
    0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0xC8,
    0x00, 0x00, 0x38, 0xFF, 0x01, 0x00, 0x08, 0x00,
    0x00, 0x01, 0xDB, 0x0F, 0x01, 0xF1, 0x0D, 0x01,
    0x68, 0x00, 0x80, 0x08, 0xB8, 0x00, 0x00, 0x00,
    0x00, 0x0F, 0x89, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x01, 0x0F, 0x0D, 0x0E, 0x0E, 0x00,
    0x00, 0x02, 0xC7, 0xFF, 0x9B, 0x00, 0x00, 0x00,
    0x01, 0x01, 0x40,
])


def twos_complement(value, bits=16):
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value


def heading_degrees(x, y):
    heading = math.degrees(math.atan2(y, x))
    if heading < 0:
        heading += 360
    return heading


def normalize_degrees(degrees):
    while degrees > 180:
        degrees -= 360
    while degrees < -180:
        degrees += 360
    return degrees


class ExpSmoother:
    def __init__(self, alpha):
        self.alpha = alpha
        self.values = {}

    def reset(self, key=None):
        if key is None:
            self.values = {}
        elif key in self.values:
            del self.values[key]

    def update(self, key, value):
        previous = self.values.get(key)
        if previous is None:
            self.values[key] = value
            return value
        smoothed = previous + self.alpha * (value - previous)
        self.values[key] = smoothed
        return smoothed


def smooth_vector(smoother, prefix, values):
    return tuple(smoother.update("{}{}".format(prefix, index), value) for index, value in enumerate(values))


class PPMReceiver:
    def __init__(self, pin_number, channel_count=RC_CHANNELS):
        self.pin = Pin(pin_number, Pin.IN, Pin.PULL_DOWN)
        self.channel_count = channel_count
        self.channels = [None] * channel_count
        self.index = 0
        self.last_edge_us = ticks_us()
        self.last_frame_us = 0
        self.pin.irq(trigger=Pin.IRQ_RISING, handler=self._on_rising_edge)

    def _on_rising_edge(self, pin):
        now = ticks_us()
        width = ticks_diff(now, self.last_edge_us)
        self.last_edge_us = now

        if width > PPM_SYNC_US:
            self.index = 0
            self.last_frame_us = now
            return

        if PPM_MIN_US <= width <= PPM_MAX_US and self.index < self.channel_count:
            self.channels[self.index] = width
            self.index += 1

    def read(self):
        irq_state = disable_irq()
        values = self.channels[:]
        last_frame_us = self.last_frame_us
        enable_irq(irq_state)
        if last_frame_us == 0 or ticks_diff(ticks_us(), last_frame_us) > PPM_STALE_US:
            return [None] * self.channel_count
        return values


class RCInputFilter:
    def __init__(self, channel_count=RC_CHANNELS, deadband_us=RC_INPUT_DEADBAND_US):
        self.deadband_us = deadband_us
        self.values = [None] * channel_count

    def update(self, channels):
        filtered = []
        for index, value in enumerate(channels):
            previous = self.values[index]
            if value is None:
                self.values[index] = None
                filtered.append(None)
            elif previous is None or abs(value - previous) > self.deadband_us:
                self.values[index] = value
                filtered.append(value)
            else:
                filtered.append(previous)
        return filtered


class LightPatternController:
    def __init__(self):
        self.current_mode = LIGHT_MODE_SOLID
        self.target_mode = None
        self.remaining_steps = 0
        self.output_on = True
        self.last_step_us = ticks_us()

    def set_target(self, target_mode):
        target_mode = int(clamp(target_mode, LIGHT_MODE_SOLID, LIGHT_MODE_FAST_BLINK))
        if self.target_mode == target_mode and self.remaining_steps > 0:
            return
        if self.current_mode == target_mode:
            self.target_mode = target_mode
            return
        cycles = (target_mode - self.current_mode) % 3
        self.remaining_steps = cycles * 2
        self.target_mode = target_mode
        self.last_step_us = ticks_us() - LIGHT_PULSE_INTERVAL_US

    def update(self):
        if self.remaining_steps > 0 and ticks_diff(ticks_us(), self.last_step_us) >= LIGHT_PULSE_INTERVAL_US:
            self.output_on = not self.output_on
            self.remaining_steps -= 1
            self.last_step_us = ticks_us()
            if self.remaining_steps == 0:
                self.output_on = True
                self.current_mode = self.target_mode
        return LIGHT_ON_US if self.output_on else LIGHT_OFF_US

    def label(self):
        if self.current_mode == LIGHT_MODE_FAST_BLINK:
            return "fast"
        if self.current_mode == LIGHT_MODE_SLOW_BLINK:
            return "slow"
        return "solid"


class PIDAxis:
    def __init__(self, kp, ki, kd, output_limit):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limit = output_limit
        self.integral = 0.0
        self.previous_error = 0.0
        self.last_us = None

    def reset(self):
        self.integral = 0.0
        self.previous_error = 0.0
        self.last_us = None

    def update(self, error):
        now = ticks_us()
        if self.last_us is None:
            dt = REPORT_INTERVAL_S
        else:
            dt = max(0.001, ticks_diff(now, self.last_us) / 1_000_000)
        self.last_us = now
        self.integral = clamp(self.integral + error * dt, -self.output_limit, self.output_limit)
        derivative = (error - self.previous_error) / dt
        self.previous_error = error
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return int(clamp(output, -self.output_limit, self.output_limit))


class FlightPIDController:
    def __init__(self):
        self.active = False
        self.flight_mode = None
        self.target_pitch = 0.0
        self.target_roll = 0.0
        self.target_heading = None
        self.target_altitude = None
        self.pitch = PIDAxis(PID_LEVEL_KP, PID_LEVEL_KI, PID_LEVEL_KD, PID_OUTPUT_LIMIT_US)
        self.roll = PIDAxis(PID_LEVEL_KP, PID_LEVEL_KI, PID_LEVEL_KD, PID_OUTPUT_LIMIT_US)
        self.heading = PIDAxis(PID_HEADING_KP, PID_HEADING_KI, PID_HEADING_KD, PID_OUTPUT_LIMIT_US)
        self.altitude = PIDAxis(PID_ALTITUDE_KP, PID_ALTITUDE_KI, PID_ALTITUDE_KD, PID_OUTPUT_LIMIT_US)

    def reset_axes(self):
        self.pitch.reset()
        self.roll.reset()
        self.heading.reset()
        self.altitude.reset()

    def set_mode(self, enabled, flight_mode, sensor_state):
        if not enabled:
            if self.active:
                self.reset_axes()
            self.active = False
            self.flight_mode = None
            return
        if not self.active or self.flight_mode != flight_mode:
            self.active = True
            self.flight_mode = flight_mode
            self.reset_axes()
            pitch = sensor_state.get("pitch")
            roll = sensor_state.get("roll")
            heading = sensor_state.get("heading")
            altitude = sensor_state.get("altitude")
            if flight_mode == FLIGHT_MODE_3:
                self.target_pitch = 0.0
                self.target_roll = 0.0
            else:
                self.target_pitch = pitch if pitch is not None else 0.0
                self.target_roll = roll if roll is not None else 0.0
            self.target_heading = heading
            self.target_altitude = altitude

    def corrections(self, sensor_state, flight_mode, command=None, gain_percent=TRAINER_GAIN_MAX_PERCENT):
        if not self.active:
            return {"pitch": 0, "roll": 0, "yaw": 0, "altitude": 0, "status": "off"}
        command = command or {"pitch": 0, "roll": 0, "yaw": 0, "altitude": 0}
        mode_mix = 1.0
        if flight_mode == FLIGHT_MODE_2:
            mode_mix = 0.5
        gain_mix = clamp(gain_percent, TRAINER_GAIN_MIN_PERCENT, TRAINER_GAIN_MAX_PERCENT) / 100
        pitch = sensor_state.get("pitch")
        roll = sensor_state.get("roll")
        heading = sensor_state.get("heading")
        altitude = sensor_state.get("altitude")
        commanded_pitch = self.target_pitch + command.get("pitch", 0)
        commanded_roll = self.target_roll + command.get("roll", 0)
        pitch_out = self.pitch.update(commanded_pitch - pitch) if pitch is not None else 0
        roll_out = self.roll.update(commanded_roll - roll) if roll is not None else 0
        yaw_out = 0
        if heading is not None and self.target_heading is not None:
            yaw_error = normalize_degrees((self.target_heading + command.get("yaw", 0)) - heading)
            yaw_out = self.heading.update(yaw_error)
        alt_out = 0
        if altitude is not None and self.target_altitude is not None and flight_mode != FLIGHT_MODE_1:
            alt_out = self.altitude.update((self.target_altitude + command.get("altitude", 0)) - altitude)
        status = "hold"
        if pitch is None or roll is None:
            status = "noimu"
        elif heading is None:
            status = "noheading"
        return {
            "pitch": int(pitch_out * mode_mix * gain_mix),
            "roll": int(roll_out * mode_mix * gain_mix),
            "yaw": int(yaw_out * mode_mix * gain_mix),
            "altitude": int(alt_out * mode_mix * gain_mix),
            "status": status,
        }


class QMC5883L:
    name = "QMC5883L"

    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = QMC5883L_ADDR
        self.i2c.writeto_mem(self.addr, 0x0B, bytes([0x01]))
        self.i2c.writeto_mem(self.addr, 0x09, bytes([0x1D]))

    def read(self):
        data = self.i2c.readfrom_mem(self.addr, 0x00, 6)
        x = twos_complement(data[1] << 8 | data[0])
        y = twos_complement(data[3] << 8 | data[2])
        z = twos_complement(data[5] << 8 | data[4])
        return x, y, z


class QMC5883P:
    base_name = "QMC5883P / HP5883"

    def __init__(self, i2c, address=QMC5883P_ADDR):
        self.i2c = i2c
        self.addr = address
        self.name = "{} @0x{:02X}".format(self.base_name, self.addr)
        chip_id = self.i2c.readfrom_mem(self.addr, 0x00, 1)[0]
        if chip_id != 0x80:
            raise RuntimeError("QMC5883P chip ID was 0x{:02x}".format(chip_id))
        self.i2c.writeto_mem(self.addr, 0x0D, bytes([0x40]))
        sleep(0.01)
        self.i2c.writeto_mem(self.addr, 0x29, bytes([0x06]))
        sleep(0.01)
        self.i2c.writeto_mem(self.addr, 0x0A, bytes([0xCF]))
        sleep(0.01)
        self.i2c.writeto_mem(self.addr, 0x0B, bytes([0x00]))
        sleep(0.01)

    def read(self):
        for _ in range(100):
            status = self.i2c.readfrom_mem(self.addr, 0x09, 1)[0]
            if status & 0x01:
                break
            sleep(0.001)
        data = self.i2c.readfrom_mem(self.addr, 0x01, 6)
        x = twos_complement(data[1] << 8 | data[0])
        y = twos_complement(data[3] << 8 | data[2])
        z = twos_complement(data[5] << 8 | data[4])
        return x, y, z

    def raw_to_microtesla(self, value):
        return value / 1000.0


class HMC5883L:
    name = "HMC5883L"

    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = HMC5883L_ADDR
        self.i2c.writeto_mem(self.addr, 0x00, bytes([0x70]))
        self.i2c.writeto_mem(self.addr, 0x01, bytes([0x20]))
        self.i2c.writeto_mem(self.addr, 0x02, bytes([0x00]))

    def read(self):
        data = self.i2c.readfrom_mem(self.addr, 0x03, 6)
        x = twos_complement(data[0] << 8 | data[1])
        z = twos_complement(data[2] << 8 | data[3])
        y = twos_complement(data[4] << 8 | data[5])
        return x, y, z


class TCA9548A:
    def __init__(self, i2c, address=TCA9548A_ADDR):
        self.i2c = i2c
        self.address = address

    def select(self, channel):
        self.i2c.writeto(self.address, bytes([1 << channel]))
        sleep(0.002)

    def disable(self):
        self.i2c.writeto(self.address, b"\x00")
        sleep(0.001)

    def safe_disable(self):
        try:
            self.disable()
        except OSError as exc:
            print("TCA disable failed:", exc)


class PCA9685:
    MODE1 = 0x00
    PRESCALE = 0xFE
    LED0_ON_L = 0x06

    def __init__(self, mux, channel=PCA9685_MUX_CHANNEL, address=PCA9685_ADDR, freq=PCA_FREQ_HZ):
        self.mux = mux
        self.channel = channel
        self.i2c = mux.i2c
        self.address = address
        self.mux.select(channel)
        self.i2c.writeto_mem(self.address, self.MODE1, bytes([0x00]))
        sleep(0.01)
        self.set_pwm_freq(freq)

    def _write(self, register, value):
        self.mux.select(self.channel)
        self.i2c.writeto_mem(self.address, register, bytes([value & 0xFF]))

    def _read(self, register):
        self.mux.select(self.channel)
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def set_pwm_freq(self, freq):
        prescale = int((PCA_OSC_HZ / (4096 * freq)) - 1 + 0.5)
        old_mode = self._read(self.MODE1)
        sleep_mode = (old_mode & 0x7F) | 0x10
        self._write(self.MODE1, sleep_mode)
        self._write(self.PRESCALE, prescale)
        self._write(self.MODE1, old_mode)
        sleep(0.005)
        self._write(self.MODE1, old_mode | 0xA1)

    def set_pwm(self, output, on, off):
        self.mux.select(self.channel)
        register = self.LED0_ON_L + 4 * output
        data = bytes([on & 0xFF, on >> 8, off & 0xFF, off >> 8])
        self.i2c.writeto_mem(self.address, register, data)

    def set_pulse_us(self, output, pulse_us):
        pulse_us = clamp(pulse_us, PULSE_MIN_US, PULSE_MAX_US)
        ticks = int(pulse_us * PCA_FREQ_HZ * 4096 / 1_000_000)
        self.set_pwm(output, 0, ticks)

    def set_on_off(self, output, is_on):
        if is_on:
            self.set_pwm(output, 0x1000, 0)
        else:
            self.set_pwm(output, 0, 0x1000)

    def neutralize(self):
        for output in ESC_OUTPUTS:
            self.set_pulse_us(output, ESC_MIN_US)
        for output in MOUNT_OUTPUTS:
            self.set_pulse_us(output, PULSE_MID_US)
        self.set_pulse_us(ELEVATOR_OUTPUT, PULSE_MID_US)
        self.set_pulse_us(RUDDER_OUTPUT, PULSE_MID_US)
        self.set_pulse_us(LIGHT_OUTPUT, LIGHT_OFF_US)


class MuxedVL53L0X:
    def __init__(self, mux, channel):
        if VL53L0X is None:
            raise RuntimeError("vl53l0x.py is missing from the Pico")
        self.mux = mux
        self.channel = channel
        self.name = "VL53L0X"
        self.mux.select(channel)
        self.sensor = VL53L0X(self.mux.i2c, address=VL53L0X_ADDR, io_timeout_ms=250)

    def read_mm(self):
        self.mux.select(self.channel)
        return self.sensor.range


class MuxedVL53L1X:
    def __init__(self, mux, channel, address=VL53L0X_ADDR):
        self.mux = mux
        self.channel = channel
        self.address = address
        self.name = "VL53L1X"
        self.mux.select(channel)
        self.reset()
        sleep(0.001)
        if self.read_reg16(0x010F) != 0xEACC:
            raise RuntimeError("VL53L1X model ID mismatch")
        self.mux.i2c.writeto_mem(
            self.address,
            0x002D,
            VL53L1X_DEFAULT_CONFIGURATION,
            addrsize=16,
        )
        self.write_reg16(0x001E, self.read_reg16(0x0022) * 4)
        sleep(0.2)

    def write_reg(self, register, value):
        self.mux.select(self.channel)
        self.mux.i2c.writeto_mem(self.address, register, bytes([value & 0xFF]), addrsize=16)

    def write_reg16(self, register, value):
        self.mux.select(self.channel)
        self.mux.i2c.writeto_mem(
            self.address,
            register,
            bytes([(value >> 8) & 0xFF, value & 0xFF]),
            addrsize=16,
        )

    def read_reg16(self, register):
        self.mux.select(self.channel)
        data = self.mux.i2c.readfrom_mem(self.address, register, 2, addrsize=16)
        return (data[0] << 8) | data[1]

    def reset(self):
        self.write_reg(0x0000, 0x00)
        sleep(0.1)
        self.write_reg(0x0000, 0x01)
        sleep(0.1)

    def read_mm(self):
        self.mux.select(self.channel)
        data = self.mux.i2c.readfrom_mem(self.address, 0x0089, 17, addrsize=16)
        value = (data[13] << 8) | data[14]
        self.write_reg(0x0086, 0x01)
        return value


class MuxedMagnetometer:
    def __init__(self, mux, channel, sensor):
        self.mux = mux
        self.channel = channel
        self.sensor = sensor
        self.name = sensor.name

    def read(self):
        self.mux.select(self.channel)
        return self.sensor.read()

    def raw_to_microtesla(self, value):
        return self.sensor.raw_to_microtesla(value)


class ADXL345:
    def __init__(self, i2c, address=ADXL345_ADDR):
        self.i2c = i2c
        self.address = address
        device_id = self.i2c.readfrom_mem(self.address, 0x00, 1)[0]
        if device_id != 0xE5:
            raise RuntimeError("ADXL345 device ID was 0x{:02x}".format(device_id))
        self.i2c.writeto_mem(self.address, 0x31, bytes([0x08]))
        self.i2c.writeto_mem(self.address, 0x2C, bytes([0x0A]))
        self.i2c.writeto_mem(self.address, 0x2D, bytes([0x08]))
        sleep(0.02)

    def read_raw(self):
        data = self.i2c.readfrom_mem(self.address, 0x32, 6)
        x = twos_complement(data[1] << 8 | data[0])
        y = twos_complement(data[3] << 8 | data[2])
        z = twos_complement(data[5] << 8 | data[4])
        return x, y, z

    def read_g(self):
        x, y, z = self.read_raw()
        return x * 0.0039, y * 0.0039, z * 0.0039


class MuxedADXL345:
    def __init__(self, mux, channel):
        self.mux = mux
        self.channel = channel
        self.mux.select(channel)
        self.sensor = ADXL345(self.mux.i2c)

    def read(self):
        self.mux.select(self.channel)
        return self.sensor.read_g()


class MPU6050:
    name = "MPU-6050"

    def __init__(self, i2c, address):
        self.i2c = i2c
        self.address = address
        who_am_i = self.i2c.readfrom_mem(self.address, 0x75, 1)[0]
        if who_am_i not in (0x68, 0x69):
            raise RuntimeError("MPU-6050 WHO_AM_I was 0x{:02x}".format(who_am_i))
        self.i2c.writeto_mem(self.address, 0x6B, bytes([0x00]))
        sleep(0.05)
        self.i2c.writeto_mem(self.address, 0x1A, bytes([0x03]))
        self.i2c.writeto_mem(self.address, 0x1B, bytes([0x00]))
        self.i2c.writeto_mem(self.address, 0x1C, bytes([0x00]))
        sleep(0.02)

    def read_g(self):
        data = self.i2c.readfrom_mem(self.address, 0x3B, 6)
        x = twos_complement(data[0] << 8 | data[1])
        y = twos_complement(data[2] << 8 | data[3])
        z = twos_complement(data[4] << 8 | data[5])
        return x / 16384.0, y / 16384.0, z / 16384.0


class MuxedMPU6050:
    def __init__(self, mux, channel, address):
        self.mux = mux
        self.channel = channel
        self.address = address
        self.mux.select(channel)
        self.sensor = MPU6050(self.mux.i2c, address)
        self.name = self.sensor.name

    def read(self):
        self.mux.select(self.channel)
        return self.sensor.read_g()


def create_magnetometer(i2c, devices):
    if QMC5883L_ADDR in devices:
        return QMC5883L(i2c)
    if HMC5883L_ADDR in devices:
        return HMC5883L(i2c)
    if QMC5883P_ADDR in devices:
        return QMC5883P(i2c, QMC5883P_ADDR)
    if QMC5883P_ALT_ADDR in devices:
        return QMC5883P(i2c, QMC5883P_ALT_ADDR)
    return None


def find_mux(i2c):
    devices = i2c.scan()
    print("Root I2C devices:", [hex(device) for device in devices])
    if TCA9548A_ADDR not in devices:
        print("No HW-617/TCA9548A detected at 0x70.")
        return None
    return TCA9548A(i2c)


def find_muxed_sensor(i2c, mux):
    try:
        mux.select(MAG_CHANNEL)
        sensor = create_magnetometer(i2c, i2c.scan())
        mux.safe_disable()
        if sensor is None:
            return None
        return MuxedMagnetometer(mux, MAG_CHANNEL, sensor)
    except Exception as exc:
        print("GY-271 channel {} init failed: {}".format(MAG_CHANNEL, exc))
        mux.safe_disable()
        return None


def find_tof_sensors(i2c, mux):
    sensors = []
    for channel in TOF_CHANNELS:
        try:
            mux.select(channel)
            devices = i2c.scan()
            print("TCA channel {} devices: {}".format(channel, [hex(device) for device in devices]))
            if VL53L0X_ADDR in devices:
                if channel in VL53L1X_CHANNELS:
                    sensor = MuxedVL53L1X(mux, channel)
                else:
                    sensor = MuxedVL53L0X(mux, channel)
                sensors.append((channel, sensor))
                print("Detected {} on TCA channel {}".format(sensor.name, channel))
            else:
                sensors.append((channel, None))
        except Exception as exc:
            sensors.append((channel, None))
            print("TOF channel {} init failed: {}".format(channel, exc))
    mux.safe_disable()
    return sensors


def find_motion_sensor(i2c, mux):
    try:
        mux.select(ADXL_CHANNEL)
        devices = i2c.scan()
        print("IMU channel {} devices: {}".format(ADXL_CHANNEL, [hex(device) for device in devices]))
        if MPU6050_ADDR_LOW in devices:
            imu = MuxedMPU6050(mux, ADXL_CHANNEL, MPU6050_ADDR_LOW)
            mux.safe_disable()
            print("Detected MPU-6050 on TCA channel {} at 0x68".format(ADXL_CHANNEL))
            return imu
        if MPU6050_ADDR_HIGH in devices:
            imu = MuxedMPU6050(mux, ADXL_CHANNEL, MPU6050_ADDR_HIGH)
            mux.safe_disable()
            print("Detected MPU-6050 on TCA channel {} at 0x69".format(ADXL_CHANNEL))
            return imu
        if ADXL345_ADDR not in devices:
            mux.safe_disable()
            return None
        accel = MuxedADXL345(mux, ADXL_CHANNEL)
        mux.safe_disable()
        print("Detected ADXL345 on TCA channel {}".format(ADXL_CHANNEL))
        return accel
    except Exception as exc:
        print("IMU channel {} init failed: {}".format(ADXL_CHANNEL, exc))
        mux.safe_disable()
        return None


def read_tof(tof_sensors, smoother):
    fields = []
    values = {}
    for channel, tof in tof_sensors:
        value = "None"
        numeric_value = None
        if tof is not None:
            try:
                numeric_value = int(smoother.update(channel, tof.read_mm()))
                value = str(numeric_value)
            except Exception:
                smoother.reset(channel)
                value = "err"
        sensor_type = tof.name if tof is not None else "None"
        values[channel] = numeric_value
        fields.append("tof{}={}".format(channel, value))
        fields.append("toftype{}={}".format(channel, sensor_type))
    return " ".join(fields), values


def read_motion(imu, smoother):
    if imu is None:
        smoother.reset()
        return "imu=None adxl=None ax=0.000 ay=0.000 az=0.000 pitch=0.0 roll=0.0", {
            "present": False,
            "ax": None,
            "ay": None,
            "az": None,
            "pitch": None,
            "roll": None,
        }
    try:
        ax, ay, az = smooth_vector(smoother, "imu", imu.read())
        pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
        roll = math.degrees(math.atan2(ay, az))
        return "imu={} adxl=ok ax={:.3f} ay={:.3f} az={:.3f} pitch={:.1f} roll={:.1f}".format(
            imu.name, ax, ay, az, pitch, roll
        ), {"present": True, "ax": ax, "ay": ay, "az": az, "pitch": pitch, "roll": roll}
    except Exception as exc:
        smoother.reset()
        return "imu=err adxl=err ax=0.000 ay=0.000 az=0.000 pitch=0.0 roll=0.0 imuerr={}".format(exc), {
            "present": False,
            "ax": None,
            "ay": None,
            "az": None,
            "pitch": None,
            "roll": None,
        }


def clamp(value, low, high):
    return max(low, min(high, value))


def map_range(value, in_low, in_high, out_low, out_high):
    return out_low + ((value - in_low) * (out_high - out_low)) / (in_high - in_low)


def rc_pulse_to_servo(value):
    if value is None:
        return PULSE_MID_US
    value = clamp(value, RC_INPUT_MIN_US, RC_INPUT_MAX_US)
    return int(map_range(value, RC_INPUT_MIN_US, RC_INPUT_MAX_US, PULSE_MIN_US, PULSE_MAX_US))


def scale_from_mid(value, gain_percent):
    return int(PULSE_MID_US + ((value - PULSE_MID_US) * gain_percent) / 100)


def rc_pulse_to_esc(value, gain_percent=TRAINER_GAIN_MAX_PERCENT):
    if value is None:
        return ESC_MIN_US
    value = clamp(value, RC_INPUT_MIN_US, RC_THROTTLE_MAX_US)
    return int(ESC_MIN_US + ((value - ESC_MIN_US) * gain_percent) / 100)


def rc_gain_percent(value):
    if value is None:
        return TRAINER_GAIN_MAX_PERCENT
    value = clamp(value, RC_INPUT_MIN_US, RC_INPUT_MAX_US)
    return int(map_range(
        value,
        RC_INPUT_MIN_US,
        RC_INPUT_MAX_US,
        TRAINER_GAIN_MIN_PERCENT,
        TRAINER_GAIN_MAX_PERCENT,
    ))


def rc_switch_to_mount(value):
    if value is None:
        return MOUNT_FLIGHT_US
    if value < MOUNT_LOW_THRESHOLD_US:
        return MOUNT_FLIGHT_US
    if value > MOUNT_HIGH_THRESHOLD_US:
        return MOUNT_HOVER_US
    return MOUNT_TRANSITION_US


def rc_switch_to_flight_mode(value):
    if value is None or value < FLIGHT_MODE_LOW_THRESHOLD_US:
        return FLIGHT_MODE_1, "plane"
    if value > FLIGHT_MODE_HIGH_THRESHOLD_US:
        return FLIGHT_MODE_3, "hover"
    return FLIGHT_MODE_2, "transition"


def rc_stick_offset(value, gain_percent=TRAINER_GAIN_MAX_PERCENT):
    value = rc_pulse_to_servo(value)
    offset = clamp(value - PULSE_MID_US, -PULSE_THROW_US, PULSE_THROW_US)
    offset = int((offset * gain_percent) / 100)
    deadband = int((RUDDER_DEADBAND_US * PULSE_THROW_US) / RC_INPUT_THROW_US)
    if abs(offset) <= deadband:
        return 0
    return offset


def rear_yaw_mount_delta(base, rudder_offset, yaw_limit=None):
    amount = min(abs(rudder_offset), PULSE_THROW_US)
    deadband = int((RUDDER_DEADBAND_US * PULSE_THROW_US) / RC_INPUT_THROW_US)
    if amount <= deadband:
        return 0
    if base > PULSE_MID_US:
        target = PULSE_MIN_US if yaw_limit is None else yaw_limit
    else:
        target = PULSE_MAX_US if yaw_limit is None else yaw_limit
    return int((target - base) * (amount / PULSE_THROW_US))


def rear_mount_values(base, aileron_offset=0, rudder_offset=0, yaw_limit=None):
    aileron_offset = clamp(aileron_offset, -PULSE_THROW_US, PULSE_THROW_US)
    left = base + aileron_offset
    right = base - aileron_offset
    yaw_delta = rear_yaw_mount_delta(base, rudder_offset, yaw_limit)
    if rudder_offset > 0:
        left += yaw_delta
    elif rudder_offset < 0:
        right += yaw_delta
    left = int(clamp(left, PULSE_MIN_US, PULSE_MAX_US))
    right = int(clamp(right, PULSE_MIN_US, PULSE_MAX_US))
    return left, right


def scale_rear_aileron_offset(offset, authority_percent=REAR_AILERON_AUTHORITY_PERCENT):
    return int((offset * authority_percent) / 100)


def add_esc_boost(esc_speeds, outputs, boost):
    if boost <= 0:
        return
    for output in outputs:
        esc_speeds[output] = int(clamp(esc_speeds[output] + boost, ESC_MIN_US, RC_THROTTLE_MAX_US))


def stick_boost(offset, max_boost=PITCH_ESC_BOOST_US):
    return int((min(abs(offset), PULSE_THROW_US) * max_boost) / PULSE_THROW_US)


def apply_rc_outputs(controller, channels, sensor_state=None, pid_controller=None, light_controller=None):
    sensor_state = sensor_state or {}
    flight_mode, flight_label = rc_switch_to_flight_mode(channels[4])
    gain_percent = rc_gain_percent(channels[7])
    control_mode = CONTROL_MODE_PID if channels[6] is not None and channels[6] >= CONTROL_MODE_SWITCH_US else CONTROL_MODE_RC
    pid = {"pitch": 0, "roll": 0, "yaw": 0, "altitude": 0, "status": "off"}
    target_light_mode = LIGHT_MODE_FAST_BLINK if control_mode == CONTROL_MODE_PID else LIGHT_MODE_SLOW_BLINK
    light = LIGHT_ON_US
    light_mode = "pending"
    if controller is None:
        if pid_controller is not None:
            temp_right_stick_lr_offset = rc_stick_offset(channels[0], gain_percent)
            temp_right_stick_ud_offset = rc_stick_offset(channels[1], gain_percent)
            temp_left_stick_lr_offset = rc_stick_offset(channels[3], gain_percent)
            pid_controller.set_mode(control_mode == CONTROL_MODE_PID, flight_mode, sensor_state)
            temp_command = {
                "pitch": (temp_right_stick_ud_offset * PID_COMMAND_PITCH_DEG) / PULSE_THROW_US,
                "roll": (temp_right_stick_lr_offset * PID_COMMAND_ROLL_DEG) / PULSE_THROW_US,
                "yaw": (temp_left_stick_lr_offset * PID_COMMAND_YAW_DEG) / PULSE_THROW_US,
                "altitude": (channels[2] - RC_INPUT_MID_US) * PID_COMMAND_ALTITUDE_MM / RC_INPUT_THROW_US
                if channels[2] is not None else 0,
            }
            pid = pid_controller.corrections(sensor_state, flight_mode, temp_command, gain_percent)
        return "pca=None flightmode={} flight={} control={} gain={} pidstatus={} lightmode={} light={}".format(
            flight_mode, flight_label, control_mode, gain_percent, pid["status"], light_mode, light
        )
    if light_controller is not None:
        light_controller.set_target(target_light_mode)
        light = light_controller.update()
        light_mode = light_controller.label()
    else:
        light = LIGHT_ON_US if control_mode == CONTROL_MODE_PID else LIGHT_OFF_US
        light_mode = "direct"

    speed = rc_pulse_to_esc(channels[2], gain_percent)
    elevator = scale_from_mid(rc_pulse_to_servo(channels[1]), gain_percent)
    rudder = scale_from_mid(rc_pulse_to_servo(channels[3]), gain_percent)
    right_stick_lr_offset = rc_stick_offset(channels[0], gain_percent)
    right_stick_ud_offset = rc_stick_offset(channels[1], gain_percent)
    left_stick_lr_offset = rc_stick_offset(channels[3], gain_percent)
    mount = scale_from_mid(rc_switch_to_mount(channels[4]), gain_percent)
    if pid_controller is not None:
        pid_controller.set_mode(control_mode == CONTROL_MODE_PID, flight_mode, sensor_state)
        command = {
            "pitch": (right_stick_ud_offset * PID_COMMAND_PITCH_DEG) / PULSE_THROW_US,
            "roll": (right_stick_lr_offset * PID_COMMAND_ROLL_DEG) / PULSE_THROW_US,
            "yaw": (left_stick_lr_offset * PID_COMMAND_YAW_DEG) / PULSE_THROW_US,
            "altitude": (channels[2] - RC_INPUT_MID_US) * PID_COMMAND_ALTITUDE_MM / RC_INPUT_THROW_US
            if channels[2] is not None else 0,
        }
        pid = pid_controller.corrections(sensor_state, flight_mode, command, gain_percent)
    esc_speeds = [ESC_MIN_US] * 16
    for output in ESC_OUTPUTS:
        esc_speeds[output] = speed
    front_mount = mount
    left_rear_mount = mount
    right_rear_mount = mount
    elevator_output = elevator
    rudder_output = rudder
    elevator_control = flight_mode in (FLIGHT_MODE_1, FLIGHT_MODE_2)
    rudder_control = flight_mode in (FLIGHT_MODE_1, FLIGHT_MODE_2)
    rear_mount_control = flight_mode in (FLIGHT_MODE_1, FLIGHT_MODE_2, FLIGHT_MODE_3)
    rear_aileron_control = flight_mode in (FLIGHT_MODE_1, FLIGHT_MODE_2, FLIGHT_MODE_3)
    rear_yaw_control = flight_mode in (FLIGHT_MODE_2, FLIGHT_MODE_3)
    rear_mount_base = mount
    rear_aileron_offset = scale_rear_aileron_offset(right_stick_lr_offset)
    rear_yaw_offset = 0
    rear_yaw_limit = None
    hover_pitch_boost = 0
    hover_mount_pitch_offset = 0
    transition_front_boost = 0
    if flight_mode == FLIGHT_MODE_2:
        rear_aileron_offset = scale_rear_aileron_offset(
            right_stick_lr_offset,
            TRANSITION_REAR_AILERON_AUTHORITY_PERCENT,
        )
        rear_yaw_offset = left_stick_lr_offset
        rear_yaw_limit = MOUNT_FLIGHT_US
        transition_front_boost = stick_boost(right_stick_ud_offset)
        add_esc_boost(esc_speeds, FRONT_ESC_OUTPUTS, transition_front_boost)
    elif flight_mode == FLIGHT_MODE_3:
        rear_aileron_offset = 0
        rear_yaw_offset = left_stick_lr_offset
        rear_yaw_limit = MOUNT_FLIGHT_US
        hover_pitch_boost = stick_boost(right_stick_ud_offset)
        hover_mount_pitch_offset = int((min(abs(right_stick_ud_offset), PULSE_THROW_US) * HOVER_PITCH_MOUNT_ADJUST_US) / PULSE_THROW_US)
        if right_stick_ud_offset > 0:
            add_esc_boost(esc_speeds, REAR_ESC_OUTPUTS, hover_pitch_boost)
        elif right_stick_ud_offset < 0:
            add_esc_boost(esc_speeds, FRONT_ESC_OUTPUTS, hover_pitch_boost)
            front_mount = int(clamp(front_mount - hover_mount_pitch_offset, PULSE_MIN_US, PULSE_MAX_US))

    left_rear_mount, right_rear_mount = rear_mount_values(
        rear_mount_base, rear_aileron_offset, rear_yaw_offset, rear_yaw_limit
    )
    hover_side_boost = 0
    if flight_mode == FLIGHT_MODE_3:
        hover_side_boost = stick_boost(right_stick_lr_offset, HOVER_SIDE_ESC_BOOST_US)
        if right_stick_lr_offset > 0:
            add_esc_boost(esc_speeds, LEFT_ESC_OUTPUTS, hover_side_boost)
        elif right_stick_lr_offset < 0:
            add_esc_boost(esc_speeds, RIGHT_ESC_OUTPUTS, hover_side_boost)
        if right_stick_ud_offset > 0:
            left_rear_mount = int(clamp(left_rear_mount - hover_mount_pitch_offset, PULSE_MIN_US, PULSE_MAX_US))
            right_rear_mount = int(clamp(right_rear_mount - hover_mount_pitch_offset, PULSE_MIN_US, PULSE_MAX_US))
    if control_mode == CONTROL_MODE_PID:
        altitude_correction = pid["altitude"] if flight_mode != FLIGHT_MODE_1 else 0
        for output in ESC_OUTPUTS:
            esc_speeds[output] = int(clamp(esc_speeds[output] + altitude_correction, ESC_MIN_US, RC_THROTTLE_MAX_US))
        if flight_mode in (FLIGHT_MODE_1, FLIGHT_MODE_2):
            elevator_output = int(clamp(elevator_output + pid["pitch"], PULSE_MIN_US, PULSE_MAX_US))
            rudder_output = int(clamp(rudder_output + pid["yaw"], PULSE_MIN_US, PULSE_MAX_US))
            left_rear_mount = int(clamp(left_rear_mount + pid["roll"], PULSE_MIN_US, PULSE_MAX_US))
            right_rear_mount = int(clamp(right_rear_mount - pid["roll"], PULSE_MIN_US, PULSE_MAX_US))
        if flight_mode in (FLIGHT_MODE_2, FLIGHT_MODE_3):
            if pid["pitch"] > 0:
                add_esc_boost(esc_speeds, REAR_ESC_OUTPUTS, abs(pid["pitch"]))
            elif pid["pitch"] < 0:
                add_esc_boost(esc_speeds, FRONT_ESC_OUTPUTS, abs(pid["pitch"]))
            if pid["roll"] > 0:
                add_esc_boost(esc_speeds, LEFT_ESC_OUTPUTS, abs(pid["roll"]))
            elif pid["roll"] < 0:
                add_esc_boost(esc_speeds, RIGHT_ESC_OUTPUTS, abs(pid["roll"]))
            if pid["yaw"] > 0:
                left_rear_mount = int(clamp(left_rear_mount - abs(pid["yaw"]), PULSE_MIN_US, PULSE_MAX_US))
            elif pid["yaw"] < 0:
                right_rear_mount = int(clamp(right_rear_mount - abs(pid["yaw"]), PULSE_MIN_US, PULSE_MAX_US))
    if not rudder_control:
        rudder_output = PULSE_MID_US
    if not elevator_control:
        elevator_output = PULSE_MID_US

    try:
        for output in ESC_OUTPUTS:
            controller.set_pulse_us(output, esc_speeds[output])
        for output in FRONT_MOUNT_OUTPUTS:
            controller.set_pulse_us(output, front_mount)
        controller.set_pulse_us(LEFT_REAR_MOUNT_OUTPUT, left_rear_mount)
        controller.set_pulse_us(RIGHT_REAR_MOUNT_OUTPUT, right_rear_mount)
        controller.set_pulse_us(ELEVATOR_OUTPUT, elevator_output)
        controller.set_pulse_us(RUDDER_OUTPUT, rudder_output)
        controller.set_pulse_us(LIGHT_OUTPUT, light)
        return "pca=ok flightmode={} flight={} control={} gain={} esc={} lfesc={} rfesc={} lresc={} rresc={} hoverboost={} pitchboost={} transfrontboost={} mount={} frontmount={} leftrear={} rightrear={} elevator={} elevatorout={} rudder={} rudderout={} rightsticklr={} rightstickud={} leftsticklr={} aileronmix={} yawmix={} pitchmount={} pidstatus={} pidpitch={} pidroll={} pidyaw={} pidalt={} elevatorctrl={} rudderctrl={} rearctrl={} aileronctrl={} yawctrl={} lightmode={} light={}".format(
            flight_mode,
            flight_label,
            control_mode,
            gain_percent,
            speed,
            esc_speeds[LEFT_FRONT_ESC_OUTPUT],
            esc_speeds[RIGHT_FRONT_ESC_OUTPUT],
            esc_speeds[LEFT_REAR_ESC_OUTPUT],
            esc_speeds[RIGHT_REAR_ESC_OUTPUT],
            hover_side_boost,
            hover_pitch_boost,
            transition_front_boost,
            mount,
            front_mount,
            left_rear_mount,
            right_rear_mount,
            elevator,
            elevator_output,
            rudder,
            rudder_output,
            right_stick_lr_offset,
            right_stick_ud_offset,
            left_stick_lr_offset,
            rear_aileron_offset,
            rear_yaw_offset,
            hover_mount_pitch_offset,
            pid["status"],
            pid["pitch"],
            pid["roll"],
            pid["yaw"],
            pid["altitude"],
            "on" if elevator_control else "off",
            "on" if rudder_control else "off",
            "on" if rear_mount_control else "off",
            "on" if rear_aileron_control else "off",
            "on" if rear_yaw_control else "off",
            light_mode,
            light,
        )
    except Exception as exc:
        return "pca=err flightmode={} flight={} control={} gain={} pidstatus={} pcaerr={}".format(
            flight_mode, flight_label, control_mode, gain_percent, pid["status"], exc
        )


def find_servo_controller(mux):
    try:
        mux.select(PCA9685_MUX_CHANNEL)
        devices = mux.i2c.scan()
        print("PCA9685 channel {} devices: {}".format(PCA9685_MUX_CHANNEL, [hex(device) for device in devices]))
        if PCA9685_ADDR not in devices:
            mux.safe_disable()
            return None
        controller = PCA9685(mux)
        controller.neutralize()
        mux.safe_disable()
        print("Detected PCA9685 on TCA channel {} at 0x{:02X}".format(PCA9685_MUX_CHANNEL, PCA9685_ADDR))
        return controller
    except Exception as exc:
        print("PCA9685 channel {} init failed: {}".format(PCA9685_MUX_CHANNEL, exc))
        mux.safe_disable()
        return None


def read_rc_fields(receiver):
    fields = []
    for index, value in enumerate(receiver.read(), start=1):
        fields.append("rc{}={}".format(index, "None" if value is None else value))
    return "rc=ppm " + " ".join(fields)


def main():
    receiver = PPMReceiver(PPM_PIN)
    rc_filter = RCInputFilter()
    i2c = None
    mux = None
    sensor = None
    tof_sensors = [(channel, None) for channel in TOF_CHANNELS]
    imu = None
    servo_controller = None
    pid_controller = FlightPIDController()
    light_controller = LightPatternController()
    mag_smoother = ExpSmoother(MAG_SMOOTH_ALPHA)
    imu_smoother = ExpSmoother(IMU_SMOOTH_ALPHA)
    tof_smoother = ExpSmoother(TOF_SMOOTH_ALPHA)
    last_retry = ticks_us()
    last_servo_retry = ticks_us()

    print("Pico flight sensor + R8EF receiver controller")
    print("Root I2C: Pico GP0=SDA, GP1=SCL to HW-617 SDA/SCL")
    print("R8EF CH2 PPM signal -> Pico GP{}".format(PPM_PIN))
    print("PCA9685 on HW-617 channel {}: RC5 low=flightmode1 plane, mid=flightmode2 transition, high=flightmode3 hover".format(PCA9685_MUX_CHANNEL))

    while True:
        now = ticks_us()
        if i2c is None and ticks_diff(now, last_retry) > SENSOR_RETRY_US:
            sda_high = Pin(SDA_PIN, Pin.IN, Pin.PULL_UP).value()
            scl_high = Pin(SCL_PIN, Pin.IN, Pin.PULL_UP).value()
            last_retry = now
            if sda_high and scl_high:
                try:
                    i2c = I2C(I2C_BUS, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=FREQ)
                    mux = find_mux(i2c)
                    if mux is not None:
                        tof_sensors = find_tof_sensors(i2c, mux)
                        imu = find_motion_sensor(i2c, mux)
                        servo_controller = find_servo_controller(mux)
                except Exception as exc:
                    print("I2C init failed:", exc)
                    i2c = None
                    mux = None
            else:
                print("I2C bus held low: SDA={} SCL={}. Check HW-617/sensor wiring.".format(sda_high, scl_high))

        if i2c is not None and mux is None and ticks_diff(now, last_retry) > SENSOR_RETRY_US:
            try:
                mux = find_mux(i2c)
            except Exception as exc:
                print("I2C mux scan failed:", exc)
                mux = None
            last_retry = now

        if mux is not None and sensor is None and ticks_diff(now, last_retry) > SENSOR_RETRY_US:
            sensor = find_muxed_sensor(i2c, mux)
            last_retry = now
            if sensor is not None:
                print("Detected {} on HW-617 channel {}".format(sensor.name, MAG_CHANNEL))

        if mux is not None and servo_controller is None and ticks_diff(now, last_servo_retry) > SENSOR_RETRY_US:
            servo_controller = find_servo_controller(mux)
            last_servo_retry = now

        rc_channels = rc_filter.update(receiver.read())
        tof_fields, tof_values = read_tof(tof_sensors, tof_smoother)
        motion_fields, motion_values = read_motion(imu, imu_smoother)
        rc_fields = "rc=ppm " + " ".join(
            "rc{}={}".format(index, "None" if value is None else value)
            for index, value in enumerate(rc_channels, start=1)
        )
        sensor_name = "Receiver / waiting"
        mag_fields = "x=0 y=0 z=0 heading=0.0"
        heading = None
        mag_error = ""

        if sensor is not None:
            try:
                x, y, z = smooth_vector(mag_smoother, "mag", sensor.read())
                heading = heading_degrees(x, y)
                sensor_name = sensor.name
                if hasattr(sensor, "raw_to_microtesla"):
                    xu = sensor.raw_to_microtesla(x)
                    yu = sensor.raw_to_microtesla(y)
                    zu = sensor.raw_to_microtesla(z)
                    mag_fields = "x={} y={} z={} xuT={:.2f} yuT={:.2f} zuT={:.2f} heading={:.1f}".format(
                        x, y, z, xu, yu, zu, heading
                    )
                else:
                    mag_fields = "x={} y={} z={} heading={:.1f}".format(x, y, z, heading)
            except OSError as exc:
                mag_smoother.reset()
                sensor_name = sensor.name
                mag_error = " magerr={}".format(exc)
                sensor = None
        sensor_state = {
            "pitch": motion_values.get("pitch"),
            "roll": motion_values.get("roll"),
            "heading": heading,
            "altitude": tof_values.get(0),
        }
        pca_fields = apply_rc_outputs(
            servo_controller,
            rc_channels,
            sensor_state,
            pid_controller,
            light_controller,
        )
        print(
            "sensor={} {} {} {} {} {}{}".format(
                sensor_name, mag_fields, tof_fields, motion_fields, rc_fields, pca_fields, mag_error
            )
        )
        sleep(REPORT_INTERVAL_S)


main()
