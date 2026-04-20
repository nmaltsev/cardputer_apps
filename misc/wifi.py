import sys
import os
import time
import json
from pydos_wifi import Pydos_wifi

ssid = Pydos_wifi.getenv('CIRCUITPY_WIFI_SSID')
password = Pydos_wifi.getenv('CIRCUITPY_WIFI_PASSWORD')

if ssid is None:
	print("[SYNC] No WiFi credentials")
	return False

if not Pydos_wifi.connect(ssid, password):
	print("[SYNC] WiFi failed")
	return False
	
# We should have a valid IP now via DHCP
print("My IP address is", Pydos_wifi.ipaddress)
	
if not success:
	for _ in range(3):
		try:
			t = Pydos_wifi.radio.get_time()[0]
			rtc_clock.datetime = time.localtime(t + tz_offset * 3600)
			success = True
			break
		except:
			pass
		
Pydos_wifi.timeout = 1000
response = Pydos_wifi.get("http://worldtimeapi.org/api/ip",None,True)
time_data = Pydos_wifi.json()