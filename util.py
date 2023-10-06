import asyncio
import enum
import struct
import time

# from https://stackoverflow.com/a/19300424
class Buttons(enum.Enum):

    # KeyName = (bytes_input_bitmap_mask, led_config_byte_index)

    def __new__(cls, *args, **kwds):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, input_mask, color_index):
        self.input_mask = input_mask
        self.int_mask = int.from_bytes(input_mask, 'big')
        self.color_index = color_index

    Fixed_Vel_TS_Mode = (b'\x00\x00\x00\x00\x00\x00\x00\x04', 41)
    Octave_Right =      (b'\x00\x00\x00\x00\x00\x00\x00\x02', 43)
    Octave_Left =       (b'\x00\x00\x00\x00\x00\x00\x00\x01', 42)
    Shift =             (b'\x00\x80\x00\x00\x00\x00\x00\x00', 14)
    Scale =             (b'\x00\x08\x00\x00\x00\x00\x00\x00', 15)
    Arp =               (b'\x00\x04\x00\x00\x00\x00\x00\x00', 16)
    Undo_Redo =         (b'\x00\x40\x00\x00\x00\x00\x00\x00', 18)
    Quantize =          (b'\x00\x02\x00\x00\x00\x00\x00\x00', 19)
    Auto =              (b'\x00\x01\x00\x00\x00\x00\x00\x00', 20)
    Loop =              (b'\x00\x20\x00\x00\x00\x00\x00\x00', 24)
    Metro =             (b'\x00\x00\x08\x00\x00\x00\x00\x00', 25)
    Tempo =             (b'\x00\x00\x04\x00\x00\x00\x00\x00', 26)
    Play =              (b'\x00\x10\x00\x00\x00\x00\x00\x00', 29)
    Record =            (b'\x00\x00\x02\x00\x00\x00\x00\x00', 30)
    Stop =              (b'\x00\x00\x01\x00\x00\x00\x00\x00', 31)
    Mute =              (b'\x00\x00\x00\x01\x00\x00\x00\x00', 0)
    Solo =              (b'\x00\x00\x00\x02\x00\x00\x00\x00', 1)
    Preset_Up =         (b'\x00\x00\x10\x00\x00\x00\x00\x00', 22)
    Preset_Down =       (b'\x00\x00\x40\x00\x00\x00\x00\x00', 27)
    Prev_Page =         (b'\x00\x00\x80\x00\x00\x00\x00\x00', 32)
    Next_Page =         (b'\x00\x00\x20\x00\x00\x00\x00\x00', 33)
    Scene =             (b'\x00\x00\x00\x04\x00\x00\x00\x00', 17)
    Pattern =           (b'\x00\x00\x00\x08\x00\x00\x00\x00', 21)
    Track =             (b'\x00\x00\x00\x10\x00\x00\x00\x00', 23)
    Key_Mode =          (b'\x00\x00\x00\x40\x00\x00\x00\x00', 28)
    Clear =             (b'\x00\x00\x00\x20\x00\x00\x00\x00', 34)

    Knob_1 =            (b'\x00\x00\x00\x00\x00\x00\x80\x00', None)
    Knob_2 =            (b'\x00\x00\x00\x00\x00\x00\x40\x00', None)
    Knob_3 =            (b'\x00\x00\x00\x00\x00\x00\x20\x00', None)
    Knob_4 =            (b'\x00\x00\x00\x00\x00\x00\x10\x00', None)
    Knob_5 =            (b'\x00\x00\x00\x00\x00\x00\x08\x00', None)
    Knob_6 =            (b'\x00\x00\x00\x00\x00\x00\x04\x00', None)
    Knob_7 =            (b'\x00\x00\x00\x00\x00\x00\x02\x00', None)
    Knob_8 =            (b'\x00\x00\x00\x00\x00\x00\x01\x00', None)

    Button_1 =          (b'\x10\x00\x00\x00\x00\x00\x00\x00', 2)
    Button_2 =          (b'\x20\x00\x00\x00\x00\x00\x00\x00', 3)
    Button_3 =          (b'\x40\x00\x00\x00\x00\x00\x00\x00', 4)
    Button_4 =          (b'\x80\x00\x00\x00\x00\x00\x00\x00', 5)
    Button_5 =          (b'\x01\x00\x00\x00\x00\x00\x00\x00', 6)
    Button_6 =          (b'\x02\x00\x00\x00\x00\x00\x00\x00', 7)
    Button_7 =          (b'\x04\x00\x00\x00\x00\x00\x00\x00', 8)
    Button_8 =          (b'\x08\x00\x00\x00\x00\x00\x00\x00', 9)

    Browser =           (b'\x00\x00\x00\x00\x04\x00\x00\x00', 35)
    Plugin =            (b'\x00\x00\x00\x00\x02\x00\x00\x00', 36)
    Mixer =             (b'\x00\x00\x00\x00\x01\x00\x00\x00', 37)
    Instance =          (b'\x00\x00\x00\x00\x10\x00\x00\x00', 38)
    Midi =              (b'\x00\x00\x00\x00\x20\x00\x00\x00', 39)
    Setup =             (b'\x00\x00\x00\x00\x08\x00\x00\x00', 40)

    Bigknob_Touch =     (b'\x00\x00\x00\x00\x00\x04\x00\x00', None)
    Bigknob_Push =      (b'\x00\x00\x00\x00\x00\x08\x00\x00', None)

    Bigknob_Up =        (b'\x00\x00\x00\x00\x00\x20\x00\x00', 11)
    Bigknob_Left =      (b'\x00\x00\x00\x00\x00\x10\x00\x00', 10)
    Bigknob_Right =     (b'\x00\x00\x00\x00\x00\x80\x00\x00', 13)
    Bigknob_Down =      (b'\x00\x00\x00\x00\x00\x40\x00\x00', 12)

    # then another 25 LEDs for the touch strip

    def get_knob_index(self):
        return {
                Buttons.Knob_1: 0,
                Buttons.Knob_2: 1,
                Buttons.Knob_3: 2,
                Buttons.Knob_4: 3,
                Buttons.Knob_5: 4,
                Buttons.Knob_6: 5,
                Buttons.Knob_7: 6,
                Buttons.Knob_8: 7,
            }.get(self, None)

    def get_button_index(self):
        return {
                Buttons.Button_1: 0,
                Buttons.Button_2: 1,
                Buttons.Button_3: 2,
                Buttons.Button_4: 3,
                Buttons.Button_5: 4,
                Buttons.Button_6: 5,
                Buttons.Button_7: 6,
                Buttons.Button_8: 7,
            }.get(self, None)

class Colors(enum.Enum):

    def with_brightness(self, brightness):
        assert brightness in [0, 1, 2, 3]
        return self.value << 2 | brightness

    @staticmethod
    def from_byte(b):
        if (b & 0x7f) != b:
            raise ValueError('Color byte value out of range')
        color_part = b >> 2
        brightness = b & 0x03
        if color_part >= Colors.WHITE.value:
            color_part = Colors.WHITE.value
        return Colors(color_part), brightness

    OFF            =  0
    RED            =  1
    ORANGE_RED     =  2
    ORANGE         =  3
    YELLOW_ORANGE  =  4
    YELLOW         =  5
    YELLOW_GREEN   =  6
    GREEN          =  7
    TURQUOISE      =  8
    CYAN           =  9
    GREENISH_BLUE  = 10
    BLUE           = 11
    BLUE_PURPLE    = 12
    PURPLE         = 13
    MAGENTA        = 14
    MAGENTA_RED    = 15
    MAGENTA_REDDER = 16
    WHITE          = 17

    BLACK = OFF

class KeyZoneConfig():
    VelocityMode = enum.Enum('VelocityMode', {
            'soft_3': bytes([0x30]),
            'soft_2': bytes([0x31]),
            'soft_1': bytes([0x32]),
            'linear': bytes([0x33]),
            'hard_1': bytes([0x34]),
            'hard_2': bytes([0x35]),
            'hard_3': bytes([0x36]),
            # other values that appear - what do they do?
            #0x09, 0x62, 0x17, 0xef
        })

    def __init__(self, last_key=127, midi_channel=0, transpose=0, velocity=VelocityMode.linear, color1=(Colors.BLUE, 0), color2=(Colors.BLUE, 2), off=False):
        '''
        last_key:
        midi_channel: 0..15
        transpose: -25..25
        '''
        self.last_key     = last_key
        self.midi_channel = midi_channel
        self.transpose    = transpose
        self.velocity     = velocity
        self.color1       = color1
        self.color2       = color2
        self.off          = off

    def convert_to_hid_config(self):
        return bytes([
                self.last_key,
                self.transpose, # FIXME negative values give error, should they just be encoded as sgined int8?
                self.midi_channel,
                0x83 if self.off else self.velocity.value[0],
                self.color1[0].with_brightness(self.color1[1]),
                self.color2[0].with_brightness(self.color2[1]),
                0x00, 0x00
            ])

    @staticmethod
    def build_full_hid_config(keyzones):
        keyzones = list(keyzones)
        if len(keyzones) > 16:
            keyzones = keyzones[:16]
        elif len(keyzones) < 16:
            keyzones.extend([KeyZoneConfig() for i in range(16-len(keyzones))])

        res = bytes([0xa4])
        res += b''.join(keyzone.convert_to_hid_config() for keyzone in keyzones)
        return res

class SliderConfig():
    SliderMode = enum.Enum('SliderMode', 'OFF MOD PITCH')
    StripMode = enum.Enum('StripMode', 'DEFAULT RETRACT GLIDE DISCRETE')

    def __init__(self, mode, midi_cc=1, midi_channel=0, min_value=0, max_value=127, strip_mode=StripMode.DEFAULT, retraction_speed=8, center_point=0): # the last two are for touch strip only
        '''
        midi_cc:          1..127
        midi_channel:     0..15
        min_value:        0..127
        max_value:        0..127
        retraction_speed: 0..8
        center_point:     0..4
        '''
        self.mode             = mode
        self.midi_cc          = midi_cc
        self.midi_channel     = midi_channel
        self.min_value        = min_value
        self.max_value        = max_value
        self.strip_mode       = strip_mode
        self.retraction_speed = retraction_speed
        self.center_point     = center_point

    @staticmethod
    def off():
        return SliderConfig(SliderConfig.SliderMode.OFF)

    @staticmethod
    def mod(midi_cc=0, midi_channel=0, min_value=0, max_value=127, strip_mode=StripMode.DEFAULT, retraction_speed=8, center_point=0): # the last two may not be available in this mode?
        return SliderConfig(SliderConfig.SliderMode.MOD, midi_cc, midi_channel, min_value, max_value, strip_mode, retraction_speed, center_point)

    @staticmethod
    def pitch(retraction_speed=8, center_point=2):
        return SliderConfig(SliderConfig.SliderMode.PITCH, strip_mode=SliderConfig.StripMode.RETRACT, retraction_speed=retraction_speed, center_point=center_point)

    def convert_to_hid_config(self, touch_strip=False):
        if self.mode == SliderConfig.SliderMode.OFF:
            res = bytes(12)
        elif self.mode == SliderConfig.SliderMode.MOD: # min and max values should be 0..127 (otherwise the sent value is just the trimmed lower part)
            res = struct.pack('<BBBBHH4s',
                    0x03,
                    self.midi_channel,
                    self.midi_cc,
                    0x20,
                    self.min_value,
                    self.max_value,
                    bytes(4),
                )
        elif self.mode == SliderConfig.SliderMode.PITCH:
            self.midi_cc = 0
            self.midi_channel = 0
            self.min_value = 0
            self.max_value = 0x3fff
            # min and max values from 0 to 0x3fff map to midi value range 0..0x7f7f (7bit midi values blabla)
            res = struct.pack('<BBBBHH4s',
                    0x06,
                    self.midi_channel,
                    self.midi_cc,
                    0x00,
                    self.min_value,
                    self.max_value,
                    bytes.fromhex('00000100'),
                )

        if touch_strip:
            # res = bytes([0x03, self.midi_cc, self.midi_channel]) + bytes.fromhex('200000ff3f00000100')
            # res = bytes([0x06, 20, 10]) + bytes.fromhex('204000ff3f00000100')
            # res = bytes([0x06, 0x00, self.midi_channel]) + bytes.fromhex('000000ff3f0000a100') XXX snap to grid?
            # res = bytes([0x06, 0x00, self.midi_channel]) + bytes.fromhex('000000ff3f000001a0') also does things
            # res = bytes([0x03, 0x00, self.midi_channel]) + bytes.fromhex('000000ff3f00001102') discrete steps?
            # res = bytes([0x03, 0x00, self.midi_channel]) + bytes.fromhex('000000ff3f00000200') glide?
            # res = bytes([0x06, 0x00, self.midi_channel]) + bytes.fromhex('000000ff3f00000100')
            if self.mode != SliderConfig.SliderMode.OFF:
                res += bytes([self.retraction_speed, 0x00, 0x00, self.center_point])
                # res += bytes([4, 0x00, 0x00, 2]) # third byte does something to center point
            else:
                res += bytes(4)

        return res

    @staticmethod
    def build_full_hid_config(pitch_wheel_config, mod_wheel_config, touchstrip_config):
        res = bytes([0xa2])
        res += pitch_wheel_config.convert_to_hid_config(False)
        res += mod_wheel_config.convert_to_hid_config(False)
        res += touchstrip_config.convert_to_hid_config(True)
        res += bytes(4)
        return res

class KnobConfig():
    KnobMode = enum.Enum('KnobMode', {
            'OFF': 0x00,
            'PRG': 0x04,
            'CC': 0x03,
            # qkontrol uses 0x08 for turning the buttons/knobs off in plugin mode?
        })

    def __init__(self, midi_cc=0, midi_channel=0, mode=KnobMode.CC):
        self.midi_cc = midi_cc
        self.midi_channel = midi_channel
        self.mode = mode
        self.min_value = 0
        self.max_value = 0x7f

    def convert_to_hid_config(self):
        return struct.pack('<BBBBHH4s',
                    self.mode.value,
                    self.midi_cc,
                    self.midi_channel,
                    0x3c, # XXX 0x7f does some digital thing
                    self.min_value,
                    self.max_value,
                    bytes.fromhex('00000000'),
                )

class ButtonConfig():
    class ButtonMode(enum.Enum):
        OFF = enum.auto()
        TOGGLE = enum.auto()
        TRIGGER = enum.auto()
        GATE = enum.auto()
        PRG = enum.auto()

        def config_byte_1(self):
            if self == ButtonConfig.ButtonMode.OFF: return bytes([0x00])
            if self == ButtonConfig.ButtonMode.PRG: return bytes([0x04])
            return bytes([0x03])
            # qkontrol uses 0x08 for turning the buttons/knobs off in plugin mode?
            # sends sysex message?

        def config_byte_2(self):
            if self == ButtonConfig.ButtonMode.TOGGLE: return bytes([0x3c])
            if self == ButtonConfig.ButtonMode.GATE: return bytes([0x3e])
            return bytes([0x3d])

    def __init__(self, midi_cc=0, midi_channel=0, mode=ButtonMode.TOGGLE, color=Colors.WHITE):
        self.midi_cc = midi_cc
        self.midi_channel = midi_channel
        self.mode = mode
        self.color = color
        self.min_value = 0
        self.max_value = 0x7f

    def convert_to_hid_config(self):
        return struct.pack('<BBBBHH4s',
                    self.mode.config_byte_1()[0],
                    self.midi_cc,
                    self.midi_channel,
                    self.mode.config_byte_2()[0],
                    self.min_value,
                    self.max_value, # value also used for trigger and prg change
                    bytes.fromhex('00000000'),
                )

    @staticmethod
    def build_full_hid_config(knobs, buttons):
        knobs = list(knobs)
        if len(knobs) > 8:
            knobs = knobs[:8]
        elif len(knobs) < 8:
            knobs.extend([KnobConfig() for i in range(8-len(knobs))])

        buttons = list(buttons)
        if len(buttons) > 8:
            buttons = buttons[:8]
        elif len(buttons) < 8:
            buttons.extend([ButtonConfig() for i in range(8-len(buttons))])

        res = bytes([0xa1])
        res += b''.join(button.convert_to_hid_config() for button in buttons)
        res += b''.join(knob.convert_to_hid_config() for knob in knobs)
        res += b''.join(bytes([button.color.value]) for button in buttons)
        res += bytes(3)  # usb descriptor says these bytes are: uint16_t 0..65534, uint8_t
        return res

class GeneralOptions(enum.Flag):

    NONE = 0x0000
    TOUCH_STRIP_ON = 0x1000
    KEY_COLOR_RESPONSE = 0x8000
    OCTAVE_SHIFT_KEYS_COLOR_RESPONSE = 0x0004
    DISPLAY_BUTTONS_COLOR_RESPONSE = 0x0100
    KNOBS_USB_HID_INPUT_DISABLE = 0x0200
    WHEELS_USB_HID_INPUT_ENABLE = 0x0008

    def to_command(self):
        return b'\xa0' + self.value.to_bytes(2, 'big')


class AsyncTrigger():
    def __init__(self, min_timeout, max_timeout, cb):
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.cb = cb

        self._triggered = None
        self._running_task = None

    def trigger(self):
        if self._running_task is None:
            self._start_task()
        else:
            self._triggered = True

    def _start_task(self):
        self._running_task = asyncio.create_task(self._task())

    def _finish(self):
        self._running_task = None
        import logging
        logging.debug(f'trigger finished {time.time() % 5}')
        self.cb()

    async def _task(self):
        start_time = time.time()

        while True:
            await asyncio.sleep(self.min_timeout)
            if not self._triggered:
                self._finish()
                return
            elif time.time() - start_time > self.max_timeout:
                self._finish()
                return
            else:
                self._triggered = False
