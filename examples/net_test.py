import network
import binascii
print("working")
wlan = network.WLAN() #  network.WLAN(network.STA_IF)
print("Network object instantiated")
wlan.active(True)
print("Network object active")
networks = wlan.scan() # list with tupples with 6 fields ssid, bssid, channel, RSSI, security, hidden
print("Network scan complete")
i=0
networks.sort(key=lambda x:x[3],reverse=True) # sorted on RSSI (3)
for w in networks:
      i+=1
      print(i,w[0].decode(),binascii.hexlify(w[1]).decode(),w[2],w[3],w[4],w[5])
