#!/usr/bin/env python2

import pexpect

child = pexpect.spawn('qemu-system-i386 -net nic,model=ne2k_pci -nographic -m 20M -hda openwrt-x86-ext2.image')
# child.logfile = blah
child.expect('Please press Enter to activate this console.')
child.sendline()
child.expect(r'entering forwarding state') # r'' means raw string - no escape necessary
child.sendline()
print '\n'
print r'^] (ctrl-]) to end session'


print '''
    Insert ascii art here
    '''

child.interact(chr(29))                    # and we should see 'root@OpenWrt:/#'
    # chr(29) is ctrl-]