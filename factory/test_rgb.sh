#!/bin/sh
# Turn on RGB and cycle through the three RGB colors with five seconds pause in-between.

echo "Turn RGB off"
./qmk_hid.exe via --rgb-effect 0
sleep 2

echo "Turn all LEDs on"
./qmk_hid.exe via --rgb-effect 1

echo "RGB White"
./qmk_hid.exe via --rgb-saturation 0
sleep 2

echo "RGB Red"
./qmk_hid.exe via --rgb-color red
sleep 2

echo "RGB Green"
./qmk_hid.exe via --rgb-color green
sleep 2

echo "RGB Blue"
./qmk_hid.exe via --rgb-color blue
