# -*- coding: UTF-8 -*-
import re

import peppy.vfs as vfs
from peppy.vfs.davclient import DAVClient


if __name__ == '__main__':
    ref = vfs.get_reference("webdav://crunchy:veggies@share.flipturn.org/davtest/locked.txt")
    
    if not vfs.exists(ref):
        fh = vfs.make_file(ref)
        fh.write("This file is locked!!!")
        fh.close()
    
    client = DAVClient(ref)
    path = str(ref.path)
    owner = "http://www.flipturn.org"
    client.set_lock(path, owner)
    vfs.can_write("webdav://share.flipturn.org/davtest/locked.txt")
