import consts

import numpy as np
from pysoundcard import Stream as PyScStream
import pysoundcard
import librosa
import logging


def de_stereo(data):
    if len(data.shape) > 1:
        return data.T[0].T
    return data


class Stream(object):
    '''
    Stream of data that notifies listeners whenever new data is queued
    '''
    def __init__(self):
        self.updateListeners = []

    def addEventListener(self, listener):
        '''
        If you register something as a listener for the stream, make sure not to perform
        too much work on the callback. It will be completed on this stream object's
        primary thread, which might slow things down.
        '''
        self.updateListeners.append(listener)

    def enqueueChunk(self, chunk):
        for listener in self.updateListeners:
            listener.onNewStreamData(chunk)


class InputStream(Stream):

    def __init__(self, device=None):
        super(self.__class__, self).__init__()
        self.device = device if device is not None else self._findDevice()
        self.sr = consts.sr
        self.inputStream = PyScStream(
            sample_rate=self.sr, block_length=consts.window_hop,
            callback=self.inputStreamCallback, input_device=self.device)
        self.iteration = 0

    def _findDevice(self):
        inputPriority = [
            "FastTrack Pro",
            "Built-in Input",
            "Soundflower (2ch)",
        ]
        for input_ in inputPriority:
            for dev in pysoundcard.devices():
                if dev['name'] == input_ and dev['input_channels'] > 0:
                    return dev

    def inputStreamCallback(self, inData, numFrames, timeInfo, status):
        '''
        Wrap our stream callback in the default pysoundcard callback
        '''
        self.iteration += 1
        if self.iteration % 3 == 0:
            print "%.2f" % np.sum(inData)
        self.enqueueChunk(inData)
        return (np.zeros((numFrames, 2)), pysoundcard.continue_flag)

    def read(self, *args, **kwargs):
        return self.inputStream.read(*args, **kwargs)

    def start(self):
        self.inputStream.start()

    def stop(self):
        self.inputStream.stop()


class WavFileStream(Stream):
    '''
    Data stream that reads data from a WAV File.
    Note that this might not be appropriate to use for large audio files (> 100 MB) as
        it appears to load the full file into memory.
    '''
    def __init__(self, filename, sampleRate=consts.sr, chunkSize=consts.window_hop):
        super(self.__class__, self).__init__()
        self.filename = filename
        self.sampleRate = sampleRate
        self.chunkSize = chunkSize

    def stream(self):
        signal, sr = librosa.load(self.filename, sr=self.sampleRate)
        logging.debug('Loaded signal at sample rate %d', sr)
        logging.debug('Signal length is %d', len(signal))
        pointer = 0
        while pointer < len(signal):
            chunk = signal[pointer:pointer + self.chunkSize]
            pointer += self.chunkSize
            self.enqueueChunk(chunk)
