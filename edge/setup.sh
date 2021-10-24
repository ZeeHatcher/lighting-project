#!/bin/bash

sudo apt-get install portaudio19-dev python-all-dev llvm libsdl2-mixer-2.0-0

python3 -m pip install -r requirements.txt
LLVM_CONFIG=$(which llvm-config) python3 -m pip install llvmlite==0.32
python3 -m pip install librosa==0.8.1
