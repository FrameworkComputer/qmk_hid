use clap::Parser;

extern crate hidapi;

use hidapi::{HidApi, HidDevice, DeviceInfo};

/// RAW HID and VIA commandline for QMK devices
#[derive(Parser, Debug)]
#[command(arg_required_else_help = true)]
struct ClapCli {
    /// List connected HID devices
    #[arg(short, long)]
    list: bool,

    /// Verbose outputs to the console
    #[arg(short, long)]
    verbose: bool,

    /// VID (Vendor ID) in hex digits
    #[arg(long)]
    vid: Option<String>,

    /// PID (Product ID) in hex digits
    #[arg(long)]
    pid: Option<String>,

    /// Show protocol version
    #[arg(long)]
    version: bool,

    /// Get device information
    #[arg(long)]
    info: bool,

    /// Get device indication
    #[arg(long)]
    device_indication: bool,

    /// Set RGB brightness percentage or get, if no value provided
    #[arg(long)]
    rgb_brightness: Option<Option<u8>>,

    /// Set RGB effect or get, if no value provided
    #[arg(long)]
    rgb_effect: Option<Option<u8>>,

    /// Set RGB effect speed or get, if no value provided (0-255)
    #[arg(long)]
    rgb_effect_speed: Option<Option<u8>>,

    /// Set RGB color or get, if no value provided
    #[arg(long)]
    rgb_color: Option<Option<u8>>,

    /// Set backlight brightness percentage or get, if no value provided
    #[arg(long)]
    backlight: Option<Option<u8>>,

    /// Set backlight breathing or get, if no value provided
    #[arg(long)]
    backlight_breathing: Option<Option<bool>>,

    // TODO:
    // - RGB light
    // - LED matrix
    // - backlight
    // - eeprom reset
    // - audio

    /// Jump to the bootloader
    #[arg(long)]
    bootloader: bool,
}

const FWK_VID: u16 = 0x32AC;
const KEYCHRON_VID: u16 = 0x3434;
const QMK_INTERFACE: i32 = 0x01;

const RAW_HID_BUFFER_SIZE: usize = 32; // ChibiOS won't respond with 32

const RAW_USAGE_PAGE: u16 = 0xFF60;
const CONSOLE_USAGE_PAGE: u16 = 0xFF31;
/// Generic Desktop
const G_DESK_USAGE_PAGE: u16 = 0x01;
const CONSUMER_USAGE_PAGE: u16 = 0x0C;

//const PROTOCOL_VER_MSG_ID: u8;
#[repr(u8)]
enum ViaCommandId {
    GetProtocolVersion              = 0x01, // always 0x01
    GetKeyboardValue                = 0x02,
    SetKeyboardValue                = 0x03,
    //DynamicKeymapGetKeycode         = 0x04,
    //DynamicKeymapSetKeycode         = 0x05,
    //DynamicKeymapReset              = 0x06,
    CustomSetValue                  = 0x07,
    CustomGetValue                  = 0x08,
    //CustomSave                      = 0x09,
    //EepromReset                     = 0x0A,
    BootloaderJump                  = 0x0B,
    //DynamicKeymapMacroGetCount      = 0x0C,
    //DynamicKeymapMacroGetBufferSize = 0x0D,
    //DynamicKeymapMacroGetBuffer     = 0x0E,
    //DynamicKeymapMacroSetBuffer     = 0x0F,
    //DynamicKeymapMacroReset         = 0x10,
    //DynamicKeymapGetLayerCount      = 0x11,
    //DynamicKeymapGetBuffer          = 0x12,
    //DynamicKeymapSetBuffer          = 0x13,
    //DynamicKeymapGetEncoder         = 0x14,
    //DynamicKeymapSetEncoder         = 0x15,
    //Unhandled                       = 0xFF,
}

enum ViaKeyboardValueId {
    Uptime            = 0x01,
    LayoutOptions     = 0x02,
    SwitchMatrixState = 0x03,
    FirmwareVersion   = 0x04,
    DeviceIndication  = 0x05,
}

enum ViaChannelId {
    //CustomChannel    = 0,
    BacklightChannel = 1,
    //RgblightChannel  = 2,
    RgbMatrixChannel = 3,
    //AudioChannel     = 4,
}

enum ViaBacklightValue {
    Brightness = 1,
    Effect     = 2,
}

//enum via_qmk_rgblight_value {
//    id_qmk_rgblight_brightness   = 1,
//    id_qmk_rgblight_effect       = 2,
//    id_qmk_rgblight_effect_speed = 3,
//    id_qmk_rgblight_color        = 4,
//}

enum ViaRgbMatrixValue {
    Brightness  = 1,
    Effect      = 2,
    EffectSpeed = 3,
    Color       = 4,
}

fn send_message(dev: &HidDevice, message_id: u8, msg: Option<&[u8]>, out_len: usize) -> Result<Vec<u8>, ()> {
    let mut data = vec![0xFE; RAW_HID_BUFFER_SIZE];
    data[0] = 0x00; // NULL report ID
    data[1] = message_id;

    if let Some(msg) = msg {
        assert!(msg.len() <= RAW_HID_BUFFER_SIZE);
        let data_msg = &mut data[2..msg.len()+2];
        data_msg.copy_from_slice(msg);
    }

    //println!("Writing data: {:?}", data);
    let res = dev.write(&data);
    match res {
        Ok(_size) => {
            //println!("Written: {}", size);
        },
        Err(err) => {
            println!("Write err: {:?}", err);
            return Err(())
        },
    };

    // Not response expected
    if out_len == 0 {
        return Ok(vec![])
    }

    dev.set_blocking_mode(true).unwrap();

    let mut buf: Vec<u8> = vec![0xFE; RAW_HID_BUFFER_SIZE];
    let res = dev.read(buf.as_mut_slice());
    match res {
        Ok(_size) => {
            //println!("Read: {}", size);
            //println!("out_len: {}", out_len);
            //println!("buf: {:?}", buf);
            Ok(buf[1..out_len+1].to_vec())
        },
        Err(err) => {
            println!("Read err: {:?}", err);
            Err(())
        },
    }
}

fn get_protocol_ver(dev: &HidDevice) -> Result<u16, ()> {
    let output = send_message(dev, ViaCommandId::GetProtocolVersion as u8, None, 2)?;
    //println!("output: {:?}", output);
    assert_eq!(output.len(), 2);
    Ok(u16::from_be_bytes(output.try_into().unwrap()))
}

fn get_keyboard_value(dev: &HidDevice, value: ViaKeyboardValueId) -> Result<u32, ()> {
    // Must skip the first byte from the output, as we're sending a message of 1 and it's preserved in the output
    let msg = vec![value as u8];
    let output = send_message(dev, ViaCommandId::GetKeyboardValue as u8, Some(&msg), 5)?;
    assert_eq!(output.len(), 5);
    Ok(u32::from_be_bytes(output[1..5].try_into().unwrap()))
}

fn set_keyboard_value(dev: &HidDevice, value: ViaKeyboardValueId, number: u32) -> Result<(), ()> {
    assert!(number < (1<<8)); // TODO: Support u32
    let msg = vec![value as u8, number as u8];
    send_message(dev, ViaCommandId::SetKeyboardValue as u8, Some(&msg), 0)?;
    Ok(())
}

fn get_rgb_u8(dev: &HidDevice, value: u8) -> Result<u8, ()> {
    let msg = vec![ViaChannelId::RgbMatrixChannel as u8, value];
    let output = send_message(dev, ViaCommandId::CustomGetValue as u8, Some(&msg), 3)?;
    //println!("Current value: {:?}", output);
    Ok(output[2])
}

fn set_rgb_u8(dev: &HidDevice, value: u8, value_data: u8) -> Result<(), ()> {
    // data = [ command_id, channel_id, value_id, value_data ]
    let msg = vec![ViaChannelId::RgbMatrixChannel as u8, value, value_data];
    send_message(dev, ViaCommandId::CustomSetValue as u8, Some(&msg), 0)?;
    Ok(())
}

fn get_rgb_color(dev: &HidDevice) -> Result<(u8, u8), ()> {
    let msg = vec![ViaChannelId::RgbMatrixChannel as u8, ViaRgbMatrixValue::Color as u8];
    let output = send_message(dev, ViaCommandId::CustomGetValue as u8, Some(&msg), 4)?;
    //println!("Current value: {:?}", output);
    // hue, saturation
    Ok((output[2], output[3]))
}

fn get_backlight(dev: &HidDevice, value: u8) -> Result<u8, ()> {
    let msg = vec![ViaChannelId::BacklightChannel as u8, value];
    let output = send_message(dev, ViaCommandId::CustomGetValue as u8, Some(&msg), 3)?;
    //println!("Current value: {:?}", output);
    Ok(output[2])
}

fn set_backlight(dev: &HidDevice, value: u8, value_data: u8) -> Result<(), ()> {
    // data = [ command_id, channel_id, value_id, value_data ]
    let msg = vec![ViaChannelId::RgbMatrixChannel as u8, value, value_data];
    send_message(dev, ViaCommandId::CustomSetValue as u8, Some(&msg), 0)?;
    Ok(())
}

fn bootloader_jump(dev: &HidDevice) -> Result<(), ()> {
    let output = send_message(dev, ViaCommandId::BootloaderJump as u8, None, 0)?;
    //println!("output: {:?}", output);
    assert_eq!(output.len(), 0);
    Ok(())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let args = ClapCli::parse_from(&args);
    //println!("args: {:?}", args);

    //println!("Printing all available hid devices:");

    match HidApi::new() {
        Ok(api) => {
            let mut selected_dev: Option<&DeviceInfo> = None;

            for dev_info in api.device_list() {
                let vid = dev_info.vendor_id();
                let pid = dev_info.product_id();
                let interface = dev_info.interface_number();
                if ![FWK_VID, KEYCHRON_VID].contains(&vid) {
                    continue;
                }

                // Print device information
                if args.list || args.verbose {
                    let usage_page = dev_info.usage_page();
                    if usage_page != RAW_USAGE_PAGE && !args.verbose {
                        continue;
                    }
                    println!("{:04x}:{:04x} Interface: {}", vid, pid, interface);
                    println!("  Manufacturer: {:?}", dev_info.manufacturer_string());
                    println!("  path:         {:?}", dev_info.path());
                    println!("  Product:      {:?}", dev_info.product_string());
                    println!("  Release:      {:x}", dev_info.release_number());
                    println!("  Interface:    {}", dev_info.interface_number());
                    print!("  Usage Page:   {:x}", dev_info.usage_page());
                    match usage_page {
                        RAW_USAGE_PAGE => println!(" (RAW_USAGE_PAGE)"),
                        CONSOLE_USAGE_PAGE => println!(" (CONSOLE_USAGE_PAGE)"),
                        G_DESK_USAGE_PAGE => println!(" (Generic Desktop Usage Page)"),
                        CONSUMER_USAGE_PAGE => println!(" (CONSUMER_USAGE_PAGE)"),
                        _ => {},
                    }
                    println!();
                }

                if args.vid.is_none() || args.pid.is_none() {
                    continue;
                }
                // TODO: Use clap-num for this
                let args_vid = u16::from_str_radix(args.vid.as_ref().unwrap(), 16).unwrap();
                let args_pid = u16::from_str_radix(args.pid.as_ref().unwrap(), 16).unwrap();

                if interface == QMK_INTERFACE && vid == args_vid && pid == args_pid {
                    selected_dev = Some(dev_info);
                }
            }

            if let Some(dev_info) = selected_dev {
                use_device(&args, &api, dev_info);
            } else {
                println!("Make sure to select a device with --vid and --pid");
            }
        },
        Err(e) => {
            eprintln!("Error: {}", e);
        },
    };
}


fn use_device(args: &ClapCli,api: &HidApi, dev_info: &DeviceInfo) {
    let vid = dev_info.vendor_id();
    let pid = dev_info.product_id();
    let interface = dev_info.interface_number();

    if args.verbose {
        println!("Connecting to {:04X}:{:04X} Interface: {}", vid, pid, interface);
    }

    let device = dev_info.open_device(&api).unwrap();

    if args.version {
        let prot_ver = get_protocol_ver(&device).unwrap();
        println!("Protocol Version: {:04X}", prot_ver);
    } else if args.bootloader {
        println!("Trying to jump to bootloader");
        bootloader_jump(&device).unwrap();
    } else if args.info {
        let prot_ver = get_protocol_ver(&device).unwrap();
        let uptime = get_keyboard_value(&device, ViaKeyboardValueId::Uptime).unwrap();
        let layout_opts = get_keyboard_value(&device, ViaKeyboardValueId::LayoutOptions).unwrap();
        let matrix_state = get_keyboard_value(&device, ViaKeyboardValueId::SwitchMatrixState).unwrap();
        let fw_ver = get_keyboard_value(&device, ViaKeyboardValueId::FirmwareVersion).unwrap();

        println!("Protocol Version:     {:04X}", prot_ver);
        println!("Uptime:               {:?}s", uptime / 1000);
        println!("Layout Options:       {:?}", layout_opts);
        println!("Switch Matrix State:  {:?}", matrix_state); // TODO: Decode
        println!("VIA Firmware Version: {:?}", fw_ver);
    } else if args.device_indication {
        println!("Setting device indication");

        // TODO: Should repeat this 6 times, every 200ms
        set_keyboard_value(&device, ViaKeyboardValueId::DeviceIndication, 0).unwrap();
    } else if let Some(arg_brightness) = args.rgb_brightness {
        if let Some(percentage) = arg_brightness {
            let brightness = (255.0 * percentage as f32) / 100.0;
            set_rgb_u8(&device, ViaRgbMatrixValue::Brightness as u8, brightness.round() as u8).unwrap();
        }
        let brightness = get_rgb_u8(&device, ViaRgbMatrixValue::Brightness as u8).unwrap();
        let percentage = (100.0 * brightness as f32) / 255.0;
        println!("Brightness: {}%", percentage.round())
    } else if let Some(arg_effect) = args.rgb_effect {
        if let Some(effect) = arg_effect {
            set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, effect).unwrap();
        }
        let effect = get_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8).unwrap();
        println!("Effect: {}", effect)
    } else if let Some(arg_speed) = args.rgb_effect_speed {
        if let Some(speed) = arg_speed {
            set_rgb_u8(&device, ViaRgbMatrixValue::EffectSpeed as u8, speed).unwrap();
        }
        let speed = get_rgb_u8(&device, ViaRgbMatrixValue::EffectSpeed as u8).unwrap();
        println!("Effect Speed: {}", speed)
    } else if let Some(arg_color) = args.rgb_color {
        if let Some(_) = arg_color {
            //set_rgb_color(&device, ViaRgbMatrixValue::Color as u8, color).unwrap();
        }
        let (hue, saturation) = get_rgb_color(&device).unwrap();
        println!("Color Hue:        {}", hue);
        println!("Color Saturation: {}", saturation);
    } else if let Some(arg_backlight) = args.backlight {
        if let Some(percentage) = arg_backlight {
            let brightness = (255.0 * percentage as f32) / 100.0;
            set_backlight(&device, ViaBacklightValue::Brightness as u8, brightness.round() as u8).unwrap();
        }
        let brightness = get_backlight(&device, ViaBacklightValue::Brightness as u8).unwrap();
        let percentage = (100.0 * brightness as f32) / 255.0;
        println!("Brightness: {}%", percentage.round())
    } else if let Some(arg_breathing) = args.backlight_breathing {
        if let Some(breathing) = arg_breathing {
            set_backlight(&device, ViaBacklightValue::Effect as u8, breathing as u8).unwrap();
        }
        let breathing = get_backlight(&device, ViaBacklightValue::Effect as u8).unwrap();
        println!("Breathing: : {:?}", breathing == 1)
    //} else if args.rgb_matrix_save {
        // TODO
        //set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, effect).unwrap();
    } else {
        println!("No command specified.");
    }
}
