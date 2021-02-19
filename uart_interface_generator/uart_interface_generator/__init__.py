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


    #def write_field_start_def(name, addr, fp):
    #    ''' defines start address '''
    #    fp.write("`define {}_field_addr {}\n".format(name.replace(" ", "_"),
    #                                                 addr // 8))

    #def generate_fields(self):
    #    conf = yaml.load(fp_in, Loader=yaml.Loader)
    #    mem_name = conf["name"]
    #    word_width = conf["word_width"]
    #    address_range = conf["address_range"]

    def call_mem_map(self):
        """Just calls the memory map script in asic utils"""
        out_fpath = os.path.join(self.get_db("internal.job_dir"), "config.yml")
        rel_out_fpath = Path(out_fpath).relative_to(
            self.get_db("internal.work_dir"))
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
        uart_module.add_parameter(Param("BaudRate", 9600))
        uart_module.add_parameter(Param("SystemClockFrequency", 156250000))
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
                    p = Port(f"o_mem_{reg['name']}", IO.OUTPUT, DataType.WIRE,
                             Vec(Range(reg["width"] - 1, 0)))
                else:
                    p = Port(f"i_mem_{reg['name']}", IO.INPUT, DataType.WIRE,
                             Vec(Range(reg["width"] - 1, 0)))
                uart_module.add_port(p)

        # Add signals to top module
        w_width = self.uart["word_width"]
        a_width = self.uart["address_width"]
        uart_module.add_signal(
            Signal("wmem", DataType.WIRE,
                   Vec(Range(w_width - 1, 0), Range((1 << a_width) - 1, 0))))
        uart_module.add_signal(
            Signal("rmem", DataType.WIRE,
                   Vec(Range(w_width - 1, 0), Range((1 << a_width) - 1, 0))))
        uart_module.add_signal(Signal("tx_valid", DataType.WIRE))
        uart_module.add_signal(Signal("tx_ready", DataType.WIRE))
        uart_module.add_signal(
            Signal("tx_data", DataType.WIRE, Vec(Range(7, 0))))
        uart_module.add_signal(Signal("rx_valid", DataType.WIRE))
        uart_module.add_signal(Signal("rx_ready", DataType.WIRE))
        uart_module.add_signal(
            Signal("rx_data", DataType.WIRE, Vec(Range(7, 0))))

        # Create inst of uart
        ports = [(Connection("i_clk", "i_clk"))]
        ports.append((Connection("i_rst", "i_rst")))
        ports.append((Connection("i_rx", "i_uart_rx")))
        ports.append((Connection("o_tx", "o_uart_tx")))
        ports.append((Connection("i_cts_n", "i_uart_cts_n")))
        ports.append((Connection("o_rts_n", "o_uart_rts_n")))
        ports.append((Connection("o_tx_ready", "tx_ready")))
        ports.append((Connection("i_tx_valid", "tx_valid")))
        ports.append((Connection("i_tx_data", "tx_data")))
        ports.append((Connection("i_rx_ready", "rx_ready")))
        ports.append((Connection("o_rx_valid", "rx_valid")))
        ports.append((Connection("o_rx_data", "rx_data")))
        params = [Connection("BaudRate", "BaudRate")]
        params.append(Connection("SystemClockFrequency", "SystemClockFrequency"))
        params.append(Connection("DataSize", 8))
        uart_inst = ModuleInstance("uart", "uart_inst", ports, params)
        uart_module.add_instance(uart_inst)

        # Memory map inst
        ports = []
        ports.append(Connection(f"{self.uart['name']}_write_mem", "wmem"))
        ports.append(Connection(f"{self.uart['name']}_read_mem", "rmem"))
        for field in self.uart["fields"]:
            for reg in field["registers"]:
                if reg["write"]:
                    ports.append(
                        Connection(reg["name"], f"o_mem_{reg['name']}"))
                else:
                    ports.append(
                        Connection(reg["name"], f"i_mem_{reg['name']}"))
        mm_inst = ModuleInstance(f"{self.uart['name']}_mem_map",
                                 f"{self.uart['name']}_mem_map_inst", ports)
        uart_module.add_instance(mm_inst)

        # Memory controller inst
        params = [Connection("DataSize", self.uart["word_width"])]
        ports = [(Connection("i_clk", "i_clk"))]
        ports.append((Connection("i_rst", "i_rst")))
        ports.append((Connection("i_rx_data", "rx_data")))
        ports.append((Connection("i_rx_valid", "rx_valid")))
        ports.append((Connection("o_rx_ready", "rx_ready")))
        ports.append((Connection("o_tx_data", "tx_data")))
        ports.append((Connection("o_tx_valid", "tx_valid")))
        ports.append((Connection("i_tx_ready", "tx_ready")))
        ports.append((Connection("o_wmem", "wmem")))
        ports.append((Connection("i_rmem", "rmem")))
        mem_access_inst = ModuleInstance(f"uart_mem_access",
                                         "uart_mem_access_inst", ports, params)
        uart_module.add_instance(mem_access_inst)

        # Generate file
        out_fpath = os.path.join(self.get_db("internal.job_dir"),
                                 f"{self.uart['name']}.v")
        rel_out_fpath = Path(out_fpath).relative_to(
            self.get_db("internal.work_dir"))
        with open(out_fpath, "w") as fp:
            fp.write(uart_module.to_string())
        self.log(f"Generated final verilog module: {rel_out_fpath}")
