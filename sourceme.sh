#!/usr/bin/env bash

# Source submodules
cd asic_utils; source sourceme.sh; cd .. 
cd toolbox; source sourceme.sh; cd .. 

# Set UART_INTERFACE_GENERATOR_HOME variable
export UART_INTERFACE_GENERATOR_HOME=$PWD
