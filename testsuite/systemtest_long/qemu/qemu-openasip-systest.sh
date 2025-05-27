#!/bin/bash
# filepath: /home/eetu/projects/openasip/testsuite/systemtest_long/qemu/qemu-openasip-systest.sh
set -e

# Set up base directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
QEMU_DIR="$BASE_DIR/qemu-openasip"
QEMU_BUILD_DIR="$QEMU_DIR/build"

# Set default LIBOPENASIP path
# if [ -z "$LIBOPENASIP" ]; then
#     LIBOPENASIP="$BASE_DIR/local/lib/libopenasip.so"
# fi

echo "Setting up QEMU OpenASIP testing environment..."

# Clone QEMU OpenASIP if not already present
if [ ! -d "$QEMU_DIR" ]; then
    echo "Cloning QEMU OpenASIP repository..."
    git clone https://github.com/cpc/qemu-openasip.git "$QEMU_DIR"
else
    echo "QEMU OpenASIP repository already exists. Updating..."
    cd "$QEMU_DIR"
    git pull
fi

# Build QEMU OpenASIP
echo "Building QEMU OpenASIP..."
mkdir -p "$QEMU_BUILD_DIR"
cd "$QEMU_BUILD_DIR"

if [ ! -f "$QEMU_BUILD_DIR/config.status" ]; then
    echo "Configuring QEMU..."
    ../configure --target-list=riscv32-softmmu
fi

echo "Compiling QEMU..."
make -j$(nproc)

# Run QEMU System test
echo "Running QEMU System test..."
export QEMU_PATH="$QEMU_BUILD_DIR"

cd "$SCRIPT_DIR"
python3 QEMUSystemtest.py

if [ $? -eq 0 ]; then
    echo "QEMU System test passed successfully!"
    exit 0
else
    echo "QEMU System test failed!"
    exit 1
fi