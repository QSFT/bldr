all:
	echo "Made."
	ls -la src

install:
	mkdir -p ${DESTDIR}/usr/lib/symlinks
	cp --no-dereference src/* ${DESTDIR}/usr/lib/symlinks/
