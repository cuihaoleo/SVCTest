#!/usr/bin/env python3

import argparse
import struct
import socket
import select
import threading
import time
import math
import heapq

from socket import IPPROTO_IP
from socket import INADDR_ANY
from socket import IP_MULTICAST_TTL, IP_ADD_MEMBERSHIP
from socket import SOCK_DGRAM, SOCK_STREAM
from socket import AF_INET, AF_INET6

from jpsvc_dec import BS_LAYER_HEADER
from jpsvc_dec import EH_LAYER_HEADER


class SVCClient(threading.Thread):

    def __init__(self, path_bl, path_el, server, buf_ms=1000):
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

        self.start_time = None
        self.start_timestamp = None
        self.buf_ms = buf_ms
        self.heap = []

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

            # first frame
            if self.start_time is None:
                hdr = buf[:BS_LAYER_HEADER.size]
                timestamp, _, _ = BS_LAYER_HEADER.unpack(hdr)
                self.start_timestamp = timestamp
                self.start_time = time.time()
                print("Current time:", self.start_time)
                print("Timestamp of 1st frame", self.start_timestamp)

            self.fbl.write(buf)
            print(self.fbl.tell())

    def _do_write(self):
        d_t = (time.time() - self.start_time) * 1000

        while len(self.heap) > 0:
            timestamp, nth, offset, pkt = self.heap[0]
            d_ts = timestamp - self.start_timestamp

            if d_t - d_ts >= self.buf_ms:
                print("WRITE timestamp:", timestamp)
                self.fel.write(pkt)
                heapq.heappop(self.heap)
            else:
                break

    def _queue_write(self, pkt):
        hdr = pkt[:EH_LAYER_HEADER.size] 
        timestamp, nth, offset, _ = EH_LAYER_HEADER.unpack(hdr)

        d_ts = timestamp - self.start_timestamp
        d_t = (time.time() - self.start_time) * 1000

        if d_ts - d_t <= self.buf_ms:
            print("QUEUE timestamp:", timestamp)
            heapq.heappush(self.heap, (timestamp, nth, offset, pkt))

    def recv_enhance(self):
        while True:
            try:
                buf, host = self.usock.recvfrom(65536)
            except BlockingIOError:
                break

            self._do_write()
            self._queue_write(buf)

    def run(self):
        self.closed = False
        self.tsock.setblocking(False)
        self.usock.setblocking(False)
        rlist = [ self.usock, self.tsock ]

        while self.start_time is None:
            self.recv_base()

        while not self.closed:
            r, w, x = select.select(rlist, [], [])

            if self.usock in r:
                self.recv_enhance()

            if self.tsock in r:
                self.recv_base()

        self.buf_ms = -math.inf
        self._do_write()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tcp_file",
                        required=True,
                        help="Base layer in TCP")
    parser.add_argument("-u", "--udp_file",
                        required=True,
                        help="Enhanced layer in UDP")
    parser.add_argument("server",
                        help="SVC server address / port")
    args = parser.parse_args()

    host, port = args.server.rsplit(":", 1)
    client = SVCClient(args.tcp_file, args.udp_file, (host, int(port)))
    client.daemon = True
    client.start()
    client.join()


if __name__ == "__main__":
    main()
