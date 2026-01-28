.DEFAULT_GOAL := all
VERSION := $(shell grep -m 1 version pyproject.toml | tr -s ' ' | tr -d "'\":" | cut -d' ' -f3)
PACKAGE := $(shell grep -m 1 name pyproject.toml | tr -s ' ' | tr -d "'\":" | cut -d' ' -f3)

SHELL := /bin/bash
ifeq ($(OS),Windows_NT)
	SHELL := /bin/bash
	ifeq ($(VENV_BIN_ACTIVATE),)
		VENV_BIN_ACTIVATE := .venv/Scripts/activate
	endif
else
	ifeq ($(VENV_BIN_ACTIVATE),)
		VENV_BIN_ACTIVATE := .venv/bin/activate
	endif
	UNAME_S := $(shell uname -s)
endif

PROTO_SOURCE := $(wildcard protobuf/*.proto)
PROTO_OBJ := $(addprefix $(PACKAGE),$(PROTO_SOURCE:%.proto=%_pb2.py))

OBJ := $(wildcard ${PACKAGE}/**)
OBJ += requirements.txt
OBJ += pyproject.toml
OBJ += README.md
OBJ += $(PROTO_OBJ)

ifeq ($(VENV_BIN_ACTIVATE),)
VENV_BIN_ACTIVATE := .venv/bin/activate
endif

ifeq ($(PYTHON),)
PYTHON := python
endif

WHEEL_NAME := $(shell python wheel_name.py)
_PYTHON_HOST_PLATFORM := $(shell python wheel_name.py --platform)
ARCHFLAGS := $(shell python wheel_name.py --archflags)

clean:
	if [ -d .venv/mnt ] && mountpoint -q .venv/mnt; then \
	    umount -ql .venv/mnt; \
	fi
	git clean --force -dX

build: wheel

release: wheel sdist executable

install: wheel
	if type pipx > /dev/null; then \
	    pipx install \
	        --force \
	        dist/${WHEEL_NAME}; \
	else \
	    pip install \
	        --user \
	        --force-reinstall \
	        --no-index \
	        --find-links=dist \
	        ${PACKAGE}; \
	fi

sdist: dist/${PACKAGE}-${VERSION}.tar.gz

wheel: dist/${WHEEL_NAME}

dist:
	mkdir -p dist

dist/${PACKAGE}-${VERSION}.tar.gz: ${VENV_BIN_ACTIVATE} dist $(OBJ)
	. ${VENV_BIN_ACTIVATE}; \
	python -m build --sdist

dist/${WHEEL_NAME}: ${VENV_BIN_ACTIVATE} dist $(OBJ)
	. ${VENV_BIN_ACTIVATE}; \
	_PYTHON_HOST_PLATFORM="${_PYTHON_HOST_PLATFORM}" \
	ARCHFLAGS="${ARCHFLAGS}" \
	python -m build --wheel
	if ! [ -f "dist/${WHEEL_NAME}" ]; then \
	  echo "${WHEEL_NAME} Missing!"; \
	  exit 1; \
	fi

${VENV_BIN_ACTIVATE}: requirements.txt
	@echo "Setting up development virtual env in .venv"
	python -m venv .venv
	. ${VENV_BIN_ACTIVATE}; \
	python -m pip install wheel build ruff; \
	python -m pip install \
	    --extra-index-url=https://wheels.eeems.codes/ \
	    -r requirements.txt

dist/vbuild: dist ${VENV_BIN_ACTIVATE} $(OBJ)
	. ${VENV_BIN_ACTIVATE}; \
	python -m pip install wheel nuitka; \
	NUITKA_CACHE_DIR="$(realpath .)/.nuitka" \
	nuitka \
	    --assume-yes-for-downloads \
	    --remove-output \
	    --output-dir=dist \
	    --output-filename=vbuild \
	    vbuild

executable: dist/vbuild

test: ${VENV_BIN_ACTIVATE} $(IMAGES) $(OBJ)
	. ${VENV_BIN_ACTIVATE}; \
	python -u test.py

all: release

lint: $(VENV_BIN_ACTIVATE)
	. $(VENV_BIN_ACTIVATE); \
	python -m ruff check

lint-fix: $(VENV_BIN_ACTIVATE)
	. $(VENV_BIN_ACTIVATE); \
	python -m ruff check --fix

format: $(VENV_BIN_ACTIVATE)
	. $(VENV_BIN_ACTIVATE); \
	python -m ruff format --diff

format-fix: $(VENV_BIN_ACTIVATE)
	. $(VENV_BIN_ACTIVATE); \
	python -m ruff format

.PHONY: \
	all \
	build \
	clean \
	executable \
	install \
	release \
	sdist \
	wheel \
	test \
	lint \
	lint-fix \
	format \
	format-fix
