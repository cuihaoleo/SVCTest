#!/usr/bin/env python3

import cv2
import struct
import zlib
import sys


class SVCWriter():

    def __init__(self, path_bl, path_el,
                 size, jpeg_quality, mtu, min_layer=2):
        self.quality = jpeg_quality
        self.fbl = open(path_bl, "wb")
        self.fel = open(path_el, "wb")
        self.min_layer = min_layer

        buf = struct.pack("!II", height, width)
        self.fbl.write(buf)

        self.mtu = mtu
        self.count = 0

    def _pack_layer(self, layer, max_pack):
        off = 0
        bs = layer.flatten()

        # yield (OFFSET, ZDATA)
        while off < len(bs):
            buf = zlib.compress(bs[off:])
            if len(buf) <= max_pack:
                yield off, buf
                break

            # detect best block
            lo, hi = 0, len(bs) - off
            hi = (hi + 7) // 8 * 8

            while lo < hi:
                mi = (lo + hi) // 2
                mi = (mi + 7) // 8 * 8
                buf = zlib.compress(bs[off:off+mi])

                if len(buf) < max_pack:
                    lo = mi + 8
                elif len(buf) > max_pack:
                    hi = mi - 8
                else:
                    break

            while len(buf) > max_pack:
                mi -= 8
                buf = zlib.compress(bs[off:off+mi])

            yield (off, buf)
            off += mi

    def _write_layer(self, timestamp, layer, nth):

        hdr_size = struct.calcsize("!IBII")
        hdr_off = struct.calcsize("!IB")
        hdr = bytearray(hdr_size)
        struct.pack_into("!IB", hdr, 0, timestamp, nth)
        max_pack = self.mtu - hdr_size

        print("LAYER #%d" % nth)
        for (offset, packet) in self._pack_layer(layer, max_pack):
            struct.pack_into("!II", hdr, hdr_off, offset, len(packet))
            self.fel.write(hdr)
            self.fel.write(packet)
            print("    offset #%d: %d" % (offset, len(packet)))

    def write_frame(self, frame, timestamp):
        jpeg_param = (cv2.IMWRITE_JPEG_QUALITY, self.quality)
        ret, buf1 = cv2.imencode(".jpg", frame, params=jpeg_param)

        base = cv2.imdecode(buf1, cv2.IMREAD_GRAYSCALE)
        diff = frame - base

        neg = (diff & 0x80) > 0
        diff[neg] ^= 0x7f
        sign = diff >> 7
        buf2 = zlib.compress(sign)

        tcp_pack = struct.pack("!III", timestamp, len(buf1), len(buf2))
        self.fbl.write(tcp_pack)
        self.fbl.write(buf1)  # JPEG data
        self.fbl.write(buf2)  # sign layer data

        for i in range(6, self.min_layer-2, -1):
            bitplane = (diff >> i) & 1
            self._write_layer(timestamp, bitplane, i)

        self.count += 1


def main():
    video_path = sys.argv[1]
    cap = cv2.VideoCapture(video_path)
    
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    writer = SVCWriter("out.tcp", "out.udp", (height, width), 40, 1400)
    fourcc = cv2.VideoWriter_fourcc(*"Y8  ")
    writer2 = cv2.VideoWriter("out.avi", fourcc, 20.0, (height, width), False)
    
    count = 0
    while (cap.isOpened() and count < 1000):
        ret, frame = cap.read()
        timestamp = int(cap.get(cv2.CAP_PROP_POS_MSEC))
    
        if not ret:
            break
    
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        writer2.write(frame)
        writer.write_frame(frame, timestamp)
        print("Frame #%d (%d)" % (count, timestamp))
    
        count += 1


if __name__ == "__main__":
    main()
