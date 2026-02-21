#!/bin/bash
exists() {
  if ! [ -f "$1" ]; then
    echo "Missing ${1}"
    return 1
  fi
}
missing() {
  if [ -f "$1" ]; then
    echo "Found ${1}"
    return 1
  fi
}
