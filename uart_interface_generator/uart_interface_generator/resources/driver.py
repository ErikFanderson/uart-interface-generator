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

# TODO Autogenerate HAL class to read and write every single register
# TODO Class should also contain its own memory to keep track of LAST WRITTEN/READ value of each register

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

    def write_byte(self, address: int, data: int, verify: bool = False, verbose: bool = False):
        """Returns True if not verified and True if verify is correct. False otherwise"""
        num_bytes = self._ser.write(bytes([address, data]))
        if verify:
            rdata = self.read_byte(address)
            if rdata == data:
                if verbose: 
                    print(f"[PASS] Address 0x{hex(address)} => Write: {hex(data)}, Read: {hex(rdata)}")
                return True
            else:
                if verbose: 
                    print(f"[FAIL] Address 0x{hex(address)} => Write: {hex(data)}, Read: {hex(rdata)}")
                return False
        else:
            if verbose: 
                print(f"Address 0x{hex(address)} => Write: {hex(data)}")
            return True
    
    def read_byte(self, address: int) -> int:
        self._ser.write((address + 128).to_bytes(1, "big"))
        return int.from_bytes(self._ser.read(), "big")

class SuperSwitchDriver(UARTDriver): 
   
    def __init__(self, **kwargs):
        super(SuperSwitchDriver, self).__init__(**kwargs)

    def initialize(self):
        """Place design in reset and initialize all memory addresses"""
        print("Initializing uart memory...")
        self.write_byte(63, 0x01, verify=True, verbose=True) # Reset high
        for i in range(63):
            self.write_byte(i, 0x00, verify=True, verbose=True)
        self.write_byte(63, 0x00, verify=True, verbose=True) # Reset low
        print("Uart memory initialized!")

    def toggle_scan_reset(self):
        """
        Toggles scan reset using the address scan controller
        1. Set address cmd = CMD_RST
        2. Toggle address wen 
        """
        self.write_addr_cmd(0)
        self.read_addr_wen()
        self.read_addr_wen()

    #--------------------------------------------------------------------------
    # Address methods
    #--------------------------------------------------------------------------

    def write_addr_cmd(self):
        """
        Writes to address scan controller cmd memory
        Width: 2 
        Address: 1 
        CMD_RST = 0
        CMD_SI = 1
        CMD_SO = 2
        CMD_UPDATE = 3
        """
        write_byte

        pass

    def write_addr_data:
        """
        Writes to address scan controller data memory
        Width: 7
        Address: 0 
        [6] Global enable signal (0 => disabled, 1 => enabled)
        [5:2] scanOutLoopback mux select (0 => scanInInst 0, ... , 8 => scanInLoopback)
        [1:0] address
        """
        pass
    
    def write_addr_wen:
        pass
    
    def read_addr_wen:
        pass
    
    #--------------------------------------------------------------------------
    # Instruction methods
    #--------------------------------------------------------------------------

    def write_inst

    #def write_address(self, address: int):
    #    pass

    #def read_address(self):
    #    pass

    #def scan_in_addr_scan(self, address: int) -> int:
    #    pass
    #
    #def scan_out_addr_scan(self) -> int:
    #    pass
    #
    #def scan_out_rst_toggle(self):
    #    pass
    #
    #def scan_out_address(self):
    #    pass

if __name__ == '__main__':
    pass
