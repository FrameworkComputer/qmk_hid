pub mod factory;
pub mod raw_hid;
pub mod via;

extern crate hidapi;

use std::fmt;

use crate::raw_hid::*;
use crate::via::*;

use hidapi::{DeviceInfo, HidApi, HidDevice, HidError};

#[derive(Debug)]
pub struct QmkError;

impl fmt::Display for QmkError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "QMK Error")
    }
}

impl std::error::Error for QmkError {}

#[derive(Clone, Copy, Debug, PartialEq, clap::ValueEnum)]
pub enum Color {
    /// 0° and 255° => 0
    Red,
    /// Yellow (120°) => 43
    Yellow,
    /// Green (120°) => 85
    Green,
    /// Cyan (180°) => 125
    Cyan,
    /// Blue (240°) => 170
    Blue,
    /// Purple (300°) => 213
    Purple,
    /// Saturation 0
    White,
}

pub struct Found {
    pub raw_usages: Vec<DeviceInfo>,
    pub console_usages: Vec<DeviceInfo>,
}

/// Format BCD version
fn format_bcd(bcd: u16) -> String {
    let bytes = bcd.to_be_bytes();
    let major = bytes[0];
    let minor = (bytes[1] & 0xF0) >> 4;
    let patch = bytes[1] & 0x0F;
    format!("{major}.{minor}.{patch}")
}

#[test]
fn formats_bcd_version() {
    assert_eq!(format_bcd(0x0213), "2.1.3");
}

const NOT_SET: &str = "NOT SET";

pub fn find_devices(
    api: &HidApi,
    list: bool,
    verbose: bool,
    args_vid: Option<&str>,
    args_pid: Option<&str>,
) -> Found {
    // Invalid library filters must not panic or accidentally select every device.
    let parse = |value: Option<&str>| value.map(|v| u16::from_str_radix(v, 16)).transpose();
    let (Ok(args_vid), Ok(args_pid)) = (parse(args_vid), parse(args_pid)) else {
        return Found {
            raw_usages: vec![],
            console_usages: vec![],
        };
    };
    let mut found: Found = Found {
        raw_usages: vec![],
        console_usages: vec![],
    };
    for dev_info in api.device_list() {
        let vid = dev_info.vendor_id();
        let pid = dev_info.product_id();

        // Print device information
        let usage_page = dev_info.usage_page();
        if ![RAW_USAGE_PAGE, CONSOLE_USAGE_PAGE].contains(&usage_page) {
            continue;
        }

        if (list && usage_page == RAW_USAGE_PAGE) || verbose {
            println!("{vid:04x}:{pid:04x}");
            let fw_ver = dev_info.release_number();
            println!(
                "  Manufacturer: {:?}",
                dev_info.manufacturer_string().unwrap_or(NOT_SET)
            );
            println!(
                "  Product:      {:?}",
                dev_info.product_string().unwrap_or(NOT_SET)
            );
            println!("  FW Version:   {}", format_bcd(fw_ver));
            println!(
                "  Serial No:    {:?}",
                dev_info.serial_number().unwrap_or(NOT_SET)
            );

            if verbose {
                println!("  VID/PID:      {vid:04x}:{pid:04x}");
                println!("  Interface:    {}", dev_info.interface_number());
                println!("  Path:         {:?}", dev_info.path());
                print!("  Usage Page:   0x{:04X}", dev_info.usage_page());
                match usage_page {
                    RAW_USAGE_PAGE => println!(" (RAW_USAGE_PAGE)"),
                    CONSOLE_USAGE_PAGE => println!(" (CONSOLE_USAGE_PAGE)"),
                    G_DESK_USAGE_PAGE => println!(" (Generic Desktop Usage Page)"),
                    CONSUMER_USAGE_PAGE => println!(" (CONSUMER_USAGE_PAGE)"),
                    _ => println!(),
                }
            }
        }

        // If filtering for specific VID or PID, skip all that don't match
        if let Some(args_vid) = args_vid
            && vid != args_vid
        {
            continue;
        }
        if let Some(args_pid) = args_pid
            && pid != args_pid
        {
            continue;
        }

        match usage_page {
            RAW_USAGE_PAGE => {
                found.raw_usages.push(dev_info.clone());
            }
            CONSOLE_USAGE_PAGE => {
                found.console_usages.push(dev_info.clone());
            }
            _ => {}
        }
    }

    found
}

pub fn new_hidapi() -> Result<HidApi, HidError> {
    HidApi::new()
}

pub fn save(save: bool, dev: &HidDevice) -> Result<(), QmkError> {
    if !save {
        return Ok(());
    }
    // Most modules implement only one lighting channel. Try both for standalone save.
    let rgb = save_rgb(dev);
    let backlight = save_backlight(dev);
    rgb.or(backlight)
}

pub fn color_as_hue(color: Color) -> u8 {
    match color {
        Color::Red => 0,
        Color::Yellow => 43,
        Color::Green => 85,
        Color::Cyan => 125,
        Color::Blue => 170,
        Color::Purple => 213,
        Color::White => 0, // Doesn't matter, only hue needs to be 0
    }
}
