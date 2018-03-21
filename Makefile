JAILDIR = /srv/miniircd/jail
JAILUSER = nobody
INSTALL = /srv/miniircd
CERTDIR = cert

.PHONY: all
all: install

.PHONY: install
install: jail cert systemd

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
	mkdir -p $(JAILDIR)/$(CERTDIR)
	@echo "Generating cert and key within $(JAILDIR)/$(CERTDIR)"
	openssl genrsa -des3 -out $(JAILDIR)/$(CERTDIR)/server.orig.key 2048
	openssl rsa -in $(JAILDIR)/$(CERTDIR)/server.orig.key -out $(JAILDIR)/$(CERTDIR)/server.key
	openssl req -new -key $(JAILDIR)/$(CERTDIR)/server.key -out $(JAILDIR)/$(CERTDIR)/server.csr
	openssl x509 -req -days 365 -in $(JAILDIR)/$(CERTDIR)/server.csr -signkey $(JAILDIR)/$(CERTDIR)/server.key -out $(JAILDIR)/$(CERTDIR)/server.crt

.PHONY: copy
copy:
	@echo "copy binaries to $(INSTALL)"
	cp $(DISTFILES) $(INSTALL)/.

.PHONY: systemd
systemd:
	@echo "generating Systemd-bullshit"
	@echo "[Unit]" >> /etc/systemd/system/irc.service
	@echo "Description=miniIRCd" >> /etc/systemd/system/irc.service
	@echo "After=network.service" >> /etc/systemd/system/irc.service
	@echo "[Service]" >> /etc/systemd/system/irc.service
	@echo "User=root" >> /etc/systemd/system/irc.service
	@echo "Group=nogroup" >> /etc/systemd/system/irc.service
	@echo "Type=simple" >> /etc/systemd/system/irc.service
	@echo "WorkingDirectory=/srv/miniircd" >> /etc/systemd/system/irc.service
	@echo "ExecStart=/usr/bin/python $(INSTALL)/miniircd --ssl-pem-file=/$(CERTDIR)/server.crt --key-file=/$(CERTDIR)/server.key --setuid=$(JAILUSER) --chroot=$(JAILDIR)" >> /etc/systemd/system/irc.service
	@echo "ExecStop=/bin/kill -9 $MAINPID" >> /etc/systemd/system/irc.service
	@echo "PIDFile=/srv/miniircd/.miniircd.pid" >> /etc/systemd/system/irc.service
	@echo "RestartSec=15" >> /etc/systemd/system/irc.service
	@echo "Restart=always" >> /etc/systemd/system/irc.service
	@echo "" >> /etc/systemd/system/irc.service
	@echo "[Install]" >> /etc/systemd/system/irc.service
	@echo "WantedBy=multi-user.target" >> /etc/systemd/system/irc.service
	systemctl daemon-reload
	systemctl enable irc


