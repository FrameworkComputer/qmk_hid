# QMK HID

Commandline (and soon library) to interact with QMK devices via their raw HID interface.

Currently focusing on the VIA API.
It will soon be superceded by QMK XAP, but that isn't ready yet.

Tested to work on Windows and Linux, without any drivers or admin privileges.

## Building

Pre-requisites: Rust, libudev

```sh
cargo build
ls -l target/debug/qmk_hid
```

## Running

The examples call the binary with the name `qmk_hid`. On Windows use
`qmk_hid.exe` and when running from source, use `cargo run --`.

###### Show the help

```sh
> qmk_hid
RAW HID and VIA commandline for QMK devices

Usage: qmk_hid [OPTIONS] [COMMAND]

Commands:
  via      Via
  qmk      QMK
  help     Print this message or the help of the given subcommand(s)

Options:
  -l, --list       List connected HID devices
  -v, --verbose    Verbose outputs to the console
      --vid <VID>  VID (Vendor ID) in hex digits
      --pid <PID>  PID (Product ID) in hex digits
  -h, --help       Print help information
  -V, --version    Print version information

> qmk_hid via
Via

Usage: qmk_hid via [OPTIONS]

Options:
      --version
          Show protocol version
      --info
          Get device information
      --device-indication
          Flash device indication (backlight) 3x
      --rgb-brightness [<RGB_BRIGHTNESS>]
          Set RGB brightness percentage or get, if no value provided
      --rgb-effect [<RGB_EFFECT>]
          Set RGB effect or get, if no value provided
      --rgb-effect-speed [<RGB_EFFECT_SPEED>]
          Set RGB effect speed or get, if no value provided (0-255)
      --rgb-hue [<RGB_HUE>]
          Set RGB hue or get, if no value provided. (0-255)
      --rgb-color <RGB_COLOR>
          Set RGB color [possible values: red, yellow, green, cyan, blue, purple, white]
      --rgb-saturation [<RGB_SATURATION>]
          Set RGB saturation or get, if no value provided. (0-255)
      --backlight [<BACKLIGHT>]
          Set backlight brightness percentage or get, if no value provided
      --backlight-breathing [<BACKLIGHT_BREATHING>]
          Set backlight breathing or get, if no value provided [possible values: true, false]
      --eeprom-reset
          Reset the EEPROM contents (Not supported by all firmware)
      --bootloader
          Jump to the bootloader
  -h, --help
          Print help information

> qmk_hid qmk
QMK

Usage: qmk_hid qmk [OPTIONS]

Options:
  -c, --console  Listen to the console. Better to use `qmk console` (https://github.com/qmk/qmk_cli)
  -h, --help     Print help information
```

###### List available devices
```sh
> qmk_hid -l
32ac:0014
  Manufacturer: "Framework Computer Inc"
  Product:      "Lotus Numpad"
  FW Version:   0.1.3
  Serial No:    "FRALDLENA100000000"
```

###### Control that device

```sh
# If there is only one device, no filter needed
> qmk_hid via --version
Protocol Version: 000B

# If there are multiple devices, need to filter by either VID, PID or both
> qmk_hid via --version
More than 1 device found. Select a specific device with --vid and --pid
> qmk_hid --vid 3434 via --version
Protocol Version: 000B

# Get current RGB brightness
> qmk_hid via --rgb-brightness 50
Brightness: 50%

# Set new RGB brightness
> qmk_hid via --rgb-brightness 100
Brightness: 100%
```

###### Jumping to the bootloader, to reflash.

Note: This will only work when the QMK firmware has this command enabled. This
is not the default upstream behavior.

```sh
> qmk_hid via --bootloader
```

###### Reset EEPROM contents / Clear VIA config

VIA stores its config in EEPROM (sometimes emulated in flash).
When using a different keyboard with the same controller board you'll want to
clear it, otherwise the previously stored VIA config overrides the hardcoded
one.

This becomes obvious when trying to change the hardcoded keymap but the
behavior does not change.

The command only does something when the firmware has `VIA_EEPROM_ALLOW_RESET` defined.

```sh
> qmk_hid via --eeprom-config
```

###### Factory testing the LEDs

```sh
# Use "device indication" to flash backlight 3 times
qmk_hid via --device-indication

# Turn RGB off
qmk_hid via --rgb-effect 0

# Turn all LEDs on
qmk_hid via --rgb-effect 1

# Change color
qmk_hid via --rgb-color red
qmk_hid via --rgb-color yellow
qmk_hid via --rgb-color green
qmk_hid via --rgb-color cyan
qmk_hid via --rgb-color blue
qmk_hid via --rgb-color purple
qmk_hid via --rgb-color white

# Enable a mode that reacts to keypresses
# Note that the effect numbers can be different per keyboard
# On Lotus we currently enable all, then 38 is `SOLID_REACTIVE_MULTICROSS`
qmk_hid via --rgb-effect 38

# Factory commands are not guaranteed to work
# And simulate keypresses ASDF (see QMK's keycodes.h)
qmk_hid factory --keycode 4
qmk_hid factory --keycode 22
qmk_hid factory --keycode 7
qmk_hid factory --keycode 9

# Or go through all keypresses (except FN)
# Only one LED is mapped to each key
qmk_hid factory --all-keycodes
```
