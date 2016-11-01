from collections import OrderedDict
from .Tools import extract_value_from_hex, convert_endianess, hex_string_to_char_string

__author__ = "Braulio Ríos"

TYPE_8_BITS = 8
TYPE_16_BITS = 16
TYPE_32_BITS = 32
TYPE_ARRAY = "ARRAY"
TYPE_STRING = "STRING"
TYPE_STRUCT = "STRUCT"


# Recover C-like structure fields data from an hex string, little endian encoded
# Supports bit-length fields contained in byte-length fields (e.g: two fields of 3 and 5 bits into an UINT8)
# e.g:
# fields = OrderedDict()
#         fields["field1"] = TYPE_8_BITS                   # simple field
#         fields["field2"] = (3, TYPE_8_BITS)              # packed field (3 bits, into an UINT8)
#         fields["field3"] = (5, TYPE_8_BITS)              # packed field (5 bits)
#         fields["field4"] = (5*TYPE_8_BITS, TYPE_ARRAY)   # 5 bytes array (length must be given in bits)
#         fields["field5"] = (7*TYPE_8_BITS, TYPE_STRING)  # 7 chars string (length must be given in bits)
#         fields["field6"] = (sub_struct, TYPE_STRUCT)     # sub_struct must be another OrderedDict (parsed recursively)
#
# Array types (TYPE_ARRAY) will be preserved as hex strings, size must be given in bits for the total array size
# String types (TYPE_STRING), are similar to TYPE_ARRAY, but the byte values are converted to char.
# Struct types (TYPE_STRUCT), structs that are parsed recursively
def parse_struct_from_hex(fields, hex_string):
    fields_parsed = OrderedDict()  # Result will be stored here
    container_fields_offset = 0
    packed_field_offset = 0
    first_packed_field = True
    prev_field_length = 0
    total_length_string = len(hex_string)

    # Check hex string is even
    assert total_length_string % 2 == 0, "Invalid hex string (length is not even): %s" % hex_string

    # Check that struct length and hex string match (check_struct validate internal structure lengths)
    struct_length = check_struct(fields)  # length in bits
    assert struct_length == total_length_string*4,\
        "hex string provided (%d bytes) does not match structure length (%d bytes)"\
        % (total_length_string / 2, struct_length/8)

    # Go over the hex string, converting from low-endian and extracting field values
    # Some fields are byte-sized, and others are bit-sized packed into byte-sized containers
    container_value = None
    for field in fields:
        # --------------------- IDENTIFY FIELD TYPE ------------------------------
        # Packed fields are variable bit-length, in container fields of fixed bit-length (8, 16 or 32 bits)
        # The packed fields must be defined as tuples with the packed size and container size
        is_simple_field = isinstance(fields[field], int)
        # Array types are preserved as hex strings
        is_array = not is_simple_field and fields[field][1] == TYPE_ARRAY
        # Similar to Array types but each byte is converted to char
        is_string = not is_simple_field and fields[field][1] == TYPE_STRING
        # Allows including structs inside structs, will be parsed recursively
        is_struct = not is_simple_field and fields[field][1] == TYPE_STRUCT

        # --------------------- CALCULATE LENGTH ------------------------------
        # Simple fields are treated as packed fields, with the same length than the container
        if is_simple_field:
            container_field_length = fields[field]
            packed_field_length = container_field_length
        elif is_array or is_string:
            container_field_length = fields[field][0]
            packed_field_length = container_field_length
        elif is_struct:
            container_field_length = check_struct(fields[field][0])  # check_struct returns struct length in bits
            packed_field_length = container_field_length
        else:  # packed fields
            container_field_length = fields[field][1]
            packed_field_length = fields[field][0]

        # --------------------- EXTRACT CONTAINER (only first packed field) ------------------------------
        if first_packed_field:
            packed_field_offset = 0
            # Container field limits in hex string
            container_start_char = int(container_fields_offset/4)  # each hex character is 4 bits
            container_end_char = int(container_start_char + container_field_length/4)
            # Extract from string
            container_value = hex_string[container_start_char:container_end_char]
            container_fields_offset += container_field_length

        # ---------------------------- EXTRACT AND PARSE FIELD ----------------------------------
        if is_array:     # Preserve as hex string
            fields_parsed[field] = container_value
        elif is_string:  # Convert to char
            fields_parsed[field] = hex_string_to_char_string(container_value)
        elif is_struct:  # Parse recursively
            fields_parsed[field] = parse_struct_from_hex(fields[field][0], container_value)
        else:            # Numeric values: convert container to big-endian and to integer (or long)
            if first_packed_field:
                container_value = convert_endianess(container_value)
            fields_parsed[field] = extract_value_from_hex(container_value, packed_field_offset, packed_field_length)

        # Execute Handler for field if present (3rd tuple element)
        if not is_simple_field and len(fields[field]) > 2 and hasattr(fields[field][2], '__call__'):
            fields_parsed[field] = fields[field][2](fields_parsed[field])

        packed_field_offset += packed_field_length

        # Detect if the next is the first packed field
        first_packed_field = (packed_field_offset == container_field_length)

    return fields_parsed


# Return structure length in bits.
# Check that fields var is in a format supported by parse_struct_from_hex
# Check that fields is OrderedDict, that each field is integer or 2-element list, containers multiple of 8 bits
# and that bit-length fields match containers length
# Struct fields are also checked recursively
def check_struct(fields):
    total_length_sum_bits = 0
    packed_field_offset = 0
    prev_container_length = 0
    assert isinstance(fields, OrderedDict), "Struct fields must be instance of OrderedDict"
    for field_name in fields:
        is_first_field = (packed_field_offset == 0)
        # Simple fields: byte-sized, not packed
        if isinstance(fields[field_name], int):
            field_length = fields[field_name]
            current_container_length = field_length
            assert packed_field_offset == 0,\
                "Malformed structure: bit-sized fields previous to %s do not match container length" % field_name
        else:
            assert (len(fields[field_name]) >= 2), "Field is not integer nor 2-element list: " + field_name
            container_info = fields[field_name][1]  # Second list parameter is Type of field
            # Array-type fields
            if container_info == TYPE_ARRAY or container_info == TYPE_STRING:
                field_length = fields[field_name][0]
                current_container_length = field_length
            # Struct-type fields (calculate length recursively)
            elif container_info == TYPE_STRUCT:
                field_length = check_struct(fields[field_name][0])
                current_container_length = field_length
            # Packed fields: bit-sized, inside a byte-sized container
            else:
                field_length = fields[field_name][0]
                current_container_length = container_info

        assert current_container_length % 8 == 0,\
            "Container field length (%d) is not multiple of 8 bits: %s" % (current_container_length, field_name)

        packed_field_offset += field_length
        if packed_field_offset > current_container_length:
            raise AssertionError("The sum of the lengths is greater than the container, overflow in field: "
                                 + field_name)
        elif packed_field_offset < current_container_length:
            if not is_first_field and prev_container_length != current_container_length:
                print(packed_field_offset, current_container_length)
                raise AssertionError("Malformed structure: field %s changed container size before allowed length"
                                     % field_name)
        else:  # Equals, end of container
            total_length_sum_bits += packed_field_offset
            packed_field_offset = 0

        prev_container_length = current_container_length

    return total_length_sum_bits


class BinaryParserTester:
    def __init__(self):
        pass

    @staticmethod
    def test_all():
        BinaryParserTester.test_endian_converter()
        BinaryParserTester.test_hex_extractor()
        BinaryParserTester.test_hex_parser()

    @staticmethod
    def test_endian_converter():
        print("Testing convert_little_endian_to_big_endian()...")
        val = convert_endianess("0f512332")
        assert val == "3223510f", "Wrong endian converted value, expected 3223510f, got %s" % val

        val = convert_endianess("12345abcdeff")
        assert val == "ffdebc5a3412", "Wrong endian converted value, expected ffdebc5a3412, got %s" % val

        val = convert_endianess("f135")
        assert val == "35f1", "Wrong endian converted value, expected 35f1, got %s" % val
        print("OK")

    @staticmethod
    def test_hex_extractor():
        print("Testing extract_value_from_hex()...")
        val = extract_value_from_hex("0552", 7, 3)  # start bit 7, length 3: 010
        assert val == 0x2, "Wrong extracted value, expected 0x2, got 0x%x" % val

        val = extract_value_from_hex("9ff2", 8, 8)
        assert val == 0x9f, "Wrong extracted value, expected 0x9f, got 0x%x" % val

        val = extract_value_from_hex("0f521236", 12, 16)
        assert val == 0xf521, "Wrong extracted value, expected 0xf521, got 0x%x" % val
        print("OK")

    @staticmethod
    def test_hex_parser():
        print("Testing parse_fields_from_hex()...")

        hex_string = "8fe37156"
        hex_string += "f87ae5" + "31206162632031"  # sub struct 1 (second part is "1 abc 1" converted to hex)
        hex_string += "a87ae3" + "32206162632032"  # sub struct 2 (second part is "2 abc 2" converted to hex)
        hex_string += "f87ae5" + "33206162632033"  # sub struct 3 (second part is "3 abc 3" converted to hex)
        hex_string += "11ff"
        hex_string += "55727567756179"  # "Uruguay" converted to hex

        # Warning: must be constructed this way because OrderedDict(arg1 =..., arg2=...) doesn't preserve ORDER
        sub_struct_format = OrderedDict()
        sub_struct_format["sub_field_1"] = TYPE_8_BITS
        sub_struct_format["sub_field_2"] = (7, TYPE_16_BITS)
        sub_struct_format["sub_field_3"] = (9, TYPE_16_BITS)
        sub_struct_format["sub_field_4"] = (7*TYPE_8_BITS, TYPE_STRING)

        fields = OrderedDict()

        fields["field1"] = TYPE_8_BITS
        fields["field2"] = (5, TYPE_8_BITS, lambda x: "ONE" if x == 1 else "NOT ONE")
        fields["field3"] = (3, TYPE_8_BITS)
        fields["field4"] = (12, TYPE_16_BITS, lambda x: x+1)
        fields["field5"] = (4, TYPE_16_BITS)
        fields["sub_struct_0"] = (sub_struct_format, TYPE_STRUCT)
        fields["sub_struct_1"] = (sub_struct_format, TYPE_STRUCT)
        fields["sub_struct_2"] = (sub_struct_format, TYPE_STRUCT)
        fields["field6"] = TYPE_16_BITS
        fields["field7"] = (7*TYPE_8_BITS, TYPE_STRING)

        structure = parse_struct_from_hex(fields, hex_string)

        assert structure["field1"] == 0x8f, "field1 wrong, expected 0x8f, got: 0x%x" % structure["field1"]
        assert structure["field2"] == "NOT ONE", "field2 wrong, expected string \"NOT ONE\", got: 0b%o" % structure["field2"]
        assert structure["field3"] == 0b111, "field3 wrong, expected 0b111, got: %d" % structure["field3"]
        assert structure["field4"] == 0x671 + 1, "field4 wrong, expected 0x672, got: 0x%x" % structure["field4"]
        assert structure["field5"] == 0x5, "field5 wrong, expected 0x5, got: 0x%x" % structure["field5"]

        # sub_struct_0
        assert structure["sub_struct_0"]["sub_field_1"] == 0xf8,\
            "sub_struct_0/sub_field_1 wrong, expected 0xf8, got 0x%x" % structure["sub_struct_0"]["sub_field_1"]
        assert structure["sub_struct_0"]["sub_field_2"] == 0x7a,\
            "sub_struct_0/sub_field_2 wrong, expected 0x7a, got 0x%x" % structure["sub_struct_0"]["sub_field_2"]
        assert structure["sub_struct_0"]["sub_field_3"] == (2*0xe5),\
            "sub_struct_0/sub_field_3 wrong, expected 2*0xe5, got 0x%x" % structure["sub_struct_0"]["sub_field_3"]
        assert structure["sub_struct_0"]["sub_field_4"] == "1 abc 1",\
            "sub_struct_0/sub_field_4 wrong, expected \'1 abc 1\', got \'%s\'"\
            % structure["sub_struct_0"]["sub_field_4"]

        # sub_struct_1
        assert structure["sub_struct_1"]["sub_field_1"] == 0xa8,\
            "sub_struct_1/sub_field_1 wrong, expected 0xa8, got 0x%x" % structure["sub_struct_1"]["sub_field_1"]
        assert structure["sub_struct_1"]["sub_field_2"] == 0x7a,\
            "sub_struct_1/sub_field_2 wrong, expected 0x7a, got 0x%x" % structure["sub_struct_1"]["sub_field_2"]
        assert structure["sub_struct_1"]["sub_field_3"] == (2*0xe3),\
            "sub_struct_1/sub_field_3 wrong, expected 2*0xe3, got 0x%x" % structure["sub_struct_1"]["sub_field_3"]
        assert structure["sub_struct_1"]["sub_field_4"] == "2 abc 2",\
            "sub_struct_1/sub_field_4 wrong, expected \'2 abc 2\', got \'%s\'"\
            % structure["sub_struct_1"]["sub_field_4"]

        # sub_struct_2
        assert structure["sub_struct_2"]["sub_field_1"] == 0xf8,\
            "sub_struct_1/sub_struct_2 wrong, expected 0xf8, got 0x%x" % structure["sub_struct_2"]["sub_field_1"]
        assert structure["sub_struct_2"]["sub_field_2"] == 0x7a,\
            "sub_struct_2/sub_field_2 wrong, expected 0x7a, got 0x%x" % structure["sub_struct_2"]["sub_field_2"]
        assert structure["sub_struct_2"]["sub_field_3"] == (2*0xe5),\
            "sub_struct_2/sub_field_3 wrong, expected 2*0xe5, got 0x%x" % structure["sub_struct_2"]["sub_field_3"]
        assert structure["sub_struct_2"]["sub_field_4"] == "3 abc 3",\
            "sub_struct_2/sub_field_4 wrong, expected \'3 abc 3\', got \'%s\'"\
            % structure["sub_struct_2"]["sub_field_4"]

        # Last 2 fields
        assert structure["field6"] == 0xff11, "field6 wrong, expected 0xff11, got: 0x%x" % structure["field6"]
        assert structure["field7"] == "Uruguay",\
            "field7 wrong, expected \'Uruguay\', got: \'%s\'"\
            % structure["field7"]

        print(structure)



        print("OK")


# class BitArray:
#     def __init__(self, hex_string):
#         self.byte_array = [] # pre-allocation barely matters in python
#         # go over the list in steps of 2 and take 2-characters as each byte
#         for byte_number in range(0, len(hex_string), 2):
#             byte_hex = hex_string[byte_number:(byte_number+2)]
#             byte_value = int(byte_hex, 16)
#             self.byte_array.append(byte_value)
#
#     def is_one(self, bit_position):
#         (byte_pos, bit_pos) = divmod(bit_position, 8)
#         return ((self.byte_array[byte_pos] & (0b10000000 >> bit_pos)) & 0xFF) != 0

# def hex_to_binary_string(hex_string):
#     binary_string = ""
#     is_msb = True
#     byte_value = 0
#     for nibble in hex_string:
#         nibble_value = int(nibble, 16)
#         if is_msb:
#             byte_value = 0x10*nibble_value
#         else:
#             byte_value += nibble_value
#             binary_string += '{:0>8}'.format(bin(byte_value).replace('0b', ''))
#         is_msb = not is_msb
#     return binary_string

