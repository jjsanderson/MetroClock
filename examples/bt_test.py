import bluetooth
import binascii
import time

_IRQ_SCAN_RESULT = const(5)
devices = {}

print("Working")

def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:        
        addr_type, addr, connectable, rssi, adv_data = data
        address = binascii.hexlify(addr).decode()
        devices[address] = rssi

ble = bluetooth.BLE() 
print("Bluetooth object instantiated")
ble.active('active')
print("Bluetooth active")
ble.irq(bt_irq)
ble.gap_scan(2000,100)
print("Bluetooth scan started.")
time.sleep(2)
print (devices)
