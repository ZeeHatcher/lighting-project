#include <stdio.h>
#include <stdlib.h>

#include <Adafruit_DotStar.h>
#include <SPI.h>

#define NUM_PIXELS 5

Adafruit_DotStar strip(NUM_PIXELS, DOTSTAR_BRG);

void setup() {
  strip.begin();
  strip.show();

  Serial.begin(115200);
}

const int INPUT_SIZE = (7 * NUM_PIXELS) - 1;
const char * DELIM = ",";

char input[INPUT_SIZE + 1];

void loop() {
  if (Serial.available() > 0) {
    byte size = Serial.readBytes(input, INPUT_SIZE);

    byte i = 0;
    char * color = strtok(input, DELIM);
    while (color != NULL) {
      strip.setPixelColor(i, strtoul(color, NULL, 16));
      
      color = strtok(NULL, DELIM);
      i++;
    }
  
    strip.show();
  }
}
