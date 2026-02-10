.DEFAULT_GOAL := all
PACKAGE := $(shell grep -m 1 name pyproject.toml | tr -s ' ' | tr -d "'\":" | cut -d' ' -f3)
SHELL := /bin/bash

ifeq ($(VENV_BIN_ACTIVATE),)
VENV_BIN_ACTIVATE := .venv/bin/activate
endif

ifeq ($(PYTHON),)
PYTHON := python
endif

OBJ := $(wildcard ${PACKAGE}/**)
OBJ += requirements.txt
OBJ += pyproject.toml
OBJ += README.md

clean:
	if [ -d .venv/mnt ] && mountpoint -q .venv/mnt; then \
	    umount -ql .venv/mnt; \
	fi
	git clean --force -dX

build: executable

release: build

dist:
	mkdir -p dist

${VENV_BIN_ACTIVATE}: requirements.txt
	@echo "Setting up development virtual env in .venv"
	python -m venv .venv
	. ${VENV_BIN_ACTIVATE}; \
	python -m pip install wheel build ruff; \
	python -m pip install \
	    --extra-index-url=https://wheels.eeems.codes/ \
	    -r requirements.txt

vbuild/cli/__names__.py: ${VENV_BIN_ACTIVATE} $(OBJ)
	. ${VENV_BIN_ACTIVATE}; \
	python -u write_cli_names.py

dist/vbuild: dist vbuild/cli/__names__.py ${VENV_BIN_ACTIVATE} $(OBJ)
	. ${VENV_BIN_ACTIVATE}; \
	python -m pip install wheel nuitka zstandard; \
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

builder:
	podman build \
	  --tag=ghcr.io/eeems/vbuild-builder \
	  builder/

.PHONY: \
	all \
	build \
	clean \
	executable \
	release \
	test \
	lint \
	lint-fix \
	format \
	format-fix \
	builder
