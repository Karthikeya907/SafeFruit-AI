# SafeFruit-AI

SAFEFRUIT AI — An intelligent automated system for AI-based fruit quality inspection, washing, UV sanitization, and smart sorting.

## Project Overview

SAFEFRUIT AI is an automated fruit inspection and sorting system that integrates hardware sensors, an Arduino-controlled conveyor and washing mechanism, and a Google Gemini AI-powered web dashboard to evaluate fruit quality.

## Key Features

- Live camera feed for visual inspection
- Gemini AI integration for fruit identification and defect detection
- Hardware monitoring including MQ-135 (Gas), pH, and distance sensors
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

## ⚠️ Important Setup & Configuration

Before running SAFEFRUIT AI, all required hardware must be properly connected to the laptop/PC and configured through the application.

### 1. Connect the Hardware First

Before opening and testing the system, connect the required hardware to the laptop/PC.

Make sure the following are properly connected:

- Arduino Nano
- USB Camera
- Arduino USB/Serial connection
- Required power connections for the hardware
- Any other USB devices required by the system

The Arduino must be detected by the laptop/PC before starting the testing process.

### 2. Open the Application / Website

After starting the SAFEFRUIT AI application, open the web dashboard in the browser.

**Do not start the main system immediately.**

First open the **Settings** section of the application.

### 3. Configure Settings

The following settings must be configured before running the system:

- **Arduino COM Port** – Select the COM port assigned to the Arduino Nano.
- **Camera Index** – Select the correct camera index for the connected USB camera.
- **Gemini API Key** – Enter the Google Gemini API key required for AI analysis.
- **Other Hardware Settings** – Configure any additional settings required by the connected hardware.

### 4. Test All Connections

After configuring the settings, test the system before starting the complete workflow.

The following should be tested:

- Arduino connection
- COM port / Serial communication
- USB camera connection
- Camera index and live camera feed
- Sensor communication
- Conveyor motor
- Water pumps
- Servo motors
- Relay / UV system
- Gemini AI API connection

Make sure the required tests are successful before running the complete fruit inspection process.

### 5. Run the System

After all connections and tests are successful:

1. Save the configured settings.
2. Confirm the correct Arduino COM port.
3. Confirm the correct camera index.
4. Confirm that the Gemini API key is valid.
5. Confirm that the camera feed is working.
6. Confirm that the Arduino is communicating correctly.
7. Start the SAFEFRUIT AI inspection workflow.

> **IMPORTANT:** Always connect the required hardware to the laptop/PC first, then open the application, configure the COM port, camera index, Gemini API key, and other required settings. Test all connections before running the main system.

> **NOTE:** The Arduino COM port and camera index can be different on different computers. Always check the available devices on the computer and select the correct values from the application's Settings page.

> **SECURITY NOTE:** Never upload or publish your actual Gemini API key to GitHub. Store API keys securely using environment variables or a local `.env` file.

## Hardware

- Arduino Nano
- USB Camera
- L298N Motor Driver – 2
- 12V DC Motor – 2
- HC-SR04 Ultrasonic Sensor
- pH Sensor
- MQ-135 Gas Sensor
- MG90S Servo
- MG996R Servo – 2
- Servo Driver Module
- Water Pump – 2
- Relay Module – 1
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
