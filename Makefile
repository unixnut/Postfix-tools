# Makefile for installing scripts into $(DEST)

PREFIX=/usr/local
DEST=$(PREFIX)/sbin
SCRIPTS=postresolve
SCRIPT_MODE=555


.PHONY: install install_scripts

install: $(DEST) install_scripts $(DEST)/README.txt

$(DEST):
	install -d $@

install_scripts: $(SCRIPTS:%=$(DEST)/%)

# could also use --owner=root and/or --group=staff (possibly depending upon whether $(DEST) has been overridden)
# for Python, could use "sed '1s@^#! /usr/bin/python$@& -O@'" instead of install 
$(DEST)/%: %.py
	install --mode=$(SCRIPT_MODE) --preserve-timestamps $(INSTALL_OPTS) \
	  $< $@

$(DEST)/%: %
	install --mode=$(SCRIPT_MODE) --preserve-timestamps $(INSTALL_OPTS) \
	  $< $(DEST)/$(<F)

$(DEST)/README.txt:
	@echo "Certain scripts (those without owner write permission) have been" >> $@
	@echo "installed here from source control work directories.  DO NOT EDIT THEM." >> $@
	@echo README.txt installed


.PHONY: subdirs $(SUBDIRS)
subdirs:
	$(MAKE) -C $@

# place prerequistes determining any ordering for subdirs here
