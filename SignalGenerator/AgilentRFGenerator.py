# -*- coding: utf-8 -*-
"""
This package requires the Visa folder and NIVISA DLL libraries installed.

Use example:
from AgilentRFGenerator import AgilentRFGenerator
rf_generator = AgilentRFGenerator()  # Finds the first connected device
rf_generator.set_frequency(32000)
rf_generator.set_frequency("32.0 kHz")
rf_generator.set_amplitude(-100)
rf_generator.set_amplitude("-100 dBm")
rf_generator.write("FREQ:CW 32.0 kHz")  # Any generic command (see User Guide)


The software tool 'VISA Interactive Control' (installed with NIVISA), allows searching for connected devices,
and the resource string can be used during initialization, for example:

rf_generator = AgilentRFGenerator("USB0::0x0957::0x2018::0115000733::INSTR")

"""

from __future__ import print_function
from ctypes import *
from Visa import VisaLibrary


# Agilent N9310A RF Signal Generator
class AgilentRFGenerator:

    # Public members
    debug = True  # Print all write / read operations

    # Private members
    _device = None
    _BUFFER_SIZE = 200
    _buffer = create_string_buffer(_BUFFER_SIZE)
    _ret_count = c_uint32()

    def __init__(self, resource_string="*"):
        # Find a device connected containing the "INSTR" string
        if resource_string == "*":
            connected_devices = VisaLibrary.list_devices()
            for device in connected_devices:
                if device.find(b'INSTR'):
                    if resource_string != "*":
                        raise RuntimeError("More than one connected device found. Resource string must be provided.")
                    resource_string = device
                    break
        # If still no device found, fail
        if resource_string == "*":
            raise RuntimeError("No Oscilloscope found. Check that device is connected using VISA Interactive Control")
        self._device = VisaLibrary.open_device(resource_string)

    # Send a generic command (see N9310A User's Guide)
    def write(self, command):
        # Convert command from str to bytes array (only necessary in Python 3)
        if not isinstance(command, bytes):
            command = command.encode()
        # Append final line break if not present
        if command[-1] != b"\n":
            command += b"\n"
        # Print command
        if self.debug:
            print("Sending command: \"%s\"..." % command[0:-1], end=' ')  # Remove line break to print
        # Write
        if 0 != VisaLibrary.visa.viWrite(self._device, command, len(command), byref(self._ret_count)):
            raise RuntimeError("Could not write data to device")
        # Check length
        if self._ret_count.value != len(command):
            raise RuntimeError("Length written is different from expected. Command length: %d bytes / %d bytes written",
                               len(command), self._ret_count)
        print("OK.")

    # Read buffer as a string
    def read(self):
        # Read
        if 0 != VisaLibrary.visa.viRead(self._device, self._buffer, self._BUFFER_SIZE, byref(self._ret_count)):
            raise RuntimeError("Could not read data from device")
        # Trim buffer into a string
        response = self._buffer.value[0:self._ret_count.value]
        # Print response
        if self.debug:
            print("Response: %s " % response)
        return response

    # Enable/Disable RF Output
    def set_output_RF(self, enable):
        self.write("RFOutput:STATE %s" % ('ON' if enable else 'OFF'))

    # Enable/Disable LF Output
    def set_output_LF(self, enable):
        self.write("LFOutput:STATE %s" % ('ON' if enable else 'OFF'))

    # Resets signal generator to default values
    def reset(self):
        self.write("*RST")

    # Close device
    def close(self):
        return VisaLibrary.visa.viClose(self._device)

    # Set Frequency in Continuous Wave (CW) [9kHz - 3GHz]
    # Receives a string including value and unit (e.g: "4.3 MHz"), or a number representing frequency in Hz
    # See User's Guide / Subsystem Command Reference / Frequency Subsystem to see available units
    def set_frequency(self, frequency):
        command = "FREQ:CW %s" % self.freq_value_to_string(frequency)
        self.write(command)

    # Set frequency sweep limits for RF ouput [9kHz - 3GHz] and enables sweeping by default
    # Receives strings including value and unit (e.g: "4.3 MHz"), or numbers representing frequency in Hz
    # Optionally set logarithmic scale to sweep (linear by default).
    def set_frequency_sweep(self, start_frequency, stop_frequency, enable=True, logarithmic_scale=False):
        command = "FREQ:RF:START %s" % self.freq_value_to_string(start_frequency)
        self.write(command)
        command = "FREQ:RF:STOP %s" % self.freq_value_to_string(stop_frequency)
        self.write(command)
        # Set sweep scale (logarithmic or linear)
        command = "FREQ:RF:SCALE %s" % ('LOG' if logarithmic_scale else 'LIN')
        self.write(command)
        self.frequency_RF_sweep_enable(enable)

    # Set frequency sweep limits for LF values [0.020 Hz - 80kHz] and enables sweeping by default
    # Receives strings including value and unit (e.g: "3 kHz"), or numbers representing frequency in Hz
    # Logarithmic scale is not available for this range
    def set_frequency_sweep_LF(self, start_frequency, stop_frequency, enable=True):
        command = "FREQ:LF:START %s" % self.freq_value_to_string(start_frequency)
        self.write(command)
        command = "FREQ:LF:STOP %s" % self.freq_value_to_string(stop_frequency)
        self.write(command)
        self.frequency_LF_sweep_enable(enable)

    # Sets Amplitude in Continuous Wave (CW) [-127dBm to +13dBm]
    # Receives a string including value and unit (e.g: "-100 dBm"), or a number representing amplitude in dBm
    # See User's Guide / Subsystem Command Reference / Amplitude Subsystem to see available units and ranges
    def set_amplitude(self, amplitude):
        # Convert numeric value to string value with unit
        if not isinstance(amplitude, str):
            amplitude = "%.7f dBm" % amplitude
        # Build command and send
        command = "AMPL:CW %s" % amplitude
        self.write(command)

    # Sets Amplitude Sweep range [-127dBm to +13dBm] and enables sweep by default
    # Receives strings including value and unit (e.g: "-100 dBm"), or numbers representing amplitude in dBm
    # See User's Guide / Subsystem Command Reference / Amplitude Subsystem to see available units and ranges
    def set_amplitude_sweep(self, start_amplitude, stop_amplitude, enable=True):
        # Convert numeric value to string value with unit
        if not isinstance(start_amplitude, str):
            start_amplitude = "%.7f dBm" % start_amplitude
        if not isinstance(stop_amplitude, str):
            stop_amplitude = "%.7f dBm" % stop_amplitude
        command = "AMPL:START %s" % start_amplitude
        self.write(command)
        command = "AMPL:STOP %s" % stop_amplitude
        self.write(command)
        # Send command to enable amplitude sweep
        self.amplitude_sweep_enable(enable)

    def configure_sweep(self, downward=False, points=10, dwell_ms=10, single=False, external_trigger=False,
                        positive_slope=True):
        self.write("SWEEP:REPEAT %s" % ("SINGLE" if single else "CONTINUOUS"))
        self.write("SWEEP:DIRECTION %s" % ("DOWN" if downward else "UP"))
        self.write("SWEEP:STEP:POINTS %d" % points)
        self.write("SWEEP:STEP:DWELL %d ms" % dwell_ms)
        self.write("SWEEP:STRG %s" % ("EXT" if external_trigger else "KEY"))  # no interest in "IMMEDIATE" here
        if external_trigger:
            self.write("SWEEP:STRG:SLOPE %s" % ("EXTP" if positive_slope else "EXTN"))

    # Cause a sweep in the parameters that have been activated
    def trigger_sweep_now(self, single=False):
        self.write("TRIGGER:%s" % ("SSWP" if single else "IMMEDIATE"))

    # Sweeps are enabled by default when they are configured
    def frequency_RF_sweep_enable(self, enable):
        command = "SWEEP:RF:STATE %s" % ('ON' if enable else 'OFF')
        self.write(command)

    def frequency_LF_sweep_enable(self, enable):
        command = "SWEEP:LF:STATE %s" % ('ON' if enable else 'OFF')
        self.write(command)

    def amplitude_sweep_enable(self, enable):
        command = "SWEEP:AMPL:STATE %s" % ('ON' if enable else 'OFF')
        self.write(command)

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
