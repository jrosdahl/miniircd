VERSION := $(shell sed -ne 's/^VERSION = "\(.*\)"/\1/p' miniircd)

DISTFILES = miniircd COPYING README.md
JAILDIR = /var/jail/miniircd
JAILUSER = nobody
CERTDIR = /tmp

.PHONY: all
all: test

.PHONY: test
test:
	./test

.PHONY: dist
dist:
	mkdir miniircd-$(VERSION)
	cp $(DISTFILES) miniircd-$(VERSION)
	tar cvzf miniircd-$(VERSION).tar.gz miniircd-$(VERSION)
	rm -rf miniircd-$(VERSION)

.PHONY: clean
clean:
	rm -rf miniircd-$(VERSION) *~

.PHONY: jail
jail:
	mkdir -p $(JAILDIR)/dev
	chmod 755 $(JAILDIR)
	mknod $(JAILDIR)/dev/null c 1 3
	mknod $(JAILDIR)/dev/urandom c 1 9
	chmod 666 $(JAILDIR)/dev/*
	chown $(JAILUSER) $(JAILDIR)

.PHONY: cert
cert:
	@echo "Generating cert and key within $(CERTDIR)"
	openssl genrsa -des3 -out $(CERTDIR)/server.orig.key 2048
	openssl rsa -in $(CERTDIR)/server.orig.key -out $(CERTDIR)/server.key
	openssl req -new -key $(CERTDIR)/server.key -out $(CERTDIR)/server.csr
	openssl x509 -req -days 365 -in $(CERTDIR)/server.csr -signkey $(CERTDIR)/server.key -out $(CERTDIR)/server.crt
