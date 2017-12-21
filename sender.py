#!/usr/bin/env python3

import time
import os
import select
import struct
import socket
import threading
import io
import queue

from jpsvc_dec import BS_LAYER_HEADER, EH_LAYER_HEADER
from socket import IPPROTO_IP
from socket import IP_MULTICAST_TTL, IP_MULTICAST_LOOP
from socket import SOCK_DGRAM, SOCK_STREAM
from socket import AF_INET, AF_INET6


class TCPSender(threading.Thread):
    def __init__(self, conn, maxsize=10):
        super().__init__()
        self.conn = conn
        self.queue = queue.Queue(maxsize)
        self.closed = False

    def send(self, data):
        while self.queue.full():
            self.queue.get_nowait()
        self.queue.put(data)

    def close(self):
        self.closed = True

    def run(self):
        while not self.closed:
            while True:
                data = self.queue.get()

                try:
                    self.conn.send(data)
                except BrokenPipeError:
                    self.close()
                    break

                if self.queue.empty():
                    break

        self.conn.close()


class SVCServer(threading.Thread):

    def __init__(self, path_bl, path_el,
                 bind=("0.0.0.0", 21222),
                 mgroup=("224.21.22.2", 21222),
                 mcast_ttl=5, udp_maxsize=1400):
        super().__init__()

        self.fbl = open(path_bl, "rb")
        self.fel = open(path_el, "rb")

        maddr_b = socket.inet_aton(mgroup[0])
        self.first_pkt = struct.pack("!4sH", maddr_b, mgroup[1])

        st_size = struct.Struct("!II")
        self.second_pkt = buf = self.fbl.read(st_size.size)
        self.height, self.width = st_size.unpack(buf)

        self.usock = usock = socket.socket(AF_INET, SOCK_DGRAM)
        self.tsock = tsock = socket.socket(AF_INET, SOCK_STREAM)
        self.mgroup = mgroup
        self.udp_maxsize = udp_maxsize

        tsock.bind(bind)
        usock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, mcast_ttl)
        #usock.setsockopt(IPPROTO_IP, IP_MULTICAST_LOOP, 1)

    def load_frame(self):
        buf_hdr = self.fbl.read(BS_LAYER_HEADER.size)
        if len(buf_hdr) < BS_LAYER_HEADER.size:
            return None, None, None
        timestamp, jpeg_size, sign_size = BS_LAYER_HEADER.unpack(buf_hdr)

        buf_data = self.fbl.read(jpeg_size + sign_size)
        tcp_buf = buf_hdr + buf_data

        udp_packs = []
        udp_packs.append(io.BytesIO())

        while True:
            buf = self.fel.read(EH_LAYER_HEADER.size)
            if len(buf) < EH_LAYER_HEADER.size:
                break

            t, _, _, size = EH_LAYER_HEADER.unpack(buf)
            if t != timestamp:
                self.fel.seek(-EH_LAYER_HEADER.size, os.SEEK_CUR)
                break

            buf2 = self.fel.read(size)

            pack_size = size + EH_LAYER_HEADER.size
            if pack_size + udp_packs[-1].tell() > self.udp_maxsize:
                udp_packs.append(io.BytesIO())

            udp_packs[-1].write(buf)
            udp_packs[-1].write(buf2)

        udp_packs = [p.getvalue() for p in udp_packs]
        return (timestamp / 1000.0, tcp_buf, udp_packs)

    def run(self):
        # wait for first connection
        self.tsock.listen(10)
        select.select([self.tsock], [], [])
        self.tsock.setblocking(False)

        timestamp, tcp_buf, udp_packs = self.load_frame()
        start_time = time.time()
        packet_start_time = timestamp
        clients = []

        while timestamp is not None:
            print("Current timestamp: %.6f" % timestamp)
            elapsed = time.time() - start_time
            packet_offset = timestamp - packet_start_time

            if elapsed < packet_offset:
                time.sleep(packet_offset - elapsed)

            for pkt in udp_packs:
                self.usock.sendto(pkt, self.mgroup)

            try:
                conn, addr = self.tsock.accept()
            except socket.timeout:
                pass
            except BlockingIOError:
                pass
            else:
                sender = TCPSender(conn)
                sender.daemon = True
                sender.start()
                sender.send(self.first_pkt)
                sender.send(self.second_pkt)
                clients.append(sender)

            for c in clients:
                if not c.closed:
                    c.send(tcp_buf)

            timestamp, tcp_buf, udp_packs = self.load_frame()

        for c in clients:
            c.close()
        self.usock.close()
        self.tsock.close()

def main():
    server = SVCServer("out.tcp", "out.udp")
    server.daemon = True
    server.start()
    server.join()


if __name__ == "__main__":
    main()
