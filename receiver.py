#!/usr/bin/env python3

import struct
import socket
import select
import threading

from socket import IPPROTO_IP
from socket import INADDR_ANY
from socket import IP_MULTICAST_TTL, IP_ADD_MEMBERSHIP
from socket import SOCK_DGRAM, SOCK_STREAM
from socket import AF_INET, AF_INET6


class SVCClient(threading.Thread):

    def __init__(self, path_bl, path_el, server):
        super().__init__()

        self.usock = usock = socket.socket(AF_INET, SOCK_DGRAM)
        self.tsock = tsock = socket.socket(AF_INET, SOCK_STREAM)

        tsock.connect(server)
        print("TCP connect: %s:%d" % server)

        st_mcast_addr = struct.Struct("!4sH")
        buf = tsock.recv(st_mcast_addr.size)
        maddr_b, port = st_mcast_addr.unpack(buf)
        maddr = socket.inet_ntoa(maddr_b)
        self.mgroup = (maddr, port)

        usock.bind(self.mgroup)
        mreq = struct.pack('4sL', maddr_b, INADDR_ANY)
        usock.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)

        print("UDP broadcast: %s:%d" % self.mgroup)

        st_size = struct.Struct("!II")
        buf = tsock.recv(st_size.size)

        self.fbl = open(path_bl, "wb")
        self.fel = open(path_el, "wb")
        self.fbl.write(buf)

    def recv_base(self):
        while True:
            try:
                buf = self.tsock.recv(65536)
            except BlockingIOError:
                break

            if not buf:
                self.closed = True
                break

            self.fbl.write(buf)

    def recv_enhance(self):
        while True:
            try:
                buf, host = self.usock.recvfrom(65536)
            except BlockingIOError:
                break

            self.fel.write(buf)

    def run(self):
        self.closed = False
        self.tsock.setblocking(False)
        self.usock.setblocking(False)
        rlist = [ self.usock, self.tsock ]

        while not self.closed:
            r, w, x = select.select(rlist, [], [])

            if self.tsock in r:
                self.recv_base()

            if self.usock in r:
                self.recv_enhance()


if __name__ == "__main__":
    client = SVCClient("recv.tcp", "recv.udp", ("127.0.0.1", 21222))
    client.start()
    client.join()
