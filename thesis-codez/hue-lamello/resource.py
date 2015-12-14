import os.path
from position import BooleanPosition, NominalPosition, LinearPosition
from model import Control
from tine import TineStrike
import logging
import json


class ControlBuilder(object):
    '''
    Builds control object from a configuration file
    '''
    POSITION_TYPE_LOOKUP = {
        'boolean': BooleanPosition,
        'nominal': NominalPosition,
        'linear': LinearPosition
    }
    def buildControl(self, configFilename):
        with open(configFilename, 'r') as configFile:
            spec = json.loads(configFile.read())
            PositionType = self.POSITION_TYPE_LOOKUP[spec['positionType']]
            position = PositionType()
            control = Control(
                tineFrequencies=spec['tineFrequencies'],
                onsetAmplitude=spec['onsetAmplitude'],
                steadyStateSeconds=spec['steadyStateSeconds'],
                transientSeconds=spec['transientSeconds'],
                position=position
            )
        return control


class StrikeBuilder(object):
    '''
    Builds strike recordings with features for all training recordings
    '''
    def buildStrikes(self, trainingDir):
        samples = []
        controltypeDirs = os.listdir(trainingDir)
        for controltype in controltypeDirs:
            controltypePath = os.path.join(trainingDir, controltype)
            controlIds = os.listdir(controltypePath)
            for controlId in controlIds:
                controlPath = os.path.join(controltypePath, controlId)
                tineIds = os.listdir(controlPath)
                for tineId in tineIds:
                    tinePath = os.path.join(controlPath, tineId)
                    recordings = os.listdir(tinePath)
                    for rec in recordings:
                        filename = os.path.join(tinePath, rec)
                        if '.wav' not in filename:
                            continue
                        samples.append(TineStrike(int(controlId), int(tineId), filename))
        logging.info('Loaded %d samples', len(samples))
        return samples
