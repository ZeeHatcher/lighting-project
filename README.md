# IoT Showcase System: Lighting Project
**Assignment Unit:** SWE40001 Software Engineering Project A, SWE40002 Software Engineering Project B  
**Language:** C++, Python, HTML, CSS, JavaScript  
**Description:** An IoT-based, cloud-enabled lightsaber, capable of remote control and different light patterns using various input. Lightsaber prototyped and built using ESP32 and Adafruit libraries, edge computing done using Python, cloud implementation with AWS, and web dashboard built using Python Flask, Bootstrap CSS, and jQuery.

## Features
+ Wireless connectivity and data transfer from lightsaber to edge
+ Lightsaber output rendered and calculated by edge device, allowing for increased flexibility in programming patterns and modes 
+ Various lighting modes and patterns
  + Basic Mode - Selection of patterns ("blink", "rainbow", etc.) and custom colors
  + Image Mode - Iterate through rows within an image for persistence-of-vision when swung around
  + Music Mode - Audio frequency visualizer from .mp3/.wav files
  + Microphone - Audio frequency visualizer from microphone input
  + Lightsaber Mode - Generate lightsaber sounds and effects when swung, powered by on-board IMU sensor
+ Remote control through the cloud, using AWS IoT Core, DynamoDB, S3, Lambda and EC2
+ Web dashboard featuring minimalistic design, clean animations, and responsive layout with Bootstrap CSS.
