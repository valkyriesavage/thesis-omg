import Tkinter as tk

from resource import ControlBuilder
from stream import InputStream
from detector import EventDetector
from concurrent.futures import ThreadPoolExecutor
from OSC import OSCClient, OSCMessage
import logging

from beautifulhue.api import Bridge

client = OSCClient()
client.connect(("localhost", 4344))
logging.basicConfig(level=logging.INFO, format="%(message)s")


bridge = Bridge(device={'ip':'192.168.1.50'}, user={'name':'beautifulhuetest'})

class RtTineDetectApp(tk.Frame):
    '''
    Note that best effects have been found using the Scarlett 18i20 sound card, with the gain for
    a contact mic set to 0.8.
    '''
    MARKER_HEIGHT = 30

    def __init__(self, parent, minPosition=-1, maxPosition=5):
        tk.Frame.__init__(self)
        self.minPosition = minPosition
        self.maxPosition = maxPosition
        self.parent = parent
        self.recording = False
        self.stream = InputStream()
        control = ControlBuilder().buildControl('config/control/slider_observed_4tines.json')
        detector = EventDetector(
            self.stream, control, windowLength=2048, windowHop=200,
            scaleScoresByFequency=True, gaussianStdDev=2)
        detector.addEventListener(self)
        self.pack(fill=tk.BOTH, expand=1)
        self._createWidgets()
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _createWidgets(self):
        self.update_idletasks()
        self.recordButton = tk.Button(self, text="Listen", command=self.toggleRecord)
        self.recordButton.pack(side=tk.TOP)
        self.canvas = tk.Canvas(self.parent, width=200, height=600)
        self.canvas.pack(side=tk.TOP)
        self.canvas.create_line(
            80, self._axisYFromPosition(-1), 80, self._axisYFromPosition(15), width=2)
        self.marker = self.canvas.create_rectangle(0, 0, 0, 0)
        self._moveMarkerToPosition(self.minPosition + 2)
        self.toggleRecord()

    def _moveMarkerToPosition(self, position):
        middleY = self._axisYFromPosition(position)
        topY = middleY - self.MARKER_HEIGHT / 2
        bottomY = middleY + self.MARKER_HEIGHT / 2
        #client.send(OSCMessage("/slider/", [(position * 400.0 + 400.0) / 2048.0]))
        hue_value = (((middleY - 0) * (254.0 - 1.0)) / (600.0 - 0.0)) + 1.0
        resource_1 = {
            'which':1,
            'data':{
                'state':{'on':True, 'bri':hue_value} # can be 1-254
            }
        }
        resource_2 = {
            'which':2,
            'data':{
                'state':{'on':True, 'bri':hue_value} # can be 1-254
            }
        }
        resource_3 = {
            'which':3,
            'data':{
                'state':{'on':True, 'bri':hue_value} # can be 1-254
            }
        }
        bridge.light.update(resource_1)
        bridge.light.update(resource_2)
        bridge.light.update(resource_3)
        #self.canvas.coords(self.marker, 105, topY, 135, bottomY)

    def _axisYFromPosition(self, value):
        TOP = 0
        BOTTOM = 600
        axisRange = abs(TOP - BOTTOM)
        valueRange = self.maxPosition - self.minPosition
        relativeHeight = float((value - self.minPosition)) / valueRange
        y = BOTTOM - (relativeHeight * axisRange)
        return y

    def toggleRecord(self):
        if self.recording:
            self.stream.stop()
            self.recordButton.config(text="Listen")
        else:
            self.stream.start()
            self.recordButton.config(text="Stop")
        self.recording = not self.recording

    def onEventDetected(self, event):
        if self.marker:
            print "In onEventDetect"
            ''' Submit move action on separate thread so that we don't block detector.
                Also, force update of UI because Tkinter doesn't always update quickly. '''
            self.executor.submit(self._moveMarkerToPosition, event.classId)
            self.update()


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("200x640")
    app = RtTineDetectApp(root)
    root.title("Tine Strike Realtime Demo")
    root.mainloop()
