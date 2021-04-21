import MySQLdb
import os
import serial
import time

from abc import ABCMeta, abstractmethod
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
DB_HOST = os.environ.get("DB_HOST")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_DATABASE = os.environ.get("DB_DATABASE")

LIGHTSTICK_ID = os.environ.get("LIGHTSTICK_ID")
NUM_PIXELS = int(os.environ.get("NUM_PIXELS"))
BAUD_RATE = int(os.environ.get("BAUD_RATE"))
SERIAL_CONN = os.environ.get("SERIAL_CONN")

# Custom data type for color
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

class NullMode(Mode):
    def _process(self):
        c_r = bytearray(NUM_PIXELS)
        c_g = bytearray(NUM_PIXELS)
        c_b = bytearray(NUM_PIXELS)

        return c_r, c_g, c_b

class BasicMode(Mode):
    def __init__(self):
        self._pattern_id = None
        self._pattern = None

    def _process(self):
        self._get_pattern()

        return self._pattern.render()

    def _get_pattern(self):
        new_pattern_id = None

        # Constantly get latest pattern value
        with db.cursor() as cur:
            cur.execute("SELECT pattern FROM lightsticks WHERE id = %s" % LIGHTSTICK_ID)
            
            new_pattern_id = cur.fetchone()[0]

            cur.close()

        # If pattern has actually changed
        if new_pattern_id != self._pattern_id:
            if new_pattern_id == 1:
                self._pattern = SolidPattern()
            elif new_pattern_id == 2:
                self._pattern = DotPattern()
            else:
                self._pattern = NullPattern()

            self._pattern_id = new_pattern_id

class Pattern:
    __metaclass__ = ABCMeta

    @abstractmethod
    def render(self):
        pass

class NullPattern(Pattern):
    def render(self):
        c_r = bytearray(NUM_PIXELS)
        c_g = bytearray(NUM_PIXELS)
        c_b = bytearray(NUM_PIXELS)

        return c_r, c_g, c_b

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

db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE) or die("Could not connect to database")
db.autocommit(True)

ser = serial.Serial(SERIAL_CONN, BAUD_RATE)

mode_id = None
mode = None

def loop():
    global mode_id, mode
    new_mode_id = None

    # Constantly get latest mode value
    with db.cursor() as cur:
        cur.execute("SELECT mode FROM lightsticks WHERE id = %s" % LIGHTSTICK_ID)
        
        new_mode_id = cur.fetchone()[0]

        cur.close()

    # If mode has actually changed
    if new_mode_id != mode_id:
        if new_mode_id == 1:
            mode = BasicMode()
        else:
            mode = NullMode()

        mode_id = new_mode_id

    mode.run()

if __name__ == "__main__":
    # Short delay to let serial setup properly
    time.sleep(1)

    while (True):
        loop()
