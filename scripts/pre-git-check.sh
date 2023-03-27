#!/bin/bash

echo
echo "Checking pylint, xcxc, pytest without touching git"
echo

# Run pylint
echo "--------------------------------------------------------------------"
echo "Running pylint..."
files=$(git ls-files -m -o --exclude-standard '*.py')
for file in $files; do
  if test -e $file; then
    echo $file
    if ! pylint --errors-only --fail-under=10 $file; then
      echo "Lint failed. Exiting."
      exit 1
    fi
  fi
done

if ! pylint --recursive=y nmmo tests; then
  echo "Lint failed. Exiting."
  exit 1
fi

# Check if there are any "xcxc" strings in the code
echo
echo "--------------------------------------------------------------------"
echo "Looking for xcxc..."
files=$(git ls-files '*.py')
for file in $files; do
  if grep -q -F 'xcxc' $file; then
    echo "Found xcxc in $file!" >&2
    read -p "Do you like to stop here? (y/n) " ans
    if [ "$ans" = "y" ]; then
      exit 1
    fi
  fi
done

# Run unit tests
echo
echo "--------------------------------------------------------------------"
echo "Running unit tests..."
if ! pytest; then
  echo "Unit tests failed. Exiting."
  exit 1
fi

echo
echo "Pre-git checks look good!"
echo