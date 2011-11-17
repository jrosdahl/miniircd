miniircd -- A (very) simple Internet Relay Chat (IRC) server
============================================================

Description
-----------

miniircd is a small and limited IRC server written in Python. Despite its size,
it is a functional alternative to a full-blown ircd for private or internal
use. Installation is simple; no configuration is required.

Features
--------

* Knows about the basic IRC protocol and commands.
* Easy installation.
* No configuration.
* No ident lookup (so that people behind firewalls that filter the ident port
  without sending NACK can connect without long timeouts).

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

Python 2.5 or newer. Get it at http://www.python.org.

Installation
------------

None. Just run "./miniircd --help" (or "python miniircd --help") to get some
help.

License
-------

GNU General Public License version 2 or later.

Author
------

Joel Rosdahl <joel@rosdahl.net>
