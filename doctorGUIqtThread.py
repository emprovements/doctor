
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
                    #logger.debug('W got data: \n' + repr(newData))
                    logger.debug('W got data')

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

class unitImage(QtGui.QGraphicsPixmapItem):

    def __init__(self):
        super(unitImage, self).__init__()
        self.setPixmap(QtGui.QPixmap("unit.png"))

class unitView(QtGui.QGraphicsView):

    def __init__(self, parent):
        super(unitView, self).__init__()
        self.setBackgroundBrush(QtGui.QColor(0, 0, 0))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.initScene()

    def initScene(self):
        self.scene = QtGui.QGraphicsScene(self)
        self.setSceneRect(0, 0, 510, 500)

        self.image = unitImage()
        self.scene.addItem(self.image)

        self.lBeam = self.scene.addRect(50,50,10,30)
        self.lBeam.setBrush(QtGui.QColor(200,10,10))
        self.lBeam.rotate(45)

        self.setScene(self.scene)

class stateImage(QtGui.QGraphicsPixmapItem):

    def __init__(self):
        super(stateImage, self).__init__()
        self.setPixmap(QtGui.QPixmap("states.png"))

class stateView(QtGui.QGraphicsView):

    def __init__(self, parent):
        super(stateView, self).__init__()
        self.setBackgroundBrush(QtGui.QColor(0, 0, 0))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.initScene()

    def initScene(self):
        self.scene = QtGui.QGraphicsScene(self)
        self.setSceneRect(0, 0, 240, 500)

        self.image = stateImage()
        self.scene.addItem(self.image)

        self.boot = self.scene.addEllipse(175,140,10,10)
        self.boot.setBrush(QtGui.QColor(200,10,10))
        
        self.off = self.scene.addEllipse(175,200,10,10)
        self.off.setBrush(QtGui.QColor(200,10,10))
        
        self.idle = self.scene.addEllipse(170,260,10,10)
        self.idle.setBrush(QtGui.QColor(200,10,10))

        self.flash = self.scene.addEllipse(170,315,10,10)
        self.flash.setBrush(QtGui.QColor(200,10,10))
        
        self.normal = self.scene.addEllipse(50,180,20,20)
        self.normal.setBrush(QtGui.QColor(200,10,10))

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

    def clear(self):
        self.boot.setBrush(QtGui.QColor(200,10,10))
        self.off.setBrush(QtGui.QColor(200,10,10))
        self.idle.setBrush(QtGui.QColor(200,10,10))
        self.flash.setBrush(QtGui.QColor(200,10,10))
        self.normal.setBrush(QtGui.QColor(200,10,10))



class Unit(QtGui.QWidget):

    def __init__(self, parent):
        super(Unit, self).__init__()
        self.parent = parent
        self.painter = QtGui.QPainter()
        self.loadImage()

    def paintEvent(self, event):
        self.painter.begin(self)
        self.drawCustomWidget(self.painter)
        self.painter.end()

    def drawCustomWidget(self, parent):
        print "Unit"

    def loadImage(self):
        self.img = QtGui.QImage("unit.png")
        if self.img.isNull():
            logger.info("Error loading image")
        else:
            print "loaded"
            self.painter.begin(self)
            self.iw = self.img.width()
            self.ih = self.img.height()
            self.rect = QtCore.QRect(0, 0, self.iw, self.ih)
            self.painter.drawImage(self.rect, self.img)
            self.painter.end()



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

    #def unitChanged(self):
    #    self.unit.repaint()

    def processQueueData(self, data):
        logger.debug("Got data from serial for processing")
        rawData = data
        startChar = rawData.find('\x80\x80')
        if (startChar != -1) and (rawData[startChar+92] == '\x9F'):


            #logger.debug('Data: \n' + repr(rawData))
            # for x in xrange(92):
            #     print str(x)+" "+str(ord(rawData[x]))

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
            
            State_Counter_value = (256*ord(rawData[78]) + ord(rawData[79]))
            Ref_transferred = (256*ord(rawData[80]) + ord(rawData[81]))
            Flash_errors = (256*ord(rawData[82]) + ord(rawData[83]))
            Reg_errors = (256*ord(rawData[84]) + ord(rawData[85]))

            if UART_TX_Mode == 1:
                UART_TX_Mode = 'Diagnostic'
            elif UART_TX_Mode == 2:
                UART_TX_Mode = 'Registers'
            else:
                UART_TX_Mode = 'None'
            self.UART_TX_Mode_label.setText(UART_TX_Mode)

            if BootState == 0:
                BootState = 'OFF'
            elif BootState == 1:
                BootState = 'ON'
                self.stateView.change('boot')
            elif BootState == 2:
                BootState = 'FAST'
                self.stateView.change('boot')
            else:
                BootState = 'None'
            self.BootState_label.setText(BootState)

            self.Ticks_label.setText(str(Ticks))

            if WindEyeState == 48:
                WindEyeState = 'OFF'
                self.stateView.change('off')
            elif WindEyeState == 49:
                WindEyeState = 'ON'
                self.stateView.change('on')
            elif WindEyeState == 53:
                WindEyeState = 'IDLE'
                self.stateView.change('idle')
            elif WindEyeState == 56:
                WindEyeState = 'FLASH'
                self.stateView.change('flash')
            else:
                WindEyeState = 'None'
            self.WindEyeState_label.setText(WindEyeState)

            if desState == 48:
                desState = 'OFF'
            elif desState == 49:
                desState= 'ON'
            elif desState == 53:
                desState = 'IDLE'
            elif desState == 56:
                desState = 'FLASH'
            else:
                desState = 'None'
            self.desState_label.setText(desState)

            if Change_status == 0:
                Change_status = 'CHANGED'
            elif Change_status == 1:
                Change_status = 'CHANGE'
            elif Change_status == 2:
                Change_status = 'CHANGING'
            else:
                Change_status = 'None'
            self.Change_status_label.setText(Change_status)

            self.State_counter_label.setText(str(State_Counter_value))
            self.Ref_transferred_label.setText(str(Ref_transferred))
            self.Flash_errors_label.setText(str(Flash_errors))
            self.Reg_errors_label.setText(str(Reg_errors))

#Graphs
            if len(self.time_np)>59:
                for x in xrange(1,60):
                    self.time_np[x-1] = self.time_np[x]

                    self.PID_CP_Zpoint_np[x-1] = self.PID_CP_Zpoint_np[x]
                    self.PID_CP_Error_np[x-1] = self.PID_CP_Error_np[x]
                    self.PID_CP_Output_np[x-1] = self.PID_CP_Output_np[x]
                    
                    self.PID_Laser_Zpoint_np[x-1] = self.PID_Laser_Zpoint_np[x]
                    self.PID_Laser_Error_np[x-1] = self.PID_Laser_Error_np[x]
                    self.PID_Laser_Output_np[x-1] = self.PID_Laser_Output_np[x]
                    
                    self.PID_AMP_Zpoint_np[x-1] = self.PID_AMP_Zpoint_np[x]
                    self.PID_AMP_Error_np[x-1] = self.PID_AMP_Error_np[x]
                    self.PID_AMP_Output_np[x-1] = self.PID_AMP_Output_np[x]
                    self.PID_OSC_Output_np[x-1] = self.PID_OSC_Output_np[x]

                self.time_np[59] = self.time_np[58]+1

                self.PID_CP_Zpoint_np[59] = PID_CP_Zpoint
                self.PID_CP_Error_np[59] = PID_CP_Error
                self.PID_CP_Output_np[59] = PID_CP_Output
                
                self.PID_Laser_Zpoint_np[59] = PID_Laser_Zpoint
                self.PID_Laser_Error_np[59] = PID_Laser_Error
                self.PID_Laser_Output_np[59] = PID_Laser_Output
                
                self.PID_AMP_Zpoint_np[59] = PID_AMP_Zpoint
                self.PID_AMP_Error_np[59] = PID_AMP_Error
                self.PID_AMP_Output_np[59] = PID_AMP_Output
                self.PID_OSC_Output_np[59] = PID_OSC_Output

            else:
                self.time_np.append(len(self.time_np)+1)

                self.PID_CP_Zpoint_np.append(PID_CP_Zpoint)
                self.PID_CP_Error_np.append(PID_CP_Error)
                self.PID_CP_Output_np.append(PID_CP_Output)
                
                self.PID_Laser_Zpoint_np.append(PID_Laser_Zpoint)
                self.PID_Laser_Error_np.append(PID_Laser_Error)
                self.PID_Laser_Output_np.append(PID_Laser_Output)

                self.PID_AMP_Zpoint_np.append(PID_AMP_Zpoint)
                self.PID_AMP_Error_np.append(PID_AMP_Error)
                self.PID_AMP_Output_np.append(PID_AMP_Output)
                self.PID_OSC_Output_np.append(PID_OSC_Output)
        
            self.PID_CP_Zpoint_curve.setData(self.time_np, self.PID_CP_Zpoint_np, pen=(0,0,255), name='Desire value')
            self.PID_CP_Error_curve.setData(self.time_np, self.PID_CP_Error_np, pen=(255,0,0), name='Error')
            self.PID_CP_Output_curve.setData(self.time_np, self.PID_CP_Output_np, pen=(0,255,0), name='Output to CP')

            self.PID_Laser_Zpoint_curve.setData(self.time_np, self.PID_Laser_Zpoint_np, pen=(0,0,255), name='Desire value')
            self.PID_Laser_Error_curve.setData(self.time_np, self.PID_Laser_Error_np, pen=(255,0,0), name='Error')
            self.PID_Laser_Output_curve.setData(self.time_np, self.PID_Laser_Output_np, pen=(0,255,0), name='Output to CP')
            
            self.PID_AMP_Zpoint_curve.setData(self.time_np, self.PID_AMP_Zpoint_np, pen=(0,0,255), name='Desire value')
            self.PID_AMP_Error_curve.setData(self.time_np, self.PID_AMP_Error_np, pen=(255,0,0), name='Error')
            self.PID_AMP_Output_curve.setData(self.time_np, self.PID_AMP_Output_np, pen=(0,255,0), name='Output to CP')
            self.PID_OSC_Output_curve.setData(self.time_np, self.PID_OSC_Output_np, pen=(200,200,200), name='Output to OSC')
            

            #self.unitChanged()
            #self.emit(QtCore.SIGNAL('unitSignal(int)'), LC_State)

            print("RAWDATA len "+str(len(rawData)))

    def initUI(self):

        #qbtn = QtGui.QPushButton('Quit', self)
        #qbtn.clicked.connect(QtCore.QCoreApplication.instance().quit)
        #qbtn.resize(qbtn.sizeHint())
        #qbtn.move(50, 50)

        self.receivedDataLabel = QtGui.QLabel('Received Data')
        self.logButton = QtGui.QPushButton('Log Data', self)

        self.uppesthbox = QtGui.QHBoxLayout()
        self.uppesthbox.addStretch(1)
        self.uppesthbox.addWidget(self.receivedDataLabel)
        self.uppesthbox.addStretch(1)
        self.uppesthbox.addWidget(self.logButton)

#add labels
        self.UART_TX_Mode_hbox = QtGui.QHBoxLayout()
        self.UART_TX_Mode_label = QtGui.QLabel('0')
        self.UART_TX_Mode_hbox.addWidget(self.UART_TX_Mode_label)
        self.UART_TX_Mode_Gbox = QtGui.QGroupBox("UART TX Mode")
        self.UART_TX_Mode_Gbox.setLayout(self.UART_TX_Mode_hbox)

        self.BootState_hbox = QtGui.QHBoxLayout()
        self.BootState_label = QtGui.QLabel('0')
        self.BootState_hbox.addWidget(self.BootState_label)
        self.BootState_Gbox = QtGui.QGroupBox("Boot State")
        self.BootState_Gbox.setLayout(self.BootState_hbox)

        self.Ticks_hbox = QtGui.QHBoxLayout()
        self.Ticks_label = QtGui.QLabel('0')
        self.Ticks_hbox.addWidget(self.Ticks_label)
        self.Ticks_Gbox = QtGui.QGroupBox("Ticks")
        self.Ticks_Gbox.setLayout(self.Ticks_hbox)
        
        self.WindEyeState_hbox = QtGui.QHBoxLayout()
        self.WindEyeState_label = QtGui.QLabel('None')
        self.WindEyeState_hbox.addWidget(self.WindEyeState_label)
        self.WindEyeState_Gbox = QtGui.QGroupBox("Wind Eye State")
        self.WindEyeState_Gbox.setLayout(self.WindEyeState_hbox)
        
        self.desState_hbox = QtGui.QHBoxLayout()
        self.desState_label = QtGui.QLabel('0')
        self.desState_hbox.addWidget(self.desState_label)
        self.desState_Gbox = QtGui.QGroupBox("desire State")
        self.desState_Gbox.setLayout(self.desState_hbox)
        
        self.Change_status_hbox = QtGui.QHBoxLayout()
        self.Change_status_label = QtGui.QLabel('0')
        self.Change_status_hbox.addWidget(self.Change_status_label)
        self.Change_status_Gbox = QtGui.QGroupBox("Change status")
        self.Change_status_Gbox.setLayout(self.Change_status_hbox)
        
        self.State_counter_hbox = QtGui.QHBoxLayout()
        self.State_counter_label = QtGui.QLabel('0')
        self.State_counter_hbox.addWidget(self.State_counter_label)
        self.State_counter_Gbox = QtGui.QGroupBox("State counter value")
        self.State_counter_Gbox.setLayout(self.State_counter_hbox)
        
        self.Ref_transferred_hbox = QtGui.QHBoxLayout()
        self.Ref_transferred_label = QtGui.QLabel('0')
        self.Ref_transferred_hbox.addWidget(self.Ref_transferred_label)
        self.Ref_transferred_Gbox = QtGui.QGroupBox("Reference fr. transferred")
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

        self.datavbox = QtGui.QVBoxLayout()
        self.datavbox.addWidget(self.UART_TX_Mode_Gbox)
        self.datavbox.addWidget(self.BootState_Gbox)
        self.datavbox.addWidget(self.Ticks_Gbox)
        self.datavbox.addWidget(self.WindEyeState_Gbox)
        self.datavbox.addWidget(self.desState_Gbox)
        self.datavbox.addWidget(self.Change_status_Gbox)
        self.datavbox.addWidget(self.State_counter_Gbox)
        self.datavbox.addWidget(self.Ref_transferred_Gbox)
        self.datavbox.addWidget(self.State_counter_Gbox)
        self.datavbox.addWidget(self.Ref_transferred_Gbox)
        self.datavbox.addWidget(self.Flash_errors_Gbox)
        self.datavbox.addWidget(self.Reg_errors_Gbox)
        self.datavbox.addStretch(1)

        self.stateView = stateView(self)
        self.statevbox = QtGui.QVBoxLayout()
        self.stateView.setFixedWidth(242)
        #self.stateView.setFixedHeight(502)
        self.statevbox.addWidget(self.stateView)

        self.unitView = unitView(self)
        self.unitvbox = QtGui.QVBoxLayout()
        self.unitView.setFixedWidth(512)
        #self.unitView.setFixedHeight(502)
        self.unitvbox.addWidget(self.unitView)

        #x = np.arange(1000)
        #y = np.random.normal(size=(3, 1000))

        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setFixedWidth(512)
        self.time_np = []
        
        
        self.plotCP = self.glw.addPlot(title="ColdPlate regulation")
        self.plotCP.enableAutoRange()
        #self.plotCP.addLegend()
        self.PID_CP_Zpoint_np = []
        self.PID_CP_Zpoint_curve = self.plotCP.plot(self.time_np, self.PID_CP_Zpoint_np, pen=(0,0,255), name='Desire value')
        self.PID_CP_Output_np = []
        self.PID_CP_Output_curve = self.plotCP.plot(self.time_np, self.PID_CP_Output_np, pen=(0,255,0), name='Output to CP')
        self.PID_CP_Error_np = []
        self.PID_CP_Error_curve = self.plotCP.plot(self.time_np, self.PID_CP_Error_np, pen=(255,0,0), name='Error')

        self.glw.nextRow()
        self.plotLaser = self.glw.addPlot(title="Laser ADC regulation")
        self.plotLaser.enableAutoRange()
        #self.plotLaser.addLegend()
        self.PID_Laser_Zpoint_np = []
        self.PID_Laser_Zpoint_curve = self.plotLaser.plot(self.time_np, self.PID_Laser_Zpoint_np, pen=(0,0,255), name='Desire value')
        self.PID_Laser_Output_np = []
        self.PID_Laser_Output_curve = self.plotLaser.plot(self.time_np, self.PID_Laser_Output_np, pen=(0,255,0), name='Output to Laser')
        self.PID_Laser_Error_np = []
        self.PID_Laser_Error_curve = self.plotLaser.plot(self.time_np, self.PID_Laser_Error_np, pen=(255,0,0), name='Error')
       
        self.glw.nextRow()
        self.plotAMP = self.glw.addPlot(title="Laser AMP regulation")
        self.plotAMP.enableAutoRange()
        #self.plotAMP.addLegend()
        self.PID_AMP_Zpoint_np = []
        self.PID_AMP_Zpoint_curve = self.plotAMP.plot(self.time_np, self.PID_AMP_Zpoint_np, pen=(0,0,255), name='Desire value')
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

        self.baudRateComboBox = QtGui.QComboBox()

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


        self.vbox = QtGui.QVBoxLayout()              # MAIN Box
        self.vbox.addLayout(self.uppesthbox)
        self.vbox.addLayout(self.upperhbox)
        self.vbox.addLayout(self.lowerhbox)
        self.vbox.addStretch(1)

        self.setLayout(self.vbox)

        self.connect(self.connectButton, QtCore.SIGNAL("clicked()"), self.OnPressConnect)
        self.connect(self.logButton, QtCore.SIGNAL("clicked()"), self.OnPressLog)
        self.connect(self.comPortComboBox, QtCore.SIGNAL("activated(int)"), self.updtPortsList)
        #self.connect(self, QtCore.SIGNAL("unitSignal(int)"), self.unitChanged)
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.comPortComboBox, QtCore.SLOT("blockSignals(False)"))
        #self.connect(self.comPortComboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.comPortComboBox.blockSignals(False))

        #self.resize(250, 150)
        #self.center_window()
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
