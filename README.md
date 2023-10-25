# QMK HID

Commandline tool to interact with QMK devices via their raw HID interface.

Currently focusing on the VIA API.
It will soon be superceded by QMK XAP, but that isn't ready yet.

Tested to work on Windows and Linux, without any drivers or admin privileges.

###### GUI

There is also an easy to use GUI tool that does not require commandline interaction.
On Linux install Python requirements via `python3 -m install -r requirements.txt` and run `qmk_gui.py`.
On Windows download the `qmk_gui.exe` and run it.

## Running

Download the latest binary from the [releases page](https://github.com/FrameworkComputer/qmk_hid/releases).

The examples call the binary with the name `qmk_hid`, as used on Linux.
If you're on Windows, use `qmk_hid.exe`, and when building from source,
use `cargo run --`.

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
      --info
          Get VIA protocol and config information (most likely NOT what you're looking for)
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
      --save
          Save RGB/backlight value, otherwise it won't persist through keyboard reboot. Can be used by itself or together with other argument
      --eeprom-reset
          Reset the EEPROM contents (Not supported by all firmware)
      --bootloader
          Jump to the bootloader (Not supported by all firmware)
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
  Product:      "Framework 16 Numpad"
  FW Version:   0.1.3
  Serial No:    "FRALDLENA100000000"
```

###### Control that device

```sh
# If there is only one device, no filter needed
> qmk_hid via --backlight
Brightness: 0%

# If there are multiple devices, need to filter by either VID, PID or both
> qmk_hid via --backlight
More than 1 device found. Select a specific device with --vid and --pid
> qmk_hid --vid 3434 via --backlight
Brightness: 0%

# Get current RGB brightness
> qmk_hid via --rgb-brightness 50
Brightness: 50%

# Set new RGB brightness
> qmk_hid via --rgb-brightness 100
Brightness: 100%
```

**NOTE:** By default the settings are not saved. To make them persistent add
the `--save` argument. Or run `qmk_hid via --save` by itself. Examples:

```
# Save directly
> qmk_hid via --rgb-brightness 100 --save

# Make a couple changes and save everything
> qmk_hid via --rgb-effect 1
> qmk_hid via --rgb-color red
> qmk_hid via --rgb-brightness 100
> qmk_hid via --save
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

###### Testing the RGB LEDs

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
# On Framework 16 we currently enable all, then 38 is `SOLID_REACTIVE_MULTICROSS`
qmk_hid via --rgb-effect 38
```

## Building from source

Pre-requisites:

- [Rust](https://rustup.rs/)
- libudev (`libudev-dev` on Ubuntu, `systemd-devel` on Fedora)

```sh
# Directly run
cargo run

# Build and run executable (on Linux)
cargo build
./target/debug/qmk_hid
```

## Running on Linux

To avoid needing root privileges to access the keyboard please follow the
official [QMK guide](https://docs.qmk.fm/#/faq_build?id=linux-udev-rules) for
how to install udev rules. After doing that, you'll be able to interact with
the keyboards as a regular user.
