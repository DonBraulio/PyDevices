# -*- coding: utf-8 -*-

import traceback

from Oscilloscope.AgilentOscilloscope import AgilentOscilloscopeDSO1002A
from Utils import Excel
from datetime import date
import subprocess

device = None
try:
    device = AgilentOscilloscopeDSO1002A()
    device.reset()

    # Wait for trigger and retrieve data (Volts / seconds)
    time_s, ch1_v, ch2_v = device.get_single_shoot(trigger_channel=1, trigger_level=1.5,
                                                   trigger_slope_down=True, time_scale="200us",
                                                   channel_1_y_scale=1, channel_2_y_scale=1)

    # Create excel file
    excel_file = "oscilloscope_out_%s.xlsx" % date.today()
    time_us = [t*1e6 for t in time_s]
    Excel.plot_signals(excel_file, time_us, ch1_v, 'Channel 1', ch2_v, 'Channel 2',
                       x_label='Time (us)', y_label='Voltage (V)', title="Signal Data")
    # Open excel file
    subprocess.call([r'C:\Program Files (x86)\Microsoft Office\Office15\excel.exe',  excel_file])

except RuntimeError as e:
    traceback.print_exc()
    print("Error description: '%s'" % e)

if device is not None:
    # Screen is locked when remote access is detected
    device.unlock_screen()
