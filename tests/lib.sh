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
owner() {
  file="$1"
  shift
  if [ $# -gt 0 ];then
    owner="$2"
  else
    owner="$(id -u):$(id -g)"
  fi
  actual="$(stat -c %u:%g "$file")"
  if [[ "$actual" != "$owner" ]];then
    echo "Incorrect owner for $file: $actual"
    exit 1
  fi
}
