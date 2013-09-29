# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Name:         streamStatus.py
# Purpose:      functionality for reporting on the notational status of streams
#
# Authors:      Josiah Wolf Oberholtzer
#
# Copyright:    Copyright © 2008-2012 Michael Scott Cuthbert and the music21
#               Project
# License:      LGPL, see license.txt
#------------------------------------------------------------------------------


import unittest

from music21 import environment

environLocal = environment.Environment(__file__)


#------------------------------------------------------------------------------


class StreamStatus(object):

    ### CLASS VARIABLES ###

    __slots__ = ('_client',)

    ### INITIALIZER ###

    def __init__(self, client):
        self._client = client

    ### PUBLIC METHODS ###

    def haveAccidentalsBeenMade(self):
        '''
        If Accidentals.displayStatus is None for all contained pitches, it as
        assumed that accidentals have not been set for display and/or
        makeAccidentals has not been run. If any Accidental has displayStatus
        other than None, this method returns True, regardless of if
        makeAccidentals has actually been run.
        '''
        for p in self.client.pitches:
            if p.accidental is not None:
                if p.accidental.displayStatus is not None:
                    return True
        return False

    def haveBeamsBeenMade(self):
        '''
        If any Note in this Stream has .beams defined, it as assumed that Beams
        have not been set and/or makeBeams has not been run. If any Beams
        exist, this method returns True, regardless of if makeBeams has
        actually been run.
        '''
        for n in self.client.flat.notes:
            if n.beams is not None and len(n.beams.beamsList):
                return True
        return False

    ### PUBLIC PROPERTIES ###

    @property
    def client(self):
        return self._client


#------------------------------------------------------------------------------


class Test(unittest.TestCase):
    '''
    Note: all Stream tests are found in test/testStream.py
    '''

    def runTest(self):
        pass


#------------------------------------------------------------------------------


if __name__ == "__main__":
    import music21
    music21.mainTest(Test)
