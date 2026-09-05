#!/bin/zsh
cd "/Users/anandjaiswal/Documents/MFT " || exit 1
export PYTHONPATH="/Users/anandjaiswal/Documents/MFT /src"
open "http://127.0.0.1:8787"
python3 -m mft.server
