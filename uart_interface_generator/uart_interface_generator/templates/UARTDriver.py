#===============================================================================
# Autogenerated UARTDriver from uart-interface-generator
# Author: {{_uname}}
# Date Created: {{_date}}
#===============================================================================

import serial

class UARTDriver:
    """Autogenerated UARTDriver from UART-interface-generator"""
    def __init__(self, **kwargs):
        self._ser = serial.Serial(**kwargs)
        self._fields = {{fields}} 

#-------------------------------------------------------------------------------
# Basic read/write methods
#-------------------------------------------------------------------------------
    
    def open(self):
        self._ser.open()

    def close(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._ser.close()
 
    def write_byte(self, address: int, data: int):
        addr_bin = f'0{address:0{{uart["address_width"]}}b}'
        addr_bin += "0" * {{(uart["address_cycles"] * 8) - 1 - uart["address_width"]}}
        bytes_bin = addr_bin + f"{data:08b}" 
        self._ser.write(int(bytes_bin, 2).to_bytes({{uart["address_cycles"] + 1}}, "big"))
 
    def read_byte(self, address: int) -> int:
        addr_bin = f'1{address:0{{uart["address_width"]}}b}'
        addr_bin += "0" * {{(uart["address_cycles"] * 8) - 1 - uart["address_width"]}}
        self._ser.write(int(addr_bin, 2).to_bytes({{uart["address_cycles"]}}, "big"))
        return int.from_bytes(self._ser.read(), "big")

#-------------------------------------------------------------------------------
# Register methods 
#-------------------------------------------------------------------------------
    
    def resize(self, bin_string, new_width):
        if len(bin_string) > new_width: # Truncate
            return bin_string[len(bin_string) - new_width:len(bin_string)]
        elif len(bin_string) < new_width: # Extend
            return (new_width - len(bin_string))*"0" + bin_string
        else:
            return bin_string
    
    def read_all_bytes(self, field: str, reg: str) -> str:
        bin_strings = []
        start_address = self._fields[field]["registers"][reg]["lsbit_address"]
        end_address = self._fields[field]["registers"][reg]["msbit_address"]
        for i in range(start_address, end_address + 1):
            bin_strings.append(f'{self.read_byte(i):08b}')
        bin_string = ""
        for i, bs in enumerate(bin_strings):
            bin_string += bin_strings[len(bin_strings)-1-i]
        return bin_string
    
    def read_register(self, field: str, reg: str) -> str:
        bin_string = self.read_all_bytes(field, reg)
        lsb = len(bin_string) - self._fields[field]["registers"][reg]["lsbit_address_bit_position"]
        msb = 7 - self._fields[field]["registers"][reg]["msbit_address_bit_position"]
        return bin_string[msb:lsb]
    
    def write_register(self, field: str, reg: str, bin_string: str):
        # Read current value first
        current_value = self.read_all_bytes(field, reg)
        num_bits = len(current_value)
        # Resize binary value to write
        bin_string = self.resize(bin_string, self._fields[field]["registers"][reg]["width"])
        # Create new full value for all registers
        new_bin_string = list(current_value)
        for i, char in enumerate(bin_string):
            j = self._fields[field]["registers"][reg]["lsbit_address_bit_position"] 
            new_bin_string[(i + j + 1) * -1] = bin_string[(i + 1) * -1]
        new_bin_string = "".join(new_bin_string)
        # Write bytes
        start_address = self._fields[field]["registers"][reg]["lsbit_address"]
        end_address = self._fields[field]["registers"][reg]["msbit_address"]
        for addr in range(start_address, end_address + 1):
            i = addr - self._fields[field]["registers"][reg]["lsbit_address"]
            lsb = (num_bits - 1) - i * 8 + 1
            msb = (num_bits - 1) - ((i + 1) * 8) + 1
            data = new_bin_string[msb:lsb]
            self.write_byte(addr, int(data, 2))
