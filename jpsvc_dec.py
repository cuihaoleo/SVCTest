import cv2
import numpy as np
import struct
import zlib
import os
import sys
import logging
import argparse

BS_LAYER_HEADER = struct.Struct("!III")
EH_LAYER_HEADER = struct.Struct("!IBII")

class SVCDecoder():

    def __init__(self, path_bl, path_el):
        self.logger = logging.getLogger("SVCDecoder")

        self.fbl = open(path_bl, "rb")
        self.fel = open(path_el, "rb")

        buf = self.fbl.read(8)
        self.height, self.width = struct.unpack("!II", buf)
        self.last_time = 0

    @property
    def size(self):
        return (self.height, self.width)

    def _el_proc(self, tcp_time, sign):
        layer = sign.astype(np.uint8)
        layer <<= 7

        while True:
            buf = self.fel.read(EH_LAYER_HEADER.size)
            if len(buf) < EH_LAYER_HEADER.size:
                break

            timestamp, nth, offset, size = EH_LAYER_HEADER.unpack(buf)
            if timestamp > tcp_time:
                self.fel.seek(-EH_LAYER_HEADER.size, os.SEEK_CUR)
                break
            elif timestamp < tcp_time:
                self.fel.seek(size, os.SEEK_CUR)
                continue

            raw = self.fel.read(size)
            buf = zlib.decompress(raw)
            decomp = np.fromiter(buf, dtype=np.uint8)
            self.logger.info("ENHANCE: %d %d %d", timestamp, nth, offset)
            layer[offset:offset+len(decomp)] += decomp << nth

        neg = (layer & 0x80) > 0
        layer[neg] ^= 0x7f
        return layer

    def read_frame(self):

        buf = self.fbl.read(BS_LAYER_HEADER.size)
        if len(buf) < BS_LAYER_HEADER.size:
            return None, None

        timestamp, jpeg_size, sign_size = BS_LAYER_HEADER.unpack(buf)
        self.logger.info("BASE: %d %d", timestamp, timestamp - self.last_time)
        self.last_time = timestamp
        jpeg = self.fbl.read(jpeg_size)

        buf = self.fbl.read(sign_size)
        buf = zlib.decompress(buf)
        sign = np.fromiter(buf, dtype=bool)

        base = cv2.imdecode(np.fromiter(jpeg, dtype=np.uint8),
                            cv2.IMREAD_GRAYSCALE)
        enhance = self._el_proc(timestamp, sign)
        rebuild = base + enhance.reshape(base.shape)

        return (timestamp, rebuild)


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("output",
                        help="Output video file")
    parser.add_argument("-t", "--tcp_file",
                        required=True,
                        help="Base layer in TCP")
    parser.add_argument("-u", "--udp_file",
                        default="/dev/null",
                        help="Enhanced layer in UDP")
    parser.add_argument("-d", "--display",
                        type=int,
                        default=0,
                        help="Display interval")
    args = parser.parse_args()

    decoder = SVCDecoder(args.tcp_file, args.udp_file)
    fourcc = cv2.VideoWriter_fourcc(*"Y8  ")
    writer = cv2.VideoWriter(args.output, fourcc, 29.97, decoder.size[::-1], False)
    
    while True:
        timestamp, frame = decoder.read_frame()
        if frame is None:
            break
        writer.write(frame)

        if args.display > 0:
            cv2.imshow('frame', frame)
            if cv2.waitKey(args.display) & 0xFF == ord('q'):
                break

    if args.display > 0:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
