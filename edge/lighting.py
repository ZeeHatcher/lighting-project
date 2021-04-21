import serial
import time

from abc import ABCMeta, abstractmethod

class Color:
    def __init__(self, color="000000"):
        if len(color) < 6:
            color = "000000"

        self.r = color[:2].decode("hex")
        self.g = color[2:4].decode("hex")
        self.b = color[4:].decode("hex")

class Mode:
    __metaclass__ = ABCMeta

    def run(self):
        c_r, c_g, c_b = self._process()

        ser.write(c_r)
        ser.write(c_g)
        ser.write(c_b)

    @abstractmethod
    def _process(self):
        pass

class BasicMode(Mode):
    def __init__(self):
        self._pattern = SolidPattern()

    def _process(self):
        return self._pattern.render()

class Pattern:
    __metaclass__ = ABCMeta

    @abstractmethod
    def render(self):
        pass

class SolidPattern(Pattern):
    def render(self):
        color = Color(raw_input("Color: "))

        c_r = color.r * NUM_PIXELS
        c_g = color.g * NUM_PIXELS
        c_b = color.b * NUM_PIXELS

        return c_r, c_g, c_b

class DotPattern(Pattern):
    def __init__(self):
        self._i = 0

    def render(self):
        color = Color("ff3300")

        c_r = bytearray(NUM_PIXELS)
        c_g = bytearray(NUM_PIXELS)
        c_b = bytearray(NUM_PIXELS)

        c_r[self._i] = color.r
        c_g[self._i] = color.g
        c_b[self._i] = color.b

        self._i += 1

        if self._i >= NUM_PIXELS:
            self._i = 0

        time.sleep(0.1)

        return c_r, c_g, c_b

BAUD_RATE = 115200
NUM_PIXELS = 8

db = None
ser = None
mode = BasicMode()

def setup():
    global ser
    ser = serial.Serial('/dev/ttyACM0', BAUD_RATE)

def loop():
    mode.run()

if __name__ == "__main__":
    setup()

    # Short delay to let serial setup properly
    time.sleep(1)

    while (True):
        loop()
