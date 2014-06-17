#!/usr/bin/env python2

import pexpect
import random
import time

class QemuImage(object):
    name = ''       # snapshot name
    router = None   # qemu pexpect instance

    def __init__(self, memory=30, snapshot=''):    # memory in megabytes, snapshot is string
        start_time = time.time()
        self.name = snapshot
        if self.snapshot is '':   # we'll create a new one
            self.name = str(int(time.time())) + random_string() + '.qcow2'  # timestampSTRING.qcow2
            cmd = 'qemu-img create -b base.qcow2 -f qcow2 %s' % self.name
            print '[#] running command: ' + cmd
            creator = pexpect.spawn(cmd)
            creator.expect(pexpect.EOF)
            for line in creator.before.split('\n'):
                print '[#] ' + line     # let's use print for logging
            # fyi: http://stackoverflow.com/questions/17067560/intercept-pythons-print-statement-and-display-in-gui
            time.sleep(0.01)    # http://pexpect.readthedocs.org/en/latest/commonissues.html#timing-issue-with-isalive
            if creator.isalive():
                print '[-] looks like something went wrong - why is the creator alive?'
            else:
                print '[+] created new image: %s' % self.name
                print '[+] done in %s seconds' % str(time.time() - start_time)
        else:
            print '[+] using previous image: %s' % self.name
        boot_time = time.time()
        cmd = 'qemu-system-i386 -net nic,model=ne2k_pci -nographic -m %sM -hda %s' % self.memory, self.name
        self.router = pexpect.spawn(cmd)
        self.router.expect('Please press Enter to activate this console.')
        self.router.sendline()
        self.router.setecho(False)
        print '[+] boot finished in %s seconds' % boot_time - time.time()
        if boot_time - time.time() > 30:
            print '[-] %s seconds is a long time... what\'s up?' % boot_time - time.time()

    def execute(self, cmd):
        self.router.sendline(cmd)

'''
    TODO: Find a good way to filter actor's input and output we probably want 
    to make a list of "easy" commands (commands that execute, print to stdout, 
    then exit) so we can execute those without trouble.
    We'll need to go into router.interact() mode when the actor is doing
    anything besides these easy commands. To do that without him/her noticing,
    we'll need to filter it, and maybe insert an escape token if something bad
    happens or when the necessity for interact() is gone.
'''
def input_filter(data):
    pass    
def output_filter(data):
    pass


def random_string(number=1):  # number: how many string names
    return ''.join([random.choice(string.letters) for i in xrange(10)])
    # I hope 10 chars + timestamp is enough to be always unique...