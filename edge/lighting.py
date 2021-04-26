import MySQLdb
import os
import serial
import time

from abc import ABCMeta, abstractmethod
from dotenv import load_dotenv

from virtual import VirtualLightstick

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

    @abstractmethod
    def run(self):
        pass

class NullMode(Mode):
    def run(self):
        color = Color()

        c_r = color.r * NUM_PIXELS
        c_g = color.g * NUM_PIXELS
        c_b = color.b * NUM_PIXELS

        return c_r, c_g, c_b

class BasicMode(Mode):
    def __init__(self):
        self._pattern_id = None
        self._pattern = None

    def run(self):
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
            elif new_pattern_id == 6:
                self._pattern = WavePattern()
            else:
                self._pattern = NullPattern()

            self._pattern_id = new_pattern_id

class Pattern:
    __metaclass__ = ABCMeta

    @abstractmethod
    def render(self):
        pass

    def _get_colors(self):
        colors = []

        with db.cursor() as cur:
            cur.execute("SELECT colors FROM lightsticks WHERE id = %s" % LIGHTSTICK_ID)

            color_string = cur.fetchone()[0]

            if color_string != None:
                colors = color_string.split(",")

            cur.close()

        return colors

class NullPattern(Pattern):
    def render(self):
        color = Color()

        c_r = color.r * NUM_PIXELS
        c_g = color.g * NUM_PIXELS
        c_b = color.b * NUM_PIXELS

        return c_r, c_g, c_b

class SolidPattern(Pattern):
    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = color.r * NUM_PIXELS
        c_g = color.g * NUM_PIXELS
        c_b = color.b * NUM_PIXELS

        return c_r, c_g, c_b

class DotPattern(Pattern):
    def __init__(self):
        self._i = 0

    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = ["\x00"]* NUM_PIXELS
        c_g = ["\x00"]* NUM_PIXELS
        c_b = ["\x00"]* NUM_PIXELS

        c_r[self._i] = color.r
        c_g[self._i] = color.g
        c_b[self._i] = color.b

        self._i += 1

        if self._i >= NUM_PIXELS:
            self._i = 0

        time.sleep(0.1)

        return c_r, c_g, c_b
        
class WavePattern(Pattern):
    def __init__(self):
        self._i = 0
        self._ascending = True
        
    def render(self):
        colors = self._get_colors()

        color0 = Color(colors[0]) if len(colors[0]) == 6 else Color()
        color1 = Color(colors[-1]) if len(colors[-1]) == 6 else Color()
        c_r = [color0.r] * NUM_PIXELS
        c_g = [color0.g] * NUM_PIXELS
        c_b = [color0.b] * NUM_PIXELS
        
        c_r[0:self._i] = [color1.r]*self._i
        c_g[0:self._i] = [color1.g]*self._i
        c_b[0:self._i] = [color1.b]*self._i
        
        if self._ascending:
            self._i += 1
        else:
            self._i -= 1

        if self._i >= NUM_PIXELS and self._ascending:
            self._ascending = False
        if self._i == 0 and not self._ascending:
            self._ascending = True

        time.sleep(0.1)

        return c_r, c_g, c_b

db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE) or die("Could not connect to database")
db.autocommit(True)

ser = None
lightstick = None

mode_id = None
mode = None

def loop():
    global mode_id, mode
    new_mode_id = None

    is_on = True

    # Constantly get on/off state of lightstick
    with db.cursor() as cur:
        cur.execute("SELECT is_on FROM lightsticks WHERE id = %s" % LIGHTSTICK_ID)
        
        state = cur.fetchone()[0]
        is_on = state == 1

        cur.close()

    if is_on:
        # Constantly get latest mode value
        with db.cursor() as cur:
            cur.execute("SELECT mode FROM lightsticks WHERE id = %s" % LIGHTSTICK_ID)
            
            new_mode_id = cur.fetchone()[0]

            cur.close()
    else:
        new_mode_id = 0

    # If mode has actually changed
    if new_mode_id != mode_id:
        if new_mode_id == 1:
            mode = BasicMode()
        else:
            mode = NullMode()

        mode_id = new_mode_id

    c_r, c_g, c_b = mode.run()

    if ser != None:
        ser.write(c_r)
        ser.write(c_g)
        ser.write(c_b)

    if lightstick != None:
        lightstick.update(c_r, c_g, c_b)

if __name__ == "__main__":
    # Short delay to let serial setup properly
    time.sleep(1)

    # ser = serial.Serial(SERIAL_CONN, BAUD_RATE)
    lightstick = VirtualLightstick(NUM_PIXELS)

    while (True):
        loop()
