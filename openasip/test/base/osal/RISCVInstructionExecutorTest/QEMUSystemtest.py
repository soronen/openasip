#!/usr/bin/env python3
import os
import subprocess
import shlex
import time

QEMU_PATH = os.environ.get("QEMU_PATH", os.path.expandvars("$HOME/qemu-openasip/build"))
QEMU_PATH = "/home/eetu/projects/qemu/build"
LIBOPENASIP = os.environ.get("LIBOPENASIP", "libopenasip.so")
TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
PROGRAM_PATH = os.path.join(TEST_ROOT, "data/crc")
MACHINE_FILE = os.path.join(PROGRAM_PATH, "start.adf")
PROGRAM_COMPILE_COMMAND = "riscv32-unknown-elf-gcc -T link.ld -nostdlib -o crc_program.elf start.S main.c crc.c"
KERNEL = os.path.join(PROGRAM_PATH, "crc_program.elf")
OUTPUT_FILE = os.path.join(PROGRAM_PATH, "output.txt")
EXPECTED_RESULT = """CHECK_VALUE: 0x62488E82
Slow CRC: 0x62488E82
Fast CRC: 0x62488E82
"""


def compile_program():
    original_dir = os.getcwd()
    try:
        os.chdir(PROGRAM_PATH)
        print(f"Compiling in {os.getcwd()}")
        
        result = subprocess.run(
            shlex.split(PROGRAM_COMPILE_COMMAND),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("Compilation successful")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    finally:
        os.chdir(original_dir)


def run_qemu():
    qemu_executable = os.path.join(QEMU_PATH, "qemu-system-riscv32")
    
    print(f"Using QEMU: {qemu_executable}")
    print(f"Using OpenASIP library: {LIBOPENASIP}")
    print(f"Using OpenASIP machine: {MACHINE_FILE}")
    print(f"Using kernel: {KERNEL}")
    
    qemu_cmd = f"{qemu_executable} " \
               f"-machine virt,openasip_machine_path={MACHINE_FILE},libopenasip_path={LIBOPENASIP} " \
               f"-bios none " \
               f"-serial file:{OUTPUT_FILE} " \
               f"-nographic " \
               f"-no-reboot " \
               f"-kernel {KERNEL}"
    
    print(f"Running QEMU command: {qemu_cmd}")
    
    try:
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
            
        process = subprocess.Popen(
            shlex.split(qemu_cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        start_time = time.time()
        timeout = 60
        
        while time.time() - start_time < timeout:
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, 'r') as f:
                    content = f.read()
                    if EXPECTED_RESULT.strip() in content:
                        print("Expected output found - terminating QEMU")
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
            print("Test PASSED: Output matches expected result")
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
    if not compile_program():
        return False
    if not run_qemu():
        return False
    return compare_output()

if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1)