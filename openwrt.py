#!/usr/bin/env python2

import pexpect
import random
import time
import string
import re
from collections import deque

######################################################
# pexpect must be used in the thread that created it #
######################################################
class QemuImage(object):
    initialized = False
    inuse = False
    users = 0
    name = ''       # snapshot name
    router = None   # qemu pexpect instance
    qemuprompt = 'root@OpenWrt:.+\\#'
    pwd = '/'
    interrupt = 0
    lines = deque()

    def __init__(self, memory=30, snapshot=''):    # memory in megabytes, snapshot is string
        start_time = time.time()
        self.name = snapshot
        self.memory = memory
        if self.name == '':   # we'll create a new one
            # self.name = str(int(time.time())) + random_string() + '.qcow2'  # timestampSTRING.qcow2
            self.name = '%s-%s.qcow2' % (str(int(time.time())), random_string())
            cmd = 'qemu-img create -b base.qcow2 -f qcow2 %s' % self.name
            print '[#] running command: ' + cmd
            creator = pexpect.spawn(cmd)
            creator.expect(pexpect.EOF)
            for line in creator.before.split('\n'):
                print '[#] %s' % line     # let's use print for logging
            # fyi: http://stackoverflow.com/questions/17067560/intercept-pythons-print-statement-and-display-in-gui
            time.sleep(0.01)    # http://pexpect.readthedocs.org/en/latest/commonissues.html#timing-issue-with-isalive
            if creator.isalive():
                print '[-] looks like something went wrong - why is the creator alive?'
            else:
                print '[+] created new image: %s' % self.name
                print '[#] done in %s seconds' % str(time.time() - start_time)
        else:
            print '[+] using previous image: %s' % self.name

    def boot(self):
        boot_time = time.time()
        print '[#] Now we wait...'
        cmd = 'qemu-system-i386 -net nic,model=ne2k_pci -nographic -m %sM -hda %s' % (self.memory, self.name)
        print '[#] executing: %s' % cmd
        self.router = pexpect.spawn(cmd)
        try:
            self.router.expect('activate this console.', timeout=40)
        except:
            print 'Exception expecting \"activate this console\"...'
            print str(self.router)
            exit()
        self.router.sendline()
        print '[#] Pressed enter'
        try:
            # Yes, there are three of them
            self.router.expect('entered forwarding state', timeout=30)
            self.router.expect('entered forwarding state', timeout=30)
            self.router.expect('entered forwarding state', timeout=30)
        except:
            print 'Exception expecting \"entered forwarding state\"'
            print str(self.router)
        self.router.setecho(False)
        print '[+] boot finished in %s seconds' % str(time.time() - boot_time)
        self.initialized = True
        if boot_time - time.time() > 60:
            print '[-] %s seconds is a long time... what\'s up?' % str(boot_time - time.time())

    def execute(self, cmd):
        self.router.sendline()
        self.router.expect(self.qemuprompt, timeout=1)
        if cmd == 'poweroff':
            return self.poweroff()
        if cmd == 'exit':
            # TODO: set timer to power off
            return 'close'
        self.router.sendline(cmd)
        return self.process_output(cmd)

    def process_output(self, cmd):
        while self.interrupt == 0:
            timeout = self.router.expect(['\r\n', pexpect.TIMEOUT], timeout=.2)
            out = self.router.before
            for line in out.split('\r\n'):     # sanitize
                if cmd in line or 'OpenWrt' in line:
                    if 'not found' in line:
                        self.lines.append(line)
                    continue
                self.lines.append(line)
            if timeout == 1:
                if 'root@OpenWrt' in self.router.before:
                    self.pwd = re.search(r'OpenWrt:(.+)#', self.router.before).group(1)
                    return 'done'
                    # this^ returns the 'status' and sets 'pwd'
                else:
                    # TODO: Maybe call a function to check if we should keep looping
                    # hm, maybe I'll just make a garbage collector

                    return 'waiting'
        return 'interrupted'

    def poweroff(self):
        self.router.sendline('poweroff')
        self.router.expect(pexpect.EOF)
        self.initialized = False
        print '[!] Instance %s powered off' % self.name
        return 'close'

    def die(self):
        self.poweroff()
        if not self.inuse:  # delete if never used
            cmd = 'rm %s' % self.name
            rmchild = pexpect.spawn(cmd)
            rmchild.expect(pexpect.EOF)
            print '[#] Instance %s deleted successfully' % self.name
        self.initialized = False

'''
    TODO: Find a good way to filter actor's input and output. we probably want 
    to make a list of "easy" commands (commands that execute, print to stdout, 
    then exit) so we can execute those without trouble.
    We'll need to go into router.interact() mode when the actor is doing
    anything besides these easy commands. To do that without him/her noticing,
    we'll need to filter it, and maybe insert an escape token if something bad
    happens or when the necessity for interact() is gone.

    BUT, *maybe* - if we can't find any better way to do this stuff. This is 
    probably the most "thin" way, but it's more difficult
'''
def input_filter(data):
    pass    
def output_filter(data):
    pass


def random_string(number=1):  # number: how many string names
    return ''.join([random.choice(string.letters) for i in xrange(10)])
    # I hope 10 chars + timestamp is enough to be always unique...

if __name__ == '__main__':
    print '[!] Starting openwrt class test'
    shell = QemuImage()
    user = raw_input('user: ')
    raw_input('pass: ')         # TODO: we should append the supplied username/passwd to /etc/passwd
    while True:
        cmd = raw_input('%s@thing:%s# ' % (user,shell.pwd))
        result = shell.execute(cmd)
        if result == 'close':
            print '[+] done'
            break
        elif result == 'waiting':
            print '[!] shouldn\'t be waiting for anything...'
        while shell.lines:
            print shell.lines.popleft()



''' TODO:

There are a bunch of things we'll want to do to make the environment look like a router...

/proc/cpuinfo
username+password in /etc/passwd


'''