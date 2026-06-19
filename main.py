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
MAG_CHANNEL = 4
ADXL_CHANNEL = 5
PCA9685_MUX_CHANNEL = 7

PCA_FREQ_HZ = 50
PCA_OSC_HZ = 25_000_000
PULSE_MIN_US = 1000
PULSE_MID_US = 1500
PULSE_MAX_US = 2000
RC_INPUT_MIN_US = 1000
RC_INPUT_MAX_US = 2000
LIGHT_SWITCH_US = 1500
MOUNT_LOW_THRESHOLD_US = 1300
MOUNT_HIGH_THRESHOLD_US = 1700
RUDDER_LEFT_THRESHOLD_US = 1300
RUDDER_RIGHT_THRESHOLD_US = 1700
RUDDER_DEADBAND_US = 40

FLIGHT_MODE_1 = "flightmode1"
FLIGHT_MODE_2 = "flightmode2"
FLIGHT_MODE_3 = "flightmode3"
FLIGHT_MODE_LOW_THRESHOLD_US = 1300
FLIGHT_MODE_HIGH_THRESHOLD_US = 1700

ESC_OUTPUTS = (0, 2, 4, 6)
MOUNT_OUTPUTS = (1, 3, 5, 7)
FRONT_MOUNT_OUTPUTS = (1, 3)
LEFT_REAR_MOUNT_OUTPUT = 5
RIGHT_REAR_MOUNT_OUTPUT = 7
ELEVATOR_OUTPUT = 8
RUDDER_OUTPUT = 9
LIGHT_OUTPUT = 11

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


def twos_complement(value, bits=16):
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value


def heading_degrees(x, y):
    heading = math.degrees(math.atan2(y, x))
    if heading < 0:
        heading += 360
    return heading


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
            self.set_pulse_us(output, PULSE_MIN_US)
        for output in MOUNT_OUTPUTS:
            self.set_pulse_us(output, PULSE_MID_US)
        self.set_pulse_us(ELEVATOR_OUTPUT, PULSE_MID_US)
        self.set_pulse_us(RUDDER_OUTPUT, PULSE_MID_US)
        self.set_pulse_us(LIGHT_OUTPUT, PULSE_MIN_US)


class MuxedVL53L0X:
    def __init__(self, mux, channel):
        if VL53L0X is None:
            raise RuntimeError("vl53l0x.py is missing from the Pico")
        self.mux = mux
        self.channel = channel
        self.mux.select(channel)
        self.sensor = VL53L0X(self.mux.i2c, address=VL53L0X_ADDR, io_timeout_ms=250)

    def read_mm(self):
        self.mux.select(self.channel)
        return self.sensor.range


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
                sensors.append((channel, MuxedVL53L0X(mux, channel)))
                print("Detected VL53L0X on TCA channel {}".format(channel))
            else:
                sensors.append((channel, None))
        except Exception as exc:
            sensors.append((channel, None))
            print("VL53L0X channel {} init failed: {}".format(channel, exc))
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


def read_tof_fields(tof_sensors, smoother):
    fields = []
    for channel, tof in tof_sensors:
        value = "None"
        if tof is not None:
            try:
                value = str(int(smoother.update(channel, tof.read_mm())))
            except Exception:
                smoother.reset(channel)
                value = "err"
        fields.append("tof{}={}".format(channel, value))
    return " ".join(fields)


def read_motion_fields(imu, smoother):
    if imu is None:
        smoother.reset()
        return "imu=None adxl=None ax=0.000 ay=0.000 az=0.000 pitch=0.0 roll=0.0"
    try:
        ax, ay, az = smooth_vector(smoother, "imu", imu.read())
        pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
        roll = math.degrees(math.atan2(ay, az))
        return "imu={} adxl=ok ax={:.3f} ay={:.3f} az={:.3f} pitch={:.1f} roll={:.1f}".format(
            imu.name, ax, ay, az, pitch, roll
        )
    except Exception as exc:
        smoother.reset()
        return "imu=err adxl=err ax=0.000 ay=0.000 az=0.000 pitch=0.0 roll=0.0 imuerr={}".format(exc)


def clamp(value, low, high):
    return max(low, min(high, value))


def rc_pulse_to_servo(value):
    if value is None:
        return PULSE_MID_US
    return int(clamp(value, RC_INPUT_MIN_US, RC_INPUT_MAX_US))


def rc_pulse_to_esc(value):
    if value is None:
        return PULSE_MIN_US
    return int(clamp(value, RC_INPUT_MIN_US, RC_INPUT_MAX_US))


def rc_switch_to_mount(value):
    if value is None:
        return PULSE_MID_US
    if value < MOUNT_LOW_THRESHOLD_US:
        return PULSE_MIN_US
    if value > MOUNT_HIGH_THRESHOLD_US:
        return PULSE_MAX_US
    return PULSE_MID_US


def rc_switch_to_flight_mode(value):
    if value is None or value < FLIGHT_MODE_LOW_THRESHOLD_US:
        return FLIGHT_MODE_1, "plane"
    if value > FLIGHT_MODE_HIGH_THRESHOLD_US:
        return FLIGHT_MODE_3, "hover"
    return FLIGHT_MODE_2, "transition"


def rear_yaw_mount_value(base, rudder):
    amount = min(abs(rudder - PULSE_MID_US), 500)
    if amount <= RUDDER_DEADBAND_US:
        return base
    if base > PULSE_MID_US:
        target = PULSE_MIN_US
    else:
        target = PULSE_MAX_US
    return int(base + (target - base) * (amount / 500))


def rear_aileron_mount_values(channel_value):
    value = rc_pulse_to_servo(channel_value)
    offset = clamp(value - PULSE_MID_US, -500, 500)
    if abs(offset) <= RUDDER_DEADBAND_US:
        return PULSE_MID_US, PULSE_MID_US
    left = int(clamp(PULSE_MID_US + offset, PULSE_MIN_US, PULSE_MAX_US))
    right = int(clamp(PULSE_MID_US - offset, PULSE_MIN_US, PULSE_MAX_US))
    return left, right


def apply_rc_outputs(controller, channels):
    flight_mode, flight_label = rc_switch_to_flight_mode(channels[4])
    if controller is None:
        return "pca=None flightmode={} flight={}".format(flight_mode, flight_label)

    speed = rc_pulse_to_esc(channels[2])
    elevator = rc_pulse_to_servo(channels[1])
    rudder = rc_pulse_to_servo(channels[3])
    mount = rc_switch_to_mount(channels[4])
    lights_on = channels[6] is not None and channels[6] >= LIGHT_SWITCH_US
    light = PULSE_MAX_US if lights_on else PULSE_MIN_US
    front_mount = mount
    left_rear_mount = mount
    right_rear_mount = mount
    rudder_output = rudder
    rudder_control = flight_mode in (FLIGHT_MODE_1, FLIGHT_MODE_2)
    rear_mount_control = flight_mode in (FLIGHT_MODE_2, FLIGHT_MODE_3)
    rear_aileron_control = flight_mode == FLIGHT_MODE_1

    if rear_aileron_control:
        left_rear_mount, right_rear_mount = rear_aileron_mount_values(channels[0])
    elif rear_mount_control:
        if rudder > PULSE_MID_US + RUDDER_DEADBAND_US:
            left_rear_mount = rear_yaw_mount_value(mount, rudder)
        elif rudder < PULSE_MID_US - RUDDER_DEADBAND_US:
            right_rear_mount = rear_yaw_mount_value(mount, rudder)
    if not rudder_control:
        rudder_output = PULSE_MID_US

    try:
        for output in ESC_OUTPUTS:
            controller.set_pulse_us(output, speed)
        for output in FRONT_MOUNT_OUTPUTS:
            controller.set_pulse_us(output, front_mount)
        controller.set_pulse_us(LEFT_REAR_MOUNT_OUTPUT, left_rear_mount)
        controller.set_pulse_us(RIGHT_REAR_MOUNT_OUTPUT, right_rear_mount)
        controller.set_pulse_us(ELEVATOR_OUTPUT, elevator)
        controller.set_pulse_us(RUDDER_OUTPUT, rudder_output)
        controller.set_pulse_us(LIGHT_OUTPUT, light)
        return "pca=ok flightmode={} flight={} esc={} mount={} frontmount={} leftrear={} rightrear={} elevator={} rudder={} rudderout={} rudderctrl={} rearctrl={} aileronctrl={} lights={} light={}".format(
            flight_mode,
            flight_label,
            speed,
            mount,
            front_mount,
            left_rear_mount,
            right_rear_mount,
            elevator,
            rudder,
            rudder_output,
            "on" if rudder_control else "off",
            "on" if rear_mount_control else "off",
            "on" if rear_aileron_control else "off",
            "on" if lights_on else "off",
            light,
        )
    except Exception as exc:
        return "pca=err flightmode={} flight={} pcaerr={}".format(flight_mode, flight_label, exc)


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
    i2c = None
    mux = None
    sensor = None
    tof_sensors = [(channel, None) for channel in TOF_CHANNELS]
    imu = None
    servo_controller = None
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

        rc_channels = receiver.read()
        pca_fields = apply_rc_outputs(servo_controller, rc_channels)
        tof_fields = read_tof_fields(tof_sensors, tof_smoother)
        motion_fields = read_motion_fields(imu, imu_smoother)
        rc_fields = "rc=ppm " + " ".join(
            "rc{}={}".format(index, "None" if value is None else value)
            for index, value in enumerate(rc_channels, start=1)
        )

        if sensor is None:
            print(
                "sensor=Receiver / waiting x=0 y=0 z=0 heading=0.0 {} {} {} {}".format(
                    tof_fields, motion_fields, rc_fields, pca_fields
                )
            )
        else:
            try:
                x, y, z = smooth_vector(mag_smoother, "mag", sensor.read())
                heading = heading_degrees(x, y)
                if hasattr(sensor, "raw_to_microtesla"):
                    xu = sensor.raw_to_microtesla(x)
                    yu = sensor.raw_to_microtesla(y)
                    zu = sensor.raw_to_microtesla(z)
                    print(
                        "sensor={} x={} y={} z={} xuT={:.2f} yuT={:.2f} zuT={:.2f} heading={:.1f} {} {} {} {}".format(
                            sensor.name, x, y, z, xu, yu, zu, heading, tof_fields, motion_fields, rc_fields, pca_fields
                        )
                    )
                else:
                    print(
                        "sensor={} x={} y={} z={} heading={:.1f} {} {} {} {}".format(
                            sensor.name, x, y, z, heading, tof_fields, motion_fields, rc_fields, pca_fields
                        )
                    )
            except OSError as exc:
                mag_smoother.reset()
                print(
                    "sensor={} x=0 y=0 z=0 heading=0.0 {} {} {} {} magerr={}".format(
                        sensor.name, tof_fields, motion_fields, rc_fields, pca_fields, exc
                    )
                )
                sensor = None
        sleep(REPORT_INTERVAL_S)


main()
