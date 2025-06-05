#!/usr/bin/env python3
### TCE TESTCASE 
### title: Evaluating OSAL instructions with QEMU. Remember to build QEMU first
# 
#  Copyright (C) 2025 Tampere University.

#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License, or (at your option) any later version.

#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.

#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#  
#  
#  @file QEMUSystemtest.py
#  
#  System test for RISCVInstructionExecutor and QEMU-OpenASIP integration
#  
#  @author Eetu Soronen 2025 (eetu.soronen@tuni.fi)
#  @note rating: red
#  

import os
import subprocess
import shlex
import time

QEMU_PATH = os.environ.get("QEMU_OPENASIP_PATH", os.path.expandvars("$HOME/qemu-openasip"))
qemu_build_dir =os.path.join(QEMU_PATH, 'build')

TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(TEST_ROOT, "data")
MACHINE_FILE = os.path.join(DATA_PATH, "machine.adf")
PROGRAM_COMPILE_COMMAND = "riscv64-unknown-elf-gcc -T link.ld -nostdlib -march=rv32imac -mabi=ilp32 -o crc_program.elf start.S main.c crc.c -g"
KERNEL = os.path.join(DATA_PATH, "crc_program.elf")
OUTPUT_FILE = os.path.join(DATA_PATH, "qemu_test_result.txt")
EXPECTED_RESULT = """CHECK_VALUE: 0x62488E82
Slow CRC: 0x62488E82
Fast CRC: 0x62488E82
"""

def qemu_available():
    qemu_executable = os.path.join(qemu_build_dir, "qemu-system-riscv32")
    if not os.path.isfile(qemu_executable) or not os.access(qemu_executable, os.X_OK):
        return False

    return True


def compile_program():
    original_dir = os.getcwd()
    try:
        os.chdir(DATA_PATH)        
        result = subprocess.run(
            shlex.split(PROGRAM_COMPILE_COMMAND),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    finally:
        os.chdir(original_dir)


def run_qemu():
    qemu_executable = os.path.join(qemu_build_dir, "qemu-system-riscv32")
    qemu_cmd = f"{qemu_executable} " \
               f"-machine virt,oasip_machine={MACHINE_FILE} " \
               f"-bios none " \
               f"-serial file:{OUTPUT_FILE} " \
               f"-nographic " \
               f"-no-reboot " \
               f"-kernel {KERNEL}"
    
    try:
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
            
        process = subprocess.Popen(
            shlex.split(qemu_cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        start_time = time.time()
        timeout = 15
        
        while time.time() - start_time < timeout:
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, 'r') as f:
                    content = f.read()
                    if EXPECTED_RESULT.strip() in content:
                        process.terminate()
                        process.wait(timeout=2)
                        return True
            time.sleep(0.1)
        
        print(f"Timeout after {timeout} seconds - terminating QEMU")
        process.terminate()
        process.wait(timeout=2)    
        return False
        
    except Exception as e:
        print(f"QEMU execution failed: {e}")
        try:
            process.terminate()
        except:
            pass
        return False
    
def compare_output():
    try:
        with open(OUTPUT_FILE, 'r') as f:
            actual_output = f.read()
        
        if actual_output.startswith(EXPECTED_RESULT):
            return True
        else:
            print("Test FAILED: Output does not match expected result")
            print(f"Expected:\n{EXPECTED_RESULT}")
            print(f"Actual:\n{actual_output}...")
            return False
    except Exception as e:
        print(f"Error comparing output: {e}")
        return False

def run_test():
    if not qemu_available():
        with open(os.path.join(TEST_ROOT, "tcetest_qemu-openasip.py.disabled"), 'w') as f:
            f.write("qemu is not available, assuming this is by intention and skipping...\n")
        exit(0) 
    if not compile_program():
        return False
    run_qemu()
    return compare_output()

if __name__ == "__main__":
    SYSTEM_TCE_DEVL_MODE = os.environ.get('TCE_DEVEL_MODE', '') 
    os.environ['TCE_DEVEL_MODE'] = '0' # averts a silent linking error that causes the behavior to not load properly
    success = run_test()
    os.environ['TCE_DEVEL_MODE'] = SYSTEM_TCE_DEVL_MODE
    exit(0 if success else 1)