/*
  SAFEFRUIT AI - Stage 1 & 2 Firmware
  ------------------------------------
  Implements the full inspection sequence.
*/

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const int TRIG1 = 12, ECHO1 = 3;
// L298N Driver 1
const int CONV_IN1 = 8, CONV_IN2 = 9, CONV_ENA = 10;
const int PUMP_IN_1 = 6, PUMP_IN_2 = 7;
// L298N Driver 2
const int PUMP_OUT_1 = 4, PUMP_OUT_2 = 5;

// UV Relay Module
const int RELAY_PIN = 11;

const int GAS_SENSOR = A0;
const int PH_SENSOR = A1;
const int GAS_THRESHOLD = 300; // Calibrate this value

const int SERVO_ENTRY_DOOR = 0;
const int SERVO_CH1 = 3;
const int SERVO_END_DOOR = 2;

const int ENTRY_DOOR_OPEN = 120;
const int ENTRY_DOOR_CLOSED = 0;
const int END_DOOR_OPEN = 85;
const int END_DOOR_CLOSED = 0;
const int SERVO_CH1_UP = 0;
const int SERVO_CH1_DOWN = 160;

const int SERVO_MIN = 125;
const int SERVO_MAX = 525;
const int FRUIT_DISTANCE_CM = 10;
const int CONVEYOR_SPEED = 150;

enum State {
  IDLE,
  WAIT_FRUIT,
  RUN_CONVEYOR_EXTRA_S1,
  WAIT_IMAGE_1_CMD,
  RUN_CONVEYOR_1,
  WAIT_IMAGE_2_CMD,
  RUN_CONVEYOR_2,
  WAIT_IMAGE_3_CMD,
  WAIT_RESULT,
  RUN_CONVEYOR_FAIL,
  RUN_CONVEYOR_PASS,
  READ_GAS_SENSOR,
  WAIT_IN_PUMP,
  READ_PH_SENSOR,
  WAIT_OUT_PUMP,
  STAGE3_MOVE_IN,
  STAGE3_UV_ON,
  STAGE3_MOVE_OUT,
  STAGE3_FAIL_DISPOSE
};

State currentState = IDLE;
unsigned long stateTimer = 0;
String serialBuffer = "";
int currentGasValue = 0;
bool fruitPassedStage2 = false;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG1, OUTPUT); pinMode(ECHO1, INPUT);
  pinMode(GAS_SENSOR, INPUT); pinMode(PH_SENSOR, INPUT);
  
  pinMode(CONV_IN1, OUTPUT); pinMode(CONV_IN2, OUTPUT); pinMode(CONV_ENA, OUTPUT);
  pinMode(PUMP_IN_1, OUTPUT); pinMode(PUMP_IN_2, OUTPUT);
  pinMode(PUMP_OUT_1, OUTPUT); pinMode(PUMP_OUT_2, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN,HIGH);
  
  conveyorStop();
  pumpInStop();
  pumpOutStop();

  Serial.println(F("Process: Initializing PWM Servo Driver..."));
  pwm.begin();
  Wire.setWireTimeout(3000, true);
  pwm.setPWMFreq(50);
  delay(200);
  
  Serial.println(F("Process: Setting initial servo positions..."));
  setServoAngle(SERVO_ENTRY_DOOR, ENTRY_DOOR_OPEN);
  Serial.println(F("stage1_door:OPEN"));
  delay(1000);
  setServoAngle(SERVO_END_DOOR, END_DOOR_OPEN);
  Serial.println(F("stage3_door:OPEN"));
  delay(1000);
  setServoAngle(SERVO_CH1, SERVO_CH1_UP); // Idle state is UP
  delay(1000);

  Serial.println(F("Process: Setup complete. Waiting for START_INSPECTION from Python."));
}

void loop() {
  handleSerialInput();

  // Continuously print ultrasonic distance to the Serial Monitor every 500ms
  static unsigned long lastUltrasonicPrint = 0;
  if (millis() - lastUltrasonicPrint >= 500) {
    long dist = readDistanceCM(TRIG1, ECHO1);
    Serial.print(F("distance:"));
    Serial.println(dist);
    lastUltrasonicPrint = millis();
  }

  switch (currentState) {
    case IDLE:
      break;

    case WAIT_FRUIT:
      {
        long dist = readDistanceCM(TRIG1, ECHO1);

        // Add a check to ensure dist is greater than 2 to filter out noise/0 values
        if (dist > 2 && dist <= FRUIT_DISTANCE_CM) {
          Serial.print(F("Process: Fruit detected at "));
          Serial.print(dist);
          Serial.println(F(" cm! Stopping conveyor briefly to prevent power crash..."));
          conveyorStop();
          delay(1000); // 1 second delay to let voltage completely recover
          
          Serial.println(F("Process: Closing entry door to block fruit..."));
          setServoAngle(SERVO_ENTRY_DOOR, ENTRY_DOOR_CLOSED);
          Serial.println(F("stage1_door:CLOSED"));
          delay(1000);
          
          Serial.println(F("Process: Moving conveyor for 2 extra seconds to align against door..."));
          conveyorRun(CONVEYOR_SPEED);
          stateTimer = millis();
          currentState = RUN_CONVEYOR_EXTRA_S1;
        }
      }
      break;

    case RUN_CONVEYOR_EXTRA_S1:
      if (millis() - stateTimer >= 2000) {
        conveyorStop();
        Serial.println(F("Process: Conveyor stopped. Requesting 1st image."));
        Serial.println(F("TAKE_IMAGE_1"));
        currentState = WAIT_IMAGE_1_CMD;
      }
      break;
      
    case RUN_CONVEYOR_1:
      if (millis() - stateTimer >= 2000) {
        conveyorStop();
        Serial.println(F("Process: Conveyor stepped 2 seconds. Requesting 2nd image."));
        Serial.println(F("TAKE_IMAGE_2"));
        currentState = WAIT_IMAGE_2_CMD;
      }
      break;
      
    case RUN_CONVEYOR_2:
      if (millis() - stateTimer >= 2000) {
        conveyorStop();
        Serial.println(F("Process: Conveyor stepped 2 seconds. Requesting 3rd image."));
        Serial.println(F("TAKE_IMAGE_3"));
        currentState = WAIT_IMAGE_3_CMD;
      }
      break;

    case RUN_CONVEYOR_FAIL:
      if (millis() - stateTimer >= 10000) {
        conveyorStop();
        delay(1500); // Power stabilize
        setServoAngle(SERVO_END_DOOR, END_DOOR_OPEN); // Open it back up for the next fruit
        Serial.println(F("stage3_door:OPEN"));
        delay(1000);
        Serial.println(F("Process: Rejected fruit disposed. System ready for next fruit."));
        currentState = IDLE;
      }
      break;

    case RUN_CONVEYOR_PASS:
      if (millis() - stateTimer >= 1250) {
        conveyorStop();
        delay(500);
        
        Serial.println(F("Process: Lowering Gas Sensor (Channel 1 Servo DOWN) for detection..."));
        setServoAngle(SERVO_CH1, SERVO_CH1_DOWN);
        delay(1500); // Wait for servo to finish moving down
        
        Serial.println(F("Process: Detecting gas for 5 seconds..."));
        stateTimer = millis();
        currentState = READ_GAS_SENSOR;
      }
      break;

    case READ_GAS_SENSOR:
      if (millis() - stateTimer >= 5000) {
        long gasSum = 0;
        for (int i=0; i<10; i++) {
          gasSum += analogRead(GAS_SENSOR);
          delay(10);
        }
        currentGasValue = gasSum / 10;
        float mqVoltage = currentGasValue * (5.0 / 1023.0);
        
        Serial.println(F("---------------------------------"));
        Serial.print(F("MQ135 Raw Value : "));
        Serial.println(currentGasValue);
        Serial.print(F("MQ135 Voltage   : "));
        Serial.print(mqVoltage, 2);
        Serial.println(F(" V"));
        Serial.println(F("---------------------------------"));
        
        Serial.print(F("mq135:"));
        Serial.println(currentGasValue);
        
        Serial.println(F("Process: Lifting Gas Sensor (Channel 1 Servo UP)..."));
        setServoAngle(SERVO_CH1, SERVO_CH1_UP);
        delay(1500); // Wait for servo to finish moving up
        
        Serial.println(F("Process: Turning ON Water Pump (IN pump) for 10 seconds..."));
        pumpInRun();
        stateTimer = millis();
        currentState = WAIT_IN_PUMP;
      }
      break;

    case WAIT_IN_PUMP:
      if (millis() - stateTimer >= 10000) {
        pumpInStop();
        delay(1500); // 1.5s delay to let power stabilize after pump stops
        
        Serial.println(F("Process: Waiting 10 seconds for pH Sensor accuracy..."));
        stateTimer = millis();
        currentState = READ_PH_SENSOR;
      }
      break;

    case READ_PH_SENSOR:
      if (millis() - stateTimer >= 10000) {
        long phSum = 0;
        for (int i=0; i<10; i++) {
          phSum += analogRead(PH_SENSOR);
          delay(10);
        }
        float rawPh = phSum / 10.0;
        float voltage = rawPh * (5.0 / 1023.0);
        float phValue = 7.0 + ((2.5 - voltage) / 0.18);
        
        Serial.println(F("---------------------------------"));
        Serial.print(F("pH Raw Value    : "));
        Serial.println(rawPh, 1);
        Serial.print(F("pH Voltage      : "));
        Serial.print(voltage, 2);
        Serial.println(F(" V"));
        Serial.print(F("Estimated pH    : "));
        Serial.println(phValue, 2);
        Serial.println(F("---------------------------------"));
        
        Serial.print(F("ph:"));
        Serial.println(phValue, 2);
        
        bool gasPass = (currentGasValue < GAS_THRESHOLD);
        bool phPass = (phValue >= 5.0);
        
        if (gasPass && phPass) {
          Serial.println(F("FINAL_RESULT: PASS"));
          fruitPassedStage2 = true;
        } else {
          Serial.print(F("FINAL_RESULT: FAIL, Reason: "));
          if (!gasPass) Serial.print(F("High Gas "));
          if (!phPass) Serial.print(F("Low pH"));
          Serial.println();
          fruitPassedStage2 = false;
        }
        
        // Note: Gas sensor is already UP, no need to lower it here.
        
        Serial.println(F("Process: Turning ON OUT pump for 10 seconds..."));
        pumpOutRun();
        stateTimer = millis();
        currentState = WAIT_OUT_PUMP;
      }
      break;
      
    case WAIT_OUT_PUMP:
      if (millis() - stateTimer >= 10000) {
        pumpOutStop();
        delay(1500);
        
        if (fruitPassedStage2) {
          Serial.println(F("Process: Moving fruit to UV Sterilization (Stage 3)..."));
          conveyorRun(CONVEYOR_SPEED);
          stateTimer = millis();
          currentState = STAGE3_MOVE_IN;
        } else {
          Serial.println(F("Process: Fruit failed Stage 2. Closing end door and disposing..."));
          setServoAngle(SERVO_END_DOOR, END_DOOR_CLOSED);
          Serial.println(F("stage3_door:CLOSED"));
          delay(1000);
          conveyorRun(CONVEYOR_SPEED);
          stateTimer = millis();
          currentState = STAGE3_FAIL_DISPOSE;
        }
      }
      break;

    case STAGE3_MOVE_IN:
      if (millis() - stateTimer >= 2250) {
        conveyorStop();
        delay(500);
        Serial.println(F("Process: Turning ON UV Sterilization for 10 seconds..."));
        digitalWrite(RELAY_PIN, LOW);
        Serial.println(F("uv:ON"));
        stateTimer = millis();
        currentState = STAGE3_UV_ON;
      }
      break;

    case STAGE3_UV_ON:
      if (millis() - stateTimer >= 10000) {
        digitalWrite(RELAY_PIN, HIGH);
        Serial.println(F("uv:OFF"));
        delay(500);
        Serial.println(F("Process: UV complete. Moving fruit to healthy bin..."));
        conveyorRun(CONVEYOR_SPEED);
        stateTimer = millis();
        currentState = STAGE3_MOVE_OUT;
      }
      break;

    case STAGE3_MOVE_OUT:
      if (millis() - stateTimer >= 10000) {
        conveyorStop();
        delay(500);
        Serial.println(F("Process: Fruit safely packed! System ready for next fruit."));
        currentState = IDLE;
      }
      break;

    case STAGE3_FAIL_DISPOSE:
      if (millis() - stateTimer >= 10000) {
        conveyorStop();
        delay(1500);
        setServoAngle(SERVO_END_DOOR, END_DOOR_OPEN); // Open it back up for the next fruit
        Serial.println(F("stage3_door:OPEN"));
        delay(1000);
        Serial.println(F("Process: Rejected fruit disposed. System ready for next fruit."));
        currentState = IDLE;
      }
      break;

    case WAIT_IMAGE_1_CMD:
    case WAIT_IMAGE_2_CMD:
    case WAIT_IMAGE_3_CMD:
    case WAIT_RESULT:
      break;
  }
}

void handleSerialInput() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      serialBuffer.trim();
      processCommand(serialBuffer);
      serialBuffer = "";
    } else if (c != '\r') {
      serialBuffer += c;
    }
  }
}

void processCommand(String cmd) {
  if (cmd.length() == 0) return;

  if (cmd == "START_INSPECTION") {
    Serial.println(F("Process: START_INSPECTION received. Stopping any active motors first..."));
    conveyorStop();
    pumpInStop();
    pumpOutStop();
    delay(1000); // 1 sec delay to stabilize power
    
    Serial.println(F("Process: Ensuring gas sensor is UP and end door is OPEN..."));
    setServoAngle(SERVO_CH1, SERVO_CH1_UP);
    setServoAngle(SERVO_END_DOOR, END_DOOR_OPEN);
    Serial.println(F("stage3_door:OPEN"));
    delay(1000);
    
    Serial.println(F("Process: Ensuring entry door is OPEN to allow fruit in..."));
    setServoAngle(SERVO_ENTRY_DOOR, ENTRY_DOOR_OPEN);
    Serial.println(F("stage1_door:OPEN"));
    delay(1000); // 1 sec delay for servo to move and power to stabilize
    
    Serial.println(F("Process: Starting conveyor. Waiting for fruit..."));
    conveyorRun(CONVEYOR_SPEED);
    currentState = WAIT_FRUIT;
  } 
  else if (cmd == "STEP_CONVEYOR") {
    if (currentState == WAIT_IMAGE_1_CMD) {
      Serial.println(F("Process: Received STEP_CONVEYOR command. Running conveyor for 1 second..."));
      conveyorRun(CONVEYOR_SPEED);
      stateTimer = millis();
      currentState = RUN_CONVEYOR_1;
    } else if (currentState == WAIT_IMAGE_2_CMD) {
      Serial.println(F("Process: Received STEP_CONVEYOR command. Running conveyor for 1 second..."));
      conveyorRun(CONVEYOR_SPEED);
      stateTimer = millis();
      currentState = RUN_CONVEYOR_2;
    }
  } 
  else if (cmd == "PASS" || cmd == "FAIL" || cmd == "OPEN_DOOR") {
    if (currentState == WAIT_IMAGE_3_CMD || currentState == WAIT_RESULT) {
      Serial.print(F("Process: AI result ["));
      Serial.print(cmd);
      Serial.println(F("] received. Stopping conveyor to prevent power drop..."));
      conveyorStop();
      delay(1000);
      
      Serial.println(F("Process: Opening 1st door..."));
      setServoAngle(SERVO_ENTRY_DOOR, ENTRY_DOOR_OPEN);
      Serial.println(F("stage1_door:OPEN"));
      delay(1000);
      
      if (cmd == "FAIL") {
        Serial.println(F("Process: Closing END door for failed fruit..."));
        setServoAngle(SERVO_END_DOOR, END_DOOR_CLOSED);
        Serial.println(F("stage3_door:CLOSED"));
        delay(1000);
        Serial.println(F("Process: Running conveyor for 10 seconds to dispose fruit..."));
        conveyorRun(CONVEYOR_SPEED);
        stateTimer = millis();
        currentState = RUN_CONVEYOR_FAIL;
      } 
      else if (cmd == "PASS") {
        Serial.println(F("Process: Running conveyor for 1.25 seconds to move to Stage 2..."));
        conveyorRun(CONVEYOR_SPEED);
        stateTimer = millis();
        currentState = RUN_CONVEYOR_PASS;
      }
      else {
        // Just OPEN_DOOR
        currentState = IDLE;
      }
    }
  } 
  else if (cmd == "SIM_FRUIT") {
    if (currentState == WAIT_FRUIT) {
      Serial.println(F("Process: Manual fruit simulation triggered! Stopping conveyor..."));
      conveyorStop();
      delay(1000);
      
      Serial.println(F("Process: Closing entry door to block fruit..."));
      setServoAngle(SERVO_ENTRY_DOOR, ENTRY_DOOR_CLOSED);
      Serial.println(F("stage1_door:CLOSED"));
      delay(1000);

      Serial.println(F("Process: Moving conveyor for 2 extra seconds to align against door..."));
      conveyorRun(CONVEYOR_SPEED);
      stateTimer = millis();
      currentState = RUN_CONVEYOR_EXTRA_S1;
    }
  }
  else if (cmd == "STOP_SYSTEM") {
    Serial.println(F("Process: STOP_SYSTEM command received from Python. Forcing stop."));
    conveyorStop();
    pumpInStop();
    pumpOutStop();
    digitalWrite(RELAY_PIN, HIGH);
    Serial.println(F("uv:OFF"));
    setServoAngle(SERVO_CH1, SERVO_CH1_UP);
    setServoAngle(SERVO_END_DOOR, END_DOOR_OPEN);
    Serial.println(F("stage3_door:OPEN"));
    currentState = IDLE;
  }
}

void conveyorRun(int speed) {
  digitalWrite(CONV_IN1, HIGH);
  digitalWrite(CONV_IN2, LOW);
  analogWrite(CONV_ENA, speed);
  Serial.println(F("conveyor:ON"));
}

void conveyorStop() {
  analogWrite(CONV_ENA, 0);
  digitalWrite(CONV_IN1, LOW);
  digitalWrite(CONV_IN2, LOW);
  Serial.println(F("conveyor:OFF"));
}

void pumpInRun() {
  digitalWrite(PUMP_IN_1, HIGH);
  digitalWrite(PUMP_IN_2, LOW);
  Serial.println(F("washing:ON"));
}

void pumpInStop() {
  digitalWrite(PUMP_IN_1, LOW);
  digitalWrite(PUMP_IN_2, LOW);
  Serial.println(F("washing:OFF"));
}

void pumpOutRun() {
  digitalWrite(PUMP_OUT_1, HIGH);
  digitalWrite(PUMP_OUT_2, LOW);
}

void pumpOutStop() {
  digitalWrite(PUMP_OUT_1, LOW);
  digitalWrite(PUMP_OUT_2, LOW);
}

int currentServoAngles[16] = {0}; // Track angles for PCA9685 channels

void setServoAngle(int channel, int targetAngle) {
  targetAngle = constrain(targetAngle, 0, 180);
  int pulse = map(targetAngle, 0, 180, SERVO_MIN, SERVO_MAX);
  pwm.setPWM(channel, 0, pulse);
  currentServoAngles[channel] = targetAngle;
}

long readDistanceCM(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return 9999;
  return duration * 0.0343 / 2;
}