import asyncio
import threading
import struct
import usb.core
import usb.util
import util

class DeviceWindow():

    def __init__(self, keystate_callback=None):

        self.general_options = GeneralOptionsManager()
        self.last_button_lighting = None
        self.button_lighting = b'\x80' + b'\x00' * 69
        self.touchstrip_lighting = b'\x00' * 25

        dev = usb.core.find(idVendor=0x17cc, idProduct=0x1620)

        if dev is None:
            # raise ValueError('Device not found')
            self._ep = None
            self._it = None
            return

        cfg = dev.get_active_configuration()
        intf = cfg[(3,0)] # interface index, alternate setting

        self._ep = intf[0]

        # self._it = InputThread(keystate_callback)
        # self._it.start()
        self._it = DeviceInput(keystate_callback)

    async def run_input_loop(self):
        if self._it:
            await self._it.run()

    def stop_input_loop(self):
        if self._it:
            self._it.stop()

    def upload_image(self, screen, x_pos, y_pos, ims):
        assert x_pos == 0
        assert y_pos == 0
        data = self._draw_image_data(screen, x_pos, y_pos, 480, 272, ims.get_data())
        self._send_image_data(data)

    def upload_options(self):
        if self._it:
            self.general_options.upload_options(self._it)
            self.upload_button_lighting()

    # XXX
    def send_raw_command(self, cmd):
        if self._it:
            self._it.write(cmd)

    def set_button_lighting(self, data):
        l = [0] * (69 - 25)

        for button, (color, brightness) in data.items():
            index = button.color_index
            if index is not None:
                l[index] = color.with_brightness(brightness)

        self.button_lighting = b'\x80' + bytes(l) + self.touchstrip_lighting

    def set_touchstrip_lighting(self, data):
        self.touchstrip_lighting = data
        self.button_lighting = self.button_lighting[:1+69-25] + data

    def upload_button_lighting(self):
        if self.last_button_lighting != self.button_lighting:
            self.last_button_lighting = self.button_lighting
            res = self._it.write(self.button_lighting)

    def upload_key_lighting(self, data):
        self.send_raw_command(b'\x81' + data)


    @staticmethod
    def _draw_image_data(screen, x_pos, y_pos, width, height, image_data):
        '''
        screen:  screen index  0..1
        x_pos: uint16_t
        y_pos: uint16_t
        width: uint16_t
        height: uint16_t
        image_data: RGB16 (5-6-5) data array
        '''
        res = bytes.fromhex('8400')
        res += bytes([screen])
        res += bytes.fromhex('6000000000')
        res += struct.pack('>4H', x_pos, y_pos, width, height)
        res += bytes.fromhex('020000000000')
        res += struct.pack('>H', width * height // 2)
        # for pixel in image_data:
        #     res += struct.pack('>H', pixel)
        # reverse pixel byte order, the fastest way I found
        pixel_count = width*height
        res += struct.pack(f'>{pixel_count}H', *struct.unpack(f'<{pixel_count}H', image_data))
        res += bytes.fromhex('020000000300000040000000')
        return res

    def _send_image_data(self, data):
        if self._ep:
            self._ep.write(data)

class InputThread(threading.Thread):
    def __init__(self, cb, *args, daemon=True, **kwargs):
        super().__init__(*args, daemon=daemon, **kwargs)
        self._cb = cb
        import hid
        self._hd = hid.device()
        self._hd.open(0x17cc, 0x1620)

    def run(self):
        while True:
            res = self._hd.read(3000)
            res = bytes(res)
            if self._cb:
                self._cb(res)
            # if self._cb and res[0] == 0x01:
            #     self._cb(res[1:])

class DeviceInput():
    def __init__(self, cb):
        self._cb = cb
        import hid
        self._hd = hid.device()
        self._hd.open(0x17cc, 0x1620)

    def _wait(self):
        res = self._hd.read(3000, 100)
        res = bytes(res)
        return res

    async def run(self):
        self.task = asyncio.create_task(self.runner())
        await self.task

    async def runner(self):
        loop = asyncio.get_running_loop()
        while True:
            res = await loop.run_in_executor(None, self._wait)
            if not res:
                continue
            if self._cb:
                self._cb(res)

    def stop(self):
        self.task.cancel()

    def write(self, data):
        return self._hd.write(data)

class GeneralOptionsManager():
    def __init__(self):
        self.config = self.get_default_config()
        self.last_usb_command = None

    @staticmethod
    def get_default_config():
        return {
                util.GeneralOptions.DISPLAY_BUTTONS_COLOR_RESPONSE: True,
                util.GeneralOptions.KEY_COLOR_RESPONSE: True,
                util.GeneralOptions.KNOBS_USB_HID_INPUT_DISABLE: True,
                util.GeneralOptions.OCTAVE_SHIFT_KEYS_COLOR_RESPONSE: False,
                util.GeneralOptions.TOUCH_STRIP_ON: True,
            }

    def set_config(self, cfg):
        self.config.update(cfg)

    def set_option(self, option, value):
        self.config[option] = value

    def construct_usb_command(self):
        res = util.GeneralOptions.NONE

        for k, v in self.config.items():
            if v:
                res |= k

        return res.to_command()

    def upload_options(self, usb_ep, force=False):
        cmd = self.construct_usb_command()
        if cmd != self.last_usb_command or force:
            self.last_usb_command = cmd
            usb_ep.write(cmd)
