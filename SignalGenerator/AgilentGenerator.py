# -*- coding: utf-8 -*-
"""
This package requires the Visa folder and NIVISA DLL libraries installed.

The software tool 'VISA Interactive Control' (installed with NIVISA), allows searching for connected devices,
and the resource string can be used during initialization, for example:

"""

from __future__ import print_function
from ctypes import *
from functools import reduce

from Visa import VisaLibrary
from math import floor

__author__ = "Braulio Ríos"


# Agilent 33220A Signal Generator
class AgilentGenerator33220A:
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
                if device.find(b"INSTR"):
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
            print("Sending command: \"%s\"..." % command[0:-1].decode(), end=' ')  # Remove line break to print
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
            print("Response: %s " % response.decode())
        return response

    # Resets signal generator to default values
    def reset(self):
        self.write("*RST")

    # Close device
    def close(self):
        return VisaLibrary.visa.viClose(self._device)

    # points_list contains only the Y values for DAC (values in range [-8191,+8191], maximum of 16384 points).
    # The X values will be equispaced between 0 and T=1/frequency.
    # Frequency in Hz, amplitudes in Volts
    def set_custom_waveform(self, points_list_volts, frequency, low_voltage_limit, high_voltage_limit):
        self.write("FREQ %f" % frequency)
        self.write("VOLT:LOW %f" % low_voltage_limit)
        self.write("VOLT:HIGH %f" % high_voltage_limit)
        points_list_str = self.convert_list_to_dac_str(points_list_volts, low_voltage_limit, high_voltage_limit)
        self.write("DATA:DAC VOLATILE, %s" % points_list_str)
        self.write("FUNC:USER VOLATILE")  # select arb function
        self.write("FUNC USER")  # output arb function

    # Receives a list of the form: [t1, t2, t3...], and set the signal generator to
    # generate a custom waveform with pulses starting at t1 and width pulse_width, etc.
    # If slope_up=False, the signal will be in voltage_high by default, and pulses will start with a down slope.
    def set_pulses_waveform(self, pulse_instants, pulse_width, total_period, voltage_low, voltage_high, slope_up=True):
        frequency = 1 / total_period
        # Convert [t1, t2, t3] to [(t1, pulse_width), (t2, pulse_width), ...]
        pulses_list = [(t, pulse_width) for t in pulse_instants]
        # Convert [(t1, width1), (t2, width2), ...] to [(t1, v1), (t2, v2), ...]
        points_sec_volts = self.generate_pulses_waveform(pulses_list, voltage_low, voltage_high, slope_up)
        # Convert [(t1, v1), (t2, v2), ...] to [Y1, Y2, Y3, Y4, ...]
        points_list_volts = self.generate_points_list(points_sec_volts, frequency)
        # Program signal generator
        self.set_custom_waveform(points_list_volts, frequency, voltage_low, voltage_high)

    def set_output(self, enable):
        self.write("OUTPUT %s" % "ON" if enable else "OFF")

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
                frequency = float(frequency) * multiplier
            except:
                raise RuntimeError("Invalid format for frequency. Valid examples: '3.002kHz', '3e3', '3MHZ', '2ghz'"
                                   "/ Invalid examples: '1.0 Hz', '1Hz', '8M' ")
        return frequency

    # Receives a list of the form: [(t1, pulse_width_1), (t2, pulse_width_2)], and generates a list of the form
    # [(t1, v1), (t2, v2), ...] to be passed to set_custom_waveform().
    @staticmethod
    def generate_pulses_waveform(pulses_list, low_voltage_level, high_voltage_level, slope_up=True):
        points_list_volts = [(0, 0)] * len(pulses_list) * 2
        k = 0
        rest_voltage = low_voltage_level if slope_up else high_voltage_level
        pulse_voltage = high_voltage_level if slope_up else low_voltage_level
        for (pulse_start, pulse_width) in pulses_list:
            points_list_volts[k] = (pulse_start, pulse_voltage)
            points_list_volts[k + 1] = (pulse_start + pulse_width, rest_voltage)
            k += 2
        return points_list_volts

    # Receives a list of tuples representing points t (seconds) and y (in volts). E.g: [(0, 3), (1e-3, 1), (0.995, 2.1)]
    # The list of points MUST BE ORDERED in time.
    # Translates the list with any number of points (t, v) to a list of points with only Y values, that the
    # signal generator will place equispaced in each signal period.
    # If the point (0, init_voltage) is not provided, this interval will be set equal to the final voltage.
    @staticmethod
    def generate_points_list(points_sec_volts, target_frequency):
        cycle_period = 1 / target_frequency
        # Try to generate less than 100 points
        gen_points_len = AgilentGenerator33220A.calculate_min_number_of_intervals(points_sec_volts, cycle_period, 100)
        # If limit of 100 points has been reached, use maximum resolution instead
        gen_points_len = gen_points_len if gen_points_len < 100 else 16384
        gen_points = [0] * gen_points_len  # initialize generated array
        gen_dt = cycle_period / gen_points_len  # delta t between generated points
        gen_current_point = 0
        gen_current_y = points_sec_volts[len(points_sec_volts) - 1]  # Set init_voltage = final_voltage by default
        points_sec_volts.append((cycle_period - gen_dt / 2, None))  # Avoid extra loop to fill final voltage until t = T
        for (t, y) in points_sec_volts:
            # Set points with t < t[k] to v[k-1]
            while gen_current_point * gen_dt < t:
                gen_points[gen_current_point] = gen_current_y
                gen_current_point += 1
            gen_current_y = y
        del points_sec_volts[len(points_sec_volts) - 1]  # remove last item added by this function
        return gen_points

    # Receives a list of points with Y values in Volts, and generates a string with corresponding DAC values
    @staticmethod
    def convert_list_to_dac_str(points_list_volts, amplitude_low, amplitude_high):
        dac_high = 8191
        dac_low = -8191
        dac_steps = dac_high - dac_low
        v_steps = amplitude_high - amplitude_low
        dac_val = lambda val: round(dac_low + val * dac_steps / v_steps)
        return ", ".join(str(dac_val(point)) for point in points_list_volts)

    # This function takes an array of time intervals in the form of points [(t1, v1), (t2, v2), (t3, v3)]
    # and calculates the minimum number of equispaced time-intervals required in order to include all boundaries
    @staticmethod
    def calculate_min_number_of_intervals(points_sec_volts, period, max_intervals):
        intervals = [0] * len(points_sec_volts)  # initalize array of intervals

        # Calculate all time intervals
        k = 0
        for k in range(0, len(intervals) - 1):
            intervals[k] = points_sec_volts[k + 1][0] - points_sec_volts[k][0]
        intervals[k + 1] = period - points_sec_volts[k + 1][0]  # add last interval: period - last
        if points_sec_volts[0][0] != 0:
            intervals.insert(0, points_sec_volts[0][0])

        # Retrieve minimum interval
        min_existent_interval = min(intervals)
        if min_existent_interval < 0:
            raise RuntimeError('Some point time is outside the period, or not ordered in the time domain')
        if min_existent_interval == 0:
            raise RuntimeError('Some points provided are redundant (zero-time interval was found)')

        # Calculate minimum interval to fit in all intervals
        min_interval_divisor = 1
        min_calculated_interval = min_existent_interval
        min_error = period / max_intervals
        if period / min_calculated_interval > max_intervals:  # check escape condition with existent intervals
            return max_intervals
        # custom divmod implementation, which avoids numeric errors minor than min_error
        calculate_error = lambda dividend, divisor: dividend - floor(dividend / divisor + min_error) * divisor
        for interval in intervals:
            while calculate_error(interval, min_calculated_interval) > min_error:
                min_interval_divisor += 1
                min_calculated_interval = min_existent_interval / min_interval_divisor
                if period / min_calculated_interval > max_intervals:  # check escape condition with new interval
                    return max_intervals
        return floor(period / min_calculated_interval)


class AgilentGeneratorTests:
    @staticmethod
    def test_intervals_optimizer():
        points = [(0, 0), (0.5, 0)]
        period = 2
        max_intervals = 8

        print("Test 4 intervals...", end=' ')
        n = AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
        print(" [n=%d] " % n, flush=True, end=' ')
        assert n == 4
        print("OK", flush=True)

        period = 1
        max_intervals = 8
        print("Test 2 intervals...", end=' ')
        n = AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
        print(" [n=%d] " % n, flush=True, end=' ')
        assert n == 2
        print("OK", flush=True)

        period = 1
        max_intervals = 8
        points.append((0.5 + period / max_intervals, None))  # add interval of 1/8 of period
        print("Test intervals equal to max_intervals...", end=' ')
        n = AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
        print(" [n=%d] " % n, flush=True, end=' ')
        assert n == max_intervals
        print("OK", flush=True)

        period = 1
        max_intervals = 8
        points.append((0.750 + period / max_intervals - 0.0001, None))  # add interval of < 1/8 of period
        print("Test with intervals greater than max_intervals...", end=' ')
        n = AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
        print(" [n=%d] " % n, flush=True, end=' ')
        assert n == max_intervals
        print("OK", flush=True)

        points = [(0.0001, None), (0.00011, None), (0.000111, None)]
        period = 1
        max_intervals = 1e6
        print("Test 1e6 intervals...", end=' ')
        n = AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
        print(" [n=%d] " % n, flush=True, end=' ')
        assert n == 1e6
        print("OK", flush=True)

        points.append((0.000111 + 1e-7, None))
        period = 1
        max_intervals = 1e6
        print("Test  with intervals greater than max_intervals...", end=' ')
        n = AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
        print(" [n=%d] " % n, flush=True, end=' ')
        assert n == max_intervals
        print("OK", flush=True)

        points.append((0.0001, None))
        try:
            AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
            raise AssertionError("Shall throw exception because points are not time-ordered")
        except RuntimeError:
            print("Test for Disordered points: As expeceted.", flush=True)

        points = [(0.1, None), (0.325, None), (0.5, None)]
        period = 10
        max_intervals = 1e6
        print("Test intervals of 0.025...", end=' ')
        n = AgilentGenerator33220A.calculate_min_number_of_intervals(points, period, max_intervals)
        print(" [n=%d] " % n, flush=True, end=' ')
        assert n == period / 0.025
        print("OK", flush=True)


if __name__ == '__main__':
    AgilentGeneratorTests.test_intervals_optimizer()
