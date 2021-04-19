#include <stdio.h>
#include <stdlib.h>

#include <Adafruit_DotStar.h>
#include <SPI.h>

#define NUM_PIXELS 144

Adafruit_DotStar strip(NUM_PIXELS, DOTSTAR_BRG);

void setup() {
  Serial.begin(115200);
  
  strip.begin();
  strip.show();
}

const int SIZE_BUFFER = NUM_PIXELS;

void loop() {
  if (Serial.available() > 0) {
    char r[SIZE_BUFFER] = {0};
    char g[SIZE_BUFFER] = {0};
    char b[SIZE_BUFFER] = {0};
    
    // Read RGB into channels
    Serial.readBytes(r, SIZE_BUFFER);
    Serial.readBytes(g, SIZE_BUFFER);
    Serial.readBytes(b, SIZE_BUFFER);
    
    // Derive RGB value for each DotStar pixel
    for (int i = 0; i < NUM_PIXELS; i++) {
      // DotStar library uses GRB (not RGB)
      // For correct conversion, byte array values is LSB -> MSB
      char bytes[4] = {b[i], r[i], g[i]};
      uint32_t color;
      
      // Convert bytes to 32-bit integer
      memcpy(&color, bytes, sizeof(uint32_t));
      
      strip.setPixelColor(i, color);
    }
    
    strip.show();
  }
}

