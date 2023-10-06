#!/usr/bin/python

import asyncio
import logging

from typing import *

import struct

import gui_debug
import gui_hw
import gui
import osc_state
import util
import views

class ArdourOscLogic():

    def __init__(self, logic):
        self.logic = logic
        self.ors = osc_state.OscRemoteState()
        self.ors.register_changed_callback(self._osc_callback)
        self._ors_server_task = None
        self.strip_view = views.StripView(self)

    def connect(self):
        self._ors_server_task = asyncio.create_task(self.ors.start_server())

    async def wait_for_completed(self):
        if self._ors_server_task is None:
            raise ValueError('Not connected')

        await self._ors_server_task

    def _osc_callback(self, event_type, *args):
        self.on_osc_event(event_type, *args)
        self.logic.redraw_trigger.trigger()
        self.logic.config_trigger.trigger()

    def on_osc_event(self, event_type, *args):
        return self.strip_view.on_osc_event(self, event_type, *args)

    def send_strip_command(self, strip, address, *args):
        """
        Send a command to a specific strip, handle the master strip as well.
        """
        if self._ors_server_task is None:
            raise ValueError('Not connected')

        if strip.ssid == 'master':
            self.ors.client.send_message('/master' + address, args)
        else:
            self.ors.client.send_message('/strip' + address, (strip.ssid, *args))

class Logic():

    def __init__(self):
        self.last_io_state = None

        self.keyzone_config = [util.KeyZoneConfig()] + [util.KeyZoneConfig(off=True) for _ in range(11)]
        self.keyzone_config_dirty = True
        self.brightness = 127
        self.brightness_dirty = True
        self.slider_config = [util.SliderConfig.pitch(), util.SliderConfig.mod(), util.SliderConfig.mod()]
        self.slider_config_dirty = True
        self.button_config = [util.ButtonConfig() for i in range(8)]
        self.knob_config = [util.KnobConfig() for i in range(8)]
        self.button_knob_config_dirty = True
        self.button_config[2].color = util.Colors.RED

        self.ardour_logic = None

    def init(self):

        self.global_view = views.GlobalView(self)
        self.view_list = [self.global_view]
        self.debug_gui = gui_debug.DebugWindow(self._window_close_callback, self._keystate_cb)
        self.device_gui = gui_hw.DeviceWindow(self._keystate_cb)
        # self.redraw_trigger = util.AsyncTrigger(.01, .1, lambda: self.draw())
        # self.config_trigger = util.AsyncTrigger(.01, .1, lambda: self._upload_options_callback())
        self.redraw_trigger = util.AsyncTrigger(.01, .02, lambda: self.draw())
        self.config_trigger = util.AsyncTrigger(.01, .02, lambda: self._upload_options_callback())

        self.redraw_trigger.trigger()
        self.config_trigger.trigger()

        self.exit_event = asyncio.Event()

    def run(self):
        gui_debug.init_for_asyncio()

        async def main_task():
            await self.exit_event.wait()

        async def asyncio_logic():
            self.init()

            done, pending = await asyncio.wait([
                    # asyncio.create_task(self.ors.start_server()),
                    asyncio.create_task(self.device_gui.run_input_loop()),
                    asyncio.create_task(main_task()),
                ], return_when=asyncio.FIRST_EXCEPTION)

            print((done, pending))

            # there are some tasks pending, meaning one of the tasks ended with an exception, quit completely
            if pending:
                logging.error('Some main task exited with an exception')
                for task in done:
                    exc = task.exception()
                    if exc is not None:
                        task.print_stack()
                logging.error('Stopping all tasks')
                self._window_close_callback()
                await asyncio.wait(pending)

        try:
            asyncio.run(asyncio_logic())

        except KeyboardInterrupt:
            # just raise again, let the application quit/crash
            raise

        # Gtk.main_quit()

    def ensure_ardour(self):
        if not self.ardour_logic:
            self.ardour_logic = ArdourOscLogic(self)
            self.ardour_logic.connect()

    def register_views(self, views):
        self.view_list.extend(views)
        for view in views:
            view.view_enter(self)
        self.redraw_trigger.trigger()
        self.config_trigger.trigger()

    def unregister_views(self, views):
        for view in views:
            try:
                self.view_list.remove(view)
            except ValueError:
                continue
            view.view_leave(self)
        self.redraw_trigger.trigger()
        self.config_trigger.trigger()

    def set_view(self, view):
        self.unregister_views(self.view_list[1:])
        self.register_views([view])

    def draw(self):
        for view in self.view_list[::-1]:
            if view.draw(self):
                return

    def upload_image(self, screen, x_pos, y_pos, ims):
        self.debug_gui.upload_image(screen, x_pos, y_pos, ims)
        self.device_gui.upload_image(screen, x_pos, y_pos, ims)

    def _window_close_callback(self, *args):
        # self.ors.transport.close()
        self.device_gui.stop_input_loop()
        self.exit_event.set()

    @staticmethod
    def _unpack_io_report(report):
        if report[0] == 0x01:
            try:
                unpacked = struct.unpack('B9s8H2HBB', report)
            except struct.error:
                raise ValueError(f'Error parsing 0x01 io_report: {report.hex(" ")}')
            res = int.from_bytes(unpacked[1][:8], 'big'), unpacked[2:10], unpacked[12], unpacked[13]
            return res

        else:
            raise ValueError(f'Unhandled io report: 0x{hex(report[0])}')

    def _keystate_cb(self, io_report):
        try:
            new_state = self._unpack_io_report(io_report)
        except ValueError as e:
            logging.warning(f'Invalid/unhandled io_report, {e}')
            return

        if self.last_io_state is None:
            old_mask = 0
        else:
            old_mask = self.last_io_state[0]
        # [0, [0]*8, 0, 0x24]
        mask = new_state[0]

        changed_mask = old_mask ^ mask

        for b in util.Buttons:
            if changed_mask & b.int_mask:
                if mask & b.int_mask:
                    self.button_pressed(b)
                else:
                    self.button_released(b)

        if self.last_io_state is not None:
            for i, k in enumerate([
                        util.Buttons.Knob_1,
                        util.Buttons.Knob_2,
                        util.Buttons.Knob_3,
                        util.Buttons.Knob_4,
                        util.Buttons.Knob_5,
                        util.Buttons.Knob_6,
                        util.Buttons.Knob_7,
                        util.Buttons.Knob_8,
                    ]):
                if self.last_io_state[1][i] != new_state[1][i]:
                    self.knob_turned(k, (new_state[1][i] - self.last_io_state[1][i] + 500) % 1000 - 500)

            if self.last_io_state[2] != new_state[2]:
                self.bigknob_turned((new_state[2] - self.last_io_state[2] + 8) % 16 - 8)

        self.last_io_state = new_state

    def get_current_button_state(self, button):
        if self.last_io_state is None:
            return False
        else:
            return bool(self.last_io_state[0] & button.int_mask)

    def get_touched_knobs(self):
        l = []
        for i, b in enumerate([
                    util.Buttons.Knob_1,
                    util.Buttons.Knob_2,
                    util.Buttons.Knob_3,
                    util.Buttons.Knob_4,
                    util.Buttons.Knob_5,
                    util.Buttons.Knob_6,
                    util.Buttons.Knob_7,
                    util.Buttons.Knob_8,
                ]):
            if self.get_current_button_state(b):
                l.append(i)
        return l

    def button_pressed(self, button):
        print(f'BP {button}')
        self.config_trigger.trigger() # for button backlights
        for view in self.view_list[::-1]:
            view.button_pressed(self, button)

    def knob_turned(self, button, delta):
        print(f'KT {button} {delta}')
        for view in self.view_list[::-1]:
            view.knob_turned(self, button, delta)

    def bigknob_turned(self, delta):
        print(f'BKT {delta}')
        for view in self.view_list[::-1]:
            view.bigknob_turned(self, delta)

    def button_released(self, button):
        self.config_trigger.trigger() # for button backlights
        for view in self.view_list[::-1]:
            view.button_released(self, button)

    def _upload_options_callback(self):
        self.device_gui.set_button_lighting(self.build_button_lighting())
        self.device_gui.general_options.set_config(self.build_general_config())
        self.device_gui.upload_options()

        # XXX
        if self.keyzone_config_dirty:
            self.keyzone_config_dirty = False
            self.device_gui.send_raw_command(util.KeyZoneConfig.build_full_hid_config(self.keyzone_config))
        if self.slider_config_dirty:
            self.slider_config_dirty = False
            self.device_gui.send_raw_command(util.SliderConfig.build_full_hid_config(*self.slider_config))
        if self.brightness_dirty:
            self.brightness_dirty = False
            self.device_gui.send_raw_command(bytes([0xf3, self.brightness]))
        if self.button_knob_config_dirty:
            self.button_knob_config_dirty = False
            self.device_gui.send_raw_command(util.ButtonConfig.build_full_hid_config(self.knob_config, self.button_config))
            print(util.ButtonConfig.build_full_hid_config(self.knob_config, self.button_config).hex())

    def build_button_lighting(self):
        res = {}
        for view in self.view_list:
            res.update(view.get_button_lighting())
        final_dict = {
                button: (color, (3 if self.get_current_button_state(button) else brightness) if active_state and brightness != 0 else brightness)
                for button, (color, brightness, active_state) in res.items()
            }
        return final_dict

    def build_general_config(self):
        res = {}
        for view in self.view_list:
            res.update(view.get_general_config())
        return res

    def set_global_config(self, cfg):
        self.device_gui.general_options.set_config(cfg)
        self.config_trigger.trigger()

    def set_global_option(self, option, value):
        self.device_gui.general_options.set_option(option, value)
        self.config_trigger.trigger()



# lost documentation:
# /strip/state  give type and other info

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logic = Logic()
    logic.run()
