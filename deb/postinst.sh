#! /bin/sh

set -e

case "$1" in
    configure)
        service miniircd start
    ;;
esac

exit 0
