class Control(object):
    '''
    A 3D-printed control, which can be described by its unique ID and the current
    'position' or state of the control.
    '''
    def __init__(self, tineFrequencies, onsetAmplitude, transientSeconds, steadyStateSeconds, position):
        self.tineFrequencies = tineFrequencies
        self.onsetAmplitude = onsetAmplitude
        self.transientSeconds = transientSeconds
        self.steadyStateSeconds = steadyStateSeconds
        self.position = position

    def update(self, tineId):
        self.position.update(tineId)

    @property
    def positionType(self):
        return type(self.position)


class SystemModel(object):
    '''
    Model of the full control system (collection of controls) that updates and reports state of
    each control component in the system.
    '''
    def __init__(self, classifier, controls):
        self.controls = controls