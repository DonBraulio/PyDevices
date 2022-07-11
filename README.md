Dev. environment: Python 3.5 de 32 bits.

DESCRIPCIÓN:
This library enables connection with some oscilloscopes and signal genrators.

Dependencies:
- Drivers for the instruments to use.
- C-types for modules that use C compiled libraries.
- C# CLR (Common Language Runtime) for C# based libraries.
```
pip install ctypes clr
```

Modules covered so far:
- SignalGenerator (tested Agilent RF N9319A 9kHz-3GHz)
- Attenuator: TEM cells attenuator (tested RCDAT-6000-60)
- Utils: conversions between hexa/string/binaries/integers, endianess, etc.
         BinaryParser to parse C structures from hex strings.
- Visa: Loads visa32.dll (NIVISA), and its functions can be used from python (not wrapped).

Some examples are provided as test_*.py.
