#! /usr/bin/python

# Copyright 2013, Oscar Jounaud <oscar.jounaud@gmail.com>
#
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the University of California, Berkeley nor the
#   names of its contributors may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import struct
import sys
import hashlib
from optparse import OptionParser

# Unpack files from a boot.img
# See system/core/mkbootimg/bootimg.h in Android sources
#
#    +-----------------+
#    | boot header     | 1 page
#    +-----------------+
#    | kernel          | n pages
#    +-----------------+
#    | ramdisk         | m pages
#    +-----------------+
#    | second stage    | o pages
#    +-----------------+
#    | device tree     | p pages
#    +-----------------+
#
#    n = (kernel_size + page_size - 1) / page_size
#    m = (ramdisk_size + page_size - 1) / page_size
#    o = (second_size + page_size - 1) / page_size
#    p = (dt_size + page_size - 1) / page_size

parser = OptionParser(usage="repack-boot-img.py -o <filename> --kernel <filename> --ramdisk <filename>\n\
  [--second <2ndbootloader-filename>] [--cmdline <kernel-commandline>]\n\
  [--base <address>] [--pagesize <pagesize>] [--ramdisk_offset <address>]\n\n\
Repacks kernel and ramdisk into a boot.img", prog="repack-boot-img")
parser.add_option("-o", "--output", action="store", dest="output",
    type="string", default="boot.img", help="output filename")
parser.add_option("--kernel", action="store", dest="kernel",
    type="string", help="kernel filename")
parser.add_option("--ramdisk", action="store", dest="ramdisk",
    type="string", help="ramdisk filename")
parser.add_option("--second", action="store", dest="second",
    type="string", help="second bootloader filename")
parser.add_option("--cmdline", action="store", dest="cmdline", default="",
    type="string", help="kernel command line")
parser.add_option("--board", action="store", dest="name", default="",
    type="string", help="board name")
parser.add_option("--pagesize", action="store", dest="pagesize", default="2048",
    type="string", help="page size (in decimal)")
parser.add_option("--base", action="store", dest="base", default="10000000",
    type="string", help="base address (in hexadecimal)")
parser.add_option("--kernel_offset", action="store", dest="kernel_offset", default="8000",
    type="string", help="kernel offset (in hexadecimal)")
parser.add_option("--ramdisk_offset", action="store", dest="ramdisk_offset", default="1000000",
    type="string", help="ramdisk offset (in hexadecimal)")
parser.add_option("--second_offset", action="store", dest="second_offset", default="f00000",
    type="string", help="second offset (in hexadecimal)")
parser.add_option("--tags_offset", action="store", dest="tags_offset", default="100",
    type="string", help="tags offset (in hexadecimal)")
(options, args) = parser.parse_args(args=sys.argv[1:])

if len(args) != 0:
    parser.print_usage()
    sys.exit(1)

page_size = int(options.pagesize, 10)

base = int(options.base, 16)
kernel_offset = int(options.kernel_offset, 16)
ramdisk_offset = int(options.ramdisk_offset, 16)
second_offset = int(options.second_offset, 16)
tags_offset = int(options.tags_offset, 16)

kernel_addr  = base + kernel_offset
ramdisk_addr = base + ramdisk_offset
second_addr  = base + second_offset
tags_addr    = base + tags_offset

magic = "ANDROID!"

output = open(options.output, "wb")
output.write('\0' * page_size)

def append(filename, sha):
    file_size = 0
    if filename:
        with open(filename, "rb") as file:
            buf = file.read()
            file_size = len(buf)
            output.write(buf)
            sha.update(buf)
            padding = file_size % page_size
            if padding > 0:
                output.write('\0' * (page_size - padding))
    sha.update(struct.pack('I', file_size))
    return file_size


m = hashlib.sha1()
kernel_size = append(options.kernel, m)
ramdisk_size = append(options.ramdisk, m)
second_size = append(options.second, m)
output.close()
id0, id1, id2, id3, id4 = struct.unpack('IIIII', m.digest())

output = open(options.output, "rb+")
output.write(struct.pack('8sIIIIIIIIII', magic, \
      kernel_size, kernel_addr, ramdisk_size, ramdisk_addr,      \
      second_size, second_addr, tags_addr, page_size, 0, 0))
output.write(struct.pack('16s512sIIIIIIII', options.name, options.cmdline, id0, id1, id2, id3, id4, 0, 0, 0))

