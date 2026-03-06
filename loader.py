import argparse
from s_record_to_hex_converter import get_hex_from_srecord
from serial import Serial, SerialException
import sys

def get_serial_connection(port: str) -> Serial:
    try:
        ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity='O',
            stopbits=2.0,
            timeout=1
        )

        return ser
    except SerialException as e:
        raise e

def get_chunked_data(series_of_data, chunk_size: int) -> list:
    return [series_of_data[i:i+chunk_size] for i in range(0, len(series_of_data), chunk_size)]

def load_data_to_programmer(contiguous_data: str, ser: Serial) -> None:
    if not ser.dsr:
        raise RuntimeError('Error: Programmer not set to RS 232 Interface')

    # Reset programmer to make it anticipate a control word next
    ser.dtr = False
    ser.dtr = True

    # The JEE 664 accepts data 256 bytes at a time
    chunked_data: list[list[str]] = get_chunked_data(get_chunked_data(contiguous_data, 2), 256)

    # This clears the address to start writing at the begininning of the lower 32K of the JEE 664 EPROM Programmer
    # For more information, check the control word table in the JEE 665 manual: 
    # https://www.manuallib.com/download/2023-10-19/Jameco%20JE665%20RS-232C%20Interface%20User%27s%20Manual.pdf
    ser.write(bytes.fromhex('A0'))

    for i, chunk in enumerate(chunked_data):
        ser.write(bytes.fromhex('AE')) # $AE is the control word for writing to the lower 32K address of the JEE 664 without clearing the current address
        print(f'Loading chunk {i+1}/{len(chunked_data)}')
        for byte in chunk:
            ser.write(bytes.fromhex(byte))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '-f', 
        '--input-file', 
        help='Path to the input S-record file to be loaded',
        required=True
    )

    parser.add_argument(
        '-p', 
        '--port', 
        help='Serial port where the RS-232 interface is connected to this computer. Examples: /dev/ttyUSB0 (Linux), COM1 (Windows), etc. Defaults to COM1.',
        default='COM1',
    )

    args = parser.parse_args()

    try:
        serial_connection = get_serial_connection(args.port)
    except SerialException as e:
        print(e)
        sys.exit(1)

    try:
        with open(args.input_file, 'r') as f:
            load_data_to_programmer(get_hex_from_srecord(f.read()), serial_connection)

        print('\nDownload successful!')
    except FileNotFoundError as e:
        print(e)
    except RuntimeError as e:
        print(e)
    finally:
        serial_connection.close()
