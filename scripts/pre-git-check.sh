#!/bin/bash

echo
echo "Checking pylint, xcxc, pytest without touching git"
echo

# Run linter
echo "--------------------------------------------------------------------"
echo "Running linter..."
if ! pylint --rcfile=pylint.cfg --fail-under=10 $(git ls-files '*.py'); then
    echo "Lint failed. Exiting."
    exit 1
fi

# Check if there are any "xcxc" strings in the code
echo "--------------------------------------------------------------------"
echo "Looking for xcxc..."
files=$(find . -name '*.py')
for file in $files; do
    if grep -q 'xcxc' $file; then
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