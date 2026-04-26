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

.PHONY: clean
clean:
	if [ -d .venv/mnt ] && mountpoint -q .venv/mnt; then \
	    umount -ql .venv/mnt; \
	fi
	git clean --force -dX

.PHONY: build
build: executable

.PHONY: release
release: build

dist:
	mkdir -p dist

vbuild/cli/__names__.py: $(OBJ)
	emake requirements
	. ${VENV_BIN_ACTIVATE}; \
	python -u write_cli_names.py

dist/vbuild: dist vbuild/cli/__names__.py $(OBJ)
	emake requirements
	. ${VENV_BIN_ACTIVATE}; \
	python -m pip install wheel nuitka zstandard; \
	NUITKA_CACHE_DIR="$(realpath .)/.nuitka" \
	nuitka \
	    --assume-yes-for-downloads \
	    --remove-output \
	    --output-dir=dist \
	    --output-filename=vbuild \
	    vbuild

.PHONY: executable
executable: dist/vbuild

.PHONY: test
test: $(IMAGES) $(OBJ)
	emake requirements
	. ${VENV_BIN_ACTIVATE}; \
	python -u test.py

.PHONY: all
all: release

.PHONY: builder
builder:
	podman build \
	  --tag=ghcr.io/eeems/vbuild-builder \
	  builder/
