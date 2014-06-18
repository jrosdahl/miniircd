VERSION := $(shell sed -ne 's/^VERSION = "\(.*\)"/\1/p' miniircd)

DISTFILES = miniircd COPYING README.md
JAILDIR = /var/jail/miniircd
JAILUSER = nobody

all:
	echo "Nothing to do."

dist:
	mkdir miniircd-$(VERSION)
	cp $(DISTFILES) miniircd-$(VERSION)
	tar cvzf miniircd-$(VERSION).tar.gz miniircd-$(VERSION)
	rm -rf miniircd-$(VERSION)

clean:
	rm -rf miniircd-$(VERSION) *~

jail:
	mkdir -p $(JAILDIR)/dev
	chmod 755 $(JAILDIR)
	mknod $(JAILDIR)/dev/null c 1 3
	mknod $(JAILDIR)/dev/urandom c 1 9
	chmod 666 $(JAILDIR)/dev/*
	chown $(JAILUSER) $(JAILDIR)
