#!/usr/bin/python
import sys
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import OscMessageBuilder
import pythonosc.osc_server
def log_osc_message(address, *args):
 print(f'{address}: {args!r}')
dispatcher = Dispatcher()
dispatcher.set_default_handler(log_osc_message)
server = pythonosc.osc_server.BlockingOSCUDPServer(('localhost', int(sys.argv[1])), dispatcher)
server.serve_forever()
