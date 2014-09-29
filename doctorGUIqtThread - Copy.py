
import sys, os
from PyQt4 import QtGui, QtCore

import serial
from serial.tools import list_ports

import time
import datetime
import threading
import Queue
import math

import pyqtgraph as pg
import numpy as np

import logging
#create file handler
loghandler = logging.FileHandler("doctorGUIlog.log")
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

class GenericThread(QtCore.Qthread):
    def __init__(self, function, *args, **kwargs):
        QtCore.QThread.__init__(self)
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def __del__(self):
        self.wait()

    def run(self):
        self.function(*self.args, **self.kwargs)
        return

class MyProcess(threading.Thread):
    def __init__(self, parent, queueData, queueComm, queueEff):	
        threading.Thread.__init__(self)
        self._stop = False				# flag to stop thread
        self.commReady = False
        self.parent = parent
        self.queueData = queueData
        self.queueComm = queueComm
        self.queueEff = queueEff
        try:
            port = str(self.parent.comPortComboBox.currentText())
            port = int(port[3:])
#            baud = (self.parent.boxBaud.get()).split()
            print port
            baud = "115200"
            self.ser = serial.Serial(port-1, baudrate=int(baud), timeout=0, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
        except serial.SerialException:
            logger.error('Cannot open port', exc_info=True)	# by exc_info=True traceback is dumped to the logger
            self._stop = True
        else:	
            self.parent.connectStatLabel.setText(u'Connected to ' + str(port))
            logger.info('Connected to port '+ str(port))

    def run (self):						# class which is automatically called after __init__
        newFrame = False
        oldFrame = ''
        oldData = ''
        while self._stop == False:
            logger.debug('Worker serial read')

            if self.queueComm.empty() == False:			# reading queue from GUI
                dataComm = self.queueComm.get()
                logger.debug('Message to Worker: '+dataComm)

                if dataComm == 'S':				# checking if command to destroy thread appears
                    self._stop = True
                    self.ser.close()
                    logger.info('Worker stop command from Queue')

                else:
                    self.commReady = True			# if not, letting know something to process appears instead

            if self._stop:						# if thread terminated, do not read serial data again (n is flag to not read data)
                n = 0
            else:
                n = self.ser.inWaiting()			# check if something in serial buffer

            if n:							# read/write serial buffer
                try:
                    newData = self.ser.read(n)
                    logger.debug('W got data: ' + repr(newData))

                except serial.SerialException:
                    logger.error('Worker cannot read Serial Port !!!')

                else:
                    if newFrame:
                        oldData = oldData+newData

                    if newData[0] == '\x80' and newData[1] == '\x80':
                        newFrame = True
                        oldData = ''
                        oldData = newData

                        #logger.debug('W New Frame: ' + repr(newData))
                        logger.debug('W New Frame')
					
                    if (len(oldData)>92):
                        if self.queueData.empty():
                            logger.debug('W Data going to Queue')
                            self.queueData.put(oldData)
                            oldData = ''
                            newFrame = False
                        else:
                            logger.debug("Queue full, data DISCARTED")
                n = 0;
            time.sleep(0.5)


class FileOperations():
    def openFile(self, name):
        self.file = open(name, 'w')

    def writeToFile(self, string):
        self.file.write(string+'\n')

    def closeFile(self):
        self.file.close()


class Doctor(QtGui.QWidget):
    def __init__(self):
        super(Doctor, self).__init__()

        self.queueData = Queue.Queue(maxsize=100) # create queue
        self.queueComm = Queue.Queue(maxsize=20) # create queue
        self.queueEff = Queue.Queue(maxsize=3)	 # create queue

        self.loggingData = False		# flag for logging button and logging data

        self.initUI()

        #self.updtPortsList()

    def updtPortsList(self):
        print "updt"
        index = self.comPortComboBox.currentIndex()
        #self.comPortComboBox.blockSignals(True)
        boxPortList = []
        boxPortList = list(self.SearchPorts())
        if boxPortList:
            self.comPortComboBox.clear()
            self.comPortComboBox.addItems(boxPortList)
            self.comPortComboBox.setCurrentIndex(index)
        #self.comPortComboBox.blockSignals(False)

    def SearchPorts(self):
        if os.name == 'nt':
            #windows
            for i in range(256):
                try:
                    s = serial.Serial(i)
                    s.close()
                    yield 'COM' + str(i + 1)
                    #self.buttonConnect['state'] = 'active' NOTE!!!
                except serial.SerialException:
                    pass
        else:
            #unix
            for port in list_ports.comports():
                yield port[0]

    def OnPressConnect(self):
        self.connector = MyProcess(self, self.queueData, self.queueComm, self.queueEff)
        self.connector.daemon = True
        self.connector.start()

        logger.info('Thread started...')

        #self.processQueueData()

    def OnPressDisconnect(self):
        self.queueComm.put('S')

        try:
            self.after_cancel(self.queueDataID)
        except:
            pass
        try:
            self.after_cancel(self.rotateArrowsID)
        except:
            pass

        self.connector.join()

        if self.loggingData:
            self.loggingData = False
            self.logFile.closeFile()
            self.buttonLog['text'] = 'Log Data'

    def OnPressLog(self):
        if self.loggingData:
            self.loggingData = False
            self.logFile.closeFile()

        else:
            t = time.strftime('%Y_%m_%d %H_%M_%S') #can add _%M', gmtime()) for GMT time
            filename = str(t)+'.txt'
            self.logFile = FileOperations()
            self.logFile.openFile(filename)
            self.loggingData = True

    def initUI(self):

        #qbtn = QtGui.QPushButton('Quit', self)
        #qbtn.clicked.connect(QtCore.QCoreApplication.instance().quit)
        #qbtn.resize(qbtn.sizeHint())
        #qbtn.move(50, 50)

        self.receivedDataLabel = QtGui.QLabel('Received Data')
        self.logButton = QtGui.QPushButton('Log Data', self)

        uppesthbox = QtGui.QHBoxLayout()
        uppesthbox.addWidget(self.receivedDataLabel)
        uppesthbox.addWidget(self.logButton)


        
        statevbox = QtGui.QVBoxLayout()

        unitvbox = QtGui.QVBoxLayout()

        graphsvbox = QtGui.QVBoxLayout()

        upperhbox = QtGui.QHBoxLayout()
        upperhbox.addLayout(statevbox)
        upperhbox.addStretch(1)
        upperhbox.addLayout(unitvbox)
        upperhbox.addStretch(1)
        upperhbox.addLayout(graphsvbox)
		
        
        self.connectStatLabel = QtGui.QLabel('Disconnected')
        self.comPortComboBox = QtGui.QComboBox()
        self.comPortComboBox.addItem("Search")
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("highlighted(int)"), self.updtPortsList)
        #self.comPortComboBox.activated.connect(self.updtPortsList)

        self.baudRateComboBox = QtGui.QComboBox()
        self.connectButton = QtGui.QPushButton('Connect', self)
        #self.connect(self.connectButton, QtCore.SIGNAL("highlighted(int)"), self.updtPortsList)

        lowerhbox = QtGui.QHBoxLayout()
        lowerhbox.addWidget(self.connectStatLabel)
        lowerhbox.addStretch(1)
        lowerhbox.addWidget(self.comPortComboBox)
        lowerhbox.addWidget(self.baudRateComboBox)
        lowerhbox.addWidget(self.connectButton)


        vbox = QtGui.QVBoxLayout()              # MAIN Box
        vbox.addLayout(uppesthbox)
        vbox.addLayout(upperhbox)
        vbox.addLayout(lowerhbox)
        vbox.addStretch(1)

        self.setLayout(vbox)

        self.connect(self.connectButton, QtCore.SIGNAL("clicked()"), self.OnPressConnect)
        self.connect(self.comPortComboBox, QtCore.SIGNAL("activated(int)"), self.updtPortsList)
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.comPortComboBox, QtCore.SLOT("blockSignals(False)"))
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.comPortComboBox.blockSignals(False))

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

#    def drawStates(self, qp):

def main():
    
    app = QtGui.QApplication(sys.argv)
    doc = Doctor()
	    	
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
