#include <stdio.h>
#include <Adafruit_DotStar.h>
#include <SPI.h>
#define NUM_PIXELS 30
#define DATAPIN    4
#define CLOCKPIN   5
Adafruit_DotStar strip(NUM_PIXELS, DATAPIN, CLOCKPIN, DOTSTAR_BRG);

unsigned int pinStatus = 0;

void setup() {
  Serial.begin(115200);
  strip.begin(); // Initialize pins for output
  strip.clear();
  strip.show();  // Turn all LEDs off ASAP
  strip.setBrightness(20);

}

void loop() {
  if (Serial.available() > 0) {
    // say what you got:
    pinStatus = Serial.parseInt();
    switch (pinStatus)
    {
      case 0:
        // off the strip
        strip.clear();
        strip.show();
        break;
      case 1:
        strip.clear();
        strip.show();
        DotStar_Rainbow();
        break;
      case 2:
        strip.clear();
        strip.show();
        DotStar_Move();
        break;
      case 3:
        //light_bounce
        strip.clear();
        strip.show();
        uint32_t color = randColor() ;
        bounceBetween(color, 2, 12, 4) ;
        break;
      case 4:
        strip.clear();
        strip.show();
        break;

      default:
        break;
    }
  }
}
