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
        r, g, b = self._process()

        ser.write(r)
        ser.write(g)
        ser.write(b)

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
    def __init__(self):
        self._color = Color()

    def render(self):
        self._color = Color(raw_input("Color: "))

        r = self._color.r * NUM_PIXELS
        g = self._color.g * NUM_PIXELS
        b = self._color.b * NUM_PIXELS

        return r, g, b

BAUD_RATE = 115200
NUM_PIXELS = 8

db = None
ser = None

def setup():
    global ser
    ser = serial.Serial('/dev/ttyACM0', BAUD_RATE)

def loop():
    mode = BasicMode()
    mode.run()

if __name__ == "__main__":
    setup()

    # Short delay to let serial setup properly
    time.sleep(1)

    while (True):
        loop()
