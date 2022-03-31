# -*- coding: UTF-8 -*-
import re

import peppy.vfs as vfs
from peppy.debug import *

import pprint
pp = pprint.PrettyPrinter(indent=0)

count = 0
def auth_callback(url, scheme, realm, username):
    dprint("url=%s: scheme=%s, realm=%s, default username=%s" % (url, scheme, realm, username))
    global count
    count += 1
    if count < 3:
        return "test", "test"
    else:
        return "crunchy", "veggies"

vfs.register_authentication_callback(auth_callback)


if __name__ == '__main__':
#    print vfs.open("webdav://crunchy:veggies@share.flipturn.org/davtest/hello.txt")
#    print vfs.open("webdav://crunchy:veggies@share.flipturn.org/davtest/xyz.pdq")
    #print vfs.open("file:///tmp/xyz.pdq")
    #print vfs.get_names("webdav://crunchy:veggies@share.flipturn.org/davtest/tmp")
    
#    ref = vfs.get_reference("webdav://cr")
#    print(ref)
#    print vfs.get_names("webdav://cr")
#    print vfs.get_names("webdav://crunchy:veggies@")
#    print vfs.get_names("webdav://crunchy:veggies@share.flip")
#    print vfs.get_names("webdav://crunchy:veggies@share.flipturn.or")
#    print vfs.get_names("webdav://crunchy:veggies@share.flipturn.org/")
#    print vfs.get_names("webdav://crunchy:veggies@share.flipturn.org/a")

    header = 'Basic realm="Webdav Test"'
    header = 'Basic realm="Webdav Test", Digest realm="stuff and things"'
    matches = re.findall('[ \t]*([^ \t]+)[ \t]+realm="([^"]*)"', header)
    print matches
    for scheme, realm in matches:
        print("scheme=%s, realm=%s" % (scheme, realm))
    #print vfs.open("webdav://share.flipturn.org/davtest/test.py")
    #vfs.can_write("webdav://share.flipturn.org/davtest/locked.txt")
    dprint(vfs.get_mimetype("webdav://share.flipturn.org/davtest/.htaccess"))
    vfs.can_write("webdav://share.flipturn.org/davtest/.htpasswd")
    names = vfs.get_names("webdav://share.flipturn.org/davtest/")
    dprint(names)
