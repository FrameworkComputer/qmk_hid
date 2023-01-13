# QMK HID

Commandline (and soon library) to interact with QMK devices via their raw HID interface.

Currently focusing on the VIA API.
It will soon be superceded by QMK XAP, but that isn't ready yet.

I've only tested on Linux so far, but should also work on Windows, FreeBSD and macOS.

## Building

Pre-requisites: Rust, libudev

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

> qmk_hid via
Via

Usage: qmk_hid via [OPTIONS]

Options:
      --version
          Show protocol version
      --info
          Get device information
      --device-indication
          Get device indication
      --rgb-brightness [<RGB_BRIGHTNESS>]
          Set RGB brightness percentage or get, if no value provided
      --rgb-effect [<RGB_EFFECT>]
          Set RGB effect or get, if no value provided
      --rgb-effect-speed [<RGB_EFFECT_SPEED>]
          Set RGB effect speed or get, if no value provided (0-255)
      --rgb-hue [<RGB_HUE>]
          Set RGB hue or get, if no value provided. (0-255)
      --rgb-saturation [<RGB_SATURATION>]
          Set RGB saturation or get, if no value provided. (0-255)
      --backlight [<BACKLIGHT>]
          Set backlight brightness percentage or get, if no value provided
      --backlight-breathing [<BACKLIGHT_BREATHING>]
          Set backlight breathing or get, if no value provided [possible values: true, false]
      --bootloader
          Jump to the bootloader
  -h, --help
          Print help information

> qmk_hid qmk
QMK

Usage: qmk_hid qmk [OPTIONS]

Options:
  -c, --console  Listen to the console
  -h, --help     Print help information
```

###### List available devices
```sh
> qmk_hid -l
3434:0100 Interface: 1
  Manufacturer: Some("Keychron")
  path:         "/dev/hidraw2"
  Product:      Some("Q1")
  Release:      100
  Interface:    1
  Usage Page:   ff60 (RAW_USAGE_PAGE)

Make sure to select a device with --vid and --pid
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
> qmk_hid --bootloader
Trying to jump to bootloader
```

###### Factory testing the LEDs

```sh
# Turn RGB off
qmk_hid via --rgb-effect 0

# Turn all LEDs on
qmk_hid via --rgb-effect 1

# Change color
qmk_hid via --rgb-saturation 255
# Blue
qmk_hid via --rgb-hue 0
# Cyan
qmk_hid via --rgb-hue 50
# Green
qmk_hid via --rgb-hue 100
# Yellow
qmk_hid via --rgb-hue 150
# Red
qmk_hid via --rgb-hue 170
# Purple
qmk_hid via --rgb-hue 200


# Enable a mode that reacts to keypresses
qmk_hid via --rgb-effect 16
# And simulate keypresses ASDF (see QMK's keycodes.h)
qmk_hid factory --keycode 4
qmk_hid factory --keycode 22
qmk_hid factory --keycode 7
qmk_hid factory --keycode 9

# Or go through all keypresses (except FN)
# Only one LED is mapped to each key
qmk_hid factory --all-keycodes
```
