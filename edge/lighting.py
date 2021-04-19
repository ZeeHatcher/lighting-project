import serial

from abc import ABCMeta, abstractmethod

class Mode:
    __metaclass__ = ABCMeta

    @abstractmethod
    def run(self):
        pass

class BasicMode(Mode):
    def run(self):
        print("Basic mode")

BAUD_RATE = 115200
NUM_PIXELS = 144

db = None
ser = None

def setup():
    global ser
    ser = serial.Serial('/dev/ttyACM0', BAUD_RATE)

    pass

def loop():
    val = raw_input("Please enter a value: ")
    r = g = b = b'\x00'

    if val == "r":
        r = b'\x33'
    elif val == "g":
        g = b'\x33'
    elif val == "b":
        b = b'\x33'

    ser.write(r * NUM_PIXELS)
    ser.write(g * NUM_PIXELS)
    ser.write(b * NUM_PIXELS)

if __name__ == "__main__":
    setup()

    while (True):
        loop()
