from __future__ import annotations

import logging

from typing import *

if TYPE_CHECKING:
    import main

import gui
import util
import struct

import views


class SetupView(views.View):
    def __init__(self, logic):
        self.logic = logic
        self.highlight_index = 0
        self.options = ['Keyzones', 'Buttons', 'Knobs', 'Sliders', 'Brightness', 'Save Configuration', 'Load Configuration']
        self.ui_left = gui.MenuDrawer(['NI Ctl', 'Options'], self.options, self.highlight_index)
        self.ui_right = gui.CrossDrawer()

    def draw(self, logic):

        self.ui_left.draw()
        self.ui_right.draw()

        logic.upload_image(0, 0, 0, self.ui_left.ims)
        logic.upload_image(1, 0, 0, self.ui_right.ims)

        return True

    def set_highlight_relative(self, value):
        self.highlight_index = (self.highlight_index + value) % len(self.options)
        self.ui_left.set_highlight_index(self.highlight_index)

    def button_pressed(self, logic: main.Logic, button: util.Buttons) -> None:

        if button == util.Buttons.Bigknob_Up:
            self.set_highlight_relative(-1)
            self.logic.redraw_trigger.trigger()
        if button == util.Buttons.Bigknob_Down:
            self.set_highlight_relative(1)
            self.logic.redraw_trigger.trigger()

        if button == util.Buttons.Bigknob_Push:
            if self.highlight_index == 0:
                self.logic.register_views([KeyzoneConfigView(self.logic)])
            elif self.highlight_index == 3:
                self.logic.register_views([SliderConfigView(self.logic)])
            elif self.highlight_index == 4:
                self.logic.register_views([SetupBrightnessView(self.logic)])

    def bigknob_turned(self, logic: main.Logic, delta: int) -> None:
        self.set_highlight_relative(-delta)
        self.logic.redraw_trigger.trigger()

    def get_button_lighting(self):
        res = {
                util.Buttons.Bigknob_Up: (util.Colors.BLUE, 2, False),
                util.Buttons.Bigknob_Down: (util.Colors.BLUE, 2, False),
            }
        return res

class TabledSetupView(views.View):
    def __init__(self, logic):
        self.logic = logic
        self.highlight_index = (0, 0)
        self.load_values()

    def load_values(self):
        raise NotImplementedError()

    def value_changed(self):
        pass

    def _values_to_strings(self):
        return [
                [ str(value) if len(self.options[index])==3 else self.options[index][0][value] for index, value in enumerate(row) ]
                for row in self.values
            ]

    def draw(self, logic):

        # TODO more persistence?
        strings = self._values_to_strings()
        self.ui_left = gui.ConfigDrawer(
                self.title,
                self.headers[:4],
                [row[:4] for row in strings],
                self.highlight_index
            )
        self.ui_right = gui.ConfigDrawer(
                [],
                self.headers[4:],
                [row[4:] for row in strings],
                (self.highlight_index[0]-4, self.highlight_index[1])
            )

        self.ui_left.draw()
        self.ui_right.draw()

        logic.upload_image(0, 0, 0, self.ui_left.ims)
        logic.upload_image(1, 0, 0, self.ui_right.ims)

        return True

    def button_pressed(self, logic: main.Logic, button: util.Buttons) -> None:

        if button == util.Buttons.Bigknob_Up:
            self.highlight_index = (self.highlight_index[0], (self.highlight_index[1] - 1) % len(self.values))
            if self.highlight_index[0] >= len(self.values[self.highlight_index[1]]):
                self.highlight_index = (len(self.values[self.highlight_index[1]]) - 1, self.highlight_index[1])
            self.logic.redraw_trigger.trigger()
        if button == util.Buttons.Bigknob_Down:
            self.highlight_index = (self.highlight_index[0], (self.highlight_index[1] + 1) % len(self.values))
            if self.highlight_index[0] >= len(self.values[self.highlight_index[1]]):
                self.highlight_index = (len(self.values[self.highlight_index[1]]) - 1, self.highlight_index[1])
            self.logic.redraw_trigger.trigger()
        if button == util.Buttons.Bigknob_Left:
            self.highlight_index = ((self.highlight_index[0] - 1) % len(self.values[self.highlight_index[1]]), self.highlight_index[1])
            self.logic.redraw_trigger.trigger()
        if button == util.Buttons.Bigknob_Right:
            self.highlight_index = ((self.highlight_index[0] + 1) % len(self.values[self.highlight_index[1]]), self.highlight_index[1])
            self.logic.redraw_trigger.trigger()

        if button == util.Buttons.Prev_Page:
            self.logic.unregister_views([self])

    def bigknob_turned(self, logic: main.Logic, delta: int) -> None:
        opt = self.options[self.highlight_index[0]]
        val = self.values[self.highlight_index[1]][self.highlight_index[0]]

        if len(opt) == 3:
            minv, maxv, _ = opt
            new_val = val + delta
            if new_val < minv:
                new_val = minv
            if new_val > maxv:
                new_val = maxv

        else:
            lst = list(opt[0].keys())
            index = lst.index(val)
            index += delta
            if index < 0:
                index = 0
            if index >= len(lst):
                index = len(lst) - 1
            new_val = lst[index]

        self.values[self.highlight_index[1]][self.highlight_index[0]] = new_val

        self.value_changed()

    def get_button_lighting(self):
        res = {
                util.Buttons.Bigknob_Up: (util.Colors.BLUE, 2, False),
                util.Buttons.Bigknob_Left: (util.Colors.BLUE, 2, False),
                util.Buttons.Bigknob_Right: (util.Colors.BLUE, 2, False),
                util.Buttons.Bigknob_Down: (util.Colors.BLUE, 2, False),

                util.Buttons.Prev_Page: (util.Colors.WHITE, 1, False),
            }
        return res

class SetupBrightnessView(TabledSetupView):
    def __init__(self, logic):
        super().__init__(logic)
        self.title = ['NI Ctl', 'Options', 'Brightness']
        self.headers = ['Brightness']

        self.options = [
                (0, 127, 127),
            ]

    def load_values(self):
        self.values = [
                [
                    self.logic.brightness
                ]
            ]
    
    def value_changed(self):
        self.logic.brightness = self.values[0][0]
        self.logic.brightness_dirty = True

        self.logic.redraw_trigger.trigger()
        self.logic.config_trigger.trigger()

class KeyzoneConfigView(TabledSetupView):
    def __init__(self, logic):
        super().__init__(logic)
        self.title = ['NI Ctl', 'Options', 'Keyzones']
        self.headers = ['Last Key', 'MIDI Channel', 'Transpose', 'Velocity', 'Color 1', 'Brightness 1', 'Color 2', 'Brightness 2']

        self.options = [
                (0, 127, 127),
                (0, 15, 0),
                (-25, 25, 0),
                (dict([ (vm, vm.name) for vm in util.KeyZoneConfig.VelocityMode ] + [('OFF', 'OFF')]), util.KeyZoneConfig.VelocityMode.linear),
                (dict([ (c, c.name) for c in util.Colors ]), util.Colors.OFF),
                (0, 3, 0),
                (dict([ (c, c.name) for c in util.Colors ]), util.Colors.OFF),
                (0, 3, 0),
            ]

        # self.values = [
        #         [ t[2] if len(t) == 3 else t[1] for t in self.options ]
        #         for i in range(4)
        #     ]
        # self.values += [
        #         [ t[2] if len(t) == 3 else t[1] for t in self.options[:6] ]
        #         for i in range(2)
        #     ]
        # self.values += [
        #         [ t[2] if len(t) == 3 else t[1] for t in self.options ]
        #         for i in range(1)
        #     ]
        # self.values += [
        #         [ t[2] if len(t) == 3 else t[1] for t in self.options[:2] ]
        #         for i in range(1)
        #     ]
        # self.values += [
        #         [ t[2] if len(t) == 3 else t[1] for t in self.options ]
        #         for i in range(1)
        #     ]

    def load_values(self):
        self.values = [
                [
                    kz.last_key,
                    kz.midi_channel,
                    kz.transpose,
                    kz.velocity if not kz.off else 'OFF',
                    kz.color1[0],
                    kz.color1[1],
                    kz.color2[0],
                    kz.color2[1]
                ]
                for kz in self.logic.keyzone_config[:8]
            ]
    
    def value_changed(self):
        self.logic.keyzone_config[self.highlight_index[1]] = self.build_keyzone_config_from_values(self.values[self.highlight_index[1]])
        self.logic.keyzone_config_dirty = True

        self.logic.redraw_trigger.trigger()
        self.logic.config_trigger.trigger()

    @staticmethod
    def build_keyzone_config_from_values(values):
        return util.KeyZoneConfig(
                last_key     = values[0],
                midi_channel = values[1],
                transpose    = values[2],
                velocity     = values[3] if values[3] != 'OFF' else util.KeyZoneConfig.VelocityMode.linear,
                color1       = (values[4], values[5]),
                color2       = (values[6], values[7]),
                off          = values[3] == 'OFF',
            )

class SliderConfigView(TabledSetupView):
    def __init__(self, logic):
        super().__init__(logic)
        self.title = ['NI Ctl', 'Options', 'Sliders']
        self.headers = ['Mode', 'MIDI Channel', 'MIDI CC', 'Min Value', 'Max Value', 'Strip Mode', 'Retr/Glide Speed', 'Center Point']

        self.options = [
                (dict([ (vm, vm.name) for vm in util.SliderConfig.SliderMode ]), util.SliderConfig.SliderMode.OFF),
                (0, 15, 0),
                (0, 127, 127),
                (0, 127, 0),
                (0, 127, 127),
                (dict([ (sm, sm.name) for sm in util.SliderConfig.StripMode ]), util.SliderConfig.StripMode.DEFAULT),
                (0, 8, 8),
                (0, 4, 0),
            ]

    def load_values(self):
        self.values = [
                [
                    sc.mode,
                    sc.midi_channel,
                    sc.midi_cc,
                    sc.min_value,
                    sc.max_value,
                    # sc.strip_mode,
                    # sc.retraction_speed,
                    # sc.center_point,
                ]
                for sc in self.logic.slider_config[:2]
            ]
        sc = self.logic.slider_config[2]
        self.values.append([
                sc.mode,
                sc.midi_channel,
                sc.midi_cc,
                sc.min_value,
                sc.max_value,
                sc.strip_mode,
                sc.retraction_speed,
                sc.center_point,
            ])
    
    def value_changed(self):
        self.logic.slider_config = [
                util.SliderConfig(*row) for row in self.values
            ]
        self.logic.slider_config_dirty = True

        self.logic.redraw_trigger.trigger()
        self.logic.config_trigger.trigger()

    @staticmethod
    def build_slider_config_from_values(values):
        return util.SliderConfig(
                mode             = values[0],
                midi_channel     = values[1],
                midi_cc          = values[2],
                min_value        = values[3],
                max_value        = values[4],
                strip_mode       = values[5],
                retraction_speed = values[6],
                center_point     = values[7],
            )
