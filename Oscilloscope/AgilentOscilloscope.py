# -*- coding: utf-8 -*-
"""
This package requires the Visa folder and NIVISA DLL libraries installed.
See "_doc\Visa\" for information and installers of Visa.

Use example:
TODO

See "_doc\Oscilloscope" to find the Agilent Oscilloscope 1000 series User Guide, where the commands
implemented here are based, and more available commands are described.

The software tool 'VISA Interactive Control' (installed with NIVISA), allows searching for connected devices,
and the resource string can be used during initialization, for example:

rf_generator = AgilentRFGenerator("USB0::0x0957::0x2018::0115000733::INSTR")

"""

from __future__ import print_function
from ctypes import *
from Visa import VisaLibrary
import time

__author__ = "Braulio Ríos"


# Agilent Oscilloscope DSO1002A
class AgilentOscilloscopeDSO1002A:

    # Public members
    debug = True  # Print all write / read operations

    # Private members
    _device = None
    _BUFFER_SIZE = 2048
    _buffer = create_string_buffer(_BUFFER_SIZE)
    _ret_count = c_uint32()

    def __init__(self, resource_string="*"):
        # Find a device connected containing the "INSTR" string
        if resource_string == "*":
            connected_devices = VisaLibrary.list_devices()
            for device in connected_devices:
                if device.find("INSTR") >= 0 and device.find("USB0") >= 0:
                    if resource_string != "*":
                        raise RuntimeError("More than one connected device found. Resource string must be provided.")
                    resource_string = device
        # If still no device found, fail
        if resource_string == "*":
            raise RuntimeError("No Oscilloscope found. Check that device is connected using VISA Interactive Control")
        self._device = VisaLibrary.open_device(resource_string)

    # Send a generic command (see N9310A User's Guide)
    def write(self, command):
        # Append final line break if not present
        if command[-1] != "\n":
            command += "\n"
        # Print command
        if self.debug:
            print("Sending command: \"%s\"..." % command[0:-1], end=' ')  # Remove line break to print
        # Write
        if VisaLibrary.visa.viWrite(self._device, command, len(command), byref(self._ret_count)) < 0:
            raise RuntimeError("Could not write data to device")
        # Check length
        if self._ret_count.value != len(command):
            raise RuntimeError("Length written is different from expected. Command length: %d bytes / %d bytes written",
                               len(command), self._ret_count)
        print("OK.")

    # Read response as a string
    def read(self):
        # Read
        ret_code = VisaLibrary.visa.viRead(self._device, self._buffer, self._BUFFER_SIZE, byref(self._ret_count))
        if ret_code < 0:
            raise RuntimeError("Could not read data from device. Return code: %d" % ret_code)
        # Trim buffer into a string
        response = self._buffer.value[0:self._ret_count.value]
        # Print response
        if self.debug:
            print("Response: %s " % response)
        return response

    # Reset oscilloscope to default values
    def reset(self):
        self.write("*RST")

    # Allow manual operation in the oscilloscope (it's disabled when any remote command is executed)
    def unlock_screen(self):
        self.write(":KEY:LOCK DISABLE")

    # Set channels to display
    def set_display_channels(self, channel_1=True, channel_2=False):
        self.write(":CHAN1:DISP %s" % ("ON" if channel_1 else "OFF"))
        self.write(":CHAN2:DISP %s" % ("ON" if channel_2 else "OFF"))

    # Same as "Run" button (or "Single" if single=True)
    def run(self, single=False):
        self.write(":SINGLE" if single else ":RUN")

    # Same as "Stop" button
    def stop(self):
        self.write(":STOP")

    # Force capture instead of waiting for trigger (similar to "Auto" trigger)
    def force_trigger(self):
        self.write(":FORCETRIG")

    # Set triggering options, channels, scales, and wait for the captured data.
    # Params:
    #     trigger_channel: 1, 2 or 0 (force immediate trigger, the other triggering options will be ignored)
    #     trigger_level: Numeric value in Volts
    #     trigger_slope_down: If True, wait for a negative slope to trigger. Otherwise wait for positive slope
    #     time_scale: Time scale Numeric value in Seconds
    #     channel_1_y_scale: Vertical scale for channel 1. If 0, the channel will be disabled.
    #     channel_2_y_scale: Vertical scale for channel 2. If 0, the channel will be disabled.
    def get_single_shoot(self, trigger_channel=0, trigger_level=0, trigger_slope_down=False, time_scale=1e-3,
                         channel_1_y_scale=1, channel_2_y_scale=0):
        self.stop()
        # Channels to display
        self.set_display_channels(channel_1=(not self.is_null(channel_1_y_scale)),
                              channel_2=(not self.is_null(channel_2_y_scale)))
        # Set scales
        self.set_vertical_scales(channel_1_y_scale, channel_2_y_scale)
        self.set_time_scale(time_scale)
        # Configure buffer format
        self.write(":WAV:FORMAT BYTE")  # 8 bits samples (WORD is not working currently)
        self.write(":WAV:POINTS:MODE NORMAL")  # Screen data (more predictable behavior)
        self.write(":WAV:POINTS 600")  # Max value for NORMAL mode
        # Configure and wait for trigger
        self.wait_one_trigger_event(trigger_channel, trigger_level, trigger_slope_down)
        # Retrieve data and calculate values
        time_s, ch1_v, ch2_v = None, None, None
        if not self.is_null(channel_1_y_scale):
            raw_buffer = self.get_raw_buffer(channel=1)
            time_s, ch1_v = self.samples_values_from_buffer(raw_buffer)
        if not self.is_null(channel_2_y_scale):
            raw_buffer = self.get_raw_buffer(channel=2)
            time_s, ch2_v = self.samples_values_from_buffer(raw_buffer)
        return time_s, ch1_v, ch2_v

    # Set triggering options, wait for one event and Stop
    # Params:
    #     trigger_channel: 1, 2 or 0 (force immediate trigger, the other triggering options will be ignored)
    #     trigger_level: Numeric value in Volts
    #     trigger_slope_down: If True, wait for a negative slope to trigger. Otherwise wait for positive slope
    def wait_one_trigger_event(self, trigger_channel=0, trigger_level=0, trigger_slope_down=False):
        # Configure trigger
        # Trigger mode AUTO
        if self.is_null(trigger_channel):
            self.run(single=True)
            self.force_trigger()
        # Trigger mode NORMAL (SINGLE)
        else:
            trigger_level_divisions = self.voltage_to_divisions(trigger_channel, trigger_level)
            self.set_trigger(trigger_channel, trigger_level_divisions, trigger_slope_down)
            self.run(single=True)
        # Wait for trigger
        n_try = 0
        while True:
            time.sleep(2**n_try)  # Wait 2^n_try seconds to check trigger status (limit is 2^6)
            n_try += 1
            self.write(":TRIGGER:STATUS?")
            if self.read().find("STOP") >= 0:  # read() may return "STOP\n"
                break
            elif n_try == 6:
                raise RuntimeError("Trigger timeout. Waited for 127 seconds without triggering.")

    # Retrieve raw samples buffer from oscilloscope (will block and throw exception if no data available)
    # NOTES: - Oscilloscope must have been triggered previously.
    #        - Will NOT set or change WAV configuration (format and number of points).
    def get_raw_buffer(self, channel=1):
        # Retrieve data (raw buffer)
        self.write(":WAV:SOURCE CHANNEL%d" % channel)
        self.write(":WAV:DATA?")
        time.sleep(1)
        raw_data = self.read()
        if len(raw_data) == 11:  # This is an error for sure (header size). Warning: other errors may not be this size.
            raise RuntimeError("Could not retrieve data from oscilloscope. Check that all values are in range.")
        return raw_data

    # Parse raw buffer and return samples values in seconds and volts
    # NOTE: Oscilloscope configuration must not have changed since get_raw_buffer()
    # STEPS: -> Detect sample format (single byte or word, ASCII not supported yet)
    #        -> Parse buffer values
    #        -> Retrieve Scales and References
    #        -> Calculate values in seconds and volts
    def samples_values_from_buffer(self, raw_buffer):
        # Detect format (single byte or two bytes per sample. See ":WAVeform:FORMat" in Programmer's Reference)
        self.write(":WAV:FORMAT?")
        samples_format = self.read()
        word_samples = samples_format.find("WORD") >= 0
        byte_samples = samples_format.find("BYTE") >= 0
        if (not word_samples) and (not byte_samples):  # ASCII format not supported yet
            raise RuntimeError("Format not supported for oscilloscope values: %s" % samples_format)

        # Parse buffer to an array of samples
        points = self._parse_samples_from_buffer(raw_buffer, word=word_samples)

        # Retrieve references from oscilloscope (must not have changed)
        xorigin, xincrement, yorigin, yincrement, yreference = self.get_current_axis_reference()

        # Calculate X and Y values (in Seconds and Volts)
        # See ":WAVeform:DATA" in Programmer's Reference
        t_seconds = []
        y_volts = []
        for index in range(0, len(points)):
            t_seconds.append(xorigin + (index * xincrement))
            y_volts.append((yreference - points[index]) * yincrement -yorigin)
        return t_seconds, y_volts

    # Retrieve current channel increments and references, to calculate values in Volts/Seconds
    # See ":WAVeform:DATA" in Programmer's Reference
    def get_current_axis_reference(self):
        self.write(":WAV:XORIGIN?")
        xorigin = float(self.read())
        self.write(":WAV:XINCREMENT?")
        xincrement = float(self.read())
        self.write(":WAV:YREFERENCE?")
        yreference = float(self.read())
        self.write(":WAV:YINCREMENT?")
        yincrement = float(self.read())
        self.write(":WAV:YORIGIN?")
        yorigin = float(self.read())
        return xorigin, xincrement, yorigin, yincrement, yreference

    # Convert a Voltage value to divisions, according to the current vertical scale for the given channel
    def voltage_to_divisions(self, channel, voltage):
        self.write(":CHAN%d:SCAL?" % channel)
        scale = float(self.read())
        return float(voltage) / scale

    # Set time units per division
    # Valid units are: ns, us, ms
    # Valid examples: "32.0ns", "32 ms"
    # Invalid examples: "32.0s"
    def set_time_scale(self, timescale):
        self.write(":TIMEBASE:SCALE %E" % self.time_string_to_value(timescale))

    # Set triggering options. Level value is given in divisions (remains with vertical scale changes)
    # Params:
    #     channel: 1 or 2.
    #     level_divisions: Numeric value in Divisions.
    #     slope_down: If True, wait for a negative slope to trigger. Otherwise wait for positive slope.
    def set_trigger(self, channel=1, level_divisions=0.0, slope_down=False):
        self.write(":TRIG:EDGE:SOURCE %d" % channel)
        self.write(":TRIG:EDGE:LEV %E" % level_divisions)
        self.write(":TRIG:EDGE:SLOPE %s" % ("NEG" if slope_down else "POS"))

    def set_vertical_scales(self, channel_1=1, channel_2=0):
        if not self.is_null(channel_1):
            self.write(":CHAN1:UNIT VOLT")
            self.write(":CHAN1:SCALE %E" % channel_1)
        if not self.is_null(channel_2):
            self.write(":CHAN2:UNIT VOLT")
            self.write(":CHAN2:SCALE %E" % channel_2)

    # Set the attenuation of the probes
    # Valid examples: 10, 1000.0, 0.001, "1000.0", "1000X", "0.001X"
    # Invalid examples: "10.0X", "10x" (wrong format), 0.0001, 10000 (out of range)
    def set_probes(self, channel_1=10, channel_2=None):
        if not self.is_null(channel_1):
            self.write(":CHAN1:PROB %s" % self.attenuation_value_to_string(channel_1))
        if not self.is_null(channel_2):
            self.write(":CHAN2:PROB %s" % self.attenuation_value_to_string(channel_2))

    @staticmethod
    # Check if the parameter shall be considered null
    def is_null(value):
        return (value is None) or (value == "") or (float(value) == 0.0)

    @staticmethod
    # Convert value (if numeric) to string value with unit
    def freq_value_to_string(frequency):
        if not isinstance(frequency, str):
            frequency = "%.4f kHz" % (frequency / 1e3)
        return frequency

    @staticmethod
    # Convert frequency string with unit to numeric value.
    # Valid units are kHz, MHz, GHz, or nothing (case insensitive, optional space, only "Hz" is not allowed).
    # Valid examples: 32.0khz , 44 MHz, 44MHZ, 44mhz, 8ghz
    def freq_string_to_value(frequency):
        if isinstance(frequency, str):
            frequency = frequency.strip().lower()  # remove spaces (beginning and ending) and convert to lower case
            unit = frequency[-3:len(frequency)]  # Extract unit in lower case
            if unit == "ghz":
                multiplier = 1e9
                frequency = frequency[0:-3]
            elif unit == "mhz":
                multiplier = 1e6
                frequency = frequency[0:-3]
            elif unit == "khz":
                multiplier = 1e3
                frequency = frequency[0:-3]
            else:
                multiplier = 1
            try:
                frequency = float(frequency)*multiplier
            except:
                raise RuntimeError("Invalid format for frequency. Valid examples: '3.002kHz', '3e3', '3MHZ', '2ghz'"
                                   "/ Invalid examples: '1.0 Hz', '1Hz', '8M' ")
        return frequency

    @staticmethod
    # Convert time string with unit to numeric value.
    # Valid units are: ns, us, ms
    # Valid examples: "32.0ns", "32 ms"
    # Invalid examples: "32.0s"
    def time_string_to_value(time):
        if isinstance(time, str):
            time = time.strip().lower()
            unit = time[-2:len(time)]
            if unit == "ns":
                multiplier = 1e-9
                time = time[0:-2]
            elif unit == "us":
                multiplier = 1e-6
                time = time[0:-2]
            elif unit == "ms":
                multiplier = 1e-3
                time = time[0:-2]
            else:
                multiplier = 1
            try:
                time = float(time)*multiplier
            except:
                raise RuntimeError("Invalid format for time. Valid examples: 32, '32.0ns', '32 ms'"
                                   "/ Invalid examples: '32.0s' ")
        return time

    @staticmethod
    # Convert parameter to a valid string for the oscilloscope
    # Valid examples: 10, 1000.0, 0.001, "1000.0", "1000X", "0.001X"
    # Invalid examples: "10.0X", "10x" (wrong format), 0.0001, 10000 (out of range)
    def attenuation_value_to_string(attenuation):
        _probes_attenuation = {0.001:"0.001X", 0.01:"0.01X", 0.1:"0.1X", 1:"1X", 10:"10X", 100:"100X", 1000:"1000X"}
        if isinstance(attenuation, str):
            if attenuation[-1] != 'X':
                attenuation = float(attenuation)
        if not isinstance(attenuation, str):
            attenuation = _probes_attenuation[attenuation]
        return attenuation

    # Extract an array with values from the buffer in the format defined in:
    #    Keysight 1000 Series Oscilloscope Programmer's Guide / Definite-Length Block Response Data
    # If word=True, each sample is two bytes in Big Endian
    def _parse_samples_from_buffer(self, buf, word=True):
        if buf[0] != '#':
            raise RuntimeError("Buffer is not in the format defined in Keysight 1000 Series Oscilloscope "
                               "Programmer's Guide / Definite-Length Block Response Data")
        length_chars = int(buf[1])
        length_buffer = int(buf[2:(2+length_chars)])
        total_length = 3 + length_chars + length_buffer
        if total_length > self._BUFFER_SIZE:
            raise RuntimeError("Not enough buffer size (%d bytes) to hold %d bytes" % self._BUFFER_SIZE, total_length)
        if total_length != len(buf):
            raise RuntimeError("Expected buffer length: %d, got: %d" % (2 + length_chars + length_buffer, len(buf)))
        first_byte_pos = 2 + length_chars  # Character "#" and one integer indicating length characters
        last_byte_pos = first_byte_pos + length_buffer - 1  # Remove \n at the end
        if word:
            # 2 bytes per sample Big Endian (see :WAVeform:FORMat in Programmer's Guide).
            return [((ord(buf[pos]) << 8) + ord(buf[pos+1])) for pos in range(first_byte_pos, last_byte_pos, 2)]
        else:
            return [ord(buf[pos]) for pos in range(first_byte_pos, last_byte_pos)]
