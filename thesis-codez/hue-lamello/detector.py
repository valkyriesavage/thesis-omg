from stream import de_stereo
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import logging
import scipy.signal
import librosa
from enum import Enum
from sys import maxint
from audio import Fft
from _collections import defaultdict


class Event(object):

    def __init__(self, classId, score, windowIndex, strikeIndex):
        self.classId = classId
        self.score = score
        self.windowIndex = windowIndex
        self.strikeIndex = strikeIndex


class WindowState(Enum):
    TRANSIENT = 1,
    STEADY_STATE = 2,
    NEUTRAL = 3


class EventDetector(object):

    def __init__(self, stream, control, windowLength=2048, windowHop=800, sampleRate=16000,
                 scaleScoresByFequency=True, gaussianStdDev=2):
        '''
        At the least, an EventDetector has to be initialized with:
        stream: a stream of audio samples that contains events
        control: a spec of a control, including its tine frequencies and envelope information
        '''
        stream.addEventListener(self)
        self.executorPool = ThreadPoolExecutor(max_workers=1)
        self.windowLength = windowLength
        self.windowHop = windowHop
        self.sampleRate = sampleRate
        self.scaleScoresOnFrequency = scaleScoresByFequency
        self.fft = Fft(self.windowLength, self.sampleRate)

        ''' Transfer control characteristics to detector specifications '''
        self.onsetAmplitude = control.onsetAmplitude
        self.transientTime = control.transientSeconds
        self.steadyStateTime = control.steadyStateSeconds
        tineBins = [self.fft.getFrequencyBin(freq) for freq in control.tineFrequencies]
        self.classes = dict(enumerate(tineBins))
        ''' Precompute Gaussian windows so that we don't have to repeat this work. '''
        ''' Also, multiple each Gaussian window by the bin index to scale higher frequencies more than
            lower frequencies. '''
        self.gaussianWindows = [
            self._getGaussianWindow(self.fft.getBinCount(), gaussianStdDev, bin_)
            for bin_ in tineBins]

        ''' State variables '''
        self.fullSignal = np.zeros(2)
        self.windowIndex = -1
        self.lastWindowStart = None
        self.firstRecentOnsetWindow = -maxint - 1
        self.eventListeners = []
        self.recentDetections = []
        self.strikeIndex = 0

    def onNewStreamData(self, chunk):
        ''' While this might look like a useless wrapper, in fact we need
            to perform processing asynchronously so that PySoundcard doesn't
            get overloaded by our processing. '''
        self.executorPool.submit(self._processChunk, chunk)

    def finishProcessing(self):
        ''' The following call waits for all tasks to complete before continuing. '''
        self.executorPool.shutdown(wait=True)
        self.executorPool = ThreadPoolExecutor(max_workers=1)

    def _processChunk(self, chunk):
        state = None
        if np.any(chunk):
            chunk = de_stereo(chunk)
            self.fullSignal = np.concatenate((self.fullSignal, chunk))
            ''' Slide window as far as it can go through the new signal '''
            while True:
                windowIndex, window = self._getNextWindow()
                if windowIndex == -1:
                    break
                state = self._getWindowState(
                    windowIndex, self.firstRecentOnsetWindow,
                    self.windowHop, self.windowLength, self.sampleRate, self.transientTime,
                    self.steadyStateTime)
                if state == WindowState.NEUTRAL:
                    if self._hasTransientOnset(window):
                        logging.info("Found transient at window %d", windowIndex)
                        self.strikeIndex += 1
                        self.firstRecentOnsetWindow = windowIndex
                        self.recentDetections = []
                elif state == WindowState.STEADY_STATE:
                    ''' We only scan an classify windows that are considered in steady state.
                        This means large frequencies from the stirke have subsided. '''
                    logging.debug("Steady state at window %d", windowIndex)
                    classScores = self.scanWindow(window)
                    for classIndex, score in classScores.items():
                        self.recentDetections.append(
                            Event(classIndex, score, windowIndex, self.strikeIndex))
                    event = self._findEvent(self.recentDetections)
                    if event is not None:
                        self._reportEvent(event)
                else:
                    continue

    def scanWindow(self, window=[]):
        fftCoefficients = self.fft.performFft(window)
        ''' Normalize FFT so that the frequency bins sum to 1 '''
        fftNormal = fftCoefficients / sum(fftCoefficients)
        ''' Find scores for all possible classifications. '''
        scores = {}
        for classId, _ in self.classes.items():
            gaussianWindow = self.gaussianWindows[classId]
            score = fftNormal.dot(gaussianWindow)
            ''' Scale by the value of the tine bin if option specified to aid the
                shorter-time, softer higher frequencies to get detected. '''
            if self.scaleScoresOnFrequency:
                score *= (self.classes[classId] * self.classes[classId])
            scores[classId] = score
        return scores

    def _findEvent(self, detections, minWindows=1):
        '''
        Filter through recent detections to determine if there has been an event.
        Effectively a smoother.
        '''
        windows = set([d.windowIndex for d in detections])
        if len(windows) < minWindows:
            return
        scores = defaultdict(int)
        for detection in detections:
            scores[detection.classId] += detection.score
        bestClass, highestScore = max(scores.items(), key=lambda item: item[1])
        detectionsWithClass = filter(lambda d: d.classId == bestClass, detections)
        recentDetection = detectionsWithClass[-1]
        return Event(
            bestClass, highestScore, recentDetection.windowIndex,
            recentDetection.strikeIndex)

    def _reportEvent(self, event):
        for listener in self.eventListeners:
            listener.onEventDetected(event)

    def _getNextWindow(self):
        if self.lastWindowStart is None:
            newWindowStart = 0
            self.windowIndex = 0
        else:
            newWindowStart = self.lastWindowStart + self.windowHop
            self.windowIndex += 1
        if (newWindowStart + self.windowLength) < len(self.fullSignal):
            window = self.fullSignal[newWindowStart:newWindowStart + self.windowLength]
            logging.debug(
                "Returning window with start %d, end %d",
                newWindowStart, newWindowStart + self.windowLength)
            self.lastWindowStart = newWindowStart
            return self.windowIndex, window
        else:
            return -1, None

    def _hasTransientOnset(self, signal):
        ''' Check whether a window contains onset of a transient response to strike '''
        THRESHOLD_ONSET_STRENGTH = 10  # not sure how we found this number
        onset_strength = librosa.onset.onset_strength(y=signal, sr=self.sampleRate)
        loudestAmplitude = max(np.abs(signal))
        if (loudestAmplitude > self.onsetAmplitude and
                np.any(onset_strength > THRESHOLD_ONSET_STRENGTH)):
            return True
        else:
            return False

    def _getWindowState(
            self, windowIndex, recentFirstOnsetWindowIndex, hopLength, windowLength,
            sampleRate, transientTime, steadyStateTime):
        ''' Check whether window represents transient, steady state, or something else '''
        hopsToJustifyTransient = (windowLength / hopLength) - 1
        timeOfHop = float(hopLength) / sampleRate
        hopsInTransient = transientTime / timeOfHop
        steadyStateStart = recentFirstOnsetWindowIndex + hopsToJustifyTransient + hopsInTransient
        hopsInSteadyState = steadyStateTime / timeOfHop
        steadyStateEnd = steadyStateStart + hopsInSteadyState
        if windowIndex >= steadyStateStart and windowIndex <= steadyStateEnd:
            return WindowState.STEADY_STATE
        elif windowIndex >= recentFirstOnsetWindowIndex and windowIndex < steadyStateStart:
            return WindowState.TRANSIENT
        else:
            return WindowState.NEUTRAL

    def _getGaussianWindow(self, length, std, center=None):
        ''' Center: the index of the Gaussian window that represents the center. '''
        if center is None:
            center = length / 2
        ''' By default, Scipy Gaussian function puts center in middle of window.
            To allow us to move it either all the way to the left or all the
            way to the right, we generate the full window at twice the length,
            and then align it to the center that the user specified. '''
        scipyGaussian = scipy.signal.gaussian(M=length * 2, std=std)
        scipyCenter = length
        shiftAmount = scipyCenter - center
        return scipyGaussian[shiftAmount:shiftAmount + length]

    def addEventListener(self, listener):
        self.eventListeners.append(listener)
