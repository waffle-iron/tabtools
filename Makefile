ENV=$(CURDIR)/.env
BIN=$(ENV)/bin
PYTHON=$(ENV)/bin/python
PYVERSION=$(shell pyversions --default)

RED=\033[0;31m
GREEN=\033[0;32m
NC=\033[0m

.PHONY: help
# target: help - Display callable targets
help:
	@egrep "^# target:" [Mm]akefile


all: env
	@echo "Virtualenv is installed"


.PHONY: clean
# target: clean - Display callable targets
clean:
	@rm -rf build dist docs/_build
	@rm -f *.py[co]
	@rm -f *.orig
	@rm -f *.prof
	@rm -f *.lprof
	@rm -f *.so
	@rm -f */*.py[co]
	@rm -f */*.orig
	@rm -f */*/*.py[co]

.PHONY: register
# target: register - Register module on PyPi
register:
	@python setup.py register

.PHONY: upload
# target: upload - Upload module on PyPi
upload:
	@python setup.py sdist bdist_wheel upload || echo 'Upload already'

.PHONY: test
# target: test - Runs tests
test: clean
	NOSE_REDNOSE=1 $(BIN)/nosetests

.PHONY: lint
# target: lint - audit code
lint:
	@tox -e pylama

env:
	virtualenv --no-site-packages .env
	$(ENV)/bin/pip install -r requirements-dev.txt
