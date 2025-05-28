#!/usr/bin/env python3
import os
import subprocess
import shlex
import time
import shutil
import multiprocessing

QEMU_PATH = os.environ.get("QEMU_PATH", os.path.expandvars("$HOME/qemu-openasip/build"))
TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(TEST_ROOT, "data")
MACHINE_FILE = os.path.join(DATA_PATH, "start.adf")
PROGRAM_COMPILE_COMMAND = "riscv64-unknown-elf-gcc -T link.ld -nostdlib -march=rv32imac -mabi=ilp32 -o crc_program.elf start.S main.c crc.c -g"
KERNEL = os.path.join(DATA_PATH, "crc_program.elf")
OUTPUT_FILE = os.path.join(DATA_PATH, "qemu_test_result.txt")
EXPECTED_RESULT = """CHECK_VALUE: 0x62488E82
Slow CRC: 0x62488E82
Fast CRC: 0x62488E82
"""

def clone_qemu_openasip():
    qemu_dir = os.path.expandvars("$HOME/qemu-openasip")
    
    if os.path.exists(qemu_dir):
        print(f"QEMU OpenASIP directory already exists at {qemu_dir}")
        print("Updating repository with git pull...")
        
        original_dir = os.getcwd()
        try:
            os.chdir(qemu_dir)
            result = subprocess.run(
                ["git", "pull"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"Git pull result: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to update repository: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"Error updating repository: {e}")
            return False
        finally:
            os.chdir(original_dir)
    
    try:
        print("Cloning QEMU OpenASIP repository...")
        result = subprocess.run(
            ["git", "clone", "https://github.com/cpc/qemu-openasip.git", qemu_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("Repository cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error in clone_qemu_openasip: {e}")
        return False

def build_qemu():
    qemu_dir = os.path.expandvars("$HOME/qemu-openasip")
    qemu_executable = os.path.join(QEMU_PATH, "qemu-system-riscv32")
    
    if not os.path.exists(qemu_dir):
        print(f"QEMU OpenASIP directory not found at {qemu_dir}")
        return False
    
    # Skip build if executable already exists
    if os.path.exists(qemu_executable):
        print(f"QEMU executable already exists at {qemu_executable}, skipping build")
        return True
    
    original_dir = os.getcwd()
    try:
        os.chdir(qemu_dir)
        print(f"Building QEMU OpenASIP in {os.getcwd()}")
        
        # Configure QEMU
        configure_cmd = "./configure --target-list=riscv32-softmmu"
        print(f"Running: {configure_cmd}")
        result = subprocess.run(
            shlex.split(configure_cmd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Build QEMU with parallel jobs
        num_cpus = multiprocessing.cpu_count()
        make_cmd = f"make -j{num_cpus}"
        print(f"Running: {make_cmd}")
        result = subprocess.run(
            shlex.split(make_cmd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("QEMU OpenASIP built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to build QEMU OpenASIP: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error in build_qemu: {e}")
        return False
    finally:
        os.chdir(original_dir)

def compile_custom_ops():
    original_dir = os.getcwd()
    try:
        os.chdir(os.path.join(TEST_ROOT, "data"))
        print(f"Building custom ops in {os.getcwd()}")
        
        result = subprocess.run(
            ["buildopset", "riscv_tutorial"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("Custom op building successful")
        
        target_dir = os.path.expandvars("$HOME/.openasip/opset/data")                
        os.makedirs(target_dir, exist_ok=True)
        
        for item in os.listdir('.'):
            src = os.path.join(os.getcwd(), item)
            dst = os.path.join(target_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        print("Custom ops installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Building custom ops failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error in compile_custom_ops: {e}")
        return False
    finally:
        os.chdir(original_dir)

def compile_program():
    original_dir = os.getcwd()
    try:
        os.chdir(DATA_PATH)
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
    print(f"Using OpenASIP machine: {MACHINE_FILE}")
    print(f"Using kernel: {KERNEL}")
    
    qemu_cmd = f"{qemu_executable} " \
               f"-machine virt,openasip_machine_path={MACHINE_FILE} " \
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
        timeout = 5
        
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
    if not clone_qemu_openasip():
        return False
    if not build_qemu():
        return False
    if not compile_custom_ops():
        return False
    if not compile_program():
        return False
    run_qemu()
    return compare_output()

if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1)