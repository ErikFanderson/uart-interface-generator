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
import math

# Imports - 3rd party packages
from toolbox.logger import LogLevel
from toolbox.tool import Tool
from toolbox.utils import *
from toolbox.database import Database
from asic_utils.verilog import *
from asic_utils.str_to_file import *
from jinja_tool import JinjaTool

# TODO get rid of address width? Memory will be sized by number of fields
# TODO make the type only R or W not read: bool write: bool
# Need to make word width adjustable!

class UARTIFaceTool(JinjaTool):
    """Generates UART IFace with memory mapped stuff"""
    def __init__(self, db: Database, log: Callable[[str, LogLevel], None]):
        super(UARTIFaceTool, self).__init__(db, log)
        self.uart = self.get_db(self.get_namespace("UARTIFaceTool"))
        self.bin = BinaryDriver("vlog-mem-map")
        self.db = None 
        self.fields = None
        self.uart["word_width"] = 8
        self.address_width = 7
        # UART blocks only support word width of 8 and address range of 128 (for now)
        self.uart["word_width"] = 8
        self.uart["address_width"] = 7
        self.uart["address_range"] = 1 << self.uart["address_width"]
        # Address buffer is not helpful
        for i, field in enumerate(self.uart["fields"]):
                self.uart["fields"][i]["address_buffer"] = 0

    def steps(self):
        return [self.populate_database, self.call_mem_map, self.gen_python_hal, self.gen_verilog_tasks, self.gen_uart_module]

    def call_mem_map(self):
        """Just calls the memory map script in asic utils"""
        out_fpath = os.path.join(self.get_db("internal.job_dir"), "config.yml")
        rel_out_fpath = Path(out_fpath).relative_to(
            self.get_db("internal.work_dir"))
        with open(out_fpath, "w") as fp:
            fp.write(yaml.dump(self.uart))
        self.log(f"Generated config file for vlog-mem-map: {rel_out_fpath}")
        self.bin.add_option("config.yml")
        self.bin.execute(self.get_db("internal.job_dir"))
    
    #--------------------------------------------------------------------------
    # Database methods 
    #--------------------------------------------------------------------------

    def populate_database(self):
        self.db = self.generate_memory_map_database()
        self.fields = self.generate_fields()
    
    def generate_fields(self):
        """Creates memory map database"""
        fields = {}
        current_address = 0
        for field in self.uart["fields"]:
            fields[field["name"]] = {"registers": {}}
            field_width = 0
            for reg in field["registers"]:
                fields[field["name"]]["registers"][reg["name"]] = {}
                fields[field["name"]]["registers"][reg["name"]]["write"] = reg["write"]
                fields[field["name"]]["registers"][reg["name"]]["width"] = reg["width"] 
                lsb_tot_bp = current_address * self.uart["word_width"] + field_width
                fields[field["name"]]["registers"][reg["name"]]["lsbit_total_bit_position"] = lsb_tot_bp 
                fields[field["name"]]["registers"][reg["name"]]["lsbit_address"] =  math.floor(lsb_tot_bp / self.uart["word_width"])
                fields[field["name"]]["registers"][reg["name"]]["lsbit_address_bit_position"] = lsb_tot_bp % self.uart["word_width"]
                field_width += reg["width"]
                msb_tot_bp = current_address * self.uart["word_width"] + field_width - 1
                fields[field["name"]]["registers"][reg["name"]]["msbit_total_bit_position"] = msb_tot_bp 
                fields[field["name"]]["registers"][reg["name"]]["msbit_address"] =  math.floor(msb_tot_bp / self.uart["word_width"])
                fields[field["name"]]["registers"][reg["name"]]["msbit_address_bit_position"] = msb_tot_bp % self.uart["word_width"]
            num_addresses = math.ceil(field_width / self.uart["word_width"])
            fields[field["name"]]["start_address"] = current_address 
            fields[field["name"]]["end_address"] = current_address + num_addresses - 1 
            current_address += num_addresses
        return fields

    def generate_memory_map_database(self):
        """Creates memory map database"""
        db = {"fields": [], "word_width": self.uart["word_width"]}
        current_address = 0
        for field in self.uart["fields"]:
            field_width = 0
            new_field = {"registers": []}
            for reg in field["registers"]:
                new_reg = {}
                new_reg["name"] = reg["name"]
                new_reg["width"] = reg["width"]
                new_reg["lsbit_total_bit_position"] = current_address * self.uart["word_width"] + field_width
                new_reg["lsbit_address"] =  math.floor(new_reg["lsbit_total_bit_position"] / self.uart["word_width"])
                new_reg["lsbit_address_bit_position"] = new_reg["lsbit_total_bit_position"] % self.uart["word_width"]
                field_width += reg["width"]
                new_reg["msbit_total_bit_position"] = current_address * self.uart["word_width"] + field_width - 1
                new_reg["msbit_address"] =  math.floor(new_reg["msbit_total_bit_position"] / self.uart["word_width"])
                new_reg["msbit_address_bit_position"] = new_reg["msbit_total_bit_position"] % self.uart["word_width"]
                new_field["registers"].append(new_reg)
            num_addresses = math.ceil(field_width / self.uart["word_width"])
            new_field["start_address"] = current_address 
            new_field["end_address"] = current_address + num_addresses - 1 
            db["fields"].append(new_field)
            current_address += num_addresses
        return db
    
    #--------------------------------------------------------------------------
    # Python HAL generation methods
    #--------------------------------------------------------------------------
    
    def gen_python_hal(self):
        template = "UARTDriver.py"
        dest = os.path.join(self.get_db("internal.job_dir"), template)
        self.render_to_file(template, dest, fields=self.fields)
    
    #--------------------------------------------------------------------------
    # Generate verilog bfm 
    #--------------------------------------------------------------------------
    
    def gen_verilog_tasks(self):
        template = "uart_tasks.svh"
        dest = os.path.join(self.get_db("internal.job_dir"), template)
        self.render_to_file(template, dest, fields=self.fields)

    #--------------------------------------------------------------------------
    # Verilog generation methods
    #--------------------------------------------------------------------------

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
        uart_module.add_signal(
            Signal("wmem", DataType.WIRE,
                   Vec(Range(self.uart["word_width"] - 1, 0), Range((1 << self.uart["address_width"]) - 1, 0))))
        uart_module.add_signal(
            Signal("rmem", DataType.WIRE,
                   Vec(Range(self.uart["word_width"] - 1, 0), Range((1 << self.uart["address_width"]) - 1, 0))))
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
