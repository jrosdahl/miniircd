#! /bin/sh

set -e

case "$1" in
    remove)
        service miniircd stop
    ;;
esac

exit 0
