NOTA SOBRE ESTA VERSIÓN:
Esta versión está testeada mayormente con Python 3.5 de 32 bits, que se incluye con Anaconda (se recomienda usar este instalador).

AUTOR:
Braulio Ríos

DESCRIPCIÓN:
Esta biblioteca contiene varios módulos que permiten manejar desde Python, distintos dispositivos, como osciloscopios o generadores de señales.
Cada dispositivo está contenido en una carpeta, que se puede no copiar cuando no se necesita, respetando las DEPENDENCIAS.

DEPENDENCIAS INTERNAS (entre paquetes):
- La carpeta Utils debe estar siempre.
- Los instrumentos (SignalGenerator y Oscilloscope) dependen de Visa

DEPENDENCIAS EXTERNAS:
- Los módulos que cargan librerías de C, utilizan C-types.
- Los módulos que cargan librerías de C#, utilizan CLR (Common Language Runtime de C#)
- > pip install ctypes clr
- Drivers de los instrumentos que se vayan a utilizar, y NIVISA.



Los módulos públicos cubiertos hasta ahora son:
- Attenuator: manejo del atenuador usado en las celdas TEM (Hasta ahora sólo se ha testeado RCDAT-6000-60)
- SignalGenerator: Generador de señales (Hasta ahora sólo Agilent RF N9319A 9kHz-3GHz)
- Utils: Tools contiene herramientas para convertir hexa/string/binarios/enteros, endianess, etc.
         BinaryParser permite parsear estructuras de C a partir de cadenas hexadecimales.
- Visa: Carga la DLL visa32.dll (NIVISA), y ofrece sus funciones para usar desde python (no las encapsula).

Los scripts test_*.py se agregan como ejemplos de uso de algunos aparatos.

Para crear ejecutables, que no requieren la instalación de python ni ninguna otra dependencia:
- Instalar PyInstaller (docs en https://pyinstaller.readthedocs.io/en/stable/usage.html):
- > pip install pyinstaller
- Cambiar al directorio de pyDevices
- > cd C:\ruta\a\pyDevices
- Crear el archivo .spec que permite modificar la configuración para incluír paquetes binarios:
- > pyi-makespec --onedir mi_script.py
- NOTA: Si el script incluye DLL's (cargar una API en C# por ejemplo), la opción --onefile no funciona.
- Abrir el archivo generado (eg: "mi_script.spec").
-  Luego que se termina de definir a = Analysis(...), agregar las siguientes líneas:
-    a.binaries=[('clr.pyd', '.'), ('Python.Runtime.dll', '.'), ('Python.Runtime.dll.config', '.')]
- Copiar clr.pyd, Python.Runtime.dll y Python.Runtime.dll.config desde la instalación de python
  (eg: C:\Anaconda3\Lib\site-packages\clr.pyd, etc...) a la carpeta de pyDevices actual.
- Crear el ejecutable:
- > pyinstaller mi_archivo.spec
- Probar el ejecutable que ha sido creado en dist\mi_archivo\mi_archivo.exe
- Distribuír toda la carpeta dist\mi_archivo.