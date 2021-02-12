# Author: Erik Anderson 
# Date Created: 02/12/2021

default: test

# Lints uart_interface_generator directory recursively
lint:
	pylint uart_interface_generator tests

# Formats uart_interface_generator directory recursively
format:
	yapf -i -r uart_interface_generator tests

# Type checks uart_interface_generator directory recursively
type:
	mypy uart_interface_generator tests

# Runs all tests in tests directory 
test:
	pytest -v tests

# Export anaconda environment
export:
	conda env export --from-history | grep -v "prefix" > environment.yml
