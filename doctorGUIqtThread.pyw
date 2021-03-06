
import sys, os
from PyQt4 import QtGui, QtCore

import serial
from serial.tools import list_ports

import time
import math

import pyqtgraph as pg

import logging
#create file handler
loghandler = logging.FileHandler("doctorGUI.log")
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
            port = int(port[3:])-1
#            baud = (self.parent.boxBaud.get()).split()
            baud = self.parent.baudRateComboBox.currentText()
            self.ser = serial.Serial(port, baudrate=int(baud), timeout=0, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
        except serial.SerialException:
            logger.error('Cannot open port', exc_info=True)	# by exc_info=True traceback is dumped to the logger
            self._stop = True
        else:	
            self.parent.connectStatLabel.setText(u'Connected to ' + str(port))
            self.parent.connectButton.setText("Disconnect")
            logger.info('Connected to port '+ str(port))

    def run (self):						# class which is automatically called after __init__
        commCounter = 0
        newFrame = False
        oldFrame = ''
        oldData = ''
        indicator = '-\|/'
        counter = 0
        self.frameData = ''
        self.frameToggle = False

        while self._stop == False:
            logger.debug('Worker serial read')

            if self._stop:						# if thread terminated, do not read serial data again (n is flag to not read data)
                n = 0
                
            else:
                if (commCounter > 0) and self.frameToggle:
                    try:
                        self.ser.write(self.frameData)
                    except serial.SerialException:
                        logger.error("Could not write to serial port")
                    else:
                        logger.debug('Data SENT to SERIAL')
                    finally:
                        self.frameToggle = False
                        self.frameData = ''

                n = self.ser.inWaiting()			# check if something in serial buffer

                if n:							# read/write serial buffer
                    commCounter = 0
                    try:
                        newData = self.ser.read(n)
                        logger.debug('W got data: \n' + repr(newData))
                        logger.debug('W got data')

                    except serial.SerialException:
                        logger.error('Worker cannot read Serial Port !!!')

                    else:
                        if newFrame:
                            oldData = oldData+newData

                        if len(newData)>2:
                            if newData[0] == '\x80' and newData[1] == '\x80':

                                newFrame = True
                                oldData = ''
                                oldData = newData

                                #logger.debug('W New Frame: ' + repr(newData))
                                logger.debug('W New Frame')

                            else:
                                if newFrame == False:
                                    self.parent.receivedDataLabel.setText("Corrupted data received")
			    		
                        if (len(oldData)>104):
                            logger.debug('W Data going to Queue')
                            self.parent.receivedDataLabel.setText(indicator[counter])
                            counter += 1
                            if counter == 4:
                                counter = 0
                            self.emit(QtCore.SIGNAL('serialData(PyQt_PyObject)'), oldData)
                            oldData = ''
                            newFrame = False
                else:
                    commCounter += 1

                n = 0;
            time.sleep(0.1)

    def toggleStop(self):
        self._stop = True
        self.ser.close()
        logger.info("Serial Data worker stopped")
        self.parent.connectButton.setText("Connect")
        self.parent.connectStatLabel.setText("Disconnected")

    def toggleFrame(self):
        self.frameToggle = True
        self.frameData = '\x53'

    def toggleON(self):
        self.frameToggle = True
        self.frameData = '\x31'

    def toggleOFF(self):
        self.frameToggle = True
        self.frameData = '\x30'

    def toggleIDLE(self):
        self.frameToggle = True
        self.frameData = '\x35'

    def toggleFLASH(self):
        self.frameToggle = True
        self.frameData = '\x38'


class FileOperations():
    def openFile(self, name):
        self.file = open(name, 'w')

    def writeToFile(self, string):
        self.file.write(string+'\n')

    def closeFile(self):
        self.file.close()

class unitImage(QtGui.QGraphicsPixmapItem):

    def __init__(self):
        super(unitImage, self).__init__()
        self.setPixmap(QtGui.QPixmap("unit.png"))

class UnitView(QtGui.QGraphicsView):

    def __init__(self, parent):
        super(UnitView, self).__init__()
        self.setBackgroundBrush(QtGui.QColor(0, 0, 0))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.initScene()

    def initScene(self):
        self.scene = QtGui.QGraphicsScene(self)
        self.setSceneRect(0, 0, 510, 734)

        self.image = unitImage()
        self.scene.addItem(self.image)

        #self.lBeam = self.scene.addRect(50,50,10,30)
        #self.lBeam.setBrush(QtGui.QColor(200,10,10))
        #self.lBeam.rotate(45)

        #self.lBeam = self.scene.addEllipse(75, 71, 10, 10)
        #self.lBeam.setBrush(QtGui.QColor(255,49,47))

        self.lBeam = self.scene.addLine(158, 127, 218, 101)
        brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
        self.lBeam.setPen(QtGui.QPen(brush, 3))
        
        #self.rBeam = self.scene.addEllipse(162, 70, 10, 10)
        #self.rBeam.setBrush(QtGui.QColor(255,49,47))

        self.rBeam = self.scene.addLine(288, 102, 347, 127)
        brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
        self.rBeam.setPen(QtGui.QPen(brush, 3))

        self.hHeater = self.scene.addLine(162, 155, 200, 260)
        brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
        self.hHeater.setPen(QtGui.QPen(brush, 3))

        self.i2c2 = self.scene.addLine(67, 458, 143, 458)
        brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
        self.i2c2.setPen(QtGui.QPen(brush, 3))

        self.i2c1 = self.scene.addLine(229, 615, 319, 615)
        brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
        self.i2c1.setPen(QtGui.QPen(brush, 3))

        self.i2c1LaserNTC = self.scene.addEllipse(196, 519, 7, 7)
        self.i2c1LaserNTC.setBrush(QtGui.QColor(255,49,47))
        
        self.i2c1CpNTC = self.scene.addEllipse(211, 519, 7, 7)
        self.i2c1CpNTC.setBrush(QtGui.QColor(255,49,47))

        self.i2c1Pd_ADC = self.scene.addEllipse(226, 519, 7, 7)
        self.i2c1Pd_ADC.setBrush(QtGui.QColor(255,49,47))

        self.HWAMP_enabled = self.scene.addEllipse(191, 489, 15, 15)
        self.HWAMP_enabled.setBrush(QtGui.QColor(255,49,47))
        
        self.HWOSC_enabled = self.scene.addEllipse(208, 489, 15, 15)
        self.HWOSC_enabled.setBrush(QtGui.QColor(255,49,47))

        self.HWTEC_enabled = self.scene.addEllipse(223, 489, 15, 15)
        self.HWTEC_enabled.setBrush(QtGui.QColor(255,49,47))

        self.CP_enabled = self.scene.addEllipse(192,558, 25, 25)
        self.CP_enabled.setBrush(QtGui.QColor(255,49,47))

        self.setScene(self.scene)

    def hHeaterSet(self, state):
        if state == 1:
            brush = QtGui.QBrush(QtGui.QColor("#13FF5C"))
            self.hHeater.setPen(QtGui.QPen(brush, 3))

        elif state == 0:
            brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
            self.hHeater.setPen(QtGui.QPen(brush, 3))

    def beamsSet(self, state):
        if state == 0:
            brushGreen = QtGui.QBrush(QtGui.QColor("#13FF5C"))
            brushRed = QtGui.QBrush(QtGui.QColor("#FF312F"))
            self.lBeam.setPen(QtGui.QPen(brushRed, 3))
            self.rBeam.setPen(QtGui.QPen(brushGreen, 3))
            #self.lBeam.setBrush(QtGui.QColor(255,49,47))
            #self.rBeam.setBrush(QtGui.QColor(20,255,92))
        elif state == 1:
            brushGreen = QtGui.QBrush(QtGui.QColor("#13FF5C"))
            brushRed = QtGui.QBrush(QtGui.QColor("#FF312F"))
            self.rBeam.setPen(QtGui.QPen(brushRed, 3))
            self.lBeam.setPen(QtGui.QPen(brushGreen, 3))
            #self.rBeam.setBrush(QtGui.QColor(255,49,47))
            #self.lBeam.setBrush(QtGui.QColor(20,255,92))
        else:
            brushRed = QtGui.QBrush(QtGui.QColor("#FF312F"))
            self.lBeam.setPen(QtGui.QPen(brushRed, 3))
            self.rBeam.setPen(QtGui.QPen(brushRed, 3))
            #self.lBeam.setBrush(QtGui.QColor(255,49,47))
            #self.rBeam.setBrush(QtGui.QColor(255,49,47))

    def i2c1Set(self, state):
        if state == 0:
            brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
            self.i2c1.setPen(QtGui.QPen(brush, 3))
            self.i2c1LaserNTC.setBrush(QtGui.QColor(255,49,47))
            self.i2c1CpNTC.setBrush(QtGui.QColor(255,49,47))
            self.i2c1Pd_ADC.setBrush(QtGui.QColor(255,49,47))
        else:
            brush = QtGui.QBrush(QtGui.QColor("#13FF5C"))
            self.i2c1.setPen(QtGui.QPen(brush, 3))
            state = bin(state)[2:]
            state = map(int, list(state))
            while len(state) < 3:
                state.insert(0, 0)
            for x in xrange(len(state)):
                if state[x] == 1:
                    if x == 0:
                        self.i2c1LaserNTC.setBrush(QtGui.QColor(20,255,92))
                    elif x == 1:
                        self.i2c1CpNTC.setBrush(QtGui.QColor(20,255,92))
                    elif x == 2:
                        self.i2c1Pd_ADC.setBrush(QtGui.QColor(20,255,92))
                else:
                    if x == 0:
                        self.i2c1LaserNTC.setBrush(QtGui.QColor(255,49,47))
                    elif x == 1:
                        self.i2c1CpNTC.setBrush(QtGui.QColor(255,49,47))
                    elif x == 2:
                        self.i2c1Pd_ADC.setBrush(QtGui.QColor(255,49,47))

    def i2c2Set(self, state):
        if state == 0:
            brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
            self.i2c2.setPen(QtGui.QPen(brush, 3))
        else:
            brush = QtGui.QBrush(QtGui.QColor("#13FF5C"))
            self.i2c2.setPen(QtGui.QPen(brush, 3))
            
    def portdSet(self, state):
        if state == 0:
            brush = QtGui.QBrush(QtGui.QColor("#FF312F"))
            self.HWAMP_enabled.setBrush(QtGui.QColor(255,49,47))
            self.HWOSC_enabled.setBrush(QtGui.QColor(255,49,47))
            self.HWTEC_enabled.setBrush(QtGui.QColor(255,49,47))
            self.CP_enabled.setBrush(QtGui.QColor(255,49,47))
        else:
            state = bin(state)[2:]
            state = map(int, list(state))
            while len(state) < 8:
                state.insert(0, 0)
            for x in xrange(len(state)):
                if state[x] == 1:
                    if x == 5:
                        self.HWTEC_enabled.setBrush(QtGui.QColor(20,255,92))
                    elif x == 4:
                        self.CP_enabled.setBrush(QtGui.QColor(20,255,92))
                    elif x == 3:
                        self.HWAMP_enabled.setBrush(QtGui.QColor(255,49,47))
                    elif x == 2:
                        self.HWOSC_enabled.setBrush(QtGui.QColor(255,49,47))

                else:
                    if x == 5:
                        self.HWTEC_enabled.setBrush(QtGui.QColor(255,49,47))
                    elif x == 4:
                        self.CP_enabled.setBrush(QtGui.QColor(255,49,47))
                    elif x == 3:
                        self.HWAMP_enabled.setBrush(QtGui.QColor(20,255,92))
                    elif x == 2:
                        self.HWOSC_enabled.setBrush(QtGui.QColor(20,255,92))

class stateImage(QtGui.QGraphicsPixmapItem):

    def __init__(self):
        super(stateImage, self).__init__()
        self.setPixmap(QtGui.QPixmap("states.png"))

class StateView(QtGui.QGraphicsView):

    def __init__(self, parent):
        super(StateView, self).__init__()
        self.setBackgroundBrush(QtGui.QColor(0, 0, 0))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.initScene()

    def initScene(self):
        self.scene = QtGui.QGraphicsScene(self)
        self.setSceneRect(0, 0, 400, 734)

        self.image = stateImage()
        self.scene.addItem(self.image)

        self.boot = self.scene.addEllipse(177, 326, 20, 20)
        self.boot.setBrush(QtGui.QColor(255,49,47))
        
        self.off = self.scene.addEllipse(177,407,20,20)
        self.off.setBrush(QtGui.QColor(255,49,47))
        
        self.idle = self.scene.addEllipse(177,487,20,20)
        self.idle.setBrush(QtGui.QColor(255,49,47))

        self.flash = self.scene.addEllipse(177,568,20,20)
        self.flash.setBrush(QtGui.QColor(255,49,47))
        
        self.normal = self.scene.addEllipse(77,387,40,40)
        self.normal.setBrush(QtGui.QColor(255,49,47))

        self.setScene(self.scene)

    def change(self, state):
        self.clear()
        if state == 'boot':
            self.boot.setBrush(QtGui.QColor(10,200,10))
        elif state == 'off':
            self.off.setBrush(QtGui.QColor(10,200,10))
        elif state == 'idle':
            self.idle.setBrush(QtGui.QColor(10,200,10))
        elif state == 'flash':
            self.flash.setBrush(QtGui.QColor(10,200,10))
        elif state == 'on':
            self.normal.setBrush(QtGui.QColor(10,200,10))
    
    def desire(self, state):
        if state == 'boot':
            self.boot.setBrush(QtGui.QColor(232,192,36))
        elif state == 'off':
            self.off.setBrush(QtGui.QColor(232,192,36))
        elif state == 'idle':
            self.idle.setBrush(QtGui.QColor(232,192,36))
        elif state == 'flash':
            self.flash.setBrush(QtGui.QColor(232,192,36))
        elif state == 'on':
            self.normal.setBrush(QtGui.QColor(232,192,36))

    def clear(self):
        self.boot.setBrush(QtGui.QColor(200,10,10))
        self.off.setBrush(QtGui.QColor(200,10,10))
        self.idle.setBrush(QtGui.QColor(200,10,10))
        self.flash.setBrush(QtGui.QColor(200,10,10))
        self.normal.setBrush(QtGui.QColor(200,10,10))


class ReFrame(QtGui.QDialog):
    def __init__(self, frame=[]):
        super(ReFrame, self).__init__()
        self.Ref_frame = frame

        self.zero = False
        self.frame = []
        self.textBrowser = QtGui.QTextBrowser(self)
        for i in range(1025):
            if i == 1:
                self.zero = True
            if i<1024:
                self.frame.append(self.Ref_frame[i])
            if (((i+1) % 4) == 0) and (self.zero == True):
                self.textBrowser.append(str(self.frame))
                self.frame = []

        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.addWidget(self.textBrowser)


class Doctor(QtGui.QWidget):
    def __init__(self):
        super(Doctor, self).__init__()

        self.loggingData = False		# flag for logging button and logging data

        self.initUI()

    def updtPortsList(self):
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
                self.logButton.setText("Log Data")
    
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


    def frameButtonClicked(self):
        self.serialThread.toggleFrame()

    def onButtonClicked(self):
        self.serialThread.toggleON()

    def offButtonClicked(self):
        self.serialThread.toggleOFF()

    def idleButtonClicked(self):
        self.serialThread.toggleIDLE()

    def flashButtonClicked(self):
        self.serialThread.toggleFLASH()

    def showButtonClicked(self):
        self.dialogReFrame = ReFrame(self.Ref_frame)
        self.dialogReFrame.exec_()


    #def unitChanged(self):
    #    self.unit.repaint()

    def convertNTC(self, value):
        val0 = (value * 3.3) / 32767.0
        u1 = 3.3 - val0
        i1 = u1 / 10000.0
        try:
            Rt = val0 / i1
        except:
            Rt = val0
        try:
            mid1 = math.log(10000.0 / Rt)
        except:
            pass
            return False
        else:
            mid2 = 3988.0 / mid1
            mid3 = mid2 * (-298.15)
            mid4 = 298.15 - mid2
            result = (mid3 / mid4) - 273.15

            return result


    def processQueueData(self, data):
        logger.debug("Got data from serial for processing")
        rawData = data
        startChar = rawData.find('\x80\x80')
        if (startChar != -1) and (rawData[startChar+104] == '\x9F'):

            self.oldUART_TX_Mode = self.UART_TX_Mode
            self.UART_TX_Mode = ord(rawData[2])

            self.LC_State = ord(rawData[3])

            self.oldBootState = self.BootState
            self.BootState = ord(rawData[4])

            self.oldTicks = self.Ticks
            self.Ticks = ord(rawData[5])

            self.oldADC_I2C1_Enable = self.ADC_I2C1_Enable
            self.ADC_I2C1_Enable = ord(rawData[6])   # in binary

            self.oldADC_I2C2_Enable = self.ADC_I2C2_Enable
            self.ADC_I2C2_Enable = ord(rawData[7])   # in binary

            self.oldPORTD = self.PORTD
            self.PORTD = ord(rawData[8])             # in binary

            self.oldPID_CP_Enabled = self.PID_CP_Enabled
            self.PID_CP_Enabled = ord(rawData[9])
            self.I2C_ADC_ColdPlate_NTC = (256*ord(rawData[10]) + ord(rawData[11]))
            self.PID_CP_Zpoint = (256*ord(rawData[12]) + ord(rawData[13]))
            PID_CP_Output = (256*ord(rawData[14]) + ord(rawData[15]))
            PID_CP_Error = (16777216*ord(rawData[16])+65536*ord(rawData[17])+256*ord(rawData[18])+ord(rawData[19]))
            if ord(rawData[16]) > 127:
                PID_CP_Error -= 4294967296
            PID_CP_Error = PID_CP_Error/10

            PID_CP_Integral = (16777216*ord(rawData[20])+65536*ord(rawData[21])+256*ord(rawData[22])+ord(rawData[23]))
            if ord(rawData[20]) > 127:
                PID_CP_Integral -= 4294967296
            PID_CP_Integral = PID_CP_Integral/10

            PID_CP_x = (16777216*ord(rawData[24])+65536*ord(rawData[25])+256*ord(rawData[26])+ord(rawData[27]))
            if ord(rawData[24]) > 127:
                PID_CP_x -= 4294967296
            PID_CP_x = PID_CP_x/10


            self.oldPID_Laser_Enabled = self.PID_Laser_Enabled
            self.PID_Laser_Enabled = ord(rawData[29])
            self.I2C_ADC_Laser_NTC = (256*ord(rawData[30]) + ord(rawData[31]))
            self.PID_Laser_Zpoint = (256*ord(rawData[32]) + ord(rawData[33]))
            PID_Laser_Output = (256*ord(rawData[34]) + ord(rawData[35]))
            PID_Laser_Error = (16777216*ord(rawData[36])+65536*ord(rawData[37])+256*ord(rawData[38])+ord(rawData[39]))
            if ord(rawData[36]) > 127:
                PID_Laser_Error -= 4294967296
            PID_Laser_Error = PID_Laser_Error/10

            PID_Laser_Integral = (16777216*ord(rawData[40])+65536*ord(rawData[41])+256*ord(rawData[42])+ord(rawData[43]))
            if ord(rawData[40]) > 127:
                PID_Laser_Integral -= 4294967296
            PID_Laser_Integral = PID_Laser_Integral/10

            PID_Laser_x = (16777216*ord(rawData[44])+65536*ord(rawData[45])+256*ord(rawData[46])+ord(rawData[47]))
            if ord(rawData[44]) > 127:
                PID_Laser_x -= 4294967296
            PID_Laser_x = PID_Laser_x/10

            
            self.oldPID_AMP_Enabled = self.PID_AMP_Enabled
            self.PID_AMP_Enabled = ord(rawData[49])
            PID_Spec_level = (256*ord(rawData[50]) + ord(rawData[51]))
            PID_AMP_Zpoint = (256*ord(rawData[52]) + ord(rawData[53]))
            PID_AMP_Output = (256*ord(rawData[54]) + ord(rawData[55]))
            PID_AMP_Error = (16777216*ord(rawData[56])+65536*ord(rawData[57])+256*ord(rawData[58])+ord(rawData[59]))
            if ord(rawData[56]) > 127:
                PID_AMP_Error -= 4294967296
            PID_AMP_Error = PID_AMP_Error/10

            PID_AMP_Integral = (16777216*ord(rawData[60])+65536*ord(rawData[61])+256*ord(rawData[62])+ord(rawData[63]))/10 # Remove /10
            #if ord(rawData[60]) > 127:
            #    PID_AMP_Integral -= 4294967296
            #PID_AMP_Integral = PID_AMP_Integral/10

            PID_AMP_x = (16777216*ord(rawData[64])+65536*ord(rawData[65])+256*ord(rawData[66])+ord(rawData[67]))
            if ord(rawData[64]) > 127:
                PID_AMP_x -= 4294967296
            PID_AMP_x = PID_AMP_x/10

            PID_OSC_Output = (16777216*ord(rawData[68])+65536*ord(rawData[69])+256*ord(rawData[70])+ord(rawData[71]))
            if ord(rawData[68]) > 127:
                PID_OSC_Output -= 4294967296

            self.oldChange_status = self.Change_status
            self.Change_status = ord(rawData[72])

            self.oldWindEyeState = self.WindEyeState
            self.WindEyeState = ord(rawData[73])

            self.olddesState = self.desState
            self.desState = ord(rawData[74])

            self.oldLC_Pulse_Counter = self.LC_Pulse_Counter
            self.LC_Pulse_Counter = (256*ord(rawData[75]) + ord(rawData[76]))
            
            self.oldhHeater = self.hHeater
            self.hHeater = ord(rawData[77])
            
            self.State_Counter_value = (256*ord(rawData[78]) + ord(rawData[79]))

            self.oldRef_transferred = self.Ref_transferred
            self.Ref_transferred = (256*ord(rawData[80]) + ord(rawData[81]))

            self.oldFlash_errors = self.Flash_errors
            self.Flash_errors = (256*ord(rawData[82]) + ord(rawData[83]))

            self.oldReg_errors = self.Reg_errors
            self.Reg_errors = (256*ord(rawData[84]) + ord(rawData[85]))

            self.oldFrame_rcvd = self.Frame_rcvd
            self.Frame_rcvd = (256*ord(rawData[87]) + ord(rawData[88]))
            
            self.oldVersion = self.Version
            self.Version = (str(ord(rawData[101])) + "." + str(ord(rawData[102])))


            if self.oldhHeater != self.hHeater:
                self.unitView.hHeaterSet(self.hHeater)

            if self.UART_TX_Mode != self.oldUART_TX_Mode:
                if self.UART_TX_Mode == 1:
                    self.UART_TX_Mode_label.setText('Diagnostic')
                elif self.UART_TX_Mode == 2:
                    self.UART_TX_Mode_label.setText('Registers')
                else:
                    self.UART_TX_Mode_label.setText('None')

            if self.oldBootState != self.BootState:
                if self.BootState == 0:
                    self.BootState_label.setText('OFF')
                elif self.BootState == 1:
                    self.BootState_label.setText('ON')
                    self.stateView.change('boot')
                elif self.BootState == 2:
                    self.BootState_label.setText('FAST')
                    self.stateView.change('boot')
                else:
                    self.BootState_label.setText('None')

            if self.Ticks != self.oldTicks:
                self.Ticks_label.setText(str(self.Ticks))

            if self.BootState == 0:
                if self.oldWindEyeState != self.WindEyeState:
                    if self.WindEyeState == 48:
                        self.stateView.change('off')
                    elif self.WindEyeState == 49:
                        self.stateView.change('on')
                    elif self.WindEyeState == 53:
                        self.stateView.change('idle')
                    elif self.WindEyeState == 56:
                        self.stateView.change('flash')
            
            if self.desState != self.WindEyeState:
                if self.olddesState != self.desState:
                    if self.desState == 48:
                        self.stateView.desire('off')
                    elif self.desState == 49:
                        self.stateView.desire('on')
                    elif self.desState == 53:
                        self.stateView.desire('idle')
                    elif self.desState == 56:
                        self.stateView.desire('flash')

            if self.oldChange_status != self.Change_status:
                if self.Change_status == 0:
                    self.Change_status_label.setText('CHANGED')
                elif self.Change_status == 1:
                    self.Change_status_label.setText('CHANGE')
                elif self.Change_status == 2:
                    self.Change_status_label.setText('CHANGING')
                else:
                    self.Change_status_label.setText('NONE')

            self.State_counter_label.setText(str(self.State_Counter_value))
            self.LC_Pulse_label.setText(str(self.LC_Pulse_Counter))

            if self.oldRef_transferred != self.Ref_transferred:
                self.Ref_transferred_label.setText(str(self.Ref_transferred))

            if self.oldFlash_errors != self.Flash_errors:
                self.Flash_errors_label.setText(str(self.Flash_errors))

            if self.oldReg_errors != self.Reg_errors:
                self.Reg_errors_label.setText(str(self.Reg_errors))

            if self.oldFrame_rcvd != self.Frame_rcvd:
                self.Frame_rcvd_label.setText(str(self.Frame_rcvd))

            if self.oldADC_I2C1_Enable != self.ADC_I2C1_Enable:
                self.unitView.i2c1Set(self.ADC_I2C1_Enable)

            if self.oldADC_I2C2_Enable != self.ADC_I2C2_Enable:
                self.unitView.i2c2Set(self.ADC_I2C2_Enable)
            
            if self.oldPORTD != self.PORTD:
                self.unitView.portdSet(self.PORTD)

            if self.oldVersion != self.Version:
                self.Version_label.setText(self.Version)

            self.unitView.beamsSet(self.LC_State)
#Graphs
            self.PID_CP_Zpoint = self.convertNTC(self.PID_CP_Zpoint)
            if self.PID_CP_Zpoint == False:
                self.PID_CP_Zpoint = self.oldPID_CP_Zpoint
            else:
                self.oldPID_CP_Zpoint = self.PID_CP_Zpoint

            self.I2C_ADC_ColdPlate_NTC = self.convertNTC(self.I2C_ADC_ColdPlate_NTC)
            if self.I2C_ADC_ColdPlate_NTC == False:
                self.I2C_ADC_ColdPlate_NTC = self.oldI2C_ADC_ColdPlate_NTC
            else:
                self.oldI2C_ADC_ColdPlate_NTC = self.I2C_ADC_ColdPlate_NTC

            self.PID_Laser_Zpoint = self.convertNTC(self.PID_Laser_Zpoint)
            if self.PID_Laser_Zpoint == False:
                self.PID_Laser_Zpoint = self.oldPID_Laser_Zpoint
            else:
                self.oldPID_Laser_Zpoint = self.PID_Laser_Zpoint

            self.I2C_ADC_Laser_NTC = self.convertNTC(self.I2C_ADC_Laser_NTC)
            if self.I2C_ADC_Laser_NTC == False:
                self.I2C_ADC_Laser_NTC = self.oldI2C_ADC_Laser_NTC
            else:
                self.oldI2C_ADC_Laser_NTC = self.I2C_ADC_Laser_NTC

            if len(self.time_np)>59:
                for x in xrange(1,60):
                    self.time_np[x-1] = self.time_np[x]

                    self.PID_CP_Zpoint_np[x-1] = self.PID_CP_Zpoint_np[x]
                    self.PID_CP_Error_np[x-1] = self.PID_CP_Error_np[x]
                    self.PID_CP_x_np[x-1] = self.PID_CP_x_np[x]
                    self.PID_CP_Integral_np[x-1] = self.PID_CP_Integral_np[x]
                    self.PID_CP_FB_np[x-1] = self.PID_CP_FB_np[x]
                    
                    self.PID_Laser_Zpoint_np[x-1] = self.PID_Laser_Zpoint_np[x]
                    self.PID_Laser_FB_np[x-1] = self.PID_Laser_FB_np[x]
                    self.PID_Laser_Error_np[x-1] = self.PID_Laser_Error_np[x]
                    self.PID_Laser_x_np[x-1] = self.PID_Laser_x_np[x]
                    
                    self.PID_AMP_Zpoint_np[x-1] = self.PID_AMP_Zpoint_np[x]
                    self.PID_AMP_FB_np[x-1] = self.PID_AMP_FB_np[x]
                    self.PID_AMP_Error_np[x-1] = self.PID_AMP_Error_np[x]
                    self.PID_AMP_Output_np[x-1] = self.PID_AMP_Output_np[x]
                    self.PID_OSC_Output_np[x-1] = self.PID_OSC_Output_np[x]

                self.time_np[59] = self.time_np[58]+1

                self.PID_CP_Zpoint_np[59] = self.PID_CP_Zpoint
                self.PID_CP_Error_np[59] = PID_CP_Error
                self.PID_CP_x_np[59] = PID_CP_x/100
                self.PID_CP_Integral_np[59] = PID_CP_Integral/100
                self.PID_CP_FB_np[59] = self.I2C_ADC_ColdPlate_NTC
                
                self.PID_Laser_Zpoint_np[59] = self.PID_Laser_Zpoint
                self.PID_Laser_FB_np[59] = self.I2C_ADC_Laser_NTC
                self.PID_Laser_Error_np[59] = PID_Laser_Error/100
                self.PID_Laser_x_np[59] = PID_Laser_x/100
                
                self.PID_AMP_Zpoint_np[59] = PID_AMP_Zpoint
                self.PID_AMP_FB_np[59] = PID_Spec_level
                self.PID_AMP_Error_np[59] = PID_AMP_Error/100
                self.PID_AMP_Output_np[59] = PID_AMP_Output/1000
                self.PID_OSC_Output_np[59] = PID_OSC_Output/1000

            else:
                self.time_np.append(len(self.time_np)+1)

                self.PID_CP_Zpoint_np.append(self.PID_CP_Zpoint)
                self.PID_CP_Error_np.append(PID_CP_Error)
                self.PID_CP_x_np.append(PID_CP_x/100)
                self.PID_CP_Integral_np.append(PID_CP_Integral/100)
                self.PID_CP_FB_np.append(self.I2C_ADC_ColdPlate_NTC)
                
                self.PID_Laser_Zpoint_np.append(self.PID_Laser_Zpoint)
                self.PID_Laser_FB_np.append(self.I2C_ADC_Laser_NTC)
                self.PID_Laser_Error_np.append(PID_Laser_Error/100)
                self.PID_Laser_x_np.append(PID_Laser_x/100)

                self.PID_AMP_Zpoint_np.append(PID_AMP_Zpoint)
                self.PID_AMP_FB_np.append(PID_Spec_level)
                self.PID_AMP_Error_np.append(PID_AMP_Error/100)
                self.PID_AMP_Output_np.append(PID_AMP_Output/100)
                self.PID_OSC_Output_np.append(PID_OSC_Output/100)
        
            self.PID_CP_Zpoint_curve.setData(self.time_np, self.PID_CP_Zpoint_np, pen=(0,0,255), name='Desire value')
            self.PID_CP_Error_curve.setData(self.time_np, self.PID_CP_Error_np, pen=(255,0,0), name='Error')
            self.PID_CP_Output_curve.setData(self.time_np, self.PID_CP_x_np, pen=(0,255,0), name='Action Value')
            self.PID_CP_Integral_curve.setData(self.time_np, self.PID_CP_Integral_np, pen=(255,255,255), name='Integral')
            self.PID_CP_FB_curve.setData(self.time_np, self.PID_CP_FB_np, pen=(255,255,0), name='Feedback')

            self.PID_Laser_Zpoint_curve.setData(self.time_np, self.PID_Laser_Zpoint_np, pen=(0,0,255), name='Desire value')
            self.PID_Laser_FB_curve.setData(self.time_np, self.PID_Laser_FB_np, pen=(255,255,0), name='Feedback value')
            self.PID_Laser_Error_curve.setData(self.time_np, self.PID_Laser_Error_np, pen=(255,0,0), name='Error')
            self.PID_Laser_x_curve.setData(self.time_np, self.PID_Laser_x_np, pen=(0,255,0), name='Output to CP')
            
            self.PID_AMP_Zpoint_curve.setData(self.time_np, self.PID_AMP_Zpoint_np, pen=(0,0,255), name='Desire value')
            self.PID_AMP_FB_curve.setData(self.time_np, self.PID_AMP_FB_np, pen=(255,255,0), name='Feedback')
            self.PID_AMP_Error_curve.setData(self.time_np, self.PID_AMP_Error_np, pen=(255,0,0), name='Error')
            self.PID_AMP_Output_curve.setData(self.time_np, self.PID_AMP_Output_np, pen=(0,255,0), name='Output to CP')
            self.PID_OSC_Output_curve.setData(self.time_np, self.PID_OSC_Output_np, pen=(200,200,200), name='Output to OSC')


        elif (startChar != -1) and (rawData[startChar+104] == '\xF9'):
            self.counterRef_frame = ord(rawData[2])
            if self.counterRef_frame == 0:
                for i in range(1, 12):
                    self.loaderRef_frame[i] = "_"
            if self.counterRef_frame < 10:
                for i in xrange(3,103):
                    self.Ref_frame[(i-3)+(100*self.counterRef_frame)] = ord(rawData[i])
            else:
                for i in xrange(3,27):
                    self.Ref_frame[(i-3)+(100*self.counterRef_frame)] = ord(rawData[i])

            self.loaderRef_frame[self.counterRef_frame+1] = "*"
            self.receivedFrameLabel.setText(''.join(self.loaderRef_frame))



        else:
            self.receivedDataLabel.setText('Corrupted data frame in processing routine')

            

    def initUI(self):

        #qbtn = QtGui.QPushButton('Quit', self)
        #qbtn.clicked.connect(QtCore.QCoreApplication.instance().quit)
        #qbtn.resize(qbtn.sizeHint())
        #qbtn.move(50, 50)
        
        self.loaderRef_frame = []
        for x in range(13):
            self.loaderRef_frame.append('_')
        self.loaderRef_frame[0] = "|"
        self.loaderRef_frame[12] = "|"
 
        self.counterRef_frame = 0
        self.Ref_frame = []
        for x in range(1024):
            self.Ref_frame.append(0)

        self.receivedDataLabel = QtGui.QLabel('Received Data')
        self.receivedFrameLabel = QtGui.QLabel('|___________|')
        self.logButton = QtGui.QPushButton('Log Data', self)
        self.frameButton = QtGui.QPushButton('Read Ref.Frame', self)
        self.showFrameButton = QtGui.QPushButton('Show Ref.Frame', self)

        self.uppesthbox = QtGui.QHBoxLayout()
        self.uppesthbox.addWidget(self.frameButton)
        self.uppesthbox.addWidget(self.receivedFrameLabel)
        self.uppesthbox.addWidget(self.showFrameButton)
        self.uppesthbox.addStretch(1)
        self.uppesthbox.addWidget(self.receivedDataLabel)
        self.uppesthbox.addStretch(1)
        self.uppesthbox.addWidget(self.logButton)

#add labels
        self.Version_hbox = QtGui.QHBoxLayout()
        self.Version_label = QtGui.QLabel('-')
        self.Version_hbox.addWidget(self.Version_label)
        self.Version_Gbox = QtGui.QGroupBox("Firmware version")
        self.Version_Gbox.setLayout(self.Version_hbox)

        self.UART_TX_Mode_hbox = QtGui.QHBoxLayout()
        self.UART_TX_Mode_label = QtGui.QLabel('-')
        self.UART_TX_Mode_hbox.addWidget(self.UART_TX_Mode_label)
        self.UART_TX_Mode_Gbox = QtGui.QGroupBox("UART TX Mode")
        self.UART_TX_Mode_Gbox.setLayout(self.UART_TX_Mode_hbox)

        self.BootState_hbox = QtGui.QHBoxLayout()
        self.BootState_label = QtGui.QLabel('-')
        self.BootState_hbox.addWidget(self.BootState_label)
        self.BootState_Gbox = QtGui.QGroupBox("Boot State")
        self.BootState_Gbox.setLayout(self.BootState_hbox)

        self.Ticks_hbox = QtGui.QHBoxLayout()
        self.Ticks_label = QtGui.QLabel('0')
        self.Ticks_hbox.addWidget(self.Ticks_label)
        self.Ticks_Gbox = QtGui.QGroupBox("Ticks")
        self.Ticks_Gbox.setLayout(self.Ticks_hbox)
        
        self.Change_status_hbox = QtGui.QHBoxLayout()
        self.Change_status_label = QtGui.QLabel('-')
        self.Change_status_hbox.addWidget(self.Change_status_label)
        self.Change_status_Gbox = QtGui.QGroupBox("Change status")
        self.Change_status_Gbox.setLayout(self.Change_status_hbox)
        
        self.State_counter_hbox = QtGui.QHBoxLayout()
        self.State_counter_label = QtGui.QLabel('0')
        self.State_counter_hbox.addWidget(self.State_counter_label)
        self.State_counter_Gbox = QtGui.QGroupBox("State counter value")
        self.State_counter_Gbox.setLayout(self.State_counter_hbox)

        self.LC_Pulse_hbox = QtGui.QHBoxLayout()
        self.LC_Pulse_label = QtGui.QLabel('0')
        self.LC_Pulse_hbox.addWidget(self.LC_Pulse_label)
        self.LC_Pulse_Gbox = QtGui.QGroupBox("LC Pulse time performance")
        self.LC_Pulse_Gbox.setLayout(self.LC_Pulse_hbox)

        self.Ref_transferred_hbox = QtGui.QHBoxLayout()
        self.Ref_transferred_label = QtGui.QLabel('0')
        self.Ref_transferred_hbox.addWidget(self.Ref_transferred_label)
        self.Ref_transferred_Gbox = QtGui.QGroupBox("Ref. frame bytes transferred")
        self.Ref_transferred_Gbox.setLayout(self.Ref_transferred_hbox)

        self.Flash_errors_hbox = QtGui.QHBoxLayout()
        self.Flash_errors_label = QtGui.QLabel('0')
        self.Flash_errors_hbox.addWidget(self.Flash_errors_label)
        self.Flash_errors_Gbox = QtGui.QGroupBox("Flash errors")
        self.Flash_errors_Gbox.setLayout(self.Flash_errors_hbox)

        self.Reg_errors_hbox = QtGui.QHBoxLayout()
        self.Reg_errors_label = QtGui.QLabel('0')
        self.Reg_errors_hbox.addWidget(self.Reg_errors_label)
        self.Reg_errors_Gbox = QtGui.QGroupBox("Register errors")
        self.Reg_errors_Gbox.setLayout(self.Reg_errors_hbox)

        self.Frame_rcvd_hbox = QtGui.QHBoxLayout()
        self.Frame_rcvd_label = QtGui.QLabel('0')
        self.Frame_rcvd_hbox.addWidget(self.Frame_rcvd_label)
        self.Frame_rcvd_Gbox = QtGui.QGroupBox("Ref. frame bytes received")
        self.Frame_rcvd_Gbox.setLayout(self.Frame_rcvd_hbox)

        self.datavbox = QtGui.QVBoxLayout()
        self.datavbox.addWidget(self.Version_Gbox)
        self.datavbox.addWidget(self.UART_TX_Mode_Gbox)
        self.datavbox.addWidget(self.BootState_Gbox)
        self.datavbox.addWidget(self.Ticks_Gbox)
        self.datavbox.addWidget(self.Change_status_Gbox)
        self.datavbox.addWidget(self.State_counter_Gbox)
        self.datavbox.addWidget(self.LC_Pulse_Gbox)
        self.datavbox.addWidget(self.Ref_transferred_Gbox)
        self.datavbox.addWidget(self.State_counter_Gbox)
        self.datavbox.addWidget(self.Ref_transferred_Gbox)
        self.datavbox.addWidget(self.Frame_rcvd_Gbox)
        self.datavbox.addWidget(self.Flash_errors_Gbox)
        self.datavbox.addWidget(self.Reg_errors_Gbox)
        self.datavbox.addStretch(1)

        self.stateView = StateView(self)
        self.statevbox = QtGui.QVBoxLayout()
        self.stateView.setFixedWidth(402)
        self.stateView.setFixedHeight(736)
        self.statevbox.addWidget(self.stateView)

        self.unitView = UnitView(self)
        self.unitvbox = QtGui.QVBoxLayout()
        self.unitView.setFixedWidth(512)
        self.unitView.setFixedHeight(736)
        self.unitvbox.addWidget(self.unitView)

        #x = np.arange(1000)
        #y = np.random.normal(size=(3, 1000))

        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setFixedWidth(500)
        self.glw.setFixedHeight(734)
        self.time_np = []
        

        self.glw.nextRow()
        self.plotCP_Tmp = self.glw.addPlot(title="ColdPlate regulation(Temp)")
        self.plotCP_Tmp.enableAutoRange()
        self.PID_CP_Zpoint_np = []
        self.PID_CP_Zpoint_curve = self.plotCP_Tmp.plot(self.time_np, self.PID_CP_Zpoint_np, pen=(0,0,255), name='Desire value')
        self.PID_CP_FB_np = []
        self.PID_CP_FB_curve = self.plotCP_Tmp.plot(self.time_np, self.PID_CP_FB_np, pen=(255,255,0), name='Feedback')

        self.glw.nextRow()
        self.plotCP = self.glw.addPlot(title="ColdPlate regulation(div by 100)")
        self.plotCP.enableAutoRange()
        #self.plotCP.addLegend()
        self.PID_CP_x_np = []
        self.PID_CP_Output_curve = self.plotCP.plot(self.time_np, self.PID_CP_x_np, pen=(0,255,0), name='Output to CP')
        self.PID_CP_Error_np = []
        self.PID_CP_Error_curve = self.plotCP.plot(self.time_np, self.PID_CP_Error_np, pen=(255,0,0), name='Error')
        self.PID_CP_Integral_np = []
        self.PID_CP_Integral_curve = self.plotCP.plot(self.time_np, self.PID_CP_Integral_np, pen=(255,255,255), name='Integral')

       
        self.glw.nextRow()
        self.plotLaser_Tmp = self.glw.addPlot(title="Laser TEC regulation(Temp)")
        self.plotLaser_Tmp.enableAutoRange()
        self.PID_Laser_Zpoint_np = []
        self.PID_Laser_Zpoint_curve = self.plotLaser_Tmp.plot(self.time_np, self.PID_Laser_Zpoint_np, pen=(0,0,255), name='Desire value')
        self.PID_Laser_FB_np = []
        self.PID_Laser_FB_curve = self.plotLaser_Tmp.plot(self.time_np, self.PID_Laser_FB_np, pen=(255,255,0), name='Feedback')

        self.glw.nextRow()
        self.plotLaser = self.glw.addPlot(title="Laser TEC regulation(div by 100)")
        self.plotLaser.enableAutoRange()
        #self.plotLaser.addLegend()
        self.PID_Laser_x_np = []
        self.PID_Laser_x_curve = self.plotLaser.plot(self.time_np, self.PID_Laser_x_np, pen=(0,255,0), name='Output to Laser')
        self.PID_Laser_Error_np = []
        self.PID_Laser_Error_curve = self.plotLaser.plot(self.time_np, self.PID_Laser_Error_np, pen=(255,0,0), name='Error')


        self.glw.nextRow()
        self.plotAMP_Tmp = self.glw.addPlot(title="Laser AMP/OSC regulation(Spectrum level)")
        self.plotAMP_Tmp.enableAutoRange()
        self.PID_AMP_Zpoint_np = []
        self.PID_AMP_Zpoint_curve = self.plotAMP_Tmp.plot(self.time_np, self.PID_AMP_Zpoint_np, pen=(0,0,255), name='Desire value')
        self.PID_AMP_FB_np = []
        self.PID_AMP_FB_curve = self.plotAMP_Tmp.plot(self.time_np, self.PID_AMP_FB_np, pen=(255,255,0), name='Feedback')

        self.glw.nextRow()
        self.plotAMP = self.glw.addPlot(title="Laser AMP/OSC regulation(div by 100)")
        self.plotAMP.enableAutoRange()
        #self.plotAMP.addLegend()
        self.PID_AMP_Output_np = []
        self.PID_AMP_Output_curve = self.plotAMP.plot(self.time_np, self.PID_AMP_Output_np, pen=(0,255,0), name='Output to AMP')
        self.PID_AMP_Error_np = []
        self.PID_AMP_Error_curve = self.plotAMP.plot(self.time_np, self.PID_AMP_Error_np, pen=(255,0,0), name='Error')
        self.PID_OSC_Output_np = []
        self.PID_OSC_Output_curve = self.plotAMP.plot(self.time_np, self.PID_OSC_Output_np, pen=(200, 200, 200), name='Output to OSC')

        #legend = pg.LegendItem()
        #legend.addItem(self.PID_CP_Zpoint_curve, name=self.PID_CP_Zpoint_curve.opts['name'])
        #legend.setParentItem(self.plotCP)
        #legend.anchor((0,0),(0,0))

        self.graphsvbox = QtGui.QVBoxLayout()
        self.graphsvbox.addWidget(self.glw)

        self.upperhbox = QtGui.QHBoxLayout()
        self.upperhbox.addLayout(self.statevbox)
        self.upperhbox.addStretch(1)
        self.upperhbox.addLayout(self.unitvbox)
        self.upperhbox.addStretch(1)
        self.upperhbox.addLayout(self.graphsvbox)
        self.upperhbox.addStretch(1)
        self.upperhbox.addLayout(self.datavbox)
        
        self.connectStatLabel = QtGui.QLabel('Disconnected')
        self.comPortComboBox = QtGui.QComboBox()
        self.comPortComboBox.addItem("Search")
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("highlighted(int)"), self.updtPortsList)
        #self.comPortComboBox.activated.connect(self.updtPortsList)
        
        self.baudRates = ['9600', '19200', '38400', '57600', '115200']
        self.baudRateComboBox = QtGui.QComboBox()
        self.baudRateComboBox.addItems(self.baudRates)
        self.baudRateComboBox.setCurrentIndex(4)

        self.connectButtonState = False
        self.connectButton = QtGui.QPushButton('Connect', self)
        #self.connect(self.connectButton, QtCore.SIGNAL("highlighted(int)"), self.updtPortsList)

        self.lowerhbox = QtGui.QHBoxLayout()
        self.lowerhbox.addStretch(1)
        self.lowerhbox.addWidget(self.connectStatLabel)
        self.lowerhbox.addStretch(1)
        self.lowerhbox.addWidget(self.comPortComboBox)
        self.lowerhbox.addWidget(self.baudRateComboBox)
        self.lowerhbox.addWidget(self.connectButton)


        self.onButton = QtGui.QPushButton('ON STATE', self)
        self.offButton = QtGui.QPushButton('OFF STATE', self)
        self.idleButton = QtGui.QPushButton('IDLE STATE', self)
        self.flashButton = QtGui.QPushButton('FLASH STATE', self)
       
        self.lowhbox = QtGui.QHBoxLayout()
        self.lowhbox.addWidget(self.onButton)
        self.lowhbox.addWidget(self.offButton)
        self.lowhbox.addWidget(self.idleButton)
        self.lowhbox.addWidget(self.flashButton)
        self.lowhbox.addStretch(1)


        self.vbox = QtGui.QVBoxLayout()              # MAIN Box
        self.vbox.addLayout(self.uppesthbox)
        self.vbox.addLayout(self.upperhbox)
        self.vbox.addLayout(self.lowhbox)
        self.vbox.addLayout(self.lowerhbox)
        self.vbox.addStretch(1)

        self.setLayout(self.vbox)

        self.connect(self.connectButton, QtCore.SIGNAL("clicked()"), self.OnPressConnect)
        self.connect(self.logButton, QtCore.SIGNAL("clicked()"), self.OnPressLog)
        self.connect(self.comPortComboBox, QtCore.SIGNAL("activated(int)"), self.updtPortsList)
        self.connect(self.showFrameButton, QtCore.SIGNAL("clicked()"), self.showButtonClicked)
        self.connect(self.frameButton, QtCore.SIGNAL("clicked()"), self.frameButtonClicked)
        self.connect(self.onButton, QtCore.SIGNAL("clicked()"), self.onButtonClicked)
        self.connect(self.offButton, QtCore.SIGNAL("clicked()"), self.offButtonClicked)
        self.connect(self.idleButton, QtCore.SIGNAL("clicked()"), self.idleButtonClicked)
        self.connect(self.flashButton, QtCore.SIGNAL("clicked()"), self.flashButtonClicked)
        #self.connect(self, QtCore.SIGNAL("unitSignal(int)"), self.unitChanged)
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.comPortComboBox, QtCore.SLOT("blockSignals(False)"))
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.comPortComboBox.blockSignals(False))

        #self.resize(250, 150)
        #self.center_window()
        self.setWindowTitle('MCU Telemetry')
        self.setWindowIcon(QtGui.QIcon('web.png'))

        self.show()
            
        self.UART_TX_Mode = 0
        self.BootState = 3
        self.Ticks = 0
        self.ADC_I2C1_Enable = 0   # in binary
        self.ADC_I2C2_Enable = 0   # in binary
        self.PORTD = 0             # in binary

        self.PID_CP_Enabled = 0
        self.PID_Laser_Enabled = 0
        self.PID_AMP_Enabled = 0
    
        self.WindEyeState = 0
        self.desState = 0
        self.LC_Pulse_Counter = 0
        self.Change_status = 3
            
        self.I2C2_Error =0
        self.hHeater = 0

        self.Ref_transferred = 0
        self.Flash_errors = 0
        self.Reg_errors = 0
        self.Frame_rcvd = 0

        self.PID_CP_Zpoint = 0
        self.I2C_ADC_ColdPlate_NTC = 0
        self.PID_Laser_Zpoint = 0
        self.I2C_ADC_Laser_NTC = 0

        self.oldPID_CP_Zpoint = 0
        self.oldI2C_ADC_ColdPlate_NTC = 0
        self.oldPID_Laser_Zpoint = 0
        self.oldI2C_ADC_Laser_NTC = 0

        self.Version = 0



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
