.PHONY: all
all: build

.PHONY: install
install: build
	cp src/*.deb src/*.tar.gz src/*.changes src/*.dsc src/*.buildinfo .

.PHONY: build
build:
	cd src/libdependable && dpkg-buildpackage --no-sign

.PHONY: clean
clean:
	rm -f src/*.deb src/*.tar.gz src/*.changes src/*.dsc src/*.buildinfo
	make -C src/libdependable -f debian/rules clean
