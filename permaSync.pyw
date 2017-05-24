#! /usr/bin/python

#Joe Snider
#3/15
#
#This is a pulser that attempts to send data to a serial port every 1-5 seconds.
#The idea is to use this to do sync pulses.
#To be as robust as possible to the port being present, it opens and closes
#  the port and recording file for every pulse.
#
#Changed 8/15 to use the newer time access
#
#Changed 11/16 to scan ports more accurately, send timing information, and have
#   backup log file.


import ctypes
import serial
import serial.tools.list_ports
import sys
import random
from PyQt4 import QtGui, QtCore
import os

import time

#wrapper class to get data from mswindows call
class FileTime(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", ctypes.c_uint),
        ("dwHighDateTime", ctypes.c_uint)]
#speed up a few calls
global getTime
getTime = ctypes.windll.kernel32.GetSystemTimePreciseAsFileTime
global getRef
getRef = ctypes.byref


#This writes to a file in a given root directory.
#The file is only locked during a write request.
#A new file is created every day, the rest of the time it is appended to.
#TODO: make this threadsafe
class safeFile():
    def __init__(self, base="c:/DataLogs/timing/log_", extension=".txt"):
        self.base = base
        self.extension = extension

        self.fil = None
        self.fname = None
        self.curDay = None

        self.subjid = ""
        self.readSubjectID()

        #this is hacked in since the format should be fixed
        self.header = """#Pulse time recorder for XBee version 0.9.0
#All times are in seconds since the UTC epoch (1/1/1601 at 12am)
#Variability from the clock itself is about 1 microsecond (on ms surface pro 3).
#requestTime can be ignored -- it includes the time to open the serial port
#
#pulseTime localTime subject requestTime\n"""
        
    def _openFile(self):
        #could be problems here if the day rolls over
        t = time.ctime().split()
        self.curDay = t[1]+"_"+t[2]+"_"+t[4]
        self.fname = self.base+"_"+self.subjid+"_"+self.curDay+self.extension
        if not os.path.isfile(self.fname):
            self.fil = open(self.fname, 'w')
            self.fil.write(self.header)
            self.fil.close()
        self.fil = open(self.fname, "a")

    def write(self, data):
        f = FileTime()
        try:
            self._openFile()
            #self.fil.write(("%20.19g "%(time.time())) + time.ctime().replace(' ', '_') + " " + self.subjid + " " + data + "\n")
            getTime(getRef(f))
            #self.fil.write(("%d%.12g "%(f.dwHighDateTime, float(f.dwLowDateTime)*1e-7)) + time.ctime().replace(' ', '_') + " " + self.subjid + " " + data + "\n")
            self.fil.write(("%20.19g "%( (f.dwHighDateTime << 32 | f.dwLowDateTime)*1e-7) ) + time.ctime().replace(' ', '_') + " " + self.subjid + " " + data + "\n")
            
            self.fil.close()
        except IOError:
            filbackup = open("emergency_ttl_backup.txt", 'a')
            filbackup.write(("%20.19g "%( (f.dwHighDateTime << 32 | f.dwLowDateTime)*1e-7) ) + time.ctime().replace(' ', '_') + " " + self.subjid + " " + data + "\n")
            filbackup.close()
            return -1
        return 1

    def readSubjectID(self):
        try:
            fil = open("c:/DataLogs/subject_id.txt", 'r')
            for line in fil:
                self.subjid = line.strip()
        except IndexError:
            print "Subject is empty"
        except IOError:
            print "Unable to open subject file"

#has a small QT UI
class portPulser(QtGui.QMainWindow):
    def __init__(self, fil):
        self.historyfile = safeFile(base='c:/DataLogs/timing/history_')

        QtGui.QMainWindow.__init__(self, None)
        self.setWindowTitle("PP")

        self.fil = fil
        self.mapPort()

        self.suspend = False
        self.errorLabel = ""

        self.low = 1
        self.high = 5
        self.nextTime = time.time() + self.low

        self.createUI()

    def createUI(self):
        self.widget = QtGui.QWidget(self)
        self.setCentralWidget(self.widget)

        self.hbuttonbox = QtGui.QHBoxLayout()
        self.suspendbutton = QtGui.QPushButton("Suspend")
        self.suspendbutton.setStyleSheet("background-color: green")
        self.hbuttonbox.addWidget(self.suspendbutton)
        self.connect(self.suspendbutton, QtCore.SIGNAL("clicked()"),
                     self._handleSuspend)
        
        self.hbuttonbox.addStretch(1)

        self.comLabel = QtGui.QLabel(self.port)

        self.vboxlayout = QtGui.QVBoxLayout()
        
        self.vboxlayout.addWidget(self.comLabel)
        self.vboxlayout.addLayout(self.hbuttonbox)

        self.widget.setLayout(self.vboxlayout)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1)
        self.timer.start()
        
        self.connect(self.timer, QtCore.SIGNAL("timeout()"),
                     self._updateUI)

    def _updateUI(self):
        self.comLabel.setText(self.port  + self.errorLabel)
        pulseDelay = 0.2#seconds, about double the pulse width set on the black box

        if time.time() > self.nextTime:
            if not self.suspend:
                #open the port (may be slow, but don't worry about blocking)
                try:
                    ser = serial.Serial(self.port, timeout=1)
                    f=FileTime()
                    getTime(getRef(f))
                    
                    #tm = time.time()
                    ser.write(chr(255))
                    time.sleep(pulseDelay)
                    '''ser.write(chr(f.dwLowDateTime & 0xff))
                    time.sleep(pulseDelay)
                    ser.write(chr(f.dwLowDateTime >> 8 & 0xff))
                    time.sleep(pulseDelay)
                    ser.write(chr(f.dwLowDateTime >> 16 & 0xff))
                    time.sleep(pulseDelay)
                    ser.write(chr(f.dwLowDateTime >> 24 & 0xff))
                    time.sleep(pulseDelay)
                    ser.write(chr(f.dwHighDateTime & 0xff))
                    time.sleep(pulseDelay)
                    ser.write(chr(f.dwHighDateTime >> 8 & 0xff))
                    time.sleep(pulseDelay)
                    ser.write(chr(f.dwHighDateTime >> 16 & 0xff))
                    time.sleep(pulseDelay)
                    ser.write(chr(f.dwHighDateTime >> 24 & 0xff))'''
                    ser.close()
                    #self.fil.write("%20.19g"%(tm))
                    #self.fil.write("%d%.12g "%(f.dwHighDateTime, float(f.dwLowDateTime)*1e-7))
                    if self.fil.write("%20.19g "%( (f.dwHighDateTime << 32 | f.dwLowDateTime)*1e-7) ) < 0:
                        self.errorLabel = "  Write Error"
                    else:
                        self.errorLabel = ""
                except serial.serialutil.SerialException:
                    #rescan the ports and try again
                    self.errorLabel = "  Port Error"
                    self.mapPort()
            self.nextTime = time.time() + random.randint(self.low, self.high)
            self.historyfile.write("next time "+str(self.nextTime)+". current time "+str(time.time()))
            self.historyfile.write("Suspend state: "+str(self.suspend))
            #print "next time ",self.nextTime,". current time ",time.time()
        
    def _handleSuspend(self):
        if self.suspend:
            self.suspend = False
            self.suspendbutton.setStyleSheet("background-color: green")
            self.errorLabel = ""
        else:
            self.suspend = True
            self.suspendbutton.setStyleSheet("background-color: red")
            self.errorLabel = "  suspended"

    def mapPort(self):
        self.port = ""
        ports = serial.tools.list_ports_windows.comports()
        for p, desc, hwid in ports:
            #print "rescan port:", p, desc, hwid, hwid.find("VID:PID")
            self.historyfile.write("rescan port: "+str(p)+" "+str(desc)+" "+str(hwid)+" "+str(hwid.find("VID:PID")))
            if hwid.find("VID:PID") >= 0:
                #print "gh0"
                self.port = p
        self.errorLabel = " using port "+self.port
        self.historyfile.write(self.errorLabel)


if __name__=='__main__':
    s1 = safeFile()

    app = QtGui.QApplication(sys.argv)
    player = portPulser(s1)
    #player.show()
    player.resize(400, 120)
    sys.exit(app.exec_())

