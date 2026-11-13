//! Interact with QMK raw HID.
use crate::QmkError;
use hidapi::HidDevice;

/// Payload size, excluding HIDAPI's report ID.
pub const RAW_HID_BUFFER_SIZE: usize = 32;
pub const RAW_USAGE_PAGE: u16 = 0xFF60;
pub const CONSOLE_USAGE_PAGE: u16 = 0xFF31;
pub const G_DESK_USAGE_PAGE: u16 = 0x01;
pub const CONSUMER_USAGE_PAGE: u16 = 0x0C;

fn encode_message(id: u8, msg: &[u8]) -> Result<[u8; 33], QmkError> {
    if msg.len() > RAW_HID_BUFFER_SIZE - 1 {
        return Err(QmkError);
    }
    let mut data = [0; RAW_HID_BUFFER_SIZE + 1];
    data[1] = id;
    data[2..2 + msg.len()].copy_from_slice(msg);
    Ok(data)
}

fn decode_response(id: u8, buf: &[u8], len: usize) -> Result<Vec<u8>, QmkError> {
    if len >= RAW_HID_BUFFER_SIZE || buf.len() <= len || buf[0] != id {
        return Err(QmkError);
    }
    Ok(buf[1..len + 1].to_vec())
}

pub fn send_message(
    dev: &HidDevice,
    message_id: u8,
    msg: Option<&[u8]>,
    out_len: usize,
) -> Result<Vec<u8>, QmkError> {
    if out_len >= RAW_HID_BUFFER_SIZE {
        return Err(QmkError);
    }
    let data = encode_message(message_id, msg.unwrap_or_default())?;
    let size = dev.write(&data).map_err(|err| {
        eprintln!("HID write failed: {err}");
        QmkError
    })?;
    if size != data.len() {
        return Err(QmkError);
    }
    if out_len == 0 {
        return Ok(vec![]);
    }
    let mut buf = [0; RAW_HID_BUFFER_SIZE];
    let size = dev.read_timeout(&mut buf, 1000).map_err(|err| {
        eprintln!("HID read failed: {err}");
        QmkError
    })?;
    decode_response(message_id, &buf[..size], out_len)
}

pub fn qmk_console(dev: &HidDevice) {
    loop {
        let mut buf = [0; RAW_HID_BUFFER_SIZE];
        match dev.read(&mut buf) {
            Ok(size) => print!("{}", String::from_utf8_lossy(&buf[..size])),
            Err(err) => {
                eprintln!("Read err: {err}");
                break;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn full_payload_has_separate_report_id() {
        let report = encode_message(7, &[42; 31]).unwrap();
        assert_eq!(&report[..2], &[0, 7]);
        assert_eq!(&report[2..], &[42; 31]);
        assert!(encode_message(7, &[0; 32]).is_err());
    }
    #[test]
    fn rejects_timeout_short_unhandled_and_stale_responses() {
        assert!(decode_response(8, &[], 3).is_err());
        assert!(decode_response(8, &[8, 3, 1], 3).is_err());
        assert!(decode_response(8, &[255, 3, 1, 0], 3).is_err());
        assert!(decode_response(8, &[7, 3, 1, 0], 3).is_err());
        assert!(decode_response(8, &[8; 32], 32).is_err());
        assert_eq!(decode_response(8, &[8, 3, 1, 42], 3).unwrap(), [3, 1, 42]);
    }
}
