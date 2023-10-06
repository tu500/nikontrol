import asyncio
import enum
import logging
import re
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import OscMessageBuilder

# packet loss with default kernel network buffer size (212992)
# works better with increased buffer size:
# sysctl -w net.core.rmem_max=26214400
# sysctl -w net.core.rmem_default=26214400

# monkey patch osc server to give close event
class _OSCProtocolFactory(AsyncIOOSCUDPServer._OSCProtocolFactory):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.close_event = asyncio.Event()

    def connection_lost(self, exc):
        super().connection_lost(exc)
        self.close_event.set()
AsyncIOOSCUDPServer._OSCProtocolFactory = _OSCProtocolFactory


LOG_UNKNOWN_MESSAGES = False
LOG_STATE_CHANGES = True

class OscEventType(enum.Enum):
    GENERAL_DATA = enum.auto()
    STRIP_LIST = enum.auto()
    STRIP_DATA = enum.auto()

class ArdourOscStripFlags(enum.IntFlag):
    NONE = 0
    AUDIO_TRACKS = 1
    MIDI_TRACKS = 2
    AUDIO_BUSSES = 4
    MIDI_BUSSES = 8
    VCAS = 16
    MASTER = 32
    MONITOR = 64
    FOLDBACK_BUSSES = 128
    SELECTED = 256
    HIDDEN = 512
    USE_GROUP = 1024

class ArdourOscFeedbackFlags(enum.IntFlag):
    NONE = 0
    STRIP_BUTTON_STATUS = 1
    STRIP_VARIABLE_CONTROL_VALUES = 2
    SSID_PATH_EXTENSION = 4
    HEARTBEAT = 8
    MASTER_SECTION = 16
    BAR_AND_BEAT = 32
    TIMECODE = 64
    METER_DB = 128
    METER_STRIP = 256
    SIGNAL_PRESENT = 512
    POSITION_IN_SAMPLES = 1024
    POSITOIN_IN_TIME = 2048
    SELECT_CHANNEL = 8192
    OSC1_REPLY = 16384

class ArdourOscGainMode(enum.IntEnum):
    GAIN_ONLY = 0
    FADER_GAIN_RENAME = 1
    FADER_AND_GAIN = 2
    FADER_ONLY = 3

# decorator to register members into dispatcher
def dispatch(address=None):
    def f(func):
        if address is None:
            if not func.__name__.startswith('on_'):
                raise ValueError()
            dispatch_address = '/' + func.__name__[3:]
        else:
            dispatch_address = address
        if not hasattr(func, '_dispatch_to'):
            func._dispatch_to = []
        func._dispatch_to.append(dispatch_address)
        return func
    return f

def log_osc_message(address, *args):
    logging.debug(f'{address}: {args!r}')

class OscRemoteState():
    def __init__(self):
        self.strips = {}
        self.state = {}
        self.changed_callbacks = []
        self.refreshing_strip_list = False

    def _get_dispatcher(self):
        state_dict = {
                '/session_name': ('session_name', str),
                '/rec_enable_toggle': ('rec_enabled', bool),
                '/transport_stop': ('transport_stopped', bool),
                '/transport_play': ('transport_playing', bool),
                '/ffwd': ('ffwd', bool),
                '/rewind': ('rewind', bool),
                '/loop_toggle': ('loopmode_enabled', bool),
                '/cancel_all_solos': ('solo_active', bool),
                '/record_tally': ('any_record_active', bool),
                '/toggle_click': ('click_active', bool),
                '/click/level': ('click_level', float),
                '/position/smpte': ('playhead_position', str),
                # '/position/bbt': ('playhead_position', str),
                # '/position/time': ('playhead_position', str),
                # '/position/samples': ('playhead_position', str),
            }
        dispatcher = Dispatcher()
        for member_name in dir(self.__class__):
            member = getattr(self.__class__, member_name)
            if hasattr(member, '_dispatch_to'):
                for address in member._dispatch_to:
                    dispatcher.map(address, getattr(self, member_name))
        for address, (target_name, target_type) in state_dict.items():
            dispatcher.map(address, self.on_state, target_name, target_type)
        if LOG_UNKNOWN_MESSAGES:
            dispatcher.set_default_handler(log_osc_message)
        return dispatcher

    async def start_server(self):
        local_port = 9100
        self.client = SimpleUDPClient('localhost', 3819)
        self.server = AsyncIOOSCUDPServer(('localhost', local_port), self._get_dispatcher(), asyncio.get_event_loop())
        self.transport, self.protocol = await self.server.create_serve_endpoint()

        self.client.send_message('/set_surface', (
                0, # no banking

                # strips
                ArdourOscStripFlags.AUDIO_TRACKS |
                ArdourOscStripFlags.MIDI_TRACKS |
                ArdourOscStripFlags.AUDIO_BUSSES |
                ArdourOscStripFlags.MIDI_BUSSES |
                ArdourOscStripFlags.VCAS |
                ArdourOscStripFlags.MASTER |
                # ArdourOscStripFlags.MONITOR |
                ArdourOscStripFlags.FOLDBACK_BUSSES |
                # ArdourOscStripFlags.SELECTED |
                # ArdourOscStripFlags.HIDDEN |
                # ArdourOscStripFlags.USE_GROUP |
                ArdourOscStripFlags.NONE,

                # feedback
                ArdourOscFeedbackFlags.STRIP_BUTTON_STATUS |
                ArdourOscFeedbackFlags.STRIP_VARIABLE_CONTROL_VALUES |
                ArdourOscFeedbackFlags.HEARTBEAT |
                ArdourOscFeedbackFlags.MASTER_SECTION |
                ArdourOscFeedbackFlags.TIMECODE |
                ArdourOscFeedbackFlags.METER_DB |
                ArdourOscFeedbackFlags.SELECT_CHANNEL |
                ArdourOscFeedbackFlags.OSC1_REPLY,

                ArdourOscGainMode.FADER_AND_GAIN,
                0, # no send paging
                0, # no plugin paging
                local_port, # reply port
            ))

        while self.get('session_name', None) is None:
            await asyncio.sleep(.1)
            print('WAITING')
        await asyncio.sleep(.1) # initial /strip/list is unreliable without this sleep
        logging.info('doing initial refresh')
        self._send_strip_list()

        # as per https://stackoverflow.com/a/65688291
        # await asyncio.Event().wait()

        await self.protocol.close_event.wait()

    def get_drawable_strips(self):
        res = []

        # TODO maybe change logic and check for refreshing state everywhere else, and refresh into temporary dict
        using_dict = self.old_strips if self.refreshing_strip_list else self.strips

        # XXX
        # if (strip := using_dict.get('master')) is not None:
        #     res.append(strip)
        for strip in using_dict.values():
            try:
                i = int(strip.ssid)
            except:
                pass
            else:
                res.append(strip)
        return res


    @dispatch()
    def on_heartbeat(self, address, *args):
        # logging.debug(f'heartbeat')
        pass

    @dispatch('/strip/list')
    def on_strip_list(self, address):
        logging.info('DOING REFRESH')
        self._send_strip_list()

    def _send_strip_list(self):
        self.refreshing_strip_list = True
        self.old_strips = self.strips
        self.strips = {}
        if 'master' in self.old_strips: # might not be present, eg when initializing
            self.strips['master'] = self.old_strips['master']

        # self.trigger_changed_callback(None) # XXX
        self.client.send_message('/strip/list', None)

    @dispatch('/reply')
    def on_reply(self, address, *args):
        if args[0] == 'end_route_list':
            _, sample_rate, current_end_sample, monitor = args
            # TODO consolidate with dispatcher dict
            self.state['sample_rate'] = int(sample_rate)
            self.state['current_end_sample'] = int(current_end_sample)
            self.state['monitored'] = bool(monitor)
            self.refreshing_strip_list = False
            self.trigger_changed_callback(OscEventType.STRIP_LIST)
            self.trigger_changed_callback(OscEventType.GENERAL_DATA)
            logging.info('refresh done')

        else:
            if len(args) == 8:
                bus = False
                strip_type, name, ninputs, noutputs, muted, soloed, ssid, rec_enabled = args
            elif len(args) == 7:
                bus = True
                # no rec_enabled for busses
                strip_type, name, ninputs, noutputs, muted, soloed, ssid = args
            else:
                raise ValueError()

            logging.info(f'refresh entry {ssid} {name}')

            if not ssid in self.strips:
                self.strips[ssid] = StripState(self, ssid)

            strip = self.strips[ssid]

            # TODO consolidate with dispatcher dict
            strip.state['strip_type'] = str(strip_type)
            strip.state['name'] = str(name)
            strip.state['ninputs'] = int(ninputs)
            strip.state['noutputs'] = int(noutputs)
            strip.state['muted'] = bool(muted)
            strip.state['soloed'] = bool(soloed)
            strip.state['ssid'] = ssid
            if not bus:
                strip.state['recenabled'] = bool(rec_enabled)

    @dispatch('/select/*')
    def on_select_message(self, address, *args):
        pass

    @dispatch('/master/*')
    def on_master_message(self, address, *args):
        self.on_strip_message(address, 'master', *args)

    @dispatch('/strip/*')
    def on_strip_message(self, address, ssid=None, *args):

        if ssid is None:
            return # '/strip/list' for example

        # kind of a hack, build a new message with reduced address to dispatch to strip class handler
        # using a dispatcher directly is more complicated because of lacking API
        empty, first_part, rest = address.split(sep='/', maxsplit=2)
        assert empty == ''
        omb = OscMessageBuilder('/' + rest)
        for a in args:
            omb.add_arg(a)
        osc_msg = omb.build()

        if not ssid in self.strips:
            self.strips[ssid] = StripState(self, ssid)
            if not self.refreshing_strip_list:
                self.trigger_changed_callback(OscEventType.STRIP_LIST)

        self.strips[ssid].dispatcher.call_handlers_for_packet(osc_msg._dgram, None)

    def on_state(self, address, fixed_args, value):
        target_name, target_type = fixed_args
        self.state[target_name] = target_type(value)
        # setattr(self, target_name, target_type(value))
        if LOG_STATE_CHANGES:
            logging.debug(f'################# {target_name} = {target_type(value)!r}')


    def on_strip_changed(self, strip):
        self.trigger_changed_callback(OscEventType.STRIP_DATA, strip.ssid)

    def trigger_changed_callback(self, event_type, *args):
        for cb in self.changed_callbacks:
            cb(event_type, *args)

    def register_changed_callback(self, cb):
        self.changed_callbacks.append(cb)

    def get(self, key, default=None):
        return self.state.get(key, default)


class StripState():
    def __init__(self, ors, ssid):
        self.ors = ors
        self.ssid = ssid
        self.state = {}
        self.dispatcher = self._get_dispatcher()

    def _get_dispatcher(self):
        state_dict = {
                '/expand': ('expanded', bool),
                '/select': ('selected', bool),
                '/name': ('name', str),
                '/meter': ('meter', float),
                '/group': ('group_name', str),
                '/mute': ('muted', bool),
                '/solo': ('soloed', bool),
                '/recenable': ('recenabled', bool),
                '/gain': ('gain', float),
                '/fader': ('fader', float),
                '/pan_stereo_position': ('pan_position', float),
            }
        dispatcher = Dispatcher()
        for member_name in dir(self.__class__):
            member = getattr(self.__class__, member_name)
            if hasattr(member, '_dispatch_to'):
                for address in member._dispatch_to:
                    dispatcher.map(address, getattr(self, member_name))
        for address, (target_name, target_type) in state_dict.items():
            dispatcher.map(address, self.on_state, target_name, target_type)
        if LOG_UNKNOWN_MESSAGES:
            dispatcher.set_default_handler(log_osc_message)
        return dispatcher

    def on_state(self, address, fixed_args, value=None):
        if value is None:
            logging.warn(f'{address} ({self.ssid}): NONE value')
        target_name, target_type = fixed_args
        self.state[target_name] = target_type(value)
        # setattr(self, target_name, target_type(value))
        self.ors.on_strip_changed(self)
        if LOG_STATE_CHANGES:
            logging.debug(f'{self.ssid}: {target_name} = {target_type(value)!r}')

    def get(self, key, default=None):
        return self.state.get(key, default)


def main_osc():
    ors = OscRemoteState()
    asyncio.run(ors.start_server())
