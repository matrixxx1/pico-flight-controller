from machine import Pin, disable_irq, enable_irq
from time import sleep, ticks_diff, ticks_us


PPM_PIN = 15
RC_CHANNELS = 8
PPM_SYNC_US = 3000
PPM_MIN_US = 750
PPM_MAX_US = 2250
PPM_STALE_US = 250_000
REPORT_INTERVAL_S = 0.05


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


def format_rc_fields(values):
    fields = []
    for index, value in enumerate(values, start=1):
        fields.append("rc{}={}".format(index, "None" if value is None else value))
    return "rc=ppm " + " ".join(fields)


def main():
    receiver = PPMReceiver(PPM_PIN)
    print("Pico R8EF receiver-only reader")
    print("R8EF CH2 PPM signal -> Pico GP{}".format(PPM_PIN))

    while True:
        rc_fields = format_rc_fields(receiver.read())
        print(
            "sensor=Receiver / PPM x=0 y=0 z=0 heading=0.0 "
            "tof0=None tof1=None tof2=None tof3=None "
            "adxl=None ax=0.000 ay=0.000 az=0.000 pitch=0.0 roll=0.0 {}".format(rc_fields)
        )
        sleep(REPORT_INTERVAL_S)


main()
