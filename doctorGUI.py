
import sys
from PyQt4 import QtGui, QtCore

import serial
from serial.tools import list_ports

import time
import datetime
import threading
import Queue
import math

import logging
#create file handler
loghandler = logging.Filehandler("doctorGUIlog.log")
loghandler.setLevel(logging.DEBUG)

#set and create logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

#create logging format
logformatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
loghandler.setFormatter(logformatter)

#add handler to logger
logger.addHandler(loghandler)
#logger disable to propagate message to terminal
logger.propagate = True

#logger example
#logger.debug("message")
#logger.info("Message")
#logger.error("Message", exec_info=True) by exec true traceback is dumped to logfile
#used in try/except in except statement

class Doctor(QtGui.QWidget):
    def __init__(self):
        super(Doctor, self).__init__()
        self.initUI()

    def initUI(self):

        #qbtn = QtGui.QPushButton('Quit', self)
        #qbtn.clicked.connect(QtCore.QCoreApplication.instance().quit)
        #qbtn.resize(qbtn.sizeHint())
        #qbtn.move(50, 50)

        connectButton = QtGui.QPushButton('Connect',self)

        statevbox = QtGui.QVBoxLayout()

        unitvbox = QtGui.QVBoxLayout()

        graphsvbox = QtGui.QVBoxLayout()

        upperhbox = QtGui.QHBoxLayout()
        upperhbox.addLayout(statevbox)
        upperhbox.addStretch(1)
        upperhbox.addLayout(unitvbox)
        upperhbox.addStretch(1)
        upperhbox.addLayout(graphsvbox)
		
        lowerhbox = QtGui.QHBoxLayout()
        lowerhbox.addStretch(1)
        lowerhbox.addWidget(connectButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(upperhbox)
        vbox.addLayout(lowerhbox)

        self.setLayout(vbox)

        #self.resize(250, 150)
        self.center_window()
        self.setWindowTitle('MCU Telemetry')
        self.setWindowIcon(QtGui.QIcon('web.png'))

        self.show()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)

        qp.end()

#    def drawStates(self, qp):

def main():
    
    app = QtGui.QApplication(sys.argv)
    doc = Doctor()
	    	
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
