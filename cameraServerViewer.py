import cv2
import socket
import pickle
import struct
import time

import numpy as np
from robotTelemModule import telemData
from robotTelemModule import commandData
from networkmodule import robotNetworkModule
from networkmodule import FailureType
from networkmodule import ConnModes

rnm = robotNetworkModule(ConnModes.CLIENT, "192.168.1.163", 4422)
if rnm.successfulConnection == True:
    pass
else:
    exit()

while True:
    
    received = rnm.receivePyObject()
    decoded_image = cv2.imdecode(received, 1)

    if rnm.isFailure(decoded_image):
        exit()
    else:
        pass
    

    cv2.imshow("Remote", decoded_image)

    keypress = cv2.waitKey(1)
    if keypress == 13:
        break



cv2.destroyAllWindows()