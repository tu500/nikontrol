import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
import cairo

import operator
import functools
import struct

import util

class DebugWindow(Gtk.Window):

    def __init__(self, window_close_callback=None, keystate_callback=None):
        super().__init__()
        self.left_ims = cairo.ImageSurface(cairo.Format.RGB16_565, 480, 272)
        self.right_ims = cairo.ImageSurface(cairo.Format.RGB16_565, 480, 272)
        self.window_close_callback = window_close_callback
        self.keystate_callback = keystate_callback
        self.init_ui()

    def init_ui(self):

        self.drawingarea = Gtk.DrawingArea()
        self.drawingarea.connect("draw", self.on_draw)
        self.add(self.drawingarea)
        #self.drawingarea.set_size_request(400, 150)

        self.set_title("Debug Window")
        #self.resize(350, 250)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.connect("delete-event", self.window_close_callback or Gtk.main_quit)
        if self.keystate_callback:
            self.connect("key-press-event",self.on_key_press_event)
            self.connect("key-release-event",self.on_key_release_event)
            self.key_states = {}
            self.knob_values = [0]*8
            self.bigknob_value = 0
        self.show_all()

    def on_draw(self, wid, ctx):
        self.drawingarea.set_size_request(480 + 20 + 480, 272)

        ctx.set_source_rgb(0.5, 0.5, 0.5)
        ctx.rectangle(480, 0, 20, 272)
        ctx.fill()

        ctx.set_source_surface(self.left_ims, 0, 0)
        ctx.paint()

        ctx.set_source_surface(self.right_ims, 480 + 20, 0)
        ctx.paint()

    def upload_image(self, screen, x_pos, y_pos, ims):
        if screen == 0:
            ctx = cairo.Context(self.left_ims)
        else:
            ctx = cairo.Context(self.right_ims)

        ctx.set_source_surface(ims, 0, 0)
        ctx.paint()

        self.drawingarea.queue_draw()

    def _restore_keyval(self, keyval):
        # restore keyval from shift modified name

        keyval = keyval
        if keyval >= 0x41 and keyval <= 0x5a:
            return keyval ^ 0x20

        d = {
                Gdk.KEY_degree: Gdk.KEY_asciicircum,
                Gdk.KEY_exclam: Gdk.KEY_1,
                Gdk.KEY_quotedbl: Gdk.KEY_2,
                Gdk.KEY_section: Gdk.KEY_3,
                Gdk.KEY_dollar: Gdk.KEY_4,
                Gdk.KEY_percent: Gdk.KEY_5,
                Gdk.KEY_ampersand: Gdk.KEY_6,
                Gdk.KEY_slash: Gdk.KEY_7,
                Gdk.KEY_parenleft: Gdk.KEY_8,
                Gdk.KEY_parenright: Gdk.KEY_9,
                Gdk.KEY_equal: Gdk.KEY_0,
                Gdk.KEY_question: Gdk.KEY_ssharp,
                Gdk.KEY_grave: Gdk.KEY_acute,

                Gdk.KEY_asterisk: Gdk.KEY_plus,
                Gdk.KEY_apostrophe: Gdk.KEY_numbersign,
                Gdk.KEY_semicolon: Gdk.KEY_comma,
                Gdk.KEY_colon: Gdk.KEY_period,
                Gdk.KEY_underscore: Gdk.KEY_minus,
                Gdk.KEY_greater: Gdk.KEY_less,
                Gdk.KEY_ISO_Left_Tab: Gdk.KEY_Tab,

                Gdk.KEY_Udiaeresis: Gdk.KEY_udiaeresis,
                Gdk.KEY_Adiaeresis: Gdk.KEY_adiaeresis,
                Gdk.KEY_Odiaeresis: Gdk.KEY_odiaeresis,
            }

        if (res := d.get(keyval, None)) is not None:
            return res

        return keyval

    def on_key_press_event(self, widget, event):
        keyval = self._restore_keyval(event.keyval)
        changed = False
        if not self.key_states.get(keyval, None):
            print(f'changed {keyval} {Gdk.keyval_name(keyval)} to {True}')
            changed = True
        self.key_states[keyval] = True

        self._update_input_states(keyval, changed)

    def on_key_release_event(self, widget, event):
        keyval = self._restore_keyval(event.keyval)
        changed = False
        if self.key_states.get(keyval, None) is True:
            print(f'changed {keyval} {Gdk.keyval_name(keyval)} to {False}')
            changed = True
        self.key_states[keyval] = False

        self._update_input_states(keyval, changed)

        # print("Key press on widget: ", widget)
        # print("          Modifiers: ", event.state)
        # print("      Key val, name: ", event.keyval, Gdk.keyval_name(event.keyval))

    def _update_input_states(self, keyval, changed):

        keymap = {
                Gdk.KEY_Left: util.Buttons.Bigknob_Left,
                Gdk.KEY_Right: util.Buttons.Bigknob_Right,
                Gdk.KEY_Up: util.Buttons.Bigknob_Up,
                Gdk.KEY_Down: util.Buttons.Bigknob_Down,
                Gdk.KEY_Return: util.Buttons.Bigknob_Push,

                Gdk.KEY_1: util.Buttons.Knob_1,
                Gdk.KEY_2: util.Buttons.Knob_2,
                Gdk.KEY_3: util.Buttons.Knob_3,
                Gdk.KEY_4: util.Buttons.Knob_4,
                Gdk.KEY_5: util.Buttons.Knob_5,
                Gdk.KEY_6: util.Buttons.Knob_6,
                Gdk.KEY_7: util.Buttons.Knob_7,
                Gdk.KEY_8: util.Buttons.Knob_8,

                Gdk.KEY_Shift_L: util.Buttons.Shift,
                Gdk.KEY_m: util.Buttons.Mute,
                Gdk.KEY_s: util.Buttons.Solo,

                Gdk.KEY_p: util.Buttons.Play,
                Gdk.KEY_o: util.Buttons.Stop,
                Gdk.KEY_i: util.Buttons.Record,

                Gdk.KEY_F1: util.Buttons.Setup,
                Gdk.KEY_F2: util.Buttons.Midi,

                Gdk.KEY_F6: util.Buttons.Scene,
            }

        s = functools.reduce(operator.ior, [v.int_mask for k, v in keymap.items() if self.key_states.get(k, False)], 0)

        if keyval == Gdk.KEY_Page_Up and self.key_states[keyval] and changed:
            self.bigknob_value = (self.bigknob_value + 1) % 16
        elif keyval == Gdk.KEY_Page_Down and self.key_states[keyval] and changed:
            self.bigknob_value = (self.bigknob_value - 1) % 16

        if keyval == Gdk.KEY_ssharp and self.key_states[keyval]:
            for i, k in enumerate([
                        Gdk.KEY_1,
                        Gdk.KEY_2,
                        Gdk.KEY_3,
                        Gdk.KEY_4,
                        Gdk.KEY_5,
                        Gdk.KEY_6,
                        Gdk.KEY_7,
                        Gdk.KEY_8,
                    ]):
                if self.key_states.get(k, False):
                    self.knob_values[i] = (self.knob_values[i] - 5) % 1000
        elif keyval == Gdk.KEY_acute and self.key_states[keyval]:
            for i, k in enumerate([
                        Gdk.KEY_1,
                        Gdk.KEY_2,
                        Gdk.KEY_3,
                        Gdk.KEY_4,
                        Gdk.KEY_5,
                        Gdk.KEY_6,
                        Gdk.KEY_7,
                        Gdk.KEY_8,
                    ]):
                if self.key_states.get(k, False):
                    self.knob_values[i] = (self.knob_values[i] + 5) % 1000

        res = struct.pack('B9s8H2HBB', 0x01, s.to_bytes(8, 'big'), *self.knob_values, 0, 0, self.bigknob_value, 0x24)

        self.keystate_callback(res)

def init_for_asyncio():
    import gbulb
    gbulb.install()
