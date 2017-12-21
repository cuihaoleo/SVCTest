import cv2
import numpy as np
import struct
import zlib
import os

BS_LAYER_HEADER = struct.Struct("!III")
EH_LAYER_HEADER = struct.Struct("!IBII")

class SVMDecoder():

    def __init__(self, path_bl, path_el):
        self.fbl = open(path_bl, "rb")
        self.fel = open(path_el, "rb")

        buf = self.fbl.read(8)
        self.height, self.width = struct.unpack("!II", buf)

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
            if timestamp != tcp_time:
                self.fel.seek(-EH_LAYER_HEADER.size, os.SEEK_CUR)
                break

            raw = self.fel.read(size)
            buf = zlib.decompress(raw)
            decomp = np.fromiter(buf, dtype=np.uint8)
            print(offset, offset+len(decomp), nth)
            layer[offset:offset+len(decomp)] += decomp << nth

        neg = (layer & 0x80) > 0
        layer[neg] ^= 0x7f
        return layer

    def read_frame(self):

        buf = self.fbl.read(BS_LAYER_HEADER.size)
        if len(buf) < BS_LAYER_HEADER.size:
            return None, None

        timestamp, jpeg_size, sign_size = BS_LAYER_HEADER.unpack(buf)
        print(timestamp)
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
    decoder = SVMDecoder("out.tcp", "out.udp")
    fourcc = cv2.VideoWriter_fourcc(*"Y8  ")
    writer = cv2.VideoWriter("dec.avi", fourcc, 20.0, decoder.size, False)
    
    while True:
        timestamp, frame = decoder.read_frame()
        if frame is None:
            break
        writer.write(frame)


if __name__ == "__main__":
    main()
