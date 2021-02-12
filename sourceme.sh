#!/usr/bin/env bash

# Set PYTHONPATH accordingly
if [ -z "$PYTHONPATH" ]
then
    export PYTHONPATH=$PWD
else
    export PYTHONPATH=$PWD:$PYTHONPATH
fi

# Set MYPYPATH accordingly
if [ -z "$MYPYPATH" ]
then
    export MYPYPATH=$PWD/uart_interface_generator
else
    export MYPYPATH=$PWD/uart_interface_generator:$MYPYPATH
fi

# Set UART_INTERFACE_GENERATOR_HOME variable
export UART_INTERFACE_GENERATOR_HOME=$PWD
