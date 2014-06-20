#!/usr/bin/env python2

import socket
import threading
import SocketServer
import signal
import sys
import time
from collections import deque
from openwrt import QemuImage

EXTRA_HOSTS = 3     # number of qemu instances to keep sitting idle, waiting for connections
queuemu = deque()
dequelock = 0       # the 'for x in deque()' can take a while, so we should make it thread-safe
lockuser = ''

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    shell = None

    def handle(self):
        global dequelock, lockuser
        try:
            qlock('handle')
            lockuser = 'handle'
            self.shell = queuemu.popleft()
        except: # queuemu is empty. hopefully this is < 40 seconds after program start
            print '[!] User attempted to connect. Probably (hopefully) during initial boot'
            print '[#] Otherwise, consider setting EXTRA_HOSTS higher'
            self.request.send('\r\nBooting... try again in a minute or so\r\n\r\n')
            self.request.close()
            return
        finally:
            qrelease()
        user, password = self.do_login()
        self.process_commands(user, password)

    def do_login(self):
        self.request.sendall('It\'s a telnet server! Not yours, go away.\r\n')
        self.request.sendall('Username: ')
        user = self.request.recv(1024).rstrip()
        self.request.sendall('Password: ')
        password = self.request.recv(1024).rstrip()
        return user, password

    # my very own REPL (read-eval-print loop)
    def process_commands(self, user, password):
        while True:
            self.request.sendall('%s@thing:%s# ' % (user,self.shell.pwd))
            string = ''
            while True: # interrupts/telnet commands are sent immediately
                data, result = self.receive_loop()
                string += data
                if result == 'break':
                    break
                elif result == 'cmd:interrupt':
                    string = 'cmd:interrupt'
                    break
            result = self.check_cmd_loop(string)
            if result == 'break':
                break
            elif result == 'continue':
                continue
            elif result == 'good':
                # done checking - now execute!
                result = self.shell.execute(string)
                if result == 'close':
                    print '[+] done'
                    break
                elif result == 'waiting':
                    print '[!] shouldn\'t be waiting for anything...'
                first = True
                while self.shell.lines:
                    tosend = self.shell.lines.popleft().lstrip().rstrip()
                    if tosend == '':
                        continue
                    self.request.sendall(tosend + '\r\n')
                continue
            elif result == 'cmd:myname':
                self.request.send(self.shell.name + '\r\n')
                continue
            print '[!!!] WE SHOULD NEVER VENTURE HERE'

    def receive_loop(self):
        data = self.request.recv(1)
        if data == '':
            print '[+] breaked due to data == \'\''
            return data, 'break'
        if ord(data) == 6:  # ^C
            # We get IAC IP IAC DO 0x06
            self.request.send(chr(0xff))    # IAC (0xff)
            self.request.send(chr(0xfb))    # WILL (0xfb)
            self.request.send(chr(0x06))    # ACK
            self.request.sendall('\r\n<interrupt>\r\n')
            # GA (0xf9)     # BRK (0xf3)    # EC (0xf7) # don't need these (yet?)
# we should maybe implement telnet commands? advanced actors might check
# http://mars.netanya.ac.il/~unesco/cdrom/booklet/HTML/NETWORKING/node300.html (not 100% accurate)
# http://www.ietf.org/rfc/rfc854.txt (accurate command list > 240)
# http://tools.ietf.org/html/rfc1184 (contains < 240)
            return data, 'cmd:interrupt'
        if ord(data) == 4:  # ^D
            self.request.sendall('logoff\r\n')  # it looks legit?
            return data, 'break'
        if ord(data) == 0x0d and ord(self.request.recv(1)) == 0x0a: # \r\n
            return data, 'break'   # let's hope they don't send a \r by itself...
        elif ord(data) == 0x0d: # but let's log it anyways and pretend they sent \n
            print '[!!!] THEY SENT A \\r WITHOUT A \\n!'
            return data, 'break'
        else:
            return data, 'good'

    def check_cmd_loop(self, string):
        print '[+] got string: %s' % string
        if string == '':
            print '[!!] Empty string - we\'re done... why'
            return 'break'
        elif string == 'cmd:interrupt':
            print '[+] processing ^C (continuing)'
            self.shell.execute(chr(3))
            return 'continue' 
        elif chr(4) in string:
            print '[+] got ^D, closing'
            return 'break'
        elif 'cmd:diepot' in string:
            print '[!] ded'
            def die():
                server.shutdown()
            threading.Thread(target=die).start()
            self.request.close()
            return 'break'
        elif 'cmd:myname' in string:
            print '[!] Sending honeypot\'s name'
            return 'cmd:myname'
        return 'good'



# source here: http://hg.python.org/cpython/file/2.7/Lib/SocketServer.py
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True  # so it doesn't whine about "already in use"


def start_qemu():
    global queuemu, booting, dequelock, lockuser
    print '[#] Creating new qemu instance'
    instance = QemuImage()
    instance.boot()
    time.sleep(25)       # it takes a little to "truly" be ready...
    qlock('start_qemu')
    queuemu.append(instance)    # we should keep enough alive that 'sleep(3)' doesn't matter
    qrelease()
    booting -= 1
    print '[+] machine %s is ready to go!' % instance.name

# Press ^C in the terminal to print out current execution time
def show_time(signal, frame):
    print '[+++] Execution time: %s' % (time.time() - start_time)
signal.signal(signal.SIGINT, show_time)

server = None
ready = False
booting = 0
start_time = 0.0

def main():
    global server, queuemu, ready, booting, start_time, dequelock, lockuser
    start_time = time.time()
    server = ThreadedTCPServer(('0.0.0.0', 62915), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    print '[+] starting server on port %s' % str(port)
    server_thread.start()
    while server_thread.isAlive():
        qavail = 0  # available qemu instances
        qlock('main')
        for qemu in queuemu:
            if not qemu.inuse:
                qavail += 1
        qrelease()
        if qavail == 0:
            ready = False
        for x in range(EXTRA_HOSTS - (qavail+booting)):     # 3 available at all times
            print '[!!!] Booting image'
            booter = threading.Thread(target=start_qemu)
            booter.start()
            booting += 1
        server_thread.join(1)
    booter.join()   # if it's killed while one is booting, it can't properly process the kill command
    qlock('main-shutdown')
    for instance in queuemu:
        booter.join()   # if it's killed while one is booting, it can't properly process the kill command
        instance.die()
        qrelease()

def qlock(who): # who's trying to take the lock?
    global lockuser, dequelock
    while dequelock > 0:
        time.sleep(1)
        print '[!] dequelock held from the %s thread by %s' % (who, lockuser)
    dequelock += 1
    lockuser = who

def qrelease():
    global dequelock
    dequelock -= 1

if __name__ == '__main__':
    main()
