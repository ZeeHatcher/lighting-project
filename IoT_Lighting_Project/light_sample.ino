void DotStar_Move() {
  int      head  = 0, tail = -10; // Index of first 'on' and 'off' pixels
  uint32_t color = 0xFF0000;      // 'On' color (starts red)
  while (true) {
    strip.setBrightness(10);
    strip.setPixelColor(head, color); // 'On' pixel at head
    strip.setPixelColor(tail, 0);     // 'Off' pixel at tail
    strip.show();                     // Refresh strip
    delay(20);

    if (++head >= NUM_PIXELS) {       // Increment head index.  Off end of strip?
      head = 0;                       //  Yes, reset head index to start
      if ((color >>= 8) == 0)         //  Next color (R->G->B) ... past blue now?
        color = 0xFF0000;             //   Yes, reset to red
    }
    if (++tail >= NUM_PIXELS) tail = 0; // Increment, reset tail index
  }
}


void DotStar_Rainbow() {
  strip.setBrightness(10);
  for (long firstPixelHue = 0; firstPixelHue < 5 * 65536; firstPixelHue += 256) {
    for (int i = 0; i < strip.numPixels(); i++) { // For each pixel in strip...
      int pixelHue = firstPixelHue + (i * 65536L / strip.numPixels());
      strip.setPixelColor(i, strip.gamma32(strip.ColorHSV(pixelHue)));
    }
    strip.show(); // Update strip with new contents
    delay(20);  // Pause for a moment
  }

}
