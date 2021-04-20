import serial
import random
import time

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
    r = bytearray(NUM_PIXELS)

    for i in range(136, NUM_PIXELS):
        r[i] = b'\xff'

    ser.write(r)
    ser.write(b'\x00' * NUM_PIXELS)
    ser.write(b'\x00' * NUM_PIXELS)

    # for i in range(NUM_PIXELS):
        # r = bytearray(NUM_PIXELS)
        # g = bytearray(NUM_PIXELS)
        # b = bytearray(NUM_PIXELS)

        # r[i] = b'\xff'
        # g[i] = b'\xff'
        # b[i] = b'\xff'

        # ser.write(r)
        # ser.write(g)
        # ser.write(b)

if __name__ == "__main__":
    setup()

    # Short delay to let serial setup properly
    time.sleep(1)

    while (True):
        loop()
