#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Erik Anderson
# Email: erik.francis.anderson@gmail.com
# Date: 02/11/2021
"""Docstring for module main"""

# Imports - standard library

# Imports - 3rd party packages
import serial
import time

# Imports - local source

class UARTDriver():
    """Follows the read/write address protocol for uart mem access fsm"""    
    
    def __init__(self, **kwargs):
        self._ser = serial.Serial(**kwargs)

    def open(self):
        self._ser.open()
    
    def close(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._ser.close()

    def write_byte(self, address: int, data: int):
        num_bytes = self._ser.write(bytes([address, data]))
    
    def read_byte(self, address: int) -> int:
        self._ser.write((address + 128).to_bytes(1, "big"))
        return int.from_bytes(self._ser.read(), "big")

if __name__ == '__main__':
    pass
    # Example
    #drv = UARTDriver(
    #    port="/dev/ttyUSB0",
    #    baudrate=9600,
    #    timeout=1,
    #    write_timeout=1,
    #    bytesize=serial.EIGHTBITS,
    #    rtscts=False,
    #    parity=serial.PARITY_NONE,
    #    stopbits=serial.STOPBITS_ONE)
    #
    #for i in range(100):
    #    print(f"LED write: {i}")
    #    drv.write_byte(0, i)
    #    time.sleep(1)
    #
    #drv.close()
