import numpy as np
import librosa
import os

def rounding(min_value, max_value,value):
    
    if value < min_value:
        return min_value
    
    if value > max_value:
        return max_value
    
    return value

class AudioAnalyzer:  
    def __init__(self, max_pixels):
#         self.frequencies_index_ratio = 0
#         self.time_index_ratio = 0
#         self.spectrogram = None
        self._min_pixel = 0
        self._max_pixel = max_pixels
        self._pixel = 0
#         self._last_amp = None
        
    def load(self,filename):
        time_series, self._sample_rate = librosa.load(filename)
        
        cur_min_amp = np.amin(time_series)
        if(cur_min_amp<0):
            self._time_series = [abs(x) for x in time_series]
        else:
            self._time_series = time_series
        self._max_amp = np.amax(self._time_series)
        self._min_amp = np.amin(self._time_series)
        print("Max Amp: ",self._max_amp)
        print("Min Amp: ",self._min_amp)
            
    def update(self,time):
        amp = abs(self._time_series[int(time*self._sample_rate)])
        cur_pixel = int((amp/self._max_amp)*self._max_pixel)
        
        if(self._pixel > cur_pixel):
            self._pixel -= 1  
        
        if(self._pixel < cur_pixel):
            self._pixel += 1
#         else:
#             self._pixel += 1

        self._pixel = rounding(self._min_pixel,self._max_pixel,self._pixel)
        
        return int(self._pixel)
    
    def get_max_amp(self):
        return self._max_amp
    
#     def get_sample_rate(self):
#         return self._sample_rate
    
#     def show(self):
#         librosa.display.specshow(self.spectrogram, y_axis='log', x_axis='time')
    
#     def get_amplitude(self, target_time, freq):
#         return self.spectrogram[int(freq*self.frequencies_index_ratio)][int(target_time*self.time_index_ratio)]
      