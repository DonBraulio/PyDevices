# -*- coding: utf-8 -*-

import clr
import sys
import os

# Agrega directorio "lib\Attenuator" al path para buscar dlls
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

# Agregar dlls de C# (wrappers para el driver del atenuador: mcl_RUDAT.dll)
clr.AddReferenceToFile("AttenuatorCSharpWrapper.dll")

import AttenuatorCSharpWrapper.Attenuator

__author__ = "Braulio Ríos"


# Based on RCDAT-6000-60 Attenuator
class RCDATAttenuator:

    debug = True

    def __init__(self):
        self.attenuator = AttenuatorCSharpWrapper.Attenuator()
        if not self.attenuator.IsConnected():
            raise RuntimeError("Attenuator is not connected")
        if self.debug:
            print("Attenuator Connected. SN: %s / Model Name: %s" % (self.get_serial_number(), self.get_model_name()))

    def set_attenuation(self, attenuation):
        if self.debug:
            print("Setting Attenuator to %.2f" % attenuation)
        return self.attenuator.SetAttenuation(attenuation)

    def get_attenuation(self):
        return self.attenuator.GetAttenuation()

    def get_model_name(self):
        return self.attenuator.GetModelName()

    def get_serial_number(self):
        return self.attenuator.GetSerialNumber()

    def close(self):
        self.attenuator.Disconnect()
