.PHONY: all
all: build

.PHONY: install
install: build
	cp src/*.deb src/*.tar.gz src/*.changes src/*.dsc src/*.buildinfo .

.PHONY: build
build:
	cd src/depend-test && dpkg-buildpackage --no-sign  --no-check-builddeps

.PHONY: clean
clean:
	rm -f src/*.deb src/*.tar.gz src/*.changes src/*.dsc src/*.buildinfo
	make -C src/depend-test -f debian/rules clean
