import os
import select
import socket
import time
import sys

from channel import Channel
from client import Client
from utils import create_directory
from utils import irc_lower

try:
    import ssl
    ssl_available = True
except ImportError:
    ssl_available = False


class Server(object):
    def __init__(self, options):
        self.ports = options.ports
        self.password = options.password
        self.motdfile = options.motd
        self.verbose = options.verbose
        self.debug = options.debug
        self.logdir = options.logdir
        self.ssl_pem_file = options.ssl_pem_file
        self.statedir = options.statedir
        self.name = socket.getfqdn()[:63]  # Server name limit from the RFC.
        self.channels = {}  # irc_lower(Channel name) --> Channel instance.
        self.clients = {}  # Socket --> Client instance.
        self.nicknames = {}  # irc_lower(Nickname) --> Client instance.
        if self.logdir:
            create_directory(self.logdir)
        if self.statedir:
            create_directory(self.statedir)

    def daemonize(self):
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError:
            sys.exit(1)
        os.setsid()
        try:
            pid = os.fork()
            if pid > 0:
                self.print_info("PID: %d" % pid)
                sys.exit(0)
        except OSError:
            sys.exit(1)
        os.chdir("/")
        os.umask(0)
        dev_null = open("/dev/null", "r+")
        os.dup2(dev_null.fileno(), sys.stdout.fileno())
        os.dup2(dev_null.fileno(), sys.stderr.fileno())
        os.dup2(dev_null.fileno(), sys.stdin.fileno())

    def get_client(self, nickname):
        return self.nicknames.get(irc_lower(nickname))

    def has_channel(self, name):
        return irc_lower(name) in self.channels

    def get_channel(self, channelname):
        if irc_lower(channelname) in self.channels:
            channel = self.channels[irc_lower(channelname)]
        else:
            channel = Channel(self, channelname)
            self.channels[irc_lower(channelname)] = channel
        return channel

    def get_motd_lines(self):
        if self.motdfile:
            try:
                return open(self.motdfile).readlines()
            except IOError:
                return ["Could not read MOTD file %r." % self.motdfile]
        else:
            return []

    def print_info(self, msg):
        if self.verbose:
            print msg
            sys.stdout.flush()

    def print_debug(self, msg):
        if self.debug:
            print msg
            sys.stdout.flush()

    def print_error(self, msg):
        sys.stderr.write("%s\n" % msg)

    def client_changed_nickname(self, client, oldnickname):
        if oldnickname:
            del self.nicknames[irc_lower(oldnickname)]
        self.nicknames[irc_lower(client.nickname)] = client

    def remove_member_from_channel(self, client, channelname):
        if irc_lower(channelname) in self.channels:
            channel = self.channels[irc_lower(channelname)]
            channel.remove_client(client)

    def remove_client(self, client, quitmsg):
        client.message_related(":%s QUIT :%s" % (client.prefix, quitmsg))
        for x in client.channels.values():
            client.channel_log(x, "quit (%s)" % quitmsg, meta=True)
            x.remove_client(client)
        if client.nickname \
               and irc_lower(client.nickname) in self.nicknames:
            del self.nicknames[irc_lower(client.nickname)]
        del self.clients[client.socket]

    def remove_channel(self, channel):
        del self.channels[irc_lower(channel.name)]

    def start(self):
        serversockets = []
        for port in self.ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("", port))
            except socket.error, x:
                self.print_error("Could not bind port %s: %s." % (port, x))
                sys.exit(1)
            s.listen(5)
            serversockets.append(s)
            del s
            self.print_info("Listening on port %d." % port)
        last_aliveness_check = time.time()
        while True:
            (iwtd, owtd, ewtd) = select.select(
                serversockets + [x.socket for x in self.clients.values()],
                [x.socket for x in self.clients.values()
                          if x.write_queue_size() > 0],
                [],
                10)
            for x in iwtd:
                if x in self.clients:
                    self.clients[x].socket_readable_notification()
                else:
                    (conn, addr) = x.accept()
                    conn_accepted = True
                    try:
                        sock = conn
                        if ssl_available and self.ssl_pem_file:
                            sock = ssl.wrap_socket(
                                       conn,
                                       server_side = True,
                                       certfile    = self.ssl_pem_file,
                                       keyfile     = self.ssl_pem_file,
                                       ssl_version = ssl.PROTOCOL_SSLv23)
                        client = Client(self, sock)
                        self.clients[sock] = client
                    except ssl.SSLError, e:
                        conn_accepted = False
                        self.print_error("SSL ERROR: %s" % e)
                        conn.close()
                    if conn_accepted:
                        self.print_info("Accepted connection from %s:%s." % (
                            addr[0], addr[1]))
            for x in owtd:
                if x in self.clients: # client may have been disconnected
                    self.clients[x].socket_writable_notification()
            now = time.time()
            if last_aliveness_check + 10 < now:
                for client in self.clients.values():
                    client.check_aliveness()
                last_aliveness_check = now


