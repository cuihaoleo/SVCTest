#!/usr/bin/env python3

import cv2
import numpy as np
import sys

fourcc = cv2.VideoWriter_fourcc(*"Y8  ")
cap1 = cv2.VideoCapture(sys.argv[1])
cap2 = cv2.VideoCapture(sys.argv[2])
count = 0

while (cap1.isOpened()):
    ret, f1 = cap1.read()
    ret, f2 = cap2.read()
    if f1 is None or f2 is None:
        break

    f1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    f2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
    diff = f1 - f2
    mse = np.square(diff).mean()

    psnr = 10 * np.log10(255 * 255 / mse)

    print(count, mse, psnr)
    count += 1

cap1.release()
cap2.release()
