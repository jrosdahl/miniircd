miniircd -- A (very) simple Internet Relay Chat (IRC) server
============================================================

Description
-----------

miniircd is a small and limited IRC server written in Python. Despite its size,
it is a functional alternative to a full-blown ircd for private or internal
use. Installation is simple; no configuration is required.

This fork adds the ability to specify a chroot jail for the server process,
as well as the ability to set the user/group of the process. (*nix OSes only)

Features
--------

* Knows about the basic IRC protocol and commands.
* Easy installation.
* Basic SSL support.
* No configuration.
* No ident lookup (so that people behind firewalls that filter the ident port
  without sending NACK can connect without long timeouts).
* Reasonably secure when used with --chroot and --setuid

Limitations
-----------

* Can't connect to other IRC servers.
* Only knows the most basic IRC commands.
* No IRC operators.
* No channel operators.
* No user or channel modes except channel key.
* No reverse DNS lookup.
* No other mechanism to reject clients than requiring a password.

Requirements
------------

Python 2.5 or newer, Python 2.6 or newer when SSL is used.
Get it at http://www.python.org.

Installation
------------

None. Just run "./miniircd --help" (or "python miniircd --help") to get some
help.

Some Notes on --chroot and --setuid
-----------------------------------

In order to use the --chroot or --setuid options, you must be using an OS
that supports these functions (most \*nixes), and you must start the server
as root. Generally, you would not want to run just any random thing you've
grabbed from github and run it as root! Fortunately this script is short enough that the
average programmer can puruse it in a few minutes and determine whether or
not it is overtly malicious.

Creating a Jail for --chroot
----------------------------

If you want to run miniircd in a chroot jail, do something like the
following as root (only tested on Linux). Assuming your chroot jail is
going to be /var/jail/miniircd, first create some required device nodes:

```
# mkdir -p /var/jail/miniircd/dev
# mknod /var/jail/miniircd/dev/null c 1 3
# mknod /var/jail/miniircd/dev/random c 1 8
# mknod /var/jail/miniircd/dev/urandom c 1 9
# chmod 666 /var/jail/miniircd/dev/*
```
If you have a motd file or an SSL pem file, you'll need to put them in the
jail as well:

```
# cp miniircd.pem motd.txt /var/jail/miniircd
```

Remember to specify the paths for --statedir, --logdir, --motd, and
--ssl-pem-file from within the jail, e.g.:

```
# ./miniircd --statedir=/ --logdir=/ --motd=/motd.txt \
      --ssl-pem-file=/miniircd.pem --chroot=/var/jail/miniircd
```
Make sure your jail is writable by whatever user/group you are running
the server as. Also, keep your jail clean. Ideally it should only contain
the files mentioned above and the state/log files from miniircd. You should
**not** place the miniircd script itself, or any executables, in the jail.

```
# ls -alR /var/jail/miniircd
.:
total 36
drwxrwxr-x 3 nobody rezrov 4096 Jun 10 16:20 .
drwxr-xr-x 4 root   root   4096 Jun 10 18:40 ..
-rw------- 1 nobody nobody   26 Jun 10 16:20 #channel
-rw-r--r-- 1 nobody nobody 1414 Jun 10 16:51 #channel.log
drwxr-xr-x 2 root   root   4096 Jun 10 16:19 dev
-rw-r----- 1 rezrov nobody 5187 Jun  9 22:25 ircd.pem
-rw-r--r-- 1 rezrov nobody   17 Jun  9 22:26 motd.txt

./dev:
total 8
drwxr-xr-x 2 root   root   4096 Jun 10 16:19 .
drwxrwxr-x 3 nobody rezrov 4096 Jun 10 16:20 ..
crw-rw-rw- 1 root   root   1, 3 Jun 10 16:16 null
crw-rw-rw- 1 root   root   1, 8 Jun 10 16:16 random
crw-rw-rw- 1 root   root   1, 9 Jun 10 16:19 urandom
```

License
-------

GNU General Public License version 2 or later.

Primary author
--------------

Joel Rosdahl <joel@rosdahl.net>

Contributors
------------

Alex Wright
Leandro Lucarella
Matt Behrens
Ron Fritz
