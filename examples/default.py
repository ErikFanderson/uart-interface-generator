#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Erik Anderson
# Email: erik.francis.anderson@gmail.com
# Date: 02/18/2021
"""Docstring for module default"""

# Imports - standard library

# Imports - 3rd party packages

# Imports - local source

if __name__ == '__main__':
    for i in range(32):
        print(f"- name: SCAN_IN_INST_{i}_DATA")
        print(f"  address_buffer: 0")
        print(f"  registers:")
        print(f"  - name: scan_in_inst_{i}_data")
        print(f"    read: true")
        print(f"    write: true")
        print(f"    width: 7")
