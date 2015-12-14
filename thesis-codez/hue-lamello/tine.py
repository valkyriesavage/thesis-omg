import librosa
import math
import numpy as np
from scipy import signal

import consts

class TineStrike:

    def __init__(self, controlId, tineId, audioPath):
        ''' controlId may be tine ID for now, but can also stand for button types, dial positions, etc. '''
        self.audioPath = audioPath 
        self.y = None
        self.controlId = controlId
        self.tineId = tineId
        self.features = self.processFeatures()

    def processFeatures(self):
        SAMPLE_START = 1600
        DEFAULT_WINDOW = 2048
        self.y, _ = librosa.load(self.audioPath, sr=consts.sr)
        filtered = band_filter(self.y)
        windowed = filtered[SAMPLE_START:SAMPLE_START + DEFAULT_WINDOW]
        return np.array([getAudioFeatures(windowed)])


def band_filter(y):
    BUTTERWORTH_B, BUTTERWORTH_A = signal.butter(consts.filter_order,
          [consts.filter_low_normed,consts.filter_high_normed], 'bandpass')
    return signal.lfilter(BUTTERWORTH_B, BUTTERWORTH_A, y)


def getAudioFeatures(data):

    def mostInteresting(columns):
        largest_number = -9999999999999
        best_column = np.zeros(columns.shape[-1])
        for col in columns.T:
            if np.sum(col) >= largest_number:
                best_column = col
                largest_number = np.sum(col)
        return best_column

    STFT = np.abs(librosa.stft(data, hop_length=consts.hop_length_fft, n_fft=consts.n_fft))**2

    # STFT is there to speed up Mel + logSF computation
    mels = librosa.feature.melspectrogram(S=STFT, n_mels=consts.n_mels)
    best_mel_col = mostInteresting(mels)  # length 128
    
    bunchafeats = []
    bunchafeats.extend(best_mel_col)
    bunchafeats = np.array(bunchafeats)

    # normalize!
    bunchafeats /= math.sqrt(sum(bunchafeats**2))
    return bunchafeats