# Batch script to list attached devices. Shows 2 for each Lotus input module!
#
# Then blinks backlight (RGB or white) 3 times
#
# Afterwards backlight should be enabled and to full brightness.
# On the RGB module it enables a mode where a button press shows a cross focused on the button.
#
# Use `qmk_hid.exe via --rgb-effect 38` to enable reactive mode to show keypresses

# Check if connected
./qmk_hid --list
./qmk_hid via --info

# Flash backlight
./qmk_hid via --device-indication

# Set backlight to full brigthness
./qmk_hid via --rgb-brightness 100
./qmk_hid via --backlight 100
./qmk_hid via --backlight-breathing false
