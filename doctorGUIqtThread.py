
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

class GenericThread(QtCore.QThread):
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

class SerialThread(QtCore.QThread):
    def __init__(self, parent):	
        QtCore.QThread.__init__(self, parent)
        self._stop = False				# flag to stop thread
        self.commReady = False
        self.parent = parent
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
            self.parent.connectButton.setText("Disconnect")
            logger.info('Connected to port '+ str(port))

    def run (self):						# class which is automatically called after __init__
        newFrame = False
        oldFrame = ''
        oldData = ''
        while self._stop == False:
            logger.debug('Worker serial read')

            if self._stop:						# if thread terminated, do not read serial data again (n is flag to not read data)
                n = 0
                
            else:
                n = self.ser.inWaiting()			# check if something in serial buffer

            if n:							# read/write serial buffer
                try:
                    newData = self.ser.read(n)
                    logger.debug('W got data: \n' + repr(newData))

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
                        logger.debug('W Data going to Queue')
                        self.emit(QtCore.SIGNAL('serialData(PyQt_PyObject)'), oldData)
                        #oldData = ''
                        newFrame = False
                n = 0;
            time.sleep(0.5)

    def toggleStop(self):
        self._stop = True
        self.ser.close()
        logger.info("Serial Data worker stopped")
        self.parent.connectButton.setText("Connect")
        self.parent.connectStatLabel.setText("Disconnected")


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

        self.loggingData = False		# flag for logging button and logging data

        self.initUI()

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
        if not self.connectButtonState:
            self.connectButtonState = True
            self.serialThread = SerialThread(self)
            self.serialThread.start()

            self.connect(self.serialThread, QtCore.SIGNAL('serialData(PyQt_PyObject)'), self.processQueueData)
            logger.info('Thread started...')

        else:
            self.connectButtonState = False
            self.serialThread.toggleStop()
    
            if self.loggingData:
                self.loggingData = False
                self.logFile.closeFile()
                self.parent.logButton.setText("Log Data")
    
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
            self.parent.logButton.setText("Logging")

    def processQueueData(self, data):
        logger.debug("Got data from serial for processing")
        rawData = data
        startChar = rawData.find('\x80\x80')
        if (startChar != -1) and (rawData[startChar+92] == '\x9F'):

            UART_TX_Mode = ord(rawData[2])
            LC_State = ord(rawData[3])
            BootState = ord(rawData[4])
            Ticks = ord(rawData[5])
            ADC_I2C1_Enable = ord(rawData[6])   # in binary
            ADC_I2C2_Enable = ord(rawData[7])   # in binary
            PORTD = ord(rawData[8])             # in binary

            PID_CP_Enabled = ord(rawData[9])
            I2C_ADC_ColdPlate_NTC = (256*ord(rawData[10]) + ord(rawData[11]))
            PID_CP_Zpoint = (256*ord(rawData[12]) + ord(rawData[13]))
            PID_CP_Output = (256*ord(rawData[14]) + ord(rawData[15]))
            PID_CP_Error = (16777216*ord(rawData[16])+65536*ord(rawData[17])+256*ord(rawData[18])+ord(rawData[19]))/10
            PID_CP_Integral = (16777216*ord(rawData[20])+65536*ord(rawData[21])+256*ord(rawData[22])+ord(rawData[23]))/10
            PID_CP_x = (16777216*ord(rawData[24])+65536*ord(rawData[25])+256*ord(rawData[26])+ord(rawData[27]))/10

            PID_Laser_Enabled = ord(rawData[29])
            I2C_ADC_Laser_NTC = (256*ord(rawData[30]) + ord(rawData[31]))
            PID_Laser_Zpoint = (256*ord(rawData[32]) + ord(rawData[33]))
            PID_Laser_Output = (256*ord(rawData[34]) + ord(rawData[35]))
            PID_Laser_Error = (16777216*ord(rawData[36])+65536*ord(rawData[37])+256*ord(rawData[38])+ord(rawData[39]))/10
            PID_Laser_Integral = (16777216*ord(rawData[40])+65536*ord(rawData[41])+256*ord(rawData[42])+ord(rawData[43]))/10
            PID_Laser_x = (16777216*ord(rawData[44])+65536*ord(rawData[45])+256*ord(rawData[46])+ord(rawData[47]))/10
            
            PID_AMP_Enabled = ord(rawData[49])
            PID_Spec_level = (256*ord(rawData[50]) + ord(rawData[51]))
            PID_AMP_Zpoint = (256*ord(rawData[52]) + ord(rawData[53]))
            PID_AMP_Output = (256*ord(rawData[54]) + ord(rawData[55]))
            PID_AMP_Error = (16777216*ord(rawData[56])+65536*ord(rawData[57])+256*ord(rawData[58])+ord(rawData[59]))/10
            PID_AMP_Integral = (16777216*ord(rawData[60])+65536*ord(rawData[61])+256*ord(rawData[62])+ord(rawData[63]))/10
            PID_AMP_x = (16777216*ord(rawData[64])+65536*ord(rawData[65])+256*ord(rawData[66])+ord(rawData[67]))/10
            PID_OSC_Output = (16777216*ord(rawData[68])+65536*ord(rawData[69])+256*ord(rawData[70])+ord(rawData[71]))/10

            WindEyeState = ord(rawData[73])
            desState = ord(rawData[74])
            oldState = ord(rawData[75])
            Change_status = ord(rawData[76])


            print("RAWDATA len "+str(len(rawData)))

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

        self.connectButtonState = False
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
        self.connect(self.logButton, QtCore.SIGNAL("clicked()"), self.OnPressLog)
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
