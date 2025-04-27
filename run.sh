#!/bin/bash

if [ -z "$1" ]; then
    echo "error: cant find Objects folder"
    echo "how to use: $0 /path/to/folder"
    exit 1
fi

FOLDER_PATH="$1"

# folder check
if [ ! -d "$FOLDER_PATH" ]; then
    echo "orror: Cant find objects folder: $FOLDER_PATH"
    exit 1
fi

# path to Blender
BLENDER_PATH="./blender-4.4.0-linux-x64/blender"

# runing script Blender
echo "Runing script Blender..."
$BLENDER_PATH -b -P render_script.py -- "$FOLDER_PATH"
if [ $? -ne 0 ]; then
    echo "Error: Script Blender failed"
    exit 1
fi

# Runing script captioning
echo "Runing script captioning..."
python3 Run_captioning.py "$FOLDER_PATH"
if [ $? -ne 0 ]; then
    echo "Error: Script captioning failed"
    exit 1
fi

echo "Data preprocessing success"