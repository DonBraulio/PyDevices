# -*- coding: utf-8 -*-
"""
Use example:

import VisaLibrary
VisaLibrary.visa.viWrite(...)  # It is not required any type of initialization, it's done automatically on import
VisaLibrary.visa.viRead(...)
VisaLibrary.visa.viClose()

The methods of the DLL (see 'NI-VISA User Guide' and 'Programmer Reference') are exposed through VisaLibrary.visa.

The methods with signature do not require c-type conversions (see __load_signatures() to see all signed methods).
Methods without declared signature must be called as VisaLibrary.visa.any_unsigned_method(ctype.c_uint32(30)).

The aim of this class is to avoid repeated calls to Load the DLL file, apply function signatures,
and to create the Default Resource Manager.
It is NOT intended to be a wrapper of the DLL methods.

See the python Ctypes library: https://docs.python.org/2/library/ctypes.html
"""

from ctypes import *
from Visa.lib.constants import *

__author__ = "Braulio Ríos"

# --------------------------- PUBLIC MEMBERS ---------------------------------------------------------------------------
# Automatically initialized on import
visa = None
default_resource_manager = None

# Used constants
BUF_SIZE = 200


# --------------------------- MODULE INITIALIZER -----------------------------------------------------------------------
# See execution at the end of this file
def __init__():

    # Public members to be initialized here
    global visa
    global default_resource_manager

    # Load DLL (windll format, not cdll)
    visa = windll.LoadLibrary(r"C:\Windows\system32\visa32.dll")

    # Define C function signatures
    __load_signatures(visa)  # allows ctypes to cast python vars to proper types expected by the C-functions

    # Open Default Resource Manager
    default_resource_manager = c_uint32()
    if visa.viOpenDefaultRM(byref(default_resource_manager)) != 0:
        raise RuntimeError("Could not open default resource manager from the NI-VISA Library")


# --------------------------- PUBLIC FUNCTIONS -------------------------------------------------------------------------
def list_devices():
    # Find connected devices
    _retCount = c_uint32()
    _findList = c_uint32()
    _instrumentDescription = create_string_buffer(VI_FIND_BUFLEN)
    if 0 != visa.viFindRsrc(default_resource_manager, c_char_p(b'?*INSTR'), byref(_findList), byref(_retCount),
                            _instrumentDescription):
        raise RuntimeError("Could not find resources connected")

    # Append devices to the list
    resources = []
    for i in range(_retCount.value):
        resources.append(_instrumentDescription.value)
        visa.viFindNext(_findList, _instrumentDescription)
    return resources


def open_device(resource_string):
    instrument = c_uint32()
    _retCount = c_uint32()

    if 0 != visa.viOpen(default_resource_manager, resource_string, VI_NULL, VI_NULL, byref(instrument)):
        raise RuntimeError("Could not open instrument")

    # Set the timeout for message-based communication
    if 0 != visa.viSetAttribute(instrument, VI_ATTR_TMO_VALUE, 5000):
        raise RuntimeError("Could not set timeout value of 5000")

    # Ask the device for identification
    query = b'*IDN?\n'
    if 0 != visa.viWrite(instrument, query, len(query), byref(_retCount)):
        raise RuntimeError("Could not write to instrument")

    # Read response and show
    buf = create_string_buffer(BUF_SIZE)
    if 0 != visa.viRead(instrument, buf, BUF_SIZE, byref(_retCount)):
        raise RuntimeError("Could not read from instrument")

    if _retCount.value <= 0:
        raise RuntimeError("Device did not respond to identification")

    print("Device connected: %s " % buf.value.decode())
    return instrument


def close():
    return visa.viClose(default_resource_manager)

# --------------------------- PRIVATE FUNCTIONS ------------------------------------------------------------------------
"""
    Code based on pyvisa.ctwrapper.functions, defines the function signatures (headers),
    so that ctypes will be able to convert the python variables to the proper types that the C functions expect.

    NOTE: c_char_p will be converted to a \00 ended string, unlike POINTER(c_char).
"""


def __apply_signature(library, function, argument_types, return_type):
    function = getattr(library, function)
    function.argtypes = argument_types
    function.resttype = return_type


def __load_signatures(library):
    # function name, argument types, return type
    __apply_signature(library, "viClear", [c_uint32], c_int32)
    __apply_signature(library, "viClose", [c_uint32], c_int32)
    __apply_signature(library, "viFlush", [c_uint32, c_uint16], c_int32)
    __apply_signature(library, "viBufRead", [c_uint32, POINTER(c_char), c_uint32, POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viBufWrite", [c_uint32, POINTER(c_char), c_uint32, POINTER(c_uint32)], c_int32)

    __apply_signature(library, "viRead", [c_uint32, POINTER(c_char), c_uint32, POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viReadAsync", [c_uint32, POINTER(c_char), c_uint32, POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viOpen", [c_uint32, c_char_p, c_uint32, c_uint32, POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viOpenDefaultRM", [POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viWrite", [c_uint32, c_char_p, c_uint32, POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viWriteAsync", [c_uint32, POINTER(c_char), c_uint32, POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viWriteFromFile", [c_uint32, c_char_p, c_uint32, POINTER(c_uint32)], c_int32)
    __apply_signature(library, "viFindNext", [c_uint32, c_char_p], c_int32)
    __apply_signature(library, "viFindRsrc", [c_uint32, c_char_p, POINTER(c_uint32), POINTER(c_uint32), c_char_p], c_int32)

    '''
    NOT IMPLEMENTED YET...
    apply("viAssertIntrSignal", [c_uint32, ViInt16, c_uint32])
    apply("viAssertTrigger", [c_uint32, c_uint16])
    apply("viAssertUtilSignal", [c_uint32, c_uint16])
    apply("viDisableEvent", [c_uint32, ViEventType, c_uint16])
    apply("viDiscardEvents", [c_uint32, ViEventType, c_uint16])
    apply("viEnableEvent", [c_uint32, ViEventType, c_uint16, ViEventFilter])
    apply("viFindNext", [c_uint32, ViAChar])
    apply("viFindRsrc", [c_uint32, c_char_p, ViPFindList, POINTER(c_uint32), ViAChar])
    apply("viGetAttribute", [c_uint32, ViAttr, c_void_p])
    apply("viGpibCommand", [c_uint32, POINTER(c_char), c_uint32, POINTER(c_uint32)])
    apply("viGpibControlATN", [c_uint32, c_uint16])
    apply("viGpibControlREN", [c_uint32, c_uint16])
    apply("viGpibPassControl", [c_uint32, c_uint16, c_uint16])
    apply("viGpibSendIFC", [c_uint32])

    apply("viIn8", [c_uint32, c_uint16, ViBusAddress, ViPUInt8])
    apply("viIn16", [c_uint32, c_uint16, ViBusAddress, ViPUInt16])
    apply("viIn32", [c_uint32, c_uint16, ViBusAddress, POINTER(c_uint32)])
    apply("viIn64", [c_uint32, c_uint16, ViBusAddress, ViPUInt64])

    apply("viIn8Ex", [c_uint32, c_uint16, ViBusAddress64, ViPUInt8])
    apply("viIn16Ex", [c_uint32, c_uint16, ViBusAddress64, ViPUInt16])
    apply("viIn32Ex", [c_uint32, c_uint16, ViBusAddress64, POINTER(c_uint32)])
    apply("viIn64Ex", [c_uint32, c_uint16, ViBusAddress64, ViPUInt64])

    apply("viInstallHandler", [c_uint32, ViEventType, ViHndlr, ViAddr])
    apply("viLock", [c_uint32, ViAccessMode, c_uint32, ViKeyId, ViAChar])
    apply("viMapAddress", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViBoolean, ViAddr, ViPAddr])
    apply("viMapTrigger", [c_uint32, ViInt16, ViInt16, c_uint16])
    apply("viMemAlloc", [c_uint32, ViBusSize, ViPBusAddress])
    apply("viMemFree", [c_uint32, ViBusAddress])
    apply("viMove", [c_uint32, c_uint16, ViBusAddress, c_uint16,
                     c_uint16, ViBusAddress, c_uint16, ViBusSize])
    apply("viMoveAsync", [c_uint32, c_uint16, ViBusAddress, c_uint16,
                          c_uint16, ViBusAddress, c_uint16, ViBusSize,
                          ViPJobId])

    apply("viMoveIn8", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt8])
    apply("viMoveIn16", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt16])
    apply("viMoveIn32", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt32])
    apply("viMoveIn64", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt64])

    apply("viMoveIn8Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt8])
    apply("viMoveIn16Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt16])
    apply("viMoveIn32Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt32])
    apply("viMoveIn64Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt64])

    apply("viMoveOut8", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt8])
    apply("viMoveOut16", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt16])
    apply("viMoveOut32", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt32])
    apply("viMoveOut64", [c_uint32, c_uint16, ViBusAddress, ViBusSize, ViAUInt64])

    apply("viMoveOut8Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt8])
    apply("viMoveOut16Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt16])
    apply("viMoveOut32Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt32])
    apply("viMoveOut64Ex", [c_uint32, c_uint16, ViBusAddress64, ViBusSize, ViAUInt64])


    apply("viOut8", [c_uint32, c_uint16, ViBusAddress, ViUInt8])
    apply("viOut16", [c_uint32, c_uint16, ViBusAddress, c_uint16])
    apply("viOut32", [c_uint32, c_uint16, ViBusAddress, c_uint32])
    apply("viOut64", [c_uint32, c_uint16, ViBusAddress, ViUInt64])

    apply("viOut8Ex", [c_uint32, c_uint16, ViBusAddress64, ViUInt8])
    apply("viOut16Ex", [c_uint32, c_uint16, ViBusAddress64, c_uint16])
    apply("viOut32Ex", [c_uint32, c_uint16, ViBusAddress64, c_uint32])
    apply("viOut64Ex", [c_uint32, c_uint16, ViBusAddress64, ViUInt64])

    apply("viParseRsrc", [c_uint32, ViRsrc, ViPUInt16, ViPUInt16])
    apply("viParseRsrcEx", [c_uint32, ViRsrc, ViPUInt16, ViPUInt16, ViAChar, ViAChar, ViAChar])

    apply("viReadSTB", [c_uint32, ViPUInt16])
    apply("viReadToFile", [c_uint32, c_char_p, c_uint32, POINTER(c_uint32)])

    apply("viSetAttribute", [c_uint32, ViAttr, ViAttrState])
    apply("viSetBuf", [c_uint32, c_uint16, c_uint32])

    apply("viStatusDesc", [c_uint32, c_int32, ViAChar])
    apply("viTerminate", [c_uint32, c_uint16, ViJobId])
    apply("viUninstallHandler", [c_uint32, ViEventType, ViHndlr, ViAddr])
    apply("viUnlock", [c_uint32])
    apply("viUnmapAddress", [c_uint32])
    apply("viUnmapTrigger", [c_uint32, ViInt16, ViInt16])
    apply("viUsbControlIn", [c_uint32, ViInt16, ViInt16, c_uint16,
                             c_uint16, c_uint16, POINTER(c_char), ViPUInt16])
    apply("viUsbControlOut", [c_uint32, ViInt16, ViInt16, c_uint16,
                              c_uint16, c_uint16, POINTER(c_char)])

    # The following "V" routines are *not* implemented in PyVISA, and will
    # never be: viVPrintf, viVQueryf, viVScanf, viVSPrintf, viVSScanf

    apply("viVxiCommandQuery", [c_uint32, c_uint16, c_uint32, POINTER(c_uint32)])
    apply("viWaitOnEvent", [c_uint32, ViEventType, c_uint32, ViPEventType, ViPEvent])



    # Functions that return void.
    apply = _applier(None, None)
    apply("viPeek8", [c_uint32, ViAddr, ViPUInt8])
    apply("viPeek16", [c_uint32, ViAddr, ViPUInt16])
    apply("viPeek32", [c_uint32, ViAddr, POINTER(c_uint32)])
    apply("viPeek64", [c_uint32, ViAddr, ViPUInt64])

    apply("viPoke8", [c_uint32, ViAddr, ViUInt8])
    apply("viPoke16", [c_uint32, ViAddr, c_uint16])
    apply("viPoke32", [c_uint32, ViAddr, c_uint32])
    apply("viPoke64", [c_uint32, ViAddr, ViUInt64])'''


# --------------------------- MODULE INITIALIZING ----------------------------------------------------------------------
# This code is executed on "import VisaLibrary" or "from VisaLibrary import ...".
# If the package is imported multiple times (even across different files), the module code is not actually executed
# unless reload(VisaLibrary) is explicitly executed.
__init__()
