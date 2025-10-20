# SPDX-FileCopyrightText: Copyright (C) 2025 ARDUINO SA <http://www.arduino.cc>
#
# SPDX-License-Identifier: MPL-2.0

"""
LED Matrix Painter
- Hosts a web UI with 13x8 pixels to activate
- Create an icon, save it, and render it on the matrix
- Receives the frame in the Python app
- Frame is sent to microcontroller/LED matrix via Bridge
"""

from arduino.app_utils import Bridge, App           
from arduino.app_bricks.web_ui import WebUI        

# Imports custom "matrix_app" module
from matrix_app import MatrixCore, IconStore, wire_webui 

import time

# configuration
W, H = 13, 8
core  = MatrixCore(W, H)     # 13×8 framebuffer
icons = IconStore(W, H)      # for storing icons from the web ui
ui    = WebUI()              # serves ./assets by default and handles sockets

# fetch latest pixel frame
def get_pixels_gs3():
    csv = core.csv_gs3()     # gets the pixel frame
    time.sleep(0.001)        # small delay to not overload router
    return csv

# make the function available to the microcontroller via Bridge
Bridge.provide("get_pixels_gs3", get_pixels_gs3) # send data to sketch

# Handles the web application and communication (see matrix_app.py)
wire_webui(ui, core, icons)

# Run the app
App.run()