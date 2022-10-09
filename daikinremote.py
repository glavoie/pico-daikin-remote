from machine import Pin, PWM
import time
import uctypes

import daikinencoder

# Code timings (In us)
BIT_MARK         = 430
ZERO             = 430
ONE              = 1290
LEADER_SPACE     = 25400
FRAME_START_HIGH = 3500
FRAME_START_LOW  = 1720
GAP              = 34950

# Validation
MIN_TEMP  = 10
MAX_TEMP  = 32
POWER_OFF = 0
POWER_ON  = 1

MODE_MAP = {
    "heat": daikinencoder.HEAT,
    "cool": daikinencoder.COOL,
    "auto": daikinencoder.AUTO,
    "dry": daikinencoder.DRY,
    "fan_only": daikinencoder.FAN,
    "off": daikinencoder.FAN
}

FAN_MAP = {
    "Auto": daikinencoder.FAN_AUTO,
    "Quiet": daikinencoder.FAN_QUIET,
    "1": 3,
    "2": 4,
    "3": 5,
    "4": 6,
    "5": 7
}

# IR carrier configuration
DUTY_ON = 32768 # 1/2
DUTY_OFF = 0
CARRIER_FREQ = 38000

pwm = PWM(Pin(13))
pwm.freq(CARRIER_FREQ)

class RemoteException(Exception):
    pass

def send_code(code):
    # Sending PREAMBLE
    for i in range(6):
        send_signal(DUTY_OFF, ZERO)
        send_signal(DUTY_ON, BIT_MARK)

    send_signal(DUTY_OFF, GAP)

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

    try:
        power_value = int(power)
        if power_value < 0 or power_value > 1:
            raise Exception()

        state.Power = power_value
    except:
        raise RemoteException("Power value must be 0 or 1...")

    try:
        state.Mode = MODE_MAP[mode]
    except:
        raise RemoteException("Invalid mode given... Possible values: heat, cool, auto, dry, fan_only or off")

    try:
        temperature_value = int(temperature)
        if temperature_value < MIN_TEMP or temperature_value > MAX_TEMP:
            raise Exception()

        state.Temperature = temperature_value
    except:
        raise RemoteException("Temperature must be between 10 and 32 (celcius)...")

    try:
        state.Fan = FAN_MAP[fan]
    except:
        raise RemoteException("Invalid fan value... Possible values: Auto, Quiet, 1, 2, 3, 4 or 5.")

    daikinencoder.update_sum(state_raw, state)
    send_code(daikinencoder.get_frames(state_raw))