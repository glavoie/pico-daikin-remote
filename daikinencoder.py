import uctypes

FRAME_1_SIZE = 8
FRAME_2_SIZE = 8
FRAME_3_SIZE = 19

AUTO = 0b000;  
DRY =  0b010;  
COOL = 0b011;
HEAT = 0b100;  
FAN =  0b110;  
MIN_TEMP = 10;  
MAX_TEMP = 32;  
FAN_MIN = 3;
FAN_MAX = 7
FAN_AUTO = 0xA;  
FAN_QUIET = 0xB;  
SWING_ON =  0b1111;
SWING_OFF = 0b0000;

# OFF - FAN - 23C - FAN AUTO - Everything else off
DEFAULT_STATE = [
    0x11, 0xda, 0x27, 0x00, 0xc5, 0x10, 0x00, 0xe7, 
    0x11, 0xda, 0x27, 0x00, 0x42, 0x00, 0x08, 0x5c, 
    0x11, 0xda, 0x27, 0x00, 0x00, 0x68, 0x32, 0x00, 0xa0, 0x00, 0x00, 0x06, 0x60, 0x00, 0x00, 0xc1, 0x00, 0x00, 0x73
]

DaikinESPProtocol = {
    #Frame 1
    "Header1": (0 | uctypes.ARRAY, 5 | uctypes.UINT8),

    "Comfort": 6 | uctypes.BFUINT8 | 4 << uctypes.BF_POS | 1 << uctypes.BF_LEN,

    "Sum1": 7 | uctypes.UINT8,

    #Frame 2
    "Header2": (8 | uctypes.ARRAY, 5 | uctypes.UINT8),

    "Time": 13 | uctypes.BFUINT16 | 0 << uctypes.BF_POS | 11 << uctypes.BF_LEN,      # Minutes past midnight
    "DayOfWeek": 13 | uctypes.BFUINT16 | 11 << uctypes.BF_POS | 3 << uctypes.BF_LEN, # Sunday = 1, Monday = 2
    
    "Sum2": 15 | uctypes.UINT8,

    #Frame 3
    "Header3": (16 | uctypes.ARRAY, 5 | uctypes.UINT8),

    "Power": 21 | uctypes.BFUINT8 | 0 << uctypes.BF_POS | 1 << uctypes.BF_LEN,
    "high_bit": 21 | uctypes.BFUINT8 | 3 << uctypes.BF_POS | 1 << uctypes.BF_LEN, # Always 1
    "Mode": 21 | uctypes.BFUINT8 | 4 << uctypes.BF_POS | 3 << uctypes.BF_LEN,

    "Temperature": 22 | uctypes.BFUINT8 | 1 << uctypes.BF_POS | 7 << uctypes.BF_LEN,

    "SwingV": 24 | uctypes.BFUINT8 | 0 << uctypes.BF_POS | 4 << uctypes.BF_LEN,
    "Fan": 24 | uctypes.BFUINT8 | 4 << uctypes.BF_POS | 4 << uctypes.BF_LEN,

    "SwingH": 25 | uctypes.BFUINT8 | 0 << uctypes.BF_POS | 4 << uctypes.BF_LEN,

    "Powerful": 29 | uctypes.BFUINT8 | 0 << uctypes.BF_POS | 1 << uctypes.BF_LEN,
    "Quiet": 29 | uctypes.BFUINT8 | 5 << uctypes.BF_POS | 1 << uctypes.BF_LEN,

    "Sensor": 32 | uctypes.BFUINT8 | 1 << uctypes.BF_POS | 1 << uctypes.BF_LEN,
    "Econo": 32 | uctypes.BFUINT8 | 2 << uctypes.BF_POS | 1 << uctypes.BF_LEN,
    
    "Sum3": 34 | uctypes.UINT8
}

def compute_sum(frame):
    sum = 0
    for byte in frame:
        sum += byte
    
    return sum & 0x00ff

def update_sum(state_raw, state):
    offset = 0

    # Sum excludes the last byte of each frame, which contains the sum.
    frame1 = uctypes.bytearray_at(uctypes.addressof(state_raw), FRAME_1_SIZE - 1)
    state.Sum1 = compute_sum(frame1)

    offset += FRAME_1_SIZE
    frame2 = uctypes.bytearray_at(uctypes.addressof(state_raw) + offset, FRAME_2_SIZE - 1)
    state.Sum2 = compute_sum(frame2)
     
    offset += FRAME_2_SIZE
    frame3 = uctypes.bytearray_at(uctypes.addressof(state_raw) + offset, FRAME_3_SIZE - 1)
    state.Sum3 = compute_sum(frame3)

def get_frames(state_raw):
    offset = 0

    frame1 = uctypes.bytearray_at(uctypes.addressof(state_raw), FRAME_1_SIZE)

    offset += FRAME_1_SIZE
    frame2 = uctypes.bytearray_at(uctypes.addressof(state_raw) + offset, FRAME_2_SIZE)

    offset += FRAME_2_SIZE
    frame3 = uctypes.bytearray_at(uctypes.addressof(state_raw) + offset, FRAME_3_SIZE)

    return frame1, frame2, frame3