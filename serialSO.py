from PyQt4 import QtCore, QtGui
import time
import sys
import math


class SerialCon(QtCore.QThread):

    received = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self)
        # specify thread context for signals and slots:
        # test: comment following line, and run again
        self.moveToThread(self)
        # timer:
        self.timer = QtCore.QTimer()
        self.timer.moveToThread(self)
        self.timer.setInterval(800)
        self.timer.timeout.connect(self.readData)

    def run(self):
        self.timer.start()
        #start eventloop
        self.exec_()

    def readData(self):
        # keeping the thread busy
        # figure out if the GUI remains responsive (should be running on a different thread)
        result = []
        for i in range(1,1000000):
            result.append(math.pow(i,0.2)*math.pow(i,0.1)*math.pow(i,0.3))
        #
        self.received.emit("New serial data!")

    @QtCore.pyqtSlot(object)
    def writeData(self, data):
       #print(self.currentThreadId())
       print(data)

class MyGui(QtGui.QWidget):
    serialWrite = QtCore.pyqtSignal(object)

    def __init__(self, app, parent=None):
       self.app = app
       super(MyGui, self).__init__(parent)
       self.initUI()

    def initUI(self):
       self.bSend = QtGui.QPushButton("Send",self)
       self.bSend.clicked.connect(self.sendData)
       self.show()
    def closeEvent(self, event):
        print("Close.")
        self.serialc.quit();

    @QtCore.pyqtSlot(object)
    def updateData(self, data):
        print(data)

    def sendData(self, pressed):
       self.serialWrite.emit("Send Me! Please?")

    def usingMoveToThread(self):
        self.serialc = SerialCon()
        # binding signals:
        self.serialc.received.connect(self.updateData)
        self.serialWrite.connect(self.serialc.writeData)
        # start thread
        self.serialc.start()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    guui = MyGui(app)
    guui.usingMoveToThread()
    sys.exit(app.exec_())