VERSION := $(shell sed -n -e '/version = /{s/version = "\(.*\)"/\1/;p;}' <miniircd)

all:
	echo "Nothing to do."

dist:
	mkdir miniircd-$(VERSION)
	cp miniircd COPYING miniircd-$(VERSION)
	tar cvzf miniircd-$(VERSION).tar.gz miniircd-$(VERSION)
	rm -rf miniircd-$(VERSION)

clean:
	rm -rf miniircd-$(VERSION) *~
