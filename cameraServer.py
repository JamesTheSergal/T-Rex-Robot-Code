import cv2
import logging
from networkmodule import robotNetworkModule
from networkmodule import FailureType
from networkmodule import ConnModes

logging.basicConfig(
    filename="cameraServer.log",
    encoding="utf-8",
    filemode='a',
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.DEBUG,
)

def handleFailure(result, networkManager: robotNetworkModule, associatedData):
    logging.info("handleFailure() was called")
    if result == FailureType.CON_CLOSED:
        result = rnm.attemptReconnection()
        if rnm.isFailure(result):
            logging.info("Connection was closed by client. We will wait for another client.")
            return False
        else:
            return True
    if result == FailureType.CON_TIMEOUT:
        result = rnm.attemptReconnection()
        if rnm.isFailure(result):
            logging.error("Connection keeps timing out. Cannot continue.")
            return False
        else:
            return True
    if result == FailureType.SOCKET_ERROR:
        logging.error("Received socket failure error signal. Cannot handle this exception!")
        return False
    if result == FailureType.UNPACK:
        logging.warning("Received bad data! Handler cannot handle this exception - Not fatal.")
        return True
    if result == FailureType.RECONNECTED:
        logging.info("Network Manager reconnected automatically. Will attempt to resend data. (If there is any)")
        if associatedData is not None:
            result = networkManager.sendPyObject(associatedData)
            if networkManager.isFailure(result):
                logging.error(f'Failed to resend data - {result}')
                return False
            else:
                return True
        else:
            return True


cameraID = 0
try:
    logging.info("cv2 is attempting to open the camera...")
    cap = cv2.VideoCapture(cameraID)
    logging.info("Camera opened sucessfully.")
except Exception:
    logging.fatal(f'cv2 cannot open camera {cameraID=} - This error is fatal', exc_info=True)
    exit()

# Start server
rnm = robotNetworkModule(ConnModes.SERVER, "0.0.0.0", 4422)
if rnm.successfulConnection == True:
    logging.info("Server is ready - Waiting on a client.")
    rnm.waitForConnection()
else:
    logging.fatal("Server failed to start. Check networking logs.")
    exit()


waitReason = False
# Main Loop
while True:
    if waitReason is False:
        ret, frame = cap.read()
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]  # Quality from 0 to 100
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        result = rnm.sendPyObject(buffer)
        if rnm.isFailure(result):
            ishandled = handleFailure(result, rnm, frame)
            if ishandled:
                pass
            else:
                waitReason = result
    else:
        if waitReason is FailureType.CON_CLOSED or FailureType.CON_TIMEOUT:
            rnm.client_socket.close()
            logging.info("Server is waiting for a new client.")
            rnm.waitForConnection()
            waitReason = False
        else:
            logging.fatal("External network error - Exiting...")
            exit()
