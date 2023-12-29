from machine import Pin, PWM
from micropython import const
import time
import uctypes
import gc
import _thread

import daikinencoder

# Validation
MIN_TEMP = 10
MAX_TEMP = 32
POWER_OFF = 0
POWER_ON = 1

MODE_MAP = {
    "heat": daikinencoder.HEAT,
    "cool": daikinencoder.COOL,
    "auto": daikinencoder.AUTO,
    "dry": daikinencoder.DRY,
    "fan_only": daikinencoder.FAN,
    "off": daikinencoder.FAN,
}

FAN_MAP = {
    "Auto": daikinencoder.FAN_AUTO,
    "Quiet": daikinencoder.FAN_QUIET,
    "1": 3,
    "2": 4,
    "3": 5,
    "4": 6,
    "5": 7,
}

# Code timings (In us)
_BIT_MARK = const(425)
_ZERO = const(445)
_ONE = const(1295)
_LEADER_SPACE = const(25400)
_FRAME_START_HIGH = const(3490)
_FRAME_START_LOW = const(1720)
_GAP = const(34950)

# IR carrier configuration
_DUTY_ON = const(16384)  # 1/4
_DUTY_OFF = const(0)
_CARRIER_FREQ = const(38000)

pwm = PWM(Pin(13))
pwm.freq(_CARRIER_FREQ)

BLASTING = False


class RemoteException(Exception):
    pass


def blast_ir_state(code):
    # Sending PREAMBLE
    for i in range(6):
        blast_ir_signal(_DUTY_OFF, _ZERO)
        blast_ir_signal(_DUTY_ON, _BIT_MARK)

    blast_ir_signal(_DUTY_OFF, _GAP)

    # Sending command
    for frame in code:
        blast_ir_signal(_DUTY_ON, _FRAME_START_HIGH)
        blast_ir_signal(_DUTY_OFF, _FRAME_START_LOW)
        blast_ir_signal(_DUTY_ON, _BIT_MARK)

        for byte in frame:
            for i in range(8):
                bit = byte >> i & 1
                blast_ir_signal(_DUTY_OFF, _ONE if bit == 1 else _ZERO)
                blast_ir_signal(_DUTY_ON, _BIT_MARK)

        blast_ir_signal(_DUTY_OFF, _GAP)


def blast_ir_signal(signal, length):
    pwm.duty_u16(signal)
    time.sleep_us(length)

    return length


def prepare_state(power, mode, temperature, fan):
    state_raw = bytearray(daikinencoder.DEFAULT_STATE)
    state = uctypes.struct(
        uctypes.addressof(state_raw),
        daikinencoder.DaikinESPProtocol,
        uctypes.LITTLE_ENDIAN,
    )

    if power == "on":
        state.Power = 1
    else:
        state.Power = 0

    try:
        state.Mode = MODE_MAP[mode]
    except:
        raise RemoteException(
            "Invalid mode given... Possible values: heat, cool, auto, dry, fan_only or off"
        )

    try:
        temperature_value = int(float(temperature))
        if temperature_value < MIN_TEMP or temperature_value > MAX_TEMP:
            raise Exception()

        state.Temperature = temperature_value
    except:
        raise RemoteException("Temperature must be between 10 and 32 (celcius)...")

    try:
        state.Fan = FAN_MAP[fan]
    except:
        raise RemoteException(
            "Invalid fan value... Possible values: Auto, Quiet, 1, 2, 3, 4 or 5."
        )

    daikinencoder.update_sum(state_raw, state)
    return state_raw


def thread_blast_ir_state(code):
    global BLASTING
    try:
        print("Sending IR state to Daikin unit...")
        blast_ir_state(code)
    finally:
        BLASTING = False


def send_daikin_state(power, mode, temperature, fan):
    global BLASTING

    state_raw = prepare_state(power, mode, temperature, fan)

    gc.collect()

    BLASTING = True
    _thread.start_new_thread(
        thread_blast_ir_state, (daikinencoder.get_frames(state_raw),)
    )

    while BLASTING:
        time.sleep_ms(100)
