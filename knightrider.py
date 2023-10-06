from __future__ import annotations

import asyncio
import cairo
import logging

from typing import *

if TYPE_CHECKING:
    import main

import math
import time

import gui_debug
import gui_hw
import gui
import osc_state
import util
import views

class KRDrawer():

    def __init__(self, side=0):
        self.side = side
        self.pos = 0
        self.ims = cairo.ImageSurface(cairo.Format.RGB16_565, 480, 272)

    def set_pos(self, pos):
        self.pos = pos

    def draw(self):
        ctx = cairo.Context(self.ims)
        gui._fill_background(ctx, self.ims)

        t = self.pos / 100 * 480*2

        if self.side == 1:
            t -= 480

        for i in range(1,20):
            ctx.set_source_rgb((20-i) / 20, .0, .0)
            ctx.rectangle(t-20-i, 200-i, 40+2*i, 10+2*i)
            ctx.stroke()
        ctx.set_source_rgb(1., .0, .0)
        ctx.rectangle(t-20, 200, 40, 10)
        ctx.fill()


        if self.side == 0:
            text = 'Thank You'
        else:
            text = 'For Listening'

        font_size = 70
        ctx.set_font_size(font_size)
        ctx.set_source_rgb(1, 1, 1)
        ctx.select_font_face('sans-serif')
        tx, _, tw, _, _, _ = ctx.text_extents(text)
        ctx.move_to(480//2 - tx - tw//2, 100 + font_size//2)
        ctx.show_text(text)

class KnightRiderView(views.View):

    task: Optional[asyncio.Task]

    def __init__(self, logic: main.Logic):
        self.logic = logic
        self.cross_drawer = gui.CrossDrawer()
        self.lkr_drawer = KRDrawer(0)
        self.rkr_drawer = KRDrawer(1)

        self.state = 0
        self.pos = 0
        self.dir = 1

        self.task = None

    def draw(self, logic):

        self.lkr_drawer.set_pos(self.pos)
        self.rkr_drawer.set_pos(self.pos)

        self.cross_drawer.draw()
        self.lkr_drawer.draw()
        self.rkr_drawer.draw()

        if self.state >= 3:
            logic.upload_image(0, 0, 0, self.lkr_drawer.ims)
            logic.upload_image(1, 0, 0, self.rkr_drawer.ims)
        else:
            logic.upload_image(0, 0, 0, self.cross_drawer.ims)
            logic.upload_image(1, 0, 0, self.cross_drawer.ims)



        if self.state >= 1:
            t = math.floor(self.pos / 100 * 61)
            b = bytes(util.Colors.RED.with_brightness(2) if abs(i-t)<=1 else util.Colors.OFF.with_brightness(0) for i in range(61))
            logic.device_gui.upload_key_lighting(b)

        if self.state >= 2:
            t = math.floor(self.pos / 100 * 25)
            b = bytes(util.Colors.RED.with_brightness(2) if abs(i-t)<=1 else util.Colors.OFF.with_brightness(0) for i in range(25))
            self.logic.device_gui.touchstrip_lighting = b
            logic.config_trigger.trigger()

        return True

    def button_pressed(self, logic: main.Logic, button: util.Buttons) -> None:

        if button == util.Buttons.Scene:
            self.state += 1
            self.logic.config_trigger.trigger()
            self.logic.redraw_trigger.trigger()

    def get_button_lighting(self):
        t = math.floor(self.pos / 100 * 8)
        b = [
                util.Buttons.Button_1,
                util.Buttons.Button_2,
                util.Buttons.Button_3,
                util.Buttons.Button_4,
                util.Buttons.Button_5,
                util.Buttons.Button_6,
                util.Buttons.Button_7,
                util.Buttons.Button_8,
            ][t]
        res = { b: (util.Colors.RED, 2, False) }
        return res

    def get_general_config(self) -> Mapping[util.GeneralOptions, bool]:
        res = {}

        if self.state >= 0:
            res[util.GeneralOptions.DISPLAY_BUTTONS_COLOR_RESPONSE] = False
        if self.state >= 1:
            res[util.GeneralOptions.KEY_COLOR_RESPONSE] = False
        if self.state >= 2:
            res[util.GeneralOptions.TOUCH_STRIP_ON] = False
        return res

    async def run_loop(self):

        while True:
            await asyncio.sleep(.02)

            now = time.time()
            self.pos = now * 100 % 199
            if self.pos >= 100:
                self.pos = 199 - self.pos

            self.logic.config_trigger.trigger()
            self.logic.redraw_trigger.trigger()

    def view_enter(self, logic: main.Logic):
        if not self.task:
            self.task = asyncio.create_task(self.run_loop())

    def view_leave(self, logic: main.Logic):
        if self.task:
            self.task.cancel()
