from tkinter import *
import tkinter.messagebox 
from networkmodule import robotNetworkModule
from networkmodule import FailureType
from networkmodule import ConnModes
from robotTelemModule import telemData
from robotTelemModule import commandData



class robotControl():
    
    def __init__(self) -> None:
        
        # Tk Items
        self.ip = tkinter.StringVar()
        self.port = tkinter.StringVar()
        self.ip_box = None
        self.port_box = None

        self.avgVolt = tkinter.StringVar()
        self.totalMa = tkinter.StringVar()
        self.timeLeft = tkinter.StringVar()
        self.voltageBatteryPercent = tkinter.StringVar()
        self.cpu_usage = tkinter.StringVar()
        self.cpu_temp = tkinter.StringVar()
        self.wifiSignal = tkinter.StringVar()

        # Internal States
        self.forward = False
        self.back = False
        self.left = False
        self.right = False
        self.right_track = False
        self.left_track = False
        self.right_track_reverse = False
        self.left_track_reverse = False
        self.forward_value = 60
        self.turn_value = 60
        self.ma = 0
        self.mb = 0

        # Network
        self.rnm = None
    
    def connect(self):
        self.rnm = robotNetworkModule(ConnModes.CLIENT, self.ip.get(), int(self.port.get()))
        if self.rnm.successfulConnection == True:
            self.ip_box.config(state="disabled")
            self.port_box.config(state="disabled")
            pass
        else:
            tkinter.messagebox.showerror("Failed to Connect", "Couldn't connect to supplied IP address. Check logs.")
            exit()
        
    def reset_direction(self):
        self.forward = False
        self.back = False
        self.left = False
        self.right = False
        self.right_track = False
        self.left_track = False
        self.right_track_reverse = False
        self.left_track_reverse = False

    def forward_pressed(self, val):
        self.forward = True

    def back_pressed(self, val):
        self.back = True

    def left_pressed(self, val):
        self.left = True

    def right_pressed(self, val):
        self.right = True

    def left_track_pressed(self, val):
        self.left_track = True

    def right_track_pressed(self, val):
        self.right_track = True

    def left_track_back(self, val):
        self.left_track_reverse = True

    def right_track_back(self, val):
        self.right_track_reverse = True

    def updateForwardSpeed(self, val):
        self.forward_value = int(val)

    def updateTurnSpeed(self, val):
        self.turn_value = int(val)

    def deriveControl(self):
        self.ma = 0
        self.mb = 0

        if self.forward:
            self.ma = self.forward_value
            self.mb = self.forward_value

        else:
            if self.right:
                self.ma = self.turn_value
                self.mb = -self.turn_value

            if self.left:
                self.ma = -self.turn_value
                self.mb = self.turn_value
            
            if self.right_track:
                self.mb = self.forward_value

            if self.left_track:
                self.ma = self.forward_value

            if self.right_track_reverse:
                self.mb = -self.forward_value
            
            if self.left_track_reverse:
                self.ma = -self.forward_value

        
        if self.back:
            self.ma = -self.forward_value
            self.mb = -self.forward_value
        
        

        # Finally adjust for motor polarity
        self.ma = -self.ma
        self.mb = self.mb

    def robotLoop(self):
        if self.rnm is not None:
            received: telemData = self.rnm.receivePyObject()

            if self.rnm.isFailure(received):
                tkinter.messagebox.showerror("Receive Failure", "An unhandled exception occured. Check logs.")
                exit()
            else:
                self.avgVolt.set(str(received.avgVolt)+"V")
                self.totalMa.set(str(round((received.totalMa / 1000),3)) +"A")
                self.timeLeft.set(str(received.timeLeft)+"H")
                self.voltageBatteryPercent.set(str(round(received.voltageBatteryPercent, 2))+"%")
                self.cpu_usage.set(str(received.cpu_usage)+"%")
                self.cpu_temp.set(str(received.cpu_temp)+"C")
                self.wifiSignal.set(str(received.wifiSignal)+" dbm")


            self.deriveControl()

            command = commandData()
            command.ma = self.ma
            command.mb = self.mb
            self.rnm.sendPyObject(command)
            self.reset_direction()
            m.after(8, rc.robotLoop)
        else:
            m.after(15, rc.robotLoop)


m = Tk()
rc = robotControl()
m.title("Robot Telemetry")

Label(m, text="IP Address").grid(row=0)
Label(m, text="Port").grid(row=1)

ip_en = Entry(m, textvariable=rc.ip)
ip_en.grid(row=0, column=1)

port = Entry(m, textvariable=rc.port)
port.grid(row=1, column=1)

connect = Button(m, text="Connect", width=15, command=rc.connect).grid(row=1, column=2) # Can add ,command=r.destroy

rc.ip_box = ip_en
rc.port_box = port

Label(m, text="Forward Speed").grid(row=2, column=0)
forward_speed = Scale(m, from_=0, to=255, orient=HORIZONTAL, command=rc.updateForwardSpeed).grid(row=2, column=1)

Label(m, text="Turn Speed").grid(row=2, column=2)
turn_speed = Scale(m, from_=0, to=255, orient=HORIZONTAL, command=rc.updateTurnSpeed).grid(row=2, column=3)

# Telem data
Label(m, text="System Avg Voltage: ").grid(row=3, column=0)
Label(m, text="System Total Amps: ").grid(row=3, column=2)
Label(m, text="System Est Hours left: ").grid(row=3, column=4)

Label(m, textvariable=rc.avgVolt).grid(row=3, column=1)
Label(m, textvariable=rc.totalMa).grid(row=3, column=3)
Label(m, textvariable=rc.timeLeft).grid(row=3, column=5)

Label(m, text="Volt Battery Percent: ").grid(row=4, column=0)
Label(m, text="CPU Usage: ").grid(row=4, column=2)
Label(m, text="CPU Temp: ").grid(row=4, column=4)

Label(m, textvariable=rc.voltageBatteryPercent).grid(row=4, column=1)
Label(m, textvariable=rc.cpu_usage).grid(row=4, column=3)
Label(m, textvariable=rc.cpu_temp).grid(row=4, column=5)

Label(m, text="WiFi Strength: ").grid(row=5, column=0)


Label(m, textvariable=rc.wifiSignal).grid(row=5, column=1)


m.bind("w", rc.forward_pressed)
m.bind("s", rc.back_pressed)
m.bind("a", rc.left_pressed)
m.bind("d", rc.right_pressed)
m.bind("e", rc.right_track_pressed)
m.bind("q", rc.left_track_pressed)
m.bind("c", rc.right_track_back)
m.bind("z", rc.left_track_back)
m.after(15, rc.robotLoop)
m.mainloop()
rc.rnm.server_socket.close()