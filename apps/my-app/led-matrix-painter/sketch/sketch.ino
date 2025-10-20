// SPDX-FileCopyrightText: Copyright (C) 2025 ARDUINO SA <http://www.arduino.cc>
//
// SPDX-License-Identifier: MPL-2.0

#include <ArduinoGraphics.h>
#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

Arduino_LED_Matrix matrix;

static void parseCsv13x8_GS3(const String& csv, uint8_t out[104]) {
  // Parse up to 104 comma-separated ints (0..7). Missing entries => 0.
  int idx = 0;
  int start = 0;
  while (start < csv.length() && idx < 104) {
    int comma = csv.indexOf(',', start);
    if (comma < 0) comma = csv.length();
    String tok = csv.substring(start, comma);
    tok.trim();
    int v = tok.toInt();             // non-numeric => 0
    if (v < 0) v = 0; if (v > 7) v = 7;
    out[idx++] = (uint8_t)v;
    start = comma + 1;
  }
  while (idx < 104) out[idx++] = 0;
}

void setup() {
  Serial.begin(9600);

  delay(200);

  matrix.begin();
  matrix.clear();
  matrix.setGrayscaleBits(3);

  Bridge.begin();
}

void loop() {
  static uint8_t frame[104];
  static uint32_t lastDrawMs = 0;
  const uint32_t now = millis();

  // checks if 100ms has passed since last draw
  if (now - lastDrawMs < 100) return;
  lastDrawMs = now;

  String payload;

  // fetch latest pixel frame from Python side
  bool ok = Bridge.call("get_pixels_gs3", payload);

  // if there's a new frame and payload is not empty, parse the CSV and draw the frame
  if (ok && payload.length() > 0) {
    parseCsv13x8_GS3(payload, frame);
    matrix.draw(frame);
  }
}