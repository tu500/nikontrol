#!/usr/bin/python

import cairo
import logging
import math

def _fill_background(ctx, ims):
    'Paint background black, any size ims'
    ctx.set_source_rgb(0, 0, 0)
    ctx.rectangle(0, 0, ims.get_width(), ims.get_height())
    ctx.fill()

def _draw_title_bar(ctx, title):
    'Assumes full width ctx'
    ctx.set_source_rgb(.2, .2, .1)
    ctx.rectangle(0, 0, 480, 22)
    ctx.fill()
    if title:
        _draw_hierarchy_string(ctx, title, 5)

def _draw_button_highlight(ctx, position, width, radiance=True):
    color = (.75, .4, 0)
    W = 10
    for i in range(W if radiance else 1):
        if i == 0:
            ctx.set_source_rgb(*color)
        else:
            ctx.set_source_rgb(*((c*2/3) * (W-1-i) / (W-1) for c in color))
        ctx.rectangle(position[0]-i, position[1]-i, width+2*i, 22+2*i)
        ctx.stroke()

def _draw_button(ctx, text, position, width, highlighted=False, centered=False, draw_background=True):
    # background
    if draw_background:
        ctx.set_source_rgb(.2, .2, .1)
        ctx.rectangle(position[0], position[1], width, 22)
        ctx.fill()

    # text
    height = 22
    font_size = 12
    # FIXME font size not set?
    ctx.set_source_rgb(1, 1, 1)
    ctx.select_font_face('sans-serif')
    if centered:
        tx, _, tw, _, _, _ = ctx.text_extents(text)
        os = -tx - tw//2 + width//2
    else:
        os = 5
    ctx.move_to(position[0] + os, position[1] + height//2 + font_size//2 - 1)
    ctx.show_text(text)

    # highlight
    if highlighted:
        _draw_button_highlight(ctx, position, width, radiance=False)

def _draw_hierarchy_string(ctx, entries, offset):
    height = 22
    font_size = 12
    triangle_size = 8
    triangle_spacing = 1.5
    ctx.set_font_size(font_size)
    ctx.set_source_rgb(1, 1, 1)

    for entry in entries[:-1]:
        ctx.select_font_face('sans-serif')
        _, _, _, _, dx, _ = ctx.text_extents(entry)
        ctx.move_to(offset, height//2 + font_size//2 - 1)
        ctx.show_text(entry)
        offset += dx

        ctx.move_to(offset + triangle_size*triangle_spacing, height//2 - triangle_size//2)
        ctx.rel_line_to(triangle_size*.75, triangle_size//2)
        ctx.rel_line_to(-triangle_size*.75, triangle_size//2)
        ctx.fill()
        offset += (2*triangle_spacing+.75)*triangle_size

    entry = entries[-1]
    ctx.select_font_face('sans-serif')
    ctx.move_to(offset, height//2 + font_size//2 - 1)
    ctx.show_text(entry)


class CrossDrawer():

    def __init__(self):
        self.ims = cairo.ImageSurface(cairo.Format.RGB16_565, 480, 272)

    def draw(self):
        ctx = cairo.Context(self.ims)
        _fill_background(ctx, self.ims)

        ctx.set_source_rgb(1, 0, 0)
        ctx.move_to(0, 0)
        ctx.line_to(479, 271)
        ctx.stroke()
        ctx.move_to(479, 0)
        ctx.line_to(0, 271)
        ctx.stroke()

class MenuDrawer():

    def __init__(self, title, options, highlight_index=0):
        self.title = title
        self.options = options
        self.ims = cairo.ImageSurface(cairo.Format.RGB16_565, 480, 272)
        self.highlight_index = highlight_index

    def set_highlight_index(self, index):
        self.highlight_index = index

    def draw(self):
        ctx = cairo.Context(self.ims)
        _fill_background(ctx, self.ims)
        _draw_title_bar(ctx, self.title)

        for i, o in enumerate(self.options):
            _draw_button(ctx, o, (15, 35 + 35*i), 200, i==self.highlight_index)

class ConfigDrawer():

    def __init__(self, title, headers, options, highlight_index=(0,0)):
        self.title = title
        self.headers = headers
        self.options = options
        self.ims = cairo.ImageSurface(cairo.Format.RGB16_565, 480, 272)
        self.highlight_index = highlight_index

    def draw(self):
        ctx = cairo.Context(self.ims)
        _fill_background(ctx, self.ims)
        _draw_title_bar(ctx, self.title)

        # draw highlight radiance first
        j, i = self.highlight_index
        _draw_button_highlight(ctx, (j*120 + 15, 50 + i * 25), 90)

        for i, header in enumerate(self.headers):
            _draw_button(ctx, header, (i*120 + 15, 25), 90, draw_background=False)

        for i, row in enumerate(self.options):
            for j, o in enumerate(row):
                _draw_button(ctx, str(o), (j*120 + 15, 50 + i * 25), 90, highlighted=(j, i) == self.highlight_index, centered=True)

class StripBankDrawer():
    def __init__(self, osc_state):
        self.osc_state = osc_state
        self.strips = []
        self.ims = cairo.ImageSurface(cairo.Format.RGB16_565, 480, 272)

    def set_strip_list(self, lst):
        # self.strips = [StripDrawer(strip) for strip in lst]
        self.strips = list(lst)

    # def read_updated_strip_data(self, ssid):
    #     for strip in self.strips:
    #         if strip.strip_state.ssid == ssid:
    #             strip.update()

    def draw(self):

        ctx = cairo.Context(self.ims)
        _fill_background(ctx, self.ims)

        if not self.strips:
            ctx.set_source_rgb(1, 0, 0)
            ctx.move_to(0, 0)
            ctx.line_to(479, 271)
            ctx.stroke()
            ctx.move_to(479, 0)
            ctx.line_to(0, 271)
            ctx.stroke()

        else:
            for i, strip in enumerate(self.strips):
                strip.draw()
                ctx.set_source_surface(strip.ims, 120*i, 0)
                ctx.paint()

            # Footer
            ctx.set_source_rgb(.1, .1, .05)
            ctx.rectangle(0, 250, 480, 22)
            ctx.fill()

            font_size = 12
            session_name = self.osc_state.get('session_name', '-')
            ctx.select_font_face('sans-serif')
            ctx.set_font_size(font_size)
            ctx.set_source_rgb(1, 1, 1)
            ctx.move_to(5, 250 + 22//2 + font_size//2 - 2)
            ctx.show_text(f'Session: {session_name}')

class StripDrawer():
    DEFAULT_UI_COLOR = ((.7, .7, .7), (.2, .2, .2))
    HIGHLIGHT_UI_COLOR = ((.7, .4, .0), (.2, .1, .0))

    def __init__(self, strip_state):
        self.strip_state = strip_state
        self.dirty = True
        self.highlight = False
        self.ims = cairo.ImageSurface(cairo.Format.RGB16_565, 120, 272)

    def set_meter(self, meter):
        self.meter = meter
        self.dirty = True

    def set_highlight(self, v):
        self.highlight = v
        self.dirty = True

    def _draw_button(self, ctx, x, y, width, height, bg_color, text_color, text):
        ctx.set_source_rgb(*bg_color)
        ctx.rectangle(x, y, width, height)
        ctx.fill()

        if text:
            text_x, text_y, text_width, text_height, text_dx, text_dy = ctx.text_extents(text)
            ctx.set_source_rgb(*text_color)
            ctx.move_to(x + width/2 - text_width/2 - text_x, y + height/2 - text_height/2 - text_y)
            ctx.show_text(text)

    def _draw_pan_bar(self, ctx, x, y, width, height, bg_color, fg_color, value):
        ctx.set_source_rgb(*bg_color)
        ctx.rectangle(x, y, width, height)
        ctx.fill()
        ctx.set_source_rgb(*fg_color)
        ctx.move_to(x + width*value, y + height)
        ctx.rel_line_to(height, height)
        ctx.rel_line_to(-2 * height, 0)
        ctx.fill()
        ctx.rectangle(x + width/2, y, width*(value-.5), height)
        ctx.fill()

    def _draw_meter_bar(self, ctx, x, y, width, height, bg_color, fg_color, value):
        ctx.set_source_rgb(*bg_color)
        ctx.rectangle(x, y, width, height)
        ctx.fill()
        ctx.set_source_rgb(*fg_color)
        ctx.rectangle(x, y + height - value*height, width, value*height)
        ctx.fill()

    def _draw_highlighting(self, ctx, color):
        W = 20
        for i in range(W):
            if i == 0:
                ctx.set_source_rgb(*color)
            else:
                ctx.set_source_rgb(*((c*2/3) * (W-1-i) / (W-1) for c in color))
            ctx.move_to(1+i, 0)
            ctx.rel_line_to(0, 271)
            ctx.stroke()
            ctx.move_to(119-i, 0)
            ctx.rel_line_to(0, 271)
            ctx.stroke()

    def update(self):
        self.dirty = True

    def draw(self):
        if not self.dirty:
            return
        self.dirty = False

        font_size = 8
        ctx = cairo.Context(self.ims)
        ctx.select_font_face('sans-serif')
        ctx.set_font_size(font_size)
        _fill_background(ctx, self.ims)

        # color selected strip
        if self.strip_state.get('selected'):
            self._draw_highlighting(ctx, (.75, 0, 0))
        elif self.highlight:
            self._draw_highlighting(ctx, (.75, .4, 0))

        # strip name
        name = self.strip_state.get('name', '')
        text_x, text_y, text_width, text_height, text_dx, text_dy = ctx.text_extents(name)
        ctx.set_source_rgb(1, 1, 1)
        ctx.move_to(5, 5 + font_size)
        ctx.show_text(name)

        # mute and solo buttons
        muted = self.strip_state.get('muted', False)
        soloed = self.strip_state.get('soloed', False)
        muted_bg = (.7, .2, .2) if muted else (.2, .2, .2)
        muted_tc = (1, 1, 1) if muted else (.5, .5, .5)
        soloed_bg = (.7, .7, .2) if soloed else (.2, .2, .2)
        soloed_tc = (0, 0, 0) if soloed else (.5, .5, .5)
        self._draw_button(ctx, 5, 20, 10, 10, muted_bg, muted_tc, 'M')
        self._draw_button(ctx, 20, 20, 10, 10, soloed_bg, soloed_tc, 'S')

        # pan bar
        pan_color_fg, pan_color_bg = self.HIGHLIGHT_UI_COLOR if self.highlight else self.DEFAULT_UI_COLOR
        pan = 1 - self.strip_state.get('pan_position', .5)
        self._draw_pan_bar(ctx, 20, 45, 80, 5, pan_color_bg, pan_color_fg, pan)

        # gain fader calculation
        gain_color_fg, gain_color_bg = self.HIGHLIGHT_UI_COLOR if self.highlight else self.DEFAULT_UI_COLOR
        # if self.highlight:
        #     gain_color_fg, gain_color_bg = ((.9, .9, .9), (.4, .4, .4))
        # else:
        #     gain_color_fg, gain_color_bg = ((.4, .4, .4), (.2, .2, .2))
        gain = self.strip_state.get('gain', math.inf)
        # print value
        db_msg = f'{gain:.2f} dB'
        text_x, text_y, text_width, text_height, text_dx, text_dy = ctx.text_extents(db_msg)
        ctx.set_source_rgb(1, 1, 1)
        ctx.move_to(60 - text_width/2 - text_x, 85 - (10 - font_size)/2)
        ctx.show_text(db_msg)
        # draw fader
        fader = max(self.strip_state.get('fader', 0), 0)
        self._draw_meter_bar(ctx, 50, 85, 20, 160, gain_color_bg, gain_color_fg, fader)

        # peak meter bar
        meter = max(self.strip_state.get('meter', 0), 0)
        self._draw_meter_bar(ctx, 35, 85, 10, 160, (.2, .2, .2), (.2, .7, .2), meter)
        self._draw_meter_bar(ctx, 75, 85, 10, 160, (.2, .2, .2), (.2, .7, .2), meter)


def main_gui():
    ui_left = UiDrawer()
    ui_right = UiDrawer()
    ui_left.set_strips([
            StripDrawer('Audio 1', .8, .7, .4),
            StripDrawer('Audio 2', .2, .3, .5),
        ])
    ui_left.update()
    ui_right.update()
    #t = ui_drawer.ims.create_for_rectangle(0, 0, 10, 10)
    # with ui_drawer.ims.map_to_image(cairo.RectangleInt(0, 0, 20, 20)) as t:
    #     print(len(t.get_data()))
    #     print(t.get_data().itemsize)
    #     print(t.get_data().ndim)
    app = gui_debug.DebugWindow(ui_left, ui_right)
    Gtk.main()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    main_gui()
    import osc_state
    osc_state.main_osc()
