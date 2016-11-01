# -*- coding: utf-8 -*-

# Uso la biblioteca standard https://docs.python.org/2/library/ctypes.html


from Attenuator.RCDATAttenuator import RCDATAttenuator

import traceback
import time


try:
    attenuator = RCDATAttenuator()

    attenuator.set_attenuation(20)
    print("Get attenuation: %.2f" % attenuator.get_attenuation())
    time.sleep(4)
    attenuator.set_attenuation(30)
    print("Get attenuation: %.2f" % attenuator.get_attenuation())
except:
    traceback.print_exc()
