'''
File containing global constants.
NOTE that many of these constants have been moved into the files that use them,
and are no longer called from here, to better package these constants with
the entities that use them.
'''

''' for testing '''
how_many_tines = 6

''' for making features '''
n_mfcc = 13
n_fft = 2048
hop_length_onset = 32
hop_length_fft = 256
n_mels = 128

''' for PCA '''
min_variance = 0.001

''' for chunking data '''
window_length = 2048
window_hop = 800
sr = 16000
nyquist = sr/2.0

''' for bandpass filter '''
filter_low = 400.0
filter_high = 7000.0
filter_low_normed = filter_low/nyquist
filter_high_normed = filter_high/nyquist
filter_order = 10

''' for onset detection '''
delta = .2
wait = 128 # TODO change based on sr
strength = 10
amplitude = 0.0025
start = -750
end = window_length+start
