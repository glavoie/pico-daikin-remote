import network
import time
from machine import Pin, PWM
import uasyncio as asyncio
import machine

from daikinremote import RemoteException, send_state
from config import SSID, PASSWORD, API_KEY

led = Pin('LED')
led.value(0)

wlan = network.WLAN(network.STA_IF)

def connect_to_network():
    print('Connecting to Network (timeout 10 seconds)...')

    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    # Wait for connect or fail
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        time.sleep(1)

    # Handle connection error
    if wlan.status() != 3:
        process_failed_network()
    else:
        blink_led(2)

        status = wlan.ifconfig()
        print('Network online! IP: ' + status[0])

def process_failed_network():
    blink_led(3)
    print("Network connection failed... Sleeping 10 seconds then resetting!")
    time.sleep(10)
    machine.reset()

def blink_led(times):
    for i in range(times):
        led.value(1)
        time.sleep_ms(250)
        led.value(0)
        time.sleep_ms(250)

async def serve_client(reader, writer):
    response_code = 200
    response_status = "Success"

    try:
        print("Client connected")

        # Capture request line
        request_line = await reader.readline()
        request = str(request_line)
        print("Request:", request)

        # Ignore the rest of the request
        while await reader.readline() != b"\r\n":
            pass

        # Parse the request
        query = ''
        url = ''
        path = ''
        query_params = {}
        if request.find('GET') > -1:
            query = request.split(' ')
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

        # Process request
        if path == "/state":
            if query_params.get('key', None) != API_KEY:
                response_code = 401
                response_status = "Unauthorized"
            else:
                try:
                    send_state(
                        query_params.get('power', None),
                        query_params.get('mode', None),
                        query_params.get('temperature', None),
                        query_params.get('fan', None)
                    )
                except RemoteException as e:
                    response_code = 500
                    response_status = str(e)
        else:
            response_code = 404
            response_status = "Not found"
    except:
        response_code = 500
        response_status = "Unknown error"
    finally:
        # Return response
        response = '{{"status": "{status}"}}'.format(status=response_status)
        writer.write("HTTP/1.0 {code} OK\r\nContent-type: text/html\r\n\r\n".format(code=response_code))
        writer.write(response)

        await writer.drain()
        await writer.wait_closed()

        print("Client disconnected")

async def main():
    connect_to_network()

    print('Starting web server...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))

    while True:
        await asyncio.sleep(2)

        if wlan.status() != 3:
            process_failed_network()

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
