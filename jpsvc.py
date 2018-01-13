#!/usr/bin/env python3

import cv2
import struct
import zlib
import logging
import argparse


class SVCWriter():

    def __init__(self, path_bl, path_el,
                 size, jpeg_quality, mtu, min_layer=2):
        self.logger = logging.getLogger("SVCWriter")

        self.quality = jpeg_quality
        self.fbl = open(path_bl, "wb")
        self.fel = open(path_el, "wb")
        self.min_layer = min_layer

        buf = struct.pack("!II", size[0], size[1])
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

        self.logger.debug("LAYER #%d", nth)
        for (offset, packet) in self._pack_layer(layer, max_pack):
            struct.pack_into("!II", hdr, hdr_off, offset, len(packet))
            self.fel.write(hdr)
            self.fel.write(packet)

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
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("input",
                        help="Input video file")
    parser.add_argument("-t", "--tcp_file",
                        required=True,
                        help="Base layer in TCP")
    parser.add_argument("-u", "--udp_file",
                        required=True,
                        help="Enhanced layer in UDP")
    parser.add_argument("-q", "--quality",
                        type=int,
                        default=40,
                        help="JPEG base layer quality")
    parser.add_argument("-m", "--mtu",
                        type=int,
                        default=1400,
                        help="Network MTU")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.input)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    writer = SVCWriter(args.tcp_file, args.udp_file,
                       (height, width), args.quality, args.mtu)

    count = 0
    while (cap.isOpened()):
        ret, frame = cap.read()
        timestamp = int(cap.get(cv2.CAP_PROP_POS_MSEC))

        if not ret:
            break

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        writer.write_frame(frame, timestamp)
        logging.info("Frame #%d (%d) written" % (count, timestamp))

        count += 1


if __name__ == "__main__":
    main()
