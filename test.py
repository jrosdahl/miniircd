#!/usr/bin/env python3

import os
import re
import shutil
import signal
import socket
import tempfile
import time
from nose.tools import assert_not_in, assert_true  # type:ignore
from types import FrameType
from typing import Dict, IO, Optional

SERVER_PORT = 16667


class ServerFixture:
    state_dir: Optional[str]

    def setUp(self, persistent: bool = False) -> None:
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
                arguments.append(f"--state-dir={self.state_dir}")
            os.execv("./miniircd", arguments)
        # Parent.
        self.child_pid = pid
        self.connections: Dict[str, IO] = {}  # nick -> fp

    def connect(self, nick: str) -> None:
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
        self.send(nick, f"NICK {nick}")
        self.send(nick, f"USER {nick} * * {nick}")
        self.expect(nick, rf":local\S+ 001 {nick} :.*")
        self.expect(nick, rf":local\S+ 002 {nick} :.*")
        self.expect(nick, rf":local\S+ 003 {nick} :.*")
        self.expect(nick, rf":local\S+ 004 {nick} .*")
        self.expect(nick, rf":local\S+ 251 {nick} :.*")
        self.expect(nick, rf":local\S+ 422 {nick} :.*")

    def shutDown(self) -> None:
        os.kill(self.child_pid, signal.SIGTERM)
        os.waitpid(self.child_pid, 0)
        if self.state_dir:
            try:
                shutil.rmtree(self.state_dir)
            except IOError:
                pass

    def tearDown(self) -> None:
        self.shutDown()
        for x in self.connections.values():
            x.close()

    def send(self, nick: str, message: str) -> None:
        self.connections[nick].write(message + "\r\n")
        self.connections[nick].flush()

    def expect(self, nick: str, regexp: str) -> None:
        def timeout_handler(signum: int, frame: FrameType) -> None:
            raise AssertionError("timeout while waiting for %r" % regexp)

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1)  # Give the server 1 second to respond
        line = self.connections[nick].readline().rstrip("\r\n")
        signal.alarm(0)  # Cancel the alarm
        regexp = f"^{regexp}$".replace(r"local\S+", socket.getfqdn())
        m = re.match(regexp, line)
        assert_true(m, f"Regexp {regexp!r} didn't match {line!r}")


class TwoClientsTwoChannelsFixture(ServerFixture):
    def setUp(self, persistent: bool = False) -> None:
        super().setUp(persistent)
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
        except Exception:
            self.shutDown()
            raise


class TestBasicStuff(ServerFixture):
    def test_registration(self) -> None:
        self.connect("apa")

    def test_bad_ping(self) -> None:
        self.connect("apa")
        self.send("apa", "PING")
        self.expect("apa", r"\S+ 409 apa :.*")

    def test_good_ping(self) -> None:
        self.connect("apa")
        self.send("apa", "PING :fisk")
        self.expect("apa", r":local\S+ PONG \S+ :fisk")

    def test_unknown_command(self) -> None:
        self.connect("apa")
        self.send("apa", "FISK fisk")
        self.expect("apa", r":local\S+ 421 apa FISK :.*")

    def test_away(self) -> None:
        self.connect("apa")
        self.send("apa", "AWAY :gone fishing")
        # Currently no reply.

    def test_argumentless_away(self) -> None:
        self.connect("apa")
        self.send("apa", "AWAY")
        # Currently no reply.

    def test_argumentless_join(self) -> None:
        self.connect("apa")
        self.send("apa", "JOIN")
        self.expect("apa", r":local\S+ 461 apa JOIN :Not enough parameters")

    def test_argumentless_list(self) -> None:
        self.connect("apa")
        self.send("apa", "LIST")
        self.expect("apa", r":local\S+ 323 apa :End of LIST")

    def test_argumentless_mode(self) -> None:
        self.connect("apa")
        self.send("apa", "MODE")
        self.expect("apa", r":local\S+ 461 apa MODE :Not enough parameters")

    def test_argumentless_motd(self) -> None:
        self.connect("apa")
        self.send("apa", "MOTD")
        self.expect("apa", r":local\S+ 422 apa :MOTD File is missing")

    def test_argumentless_nick(self) -> None:
        self.connect("apa")
        self.send("apa", "NICK")
        self.expect("apa", r":local\S+ 431 :No nickname given")

    def test_argumentless_notice(self) -> None:
        self.connect("apa")
        self.send("apa", "NOTICE")
        self.expect("apa", r":local\S+ 411 apa :No recipient given \(NOTICE\)")

    def test_privmsg_to_user(self) -> None:
        self.connect("apa")
        self.connect("lemur")
        self.send("apa", "PRIVMSG lemur :fisk")
        self.expect("lemur", r":apa!apa@127.0.0.1 PRIVMSG lemur :fisk")

    def test_privmsg_to_nobody(self) -> None:
        self.connect("apa")
        self.send("apa", "PRIVMSG lemur :fisk")
        self.expect("apa", r":local\S+ 401 apa lemur :.*")

    def test_notice_to_user(self) -> None:
        self.connect("apa")
        self.connect("lemur")
        self.send("apa", "NOTICE lemur :fisk")
        self.expect("lemur", r":apa!apa@127.0.0.1 NOTICE lemur :fisk")

    def test_notice_to_nobody(self) -> None:
        self.connect("apa")
        self.send("apa", "NOTICE lemur :fisk")
        self.expect("apa", r":local\S+ 401 apa lemur :.*")

    def test_join_and_part_one_user(self) -> None:
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

    def test_join_and_part_two_users(self) -> None:
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

    def test_join_and_name_many_users(self) -> None:
        base_nick = "A" * 49
        # :FQDN 353 nick = #fisk :
        base_len = len(socket.getfqdn()) + 66

        one_line = (512 - base_len) // 50
        nick_list_one = []
        for i in range(one_line):
            long_nick = f"{base_nick}{i}"
            nick_list_one.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")
            self.expect(
                long_nick, rf":{long_nick}!{long_nick}@127.0.0.1 JOIN #fisk"
            )
            self.expect(long_nick, rf":local\S+ 331 {long_nick} #fisk :.*")
            nicks = " ".join(nick_list_one)
            self.expect(
                long_nick, rf":local\S+ 353 {long_nick} = #fisk :{nicks}"
            )
            self.expect(long_nick, rf":local\S+ 366 {long_nick} #fisk :.*")

        nick_list_two = []
        for i in range(10 - one_line):
            long_nick = f"{base_nick}{one_line + i}"
            nick_list_two.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")
            self.expect(
                long_nick,
                r":%(nick)s!%(nick)s@127.0.0.1 JOIN #fisk"
                % {"nick": long_nick},
            )
            self.expect(long_nick, rf":local\S+ 331 {long_nick} #fisk :.*")
            nicks_one = " ".join(nick_list_one)
            self.expect(
                long_nick, rf":local\S+ 353 {long_nick} = #fisk :{nicks_one}"
            )
            nicks_two = " ".join(nick_list_two)
            self.expect(
                long_nick, rf":local\S+ 353 {long_nick} = #fisk :{nicks_two}"
            )
            self.expect(long_nick, rf":local\S+ 366 {long_nick} #fisk :.*")

    def test_join_and_request_names(self) -> None:
        base_nick = "A" * 49
        # :FQDN 353 nick = #fisk :
        base_len = len(socket.getfqdn()) + 66

        one_line = (512 - base_len) // 50
        nick_list_one = []
        for i in range(one_line):
            long_nick = "%s%d" % (base_nick, i)
            nick_list_one.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")

        nick_list_two = []
        for i in range(10 - one_line):
            long_nick = "%s%d" % (base_nick, one_line + i)
            nick_list_two.append(long_nick)
            self.connect(long_nick)
            self.send(long_nick, "JOIN #fisk")

        self.expect(
            long_nick,
            r":%(nick)s!%(nick)s@127.0.0.1 JOIN #fisk" % {"nick": long_nick},
        )
        self.expect(long_nick, r":local\S+ 331 %s #fisk :.*" % long_nick)
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_one)),
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_two)),
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

        # Request for one channel
        self.send(long_nick, "NAMES #fisk")
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_one)),
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_two)),
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

        # Request no channel
        self.send(long_nick, "NAMES")
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_one)),
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_two)),
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)

        # Request for multiple channels
        self.send(long_nick, "JOIN #test")
        self.expect(
            long_nick,
            r":%(nick)s!%(nick)s@127.0.0.1 JOIN #test" % {"nick": long_nick},
        )
        self.expect(long_nick, r":local\S+ 331 %s #test :.*" % long_nick)
        self.expect(
            long_nick, r":local\S+ 353 %s = #test :%s" % (long_nick, long_nick)
        )
        self.expect(long_nick, r":local\S+ 366 %s #test :.*" % long_nick)
        self.send(long_nick, "NAMES #fisk,#test")
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_one)),
        )
        self.expect(
            long_nick,
            r":local\S+ 353 %s = #fisk :%s"
            % (long_nick, " ".join(nick_list_two)),
        )
        self.expect(long_nick, r":local\S+ 366 %s #fisk :.*" % long_nick)
        self.expect(
            long_nick, r":local\S+ 353 %s = #test :%s" % (long_nick, long_nick)
        )
        self.expect(long_nick, r":local\S+ 366 %s #test :.*" % long_nick)

    def test_ison(self) -> None:
        self.connect("apa")
        self.send("apa", "ISON apa lemur")
        self.expect("apa", r":local\S+ 303 apa :apa")

        self.connect("lemur")
        self.send("apa", "ISON apa lemur")
        self.expect("apa", r":local\S+ 303 apa :apa lemur")

    def test_lusers(self) -> None:
        self.connect("apa")
        self.send("apa", "lusers")
        self.expect(
            "apa",
            r":local\S+ 251 apa :There are \d+ users and \d+ services"
            r" on \d+ servers*",
        )


class TestTwoChannelsStuff(TwoClientsTwoChannelsFixture):
    def test_privmsg_to_channel(self) -> None:
        self.send("apa", "PRIVMSG #fisk :lax")
        self.expect("lemur", r":apa!apa@127.0.0.1 PRIVMSG #fisk :lax")

    def test_notice_to_channel(self) -> None:
        self.send("apa", "NOTICE #fisk :lax")
        self.expect("lemur", r":apa!apa@127.0.0.1 NOTICE #fisk :lax")

    def test_get_empty_topic(self) -> None:
        self.send("apa", "TOPIC #fisk")
        self.expect("apa", r":local\S+ 331 apa #fisk :.*")

    def test_set_topic(self) -> None:
        self.send("apa", "TOPIC #fisk :sill")
        self.expect("apa", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")
        self.expect("lemur", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")

        self.send("apa", "LIST")
        self.expect("apa", r":local\S+ 322 apa #brugd 2 :")
        self.expect("apa", r":local\S+ 322 apa #fisk 2 :sill")
        self.expect("apa", r":\S+ 323 apa :.*")

    def test_get_topic(self) -> None:
        self.send("apa", "TOPIC #fisk :sill")
        self.expect("apa", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")
        self.expect("lemur", r":apa!apa@127.0.0.1 TOPIC #fisk :sill")
        self.send("lemur", "TOPIC #fisk")
        self.expect("lemur", r":local\S+ 332 lemur #fisk :sill")

    def test_channel_key(self) -> None:
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

    def test_whois(self) -> None:
        self.send("apa", "WHOIS bepa")
        self.expect("apa", r":local\S+ 401 apa bepa :No such nick")

        self.send("apa", "WHOIS apa")
        self.expect("apa", r":local\S+ 311 apa apa apa .+? \* :apa")
        self.expect("apa", r":local\S+ 312 apa apa .+")
        self.expect("apa", r":local\S+ 319 apa apa :#fisk #brugd ")
        self.expect("apa", r":local\S+ 318 apa apa :End of WHOIS list")

        self.send("apa", "PART #fisk,#brugd")
        self.expect("apa", r":apa!apa@127.0.0.1 PART #fisk :apa")
        self.expect("apa", r":apa!apa@127.0.0.1 PART #brugd :apa")

        self.send("apa", "WHOIS apa")
        self.expect("apa", r":local\S+ 311 apa apa apa .+? \* :apa")
        self.expect("apa", r":local\S+ 312 apa apa .+")
        self.expect("apa", r":local\S+ 319 apa apa :")
        self.expect("apa", r":local\S+ 318 apa apa :End of WHOIS list")


class TestPersistentState(ServerFixture):
    def setUp(self, persistent: bool = True) -> None:
        super().setUp(persistent)

    def test_persistent_channel_state(self) -> None:
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
