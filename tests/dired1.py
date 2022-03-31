# -*- coding: UTF-8 -*-
import os, sys

import peppy.vfs as vfs
from peppy.debug import *

from peppy_hsi_formats import nitffs


if __name__ == '__main__':
    ref = vfs.get_reference("file:/etc")
    dprint(vfs.exists(ref))
