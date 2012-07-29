import time
from socket import *
import threading
import sys
import struct
import hashlib
import urllib
from collections import deque
from events import *

# Run a method at regular intervals in its own thread
class Threader(threading.Thread):
    
    def __init__(self, repeat_time, callback, *args):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.time = repeat_time
        self.callback = callback
        self.args = args
        self.quit = False
        self.start()

    def run(self):
        while not self.quit:
            self.callback(*self.args)
            time.sleep(self.time)

    def stop(self):
        self.quit = True
        
# Random utils
class Utils():
    def __init__(self):
        self.types = {
            "x": 0,
            "c": 1,
            "b": 1,
            "B": 1,
            "?": 1,
            "h": 2,
            "H": 2,
            "i": 4,
            "I": 4,
            "l": 4,
            "L": 4,
            "q": 8,
            "Q": 8,
            "f": 4,
            "d": 8
            }

    def encode_string(self, string):
        try:
            string = str(string)
        except:
            pass
            
        string = string.replace("&", "&amp;")
        string = string.replace("<", "&lt;")
        string = string.replace("\n", "\r")
        return string.encode("utf-8", "replace")

    def decode_string(self, string):
        string = string.decode("utf-8", "replace")
        string = string.replace("\r", "\n")
        string = string.replace("&lt;", "<")
        return string.replace("&amp", "&")

    def pack(self, types, *data):

        assert len(types) == len(data)
        
        result = ""

        for i in range(0, len(data)):
            d = data[i]
            t = types[i]
            
            if t == "s":
                d = self.encode_string(d)
                length = struct.pack("!H", len(d))
                result += length + d
            else:
                result += struct.pack("!"+t, d)

        return result

    def unpack(self, types, data):
        result = []

        for i in range(0, len(types)):
            assert len(data) > 0
            t = types[i]
            if t in self.types:
                result.append(struct.unpack("!"+t, data[:self.types[t]])[0])
                data = data[self.types[t]:]
            elif t == "s":
                str_len = struct.unpack("!H", data[:2])[0]
                result.append(self.decode_string(data[2:2+str_len]))
                data = data[2+str_len:]

        if len(result) == 1:
            return result[0]

        return result

    def display(self, message):
        print time.strftime("[%H:%M:%S] ") + message

# Socket to connect to a server
class TFMSocket():

    def __init__(self, parent):
        self.parent = parent        
        self.MDT = None
        self.CMDTEC = None
        self.connected = False
        self.socket = None
        self.data = ""

    def connect(self, IP, port=443):
        if self.connected:
            self.Close()
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.parent.display("Connecting to %s" % IP)
        self.socket.connect((IP, port))
        self.connected = True
        self.parent.display("Connected to %s" % IP)

    def close(self):
        self.connected = False
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def gen_fp(self):
        fp = ''
        if self.MDT is None:
            fp = '\x00' * 4
        else:
            loc = self.CMDTEC % 9000 + 1000
            fp += chr(self.MDT[int(loc / 1000)])
            fp += chr(self.MDT[int(loc / 100) % 10])
            fp += chr(self.MDT[int(loc / 10) % 10])
            fp += chr(self.MDT[loc % 10])

            self.CMDTEC += 1

        return fp

    def set_fp(self, MDT, CMDTEC):
        new_MDT = [10] * 10
        for i in range(0, 10):
            if int(MDT[i]) > 0:
                new_MDT[i] = int(MDT[i])
        self.MDT = new_MDT
        self.CMDTEC = int(CMDTEC)

    def send(self, old, c, cc, *data):

        packet = self.parent.utils.pack("BB", c, cc)

        if old:
            packet += '\x01' + '\x01'.join(map(self.parent.utils.encode_string, data))
            packet = '\x01\x01' + self.parent.utils.pack("H", len(packet)) + packet
        else:
            assert len(data) <= 1
            if len(data) == 1:
                packet += data[0]

        packet = self.gen_fp() + packet

        packet = self.parent.utils.pack("I", len(packet)+4) + packet

        if not self.connected:
            return

        try:
            self.socket.send(packet)
        except:
            self.parent.sock_error = repr(sys.exc_info()[1])


    def recv(self):
        if self.connected:
            try:
                self.data += self.socket.recv(4096)
            except:
                self.parent.sock_error = repr(sys.exc_info()[1])
            while self.data != "":
                dl = len(self.data)
                if dl > 4:
                    pl = self.parent.utils.unpack("I", self.data[:4])
                    if dl >= pl:
                        self.parent.parse(self.data[4:pl])
                        self.data = self.data[pl:]
                    else:
                        break
                else:
                    break

# The bot itself
class TFMBot():
    def __init__(self, username, password, botted_account, event_handler):
        self.username = username
        if password == "":
            self.password = ""
        else:
            self.password = hashlib.sha256(password).hexdigest()
        self.room = '*' + hashlib.sha256(username).hexdigest()
        self.botted_account = botted_account
        self.events = event_handler
        self.events.set_bot(self)

        self.main_server = TFMSocket(self)     
        self.main_poller = Threader(0.01, self.main_server.recv)
        self.keepalive_thread = Threader(12, self.keepalive)
        
        self.sock_error = ""
        self.utils = Utils()

        self.tribe_members = set()
        self.chat_queue = deque()

        if botted_account:
            self.chat_wait = 0.01
        else:
            self.chat_wait = 1


    def go(self):
        if self.botted_account:
            version, key = ['', '']
        else:
            self.display("Fetching key")
            try:
                data = urllib.urlopen("http://kikoo.formice.com/data.txt").read()
            except:
                self.display("Error fetching key")
                return
            t, version, key = data.split()
        self.main_server.connect("serveur.transformice.com")
        self.send_connect_main(version, key)
        
        while self.sock_error == "":
            if len(self.chat_queue) > 0:
                self.main_server.send(*self.chat_queue.popleft())
            time.sleep(self.chat_wait)

        self.display("Disconnected from server - %s" % self.sock_error)

    def parse(self, packet):
        
        original = packet
        c, cc = self.utils.unpack("BB", packet)
        data = packet[2:]

        handled = False

        if c == 1 and cc == 1:
            # Old protocol
            c, cc = self.utils.unpack("BB", data[2:])
            data = data[5:]
            args = data.split('\x01')

            if c == 1 and cc == 1:
                pass

            elif c == 8 and cc == 15:               # List of titles
                handled = True

            elif c == 16 and cc == 4:               # Tribe actions
                action = int(args[0])                
                if action == 1:                         # Connect
                    handled = True
                    mouse = args[1]
                    self.tribe_members.add(mouse)
                    self.events.on_tribe_connect(mouse)
                elif action == 2:                       # Disconnect
                    handled = True
                    mouse = args[1]
                    try:
                        self.tribe_members.remove(mouse)
                    except:
                        self.update_tribe_list()
                    self.events.on_tribe_disconnect(mouse)
                elif action == 6:                       # Join tribe
                    handled = True
                    mouse = args[1]
                    if mouse == self.username:
                        self.events.on_self_tribe_join()
                    else:
                        self.events.on_tribe_join(mouse)
                elif action == 11:                      # Leave tribe
                    handled = True
                    mouse = args[1]
                    if mouse == self.username:
                        self.tribe_members = set()
                        self.events.on_self_tribe_leave()
                    else:
                        self.events.on_tribe_leave(mouse)

            elif c == 16 and cc == 14:              # Tribe invite
                handled = True
                tribe_id, mouse, tribe = args
                self.events.on_tribe_invite(mouse, tribe, tribe_id)

            elif c == 16 and cc == 16:              # Tribe list
                handled = True
                self.tribe_members = set()
                for mouse in args:
                    self.tribe_members.add(mouse.split('\x02')[0])

            elif c == 26 and cc == 3:               # Login error
                handled = True
                self.sock_error = "Invalid username or password or already connected"

            elif c == 26 and cc == 8:               # Logged in
                handled = True
                name, uid, rank, unknown = args
                self.username = name
                self.display("Logged in as %s (%s) - rank %s" % (name, uid, rank))
                self.update_tribe_list()
                self.events.on_login(name)

            elif c == 26 and cc == 27:              # Connected to server
                handled = True
                self.display("%s mice online." % args[0])
                self.main_server.set_fp(args[1], args[2])
                self.login()

        else:
            # New
            if c == 1 and cc == 1:
                pass

            elif c == 6 and cc == 7:                # Whisper
                handled = True
                direction, mouse, community, message, mod =\
                           self.utils.unpack("BsBsB", data)
                self.events.on_whisper(mouse, direction, message)

            elif c == 6 and cc == 8:                # Tribe chat
                handled = True
                message, mouse = self.utils.unpack("ss", data)
                self.events.on_tribe_chat(mouse, message)

            elif c == 16 and cc == 18:              # Tribe message, tribe house etc
                handled = True

            elif c == 26 and cc == 26:              # Old ping
                handled = True

            elif c == 28 and cc == 13:              # Email validated or not
                handled = True

            elif c == 44 and cc == 1:               # Bulle data
                handled = True

        if handled == False:
            self.display("Unknown packet " + repr([original]))

    def send_connect_main(self, version, key):
        if self.botted_account:        
            self.main_server.send(False, 28, 1, self.utils.pack("H", 666))
        else:
            packet = self.utils.pack("hs", int(version), key) + '\x17\xed'
            self.main_server.send(False, 28, 1, packet)

    def login(self):
        self.display("Logging in")
        self.main_server.send(True, 26, 4, self.username, self.password, self.room, "http://www.transformice.com/Transformice.swf?n=1335716949138")

    def keepalive(self):
        try:
            self.main_server.send(False, 26, 2)
        except:
            pass
        

    # Actions

    def display(self, msg):
        """Display a message to the console."""
        self.utils.display(msg)
    
    def whisper(self, mouse, message):
        """Send a whisper to mouse."""
        self.chat_queue.append((False, 6, 7, self.utils.pack("ss", mouse, message)))

    def accept_invite(self, tribe_id):
        """Accept a tribe invite."""
        self.main_server.send(True, 16, 13, tribe_id)

    def tribe_chat(self, message):
        """Send a message in tribe chat."""
        self.chat_queue.append((False, 6, 8, self.utils.pack("s", message)))

    def update_tribe_list(self):
        """Force the tribe list to refresh."""
        self.main_server.send(True, 16, 16)
