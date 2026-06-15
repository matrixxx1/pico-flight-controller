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
TCA9548A_ADDR = 0x70
VL53L0X_ADDR = 0x29
ADXL345_ADDR = 0x53

TOF_CHANNELS = (0, 1, 2, 3, 6)
MAG_CHANNEL = 4
ADXL_CHANNEL = 5

PPM_PIN = 15
RC_CHANNELS = 8
PPM_SYNC_US = 3000
PPM_MIN_US = 750
PPM_MAX_US = 2250
PPM_STALE_US = 250_000

REPORT_INTERVAL_S = 0.10
SENSOR_RETRY_US = 5_000_000


def twos_complement(value, bits=16):
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value


def heading_degrees(x, y):
    heading = math.degrees(math.atan2(y, x))
    if heading < 0:
        heading += 360
    return heading


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
    name = "QMC5883P / HP5883"

    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = QMC5883P_ADDR
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


def create_magnetometer(i2c, devices):
    if QMC5883L_ADDR in devices:
        return QMC5883L(i2c)
    if HMC5883L_ADDR in devices:
        return HMC5883L(i2c)
    if QMC5883P_ADDR in devices:
        return QMC5883P(i2c)
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


def find_adxl345(i2c, mux):
    try:
        mux.select(ADXL_CHANNEL)
        devices = i2c.scan()
        print("ADXL channel {} devices: {}".format(ADXL_CHANNEL, [hex(device) for device in devices]))
        if ADXL345_ADDR not in devices:
            mux.safe_disable()
            return None
        accel = MuxedADXL345(mux, ADXL_CHANNEL)
        mux.safe_disable()
        print("Detected ADXL345 on TCA channel {}".format(ADXL_CHANNEL))
        return accel
    except Exception as exc:
        print("ADXL345 channel {} init failed: {}".format(ADXL_CHANNEL, exc))
        mux.safe_disable()
        return None


def read_tof_fields(tof_sensors):
    fields = []
    for channel, tof in tof_sensors:
        value = "None"
        if tof is not None:
            try:
                value = str(tof.read_mm())
            except Exception:
                value = "err"
        fields.append("tof{}={}".format(channel, value))
    return " ".join(fields)


def read_adxl_fields(adxl):
    if adxl is None:
        return "adxl=None ax=0.000 ay=0.000 az=0.000 pitch=0.0 roll=0.0"
    try:
        ax, ay, az = adxl.read()
        pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
        roll = math.degrees(math.atan2(ay, az))
        return "adxl=ok ax={:.3f} ay={:.3f} az={:.3f} pitch={:.1f} roll={:.1f}".format(
            ax, ay, az, pitch, roll
        )
    except Exception as exc:
        return "adxl=err ax=0.000 ay=0.000 az=0.000 pitch=0.0 roll=0.0 adxlerr={}".format(exc)


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
    adxl = None
    last_retry = ticks_us()

    print("Pico flight sensor + R8EF receiver reader")
    print("Root I2C: Pico GP0=SDA, GP1=SCL to HW-617 SDA/SCL")
    print("R8EF CH2 PPM signal -> Pico GP{}".format(PPM_PIN))

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
                        adxl = find_adxl345(i2c, mux)
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

        tof_fields = read_tof_fields(tof_sensors)
        adxl_fields = read_adxl_fields(adxl)
        rc_fields = read_rc_fields(receiver)

        if sensor is None:
            print(
                "sensor=Receiver / waiting x=0 y=0 z=0 heading=0.0 {} {} {}".format(
                    tof_fields, adxl_fields, rc_fields
                )
            )
        else:
            try:
                x, y, z = sensor.read()
                heading = heading_degrees(x, y)
                if hasattr(sensor, "raw_to_microtesla"):
                    xu = sensor.raw_to_microtesla(x)
                    yu = sensor.raw_to_microtesla(y)
                    zu = sensor.raw_to_microtesla(z)
                    print(
                        "sensor={} x={} y={} z={} xuT={:.2f} yuT={:.2f} zuT={:.2f} heading={:.1f} {} {} {}".format(
                            sensor.name, x, y, z, xu, yu, zu, heading, tof_fields, adxl_fields, rc_fields
                        )
                    )
                else:
                    print(
                        "sensor={} x={} y={} z={} heading={:.1f} {} {} {}".format(
                            sensor.name, x, y, z, heading, tof_fields, adxl_fields, rc_fields
                        )
                    )
            except OSError as exc:
                print(
                    "sensor={} x=0 y=0 z=0 heading=0.0 {} {} {} magerr={}".format(
                        sensor.name, tof_fields, adxl_fields, rc_fields, exc
                    )
                )
                sensor = None
        sleep(REPORT_INTERVAL_S)


main()
