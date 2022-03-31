#!/bin/bash

mkdir -p webdav_jail

# Needs pydavserver: http://code.google.com/p/pywebdav/
# install by: easy_install pywebdav
davserver -D $PWD/webdav_jail -u test -p passwd
