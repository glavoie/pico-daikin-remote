# From https://datasheets.raspberrypi.com/picow/connecting-to-the-internet-with-pico-w.pdf
import network
import socket
import time
from machine import Pin, PWM

from daikinremote import ac_on, ac_off
from config import SSID, PASSWORD

led = Pin('LED')
led.value(0)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

html = """<!DOCTYPE html>
<html>
    <head> <title>Pico W - Daikin Remote</title> </head>
    <body> <h1>Pico W - Daikin Remote</h1>
    <p><a href="/on">Turn ON fan</a></p>
    <p><a href="/off">Turn OFF</a></p>
    </body>
</html>
"""

# Wait for connect or fail
max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

# Handle connection error
if wlan.status() != 3:
    raise RuntimeError('network connection failed')
else:
    print('connected')
    led.value(1)
    status = wlan.ifconfig()
    print( 'ip = ' + status[0] )

# Open socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.bind(addr)
s.listen(1)

print('listening on', addr)

# Listen for connections
while True:
    try:
        cl, addr = s.accept()
        print('client connected from', addr)
        cl_file = cl.makefile('rwb', 0)

        line = str(cl_file.readline())

        print("Line: " + line)

        if line.find('/on') > -1:
            ac_on()
        elif line.find('/off') > -1:
            ac_off()

        while True:
            line = cl_file.readline()
            if not line or line == b'\r\n':
                break
        response = html
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(response)
        cl.close()

    except OSError as e:
        cl.close()
        print('connection closed')
