#! /usr/bin/env python

import os
import re
import shutil
import signal
import socket
import tempfile
import time
from nose.tools import assert_not_in, assert_true

SERVER_PORT = 16667


class ServerFixture(object):
    def setUp(self, persistent=False):
        if persistent:
            self.state_dir = tempfile.mkdtemp()
        else:
            self.state_dir = None
        pid = os.fork()
        if pid == 0:
            # Child.
            arguments = [
                "miniircd",
                # "--debug",
                "--ports=%d" % SERVER_PORT,
                ]
            if persistent:
                arguments.append("--state-dir=%s" % self.state_dir)
            os.execv("./miniircd", arguments)
        # Parent.
        self.child_pid = pid
        self.connections = {}  # nick -> fp

    def connect(self, nick):
        assert_not_in(nick, self.connections)
        s = socket.socket()
        tries_left = 100
        while tries_left > 0:
            try:
                s.connect(("localhost", SERVER_PORT))
                break
            except socket.error:
                tries_left -= 1
                time.sleep(0.01)
        self.connections[nick] = s.makefile(mode="rw")
        self.send(nick, "NICK %s" % nick)
        self.send(nick, "USER %s * * %s" % (nick, nick))
        self.expect(nick, r":local\S+ 001 %s :.*" % nick)
        self.expect(nick, r":local\S+ 002 %s :.*" % nick)
        self.expect(nick, r":local\S+ 003 %s :.*" % nick)
        self.expect(nick, r":local\S+ 004 %s .*" % nick)
        self.expect(nick, r":local\S+ 251 %s :.*" % nick)
        self.expect(nick, r":local\S+ 422 %s :.*" % nick)

    def shutDown(self):
        os.kill(self.child_pid, signal.SIGTERM)
        os.waitpid(self.child_pid, 0)
        if self.state_dir:
            try:
                shutil.rmtree(self.state_dir)
            except IOError:
                pass

    def tearDown(self):
        self.shutDown()
        for x in self.connections.values():
            x.close()

    def send(self, nick, message):
        self.connections[nick].write(message + "\r\n")
        self.connections[nick].flush()

    def expect(self, nick, regexp):
        def timeout_handler(signum, frame):
            raise AssertionError("timeout while waiting for %r" % regexp)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1)  # Give the server 1 second to respond
        line = self.connections[nick].readline().rstrip()
        signal.alarm(0)  # Cancel the alarm
        regexp = ("^%s$" % regexp).replace(r"local\S+", socket.getfqdn())
        m = re.match(regexp, line)
        if m:
            return m
        else:
            assert_true(False, "Regexp %r didn't match %r" % (regexp, line))


class TwoClientsTwoChannelsFixture(ServerFixture):
    def setUp(self):
        ServerFixture.setUp(self)
        try:
            self.connect("apa")
            self.send("apa", "JOIN #fisk,#brugd")
            self.expect("apa", r":apa!apa@127.0.0.1 JOIN #fisk")
            self.expect("apa", r":local\S+ 331 apa #fisk :.*")
            self.expect("apa", r":local\S+ 353 apa = #fisk :apa")
            self.expect("apa", r":local\S+ 366 apa #fisk :.*")
            self.expect("apa", r":apa!apa@127.0.0.1 JOIN #brugd")
            self.expect("apa", r":local\S+ 331 apa #brugd :.*")
            self.expect("apa", r":local\S+ 353 apa = #brugd :apa")
            self.expect("apa", r":local\S+ 366 apa #brugd :.*")

            self.connect("lemur")
            self.send("lemur", "JOIN #fisk,#brugd unused1,unused2")
            self.expect("lemur", r":lemur!lemur@127.0.0.1 JOIN #fisk")
            self.expect("lemur", r":local\S+ 331 lemur #fisk :.*")
            self.expect("lemur", r":local\S+ 353 lemur = #fisk :apa lemur")
            self.expect("lemur", r":local\S+ 366 lemur #fisk :.*")
            self.expect("lemur", r":lemur!lemur@127.0.0.1 JOIN #brugd")
            self.expect("lemur", r":local\S+ 331 lemur #brugd :.*")
            self.expect("lemur", r":local\S+ 353 lemur = #brugd :apa lemur")
            self.expect("lemur", r":local\S+ 366 lemur #brugd :.*")

            self.expect("apa", r":lemur!lemur@127.0.0.1 JOIN #fisk")
            self.expect("apa", r":lemur!lemur@127.0.0.1 JOIN #brugd")
        except:
            self.shutDown()
            raise


class TestBasicStuff(ServerFixture):
    def test_registration(self):
        self.connect("apa")

    def test_bad_ping(self):
        self.connect("apa")
        self.send("apa", "PING")
        self.expect("apa", r"\S+ 409 apa :.*")

    def test_good_ping(self):
        self.connect("apa")
        self.send("apa", "PING :fisk")
        self.expect("apa", r":local\S+ PONG \S+ :fisk")

    def test_unknown_command(self):
        self.connect("apa")
        self.send("apa", "FISK fisk")
        self.expect("apa", r":local\S+ 421 apa FISK :.*")

    def test_away(self):
        self.connect("apa")
        self.send("apa", "AWAY :gone fishing")
        # Currently no reply.

    def test_argumentless_away(self):
        self.connect("apa")
        self.send("apa", "AWAY")
        # Currently no reply.

    def test_argumentless_join(self):
        self.connect("apa")
        self.send("apa", "JOIN")
        self.expect("apa", r":local\S+ 461 apa JOIN :Not enough parameters")

    def test_argumentless_list(self):
        self.connect("apa")
        self.send("apa", "LIST")
        self.expect("apa", r":local\S+ 323 apa :End of LIST")

    def test_argumentless_mode(self):
        self.connect("apa")
        self.send("apa", "MODE")
        self.expect("apa", r":local\S+ 461 apa MODE :Not enough parameters")

    def test_argumentless_motd(self):
        self.connect("apa")
        self.send("apa", "MOTD")
        self.expect("apa", r":local\S+ 422 apa :MOTD File is missing")

    def test_argumentless_nick(self):
        self.connect("apa")
        self.send("apa", "NICK")
        self.expect("apa", r":local\S+ 431 :No nickname given")

    def test_argumentless_notice(self):
        self.connect("apa")
        self.send("apa", "NOTICE")
        self.expect("apa", r":local\S+ 411 apa :No recipient given \(NOTICE\)")

    def test_privmsg_to_user(self):
        self.connect("apa")
        self.connect("lemur")
        self.send("apa", "PRIVMSG lemur :fisk")
        self.expect("lemur", r":apa!apa@127.0.0.1 PRIVMSG lemur :fisk")

    def test_privmsg_to_nobody(self):
        self.connect("apa")
        self.send("apa", "PRIVMSG lemur :fisk")
        self.expect("apa", r":local\S+ 401 apa lemur :.*")

    def test_notice_to_user(self):
        self.connect("apa")
        self.connect("lemur")
        self.send("apa", "NOTICE lemur :fisk")
        self.expect("lemur", r":apa!apa@127.0.0.1 NOTICE lemur :fisk")

    def test_notice_to_nobody(self):
        self.connect("apa")
        self.send("apa", "NOTICE lemur :fisk")
        self.expect("apa", r":local\S+ 401 apa lemur :.*")

    def test_join_and_part_one_user(self):
        self.connect("apa")

        self.send("apa", "LIST")
        self.expect("apa", r":local\S+ 323 apa :.*")

        self.send("apa", "JOIN #fisk")
        self.expect("apa", r":apa!apa@127.0.0.1 JOIN #fisk")
        self.expect("apa", r":local\S+ 331 apa #fisk :.*")
        self.expect("apa", r":local\S+ 353 apa = #fisk :apa")
        self.expect("apa", r":local\S+ 366 apa #fisk :.*")

        self.send("apa", "LIST")
        self.expect("apa", r":local\S+ 322 apa #fisk 1 :")
        self.expect("apa", r":\S+ 323 apa :.*")

        self.send("apa", "PART #fisk")
        self.expect("apa", r":apa!apa@127.0.0.1 PART #fisk :apa")

        self.send("apa", "LIST")
        self.expect("apa", r":\S+ 323 apa :.*")

    def test_join_and_part_two_users(self):
        self.connect("apa")
        self.send("apa", "JOIN #fisk")
        self.expect("apa", r":apa!apa@127.0.0.1 JOIN #fisk")
        self.expect("apa", r":local\S+ 331 apa #fisk :.*")
        self.expect("apa", r":local\S+ 353 apa = #fisk :apa")
        self.expect("apa", r":local\S+ 366 apa #fisk :.*")

        self.connect("lemur")
        self.send("lemur", "JOIN #fisk")
        self.expect("lemur", r":lemur!lemur@127.0.0.1 JOIN #fisk")
        self.expect("lemur", r":local\S+ 331 lemur #fisk :.*")
        self.expect("lemur", r":local\S+ 353 lemur = #fisk :apa lemur")
        self.expect("lemur", r":local\S+ 366 lemur #fisk :.*")
        self.expect("apa", r":lemur!lemur@127.0.0.1 JOIN #fisk")

        self.send("lemur", "PART #fisk :boa")
        self.expect("lemur", r":lemur!lemur@127.0.0.1 PART #fisk :boa")
        self.expect("apa", r":lemur!lemur@127.0.0.1 PART #fisk :boa")

    def test_join_and_name_many_users(self):
        base_nick = 'A' * 49
        # :FQDN 353 nick = #fisk :
        base_len = len(socket.getfqdn()) + 66

        one_line = (512 - base_len) // 50
        nick_list_one = []
        for i in range(one_line):
            long_nick = '%s%d' % (base_nick, i)
            nick_list_one.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")
            self.expect(
                long_nick,
                r":%(nick)s!%(nick)s@127.0.0.1 JOIN #fisk" % {
                    'nick': long_nick
                }
            )
            self.expect(long_nick, r":local\S+ 331 %s #fisk :.*" % long_nick)
            self.expect(
                long_nick,
                r":local\S+ 353 %s = #fisk :%s" % (
                    long_nick, ' '.join(nick_list_one)
                )
            )
            self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

        nick_list_two = []
        for i in range(10 - one_line):
            long_nick = '%s%d' % (base_nick, one_line + i)
            nick_list_two.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")
            self.expect(
                long_nick,
                r":%(nick)s!%(nick)s@127.0.0.1 JOIN #fisk" % {
                    'nick': long_nick
                }
            )
            self.expect(long_nick, r":local\S+ 331 %s #fisk :.*" % long_nick)
            self.expect(
                long_nick,
                r":local\S+ 353 %s = #fisk :%s" % (
                    long_nick, ' '.join(nick_list_one)
                )
            )
            self.expect(
                long_nick,
                r":local\S+ 353 %s = #fisk :%s" % (
                    long_nick, ' '.join(nick_list_two)
                )
            )
            self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

    def test_join_and_request_names(self):
        base_nick = 'A' * 49
        # :FQDN 353 nick = #fisk :
        base_len = len(socket.getfqdn()) + 66

        one_line = (512 - base_len) / 50
        nick_list_one = []
        for i in range(one_line):
            long_nick = '%s%d' % (base_nick, i)
            nick_list_one.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")

        nick_list_two = []
        for i in range(10 - one_line):
            long_nick = '%s%d' % (base_nick, one_line + i)
            nick_list_two.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")

        self.expect(
            long_nick,
            r":%(nick)s!%(nick)s@127.0.0.1 JOIN #fisk" % {
                'nick': long_nick
            }
        )
        self.expect(long_nick, r":local\S+ 331 %s #fisk :.*" % long_nick)
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_one)
            )
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_two)
            )
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

        # Request for one channel
        self.send(long_nick, "NAMES #fisk")
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_one)
            )
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_two)
            )
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

        # Request no channel
        self.send(long_nick, "NAMES")
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_one)
            )
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_two)
            )
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

        # Request for multiple channels
        self.send(long_nick, "JOIN #test")
        self.expect(
            long_nick,
            r":%(nick)s!%(nick)s@127.0.0.1 JOIN #test" % {
                'nick': long_nick
            }
        )
        self.expect(long_nick, r":local\S+ 331 %s #test :.*" % long_nick)
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #test :%s" % (
                long_nick, long_nick
            )
        )
        self.expect(long_nick, r":local\S+ 366 %s #test :.*" % long_nick)
        self.send(long_nick, "NAMES #fisk,#test")
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_one)
            )
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s" % (
                long_nick, ' '.join(nick_list_two)
            )
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #test :%s" % (
                long_nick, long_nick
            )
        )
        self.expect(long_nick, r":local\S+ 366 %s #test :.*" % long_nick)

    def test_ison(self):
        self.connect("apa")
        self.send("apa", "ISON apa lemur")
        self.expect("apa", r":local\S+ 303 apa :apa")

        self.connect("lemur")
        self.send("apa", "ISON apa lemur")
        self.expect("apa", r":local\S+ 303 apa :apa lemur")

    def test_lusers(self):
        self.connect("apa")
        self.send("apa", "lusers")
        self.expect("apa",
                    r":local\S+ 251 apa :There are \d+ users and \d+ services"
                    " on \d+ servers*")


class TestTwoChannelsStuff(TwoClientsTwoChannelsFixture):
    def test_privmsg_to_channel(self):
        self.send("apa", "PRIVMSG #fisk :lax")
        self.expect("lemur", r":apa!apa@127.0.0.1 PRIVMSG #fisk :lax")

    def test_notice_to_channel(self):
        self.send("apa", "NOTICE #fisk :lax")
        self.expect("lemur", r":apa!apa@127.0.0.1 NOTICE #fisk :lax")

    def test_get_empty_topic(self):
        self.send("apa", "TOPIC #fisk")
        self.expect("apa", r":local\S+ 331 apa #fisk :.*")

    def test_set_topic(self):
        self.send("apa", "TOPIC #fisk :sill")
        self.expect("apa", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")
        self.expect("lemur", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")

        self.send("apa", "LIST")
        self.expect("apa", r":local\S+ 322 apa #brugd 2 :")
        self.expect("apa", r":local\S+ 322 apa #fisk 2 :sill")
        self.expect("apa", r":\S+ 323 apa :.*")

    def test_get_topic(self):
        self.send("apa", "TOPIC #fisk :sill")
        self.expect("apa", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")
        self.expect("lemur", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")
        self.send("lemur", "TOPIC #fisk")
        self.expect("lemur", r":local\S+ 332 lemur #fisk :sill")

    def test_channel_key(self):
        self.send("apa", "MODE #fisk +k nors")
        self.expect("apa", r":apa!apa@127.0.0.1 MODE #fisk \+k nors")
        self.expect("lemur", r":apa!apa@127.0.0.1 MODE #fisk \+k nors")

        self.send("apa", "PART #fisk")
        self.expect("apa", r":apa!apa@127.0.0.1 PART #fisk :apa")
        self.expect("lemur", r":apa!apa@127.0.0.1 PART #fisk :apa")

        self.send("apa", "MODE #fisk -k")
        self.expect("apa", r":local\S+ 442 #fisk :.*")

        self.send("apa", "MODE #fisk +k boa")
        self.expect("apa", r":local\S+ 442 #fisk :.*")

        self.send("apa", "JOIN #fisk")
        self.expect("apa", r":local\S+ 475 apa #fisk :.*")

        self.send("apa", "JOIN #fisk nors")
        self.expect("apa", r":apa!apa@127.0.0.1 JOIN #fisk")
        self.expect("apa", r":local\S+ 331 apa #fisk :.*")
        self.expect("apa", r":local\S+ 353 apa = #fisk :apa lemur")
        self.expect("apa", r":local\S+ 366 apa #fisk :.*")
        self.expect("lemur", r":apa!apa@127.0.0.1 JOIN #fisk")

        self.send("apa", "MODE #fisk")
        self.expect("apa", r":local\S+ 324 apa #fisk \+k nors")


class TestPersistentState(ServerFixture):
    def setUp(self):
        ServerFixture.setUp(self, True)

    def test_persistent_channel_state(self):
        self.connect("apa")

        self.send("apa", "JOIN #fisk")
        self.expect("apa", r":apa!apa@127.0.0.1 JOIN #fisk")
        self.expect("apa", r":local\S+ 331 apa #fisk :.*")
        self.expect("apa", r":local\S+ 353 apa = #fisk :apa")
        self.expect("apa", r":local\S+ 366 apa #fisk :.*")

        self.send("apa", "TOPIC #fisk :molusk")
        self.expect("apa", r":apa!apa@127.0.0.1 TOPIC #fisk :molusk")

        self.send("apa", "MODE #fisk +k skunk")
        self.expect("apa", r":apa!apa@127.0.0.1 MODE #fisk \+k skunk")

        self.send("apa", "PART #fisk")
        self.expect("apa", r":apa!apa@127.0.0.1 PART #fisk :apa")

        self.send("apa", "MODE #fisk")
        self.expect("apa", r":local\S+ 403 apa #fisk :.*")

        self.send("apa", "JOIN #fisk")
        self.expect("apa", r":local\S+ 475 apa #fisk :.*")

        self.send("apa", "JOIN #fisk skunk")
        self.expect("apa", r":apa!apa@127.0.0.1 JOIN #fisk")
        self.expect("apa", r":local\S+ 332 apa #fisk :molusk")
        self.expect("apa", r":local\S+ 353 apa = #fisk :apa")
        self.expect("apa", r":local\S+ 366 apa #fisk :.*")

        self.send("apa", "MODE #fisk")
        self.expect("apa", r":local\S+ 324 apa #fisk \+k skunk")
