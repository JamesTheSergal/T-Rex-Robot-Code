import cv2
import socket
import pickle
import struct
from robotTelemModule import telemData
from robotTelemModule import commandData

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('192.168.1.162', 4222))

while True:
    packet = client_socket.recv(8)
    if not packet:
        break
    (length,) = struct.unpack('>Q', packet)
    data = b''
    while len(data) < length:
        # doing it in batches is generally better than trying
        # to do it all in one go, so I believe.
        to_read = length - len(data)
        data += client_socket.recv(
            4096 if to_read > 4096 else to_read)
        
    receivedTelem: telemData = pickle.loads(data)

    # Build image
    
    viewport = cv2.putText(
        img=receivedTelem.remoteCapture,
        text=f'Avg Voltage: {receivedTelem.avgVoltage}',
        org=(00, 20),
        fontFace=cv2.FONT_HERSHEY_DUPLEX,
        fontScale=0.50,
        color=(0,0,0),
        thickness=2)
    
    viewport = cv2.putText(
        img=viewport,
        text=f'Total Amps: {receivedTelem.totalMa / 1000}A',
        org=(00, 40),
        fontFace=cv2.FONT_HERSHEY_DUPLEX,
        fontScale=0.50,
        color=(0,0,0),
        thickness=2)
    
    viewport = cv2.putText(
        img=viewport,
        text=f'Battery Percent: {round(receivedTelem.voltageBatteryPercent,2)}%',
        org=(00, 60),
        fontFace=cv2.FONT_HERSHEY_DUPLEX,
        fontScale=0.50,
        color=(0,0,0),
        thickness=2)
    
    viewport = cv2.putText(
        img=viewport,
        text=f'Time Left: {receivedTelem.timeLeft}Hr',
        org=(00, 80),
        fontFace=cv2.FONT_HERSHEY_DUPLEX,
        fontScale=0.50,
        color=(0,0,0),
        thickness=2)

    cv2.imshow("Remote", viewport)

    controls = commandData()

    keypress = cv2.waitKey(12)
    if keypress == 13:
        break
    elif keypress == 97: # A key
        controls.ma = 60
        controls.mb = 60
    elif keypress == 100: # D Key
        controls.ma = -60
        controls.mb = -60
    elif keypress == 119: # W Key
        controls.ma = -60
        controls.mb = 60
    elif keypress == 115: # S Key
        controls.ma = 60
        controls.mb = -60

    

    packed = pickle.dumps(controls)
    length = struct.pack('>Q', len(packed))
    client_socket.sendall(length)
    client_socket.sendall(packed)

cv2.destroyAllWindows()