#!/bin/bash

# Set up environment for Qt
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=none  # Disable OpenGL if causing issues
export DISPLAY=${DISPLAY:-:0}

# Activate virtual environment and run the GUI
cd "$(dirname "$0")"
source venv/bin/activate
python test_app.py --gui