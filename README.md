# QMK HID

Commandline (and soon library) to interact with QMK devices via their raw HID interface.

Currently focusing on the VIA API.
It will soon be superceded by QMK XAP, but that isn't ready yet.

I've only tested on Linux so far, but should also work on Windows, FreeBSD and macOS.

## Building

Pre-requisites: Rust

## Running

The examples call the binary with the name `qmk_hid`. On Windows use
`qmk_hid.exe` and when running from source, use `cargo run --`.

###### Show the help

```
> qmk_hid -h
RAW HID and VIA commandline for QMK devices

Usage: qmk_hid [OPTIONS]

Options:
  -l, --list
          List connected HID devices
  -v, --verbose
          Verbose outputs to the console
      --vid <VID>
          VID (Vendor ID) in hex digits
      --pid <PID>
          PID (Product ID) in hex digits
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
      --rgb-color [<RGB_COLOR>]
          Set RGB color or get, if no value provided
      --backlight [<BACKLIGHT>]
          Set backlight brightness percentage or get, if no value provided
      --backlight-breathing [<BACKLIGHT_BREATHING>]
          Set backlight breathing or get, if no value provided [possible values: true, false]
      --bootloader
          Jump to the bootloader
  -h, --help
          Print help information
```

###### List available devices

```
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
# Get current RGB brightness
> qmk_hid --vid 3434 --pid 100 --rgb-brightness 50
Brightness: 50%

# Set new brightness
> qmk_hid --vid 3434 --pid 100 --rgb-brightness 100
Brightness: 100%
```

###### Jumping to the bootloader, to reflash.

Note: This will only work when the QMK firmware has this command enabled. This
is not the default upstream behavior.
```sh
> cargo run -q -- --vid 3434 --pid 100 --bootloader
Trying to jump to bootloader
```
