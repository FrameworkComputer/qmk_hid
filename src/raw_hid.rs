//! Interact with the raw HID interface of QMK firmware

use hidapi::HidDevice;

// ChibiOS won't respond if we send 32.
// Currently I hardcoded it to ignore. But in upstream QMK/ChibiOS we have to send 33 bytes.
// See raw_hid_send in tmk_core/protocol/chibios/usb_main.c
pub const RAW_HID_BUFFER_SIZE: usize = 32;

pub const RAW_USAGE_PAGE: u16 = 0xFF60;
pub const CONSOLE_USAGE_PAGE: u16 = 0xFF31;
/// Generic Desktop
pub const G_DESK_USAGE_PAGE: u16 = 0x01;
pub const CONSUMER_USAGE_PAGE: u16 = 0x0C;

pub fn send_message(
    dev: &HidDevice,
    message_id: u8,
    msg: Option<&[u8]>,
    out_len: usize,
) -> Result<Vec<u8>, ()> {
    // TODO: Why fill the rest with 0xFE? hidapitester uses 0x00
    let mut data = vec![0x00; RAW_HID_BUFFER_SIZE];
    data[0] = 0x00; // NULL report ID
    data[1] = message_id;

    if let Some(msg) = msg {
        assert!(msg.len() <= RAW_HID_BUFFER_SIZE);
        let data_msg = &mut data[2..msg.len() + 2];
        data_msg.copy_from_slice(msg);
    }

    //println!("Writing data: {:?}", data);
    let res = dev.write(&data);
    match res {
        Ok(_size) => {
            //println!("Written: {}", size);
        }
        Err(err) => {
            println!("Write err: {err:?}");
            return Err(());
        }
    };

    // No response expected
    if out_len == 0 {
        return Ok(vec![]);
    }

    dev.set_blocking_mode(true).unwrap();

    let mut buf: Vec<u8> = vec![0xFE; RAW_HID_BUFFER_SIZE];
    let res = dev.read(buf.as_mut_slice());
    match res {
        Ok(_size) => {
            //println!("Read: {}", size);
            //println!("out_len: {}", out_len);
            //println!("buf: {:?}", buf);
            Ok(buf[1..out_len + 1].to_vec())
        }
        Err(err) => {
            println!("Read err: {err:?}");
            Err(())
        }
    }
}

// TODO: I actually don't think this is QMK specific
// Same protocol as https://www.pjrc.com/teensy/hid_listen.html
pub fn qmk_console(dev: &HidDevice) {
    loop {
        let mut buf: Vec<u8> = vec![0xFE; RAW_HID_BUFFER_SIZE];
        let res = dev.read(buf.as_mut_slice());
        match res {
            Ok(_size) => {
                let string = String::from_utf8_lossy(&buf);
                print!("{string}");
            }
            Err(err) => {
                println!("Read err: {err:?}");
            }
        }
    }
}
