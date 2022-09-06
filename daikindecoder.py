from machine import Timer, Pin, PWM
import utime
from time import sleep

led = Pin(25, Pin.OUT)

stream = []
started = False
timer = Timer(-1)


def timer_callback(timer):
    global stream
    global started

    START = 280
    BIT_MARK = 430
    ZERO = 430
    ONE = 1300
    LEADER_SPACE = 25400
    FRAME_START_HIGH = 3500
    FRAME_START_LOW = 1730
    GAP = 34950

    frames = []
    frame = []
    current_frame = -1

    # Dump the captured edges
    print("-----CAPTURE-----")
    for i in range(len(stream)):
        diff = 0
        if i > 0:
            diff = utime.ticks_diff(stream[i][1], stream[i - 1][1])

        if diff > 25200 and diff < 25600:
            frame = []
            current_frame += 1
            print("Capturing frame: " + str(current_frame))

        if diff > 34700 and diff < 35100:
            frames.append(frame)
            frame = []
            current_frame += 1
            print("Capturing frame: " + str(current_frame))

        if stream[i][0] == 0 and diff > 340 and diff < 500:
            frame.append(0)
        
        if stream[i][0] == 0 and diff > 1200 and diff < 1400:
            frame.append(1)

    frames.append(frame)
    
    print(frames)

    byte_frames = []
    for frame in frames:
        byte_arr = []
        count = 0
        byte = 0
        for b in frame:
            byte |= b << count
            count += 1

            if count > 7:
                byte_arr.append("0x{:02x}".format(byte))

                count = 0
                byte = 0
            
        byte_frames.append(byte_arr)

    print(byte_frames)

    print("-----END OF CAPTURE-----")
    started = False
    stream = []

def callback(pin):
    global led
    global stream
    global started
    global timer 

    led.value(1)
    
    if started == False:
        # Capture for 500ms
        timer.init(period=750, mode=Timer.ONE_SHOT, callback=timer_callback)
        started = True

    stream.append((pin.value(), utime.ticks_us()))

    led.value(0)
    
pin = Pin(22, Pin.IN)
pin.irq(callback, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)

while True:
    sleep(1)