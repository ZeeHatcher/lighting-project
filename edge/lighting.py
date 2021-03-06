from abc import ABC, abstractmethod
from dotenv import load_dotenv
import json
from multiprocessing import Value
import os
import sys
import threading
import time
import traceback

# Cloud connectivity
from awscrt import io, mqtt
from awsiot import iotshadow
from awsiot import mqtt_connection_builder
import boto3
from concurrent.futures import Future
from uuid import uuid4

# Basic Mode
from colorsys import hls_to_rgb

# Image Mode
from PIL import Image

# Music Mode
# import numpy as np
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
# from audio_analyzer import *
from pydub import AudioSegment
import pyaudio
import audioop
import wave
from gradient_generator import *

# Wireless/Virtual output
import select
import socket
from virtual import VirtualLightstick

#lightsaber mode
import librosa
import random

load_dotenv()

NUM_PIXELS = int(os.environ.get("NUM_PIXELS"))

CLIENT_ID = os.environ.get("CLIENT_ID") or str(uuid4())
S3_BUCKET = os.environ.get("S3_BUCKET")
THING_NAME = os.environ.get("THING_NAME")

lightstick = None

mode_id = None
mode = None

mqtt_connection = None
shadow_client = None

is_done = threading.Event()

class LockedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.shadow_state = {
            "is_on": False,
            "mode": 1,
            "pattern": 1,
            "colors": [],
            "upload_image": 0,
            "upload_audio": 0,
            "microphone_max": 32767,
        }

locked_data = LockedData()

# Custom data type for color
class Color:
    def __init__(self, color="000000"):
        if len(color) < 6:
            color = "000000"

        self.r = int(color[0:2], 16)
        self.g = int(color[2:4], 16)
        self.b = int(color[4:], 16)

class Mode(ABC):
    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def exit(self):
        pass
    
    def _get_colors(self):
        return locked_data.shadow_state["colors"]

class NullMode(Mode):
    def run(self):
        c_r = c_g = c_b = bytearray([0] * NUM_PIXELS)

        return c_r, c_g, c_b

    def exit(self):
        pass


class MusicMode(Mode):
#     https://stackoverflow.com/questions/19529230/mp3-with-pyaudio?rq=1
    def __init__(self):
        self._set = True

        if not os.path.exists("audio"):
            print("not exist")
            self._set = False
            return

        # Don't add songs with any extension
        # The conversion will cause it to break T-T
        filename = r"audio"
        try:
            self._wf = wave.open(filename,'rb')
        except:
            print("Incompatible format, converting file")
            new_file = AudioSegment.from_mp3(filename)
            new_file.export(filename,format="wav")
            self._wf = wave.open(filename,'rb')
            
        self._data = self._wf.readframes(self._wf.getnframes())
        
#         self._pixels = 0
        self._previous = 0

        pygame.init()
        self._rate = self._wf.getframerate()
        
        self._frames_per_sec = int(len(self._data)/(self._wf.getnframes()/self._rate))

        #32767(max data for 16bit integer 2^15 -1)
        self._max = int(32767 * 1.05)
        self._lastHeartBeat = time.time()
        self._increaseHeartBeat = True

        half_pixels = int(NUM_PIXELS/2)
        array1 = get_gradient_3d(half_pixels,1,(30,150,0),(255,242,0),(True,True,True))
        array2 = get_gradient_3d((NUM_PIXELS - half_pixels),1,(255,242,0),(255,0,0),(True,True,True))
        self._r = [int(val[0]) for val in array1[0]] + [int(val[0]) for val in array2[0]]
        self._g = [int(val[1]) for val in array1[0]] + [int(val[1]) for val in array2[0]]
        self._b = [int(val[2]) for val in array1[0]] + [int(val[2]) for val in array2[0]]
        
        #quit to reset the initial
        pygame.mixer.quit()
        pygame.mixer.init(frequency=self._rate)
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
    
    def run(self):
        if not self._set:
            c_r = c_g = c_b = bytearray([0] * NUM_PIXELS)

            return c_r, c_g, c_b

        c_r = bytearray([0] * NUM_PIXELS)
        c_g = bytearray([0] * NUM_PIXELS)
        c_b = bytearray([0] * NUM_PIXELS)
        
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                sound = 0
                place = int(pygame.mixer.music.get_pos()/1000*self._frames_per_sec)
                try:
                    data = self._data[place:place+2048]
                    if(len(data)>1):
                        reading = audioop.max(data,2)
                    else:
                        reading = self._previous
                    
                    if(self._previous is 0):
                        self._previous = reading
                    else:
                        if(reading >= 32760 or abs(self._previous-reading)>20000):
                            reading = self._previous
                        else:
                            self._previous = reading
                            
                    sound += reading
#                 print(reading)
                    percentage = int(sound/self._max * NUM_PIXELS)
                    
#                 if(self._pixels < percentage):
#                     self._pixels += 1
#                 
#                 if(self._pixels > percentage):
#                     self._pixels -= 1
#                 
#                 percentage = self._pixels
                        
                    minimum = int(0.05 * NUM_PIXELS)
                    if(time.time() - self._lastHeartBeat > 0.1 and percentage >0):
            #                 print("Sending heartbeat")
                        if(percentage < minimum):
                            self._increaseHeartBeat = True
                        if(percentage > (NUM_PIXELS - minimum)):
                            self._increaseHeartBeat = False
                            
                        if(self._increaseHeartBeat):
                            percentage += minimum
                            self._increaseHeartBeat = False
                        else:
                            percentage -= minimum
                            self._increaseHeartBeat = True
                        self._lastHeartBeat = time.time()
                except:
                    percentage = 0
            else:
                percentage = 0
            c_r[0:percentage] = bytearray(self._r[0:percentage])
            c_g[0:percentage] = bytearray(self._g[0:percentage])
            c_b[0:percentage] = bytearray(self._b[0:percentage])

        except AttributeError:
            c_r = c_g = c_b = bytearray([0] * NUM_PIXELS)

        return c_r,c_g,c_b
    
    def exit(self):
        if self._set:
            self._wf.close()
            print("Closed wave")
            pygame.quit()

class AudioMode(Mode):
    def __init__(self):
        self._chunk = 1024
        self._format = pyaudio.paInt16
        self._channels = 2
        self._rate = 44100
        #Low: 16383
        #Medium: 32767
        #High: 65534
        #self._max = locked_data.shadow_state["microphone_max"]
        self._dev_index = 0
        
        half_pixels = int(NUM_PIXELS/2)
        array1 = get_gradient_3d(half_pixels,1,(30,150,0),(255,242,0),(True,True,True))
        array2 = get_gradient_3d((NUM_PIXELS - half_pixels),1,(255,242,0),(255,0,0),(True,True,True))
        self._r = [int(val[0]) for val in array1[0]] + [int(val[0]) for val in array2[0]]
        self._g = [int(val[1]) for val in array1[0]] + [int(val[1]) for val in array2[0]]
        self._b = [int(val[2]) for val in array1[0]] + [int(val[2]) for val in array2[0]]
        
        self._p = pyaudio.PyAudio()
        
        for ii in range(self._p.get_device_count()):
#             print(p.get_device_info_by_index(ii).get('name'))
            dev = self._p.get_device_info_by_index(ii)
            if(dev['maxInputChannels']>1):
                print('Using the first compatible audio device detected:')
                print((ii,dev['name'],dev['maxInputChannels']))
                self._dev_index = ii
#                 if(dev['maxInputChannels']>1):
#                     self._channels = 2
                break
            
        self._stream = self._p.open(format = self._format,
                              channels = self._channels,
                              input_device_index = self._dev_index,
                              rate = self._rate,
                              input = True,
                              output = True,
                              frames_per_buffer=self._chunk
                              )

    def run(self):
#         colors = locked_data.shadow_state["colors"]
#         color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()
        c_r = bytearray([0] * NUM_PIXELS)
        c_g = bytearray([0] * NUM_PIXELS)
        c_b = bytearray([0] * NUM_PIXELS)
        
        sound = 0
        for i in range(0,2):
            data = self._stream.read(self._chunk)
            reading = audioop.max(data,2)
            sound += reading
            # time.sleep(.0001)
        microphone_max = locked_data.shadow_state["microphone_max"]
        if(len(data) > 0):
            percentage = int(sound/microphone_max * NUM_PIXELS)
#             print(percentage)
            c_r[0:percentage] = bytearray(self._r[0:percentage])
            c_g[0:percentage] = bytearray(self._g[0:percentage])
            c_b[0:percentage] = bytearray(self._b[0:percentage])
        
        return c_r,c_g,c_b
        
    def exit(self):
#         pass
        self._stream.stop_stream()
        self._stream.close()
        print("Closed stream")
        self._p.terminate()
        print("PyAudio Terminated")


class BasicMode(Mode):
    def __init__(self):
        self._pattern_id = None
        self._pattern = None

    def run(self):
        self._get_pattern()

        return self._pattern.render()

    def exit(self):
        pass

    def _get_pattern(self):
        new_pattern_id = locked_data.shadow_state["pattern"]

        # If pattern has actually changed
        if new_pattern_id != self._pattern_id:
            if new_pattern_id == 1:
                self._pattern = SolidPattern()
            elif new_pattern_id == 2:
                self._pattern = DotPattern()
            elif new_pattern_id == 3:
                self._pattern = BlinkPattern()
            elif new_pattern_id == 4:
                self._pattern = BreathePattern()
            elif new_pattern_id == 5:
                self._pattern = RainbowPattern()
            elif new_pattern_id == 6:
                self._pattern = WavePattern()
            else:
                self._pattern = NullPattern()

            self._pattern_id = new_pattern_id

class ImageMode(Mode):
    def __init__(self):
        self._set = True

        if not os.path.exists("image"):
            self._set = False
            return

        # Load and resize image
        im = Image.open("image")

        if im.mode == "P":
            im = im.convert("RGB")

        # Resize image while keeping aspect ratio if image width is larger than NUM_PIXELS
        if im.width > NUM_PIXELS:
            ratio = im.height / im.width
            im = im.resize((NUM_PIXELS, max(1, round(NUM_PIXELS * ratio))))

        rows = [] # 3D-Array: Rows -> Channels -> Color

        for y in range(im.height):
            rows.append([]) # Initialize row arrays

            for c in range(3):
                rows[y].append([]) # Initialize channel arrays

            # Fill channel arrays with color data
            for x in range(NUM_PIXELS):
                if x < im.width:
                    colors = im.getpixel((x, y))

                    for c in range(3):
                        rows[y][c].append(colors[c])

                else:
                    for c in range(3):
                        rows[y][c].append(0)

        im.close()

        self._rows = rows
        self._row = 0

    def run(self):
        if self._set:
            c_r = bytearray(self._rows[self._row][0])
            c_g = bytearray(self._rows[self._row][1])
            c_b = bytearray(self._rows[self._row][2])

            self._row += 1

            if self._row >= len(self._rows):
                self._row = 0

        else:
            c_r = c_g = c_b = bytearray([0] * NUM_PIXELS)

        return c_r, c_g, c_b

    def exit(self):
        pass

class LightsaberMode(Mode):
    
    def __init__(self):
        self._value = Value("f", 0)
        self._thread = None
        self._phase = 0
        self._pixels = 0
#         self._value_file = open("values.txt","r")
#         self._values = self._value_file.read().split("|")
#         self._tracker = 0
#         self._stime = 0
        self._last_val = 0
        self._consequtive_val = 0
        pygame.mixer.init()
        pygame.mixer.set_num_channels(4)
        
        self._direct = "./saber-sounds/"
        self._start_sound = self._direct+ "saber-on.wav"
        self._idle_sound = self._direct + "saber-idle.wav"
        self._clash_sounds = ["saber-clash1.wav","saber-clash2.wav","saber-clash3.wav","saber-clash4.wav"]
        self._swing_sound = self._direct + "saber-swing.wav"
        

    def run(self):
        val = self._value.value

        c_r = bytearray([0] * NUM_PIXELS)
        c_g = bytearray([0] * NUM_PIXELS)
        c_b = bytearray([0] * NUM_PIXELS)
        
#         colors=['0000ff']
        colors = self._get_colors()
#         print(locked_data.shadow_state["colors"])

        
        if self._thread == None:
            print("Starting publish thread... ", end="")
            self._thread = threading.Thread(target=publish_sensors_data, args=(self._value,))
            self._thread.start()
            print("Started.")

        if(self._phase == 1):
            self._pixels = NUM_PIXELS
#             value = float(self._values[self._tracker])
#             if(self._tracker < len(self._values)-1):
#                 self._tracker += 1
#             else:
#                 self._tracker = 0
                
#             print (value)
            
            clash_channel = pygame.mixer.Channel(1)
            swing_channel = pygame.mixer.Channel(2)
            swing_sound = pygame.mixer.Sound(self._swing_sound)
            clash_sound = pygame.mixer.Sound(self._direct + random.choice(self._clash_sounds))
#             if (self._last_val < value):
#             if channel.get_busy():
#                 pass
#             else:
            if(val > 21):
                if(clash_channel.get_busy()):
                    pass
                else:
                    clash_channel.play(clash_sound)
                    colors = ['ffffff']
            elif(val > 11):
                if(clash_channel.get_busy() or swing_channel.get_busy()):
                    pass
                else:
                    if(self._consequtive_val == 0):
                        swing_channel.play(swing_sound)
                        
                    if(self._consequtive_val >= 3):
                        swing_channel.play(swing_sound)
                        self._consequtive_val = 0
                    
                    if(val >0.0 and abs(val - self._last_val)<=3):
                        self._consequtive_val += 1
                    else:
                        self._consequtive_val = 0
                        
        #             print("Consequtive:",self._consequtive_val)
                    self._last_val = val
            else:
                pass
                      
            
        if(self._phase == 0):
            song_length = librosa.get_duration(filename=self._start_sound) * 1000
            if pygame.mixer.music.get_busy():
                self._pixels = int((pygame.mixer.music.get_pos()/song_length)*NUM_PIXELS)
                
                if (pygame.mixer.music.get_pos() > int(song_length*0.95)):
                    channel = pygame.mixer.Channel(0)
                    sound = pygame.mixer.Sound(self._idle_sound)
                    channel.play(sound,loops = -1)
            else:
                if(self._pixels == 0):
                    pygame.mixer.music.load(self._start_sound)
                    pygame.mixer.music.play()
#                     self._stime = time.time()
                else:
#                     idle = pygame.mixer.music.load(direct+ "saber-idle.wav")
#                     pygame.mixer.music.play(loops=-1)
                    self.pixels = NUM_PIXELS
                    self._phase = 1
                    
#         print(pygame.mixer.music.get_pos())        
        if(self._pixels > NUM_PIXELS):
            self._pixels = NUM_PIXELS
                
        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()
        c_r[0:self._pixels] = bytearray([color.r] * self._pixels)
        c_g[0:self._pixels] = bytearray([color.g] * self._pixels)
        c_b[0:self._pixels] = bytearray([color.b] * self._pixels)
        
        # Limit to 30 frames per second
        time.sleep(0.034)
        return c_r, c_g, c_b
    
    def exit(self):
#         self._value_file.close()
        if self._thread != None:
            print("Stopping publish thread... ", end="")

            self._thread.is_run = False
            self._thread.join()

            self._thread = None
            print("Stopped publish thread.")

    @property
    def value(self):
        return self._value.value

    @value.setter
    def value(self, value):
        self._value.value = value

class Pattern(ABC):
    @abstractmethod
    def render(self):
        pass

    def _get_colors(self):
        return locked_data.shadow_state["colors"]

class NullPattern(Pattern):
    def render(self):
        c_r = c_g = c_b = bytearray([0] * NUM_PIXELS)

        return c_r, c_g, c_b

class SolidPattern(Pattern):
    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = bytearray([color.r] * NUM_PIXELS)
        c_g = bytearray([color.g] * NUM_PIXELS)
        c_b = bytearray([color.b] * NUM_PIXELS)

        return c_r, c_g, c_b

class DotPattern(Pattern):
    def __init__(self):
        self._i = 0
        self._dir = 1

    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = bytearray([0] * NUM_PIXELS)
        c_g = bytearray([0] * NUM_PIXELS)
        c_b = bytearray([0] * NUM_PIXELS)

        c_r[self._i] = color.r
        c_g[self._i] = color.g
        c_b[self._i] = color.b

        if self._i >= NUM_PIXELS - 1:
            self._dir = -1

        if self._i <= 0:
            self._dir = 1

        self._i += self._dir

        return c_r, c_g, c_b
        
class WavePattern(Pattern):
    def __init__(self):
        self._i = 0
        self._ascending = True
        
    def render(self):
        colors = self._get_colors()

        color0 = Color(colors[0]) if len(colors[0]) == 6 else Color()
        color1 = Color(colors[-1]) if len(colors[-1]) == 6 else Color()
        c_r = bytearray([color0.r] * NUM_PIXELS)
        c_g = bytearray([color0.g] * NUM_PIXELS)
        c_b = bytearray([color0.b] * NUM_PIXELS)
        
        c_r[0:self._i] = bytearray([color1.r] * self._i)
        c_g[0:self._i] = bytearray([color1.g] * self._i)
        c_b[0:self._i] = bytearray([color1.b] * self._i)
        
        if self._ascending:
            self._i += 1
        else:
            self._i -= 1

        if self._i >= NUM_PIXELS and self._ascending:
            self._ascending = False
        if self._i == 0 and not self._ascending:
            self._ascending = True

        return c_r, c_g, c_b

class BreathePattern(Pattern):
    def __init__(self):
        self._mult = 0
        self._fade_in = True

    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = bytearray([round(color.r * self._mult)] * NUM_PIXELS)
        c_g = bytearray([round(color.g * self._mult)] * NUM_PIXELS)
        c_b = bytearray([round(color.b * self._mult)] * NUM_PIXELS)
        
        if self._fade_in:
            self._mult += 0.1
        else:
            self._mult -= 0.1
        
        if self._mult >= 1.0 and self._fade_in:
            self._mult = 1.0
            self._fade_in = False
            
        if self._mult <= 0.0 and not self._fade_in:
            self._mult = 0.0
            self._fade_in = True

        return c_r, c_g, c_b
    
class BlinkPattern(Pattern):
    def __init__(self):
        self._all_up = True
        self._count = 0
        self._threshold = 3

    def render(self):
        colors = self._get_colors()

        selected = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()
        
        if self._all_up:
            color = selected
        else:
            color = Color()
        self._count += 1
        
        if self._count >= self._threshold:
            self._all_up = not self._all_up
            self._count = 0
        
        c_r = bytearray([color.r] * NUM_PIXELS)
        c_g = bytearray([color.g] * NUM_PIXELS)
        c_b = bytearray([color.b] * NUM_PIXELS)
        
        return c_r, c_g, c_b
    
class RainbowPattern(Pattern):
    def __init__(self):
        rainbow = [ hls_to_rgb(1 * i/(NUM_PIXELS-1), 0.5, 1) for i in range(NUM_PIXELS) ]
        self._r_vals = []
        self._g_vals = []
        self._b_vals = []
        for colors in rainbow:
            self._r_vals.append(int(colors[0]*255))
            self._g_vals.append(int(colors[1]*255))
            self._b_vals.append(int(colors[2]*255))

    def render(self):
        c_r = bytearray(self._r_vals)
        c_g = bytearray(self._g_vals)
        c_b = bytearray(self._b_vals)
        
        self._r_vals.insert(0,self._r_vals.pop())
        self._b_vals.insert(0,self._b_vals.pop())
        self._g_vals.insert(0,self._g_vals.pop())
                 
        return c_r, c_g, c_b
        

# Function for gracefully quitting
def exit(msg_or_exception):
    if isinstance(msg_or_exception, Exception):
        print("Exiting due to exception.")
        traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
    else:
        print("Exiting:", msg_or_exception)

    print("Disconnecting... ", end="")
    if mode != None:
        mode.exit()

    for s in sockets:
        s.close()

    future = mqtt_connection.disconnect()
    future.add_done_callback(on_disconnected)

def on_disconnected(disconnect_future):
    # type: (Future) -> None
    print("Disconnected.")
    is_done.set()

def on_get_shadow_accepted(response):
    # type: (iotshadow.GetShadowResponse) -> None
    try:
        is_update = False

        print("Finished getting initial shadow state.")

        if response.state.reported:
            print("  Shadow reported state: ", end="")
            print(json.dumps(response.state.reported))

            change_local_state(response.state.reported)
        else:
            is_update = True

        if response.state.delta:
            delta = response.state.delta
            print("  Shadow delta: ", end="")
            print(json.dumps(delta))

            change_local_state(delta)

            if ("upload_image" in delta):
                start_download_thread("image")

            if ("upload_audio" in delta):
                start_download_thread("audio")

            is_update = True

        if is_update:
            print("  Shadow state has changed/does not exist.")

            change_shadow_state()

    except Exception as e:
        exit(e)

def on_get_shadow_rejected(error):
    # type: (iotshadow.ErrorResponse) -> None
    if error.code == 404:
        print("Thing has no shadow document.")
        change_shadow_state()
    else:
        exit("Get request was rejected. code:{} message:'{}'".format(
            error.code, error.message))

def on_shadow_delta_updated(delta):
    # type: (iotshadow.ShadowDeltaUpdatedEvent) -> None
    try:
        print("Received shadow delta event.")
        if delta.state:
            print("  Delta reports desired values are: ", end="")
            print(json.dumps(delta.state))

            change_local_state(delta.state)

            if ("upload_image" in delta.state):
                start_download_thread("image")

            if ("upload_audio" in delta.state):
                start_download_thread("audio")

            change_shadow_state()
        else:
            print("  Delta did not report a change.")

    except Exception as e:
        exit(e)

def on_publish_update_shadow(future):
    #type: (Future) -> None
    try:
        future.result()
        print("Update request published.")
    except Exception as e:
        print("Failed to publish update request.")
        exit(e)

def on_update_shadow_accepted(response):
    # type: (iotshadow.UpdateShadowResponse) -> None
    try:
        print("Finished updating reported shadow state to: ", end="")
        print(json.dumps(response.state.reported))
    except:
        exit("Updated shadow is missing the target property.")

def on_update_shadow_rejected(error):
    # type: (iotshadow.ErrorResponse) -> None
    exit("Update request was rejected. code:{} message:'{}'".format(
        error.code, error.message))

def download_file(file_type):
    global mode, mode_id
    key = THING_NAME + "/" + file_type

    print("Downloading %s... " % file_type, end="")
    s3.download_file(S3_BUCKET, key, file_type)
    print("Download completed.")

    # Reset mode to load in newly downloaded image
    if mode_id == 2 and file_type == "image":
        mode.exit()
        mode = ImageMode()

    elif mode_id == 3 and file_type == "audio":
        mode.exit()
        mode = MusicMode()

def start_download_thread(file_type):
    thread = threading.Thread(target=download_file, args=(file_type,))
    thread.start()

def publish_sensors_data(v):
    t = threading.currentThread()
    while getattr(t, "is_run", True):
        topic = "lightstick/" + THING_NAME + "/data"
        payload = {
            "acceleration": v.value,
            "is_clash": v.value > 21
        }

        mqtt_connection.publish(
            topic=topic,
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_LEAST_ONCE)

        time.sleep(1)

    print("Stopped publish thread.")

def change_local_state(new_state):
    with locked_data.lock:
        for p in new_state:
            locked_data.shadow_state[p] = new_state[p]

def change_shadow_state():
    print("Updating reported shadow value...")
    reported = {}
    with locked_data.lock:
        reported = locked_data.shadow_state

    request = iotshadow.UpdateShadowRequest(
        thing_name=THING_NAME,
        state=iotshadow.ShadowState(
            reported=reported,
        )
    )
    future = shadow_client.publish_update_shadow(request, mqtt.QoS.AT_LEAST_ONCE)
    future.add_done_callback(on_publish_update_shadow)
    print("Change requested")



buf = ""

def loop():
    global mode_id, mode, buf

    is_on = locked_data.shadow_state["is_on"]
    new_mode_id = locked_data.shadow_state["mode"] if is_on else 0

    # If mode has actually changed
    if new_mode_id != mode_id:
        if mode != None:
            mode.exit()

        if new_mode_id == 1:
            mode = BasicMode()
        elif new_mode_id == 2:
            mode = ImageMode()
        elif new_mode_id == 3:
            mode = MusicMode()
        elif new_mode_id == 4:
            mode = AudioMode()
        elif new_mode_id == 5:
            mode = LightsaberMode()
        else:
            mode = NullMode()

        mode_id = new_mode_id

    c_r, c_g, c_b = mode.run()

    # mode.values = tuple(map(lambda v: float(v), l.split(",")))

    # Wireless output
    readable, writable, exceptional = select.select(sockets, sockets, sockets)

    for s in readable:
        if s is server_socket: # New client is attempting connection to server
            print("New client detected.")
            client_socket, address = server_socket.accept()
            client_socket.setblocking(False)
            sockets.append(client_socket)

        else: # Client has sent data
            try:
                data = s.recv(64)

            except ConnectionResetError:
                print("Connection reset by peer.")

                if s in sockets:
                    print("Closing client... ", end="")
                    s.close()
                    sockets.remove(s)
                    print("Closed.")

                    break

            else:
                if data:
                    if mode_id == 5:
                        buf += data.decode()
                        
                else:
                    print("Received 0 bytes. Connection to client is closed.")

                    if s in sockets:
                        print("Closing client... ", end="")
                        s.close()
                        sockets.remove(s)
                        print("Closed.")

                    break

    for s in writable:
        try:
            s.sendall(c_r)
            s.sendall(c_g)
            s.sendall(c_b)

        except socket.error: # Connection closed
            print("Error occured while writing to client.")

            if s in sockets:
                print("Closing client... ", end="")
                sockets.remove(s)
                s.close()
                print("Closed.")

    for s in exceptional:
        print("An exception occured.")

        if s in sockets:
            print("Closing client... ", end="")
            sockets.remove(s)
            s.close()
            print("Closed.")

    # Get latest value from incoming byte stream
    if mode_id == 5:
        val = None

        while True:
            i_delimiter = buf.find("|")

            if i_delimiter == -1:
#                 print("break")
                break


            val = buf[:i_delimiter]
            buf = buf[i_delimiter+1:]
            

        if val != None:
            mode.value = float(val)
#             f.write(str(float(val)))
        else:
            mode.value = 0
        
#         f.write("|")

    # Virtual output
    if lightstick != None:
        lightstick.update(c_r, c_g, c_b)

    # Limit to 30 frames per second
    # time.sleep(0.034)
    time.sleep(0.011)



if __name__ == "__main__":
    # Create TCP/IP socket
    print("Intializing TCP server... ", end="")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", 12345))
    server_socket.listen(1)
    print("Initialized.")
#     f = open("values.txt","a")

    sockets = [server_socket]

    lightstick = VirtualLightstick(NUM_PIXELS)

    s3 = boto3.client("s3")

    # Short delay to let serial setup properly
    time.sleep(1)

    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    # Initiate MQTT connection
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=os.environ.get("THING_ENDPOINT"),
        cert_filepath=os.environ.get("CERT_FILE"),
        pri_key_filepath=os.environ.get("PRIVATE_KEY_FILE"),
        client_bootstrap=client_bootstrap,
        ca_filepath=os.environ.get("CA_FILE"),
        client_id=CLIENT_ID,
        clean_session=False,
        keep_alive_secs=6)

    print("Connecting to {} with client ID '{}'... ".format(
        os.environ.get("THING_ENDPOINT"), CLIENT_ID), end="")

    connected_future = mqtt_connection.connect()

    shadow_client = iotshadow.IotShadowClient(mqtt_connection)

    # Wait for connection to be fully established.
    connected_future.result()
    print("Connected.")

    try:
        # Subscribe to topics: delta, update_success, update_rejected, get_success, get_rejected
        print("Subscribing to Delta events... ", end="")
        delta_subscribed_future, _ = shadow_client.subscribe_to_shadow_delta_updated_events(
            request=iotshadow.ShadowDeltaUpdatedSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_shadow_delta_updated)

        # Wait for subscription to succeed
        delta_subscribed_future.result()
        print("Subscribed.")

        print("Subscribing to Update responses... ", end="")
        update_accepted_subscribed_future, _ = shadow_client.subscribe_to_update_shadow_accepted(
            request=iotshadow.UpdateShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_shadow_accepted)

        update_rejected_subscribed_future, _ = shadow_client.subscribe_to_update_shadow_rejected(
            request=iotshadow.UpdateShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_shadow_rejected)

        # Wait for subscriptions to succeed
        update_accepted_subscribed_future.result()
        update_rejected_subscribed_future.result()
        print("Subscribed.")

        print("Subscribing to Get responses... ", end="")
        get_accepted_subscribed_future, _ = shadow_client.subscribe_to_get_shadow_accepted(
            request=iotshadow.GetShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_get_shadow_accepted)

        get_rejected_subscribed_future, _ = shadow_client.subscribe_to_get_shadow_rejected(
            request=iotshadow.GetShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_get_shadow_rejected)

        # Wait for subscriptions to succeed
        get_accepted_subscribed_future.result()
        get_rejected_subscribed_future.result()
        print("Subscribed.")

        # Issue request for shadow's current state.
        print("Requesting current shadow state... ", end="")
        publish_get_future = shadow_client.publish_get_shadow(
            request=iotshadow.GetShadowRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE)

        # Ensure that publish succeeds
        publish_get_future.result()
        print("Received.")

        while (True):
            loop()

    except KeyboardInterrupt:
#         f.close()
        exit("Caught KeyboardInterrupt, terminating connections")

    except Exception as e:
        exit(e)

    # Wait for everything to finish
    is_done.wait()
