#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Default I2C address is 0x40
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const int SERVO_MIN = 125;
const int SERVO_MAX = 525;
const int CHANNEL = 0;

void setup() {
  Serial.begin(9600);
  Serial.println("PCA9685 Servo Sweep Test Started!");
  
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);
}

void loop() {
  Serial.println("Moving to 0 degrees (Open)");
  setServoAngle(CHANNEL, 0);
  delay(2000);
  
  Serial.println("Moving to 90 degrees (Closed)");
  setServoAngle(CHANNEL, 90);
  delay(2000);
}

void setServoAngle(int channel, int angle) {
  angle = constrain(angle, 0, 180);
  int pulse = map(angle, 0, 180, SERVO_MIN, SERVO_MAX);
  pwm.setPWM(channel, 0, pulse);
}
