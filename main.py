# From https://datasheets.raspberrypi.com/picow/connecting-to-the-internet-with-pico-w.pdf
import network
import socket
import time
from machine import Pin, PWM

from daikinremote import send_state
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

        query = ''
        url = ''
        path = ''
        query_params = {}
        if line.find('GET') > -1:
            query = line.split(' ')
            url = query[1]

            split_url = url.split('?')
            path = split_url[0]
            query_string = split_url[1] if len(split_url) > 1 else None

            query_params = {}
            if query_string is not None:
                params = query_string.split("&")
                for param_raw in params:
                    param = param_raw.split("=")
                    query_params[param[0]] = param[1]

            print("Path is: " + path)
            print("Params: " + str(query_params))

        if path == "/state":
            send_state(
                query_params['power'],
                query_params['mode'],
                query_params['temperature'],
                query_params['fan']
            )

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
