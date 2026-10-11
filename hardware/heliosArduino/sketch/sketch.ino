#include <Arduino_RouterBridge.h>

const int PINS[] = {5, 6, 7, 8};
const int NUM_PINS = sizeof(PINS) / sizeof(PINS[0]);

int lastPinStates[NUM_PINS] = {LOW, LOW, LOW, LOW};

void setup() {
  Bridge.begin();
  Monitor.begin(115200);

  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(PINS[i], INPUT);
  }

  for (int i = 0; i < NUM_PINS; i++) {
    lastPinStates[i] = digitalRead(PINS[i]);
  }

}

void loop() {
  for (int i = 0; i < NUM_PINS; i++) {
    int currentState = digitalRead(PINS[i]);

    if (lastPinStates[i] == LOW && currentState == HIGH) {
      Monitor.print("Rising edge detected on pin ");
      Monitor.println(PINS[i]);

      Bridge.notify("send_post_request", PINS[i]);
    }

    lastPinStates[i] = currentState;
  }

  delay(10);
}