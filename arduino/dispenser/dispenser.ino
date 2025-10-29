#include <Wire.h>
#include <RTClib.h>
#include <Servo.h>

RTC_DS3231 rtc;
Servo servo;

// Pin definitions
const int SERVO_PIN = 3;   // SG90 signal pin (yellow/orange wire)
const int BUZZER_PIN = 8;  // Active buzzer, LOW = ON

// Medicine schedule slots
const int NUM_SLOTS = 3;
int hours[NUM_SLOTS] = {9, 13, 20};
int minutes_[NUM_SLOTS] = {0, 0, 0};
int currentSlot = 0;

bool dispensing = false;
String jobId = "";

void setup() {
  Serial.begin(9600);
  Wire.begin();
  rtc.begin();

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, HIGH); // buzzer off (LOW = ON)

  servo.attach(SERVO_PIN);
  servo.write(0); // home position

  delay(1500); // allow serial bridge to connect
  Serial.println("ARDUINO_CONNECTED");
}

void loop() {
  DateTime now = rtc.now();

  // Trigger dispensing automatically at scheduled time
  if (!dispensing && currentSlot < NUM_SLOTS) {
    if (now.hour() == hours[currentSlot] &&
        now.minute() == minutes_[currentSlot] &&
        now.second() == 0) {
      startDispenseCycle();
    }
  }

  // Handle incoming serial messages
  if (Serial.available() > 0) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    Serial.print("RX:");
    Serial.println(msg);

    if (msg.startsWith("JOB_ID:")) {
      jobId = msg.substring(7);
      Serial.print("JOB_STORED:");
      Serial.println(jobId);
    }
    else if (msg.startsWith("DISPENSE:OK:")) {
      dispenseMedicine();
      notifyDone();
      moveToNextSlot();
    } 
    else if (msg.startsWith("DISPENSE:SKIP:")) {
      notifyDone();
      moveToNextSlot();
    }
  }

  // Periodically poll backend for status updates
  static unsigned long lastPoll = 0;
  if (dispensing && millis() - lastPoll > 2000) {
    lastPoll = millis();
    if (jobId.length() > 0) {
      Serial.print("STATUS_REQ:");
      Serial.println(jobId);
    }
  }

  delay(50);
}

void startDispenseCycle() {
  dispensing = true;
  jobId = ""; // reset until backend sends a JOB_ID
  Serial.println("START_DISPENSE");
  buzz(100);
}

void dispenseMedicine() {
  buzz(200);
  servo.write(90);
  delay(1000);
  servo.write(0);
  delay(200);
  Serial.println("DISPENSE_ACTION_DONE");
}

void notifyDone() {
  if (jobId.length() > 0)
    Serial.print("DISPENSE_DONE:"), Serial.println(jobId);
  else
    Serial.println("DISPENSE_DONE:unknown");
  dispensing = false;
}

void moveToNextSlot() {
  currentSlot++;
  if (currentSlot >= NUM_SLOTS) currentSlot = 0;
  Serial.print("NEXT_SLOT:"), Serial.println(currentSlot);
}

void buzz(int duration) {
  digitalWrite(BUZZER_PIN, LOW);   // ON
  delay(duration);
  digitalWrite(BUZZER_PIN, HIGH);  // OFF
}
