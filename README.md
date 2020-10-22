BLDR
====

Build debian packages in a clean docker environment

Features:

* provide a dockerized dpkg-buildpackage wrapper, as Docker can be used to create a clean build environment for Debian packaging
* easy-to-use: navigate inside a directory that has a debian subdirectory and run build
* collect the debian dependencies automatically and puts them in Docker build layer
* cache the dependency install step and the re-build will be quicker
* to test the debian package you can enter to the container which contains the build environment
* the built debian package is stored in a local apt repository
* build multiple dependent packages, if called multiple times (uses the built packages as build dependencies of the next ones)
