import sys
from PyQt4 import QtCore, QtGui
import time

class Gui(QtGui.QWidget):
	def __init__(self, parent=None):
		QtGui.QGroupBox.__init__(self, parent)
		self.gcenter = QtGui.QPushButton("X", self)
		self.textout = QtGui.QLineEdit("default")
		self.textout2 = QtGui.QLineEdit("")
		guiLayout = QtGui.QGridLayout()
		guiLayout.addWidget(self.gcenter,1,0)
		guiLayout.addWidget(self.textout,1,1)
		self.setLayout(guiLayout)
		self.thread = logJ()
		self.thread.start()
		self.connect(self.gcenter, QtCore.SIGNAL("clicked()"), self.thread.toggle)
		self.connect(self.textout, QtCore.SIGNAL("textChanged(QString)"), self.thread.setValue)


class logJ(QtCore.QThread):
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)
		self.value = 0
		self.alive = 1
		self.running = 0


	def run(self):
		while self.alive:
			while self.running:
				try :
					a = self.aggiorna()
					#startj(0,0)
					print a
					time.sleep(1)
				except :
					print 'exit from Joy mode'


	def toggle(self):
		if self.running:
			self.running = 0
		else :
			self.running = 1


	def stop(self):
		self.alive = 0
		self.running = 0
		self.wait()


	def setValue(self, value):
		self.value = value


	def aggiorna(self):
		newvalue = str(self.value)
		return newvalue


if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)
	gui = Gui()
	gui.show()
	sys.exit(app.exec_())