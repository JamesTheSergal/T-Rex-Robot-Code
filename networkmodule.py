import socket
import pickle
import logging
import struct
from enum import Enum




class ConnModes(Enum):
    CLIENT = 1
    SERVER = 2

class FailureType(Enum):
    NONE = 0
    CON_CLOSED = 1
    CON_TIMEOUT = 2
    SOCKET_ERROR = 3
    UNPACK = 4
    RECONNECTED = 5

class robotNetworkModule:

    def __init__(self, mode: ConnModes, address, port) -> None:

        self.mode = mode
        self.address = address
        self.port = port
        self.successfulConnection = False
        self.client_socket = None
        self.client_address = None

        self.server_socket = None
        self.server_address = None

        if mode == ConnModes.CLIENT:

            logging.basicConfig(
                filename="robotnetworkclient.log",
                encoding="utf-8",
                filemode='a',
                format="{asctime} - {levelname} - {message}",
                style="{",
                datefmt="%Y-%m-%d %H:%M",
                level=logging.DEBUG,
            )

            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.settimeout(10)
                self.server_socket.connect((address, port))
                self.successfulConnection = True
            except socket.timeout:
                logging.fatal(f'Could not connect to the server at {address}:{port}', exc_info=True)
            except socket.error:
                logging.fatal("A fatal socket error has occured", exc_info=True)


        if mode == ConnModes.SERVER:

            logging.basicConfig(
                filename="robotnetworkserver.log",
                encoding="utf-8",
                filemode='a',
                format="{asctime} - {levelname} - {message}",
                style="{",
                datefmt="%Y-%m-%d %H:%M",
                level=logging.DEBUG,
            )

            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.bind((address, port))
                self.successfulConnection = True
            except socket.error:
                logging.fatal("A fatal socket error has occured", exc_info=True)
                

            self.sock.listen()
            logging.info(f'Server is listening on {address}:{port}...')
            
        if mode != ConnModes.CLIENT or mode != ConnModes.SERVER:
            logging.error("No proper mode selected. Check your code.")

    def attemptReconnection(self):
        if self.mode == ConnModes.CLIENT:
            logging.info("On the fly reconnect requested for client. Attempting to reconnect...")
            try:
                self.server_socket.connect((self.address, self.port))
            except socket.timeout:
                logging.error("Server failed to respond. TIMEOUT. Unable to reconnect to server.")
                return FailureType.CON_TIMEOUT
            except socket.error:
                logging.error("Failed to open connection.", exc_info=True)
                return FailureType.SOCKET_ERROR
            logging.info("Reconnected successfully...")
            return FailureType.RECONNECTED
        if self.mode == ConnModes.SERVER:
            logging.info("On the fly reconnect requested for server. (We lost our client) Passing signal for outside code to handle reconnection.")
            return FailureType.CON_CLOSED

    def handleNoData(self):
        logging.warning(f'Did not receive any data when expected. Connection closed abruptly.')
        result = self.attemptReconnection()
        if result == FailureType.CON_CLOSED:
            return FailureType.CON_CLOSED
        if result == FailureType.CON_TIMEOUT:
            logging.error("Unable to reconnect to server after retry (CON_TIMEOUT). Handing off to outside code to handle.")
            return FailureType.CON_TIMEOUT
        if result == FailureType.SOCKET_ERROR:
            logging.error("Unable to reconnect to server after retry (SOCKET_ERROR) Handing off to outside code to handle.")
            return FailureType.SOCKET_ERROR
        if result == FailureType.RECONNECTED:
            return FailureType.RECONNECTED

    def waitForConnection(self):
        if self.mode == ConnModes.SERVER:
            logging.debug("Server is waiting for a connection... (This is blocking)")
            self.client_socket, self.client_address = self.sock.accept()
            logging.info(f'Server has accepted a connection from -> {self.client_address}')
            return True
        else:
            logging.debug("waitForConnection() was called in Client mode. Please check your code.")
            return False
        
    def sendPyObject(self, ObjToSend):

        # Since sending these objects is the same for server and client
        # We will just make sure we are referencing the same socket

        if self.mode == ConnModes.SERVER:
            sock = self.client_socket
        if self.mode == ConnModes.CLIENT:
            sock = self.server_socket    

        packed = pickle.dumps(ObjToSend)
        length = struct.pack('<Q', len(packed))

        # Attempt to send the length of data we are about to send
        try:
            sock.sendall(length)
            # Hopefully the client has received the data. We will send the rest of our data
            sock.sendall(packed)
        except socket.timeout:
            logging.error("Attempting to send data has timed out ->", exc_info=True)
            return FailureType.CON_TIMEOUT
        except BrokenPipeError:
            logging.error("BrokenPipe - Socket connection was closed for some reason ->", exc_info=True)
            return FailureType.CON_CLOSED
        except ConnectionResetError:
            logging.error("Connection was reset by remote ->", exc_info=True)
            return FailureType.CON_CLOSED
        except socket.error:
            logging.error("Attempting to send data has failed ->", exc_info=True)
            return FailureType.SOCKET_ERROR
        return FailureType.NONE
    
    def receivePyObject(self):

        # Since receiving these objects is the same for server and client
        # We will just make sure we are referencing the same socket

        if self.mode == ConnModes.SERVER:
            sock = self.client_socket
        if self.mode == ConnModes.CLIENT:
            sock = self.server_socket  

        length = sock.recv(8) # Get length of content client is sending
        if not length: # Handle possible abrupt disconnection.
            return self.handleNoData()
        
        try:    
            (length,) = struct.unpack('<Q', length) # TODO: This can error out if our data is bad
        except struct.error:
            logging.error(f'Unpack of data for content length -> {length} has failed. This indicates corrupted/bad data.')
            return FailureType.UNPACK

        data = b''
        while len(data) < length:
            # doing it in batches is generally better than trying
            # to do it all in one go, so I believe.
            to_read = length - len(data)
            received = sock.recv(
                4096 if to_read > 4096 else to_read)
            if not received:
                return self.handleNoData()
            data += received
            
        unpacked = pickle.loads(data) # Turn back into a python object
        return unpacked
    
    def isFailure(self, check):
        if isinstance(check, FailureType):
            failureEnums = [FailureType.CON_CLOSED, FailureType.CON_TIMEOUT, FailureType.SOCKET_ERROR, FailureType.UNPACK, FailureType.RECONNECTED]
            if check in failureEnums:
                return True
            else:
                return False
        else:
            return False