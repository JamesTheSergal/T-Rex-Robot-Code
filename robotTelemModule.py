import cv2

class telemData():
    def __init__(self) -> None:
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
        self.battSize = 0.0
        self.voltageBatteryPercent = 0.0
        self.cpu_usage = 0
        self.ram_usage = 0
        self.cpu_temp = 0
        self.wifiSignal = "Not Available"


class commandData():
    def __init__(self):
        self.ma = 0
        self.mb = 0