CONFIG ?= config.yml

ifndef VERBOSE
.SILENT:
endif

.venv/touchfile: requirements.txt
 	ifeq (, $(shell which virtualenv))
 		$(error "Could not find virtualenv, consider doing `pip install virtualenv`")
 	endif	
	test -d .venv || virtualenv .venv
	. .venv/bin/activate ; pip install -Ur requirements.txt
	touch .venv/touchfile

init: .venv/touchfile

freeze: .venv/touchfile
	set -e ; . .venv/bin/activate ; pip freeze
	
import: .venv/touchfile
	set -e ; . .venv/bin/activate ; python wismap.py import

list: .venv/touchfile
	set -e ; . .venv/bin/activate ; python wismap.py list

info: .venv/touchfile
	set -e ; . .venv/bin/activate ; python wismap.py info

combine: .venv/touchfile
	set -e ; . .venv/bin/activate ; python wismap.py combine

clean:
	set -e ; . .venv/bin/activate ; python wismap.py clean
	find -iname "*.pyc" -delete
	find -iname "__pycache__" -delete

setup:
	pip install -Ur requirements.txt

.PHONY: clean freeze import

