/*
  Ultrasonic Sensor Test Code
  ---------------------------
  Upload this to your Arduino Nano to test the ultrasonic sensor independently.
  Open the Serial Monitor at 9600 baud to see the distance readings.

  Wiring:
  - VCC to 5V
  - GND to GND
  - TRIG to Pin 2
  - ECHO to Pin 3
*/

const int TRIG_PIN = 2;
const int ECHO_PIN = 3;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  Serial.println("Ultrasonic Sensor Test Started!");
  Serial.println("-------------------------------");
}

void loop() {
  long distance = readDistanceCM(TRIG_PIN, ECHO_PIN);
  
  Serial.print("Distance: ");
  if (distance == 9999) {
    Serial.println("Out of range or disconnected");
  } else {
    Serial.print(distance);
    Serial.println(" cm");
  }
  
  delay(500); // Wait half a second before the next reading
}

// Function to read distance in centimeters
long readDistanceCM(int trigPin, int echoPin) {
  // Clear the trigPin by setting it LOW:
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // Trigger the sensor by setting the trigPin high for 10 microseconds:
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Read the echoPin. pulseIn() returns the duration (length of the pulse) in microseconds:
  // We use a 30000 microsecond timeout (~5 meters max range)
  long duration = pulseIn(echoPin, HIGH, 30000); 
  
  if (duration == 0) {
    return 9999; // 9999 means timeout (no echo received)
  }
  
  // Calculate the distance:
  // Speed of sound is 0.0343 cm/microsecond
  // Distance = (Duration * 0.0343) / 2
  return duration * 0.0343 / 2;
}
