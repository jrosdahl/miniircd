from datetime import datetime
import re
import socket
import string
import time
from utils import irc_lower
from utils import VERSION


class Client(object):
    __linesep_regexp = re.compile(r"\r?\n")
    # The RFC limit for nicknames is 9 characters, but what the heck.
    __valid_nickname_regexp = re.compile(
        r"^[][\`_^{|}A-Za-z][][\`_^{|}A-Za-z0-9]{0,50}$")
    __valid_channelname_regexp = re.compile(
        r"^[&#+!][^\x00\x07\x0a\x0d ,:]{0,50}$")

    def __init__(self, server, socket):
        global ssl_available

        self.server = server
        self.socket = socket
        self.channels = {}  # irc_lower(Channel name) --> Channel
        self.nickname = None
        self.user = None
        self.realname = None
        self.away = False
        (self.host, self.port) = socket.getpeername()
        self.__timestamp = time.time()
        self.__readbuffer = ""
        self.__writebuffer = ""
        self.__sent_ping = False
        if self.server.password:
            self.__handle_command = self.__pass_handler
        else:
            self.__handle_command = self.__registration_handler

    def get_prefix(self):
        return "%s!%s@%s" % (self.nickname, self.user, self.host)
    prefix = property(get_prefix)

    def check_aliveness(self):
        now = time.time()
        if self.__timestamp + 180 < now:
            self.disconnect("ping timeout")
            return
        if not self.__sent_ping and self.__timestamp + 90 < now:
            if self.__handle_command == self.__command_handler:
                # Registered.
                self.message("PING :%s" % self.server.name)
                self.__sent_ping = True
            else:
                # Not registered.
                self.disconnect("ping timeout")

    def write_queue_size(self):
        return len(self.__writebuffer)

    def __parse_read_buffer(self):
        lines = self.__linesep_regexp.split(self.__readbuffer)
        self.__readbuffer = lines[-1]
        lines = lines[:-1]
        for line in lines:
            if not line:
                # Empty line. Ignore.
                continue
            x = line.split(" ", 1)
            command = x[0].upper()
            if len(x) == 1:
                arguments = []
            else:
                if len(x[1]) > 0 and x[1][0] == ":":
                    arguments = [x[1][1:]]
                else:
                    y = string.split(x[1], " :", 1)
                    arguments = string.split(y[0])
                    if len(y) == 2:
                        arguments.append(y[1])
            self.__handle_command(command, arguments)

    def __pass_handler(self, command, arguments):
        server = self.server
        if command == "PASS":
            if len(arguments) == 0:
                self.reply_461("PASS")
            else:
                if arguments[0].lower() == server.password:
                    self.__handle_command = self.__registration_handler
                else:
                    self.reply("464 :Password incorrect")
        elif command == "QUIT":
            self.disconnect("Client quit")
            return

    def __registration_handler(self, command, arguments):
        server = self.server
        if command == "NICK":
            if len(arguments) < 1:
                self.reply("431 :No nickname given")
                return
            nick = arguments[0]
            if server.get_client(nick):
                self.reply("433 * %s :Nickname is already in use" % nick)
            elif not self.__valid_nickname_regexp.match(nick):
                self.reply("432 * %s :Erroneous nickname" % nick)
            else:
                self.nickname = nick
                server.client_changed_nickname(self, None)
        elif command == "USER":
            if len(arguments) < 4:
                self.reply_461("USER")
                return
            self.user = arguments[0]
            self.realname = arguments[3]
        elif command == "QUIT":
            self.disconnect("Client quit")
            return
        if self.nickname and self.user:
            self.reply("001 %s :Hi, welcome to IRC" % self.nickname)
            self.reply("002 %s :Your host is %s, running version miniircd-%s"
                       % (self.nickname, server.name, VERSION))
            self.reply("003 %s :This server was created sometime"
                       % self.nickname)
            self.reply("004 %s :%s miniircd-%s o o"
                       % (self.nickname, server.name, VERSION))
            self.send_lusers()
            self.send_motd()
            self.__handle_command = self.__command_handler

    def __command_handler(self, command, arguments):
        def away_handler():
            if not arguments:
                self.away = False
                self.reply("305 %s :You are no longer marked as being away"
                           % self.nickname)
            else:
                self.away = arguments[0]
                self.reply("306 %s :You have been marked as being away"
                           % self.nickname)

        def ison_handler():
            if len(arguments) < 1:
                self.reply_461("ISON")
                return
            nicks = arguments
            online = [n for n in nicks if server.get_client(n)]
            self.reply("303 %s :%s" % (self.nickname, " ".join(online)))

        def join_handler():
            if len(arguments) < 1:
                self.reply_461("JOIN")
                return
            if arguments[0] == "0":
                for (channelname, channel) in self.channels.items():
                    self.message_channel(channel, "PART", channelname, True)
                    self.channel_log(channel, "left", meta=True)
                    server.remove_member_from_channel(self, channelname)
                self.channels = {}
                return
            channelnames = arguments[0].split(",")
            if len(arguments) > 1:
                keys = arguments[1].split(",")
            else:
                keys = []
            keys.extend((len(channelnames) - len(keys)) * [None])
            for (i, channelname) in enumerate(channelnames):
                if irc_lower(channelname) in self.channels:
                    continue
                if not valid_channel_re.match(channelname):
                    self.reply_403(channelname)
                    continue
                channel = server.get_channel(channelname)
                if channel.key is not None and channel.key != keys[i]:
                    self.reply(
                        "475 %s %s :Cannot join channel (+k) - bad key"
                        % (self.nickname, channelname))
                    continue
                channel.add_member(self)
                self.channels[irc_lower(channelname)] = channel
                self.message_channel(channel, "JOIN", channelname, True)
                self.channel_log(channel, "joined", meta=True)
                if channel.topic:
                    self.reply("332 %s %s :%s"
                               % (self.nickname, channel.name, channel.topic))
                else:
                    self.reply("331 %s %s :No topic is set"
                               % (self.nickname, channel.name))
                self.reply("353 %s = %s :%s"
                           % (self.nickname,
                              channelname,
                              " ".join(sorted(x.nickname
                                              for x in channel.members))))
                self.reply("366 %s %s :End of NAMES list"
                           % (self.nickname, channelname))

        def list_handler():
            if len(arguments) < 1:
                channels = server.channels.values()
            else:
                channels = []
                for channelname in arguments[0].split(","):
                    if server.has_channel(channelname):
                        channels.append(server.get_channel(channelname))
            channels.sort(key=lambda x: x.name)
            for channel in channels:
                self.reply("322 %s %s %d :%s"
                           % (self.nickname, channel.name,
                              len(channel.members), channel.topic))
            self.reply("323 %s :End of LIST" % self.nickname)

        def lusers_handler():
            self.send_lusers()

        def mode_handler():
            if len(arguments) < 1:
                self.reply_461("MODE")
                return
            targetname = arguments[0]
            if server.has_channel(targetname):
                channel = server.get_channel(targetname)
                if len(arguments) < 2:
                    if channel.key:
                        modes = "+k"
                        if irc_lower(channel.name) in self.channels:
                            modes += " %s" % channel.key
                    else:
                        modes = "+"
                    self.reply("324 %s %s %s"
                               % (self.nickname, targetname, modes))
                    return
                flag = arguments[1]
                if flag == "+k":
                    if len(arguments) < 3:
                        self.reply_461("MODE")
                        return
                    key = arguments[2]
                    if irc_lower(channel.name) in self.channels:
                        channel.key = key
                        self.message_channel(
                            channel, "MODE", "%s +k %s" % (channel.name, key),
                            True)
                        self.channel_log(
                            channel, "set channel key to %s" % key, meta=True)
                    else:
                        self.reply("442 %s :You're not on that channel"
                                   % targetname)
                elif flag == "-k":
                    if irc_lower(channel.name) in self.channels:
                        channel.key = None
                        self.message_channel(
                            channel, "MODE", "%s -k" % channel.name,
                            True)
                        self.channel_log(
                            channel, "removed channel key", meta=True)
                    else:
                        self.reply("442 %s :You're not on that channel"
                                   % targetname)
                else:
                    self.reply("472 %s %s :Unknown MODE flag"
                               % (self.nickname, flag))
            elif targetname == self.nickname:
                if len(arguments) == 1:
                    self.reply("221 %s +" % self.nickname)
                else:
                    self.reply("501 %s :Unknown MODE flag" % self.nickname)
            else:
                self.reply_403(targetname)

        def motd_handler():
            self.send_motd()

        def nick_handler():
            if len(arguments) < 1:
                self.reply("431 :No nickname given")
                return
            newnick = arguments[0]
            client = server.get_client(newnick)
            if newnick == self.nickname:
                pass
            elif client and client is not self:
                self.reply("433 %s %s :Nickname is already in use"
                           % (self.nickname, newnick))
            elif not self.__valid_nickname_regexp.match(newnick):
                self.reply("432 %s %s :Erroneous Nickname"
                           % (self.nickname, newnick))
            else:
                for x in self.channels.values():
                    self.channel_log(
                        x, "changed nickname to %s" % newnick, meta=True)
                oldnickname = self.nickname
                self.nickname = newnick
                server.client_changed_nickname(self, oldnickname)
                self.message_related(
                    ":%s!%s@%s NICK %s"
                    % (oldnickname, self.user, self.host, self.nickname),
                    True)

        def notice_and_privmsg_handler():
            if len(arguments) == 0:
                self.reply("411 %s :No recipient given (%s)"
                           % (self.nickname, command))
                return
            if len(arguments) == 1:
                self.reply("412 %s :No text to send" % self.nickname)
                return
            targetname = arguments[0]
            message = arguments[1]
            client = server.get_client(targetname)
            if client:
                if client.away:
                    self.reply("301 %s %s :%s"
                               % (self.nickname, client.nickname, client.away))
                client.message(":%s %s %s :%s"
                               % (self.prefix, command, targetname, message))
            elif server.has_channel(targetname):
                channel = server.get_channel(targetname)
                self.message_channel(
                    channel, command, "%s :%s" % (channel.name, message))
                self.channel_log(channel, message)
            else:
                self.reply("401 %s %s :No such nick/channel"
                           % (self.nickname, targetname))

        def part_handler():
            if len(arguments) < 1:
                self.reply_461("PART")
                return
            if len(arguments) > 1:
                partmsg = arguments[1]
            else:
                partmsg = self.nickname
            for channelname in arguments[0].split(","):
                if not valid_channel_re.match(channelname):
                    self.reply_403(channelname)
                elif not irc_lower(channelname) in self.channels:
                    self.reply("442 %s %s :You're not on that channel"
                               % (self.nickname, channelname))
                else:
                    channel = self.channels[irc_lower(channelname)]
                    self.message_channel(
                        channel, "PART", "%s :%s" % (channelname, partmsg),
                        True)
                    self.channel_log(channel, "left (%s)" % partmsg, meta=True)
                    del self.channels[irc_lower(channelname)]
                    server.remove_member_from_channel(self, channelname)

        def ping_handler():
            if len(arguments) < 1:
                self.reply("409 %s :No origin specified" % self.nickname)
                return
            self.reply("PONG %s :%s" % (server.name, arguments[0]))

        def pong_handler():
            pass

        def quit_handler():
            if len(arguments) < 1:
                quitmsg = self.nickname
            else:
                quitmsg = arguments[0]
            self.disconnect(quitmsg)

        def topic_handler():
            if len(arguments) < 1:
                self.reply_461("TOPIC")
                return
            channelname = arguments[0]
            channel = self.channels.get(irc_lower(channelname))
            if channel:
                if len(arguments) > 1:
                    newtopic = arguments[1]
                    channel.topic = newtopic
                    self.message_channel(
                        channel, "TOPIC", "%s :%s" % (channelname, newtopic),
                        True)
                    self.channel_log(
                        channel, "set topic to %r" % newtopic, meta=True)
                else:
                    if channel.topic:
                        self.reply("332 %s %s :%s"
                                   % (self.nickname, channel.name,
                                      channel.topic))
                    else:
                        self.reply("331 %s %s :No topic is set"
                                   % (self.nickname, channel.name))
            else:
                self.reply("442 %s :You're not on that channel" % channelname)

        def wallops_handler():
            if len(arguments) < 1:
                self.reply_461(command)
            message = arguments[0]
            for client in server.clients.values():
                client.message(":%s NOTICE %s :Global notice: %s"
                               % (self.prefix, client.nickname, message))

        def who_handler():
            if len(arguments) < 1:
                return
            targetname = arguments[0]
            if server.has_channel(targetname):
                channel = server.get_channel(targetname)
                for member in channel.members:
                    self.reply("352 %s %s %s %s %s %s H :0 %s"
                               % (self.nickname, targetname, member.user,
                                  member.host, server.name, member.nickname,
                                  member.realname))
                self.reply("315 %s %s :End of WHO list"
                           % (self.nickname, targetname))

        def whois_handler():
            if len(arguments) < 1:
                return
            username = arguments[0]
            user = server.get_client(username)
            if user:
                self.reply("311 %s %s %s %s * :%s"
                           % (self.nickname, user.nickname, user.user,
                              user.host, user.realname))
                self.reply("312 %s %s %s :%s"
                           % (self.nickname, user.nickname, server.name,
                              server.name))
                if user.away:
                    self.reply("301 %s %s :%s"
                               % (self.nickname, user.nickname, user.away))
                if len(user.channels) != 0:
                    self.reply("319 %s %s :%s"
                               % (self.nickname, user.nickname,
                                  " ".join(user.channels)))
                self.reply("318 %s %s :End of WHOIS list"
                           % (self.nickname, user.nickname))
            else:
                self.reply("401 %s %s :No such nick"
                           % (self.nickname, username))

        handler_table = {
            "AWAY": away_handler,
            "ISON": ison_handler,
            "JOIN": join_handler,
            "LIST": list_handler,
            "LUSERS": lusers_handler,
            "MODE": mode_handler,
            "MOTD": motd_handler,
            "NICK": nick_handler,
            "NOTICE": notice_and_privmsg_handler,
            "PART": part_handler,
            "PING": ping_handler,
            "PONG": pong_handler,
            "PRIVMSG": notice_and_privmsg_handler,
            "QUIT": quit_handler,
            "TOPIC": topic_handler,
            "WALLOPS": wallops_handler,
            "WHO": who_handler,
            "WHOIS": whois_handler,
        }
        server = self.server
        valid_channel_re = self.__valid_channelname_regexp
        try:
            handler_table[command]()
        except KeyError:
            self.reply("421 %s %s :Unknown command" % (self.nickname, command))

    def socket_readable_notification(self):
        try:
            data = self.socket.recv(2 ** 10)
            self.server.print_debug(
                "[%s:%d] -> %r" % (self.host, self.port, data))
            quitmsg = "EOT"
        except socket.error, x:
            data = ""
            quitmsg = x
        if data:
            self.__readbuffer += data
            self.__parse_read_buffer()
            self.__timestamp = time.time()
            self.__sent_ping = False
        else:
            self.disconnect(quitmsg)

    def socket_writable_notification(self):
        try:
            sent = self.socket.send(self.__writebuffer)
            self.server.print_debug(
                "[%s:%d] <- %r" % (
                    self.host, self.port, self.__writebuffer[:sent]))
            self.__writebuffer = self.__writebuffer[sent:]
        except socket.error, x:
            self.disconnect(x)

    def disconnect(self, quitmsg):
        self.message("ERROR :%s" % quitmsg)
        self.server.print_info(
            "Disconnected connection from %s:%s (%s)." % (
                self.host, self.port, quitmsg))
        self.socket.close()
        self.server.remove_client(self, quitmsg)

    def message(self, msg):
        self.__writebuffer += msg + "\r\n"

    def reply(self, msg):
        self.message(":%s %s" % (self.server.name, msg))

    def reply_403(self, channel):
        self.reply("403 %s %s :No such channel" % (self.nickname, channel))

    def reply_461(self, command):
        nickname = self.nickname or "*"
        self.reply("461 %s %s :Not enough parameters" % (nickname, command))

    def message_channel(self, channel, command, message, include_self=False):
        line = ":%s %s %s" % (self.prefix, command, message)
        for client in channel.members:
            if client != self or include_self:
                client.message(line)

    def channel_log(self, channel, message, meta=False):
        if not self.server.logdir:
            return
        if meta:
            format = "[%s] * %s %s\n"
        else:
            format = "[%s] <%s> %s\n"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        logname = channel.name.replace("_", "__").replace("/", "_")
        fp = open("%s/%s.log" % (self.server.logdir, logname), "a")
        fp.write(format % (timestamp, self.nickname, message))
        fp.close()

    def message_related(self, msg, include_self=False):
        clients = set()
        if include_self:
            clients.add(self)
        for channel in self.channels.values():
            clients |= channel.members
        if not include_self:
            clients.discard(self)
        for client in clients:
            client.message(msg)

    def send_lusers(self):
        self.reply("251 %s :There are %d users and 0 services on 1 server"
                   % (self.nickname, len(self.server.clients)))

    def send_motd(self):
        server = self.server
        motdlines = server.get_motd_lines()
        if motdlines:
            self.reply("375 %s :- %s Message of the day -"
                       % (self.nickname, server.name))
            for line in motdlines:
                self.reply("372 %s :- %s" % (self.nickname, line.rstrip()))
            self.reply("376 %s :End of /MOTD command" % self.nickname)
        else:
            self.reply("422 %s :MOTD File is missing" % self.nickname)


