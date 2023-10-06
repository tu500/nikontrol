from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import OscMessageBuilder
client = SimpleUDPClient('localhost', 3819)
# client.send_message('/set_surface', (2, 159, 8, 0, 2, 2, 10000, 0, 0))
# client.send_message('/set_surface', (2, 159, 16392, 0, 2, 2, 10000, 0, 0))
# client.send_message('/strip/list', ())
