# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         testSerialization.py
# Purpose:      tests for serializing music21 objects
#
# Authors:      Christopher Ariza
#
# Copyright:    (c) 2012 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------


import copy, types, random
import doctest, unittest
import sys
from copy import deepcopy


import music21 # needed to do fully-qualified isinstance name checking

from music21 import environment
_MOD = "testSerialization.py"
environLocal = environment.Environment(_MOD)





#-------------------------------------------------------------------------------
class Test(unittest.TestCase):

    def runTest(self):
        '''Need a comment
        '''
        pass

    def testBasicA(self):
        from music21 import note, stream

        n1 = note.Note('G#3', quarterLength=3)
        n1.lyric = 'testing'
        self.assertEqual(n1.pitch.nameWithOctave, 'G#3')        
        self.assertEqual(n1.quarterLength, 3.0)        
        self.assertEqual(n1.lyric, 'testing')        
        
        raw = n1.json

        n2 = note.Note()
        n2.json = raw
        
        self.assertEqual(n2.pitch.nameWithOctave, 'G#3')    
        self.assertEqual(n2.quarterLength, 3.0)        
        #self.assertEqual(n2.lyric, 'testing')        

            
    def testBasicB(self):
        from music21 import note, stream, chord

        c1 = chord.Chord(['c2', 'a4', 'e5'], quarterLength=1.25)

        raw = c1.json

        




#------------------------------------------------------------------------------

if __name__ == "__main__":
    music21.mainTest(Test)


#------------------------------------------------------------------------------
# eof






