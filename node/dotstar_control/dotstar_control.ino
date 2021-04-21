#include <stdio.h>
#include <stdlib.h>

#include <Adafruit_DotStar.h>
#include <SPI.h>

#define NUM_PIXELS 8

Adafruit_DotStar strip(NUM_PIXELS, DOTSTAR_BGR);

void setup() {
  Serial.begin(115200);
  
  strip.begin();
  strip.clear();
  strip.show();
}

void loop() {
  if (Serial.available() > 0) {
    char r[NUM_PIXELS] = {0};
    char g[NUM_PIXELS] = {0};
    char b[NUM_PIXELS] = {0};
    
    // Read RGB into channels
    Serial.readBytes(r, NUM_PIXELS);
    Serial.readBytes(g, NUM_PIXELS);
    Serial.readBytes(b, NUM_PIXELS);
    
    // Set RGB value for each DotStar pixel
    for (int i = 0; i < NUM_PIXELS; i++) {
      strip.setPixelColor(i, (uint8_t) r[i], (uint8_t) g[i], (uint8_t) b[i]);
    }
    
    strip.show();
  }
}

