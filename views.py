from __future__ import annotations

import logging

from typing import *

if TYPE_CHECKING:
    import main

import gui
import gui_hw
import osc_state
import util


class View():

    def draw(self, logic: main.Logic) -> bool:
        return False

    def view_enter(self, logic: main.Logic):
        pass

    def view_leave(self, logic: main.Logic):
        pass

    def button_pressed(self, logic: main.Logic, button: util.Buttons) -> None:
        pass

    def knob_turned(self, logic: main.Logic, button: util.Buttons, delta: int) -> None:
        pass

    def bigknob_turned(self, logic: main.Logic, delta: int) -> None:
        pass

    def button_released(self, logic: main.Logic, button: util.Buttons) -> None:
        pass

    def get_button_lighting(self) -> Mapping[util.Buttons, Tuple[util.Colors, int, bool]]:
        return {}

    def get_general_config(self) -> Mapping[util.GeneralOptions, bool]:
        return {}

class GlobalView(View):
    def __init__(self, logic):
        self.logic = logic
        self.cross_drawer = gui.CrossDrawer()

    def draw(self, logic):

        self.cross_drawer.draw()

        logic.upload_image(0, 0, 0, self.cross_drawer.ims)
        logic.upload_image(1, 0, 0, self.cross_drawer.ims)

        return True

    def button_pressed(self, logic: main.Logic, button: util.Buttons) -> None:

        if button == util.Buttons.Setup:
            import views_setup
            logic.set_view(views_setup.SetupView(logic))

        if button == util.Buttons.Midi:
            logic.ensure_ardour()
            logic.set_view(logic.ardour_logic.strip_view)

        if button == util.Buttons.Scene:
            import knightrider
            for view in logic.view_list:
                if isinstance(view, knightrider.KnightRiderView):
                    return
            logic.set_view(knightrider.KnightRiderView(logic))

    def get_button_lighting(self):
        res = {
                util.Buttons.Setup: (util.Colors.WHITE, 2, False),
                util.Buttons.Midi: (util.Colors.WHITE, 2, False),
            }
        return res

    def get_general_config(self) -> Mapping[util.GeneralOptions, bool]:
        return gui_hw.GeneralOptionsManager.get_default_config()


class StripView(View):
    def __init__(self, ardour_logic):
        self.ardour_logic = ardour_logic
        self.logic = ardour_logic.logic

        self.ui_left = gui.StripBankDrawer(ardour_logic.ors)
        self.ui_right = gui.StripBankDrawer(ardour_logic.ors)

        self.strips = []
        self.highlight_index = None
        self.page_index = 0

    def draw(self, logic):
        self.ui_left.draw()
        self.ui_right.draw()
        logic.upload_image(0, 0, 0, self.ui_left.ims)
        logic.upload_image(1, 0, 0, self.ui_right.ims)
        return True

    def _update_highlight_for_new_list(self, new_list):

        if len(new_list) > 0:
            if self.highlight_index is not None:
                name = self.strips[self.highlight_index].strip_state.get('name', None)

                if self.highlight_index in new_list and new_list[self.highlight_index].get('name', None) == name:
                    pass

                else:
                    for i, strip in enumerate(new_list):
                        print(f'trying name {strip.strip_state.get("name", None)!r}')
                        if strip.strip_state.get('name', None) == name:
                            self.highlight_index = i
                            break
                    else:
                        print(f'name not found {name!r}')
                        self.highlight_index = None

            if self.highlight_index is None:
                for i, strip in enumerate(new_list):
                    if strip.strip_state.get('selected', False):
                        self.highlight_index = i
                        print('fallback selected')
                else:
                    self.highlight_index = 0

        else:
            self.highlight_index = None

        if self.highlight_index is not None:
            new_list[self.highlight_index].set_highlight(True)

    def _set_highlight_relative(self, v):
        if self.highlight_index is None:
            new_index = self.page_index * 8
        else:
            new_index = self.highlight_index + v
        return self._set_highlight(new_index)

    def _set_highlight(self, new_index):
        if new_index < 0 or new_index >= len(self.strips):
            return False

        if self.highlight_index is not None:
            self.strips[self.highlight_index].set_highlight(False)
        self.strips[new_index].set_highlight(True)
        self.highlight_index = new_index
        new_page_index = new_index // 8
        if new_page_index != self.page_index:
            self.page_index = new_page_index
            self.ui_left.set_strip_list(self.strips[new_page_index*8:new_page_index*8+4])
            self.ui_right.set_strip_list(self.strips[new_page_index*8+4:new_page_index*8+8])
        return True

    def on_osc_event(self, ardour_logic, event_type, *args):

        if event_type == osc_state.OscEventType.GENERAL_DATA:
            pass

        elif event_type == osc_state.OscEventType.STRIP_LIST:
            new_list = [gui.StripDrawer(strip) for strip in ardour_logic.ors.get_drawable_strips()]
            self._update_highlight_for_new_list(new_list)
            self.strips = new_list
            logging.debug(f'new strips {self.strips}')
            self.page_index = self.highlight_index // 8 if self.highlight_index is not None else 0
            self.ui_left.set_strip_list(self.strips[self.page_index*8:self.page_index*8+4])
            self.ui_right.set_strip_list(self.strips[self.page_index*8+4:self.page_index*8+8])
            for strip in self.strips:
                strip.update()

        elif event_type == osc_state.OscEventType.STRIP_DATA:
            ssid, = args
            for strip in self.strips:
                if strip.strip_state.ssid == ssid:
                    strip.update()

        self.logic.redraw_trigger.trigger() # XXX
        self.logic.config_trigger.trigger()

    def button_pressed(self, logic, button):
        if button == util.Buttons.Mute:
            tlist = logic.get_touched_knobs()
            if not tlist:
                slist = [self.strips[self.highlight_index]] if self.highlight_index is not None else []
            else:
                slist = [self.strips[self.page_index*8 + i] for i in tlist if self.page_index*8 + i <= len(self.strips)]

            for s in slist:
                logic.send_strip_command(s.strip_state, '/mute', 0 if s.strip_state.get('muted', False) else 1)

        if button == util.Buttons.Solo:
            tlist = logic.get_touched_knobs()
            if not tlist:
                slist = [self.strips[self.highlight_index]] if self.highlight_index is not None else []
            else:
                slist = [self.strips[self.page_index*8 + i] for i in tlist if self.page_index*8 + i <= len(self.strips)]

            for s in slist:
                logic.send_strip_command(s.strip_state, '/solo', 0 if s.strip_state.get('soloed', False) else 1)

        if button == util.Buttons.Bigknob_Left:
            self._set_highlight_relative(-1)
            logic.redraw_trigger.trigger()
            logic.config_trigger.trigger()

        if button == util.Buttons.Bigknob_Right:
            self._set_highlight_relative(+1)
            logic.redraw_trigger.trigger()
            logic.config_trigger.trigger()

        if button == util.Buttons.Bigknob_Push:
            if self.highlight_index is not None:
                strip = self.strips[self.highlight_index]
                logic.send_strip_command(strip.strip_state, '/selected', 1)

        if (index := button.get_button_index()) is not None:
            new_highlight = self.page_index * 8 + index
            if self._set_highlight(new_highlight):
                logic.redraw_trigger.trigger()
                logic.config_trigger.trigger()

        if button == util.Buttons.Next_Page:
            new_highlight = (self.page_index + 1) * 8
            if self._set_highlight(new_highlight):
                self.strips[self.highlight_index].set_highlight(False)
                self.highlight_index = None
                logic.redraw_trigger.trigger()
                logic.config_trigger.trigger()

        if button == util.Buttons.Prev_Page:
            new_highlight = (self.page_index - 1) * 8
            if self._set_highlight(new_highlight):
                self.strips[self.highlight_index].set_highlight(False)
                self.highlight_index = None
                logic.redraw_trigger.trigger()
                logic.config_trigger.trigger()

        # from gui_debug import Gdk
        # if changed and keyval == Gdk.KEY_m and state_dict[keyval]:
        #     self.ors.client.send_message('/master/mute', 0 if self.ors.strips['master'].get('muted', False) else 1)
        # if changed and keyval == Gdk.KEY_s and state_dict[keyval]:
        #     self.ors.client.send_message('/strip/solo', (1, 0 if self.ors.strips[1].get('soloed', False) else 1))
        # if keyval == Gdk.KEY_Up and state_dict[keyval]:
        #     self.ors.client.send_message('/strip/fader', (1, self.ors.strips[1].get('fader', 0) + .01))
        # if keyval == Gdk.KEY_Down and state_dict[keyval]:
        #     self.ors.client.send_message('/strip/fader', (1, self.ors.strips[1].get('fader', 0) - .01))
        # if keyval == Gdk.KEY_Left and state_dict[keyval]:
        #     self.ors.client.send_message('/strip/pan_stereo_position', (1, self.ors.strips[1].get('pan_position', 0) + .01))
        # if keyval == Gdk.KEY_Right and state_dict[keyval]:
        #     self.ors.client.send_message('/strip/pan_stereo_position', (1, self.ors.strips[1].get('pan_position', 0) - .01))

        self.logic.redraw_trigger.trigger() # XXX
        self.logic.config_trigger.trigger()

    def knob_turned(self, logic, button, delta):
        index = self.page_index*8 + button.get_knob_index()
        if index >= len(self.strips):
            return

        strip = self.strips[index]
        fader_value = strip.strip_state.get('fader', 0)
        if logic.get_current_button_state(util.Buttons.Shift):
            new_value = fader_value + delta * .0002
        else:
            new_value = fader_value + delta * .002

        self.ardour_logic.send_strip_command(strip.strip_state, '/fader', new_value)

        self.logic.redraw_trigger.trigger() # XXX
        self.logic.config_trigger.trigger()

    def get_button_lighting(self):
        res = {
                util.Buttons.Prev_Page: (util.Colors.WHITE, 1, False) if self.page_index is not None and self.page_index > 0 else (util.Colors.OFF, 0, False),
                util.Buttons.Next_Page: (util.Colors.WHITE, 1, False) if self.page_index is not None and self.page_index < len(self.strips) // 8 else (util.Colors.OFF, 0, False),

                util.Buttons.Bigknob_Left: (util.Colors.BLUE, 1, False) if self.highlight_index is not None and self.highlight_index > 0 else (util.Colors.OFF, 0, False),
                util.Buttons.Bigknob_Right: (util.Colors.BLUE, 1, False) if self.highlight_index is not None and self.highlight_index < len(self.strips) - 1 else (util.Colors.OFF, 0, False),

                util.Buttons.Shift: (util.Colors.WHITE, 1, True)
            }

        if not self.highlight_index:
            res[util.Buttons.Mute] = (util.Colors.CYAN, 0, False)
            res[util.Buttons.Solo] = (util.Colors.YELLOW_ORANGE, 0, False)
        else:
            strip = self.strips[self.highlight_index]
            res[util.Buttons.Mute] = (util.Colors.CYAN, 2 if strip.strip_state.get('muted', False) else 1, True)
            res[util.Buttons.Solo] = (util.Colors.YELLOW_ORANGE, 2 if strip.strip_state.get('soloed', False) else 1, True)

        return res
