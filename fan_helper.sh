#!/bin/bash

ACPI_CALL=/proc/acpi/call

call_acpi() {
    echo "$1" > $ACPI_CALL
}

case "$1" in
  cpu)
    call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x02,0x32,0x$(printf '%02X' $2),0x00}"
    ;;
  gpu)
    call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x02,0x33,0x$(printf '%02X' $2),0x00}"
    ;;
  both)
    call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x02,0x32,0x$(printf '%02X' $2),0x00}"
    call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x02,0x33,0x$(printf '%02X' $3),0x00}"
    ;;
  profile)
    case "$2" in
      balanced)    call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x01,0xA0,0x00,0x00}" ;;
      performance) call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x01,0xA1,0x00,0x00}" ;;
      quiet)       call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x01,0xA3,0x00,0x00}" ;;
      gameshift)   call_acpi "\_SB.AMWW.WMAX 0 0x15 {0x01,0xAB,0x00,0x00}" ;;
    esac
    ;;
  *)
    echo "Usage: fan_helper.sh cpu <0-100>"
    echo "       fan_helper.sh gpu <0-100>"
    echo "       fan_helper.sh both <cpu%> <gpu%>"
    echo "       fan_helper.sh profile <balanced|performance|quiet|gameshift>"
    exit 1
    ;;
esac
