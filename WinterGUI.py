import Tkinter
import ttk
import tkMessageBox
import serial
import time
import threading
import os
import random
import Queue
import datetime
import math
import sys

import random

# ----------Import and initialize for graph ------------------
import matplotlib
matplotlib.use('TkAgg')		#Select TkAgg before importing pyplot

from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg

import numpy
from numpy import linspace, arange, array

# ----------Serial ---------------------------
from serial.tools import list_ports

# ----------Logging -------------------------
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# create a file handler
loghandler = logging.FileHandler('WinterGUIlog.log')
loghandler.setLevel(logging.INFO)

# create a logging format
logformatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
loghandler.setFormatter(logformatter)

# add the handlers to the logger
logger.addHandler(loghandler)

#logger disable to propagate message to terminal
logger.propagate = False


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
			port = self.parent.boxPort.get()
			baud = (self.parent.boxBaud.get()).split()
			self.ser = serial.Serial(port, baudrate=int(baud[0]), timeout=0, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
		except serial.SerialException:
			logger.error('Cannot open port', exc_info=True)	# by exc_info=True traceback is dumped to the logger
			self._stop = True
		else:	
			app.labelConStatus.set(u'Connected to ' + port)
			logger.info('Connected to port '+ port)

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

					if newData[0] == '\xea':
						newFrame = True
						oldData = ''
						oldData = newData

						logger.debug('W New Frame: ' + repr(newData))
					
					if (len(oldData)>36):
						if self.queueData.empty():
							logger.debug('W Data going to Queue')
							self.queueData.put(oldData)
							oldData = ''
							newFrame = False

			#		if self.commReady:			# flag for sending data to RS485 bus but disabled for this release
			#			try:
			#				self.ser.write(dataComm)	

			#			except serial.SerialException:
			#				logger.error('Cannot write to serial port')

			#			else:
			#				self.commReady = False

				n = 0;
			time.sleep(0.1)
					
				
class FileOperations():
	def openFile(self, name):
		self.file = open(name, 'w')

	def writeToFile(self, string):
		self.file.write(string+'\n')

	def closeFile(self):
		self.file.close()


class MyGUI(Tkinter.Tk):
	def __init__(self, parent):
		Tkinter.Tk.__init__(self, parent)
		self.parent = parent
		self.queueData = Queue.Queue(maxsize=40) # create queue
		self.queueComm = Queue.Queue(maxsize=20) # create queue
		self.queueEff = Queue.Queue(maxsize=3)	 # create queue

		self.loggingData = False		# flag for logging button and logging data
		self.drawing = True		# flag for pause and play refreshing graphs

		self.angle = 0
		self.angleF = 0

		self.initialize()


	def initialize(self):
		"""Create the GUI"""
		self.grid()
		
		#---DATA FRAME------------------------------------------------------------------------------->
		dataFrame = Tkinter.LabelFrame(self, text='Real-time received data')
		dataFrame.grid(row=0, column=0, columnspan=2, sticky='NEW', padx=5, pady=5, ipadx=5, ipady=5)
		dataFrame.columnconfigure(1, weight=1)

		self.labelData = Tkinter.StringVar()
		labelData = Tkinter.Label(dataFrame, textvariable=self.labelData)
		labelData.grid(row=1, column=1, columnspan=1, sticky='EW', padx=2, pady=2, ipadx=2, ipady=2)
		self.labelData.set(u'-')


		self.buttonLog = Tkinter.Button(dataFrame, text=u'Log Data', state='disabled', command=self.OnPressLog)
		self.buttonLog.grid(row=1, column=2, sticky='W', padx=5, pady=5)

		#---GRAPH FRAME------------------------------------------------------------------------------->
		graphFrame = Tkinter.LabelFrame(self, text='DISPLAY')
		graphFrame.grid(row=1, column=0, columnspan=1, sticky='NWES', padx=2, pady=2, ipadx=2, ipady=2)
		graphFrame.columnconfigure(1, weight=1)

		self.graphCanvas = Tkinter.Canvas(graphFrame, width=500, heigh=500)
		self.graphCanvas.grid(row=1, column=1, sticky='NWS')

		self.nacelle = self.graphCanvas.create_polygon(225, 445, 235, 445, 235, 420, 265, 420, 265, 445, 275, 445, 270, 500, 230, 500, fill='white', outline='grey')
#		self.nacelleBlock = self.graphCanvas.create_rectangle(230, 445, 270, 500)

#		self.nacelleShaft0 = self.graphCanvas.create_line(235, 420, 235, 445)
#		self.nacelleShaft1 = self.graphCanvas.create_line(265, 420, 265, 445)
		self.nacelleTip = self.graphCanvas.create_arc(235, 440, 265, 410, start=-1, extent=180, fill='white', outline='grey')

		self.bladeL = self.graphCanvas.create_polygon(235, 420, 32, 430, 235, 440, fill='white', outline='grey')
#		self.bladeL1 = self.graphCanvas.create_line(235, 420, 32, 430)
#		self.bladeL2 = self.graphCanvas.create_line(235, 440, 32, 430)

		self.bladeR = self.graphCanvas.create_polygon(265, 420, 468, 430, 265, 440, fill='white', outline='grey')
#		self.bladeR1 = self.graphCanvas.create_line(265, 420, 468, 430)
#		self.bladeR2 = self.graphCanvas.create_line(265, 440, 468, 430)


		#self.lidarCanvas = self.graphCanvas.create_oval(240, 450, 260, 470, fill='red')
		self.lidarCanvas = self.graphCanvas.create_polygon(240, 455, 250, 452, 260, 455, 258, 475, 242, 475, fill='red', outline='black')

		self.leftBeam = self.graphCanvas.create_line(10, 10, 240, 450, fill='')

		self.rightBeam = self.graphCanvas.create_line(260, 450, 490, 10, fill='')

		self.axialComponent = self.graphCanvas.create_line(250, 10, 250, 390, dash=20, fill='grey')

		self.windLine1 = self.graphCanvas.create_line(250, 50, 250, 300, arrow='last', width=3, fill='blue')
		self.windLine2 = self.graphCanvas.create_line(250, 50, 250, 300, arrow='last', width=3, fill='blue')
		self.windLine3 = self.graphCanvas.create_line(250, 50, 250, 300, arrow='last', width=3, fill='blue')
		self.windLine4 = self.graphCanvas.create_line(250, 50, 250, 300, arrow='last', width=3, fill='blue')
		self.windLine5 = self.graphCanvas.create_line(250, 50, 250, 300, arrow='last', width=3, fill='blue')
		
		# ----------------- PLOTS ---------------------
		# ----- Initialize graphs ----------------------
		self.gs = gridspec.GridSpec(2,3)
		self.gs.update(hspace=0.6, wspace=0.6)
		self.plotFigure = Figure(figsize=(8,5), frameon=False)

		# ----- Speed PLOT ------

		self.speedValues = []
		self.badValues = []
		self.goodValues = []
		self.timeValues = []

		self.plotSpeed = self.plotFigure.add_subplot(self.gs[0,:])

		self.plotSpeed.grid(True)
		self.plotSpeed.set_title('Wind direction last 30 seconds')
		self.plotSpeed.set_xlabel('Elapsed time-frame [s]')
		self.plotSpeed.set_ylabel('Wind angle [degrees]')
		
		self.lineSpeed = self.plotSpeed.plot(self.timeValues, self.speedValues, ':b')
		self.lineGoodSpeedValues = self.plotSpeed.plot([], [], 'ob')
		self.lineBadSpeedValues = self.plotSpeed.plot([], [], 'xr')
		#self.lineAverageSpeedValues = self.plotSpeed.plot([], [], '--g')

		# ----- Pie PLOT ------

		self.efficiency = 0
		self.totalSamples = 0
		self.goodSamples = 0
		self.badSamples = 0
		self.fracs = [50, 50]

		self.plotEff = self.plotFigure.add_subplot(self.gs[1,0])
		self.plotEff.set_title('Efficiency last 60 seconds', fontsize=12)
		
		self.pie_wedges = self.plotEff.pie(self.fracs, radius=0.8, colors=('g','r'))
		for wedges in self.pie_wedges[0]:
			wedges.set_edgecolor('white')
		self.plotEff.set_xlabel('50.0 % (0 / 0)')
		
		# ----- BAR PLOT ----------

		self.effValues = []
		self.effTimeValues = []

		self.plotBar = self.plotFigure.add_subplot(self.gs[1,1:])

		self.plotBar.grid(True)
		self.plotBar.set_title('Efficiency last 60 minutes', fontsize=12)
		self.plotBar.set_xlabel('Elapsed time-frame [min]')
		self.plotBar.set_ylabel('Efficiency [%]')

		self.bars = self.plotBar.bar(self.effTimeValues, self.effValues, radius=0.8)

		# ----- Frame for GRAPHS -------------------- 
		self.speedFrame = Tkinter.Frame(graphFrame)
		self.speedFrame.grid(row=1, column=2, sticky='NEWS', columnspan=2)

		self.buttonGraphOnOff = Tkinter.Button(self.speedFrame, text=u'Turn OFF graphs', command=self.OnPressGraphOnOff)
		self.buttonGraphOnOff.grid(row=2, column=1, sticky='SWE', padx=2, pady=2)

		self.buttonGraphReset = Tkinter.Button(self.speedFrame, text=u'Reset graphs', command=self.OnPressGraphReset)
		self.buttonGraphReset.grid(row=2, column=2, sticky='SWE', padx=2, pady=2)
		
		self.speedCanvas = FigureCanvasTkAgg(self.plotFigure, master=self.speedFrame)
		self.speedCanvas.show()
		self.speedCanvas._tkcanvas.grid(row=1, column=1, columnspan=3, sticky='NES', padx=2, pady=2)

		self.toolbarSpeed = NavigationToolbar2TkAgg(self.speedCanvas, self.speedFrame)
		self.toolbarSpeed.update()
		self.toolbarSpeed.grid(row=3, column=1, columnspan=2, sticky='WS')


		#---PORTS FRAME------------------------------------------------------------------------------->
		portsFrame = Tkinter.LabelFrame(self, text='Ports')
		portsFrame.grid(row=2, column=0, columnspan=2, sticky='WE', padx=5, pady=5, ipadx=5, ipady=5)
		portsFrame.columnconfigure(1, weight=1)

		self.buttonConnect = Tkinter.Button(portsFrame, text=u'Connect', state='disabled', command=self.OnPressConnect)
		self.buttonConnect.grid(row=1, column=6, sticky='E', padx=2, pady=5)
	#self.buttonConnect.grid_propagate(False)

		
		self.buttonDisconnect = Tkinter.Button(portsFrame, text=u'Disconnect', state='disabled', command=self.OnPressDisconnect)
		self.buttonDisconnect.grid(row=1, column=7, sticky='E', padx=2, pady=5)
	#self.buttonDisconnect.grid_propagate(False)


		self.labelConStatus = Tkinter.StringVar()
		labelStatusFrame = Tkinter.Label(portsFrame, textvariable=self.labelConStatus)
		labelStatusFrame.grid(row=1, column=1, columnspan=1, sticky='WE', padx=2, pady=5)
	#labelStatusFrame.grid_propagate(False)
		self.labelConStatus.set(u'Disconnected')

		#self.boxPortValue = Tkinter.StringVar()
		#self.boxPort = ttk.Combobox(self, textvariable=self.boxPortValue, state='readonly')
		#self.boxPort['values'] = ('/dev/ttyUSB0', '/dev/ttyUSB1')
		#self.boxPort.current(0)
		#self.boxPort.grid(column=4, row=5)

		self.boxPortValue = Tkinter.StringVar()
		self.boxPort = ttk.Combobox(portsFrame, width=6, textvariable=self.boxPortValue, postcommand=self.UpdtPortsList)
		self.boxPort.grid(row=1, column=3, sticky='E', padx=2, pady=5)
	#self.boxPort.grid_propagate(False)

		self.boxBaudValue = Tkinter.StringVar()
		self.boxBaud = ttk.Combobox(portsFrame, width=15, textvariable=self.boxBaudValue)
		self.boxBaud['values'] = ('9600', '19200 (WindEYE)', '38400', '57600', '115200')
		self.boxBaud.current(1)
		self.boxBaud.grid(row=1, column=5, sticky='E', padx=2, pady=5)
		
		labelPortFrame = Tkinter.Label(portsFrame, text='Port:')
		labelPortFrame.grid(row=1, column=2, columnspan=1, sticky='E', padx=2, pady=5)
		
		labelBaudFrame = Tkinter.Label(portsFrame, text='Baudrate:')
		labelBaudFrame.grid(row=1, column=4, columnspan=1, sticky='E', padx=2, pady=5)


		#---STATUS FRAME------------------------------------------------------------------------------->
		statusFrame = Tkinter.LabelFrame(self, text='Last Valid Values')
		statusFrame.grid(row=1, column=1, sticky='NES', padx=2, pady=2)
		statusFrame.columnconfigure(1, weight=1)


		labelV1Frame = Tkinter.LabelFrame(statusFrame, text='Vlos1 [Cm/s]')
		labelV1Frame.grid(row=1, column=1, columnspan=1, sticky='EWN', padx=2, pady=2)
		labelV1Frame.columnconfigure(1, weight=1)

		self.labelV1 = Tkinter.StringVar()
		labelV1Frame = Tkinter.Label(labelV1Frame, textvariable=self.labelV1)
		labelV1Frame.grid(row=1, column=1, columnspan=1, sticky='EW', padx=2, pady=2)
		self.labelV1.set(u'0')

	
		labelV2Frame = Tkinter.LabelFrame(statusFrame, text='Vlos2 [Cm/s]')
		labelV2Frame.grid(row=2, column=1, columnspan=1, sticky='EWN', padx=2, pady=2)
		labelV2Frame.columnconfigure(1, weight=1)

		self.labelV2 = Tkinter.StringVar()
		labelV2Frame = Tkinter.Label(labelV2Frame, textvariable=self.labelV2)
		labelV2Frame.grid(row=1, column=1, columnspan=1, sticky='EW', padx=2, pady=2)
		self.labelV2.set(u'0')

		
		labelAxialFrame = Tkinter.LabelFrame(statusFrame, text='Axial Component [Cm/s]')
		labelAxialFrame.grid(row=3, column=1, columnspan=1, sticky='EWN', padx=2, pady=2)
		labelAxialFrame.columnconfigure(1, weight=1)

		self.labelW = Tkinter.StringVar()
		labelWFrame = Tkinter.Label(labelAxialFrame, textvariable=self.labelW)
		labelWFrame.grid(row=1, column=1, columnspan=1, sticky='EW', padx=2, pady=2)
		self.labelW.set(u'0')

	
		labelDirectionFrame = Tkinter.LabelFrame(statusFrame, text='Direction [degree]')
		labelDirectionFrame.grid(row=4, column=1, columnspan=1, sticky='EWN', padx=2, pady=2)
		labelDirectionFrame.columnconfigure(1, weight=1)

		self.labelFI = Tkinter.StringVar()
		labelFIFrame = Tkinter.Label(labelDirectionFrame, textvariable=self.labelFI)
		labelFIFrame.grid(row=4, column=1, columnspan=1, sticky='EW', padx=2, pady=2)
		self.labelFI.set(u'0')
	

		labelStatusFrame = Tkinter.LabelFrame(statusFrame, text='Status [True/False]')
		labelStatusFrame.grid(row=5, column=1, columnspan=1, sticky='EWN', padx=2, pady=2)
		labelStatusFrame.columnconfigure(1, weight=1)

		self.labelS = Tkinter.StringVar()
		labelSFrame = Tkinter.Label(labelStatusFrame, textvariable=self.labelS)
		labelSFrame.grid(row=1, column=1, columnspan=1, sticky='EW', padx=2, pady=2)
		self.labelS.set(u'0')
		
		labelVFrame = Tkinter.LabelFrame(statusFrame, text='WindSpeed [Cm/s]')
		labelVFrame.grid(row=6, column=1, columnspan=1, sticky='EWN', padx=2, pady=2)
		labelVFrame.columnconfigure(1, weight=1)

		self.labelV = Tkinter.StringVar()
		labelVFrame = Tkinter.Label(labelVFrame, textvariable=self.labelV)
		labelVFrame.grid(row=1, column=1, columnspan=1, sticky='EW', padx=2, pady=2)
		self.labelV.set(u'0')

		sendFrame = Tkinter.LabelFrame(statusFrame, text='Send Command')
		sendFrame.grid(row=8, column=1, sticky='EWS', padx=2, pady=30)
		sendFrame.columnconfigure(1, weight=1)

		self.buttonOn = Tkinter.Button(sendFrame, text=u'On', state='disabled', command=self.OnPressOn)
		self.buttonOn.grid(row=1, column=1, sticky='WES', padx=5, pady=5)
		
		self.buttonOff = Tkinter.Button(sendFrame, text=u'Off', state='disabled', command=self.OnPressOff)
		self.buttonOff.grid(row=2, column=1, sticky='WES', padx=5, pady=5)
	
		self.buttonIdle = Tkinter.Button(sendFrame, text=u'Idle', state='disabled', command=self.OnPressIdle)
		self.buttonIdle.grid(row=3, column=1, sticky='WES', padx=5, pady=5)
	

		#Connected = Tkinter.IntVar()	#State of the GUI
		#Connected.set(0)
		#Connected.trace('w',ButtonStatusSwitch)



		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)
		self.resizable(True, True)
		self.update()
		self.geometry(self.geometry())
		#self.<object>.focus_set()	#set focus on object
		#self.<object>.selection_range(0, Tkinter.END)	#select all text

		# Initialization (FANCY)----------------------------------------------------------------
		self.Startup()
	
	def Startup(self):

		line1 = 250
		line2 = 250
		line3 = 250
		line4 = 250
		line5 = 250

		for i in xrange (100):

			self.graphCanvas.coords(self.windLine1, (line1, 50, line1, 300))
			self.graphCanvas.coords(self.windLine2, (line2, 50, line2, 300))
			self.graphCanvas.coords(self.windLine4, (line4, 50, line4, 300))
			self.graphCanvas.coords(self.windLine5, (line5, 50, line5, 300))

			line1 -= 2
			line2 -= 1
			line4 += 1
			line5 += 2

			self.graphCanvas.update_idletasks() # Update GRAPH ---------------------
			time.sleep(0.005)

	

	def OnPressOn(self):
		self.queueComm.put('\x6e\x31\x92')
		
	def OnPressOff(self):
		self.queueComm.put('\x6e\x30\x92')
	
	def OnPressIdle(self):
		self.queueComm.put('\x6e\x35\x92')

	def UpdtPortsList(self):
		self.boxPort['values'] = list(self.SearchPorts())
		if self.boxPort['values']:
			self.boxPort.current(0)		# set focus to first item from list

	def SearchPorts(self):
		if os.name == 'nt':
			#windows
			for i in range(256):
				try:
					s = serial.Serial(i)
					s.close()
					yield 'COM' + str(i + 1)
					self.buttonConnect['state'] = 'active'
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

		self.graphCanvas.itemconfig(self.leftBeam, fill='red')
		self.graphCanvas.itemconfig(self.rightBeam, fill='red')

		self.processQueueData()
		self.rotateArrows()

		self.buttonDisconnect['state'] = 'active'
		self.buttonConnect['state'] = 'disabled'
		self.buttonOn['state'] = 'active'
		self.buttonOff['state'] = 'active'
		self.buttonIdle['state'] = 'active'
		self.buttonLog['state'] = 'active'
		#	tkMessageBox.showinfo('Port','Port already open')

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

		self.labelConStatus.set(u'Disconnected')

		self.buttonDisconnect['state'] = 'disabled'
		self.buttonConnect['state'] = 'active'

		self.buttonLog['state'] = 'disabled'
		self.buttonOn['state'] = 'disabled'
		self.buttonOff['state'] = 'disabled'
		self.buttonIdle['state'] = 'disabled'

		self.graphCanvas.itemconfig(self.lidarCanvas, fill='red')
		self.graphCanvas.itemconfig(self.leftBeam, fill='')
		self.graphCanvas.itemconfig(self.rightBeam, fill='')
		
		self.effValues = []
		self.effTimeValues = []
		self.OnPressGraphReset()

		self.rotateArrowsInit(0, 0.001)

	def OnPressLog(self):
		if self.loggingData:
			self.loggingData = False
			self.logFile.closeFile()
			self.buttonLog['text'] = 'Log Data'

		else:
			t = time.strftime('%Y_%m_%d %H_%M_%S') #can add _%M', gmtime()) for GMT time
			filename = str(t)+'.txt'
			self.logFile = FileOperations()
			self.logFile.openFile(filename)
			self.loggingData = True
			self.buttonLog.config(text='Stop Log')
	
	def OnPressGraphOnOff(self):
		if self.drawing:
			self.drawing = False
			self.buttonGraphOnOff.config(text=u'Turn ON  graphs')
		elif not self.drawing:
			self.drawing = True
			self.buttonGraphOnOff.config(text=u'Turn OFF graphs')
	
	def OnPressGraphReset(self):

		self.speedValues = []
		self.badValues = []
		self.goodValues = []
		self.timeValues = []

		self.efficiency = 0
		self.totalSamples = 0
		self.goodSamples = 0
		self.badSamples = 0

	def rotateArrowsInit (self, F, speed):

		speed = speed
		F = F

		while round(self.angle) != round(F):

			if F > self.angle:
				self.angle += 1
			if F < self.angle:
				self.angle -= 1

			self.rotateObject(50, 50, 50, 300, 50, 125, self.windLine1, self.angle)
			self.rotateObject(150, 50, 150, 300, 150, 125, self.windLine2, self.angle)
			self.rotateObject(250, 50, 250, 300, 250, 125, self.windLine3, self.angle)
			self.rotateObject(350, 50, 350, 300, 350, 125, self.windLine4, self.angle)
			self.rotateObject(450, 50, 450, 300, 450, 125, self.windLine5, self.angle)

			self.graphCanvas.update_idletasks() # Update GRAPH ---------------------
			time.sleep(speed)
	
	def rotateArrows (self):

		logger.debug('rotate')
		if round(self.angle) != round(self.angleF):

			if self.angleF > self.angle:
				self.angle += 1
			if self.angleF < self.angle:
				self.angle -= 1

			self.rotateObject(50, 50, 50, 300, 50, 125, self.windLine1, self.angle)
			self.rotateObject(150, 50, 150, 300, 150, 125, self.windLine2, self.angle)
			self.rotateObject(250, 50, 250, 300, 250, 125, self.windLine3, self.angle)
			self.rotateObject(350, 50, 350, 300, 350, 125, self.windLine4, self.angle)
			self.rotateObject(450, 50, 450, 300, 450, 125, self.windLine5, self.angle)

			self.graphCanvas.update_idletasks() # Update GRAPH ---------------------

		self.rotateArrowsID = self.after(100, self.rotateArrows)
				
	def rotateObject (self, x1, y1, x2, y2, p, q, objectHandler, F):
		
		F = F
		oH = objectHandler

		x1 = x1
		y1 = y1

		x2 = x2
		y2 = y2

		p = p
		q = q


		Frad = (math.pi/180)*F

		if Frad >= 0:
			x1t = ((y1-q)*math.sin(Frad))
			y1t = ((y1-q)*math.cos(Frad))
			x2t = ((y2-q)*math.sin(Frad))
			y2t = ((y2-q)*math.cos(Frad))
	
		if Frad < 0:
			x1t = ((y1-q)*math.sin(Frad))
			y1t = ((y1-q)*math.cos(Frad))
			x2t = ((y2-q)*math.sin(Frad))
			y2t = ((y2-q)*math.cos(Frad))

		self.graphCanvas.coords(oH, (x1t+p, y1t+q, x2t+p, y2t+q))

	def movingAverage (self, values, window):
		weights = numpy.repeat(1.0, window)/window
		sma = numpy.convolve(values, weights, 'valid')
		return sma
		
	def processQueueData(self):
		try:
			rawData = self.queueData.get(0)	#block and timeout, rise exception after half second (1, 05) - block enabled, rise exception after 0.5 s
		except Queue.Empty:
			pass
		else:
			logger.debug('G Got data from queue start processing')
			startChar = rawData.find('\xea\x21')
			if (startChar!=-1)and(rawData[startChar+1]=='\x21')and(rawData[startChar+36]=='\x16'):

				V1 = (256*ord(rawData[startChar+2]))+ord(rawData[startChar+3])
				V2 = (256*ord(rawData[startChar+4]))+ord(rawData[startChar+5])
				W = (256*ord(rawData[startChar+6]))+ord(rawData[startChar+7])
				F = (256*ord(rawData[startChar+8]))+ord(rawData[startChar+9])
				S = ord(rawData[startChar+10])
				Ar1 = (256*ord(rawData[startChar+11]))+ord(rawData[startChar+12])
				At1 = (256*ord(rawData[startChar+13]))+ord(rawData[startChar+14])
				Ar2 = (256*ord(rawData[startChar+15]))+ord(rawData[startChar+16])
				At2 = (256*ord(rawData[startChar+17]))+ord(rawData[startChar+18])
				M1 = ord(rawData[startChar+19])
				M2 = ord(rawData[startChar+20])
				G1 = ord(rawData[startChar+21])
				G2 = ord(rawData[startChar+22])
				W1 = ord(rawData[startChar+23])
				W2 = ord(rawData[startChar+24])
				N1 = ord(rawData[startChar+25])
				N2 = ord(rawData[startChar+26])
				Min1 = (256*ord(rawData[startChar+27]))+ord(rawData[startChar+28])
				Max1 = (256*ord(rawData[startChar+29]))+ord(rawData[startChar+30])
				Min2 = (256*ord(rawData[startChar+31]))+ord(rawData[startChar+32])
				Max2 = (256*ord(rawData[startChar+33]))+ord(rawData[startChar+34])

				if ord(rawData[8])>127:
					F -=65536
				F = F/100

				if (V2>V1)and(F>0):		#Fix for some old systems giving the positive value all the time
					F = -F

		
				#F = F+int((random.random()*10))
				#S = S*random.randint(0,1)

				V = round(W / math.cos(abs(math.radians(F))))	

				# Update FINAL DATA ------------------------------
				t = '"' + time.strftime('%Y-%m-%d %H:%M:%S') + '"'
				c = ', '
				finalData = t+" "+str(V1)+c+str(V2)+c+str(W)+c+str(F)+c+str(S)+c+str(Ar1)+c+str(At1)+c+str(Ar2)+c+str(At2)+c+str(M1)+c+str(M2)+c+str(G1)+c+str(G2)+c+str(W1)+c+str(W2)+c+str(N1)+c+str(N2)+c+str(Min1)+c+str(Max1)+c+str(Min2)+c+str(Max2)

				logger.debug('G data processed')
				# LOGGING ------------------------------------------------
				if self.loggingData:
					self.logFile.writeToFile(finalData)
				
				#REDRAWING Graph + adding DATA for PLOTTING ---------------------------------------------------
				self.labelData.set(finalData) #setting frame values

				self.totalSamples += 1		#increase for measuring efficiency
				if S:
					self.goodSamples += 1	#measuring efficiency

					self.graphCanvas.itemconfig(self.lidarCanvas, fill='green')
					
					self.graphCanvas.itemconfig(self.leftBeam, fill='green')
					self.graphCanvas.itemconfig(self.rightBeam, fill='green')
					
					self.labelV1.set(V1)
					self.labelV2.set(V2)
					self.labelW.set(W)
					self.labelFI.set(F)
					self.labelS.set(S)
					self.labelV.set(V)

					self.graphCanvas.update_idletasks()
					
					if F<(60) and F>(-60):			#!!!!!!!!!!!!!!!!! adjus to smooth movement
						self.angleF = F

			
				else:
					self.badSamples += 1		#measuring efficiency

					self.labelS.set(S)
					self.graphCanvas.itemconfig(self.lidarCanvas, fill='red')
					self.graphCanvas.itemconfig(self.leftBeam, fill='red')
					self.graphCanvas.itemconfig(self.rightBeam, fill='red')

					self.graphCanvas.update_idletasks()

				logger.debug('G gui labels updated')
				# Update STATIC PLOTS ------------------------------------------
				self.efficiency = int((100.0 / self.totalSamples) * self.goodSamples)

				if self.totalSamples == 60:
					self.totalSamples = 0
					self.badSamples = 0
					self.goodSamples = 0
					if len(self.effValues)>59:
						for x in xrange (1, 60):			# push all values to left and store speed to last position
							self.effValues[x-1] = self.effValues[x]
						self.effValues[59] = self.efficiency
					else:
						self.effValues.append(self.efficiency)
						self.effTimeValues.append(len(self.effTimeValues))

					self.plotBar.cla()
					self.plotBar.axis([min(self.effTimeValues), max(self.effTimeValues)+1, 0, max(self.effValues)+5])
					self.bars = self.plotBar.bar(self.effTimeValues, self.effValues)
					self.plotBar.set_xlabel('Elapsed time-frame [min]')
					self.plotBar.grid(True)
	
				if self.drawing:

					self.plotEff.cla()
					self.fracs = [self.efficiency, 100-self.efficiency]
					self.pie_wedges = self.plotEff.pie(self.fracs, colors=('g','r'))
					self.plotEff.set_xlabel(str(self.efficiency) + ' % ' + '(' + str(self.goodSamples) + ' / ' + str(self.badSamples) + ')')
					self.plotEff.set_title('Efficiency last 60 seconds',fontsize=12)
					for wedges in self.pie_wedges[0]:
						wedges.set_edgecolor('white')

				if len(self.speedValues)>29:
					for x in xrange (1, 30):			# push all values to left and store speed to last position
						self.speedValues[x-1] = self.speedValues[x]
					self.speedValues[29] = F
	
					for x in xrange (0, len(self.goodValues)):
						self.goodValues[x] -= 1
					for x in xrange (0, len(self.badValues)):
						self.badValues[x] -= 1

					try:
						self.goodValues.remove(-1)
					except:
						pass
					try:
						self.badValues.remove(-1)
					except:
						pass
				
					if S:
						self.goodValues.append(29)
					else:
						self.badValues.append(29)

				else:
					self.speedValues.append(F)

					if S:
						self.goodValues.append(len(self.speedValues)-1)
					else:
						self.badValues.append(len(self.speedValues)-1)

					self.timeValues = linspace(0, len(self.goodValues+self.badValues), len(self.speedValues))#.astype('int') 

				self.numpySpeed = numpy.array(self.speedValues)

				if self.drawing:
				
					self.plotSpeed.axis([min(self.timeValues), max(self.timeValues)+0.1, min(self.speedValues)-5, max(self.speedValues)+5])

					self.lineSpeed[0].set_data(self.timeValues, self.speedValues)

					self.lineGoodSpeedValues[0].set_data(self.timeValues[self.goodValues], self.numpySpeed[self.goodValues])
					self.lineBadSpeedValues[0].set_data(self.timeValues[self.badValues], self.numpySpeed[self.badValues])
					
					self.speedCanvas.draw()
				logger.debug('G end of processing')
		
			else:
				logger.info("Gui found rubbish in Queue")
		finally:
						
			self.queueDataID = self.after(50, self.processQueueData) #after_cancel to cancel the callback


if __name__ == "__main__":
	app = MyGUI(None)
	app.title('RS-485 Windar')
	app.mainloop()

		
