Some information about the USB protocol spoken by the Komplete Kontrol can be
found here.

## USB endpoints / interfaces

It provides 4 USB endpoints:

* Default (USB internal) config
* Realtime streaming endpoint for MIDI data
* HID interface, used for:
    * Configuring the device's functions
    * Reading button and knob states
* Bulk data endpoint for sending display image data

Code for interfacing the display lies in `gui_hw.py`.

The MIDI interface is standard.

The most interesting part is probably the HID interface.

## HID Interface

There are some files in this folder just containing usb hiddump output. This
includes descriptor data.

A breakdown of the different HID reports can be found in [doc.txt](doc.txt).
The data types there are taken from the HID descriptor.
[Useful parsing tool.](https://eleccelerator.com/usbdescreqparser/)

The file `util.py` contains some API classes to construct configuration
reports. It also provides detailed info about button and color ordering, input
element config fields and such.
