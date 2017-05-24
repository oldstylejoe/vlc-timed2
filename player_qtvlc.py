#! /usr/bin/python

#
# Qt example for VLC Python bindings
# Copyright (C) 2009-2010 the VideoLAN team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
#

import ctypes
import os
import sys
#import user
import vlc
from PyQt5 import QtGui, QtCore, QtWidgets

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

#modify a file with today's date.
#File is kept open for quicker access.
#try to flush occasionally
class safishFile:
    def __init__(self, base="c:/DataLogs/timing/movielog_", extension=".txt"):
        self.base = base
        self.extension = extension

        self.fil = None
        self.fname = None
        self.curDay = None

        self.subjid = ""
        self.readSubjectID()
        
        #this is hacked in since the format should be fixed
        self.header = """#Movie recorder. Wraps VLC and marks the time when each
#event vlc.EventType.MediaPlayerPositionChanged occurs (a frame was rendered)
#frame is in fractions of the movie (zero to one).
#frameTime (last column) is in seconds since the UTC epoch (1/1/1601 at 12am)
#Variability from the clock itself is about 1 microsecond (on ms surface pro 3).
#requestTime can be ignored -- it is a deprecated call to python's time.time
#
#requestTime localTime subject movie frame frameTime\n"""

        self._openFile()

    def _openFile(self):
        #could be problems here if the day rolls over
        t = time.ctime().split()
        self.curDay = t[1]+"_"+t[2]+"_"+t[4]
        self.fname = self.base+self.subjid+self.curDay+self.extension
        if not os.path.isfile(self.fname):
            self.fil = open(self.fname, 'w')
            self.fil.write(self.header)
            self.fil.close()
        self.fil = open(self.fname, "a")

    def readSubjectID(self):
        try:
            fil = open("c:/DataLogs/subject_id.txt", 'r')
            for line in fil:
                self.subjid = line.strip()
        except IndexError:
            print("Subject is empty")
        except IOError:
            print("Unable to open subject file")

    def write(self, data):
        try:
            self._openFile()
            self.fil.write(("%20.19g "%(time.time())) + time.ctime().replace(' ', '_') + " " + self.subjid + " " + data + "\n")
        except IOError:
            return -1
        return 1

class Player(QtWidgets.QMainWindow):
    """A simple Media Player using VLC and Qt
    """
    def __init__(self, master=None):
        QtWidgets.QMainWindow.__init__(self, master)

        self.fil = safishFile()
        self.mediaName = ""
        
        self.setWindowTitle("Media Player")

        # creating a basic vlc instance
        self.instance = vlc.Instance()
        # creating an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()

        self.event_manager = self.mediaplayer.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.pos_callback, self.mediaplayer)

        self.createUI()
        self.isPaused = False
        self.setMouseTracking(True)
        self.playervalue = 0

        #mouse tracking isn't working on the player for some reason.
        #Use vlc's built in mouse position thing, and just test it on the UI thread.
        self.mouseX, self.mouseY = 0,0

    def pos_callback(self, event, player):
        f=FileTime()
        getTime(getRef(f))
        self.fil.write(self.mediaName + \
                       " %20.19g %20.19g"%(player.get_position(), \
                                      float(f.dwHighDateTime << 32 | f.dwLowDateTime)*1e-7))

    def createUI(self):
        """Set up the user interface, signals & slots
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        # In this widget, the video will be drawn
        if sys.platform == "darwin": # for MacOS
            self.videoframe = QtWidgets.QMacCocoaViewContainer(0)
        else:
            self.videoframe = QtWidgets.QFrame()
        self.palette = self.videoframe.palette()
        self.palette.setColor (QtGui.QPalette.Window,
                               QtGui.QColor(0,0,0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.hbuttonbox = QtWidgets.QHBoxLayout()
        self.playbutton = QtWidgets.QPushButton("Play")
        self.playbutton.clicked.connect(self.PlayPause)
        ft = self.playbutton.font()
        ft.setPointSize(20)
        self.playbutton.setFont(ft)
        self.playbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.playbutton.setIconSize(QtCore.QSize(60,60))
        self.playbutton.setStyleSheet("background-color: green")
        self.hbuttonbox.addWidget(self.playbutton)

        self.stopbutton = QtWidgets.QPushButton("Stop")
        self.stopbutton.clicked.connect(self.Stop)
        ft.setPointSize(20)
        self.stopbutton.setFont(ft)
        self.stopbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stopbutton.setIconSize(QtCore.QSize(60,60))
        self.hbuttonbox.addWidget(self.stopbutton)

        self.openbutton = QtWidgets.QPushButton("Open")
        self.openbutton.clicked.connect(self.OpenFile)
        ft.setPointSize(20)
        self.openbutton.setFont(ft)
        self.openbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
        self.openbutton.setIconSize(QtCore.QSize(60,60))
        self.hbuttonbox.addWidget(self.openbutton)

        #self.hbuttonbox.addStretch(1)
        
        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.positionslider.setToolTip("Position")
        self.positionslider.setMinimum(0)
        self.positionslider.setMaximum(1000)
        self.positionslider.actionTriggered.connect(self.setPosition)
        self.positionslider.setStyleSheet("""
        QSlider:horizontal {
            min-height: 48px;
        }

        QSlider::groove:horizontal {
            height: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
            margin: 2px 0px;
        }
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
            border: 1px solid #5c5c5c;
            width: 60px;
            margin: -20px -10px; 
        }
QSlider::add-page:qlineargradient {
background: lightgrey;
border-top-right-radius: 9px;
border-bottom-right-radius: 9px;
border-top-left-radius: 0px;
border-bottom-left-radius: 0px;
}

QSlider::sub-page:qlineargradient {
background: darkgrey;
border-top-right-radius: 0px;
border-bottom-right-radius: 0px;
border-top-left-radius: 9px;
border-bottom-left-radius: 9px;
}        """)
        self.hbuttonbox.addWidget(self.positionslider)

        self.exitbutton = QtWidgets.QPushButton("Exit")
        self.exitbutton.clicked.connect(self.Exit)
        ft.setPointSize(20)
        self.exitbutton.setFont(ft)
        self.exitbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserStop))
        self.exitbutton.setIconSize(QtCore.QSize(60,60))
        self.hbuttonbox.addWidget(self.exitbutton)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addLayout(self.hbuttonbox)
        self.vboxlayout.addWidget(self.videoframe)
        self.setMouseTracking(True)

        self.widget.setLayout(self.vboxlayout)

        '''self.open = QtWidgets.QAction("&Open", self)
        self.open.triggered.connect(self.OpenFile)
        self.exit = QtWidgets.QAction("&Exit", self)
        self.exit.triggered.connect(self.Exit)
        menubar = self.menuBar()
        filemenu = menubar.addMenu("&File")
        filemenu.addAction(self.open)
        filemenu.addSeparator()
        filemenu.addAction(self.exit)'''

        #some of the widgets will be hidden after a certain time
        self.hideMe = [self.positionslider,
                       self.playbutton, self.openbutton, self.stopbutton, self.exitbutton]
        self.delayHide = 5000000000000 #seconds
        self.minHideTime = 1
        self.hideTime = [time.time()+self.minHideTime, time.time() + self.delayHide]
        self.hidden = False

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.updateUI)

    def  mouseMoveEvent(self, event):
        #print("mouse move")
        self.unhide()
    def hide(self):
        if not self.hidden:
            for w in self.hideMe:
                w.hide()
            self.hidden = True
        self.hideTime = [time.time()+self.minHideTime, time.time() + self.delayHide]
    def unhide(self):
        if self.hidden:
            for w in self.hideMe:
                w.show()
            self.hidden = False
        self.hideTime = [time.time()+self.minHideTime, time.time() + self.delayHide]

    def PlayPause(self):
        """Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
            self.playbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
            self.playbutton.setStyleSheet("background-color: green")
            self.isPaused = True
        else:
            if self.mediaplayer.play() == -1:
                self.OpenFile()
                return
            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.playbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
            self.playbutton.setStyleSheet("background-color: none")
            self.timer.start()
            self.isPaused = False

    def Stop(self):
        """Stop player
        """
        if self.mediaplayer.is_playing():
            self.PlayPause()
        self.mediaplayer.stop()

    def OpenFile(self, filename=None):
        """Open a media file in a MediaPlayer
        """
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", "C:/Public/Videos")[0]
        '''if filename is None:
            filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", "C:/Public/Videos")
        if not filename:
            return'''

        # create the media
        self.media = self.instance.media_new(filename)
        # put the media in the media player
        self.mediaplayer.set_media(self.media)

        # parse the metadata of the file
        self.media.parse()
        # set the title of the track as window title
        self.setWindowTitle(self.media.get_meta(0))
        self.mediaName = filename.replace(' ', '_')

        # the media player has to be 'connected' to the QFrame
        # (otherwise a video would be displayed in it's own window)
        # this is platform specific!
        # you have to give the id of the QFrame (or similar object) to
        # vlc, different platforms have different functions for this
        if sys.platform == "linux2": # for Linux using the X Server
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32": # for Windows
            self.mediaplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin": # for MacOS
            self.mediaplayer.set_nsobject(self.videoframe.winId())
        self.PlayPause()

    def setPosition(self):
        """Set the position
        """
        # setting the position to where the slider was dragged
        if self.mediaplayer.is_playing():
            self.mediaplayer.set_position(self.positionslider.sliderPosition() / 1000.0)
        # the vlc MediaPlayer needs a float value between 0 and 1, Qt
        # uses integer variables, so you need a factor; the higher the
        # factor, the more precise are the results
        # (1000 should be enough)

    def updateUI(self):
        """updates the user interface"""
        # setting the slider to the desired position
        self.positionslider.setValue(self.mediaplayer.get_position() * 1000)

        if not self.hidden and  time.time() > self.hideTime[1]:
            self.hide()

        x, y = self.mediaplayer.video_get_cursor()
        if self.mouseX != x and time.time() > self.hideTime[0]:  #only check x in case of vertical stretching
            self.unhide()
        self.mouseX, self.mouseY = x,y

        if not self.mediaplayer.is_playing():
            # no need to call this function if nothing is played
            self.timer.stop()
            if not self.isPaused:
                # after the video finished, the play button stills shows
                # "Pause", not the desired behavior of a media player
                # this will fix it
                self.Stop()

            self.unhide()

    def Exit(self):
        #self.Stop()
        if self.mediaplayer.is_playing():
            self.mediaplayer.stop()
        sys.exit()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    player = Player()
    player.showFullScreen()
    #player.resize(640, 480)
    #player.show()
    if sys.argv[1:]:
        player.OpenFile(sys.argv[1])
    sys.exit(app.exec_())
