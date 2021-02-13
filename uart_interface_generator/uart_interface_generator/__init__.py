#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Erik Anderson
# Email: erik.francis.anderson@gmail.com
# Date: 03/03/2020
"""Docstring for module __init__.py"""

# Imports - standard library
import re
from dataclasses import dataclass, replace
from typing import List, Callable
import os
import fnmatch
import yaml

# Imports - 3rd party packages
from toolbox.logger import LogLevel
from toolbox.tool import Tool
from toolbox.utils import * 
from toolbox.database import Database
from asic_utils.verilog import *
from jinja_tool import JinjaTool


class UARTIFaceTool(Tool):
    """Generates UART IFace with memory mapped stuff"""
    def __init__(self, db: Database, log: Callable[[str, LogLevel], None]):
        super(UARTIFaceTool, self).__init__(db, log)
        self.uart = self.get_db(self.get_namespace("UARTIFaceTool"))
        self.bin = BinaryDriver("vlog-mem-map")

    def steps(self):
        return [self.call_mem_map, self.gen_uart_module]

    def call_mem_map(self):
        """Just calls the memory map script in asic utils"""
        out_fpath = os.path.join(self.get_db("internal.job_dir"), "config.yml")
        rel_out_fpath = Path(out_fpath).relative_to(self.get_db("internal.work_dir"))
        self.uart["address_range"] = 1 << self.uart["address_width"]
        with open(out_fpath, "w") as fp:
            fp.write(yaml.dump(self.uart))
        self.log(f"Generated config file for vlog-mem-map: {rel_out_fpath}")
        self.bin.add_option("config.yml")
        print(self.bin.get_execute_string())
        self.bin.execute(self.get_db("internal.job_dir"))

    def gen_uart_module(self):
        """Builds a uart module that combines memory map, uart block, and uart memory access FSM"""
        # Create top module
        uart_module = Module(self.uart["name"])
        uart_module.add_port(Port("i_clk", IO.INPUT, DataType.WIRE))
        uart_module.add_port(Port("i_rst", IO.INPUT, DataType.WIRE))
        uart_module.add_port(Port("o_uart_tx", IO.OUTPUT, DataType.WIRE))
        uart_module.add_port(Port("i_uart_rx", IO.INPUT, DataType.WIRE))
        uart_module.add_port(Port("o_uart_rts_n", IO.OUTPUT, DataType.WIRE))
        uart_module.add_port(Port("i_uart_cts_n", IO.INPUT, DataType.WIRE))
        uart_module.add_port(Port("o_uart_rx_error", IO.OUTPUT, DataType.WIRE))
        for field in self.uart["fields"]:
            for reg in field["registers"]:
                if reg["write"]:
                    p = Port(f"o_mem_{reg['name']}", IO.OUTPUT, DataType.WIRE, Vec(Range(reg["width"]-1, 0)))
                else:
                    p = Port(f"i_mem_{reg['name']}", IO.INPUT, DataType.WIRE, Vec(Range(reg["width"]-1, 0)))
                uart_module.add_port(p)

        # Add signals to top module 
        w_width = self.uart["word_width"]
        a_width = self.uart["address_width"]
        uart_module.add_signal(Signal("wmem", DataType.WIRE, Vec(Range(w_width - 1, 0), Range((1 << a_width) - 1, 0))))
        uart_module.add_signal(Signal("rmem", DataType.WIRE, Vec(Range(w_width - 1, 0), Range((1 << a_width) - 1, 0))))
        uart_module.add_signal(Signal("tx_en", DataType.WIRE))
        uart_module.add_signal(Signal("tx_byte", DataType.WIRE, Vec(Range(7, 0))))
        uart_module.add_signal(Signal("rx_done", DataType.WIRE))
        uart_module.add_signal(Signal("rx_byte", DataType.WIRE, Vec(Range(7, 0))))
        uart_module.add_signal(Signal("rx_busy", DataType.WIRE))
        uart_module.add_signal(Signal("tx_busy", DataType.WIRE))
        uart_module.add_signal(Signal("rx_data_valid", DataType.WIRE))
        uart_module.add_signal(Signal("rx_data_ready", DataType.WIRE))
        uart_module.add_signal(Signal("tx_data_valid", DataType.WIRE))
        uart_module.add_signal(Signal("tx_data_ready", DataType.WIRE))

        # Assign statements
        # TODO may want to build a ready valid interface into the UART... Current one doesn't have one.
        # IF rx_done is asserted but we are not ready to process is then we lost the data potentially
        # Honestly this will probably still work.
        uart_module.add_internal("assign rx_data_valid = rx_done;\n") # TODO data valid needs to stay valid until processed!!?
        uart_module.add_internal("assign o_uart_rts_n = !(rx_data_ready && rx_busy);\n")
        uart_module.add_internal("assign tx_data_ready = !(i_uart_cts_n && tx_busy);\n")
        uart_module.add_internal("assign tx_en = tx_data_valid;\n")

        # Create inst of uart
        ports = [(Connection("clk", "i_clk"))]
        ports.append((Connection("rst", "i_rst")))
        ports.append((Connection("rx", "i_uart_rx")))
        ports.append((Connection("tx", "o_uart_tx")))
        ports.append((Connection("transmit", "tx_en")))
        ports.append((Connection("tx_byte", "tx_byte")))
        ports.append((Connection("received", "rx_done")))
        ports.append((Connection("rx_byte", "rx_byte")))
        ports.append((Connection("is_receiving", "rx_busy")))
        ports.append((Connection("is_transmitting", "tx_busy")))
        ports.append((Connection("recv_error", "o_uart_rx_error")))
        params = [Connection("baud_rate", "BaudRate")]
        params.append(Connection("sys_clk_freq", "SystemClockFrequency"))
        uart_inst = ModuleInstance("uart", "uart_inst", ports, params)
        uart_module.add_instance(uart_inst)
        
        # Memory map inst
        ports = []
        for field in self.uart["fields"]:
            for reg in field["registers"]:
                if reg["write"]:
                    ports.append(Connection(reg["name"], f"o_mem_{reg['name']}"))
                else:
                    ports.append(Connection(reg["name"], f"i_mem_{reg['name']}"))
        mm_inst = ModuleInstance(f"{self.uart['name']}_mem_map", f"{self.uart['name']}_mem_map_inst", ports)
        uart_module.add_instance(mm_inst)
        
        # Memory controller inst
        ports = [(Connection("i_clk", "i_clk"))]
        ports.append((Connection("i_rst", "i_rst")))
        ports.append((Connection("i_rx_data", "rx_byte")))
        ports.append((Connection("i_rx_data_valid", "rx_data_valid")))
        ports.append((Connection("o_rx_data_ready", "rx_data_ready")))
        ports.append((Connection("o_tx_data", "tx_byte")))
        ports.append((Connection("o_tx_data_valid", "tx_data_valid")))
        ports.append((Connection("i_tx_data_ready", "tx_data_ready")))
        ports.append((Connection("o_wmem", "wmem")))
        ports.append((Connection("i_rmem", "rmem")))
        
        mem_access_inst = ModuleInstance(f"uart_mem_access", "uart_mem_access_inst", ports)
        uart_module.add_instance(mem_access_inst)
        
        # Generate file
        out_fpath = os.path.join(self.get_db("internal.job_dir"), f"{self.uart['name']}.v")
        rel_out_fpath = Path(out_fpath).relative_to(self.get_db("internal.work_dir"))
        with open(out_fpath, "w") as fp:
            fp.write(uart_module.to_string())
        self.log(f"Generated final verilog module: {rel_out_fpath}")

