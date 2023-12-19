#!/bin/sh

set -e

mypy --strict --disallow-incomplete-defs --disallow-untyped-calls --disallow-untyped-decorators --disallow-untyped-defs miniircd test.py
flake8 miniircd test.py
nosetests3 test.py
