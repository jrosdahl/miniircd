#! /bin/sh

set -e

case "$1" in
    install)
        mkdir -p /var/lib/miniircd
	chown nobody /var/lib/miniircd
    ;;

    upgrade)
        service miniircd status | grep -q start &&
            service miniircd stop
    ;;

    abort-upgrade)
    ;;

    *)
        echo "preinst called with unknown argument \`$1'" >&2
        exit 1
    ;;
esac

exit 0
