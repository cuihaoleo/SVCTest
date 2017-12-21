#!/usr/bin/env python3

import cv2
import sys

fourcc = cv2.VideoWriter_fourcc(*"Y8  ")
cap = cv2.VideoCapture(sys.argv[1])

while (cap.isOpened()):
    ret, frame = cap.read()
    if frame is None:
        continue
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    cv2.imshow('frame', gray)
    if cv2.waitKey(50) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
