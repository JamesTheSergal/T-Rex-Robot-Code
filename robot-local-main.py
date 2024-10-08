import re
import subprocess
import serial
import time
from configparser import ConfigParser
import os.path
import logging
from networkmodule import robotNetworkModule
from networkmodule import FailureType
from networkmodule import ConnModes
from robotTelemModule import telemData
from robotTelemModule import commandData
import psutil
import platform

## Set up logger

logging.basicConfig(
    filename="robotlocal.log",
    encoding="utf-8",
    filemode='a',
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.DEBUG,
)

class mcuControl():

    def __init__(self, serialPath: str) -> None:
        self.lastHeartBeatMs = round(time.time() * 1000)
        try:
            self.mcuSerial = serial.Serial(
                port=serialPath,
                baudrate=115200,
                timeout=5000
            )
        except serial.SerialException:
            logging.fatal(f'Unable to open serial port to MCU at {serialPath=} shutting down...', exc_info=True)
            exit()
        logging.debug(f'Opened serial port to MCU at {serialPath=}')

    def readMessage(self):
        data = self.mcuSerial.readline()
        time.sleep(1./120)
        if len(data) > 0:
            try:
                decoded = data.decode('utf-8').rstrip()
            except UnicodeDecodeError:
                logging.error("Received corrupt data from the MCU ->", exc_info=True)
                return ""
            return decoded
        else:
            return ""
   
    def sendMessage(self, message: str):
        message = message + "\n"
        self.mcuSerial.write(message.encode('utf-8'))
        time.sleep(1./120)

    def heartBeat(self):
        if (round(time.time() * 1000) - self.lastHeartBeatMs) > 150:
            self.sendMessage("heartbeat")
            if self.readMessage() == "heartbeat":
                pass # Cool, got good data
            else:
                logging.warning("Possible data corruption between MCU. Heartbeat did not return correct data.")
        else:
            pass
        self.lastHeartBeatMs = round(time.time() * 1000)

    def getPower(self):
        self.sendMessage("pwr")
        return self.readMessage()

class pwrSubSystem():
    def __init__(self, battSize: int):
        self.ch1volt = 0.0
        self.ch2volt = 0.0
        self.ch3volt = 0.0
        self.ch1ma = 0.0
        self.ch2ma = 0.0
        self.ch3ma = 0.0
        self.avgVolt = 0.0
        self.avgMa = 0.0
        self.totalMa = 0.0
        self.timeLeft = 0.0
        self.battSize = battSize
        self.voltageBatteryPercent = 0.0

    def utilCalc(self):
        self.avgVolt = round(((self.ch1volt + self.ch2volt + self.ch3volt) / 3), 2)
        self.avgMa = round(((self.ch1ma + self.ch2ma + self.ch3ma) / 3), 2)
        self.totalMa = self.ch1ma + self.ch2ma + self.ch3ma
        try:
            # Mapping ranges
            self.voltageBatteryPercent = 0 + (float(self.avgVolt - 9.0) / float(12.70 - 9.0) * (100 - 0))

            self.timeLeft = round(((self.battSize * (self.voltageBatteryPercent / 100)) / self.totalMa), 2) # In hours

        except ZeroDivisionError:
            logging.error("Bad data from calculated averages from MCU -> Check values from Ingest", exc_info=True)

    def ingestFromMCU(self, data: str):
        try:
            datapoints = data.split(" ")
            self.ch1volt = float(datapoints[0])
            self.ch1ma = float(datapoints[1])
            self.ch2volt = float(datapoints[2])
            self.ch2ma = float(datapoints[3])
            self.ch3volt = float(datapoints[4])
            self.ch3ma = float(datapoints[5])
        except ValueError:
            logging.error(f'Bad data from MCU ingest -> Possible data corruption {data=}', exc_info=True)
        except Exception:
            logging.error(f'Error when processing data for ingest {data=}', exc_info=True)
        self.utilCalc()

    def reportToTelem(self, telem: telemData):
        telem.ch1volt = self.ch1volt
        telem.ch2volt = self.ch2volt
        telem.ch3volt = self.ch3volt
        telem.ch1ma = self.ch1ma
        telem.ch2ma = self.ch2ma
        telem.ch3ma = self.ch3ma
        telem.avgVolt = self.avgVolt
        telem.avgMa = self.avgMa
        telem.totalMa = self.totalMa
        telem.timeLeft = self.timeLeft
        telem.battSize = telem.battSize
        telem.voltageBatteryPercent = self.voltageBatteryPercent
        return telem

class internalReporting():
    
    def __init__(self) -> None:
        self.cpu_usage = 0
        self.ram_usage = 0
        self.cpu_temp = 0
        self.wifiSignal = "Not Available"
        self.lastReport = round(time.time() * 1000)

    def update(self):
        currentTime = round(time.time() * 1000)
        if (currentTime - self.lastReport) > 15000:
            if platform.system() == "Linux":
                self.cpu_usage = psutil.cpu_percent(interval=None)
                self.ram_usage = psutil.virtual_memory().percent
                temps = psutil.sensors_temperatures()
                if "coretemp" in temps:
                    self.cpu_temp = temps["coretemp"][0].current
                result = subprocess.run(['iwconfig', "wlan0"], capture_output=True, text=True)
                signal_level = re.search(r'Signal level=(-?\d+)', result.stdout)
                if signal_level:
                    self.wifiSignal = int(signal_level.group(1))
                self.lastReport = currentTime
        
    
    def reportToTelem(self, telem: telemData):
        telem.cpu_usage = self.cpu_usage
        telem.ram_usage = self.ram_usage
        telem.cpu_temp = self.cpu_temp
        telem.wifiSignal = self.wifiSignal
        return telem

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
        
## Load configuration first

config = ConfigParser()
if os.path.isfile("robotlocal.conf"):
    config.read("robotlocal.conf")
    serialPath = config.get("connection", "mcuSerialPath")
    cameraID = config.getint("camera", "sysCamID")
    battSize = config.getint("power", "batterySize")
else:
    logging.debug("New config file generated.")
    config.read('robotlocal.conf')
    config.add_section("connection")
    config.set('connection', 'serverIP', 'IP_HERE')
    config.set('connection', 'mcuSerialPath', 'SERIALPATH')
    config.add_section("camera")
    config.set('camera', 'sysCamID', '0')
    config.add_section("power")
    config.set('power', 'batterySize', '6500')
    with open("robotlocal.conf", 'w') as f:
        config.write(f)
        print("Please finalize the config file.")
        exit()


## Initialize web server
logging.info("Starting socket server to send frames / Telem data...")
rnm = robotNetworkModule(ConnModes.SERVER, "0.0.0.0", 4421)
logging.info("Waiting for a connection before starting up MCU.")

# Wait for our client to connect
rnm.waitForConnection()


pwr = pwrSubSystem(battSize)
mcu = mcuControl(serialPath)
internal = internalReporting()
time.sleep(1)
mcu.mcuSerial.read_all() # Clears garbage from MCU reset


waitReason = False
while True:

    if waitReason is False:
        mcu.heartBeat()
        toSend = telemData()
        pwr.ingestFromMCU(mcu.getPower())
        toSend = pwr.reportToTelem(toSend)

        internal.update()
        toSend = internal.reportToTelem(toSend)

        result = rnm.sendPyObject(toSend)
        if rnm.isFailure(result):
            ishandled = handleFailure(result, rnm, toSend)
            if ishandled:
                pass
            else:
                waitReason = result

        if waitReason is False:
            result: commandData = rnm.receivePyObject()
            if rnm.isFailure(result):
                ishandled = handleFailure(result, rnm, toSend)
                if ishandled:
                    pass
                else:
                    waitReason = result
            else:
                try:
                    mcu.sendMessage(f'ma {result.ma}')
                    mcu.sendMessage(f'mb {result.mb}')
                except NameError:
                    logging.error(f'Bad data from receiving client data - Possible data corruption', exc_info=True)
                mcu.heartBeat()
        

        ## React to com Instructions
        
    else:
        if waitReason is FailureType.CON_CLOSED or FailureType.CON_TIMEOUT:
            rnm.client_socket.close()
            logging.info("Server is waiting for a new client.")
            rnm.waitForConnection()
            waitReason = False
            mcu.mcuSerial.read_all() # Clears garbage
        else:
            logging.fatal("External network error - Exiting...")
            exit()
