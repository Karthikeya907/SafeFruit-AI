# SafeFruit-AI
SAFEFRUIT AI — An intelligent automated system for AI-based fruit quality inspection, washing, UV sanitization, and smart sorting.
## Project Overview
SAFEFRUIT AI is an automated fruit inspection and sorting system that integrates hardware sensors, an Arduino-controlled conveyor and washing mechanism, and a Google Gemini AI-powered web dashboard to evaluate fruit quality.

## Key Features
- Live camera feed for visual inspection
- Gemini AI integration for fruit identification and defect detection
- Hardware monitoring including MQ135 (Gas), pH, and distance sensors
- Automated conveyor and washing stage control via Arduino
- Web-based dashboard for real-time telemetry and AI results

## System Architecture
The system consists of a Python Flask backend, a web frontend dashboard, and an Arduino microcontroller. The Arduino handles sensor data collection and actuator control (conveyor, pumps, gates), while the Python backend processes camera feeds and communicates with the Gemini AI API for inspection.

## Project Workflow
1. Hardware initialization and system check.
2. Fruit enters Stage 1 (Conveyor).
3. Sensors (Gas, pH, Distance) collect environmental and fruit data.
4. Camera captures images of the fruit.
5. Images are sent to Gemini AI for analysis.
6. The dashboard displays the AI confidence and defect results.
7. Fruit is routed based on the AI analysis (e.g., washing, sorting).

## Hardware
- Arduino Nano
- USB Camera
- L298N Motor Driver – 2
- 12V DC Motor – 2
- HC-SR04 Ultrasonic Sensor
- pH Sensor
- MQ-135 Gas Sensor
- mg90s servo
- mg996r servo -2 
- Servo Driver Module
- Water Pump – 2
- Relay Module -1
- UV LED Strip
- 12V Battery
- Buck Converter
- Conveyor Belt
- PVC/Aluminium Frame
- Jumper Wires
- PCB/Perfboard
- Terminal Blocks
- Screws & Nuts
- Power Switch
- Connecting Wires
- Water Tank
- Water Pipes/Tube
- Fruit Collection Tray
- Laptop/PC for AI Processing

## Software
- Python 3
- Flask (Web Server)
- OpenCV (Camera processing)
- PySerial (Arduino communication)
- Google Gemini API (AI Analysis)
- HTML/CSS/JS (Frontend Dashboard)


## Project Status
Active Development.

## Future Scope
Further enhancements to the AI model for broader fruit classification, improved sorting mechanisms, and historical data analytics.
