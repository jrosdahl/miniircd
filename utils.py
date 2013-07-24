import argparse
import os
import re
import string


VERSION = "0.5a1"


_alpha = "abcdefghijklmnopqrstuvwxyz"
_ircstring_translation = string.maketrans(
    string.upper(_alpha) + "[]\\^",
    _alpha + "{}|~")


def create_directory(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def irc_lower(s):
    return string.translate(s, _ircstring_translation)


class PortListType(object):
    def __call__(self, ports):
        portlist = []
        for port in re.split(r"[,]+", ports):
            try:
                portlist.append(int(port))
            except ValueError:
                raise argparse.ArgumentTypeError(
                        "bad port value, must be a valid port number, or a "
                        "list of valid port numbers separated by a comma")
        return portlist
