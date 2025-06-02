# Setting up QEMU and OpenASIP for evaluating custom instructions

1. Install OpenASIP according to the instructions on the repository page.

2. Clone and build QEMU-openasip:

```bash
git clone https://github.com/cpc/qemu-openasip.git
cd qemu-openasip 
./configure --target-list=riscv64-softmmu,riscv32-softmmu
make -j${nproc}
```

3. Install some custom instructions with OpenASIP, or copy some from the qemu-openasip/data to ~/.openasip/.opset/custom, or any other valid path as specified by chapter 4.4 on the manual. There are also custom_instructions.cc and .opp in the data/ folder you can try with.

4. Compile a program that uses those custom instructions. You can use either oacc-riscv or riscv64-unknown-elf-gcc:

```C
# oacc-riscv can compile custom instructions written in C like so:
int output;
int remainder;

_OA_RV_REFLECT32(remainder, output), if you use a normal compiler

# with standard unknown-elf-gcc you can write the custom instructions like so in C:
// same as _OA_RV_REFLECT32(remainder, output)
asm volatile(".insn r 0x0B, 0x01, 0x00, %0, %1, x0"
                 : "=r"(output)
                 : "r"(remainder));

# you can get the bit representation of a custom instruction with $ riscv-tdgen -a /path/to/machine.adf -o out.txt
```

5. Run QEMU RISC-V virt machine with the added **oasip_machine** parameter, which should point to the .adf machine file. Rest of the parameters are given normally.

```bash
OPENASIP_MACHINE=/path/to/machine.adf
KERNEL=/path/to/program.elf
./build/qemu-system-riscv32 \
  -machine virt,oasip_machine=$OPENASIP_MACHINE \
  -bios none \
  -nographic \
  -no-reboot \
  -kernel $KERNEL

```
