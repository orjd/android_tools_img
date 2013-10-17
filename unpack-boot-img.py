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

parser = OptionParser(usage="unpack-boot-img.py <boot.img>\n\
Extract files from a boot.img", prog="unpack-boot-img")
(options, args) = parser.parse_args(args=sys.argv[1:])

if len(args) != 1:
    parser.print_usage()
    sys.exit(1)

padding = 0
with open(args[0], "rb") as img:
    buf = img.read(48)
    padding += 48
    magic, kernel_size, kernel_addr, ramdisk_size, ramdisk_addr,      \
      second_size, second_addr, tags_addr, page_size, dt_size, unused \
      = struct.unpack('8sIIIIIIIIII', buf)
    buf = img.read(560)
    padding += 560
    name, cmdline, id0, id1, id2, id3, id4, id5, id6, id7             \
      = struct.unpack('16s512sIIIIIIII', buf)
    pos = name.index('\0')
    if pos >= 0: name = name[0:pos]
    pos = cmdline.index('\0')
    if pos >= 0: cmdline = cmdline[0:pos]
    #print("magic=%s" % magic)
    #print("kernel_size=%d kernel_addr=%x" % (kernel_size, kernel_addr))
    #print("ramdisk_size=%d ramdisk_addr=%x" % ( ramdisk_size, ramdisk_addr))
    #print("second_size=%d second_addr=%x" % ( second_size, second_addr))
    #print("tags_addr=%x page_size=%d dt_size=%d" % ( tags_addr, page_size, dt_size))
    #print("name=%s" % name)
    #print("cmdline=%s" % cmdline)
    if padding < page_size: img.read(page_size - padding)
    padding = 0

    n = (kernel_size + page_size - 1) / page_size
    m = (ramdisk_size + page_size - 1) / page_size
    o = (second_size + page_size - 1) / page_size
    p = (dt_size + page_size - 1) / page_size

    # Kernel
    buf = img.read(kernel_size)
    print("Write kernel")
    kernel = open("kernel", "wb")
    kernel.write(buf)
    kernel.close()
    if kernel_size < n * page_size: img.read(n * page_size - kernel_size)

    # Ramdisk
    buf = img.read(ramdisk_size)
    print("Write ramdisk.gz")
    ramdisk = open("ramdisk.gz", "wb")
    ramdisk.write(buf)
    ramdisk.close()
    if ramdisk_size < m * page_size: img.read(m * page_size - ramdisk_size)

    # Optional second stage
    if o > 0:
        buf = img.read(second_size)
        print("Write second")
        second = open("second", "wb")
        second.write(buf)
        second.close()
        if second_size < o * page_size: img.read(o * page_size - second_size)

    # Optional device tree
    if p > 0:
        buf = img.read(dt_size)
        print("Write devicetree")
        dt = open("devicetree", "wb")
        dt.write(buf)
        dt.close()
        if dt_size < p * page_size: img.read(p * page_size - dt_size)

print("To recompress boot.img:")
kernel_offset = 0x8000
base = kernel_addr - kernel_offset
ramdisk_offset = ramdisk_addr - base
second_offset = second_addr - base
cmd = "  python repack-boot-img.py --kernel kernel --ramdisk ramdisk.gz --pagesize %d --base %x --kernel_offset %x --ramdisk_offset %x" % (page_size, base, kernel_offset, ramdisk_offset)
if len(cmdline) > 0:
    cmd += " --cmdline %s" % cmdline
if len(name) > 0:
    cmd += " --board %s" % name
if o > 0:
    cmd += " --second second --second_offset %x" % second_offset
if p > 0:
    cmd += " --dt devicetree"
print(cmd)

