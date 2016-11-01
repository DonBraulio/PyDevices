import sys

__author__ = "Braulio Ríos"

# Converts a 2 bytes integer to 4 characters string, in little endian (as used in RDP words)
def to_word_little_endian(number):
    return '{0:02X}{1:02X}'.format(number & 0xFF, (number >> 8) & 0xFF)


# Converts any integer to hexa string of 2*length_bytes characters, in little endian
def to_string_little_endian(number, length_bytes):
    hex_str = ""
    for i in range(0, length_bytes):
        hex_str += '{:02X}'.format((number >> 8*i) & 0xFF)
    return hex_str


# Extract a byte value from an hex string at given position (starts in 0)
def get_byte_from_hex(position, hex_string):
    return int(hex_string[2*position:2*(position + 1)], 16)


def hex_string_to_char_string(hex_string):
    string = ""
    for byte_n in range(0, int(len(hex_string)/2)):
        string += chr(get_byte_from_hex(byte_n, hex_string))
    return string


# Extract selected bits (LSB ->bit 0) from hex string and convert to integer (cannot be used if string is little-endian)
def extract_value_from_hex(hex_string, start_bit, length_bits):
    result = int(hex_string, 16)
    result >>= start_bit
    result &= 2**length_bits - 1  # Mask
    return result


# Swap byte orders in an hex string, to switch from little-endian to big-endian or vice-versa
def convert_endianess(hex_string):
    result = ""
    length = len(hex_string)
    for i in range(0, length, 2):
        result += hex_string[(length-i-2):(length-i)]
    return result


# Avoid using input() and raw_input() for compatibility between python 2 and 3
def wait_input(message):
    if sys.version_info >= (3, 0):
        return input(message)
    else:
        return raw_input(message)