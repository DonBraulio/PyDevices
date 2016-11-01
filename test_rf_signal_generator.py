# -*- coding: utf-8 -*-

from SignalGenerator.AgilentRFGenerator import AgilentRFGenerator

import traceback, time


try:
    device = AgilentRFGenerator()
    device.reset()
    time.sleep(8)
    device.set_amplitude(1)
    device.set_frequency(4e6)
    time.sleep(5)
    device.set_frequency(9001.2)
    device.set_amplitude(-50)
    time.sleep(5)
    device.set_frequency("3 MHz")
    device.set_amplitude("2 dBm")
    time.sleep(5)
    # Accepted even with no spaces between value and unit (User's guide says that this is invalid but it works)
    device.set_frequency("1MHz")
    device.set_amplitude("20dBm")
    # Freq sweep (LF)
    device.set_frequency_sweep_LF("21e-3kHz", 70e3)
    time.sleep(5)
    # Freq sweep (RF)
    device.set_frequency_sweep(10e3, "2.32ghz")
    time.sleep(5)
    # Freq sweep (RF, logarithmic scale)
    device.set_frequency_sweep(10e3, "2.32ghz", True)
    time.sleep(5)
    # Amplitude sweep
    device.set_amplitude_sweep("-100dBm", "-20.0")

    time.sleep(5)
    device.set_output_RF(True)
    device.set_output_LF(True)
    time.sleep(5)
    device.configure_sweep(True, 200, 1000, False, False)
    time.sleep(5)
    device.trigger_sweep_now()


except:
    traceback.print_exc()
