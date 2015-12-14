class Position(object):
    '''
    Abstract class.
    A position class defines rules on how to compute a location of a touch
    given a sequence of IDs of tines that have been struck.
    
    The basic procedure is something like this:
    1. tineId = readTineStrike()
    2. position.update(tineId)
    3. currentPosition = position
    Iterate with continual readings of tine IDs struck to get the current positions.
    '''
    
    def __init__(self):
        self.value = None
    
    def update(self, tineId):
        pass
    
    def getValue(self):
        return self.value


class BooleanPosition(Position):
    '''
    A position that can either be on (1) or off (0).
    
    Currently there isn't a way to make sure that this turns back off after being engaged.
    '''

    def __init__(self):
        super(self.__class__, self).__init__()
        self.value = 0

    def update(self, tineId):
        super(self.__class__, self).update(tineId)
        ''' If a tine is hit, we claim that this control is in position '1' '''
        self.value = 1


class NominalPosition(Position):
    '''
    Position where the value is equal to the last tine that has been struck. Described as 'nominal'
    because although it can take on multiple values, they are not ordered.
    '''
    def update(self, tineId):
        if type(tineId) is not int:
            raise ValueError("Tine ID for nominal position must be integer")
        super(self.__class__, self).update(tineId)
        self.value = tineId


class LinearPosition(Position):
    '''
    Position describes a point on a sliding scale. This point is indicated by a sequence of
    two or more tines struck in sequence.
    '''
    pass