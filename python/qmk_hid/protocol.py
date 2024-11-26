import os
import sys

import hid

FWK_VID = 0x32AC

QMK_INTERFACE = 0x01
RAW_HID_BUFFER_SIZE = 32

RAW_USAGE_PAGE = 0xFF60
CONSOLE_USAGE_PAGE = 0xFF31
# Generic Desktop
G_DESK_USAGE_PAGE = 0x01
CONSUMER_USAGE_PAGE = 0x0C

GET_PROTOCOL_VERSION = 0x01  # always 0x01
GET_KEYBOARD_VALUE = 0x02
SET_KEYBOARD_VALUE = 0x03
# DynamicKeymapGetKeycode         = 0x04
# DynamicKeymapSetKeycode         = 0x05
# DynamicKeymapReset              = 0x06
CUSTOM_SET_VALUE = 0x07
CUSTOM_GET_VALUE = 0x08
CUSTOM_SAVE = 0x09
EEPROM_RESET = 0x0A
BOOTLOADER_JUMP = 0x0B

CHANNEL_CUSTOM = 0
CHANNEL_BACKLIGHT = 1
CHANNEL_RGB_LIGHT = 2
CHANNEL_RGB_MATRIX = 3
CHANNEL_AUDIO = 4

BACKLIGHT_VALUE_BRIGHTNESS = 1
BACKLIGHT_VALUE_EFFECT = 2

RGB_MATRIX_VALUE_BRIGHTNESS = 1
RGB_MATRIX_VALUE_EFFECT = 2
RGB_MATRIX_VALUE_EFFECT_SPEED = 3
RGB_MATRIX_VALUE_COLOR = 4

RED_HUE = 0
YELLOW_HUE = 43
GREEN_HUE = 85
CYAN_HUE = 125
BLUE_HUE = 170
PURPLE_HUE = 213

RGB_EFFECTS = [
    "Off",
    "SOLID_COLOR",
    "ALPHAS_MODS",
    "GRADIENT_UP_DOWN",
    "GRADIENT_LEFT_RIGHT",
    "BREATHING",
    "BAND_SAT",
    "BAND_VAL",
    "BAND_PINWHEEL_SAT",
    "BAND_PINWHEEL_VAL",
    "BAND_SPIRAL_SAT",
    "BAND_SPIRAL_VAL",
    "CYCLE_ALL",
    "CYCLE_LEFT_RIGHT",
    "CYCLE_UP_DOWN",
    "CYCLE_OUT_IN",
    "CYCLE_OUT_IN_DUAL",
    "RAINBOW_MOVING_CHEVRON",
    "CYCLE_PINWHEEL",
    "CYCLE_SPIRAL",
    "DUAL_BEACON",
    "RAINBOW_BEACON",
    "RAINBOW_PINWHEELS",
    "RAINDROPS",
    "JELLYBEAN_RAINDROPS",
    "HUE_BREATHING",
    "HUE_PENDULUM",
    "HUE_WAVE",
    "PIXEL_FRACTAL",
    "PIXEL_FLOW",
    "PIXEL_RAIN",
    "TYPING_HEATMAP",
    "DIGITAL_RAIN",
    "SOLID_REACTIVE_SIMPLE",
    "SOLID_REACTIVE",
    "SOLID_REACTIVE_WIDE",
    "SOLID_REACTIVE_MULTIWIDE",
    "SOLID_REACTIVE_CROSS",
    "SOLID_REACTIVE_MULTICROSS",
    "SOLID_REACTIVE_NEXUS",
    "SOLID_REACTIVE_MULTINEXUS",
    "SPLASH",
    "MULTISPLASH",
    "SOLID_SPLASH",
    "SOLID_MULTISPLASH",
]

def find_devs(show, verbose):
    if verbose:
        show = True

    devices = []
    for device_dict in hid.enumerate():
        vid = device_dict["vendor_id"]
        pid = device_dict["product_id"]
        product = device_dict["product_string"]
        manufacturer = device_dict["manufacturer_string"]
        sn = device_dict['serial_number']
        interface = device_dict['interface_number']
        path = device_dict['path']

        if vid != FWK_VID:
            if verbose:
                print("Vendor ID not matching")
            continue

        if interface != QMK_INTERFACE:
            if verbose:
                print("Interface not matching")
            continue
        # For some reason on Linux it'll always show usage_page==0
        if os.name == 'nt' and device_dict['usage_page'] not in [RAW_USAGE_PAGE, CONSOLE_USAGE_PAGE]:
            if verbose:
                print("Usage Page not matching")
            continue
        # Lots of false positives, so at least skip Framework false positives
        if vid == FWK_VID and pid not in [0x12, 0x13, 0x14, 0x18, 0x19]:
            if verbose:
                print("False positive, device is not allowed")
            continue

        fw_ver = device_dict["release_number"]

        if (os.name == 'nt' and device_dict['usage_page'] == RAW_USAGE_PAGE) or verbose:
            if show:
                print(f"Manufacturer: {manufacturer}")
                print(f"Product:      {product}")
                print("FW Version:   {}".format(format_fw_ver(fw_ver)))
                print(f"Serial No:    {sn}")

            if verbose:
                print(f"Path:         {path}")
                print(f"VID/PID:      {vid:02X}:{pid:02X}")
                print(f"Interface:    {interface}")
                # TODO: print Usage Page
                print("")

        devices.append(device_dict)

    return devices


def send_message(dev, message_id, msg, out_len):
    data = [0xFE] * RAW_HID_BUFFER_SIZE
    data[0] = 0x00 # NULL report ID
    data[1] = message_id

    if msg:
        if len(msg) > RAW_HID_BUFFER_SIZE-2:
            print("Message too big. BUG. Please report")
            sys.exit(1)
        for i, x in enumerate(msg):
            data[2+i] = x

    try:
        # TODO: Do this somewhere outside
        h = hid.device()
        h.open_path(dev['path'])
        #h.set_nonblocking(0)
        h.write(data)

        if out_len == 0:
            return None

        out_data = h.read(out_len+3)
        return out_data
    except (IOError, OSError) as ex:
        disable_devices([dev])
        debug_print("Error ({}): ".format(dev['path']), ex)

def set_keyboard_value(dev, value, number):
    msg = [value, number]
    send_message(dev, SET_KEYBOARD_VALUE, msg, 0)

def set_rgb_u8(dev, value, value_data):
    msg = [CHANNEL_RGB_MATRIX, value, value_data]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)

# Returns brightness level: x/255
def get_rgb_u8(dev, value):
    msg = [CHANNEL_RGB_MATRIX, value]
    output = send_message(dev, CUSTOM_GET_VALUE, msg, 1)
    if output[0] == 255: # Not RGB
        return None
    return output[3]

# Returns (hue, saturation)
def get_rgb_color(dev):
    msg = [CHANNEL_RGB_MATRIX, RGB_MATRIX_VALUE_COLOR]
    output = send_message(dev, CUSTOM_GET_VALUE, msg, 2)
    return (output[3], output[4])

# Returns brightness level: x/255
def get_backlight(dev, value):
    msg = [CHANNEL_BACKLIGHT, value]
    output = send_message(dev, CUSTOM_GET_VALUE, msg, 1)
    return output[3]

def set_backlight(dev, value, value_data):
    msg = [CHANNEL_BACKLIGHT, value, value_data]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)

def save(dev):
    save_rgb(dev)
    save_backlight(dev)

def save_rgb(dev):
    msg = [CHANNEL_RGB_MATRIX]
    send_message(dev, CUSTOM_SAVE, msg, 0)

def save_backlight(dev):
    msg = [CHANNEL_BACKLIGHT]
    send_message(dev, CUSTOM_SAVE, msg, 0)

def eeprom_reset(dev):
    send_message(dev, EEPROM_RESET, None, 0)


def bootloader_jump(dev):
    send_message(dev, BOOTLOADER_JUMP, None, 0)


def bios_mode(dev, enable):
    param = 0x01 if enable else 0x00
    send_message(dev, BOOTLOADER_JUMP, [0x05, param], 0)


def factory_mode(dev, enable):
    param = 0x01 if enable else 0x00
    send_message(dev, BOOTLOADER_JUMP, [0x06, param], 0)


def set_rgb_brightness(dev, brightness):
    set_rgb_u8(dev, RGB_MATRIX_VALUE_BRIGHTNESS, brightness)


def set_brightness(dev, brightness):
    set_backlight(dev, BACKLIGHT_VALUE_BRIGHTNESS, brightness)

def set_white_effect(dev, breathing_on):
    set_backlight(dev, BACKLIGHT_VALUE_EFFECT, breathing_on)

# Set both
def set_white_rgb_brightness(dev, brightness):
    set_brightness(dev, brightness)
    set_rgb_brightness(dev, brightness)


def set_rgb_color(dev, hue, saturation):
    (cur_hue, cur_sat) = get_rgb_color(dev)
    if hue is None:
        hue = cur_hue
    msg = [CHANNEL_RGB_MATRIX, RGB_MATRIX_VALUE_COLOR, hue, saturation]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)

