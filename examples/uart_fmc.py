#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Erik Anderson
# Email: erik.francis.anderson@gmail.com
# Date: 03/08/2022
"""Docstring for module fmc_uart"""

# Imports - standard library

# Imports - 3rd party packages

# Imports - local source

if __name__ == '__main__':
    print('uart.name: "uart_fmc"')
    print('uart.fields:')
    print('- name: "FMC"')
    print('  registers:')
    for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K']:
        for num in range(1,41):
            print(f'  - name: "{letter}{num}"')
            print(f'    read: true')
            print(f'    write: true')
            print(f'    width: 1')

print('- name: "RESET"') 
print('  registers:')
print('  - name: "reset"')
print(f'    read: true')
print(f'    write: true')
print(f'    width: 1')
