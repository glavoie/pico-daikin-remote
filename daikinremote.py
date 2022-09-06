from machine import Pin, PWM
import time
import uctypes

import daikinencoder

DUTY_ON = 21843 # 1/3
DUTY_OFF = 0

# In microseconds (us)
START = 280
BIT_MARK = 430
ZERO = 430
ONE = 1300
LEADER_SPACE = 25400
FRAME_START_HIGH = 3500
FRAME_START_LOW = 1730
GAP = 34950

pwm = PWM(Pin(13))

# Carrier frequency
pwm.freq(38000)

def send_code(code):
    # Sending PREAMBLE pulse
    # ... MAYBE... MAYBE NOT

    # Sending command
    for frame in code:
        send_signal(DUTY_ON, FRAME_START_HIGH)
        send_signal(DUTY_OFF, FRAME_START_LOW)
        send_signal(DUTY_ON, BIT_MARK)

        for byte in frame:
            for i in range(8):
                bit = byte >> i & 1
                send_signal(DUTY_OFF, ONE if bit == 1 else ZERO)
                send_signal(DUTY_ON, BIT_MARK)
        
        send_signal(DUTY_OFF, GAP)

def send_signal(signal, length):
    pwm.duty_u16(signal)
    time.sleep_us(length)

    return length

def send_state(power, mode, temperature, fan):
    state_raw = bytearray(daikinencoder.DEFAULT_STATE)
    state = uctypes.struct(uctypes.addressof(state_raw), daikinencoder.DaikinESPProtocol, uctypes.LITTLE_ENDIAN)

    state.Power = int(power)

    mode_map = {
        "heat": daikinencoder.HEAT,
        "cool": daikinencoder.COOL,
        "auto": daikinencoder.AUTO,
        "dry": daikinencoder.DRY,
        "fan_only": daikinencoder.FAN,
        "off": daikinencoder.FAN
    }
    state.Mode = mode_map[mode]
    state.Temperature = int(temperature)

    fan_map = {
        "Auto": daikinencoder.FAN_AUTO,
        "Quiet": daikinencoder.FAN_QUIET,
        "1": 3,
        "2": 4,
        "3": 5,
        "4": 6,
        "5": 7
    }
    state.Fan = fan_map[fan]

    daikinencoder.update_sum(state_raw, state)
    daikinencoder.get_frames(state_raw)

    send_code(daikinencoder.get_frames(state_raw))