# -*- coding: utf-8 -*-

from SignalGenerator.AgilentGenerator import AgilentGenerator33220A

import traceback, json


try:
    device = AgilentGenerator33220A()
    device.reset()
    frequency = 4
    low_limit = 0
    high_limit = 2.5
    # Define the list of points as a list of (time, voltage) tuples
    point_list = [(0, 0.1), (5e-3, 1), (10e-3, 2.5), (0.15, 2)]
    # Convert the (t, v) sequence to generator format: a list with the Y values that will be equispaced in time
    generator_points = AgilentGenerator33220A.generate_points_list(point_list, frequency)
    # print(json.dumps(generator_points, indent=5))
    # Send the order. Signal voltage values will be converted to DAC values between -8191 and 8191
    device.set_custom_waveform(generator_points, frequency, low_limit, high_limit)
    device.set_output(True)
    device.close()



except:
    traceback.print_exc()
