#! /bin/sh

set -e

case "$1" in
    remove)
        rmdir --ignore-fail-on-non-empty /var/lib/miniircd
    ;;

    purge)
        rm -fr /var/lib/miniircd
    ;;
esac

exit 0
