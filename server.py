#!/usr/bin/env python2

import socket
import threading
import SocketServer
import signal
import sys

# yes, ^C is passed to thread (somehow)

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        while True:
            string = ''
            self.request.sendall('# ')
            while True: # interrupts and telnet commands are sent immediately
                data = self.request.recv(1)
                string += data
                if data == '':
                    print '[+] breaked due to data = \'\''
                    break
                if ord(data) == 6:  # ^C
# We get IAC IP IAC DO 0x06  (interrupt, then confirm (WILL) you'll do 0x06 (ACK), then ACK (0x06))
                    self.request.send(chr(0xff))    # IAC (0xff)
                    self.request.send(chr(0xfb))    # WILL (0xfb)
                    self.request.send(chr(0x06))    # ACK
                    self.request.sendall('\r\n<interrupt>\r\n')
                    # GA (249 ... 0xf9)     # BRK (0xf3)    # EC (0xf7)
    # we should maybe implement telnet commands? advanced actors might check
# http://mars.netanya.ac.il/~unesco/cdrom/booklet/HTML/NETWORKING/node300.html (not 100% accurate)
# http://www.ietf.org/rfc/rfc854.txt (accurate command list)
# http://tools.ietf.org/html/rfc1184 (contains < 240)
                    break
                if ord(data) == 4:  # ^D
                    self.request.sendall('logoff\r\n')
                    break
                if ord(data) == 0x0d and ord(self.request.recv(1)) == 0x0a: # \r\n
                    break
            if string == '':
                print '[#] Empty string - we\'re done'
                break
            if chr(6) in string:
                print '[+] processing ^C (continuing)'
                # TODO: process ^C
                continue 
            if chr(4) in string:
                print '[!] got ^D, closing'
                break
            # TODO: execute string
            # TODO: send response back (streaming?)
            print '[+] got string: %s' % string
            if 'die' in string:
                print '[!!!] ded'
                def die():
                    server.shutdown()
                threading.Thread(target=die).start()
                self.request.close()
                break


# source here: http://hg.python.org/cpython/file/2.7/Lib/SocketServer.py
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True  # so it doesn't whine about "already in use"
    pass

server = None

def main():
    global server
    server = ThreadedTCPServer(('localhost', 0), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    print '[+] starting server on ip %s' % str(port)
    server_thread.start()
    server_thread.join()

def sigint_handler(singal, frame):
    global server
    print '<> got SIGINT'
        # pexpect.send(chr(3))  # to send SIGINT to qemu
    # server.shutdown()
signal.signal(signal.SIGINT, sigint_handler)

if __name__ == '__main__':
    main()