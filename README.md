# Alienware 16X Aurora Fan Control for Linux

A fan speed controller for the Alienware 16X Aurora (AC16251) on Linux,
achieved through reverse engineering of the ACPI/WMI interface.

<img width="918" height="795" alt="image" src="https://github.com/user-attachments/assets/4e1d98ca-fec4-41cd-a11b-a1cf585dfed1" />



## Hardware
- Machine: Alienware 16X Aurora AC16251
- CPU: Intel Core Ultra 9 275HX
- GPU: NVIDIA GeForce RTX 5070 Laptop
- Tested on: Arch Linux, kernel 6.18.24-1-lts

## How it works

Dell/Alienware exposes fan control through a proprietary WMI interface
(AWCCWmiMethodFunction) implemented in ACPI SSDT table AWCCTABL.

By decompiling the ACPI tables and reverse engineering the WMAX method,
we discovered the following protocol:

### Fan Control Commands (via /proc/acpi/call)

CPU fan speed (0-100%):
echo '\_SB.AMWW.WMAX 0 0x15 {0x02,0x32,SPEED,0x00}' > /proc/acpi/call

GPU fan speed (0-100%):
echo '\_SB.AMWW.WMAX 0 0x15 {0x02,0x33,SPEED,0x00}' > /proc/acpi/call

Thermal profiles:
echo '\_SB.AMWW.WMAX 0 0x15 {0x01,0xA0,0x00,0x00}' > /proc/acpi/call  # Balanced
echo '\_SB.AMWW.WMAX 0 0x15 {0x01,0xA1,0x00,0x00}' > /proc/acpi/call  # Performance
echo '\_SB.AMWW.WMAX 0 0x15 {0x01,0xA3,0x00,0x00}' > /proc/acpi/call  # Quiet
echo '\_SB.AMWW.WMAX 0 0x15 {0x01,0xAB,0x00,0x00}' > /proc/acpi/call  # Game Shift

Where SPEED is a hex value from 0x00 (0%) to 0x64 (100%).

### Fan IDs
- 0x32 = CPU fan
- 0x33 = GPU fan

## Dependencies

Arch Linux:
sudo pacman -S acpi_call-lts python-gobject gtk4 libadwaita

Load module:
sudo modprobe acpi_call

Auto-load on boot:
echo 'acpi_call' | sudo tee /etc/modules-load.d/acpi_call.conf

## Installation

git clone https://github.com/Hugo2049/alienware-16x-fan-control
cd alienware-16x-fan-control

Add sudoers rule:
echo "$USER ALL=(ALL) NOPASSWD: $(pwd)/fan_helper.sh" | sudo tee /etc/sudoers.d/fancontroller
sudo chmod 440 /etc/sudoers.d/fancontroller
chmod +x fan_helper.sh

Run:
python fan_control.py

## CLI Usage

sudo ./fan_helper.sh cpu 75
sudo ./fan_helper.sh gpu 50
sudo ./fan_helper.sh both 80 60
sudo ./fan_helper.sh profile performance

## Discovery Method

1. Dumped ACPI tables with acpidump
2. Decompiled SSDT tables with iasl
3. Found AWCCTABL SSDT containing AWCCWmiMethodFunction implementation
4. Reverse engineered WMAX method and AX24/AX26 sub-functions
5. Identified EC register writes via ECW1(0x21, speed) and ECW1(0x39, fan_id)
6. Confirmed via acpi_call kernel module

## Credits

Developed by Hugo (Hugo2049) with assistance from Claude (Anthropic).
The reverse engineering methodology, ACPI analysis, and protocol discovery
were worked out collaboratively through an iterative process of dumping
tables, reading ASL source, probing WMI interfaces on Windows, and
testing on Linux via acpi_call.

Claude: https://claude.ai
Anthropic: https://anthropic.com

## License
GPL-2.0
