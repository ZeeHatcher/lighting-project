void bounceBetween(uint32_t color, uint16_t start, uint16_t finish, uint16_t len) {
  while (true) {
    int path_length = finish - start ;

    // Get light snake moving forward down the line.
    for (int i = 0 ; i < path_length ; i++) {
      // Populate the snake
      for (int j = 0 ; j < len ; j++) {
        if ((j + i + start) <= finish) {
          strip.setPixelColor(i + j + start, color) ;
          strip.show() ;
        }
      }
      // Write the end of the snake to be "off"
      if ( (i + start) <= (finish - len) ) {
        strip.setPixelColor(i + start, 0) ;
        delay(50) ;
      }
    }

    // Get the light snake moving backwards.
    for (int i = 0 ; (-1)*i < path_length ; i--) {
      // Populate the snake
      for (int j = 0 ; (-1)*j < len ; j--) {
        if ((i + j + finish) >= start) {
          strip.setPixelColor(i + j + finish, color) ;
          strip.show() ;
        }
      }
      // Write the end of the snake to be "off"
      if ( (i + finish) >= (len + start) ) {
        strip.setPixelColor(i + finish, 0) ;
        delay(50) ;
      }
    }
  }
}

uint32_t randColor() {
  uint8_t red = random(0, 255) ;
  uint8_t blue = random(0, 255) ;
  uint8_t green = random(0, 255) ;

  uint32_t color = 0x000000 ; //GRB

  color = color | (green << 16) ;
  color = color | (red << 8) ;
  color = color | blue ;

  return color ;
}
