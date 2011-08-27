VERSION := $(shell sed -ne 's/^VERSION = "\(.*\)"/\1/p' miniircd)

DISTFILES = miniircd COPYING README.md

all:
	echo "Nothing to do."

dist:
	mkdir miniircd-$(VERSION)
	cp $(DISTFILES) miniircd-$(VERSION)
	tar cvzf miniircd-$(VERSION).tar.gz miniircd-$(VERSION)
	rm -rf miniircd-$(VERSION)

clean:
	rm -rf miniircd-$(VERSION) *~
