pub mod factory;
pub mod lamparray;
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

const QMK_INTERFACE: i32 = 0x01;

pub struct Found {
    pub raw_usages: Vec<DeviceInfo>,
    pub console_usages: Vec<DeviceInfo>,
}

/// Format BCD version
///
/// # Examples
///
/// ```
/// let ver = format_bcd(0x0213);
/// assert_eq!(ver, "2.1.3");
/// ```
fn format_bcd(bcd: u16) -> String {
    let bytes = bcd.to_be_bytes();
    let major = bytes[0];
    let minor = (bytes[1] & 0xF0) >> 4;
    let patch = bytes[1] & 0x0F;
    format!("{major}.{minor}.{patch}")
}

const NOT_SET: &str = "NOT SET";

pub fn find_devices(
    api: &HidApi,
    list: bool,
    verbose: bool,
    args_vid: Option<&str>,
    args_pid: Option<&str>,
) -> Found {
    let mut found: Found = Found {
        raw_usages: vec![],
        console_usages: vec![],
    };
    for dev_info in api.device_list() {
        let vid = dev_info.vendor_id();
        let pid = dev_info.product_id();
        let interface = dev_info.interface_number();

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

        // TODO: Use clap-num for this
        let args_vid = args_vid
            .as_ref()
            .map(|s| u16::from_str_radix(s, 16).unwrap());
        let args_pid = args_pid
            .as_ref()
            .map(|s| u16::from_str_radix(s, 16).unwrap());

        // If filtering for specific VID or PID, skip all that don't match
        if let Some(args_vid) = args_vid {
            if vid != args_vid {
                continue;
            }
        }
        if let Some(args_pid) = args_pid {
            if pid != args_pid {
                continue;
            }
        }

        match usage_page {
            RAW_USAGE_PAGE => {
                if interface != QMK_INTERFACE {
                    println!(
                        "Something is wrong with {vid}:{pid}. The interface isn't {QMK_INTERFACE}"
                    );
                } else {
                    found.raw_usages.push(dev_info.clone());
                }
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

pub fn save(save: bool, dev: &HidDevice) {
    if !save {
        return;
    }

    save_rgb(dev).unwrap();
    save_backlight(dev).unwrap();
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
