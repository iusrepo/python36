#!/usr/bin/python3.4m
# -*- python -*-

import sys
import subprocess
ver = sys.version[:3]
arch = subprocess.check_output('uname -m'.split()).decode("utf-8").rstrip()
call = ['python{ver}m-{arch}-config'.format(ver=ver, arch=arch)] + sys.argv[1:]
retval = subprocess.call(call)
if retval == 127:
    print('Could not find python{ver}m-{arch}-config. Look around to see available arches.'.format(ver=ver, arch=arch), file=sys.stderr)
