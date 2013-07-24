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
* (Optional) SSL encrypted client-to-server communication

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

Python 2.7 or newer. Get it at http://www.python.org.

Installation
------------

None. Just run "./miniircd --help" (or "python miniircd --help") to get some
help.

License
-------

GNU General Public License version 2 or later.

Authorship
----------

Authored by Joel Rosdahl <joel@rosdahl.net>

Contributors:

  * Matt Behrens (github.com/zigg)
  * Alex Wright (github.com/alexwright)
  * Bui (github.com/bui)
  * Rui Carmo (github.com/rcarmo)
  * Joel Kleier (github.com/zombified)

