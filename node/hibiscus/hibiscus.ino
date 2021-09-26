#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>
#include <WiFi.h>

#include <Adafruit_DotStar.h>
#include <SPI.h>

#include <Adafruit_MPU6050.h>

#include "LightingConfig.h"

#define WIFI_TIMEOUT_MS 20000

IPAddress server(address[0], address[1], address[2], address[3]);
WiFiClient client;

Adafruit_DotStar strip(NUM_PIXELS, 23, 18, DOTSTAR_BGR);
Adafruit_MPU6050 mpu;
Adafruit_Sensor* accel;

sensors_event_t event;

void connectToWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttemptTime = millis();

  while(WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < WIFI_TIMEOUT_MS) {
    Serial.print(".");
    delay(100);
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(" Failed!");
  } else {
    Serial.println(" Connected!");
  }
}

void connectToServer() {
  if (client.connect(server, 12345)) {
    Serial.println("Connected to server.");
  } else {
    Serial.println("Failed to connect to server.");
  }
}

void setup() {
  Serial.begin(9600);
  
  strip.begin();

  if (!mpu.begin()) {
    Serial.println("Failed to find Hibiscus Sense MPU6050 chip!");
  }

  accel = mpu.getAccelerometerSensor();

  strip.clear();
  strip.show();
}

void loop() {
  if (WiFi.status() == WL_CONNECTED && client.connected()) {
    if (client.available() >= NUM_PIXELS * 3) {
      uint8_t r[NUM_PIXELS] = {0};
      uint8_t g[NUM_PIXELS] = {0};
      uint8_t b[NUM_PIXELS] = {0};

      // Read RGB into channels
      client.read(r, NUM_PIXELS);
      client.read(g, NUM_PIXELS);
      client.read(b, NUM_PIXELS);

      // Set RGB value for each DotStar pixel
      for (int i = 0; i < NUM_PIXELS; i++) {
        strip.setPixelColor(i, (uint8_t) r[i], (uint8_t) g[i], (uint8_t) b[i]);
      }
      
      strip.show();
    }

    accel->getEvent(&event);
    double mag = sqrt(pow(event.acceleration.x, 2) + pow(event.acceleration.y, 2) + pow(event.acceleration.z, 2));
    client.print(mag);
    client.print("|");

    // Limit loop rate to 30 frames per second
    delay(34);
  } else if (WiFi.status() != WL_CONNECTED) {
    // (Re)Connect to WiFi network
    connectToWiFi();
  } else if (!client.connected()) {
    // (Re)Connect to server
    client.stop();
    connectToServer();
    delay(1000);
  }
}
