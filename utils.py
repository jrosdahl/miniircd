import os
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

