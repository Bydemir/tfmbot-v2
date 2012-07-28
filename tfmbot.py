import time
from socket import *
import threading
import sys
import struct
import hashlib
import urllib

# Run a method at regular intervals in its own thread
class Threader(threading.Thread):
    
    def __init__(self, repeat_time, callback, *args):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.time = repeat_time
        self.callback = callback
        self.args = args
        self.quit = False

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

    def __init__(self, parent, verbose):
        self.parent = parent        
        self.MDT = None     # For fingerprint
        self.CMDTEC = None  # For fingerprint
        self.connected = False
        self.socket = None
        self.data = ""
        self.verbose = verbose

    def connect(self, IP, port=443):
        if self.connected:
            self.Close()
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.parent.utils.display("Connecting to " + IP)
        self.socket.connect((IP, port))
        self.connected = True
        self.parent.utils.display("Connected to " + IP)

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
            if self.verbose:
                self.parent.utils.display("[SEND] " + repr([packet]))
        except:
            self.parent.sock_error = repr(sys.exc_info())


    def recv(self):
        if self.connected:
            try:
                self.data += self.socket.recv(4096)
            except:
                self.parent.sock_error = repr(sys.exc_info())
            while self.data != "":
                dl = len(self.data)
                if dl > 4:
                    pl = self.parent.utils.unpack("I", self.data[:4])
                    if dl >= pl:
                        if self.verbose:
                            self.parent.utils.display("[RECV] " + repr([self.data[:pl]]))
                        self.parent.parse(self.data[4:pl])
                        self.data = self.data[pl:]
                    else:
                        break
                else:
                    break


class TFMBot():
    def __init__(self, username, password, room, community=0, botted_account=False):
        self.username = username
        if password == "":
            self.password = ""
        else:
            self.password = hashlib.sha256(password).hexdigest()
        self.community = community
        self.botted_account = botted_account

        self.main_server = TFMSocket(self, False)
        self.bulle_server = TFMSocket(self, False)
        self.main_poller = Threader(0.01, self.main_server.recv)
        self.main_poller.start()
        self.keepalive_thread = Threader(12, self.keepalive)
        self.keepalive_thread.start()

        self.shamans = []
        self.mice = []
        self.room_to_join = room
        self.room = None
        
        self.sock_error = ""
        self.utils = Utils()

    def go(self):
        if self.botted_account:
            version, key = ['', '']
        else:
            self.utils.display("Fetching key from Danley")
            t, version, key = urllib.urlopen("http://kikoo.formice.com/data.txt").read().split()
        self.main_server.connect("serveur.transformice.com")
        self.send_connect_main(version, key)
        while self.sock_error == "":
            time.sleep(0.01)

        self.utils.display("Disconnected from server - " + self.sock_error)

    def parse(self, packet):
        
        original = packet
        c, cc = self.utils.unpack("BB", packet)
        packet = packet[2:]

        handled = False

        if c == 1 and cc == 1:
            # Old protocol
            c, cc = self.utils.unpack("BB", packet[2:])
            packet = packet[5:]
            args = packet.split('\x01')

            if c == 1 and cc == 1:
                pass

            elif c == 8 and cc == 15: # List of titles
                handled = True

            elif c == 26 and cc == 3: # Login error
                handled = True
                self.sock_error = "Invalid username or password"
                # want to tidy this up

            elif c == 26 and cc == 8: # Logged in
                handled = True
                name, uid, rank, unknown = args
                self.username = name
                self.utils.display("Logged in as " + name + " (" + uid + ") - rank " + rank)

            elif c == 26 and cc == 27: # Connected to server
                handled = True
                self.utils.display(args[0] + " mice online.")
                self.main_server.set_fp(args[1], args[2])
                self.login()


        else:
            # New
            if c == 1 and cc == 1:
                pass

            elif c == 28 and cc == 13: # Email validated or not
                handled = True

        if handled == False:
            self.utils.display("Unknown packet " + repr([original]))

    def send_connect_main(self, version=666, key=''):
        if self.botted_account:        
            self.main_server.send(False, 28, 1, self.utils.pack("H", 666))
        else:
            packet = self.utils.pack("hs", int(version), key) + '\x17\xed'
            self.main_server.send(False, 28, 1, packet)

    def login(self):
        self.utils.display("Logging in")
        self.main_server.send(False, 8, 2, self.utils.pack("b", self.community))
        self.main_server.send(True, 26, 4, self.username, self.password, self.room_to_join, "http://www.transformice.com/Transformice.swf?n=1335716949138")

    def keepalive(self):
        try:
            self.main_server.send(False, 26, 2)
        except:
            pass

        try:
            self.bulle_server.send(False, 26, 2)
        except:
            pass
            

bot = TFMBot("Anatidae", "sgfdhfgdh", "testingroompls", 0, True) # 0 = EN
bot.go()
        

        
        
