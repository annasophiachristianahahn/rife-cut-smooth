#!/bin/bash
# RIFE Cut Smooth Launcher Script
# Makes it easier to run the tool from anywhere

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project directory
cd "$SCRIPT_DIR"

# Run the Python module
python3 -m rife_cut_smooth "$@"
