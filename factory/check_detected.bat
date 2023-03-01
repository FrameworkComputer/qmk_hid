REM Batch script to list attached devices. Shows 2 for each Lotus input module!
REM
REM Then blinks backlight (RGB or white) 3 times
REM
REM Afterwards backlight should be enabled and to full brightness.
REM On the RGB module it enables a mode where a button press shows a cross focused on the button.
REM
REM Use `qmk_hid.exe via --rgb-effect 38` to enable reactive mode to show keypresses
pushd %~dp0

REM Check if connected
qmk_hid.exe --list
qmk_hid.exe via --info

REM Flash backlight
qmk_hid.exe via --device-indication

REM Set backlight to full brigthness
qmk_hid.exe via --rgb-brightness 100
qmk_hid.exe via --backlight 100
qmk_hid.exe via --backlight-breathing false

popd
