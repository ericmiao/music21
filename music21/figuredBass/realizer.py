#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:         realizer.py
# Purpose:      music21 class to define a figured bass line, consisting of notes
#                and figures in a given key.
# Authors:      Jose Cabal-Ugaz
#
# Copyright:    (c) 2011 The music21 Project    
# License:      LGPL
#-------------------------------------------------------------------------------
'''
This module, the heart of fbRealizer, is all about realizing a bass line of (bassNote, notationString)
pairs. All it takes to create well-formed realizations of a bass line is a few lines of music21 code, 
from start to finish. See :class:`~music21.figuredBass.realizer.FiguredBassLine` for more details.

>>> from music21.figuredBass import realizer
>>> from music21 import note
>>> fbLine = realizer.FiguredBassLine()
>>> fbLine.addElement(note.Note('C3'))
>>> fbLine.addElement(note.Note('D3'), '4,3')
>>> fbLine.addElement(note.Note('C3', quarterLength = 2.0))
>>> allSols = fbLine.realize()
>>> allSols.getNumSolutions()
30
>>> #_DOCS_SHOW allSols.generateRandomRealizations(14).show()

    .. image:: images/figuredBass/fbRealizer_intro.*
        :width: 500
        

The same can be accomplished by taking the notes and notations from a :class:`~music21.stream.Stream`.
See :meth:`~music21.figuredBass.realizer.figuredBassFromStream` for more details.


>>> from music21 import tinyNotation
>>> s = tinyNotation.TinyNotationStream("C4 D4_4,3 C2")
>>> fbLine = realizer.figuredBassFromStream(s)
>>> allSols2 = fbLine.realize()
>>> allSols2.getNumSolutions()
30
'''

import collections
import copy
import itertools
import music21
import random
import unittest

from music21 import chord
from music21 import clef
from music21 import environment
from music21 import key
from music21 import meter
from music21 import note
from music21 import pitch
from music21 import stream
from music21.figuredBass import notation
from music21.figuredBass import realizerScale
from music21.figuredBass import rules
from music21.figuredBass import segment

_MOD = 'realizer.py'

def figuredBassFromStream(streamPart):
    '''
    Takes a :class:`~music21.stream.Part` (or another :class:`~music21.stream.Stream` subclass) 
    and returns a :class:`~music21.figuredBass.realizer.FiguredBassLine` object whose bass notes 
    have notations taken from the lyrics in the source stream. This method along with the
    :meth:`~music21.figuredBass.realizer.FiguredBassLine.realize` method provide the easiest 
    way of converting from a notated version of a figured bass (such as in a MusicXML file) to 
    a realized version of the same line.
    
    
    .. note:: This example corresponds to example 1b in "fbREALIZER: AUTOMATIC FIGURED BASS REALIZATION FOR 
         MUSIC INFORMATION RETRIEVAL IN music21," which was submitted for consideration for the 12th International 
         Society for Music Information Retrieval Conference (`ISMIR 2011 <http://ismir2011.ismir.net/>`_).
        
    >>> from music21 import tinyNotation
    >>> from music21.figuredBass import realizer
    >>> s = tinyNotation.TinyNotationStream('C4 D8_6 E8_6 F4 G4_7 c1', '4/4')
    >>> fb = realizer.figuredBassFromStream(s)
    >>> fbRules = rules.Rules()
    >>> fbRules.partMovementLimits = [(1,2),(2,12),(3,12)]
    >>> fbRealization = fb.realize(fbRules)
    >>> fbRealization.getNumSolutions()
    13
    >>> #_DOCS_SHOW fbRealization.generateRandomRealizations(8).show()
    
    .. image:: images/figuredBass/fbRealizer_fbStreamPart.*
        :width: 500
    '''
    sf = streamPart.flat
    sfn = sf.notes
    
    keyList = sf.getElementsByClass(key.Key)
    myKey = None
    if len(keyList) == 0:
        keyList = sf.getElementsByClass(key.KeySignature)
        if len(keyList) == 0:
            myKey = key.Key('C')
        else:
            if keyList[0].pitchAndMode[1] is None:
                mode = 'major'
            else:
                mode = keyList[0].pitchAndMode[1]
            myKey = key.Key(keyList[0].pitchAndMode[0], mode)
    else:
        myKey = keyList[0]

    tsList = sf.getElementsByClass(meter.TimeSignature)
    if len(tsList) == 0:
        ts = meter.TimeSignature('4/4')
    else:
        ts = tsList[0]
    
    fb = FiguredBassLine(myKey, ts)
    
    for n in sfn:
        if len(n.lyrics) > 0:
            annotationString = ", ".join([x.text for x in n.lyrics])
            fb.addElement(n, annotationString)
        else:
            fb.addElement(n)
    
    return fb

def figuredBassFromStreamPart(streamPart):
    '''
    Deprecated. Use :meth:`~music21.figuredBass.realizer.figuredBassFromStream` instead.
    '''
    _environRules = environment.Environment(_MOD)
    _environRules.warn("The method figuredBassFromStreamPart() is deprecated. Use figuredBassFromStream().", DeprecationWarning)
    return figuredBassFromStream(streamPart)
    
def addLyricsToBassNote(bassNote, notationString = None):
    '''
    Takes in a bassNote and a corresponding notationString as arguments. 
    Adds the parsed notationString as lyrics to the bassNote, which is 
    useful when displaying the figured bass in external software.
    
    >>> from music21.figuredBass import realizer
    >>> from music21 import note
    >>> n1 = note.Note('G3')
    >>> realizer.addLyricsToBassNote(n1, "6,4")
    >>> n1.lyrics[0].text
    '6'
    >>> n1.lyrics[1].text
    '4'
    >>> #_DOCS_SHOW n1.show()
    
    .. image:: images/figuredBass/fbRealizer_lyrics.*
        :width: 100
    '''
    bassNote.lyrics = []
    n = notation.Notation(notationString)
    if len(n.figureStrings) == 0:
        return
    maxLength = 0
    for fs in n.figureStrings:
        if len(fs) > maxLength:
            maxLength = len(fs)
    for fs in n.figureStrings:
        spacesInFront = ''
        for space in range(maxLength - len(fs)):
            spacesInFront += ' '
        bassNote.addLyric(spacesInFront + fs, applyRaw = True)


class FiguredBassLine(object):
    '''
    A FiguredBassLine is an interface for realization of a line of (bassNote, notationString) pairs.
    Currently, only 1:1 realization is supported, meaning that every bassNote is realized and the 
    :attr:`~music21.note.GeneralNote.quarterLength` or duration of a realization above a bassNote 
    is identical to that of the bassNote.
    '''
    _DOC_ORDER = ['addElement', 'generateBassLine', 'realize']
    _DOC_ATTR = {'inKey': 'A :class:`~music21.key.Key` which implies a scale value, scale mode, and key signature for a :class:`~music21.figuredBass.realizerScale.FiguredBassScale`.',
                 'inTime': 'A :class:`~music21.meter.TimeSignature` which specifies the time signature of realizations outputted to a :class:`~music21.stream.Score`.'}    
    
    def __init__(self, inKey = key.Key('C'), inTime = meter.TimeSignature('4/4')):
        '''
        >>> from music21.figuredBass import realizer
        >>> from music21 import key
        >>> from music21 import meter
        >>> fbLine = realizer.FiguredBassLine(key.Key('B'), meter.TimeSignature('3/4'))
        >>> fbLine.inKey
        <music21.key.Key of B major>
        >>> fbLine.inTime
        <music21.meter.TimeSignature 3/4>
        '''
        self.inKey = inKey
        self.inTime = inTime
        self._fbScale = realizerScale.FiguredBassScale(inKey.pitchFromDegree(1), inKey.mode)
        self._fbList = []
    
    def addElement(self, bassNote, notationString = None):
        '''
        Use this method to add (bassNote, notationString) pairs to the bass line. Elements
        are realized in the order they are added.
        
        
        >>> from music21.figuredBass import realizer
        >>> from music21 import key
        >>> from music21 import meter
        >>> from music21 import note
        >>> fbLine = realizer.FiguredBassLine(key.Key('B'), meter.TimeSignature('3/4'))
        >>> fbLine.addElement(note.Note('B2'))
        >>> fbLine.addElement(note.Note('C#3'), "6")
        >>> fbLine.addElement(note.Note('D#3'), "6")
        >>> #_DOCS_SHOW fbLine.generateBassLine().show()
        
        .. image:: images/figuredBass/fbRealizer_bassLine.*
            :width: 200
        '''
        self._fbList.append((bassNote, notationString))
        addLyricsToBassNote(bassNote, notationString)
    
    def generateBassLine(self):
        '''
        Generates the bass line as a :class:`~music21.stream.Score`.
        
        >>> from music21.figuredBass import realizer
        >>> from music21 import key
        >>> from music21 import meter
        >>> from music21 import note
        >>> fbLine = realizer.FiguredBassLine(key.Key('B'), meter.TimeSignature('3/4'))
        >>> fbLine.addElement(note.Note('B2'))
        >>> fbLine.addElement(note.Note('C#3'), "6")
        >>> fbLine.addElement(note.Note('D#3'), "6")
        >>> #_DOCS_SHOW fbLine.generateBassLine().show()
        
        .. image:: images/figuredBass/fbRealizer_bassLine.*
            :width: 200
        '''
        bassLine = stream.Part()
        bassLine.append(copy.deepcopy(self.inTime))
        bassLine.append(key.KeySignature(self.inKey.sharps))

        bassLine.append(clef.BassClef())
        for (bassNote, notationString) in self._fbList:
            bassLine.append(bassNote)
            
        return bassLine
    
    def realize(self, fbRules = rules.Rules(), numParts = 4, maxPitch = pitch.Pitch('B5')):
        '''
        Creates a :class:`~music21.figuredBass.segment.Segment` for each (bassNote, notationString) pair
        added using :meth:`~music21.figuredBass.realizer.FiguredBassLine.addElement`. Each Segment is associated
        with the :class:`~music21.figuredBass.rules.Rules` object provided, meaning that rules are
        universally applied across all Segments. The number of parts in a realization
        (including the bass) can be controlled through numParts, and the maximum pitch can
        likewise be controlled through maxPitch. Returns a :class:`~music21.figuredBass.realizer.Realization`.
        
        
        If this methods is called without having provided any (bassNote, notationString) pairs,
        a FiguredBassLineException is raised. If only one pair is provided, the Realization will
        contain :meth:`~music21.figuredBass.segment.Segment.allCorrectConsecutivePossibilities`
        for the one note.
        
        >>> from music21.figuredBass import realizer
        >>> from music21.figuredBass import rules
        >>> from music21 import key
        >>> from music21 import meter
        >>> from music21 import note
        >>> fbLine = realizer.FiguredBassLine(key.Key('B'), meter.TimeSignature('3/4'))
        >>> fbLine.addElement(note.Note('B2'))
        >>> fbLine.addElement(note.Note('C#3'), "6")
        >>> fbLine.addElement(note.Note('D#3'), "6")
        >>> fbRules = rules.Rules()
        >>> r1 = fbLine.realize(fbRules)
        >>> r1.getNumSolutions()
        208
        >>> fbRules.forbidVoiceOverlap = False
        >>> r2 = fbLine.realize(fbRules)
        >>> r2.getNumSolutions()
        7908
        '''
        segmentList = []
        for (bassNote, notationString) in self._fbList:
            correspondingSegment = segment.Segment(bassNote, notationString, self._fbScale, fbRules, numParts, maxPitch)
            segmentList.append(correspondingSegment)

        if len(segmentList) >= 2:
            for segmentIndex in range(len(segmentList) - 1):
                segmentA = segmentList[segmentIndex]
                segmentB = segmentList[segmentIndex + 1]
                correctAB = segmentA.allCorrectConsecutivePossibilities(segmentB)
                segmentA.movements = collections.defaultdict(list)
                listAB = list(correctAB)
                for (possibA, possibB) in listAB:
                    segmentA.movements[possibA].append(possibB)
            self._trimAllMovements(segmentList)
        elif len(segmentList) == 1:
            segmentA = segmentList[0]
            segmentA.correctA = list(segmentA.allCorrectSinglePossibilities())
        elif len(segmentList) == 0:
            raise FiguredBassLineException("No (bassNote, notationString) pairs to realize.")

        return Realization(realizedSegmentList = segmentList, inKey = self.inKey, inTime = self.inTime)

    def generateRandomRealization(self):         
        '''
        Generates a random realization of a figured bass as a :class:`~music21.stream.Score`, 
        with the default rules set **and** a soprano line limited to stepwise motion.
        
        
        .. note:: Deprecated. Use :meth:`~music21.figuredBass.realizer.FiguredBassLine.realize`
            which returns a :class:`~music21.figuredBass.realizer.Realization`. Then, call :meth:`~music21.figuredBass.realizer.Realization.generateRandomRealization`.
        '''
        _environRules = environment.Environment(_MOD)
        _environRules.warn("The method generateRandomRealization() is deprecated. Use realize() instead and call generateRandomRealization() on the result.", DeprecationWarning)
        fbRules = rules.Rules()
        fbRules.partMovementLimits = [(1,2),(2,12),(3,12)]        
        return self.realize(fbRules).generateRandomRealization()

    def showRandomRealization(self):         
        '''
        Displays a random realization of a figured bass as a musicxml in external software, 
        with the default rules set **and** a soprano line limited to stepwise motion.
        
        
        .. note:: Deprecated. Use :meth:`~music21.figuredBass.realizer.FiguredBassLine.realize`
            which returns a :class:`~music21.figuredBass.realizer.Realization`. Then, call :meth:`~music21.figuredBass.realizer.Realization.generateRandomRealization`
            followed by a call to :meth:`~music21.base.Music21Object.show`.
        '''
        _environRules = environment.Environment(_MOD)
        _environRules.warn("The method showRandomRealization() is deprecated. Use realize() instead and call generateRandomRealization().show() on the result.", DeprecationWarning)
        fbRules = rules.Rules()
        fbRules.partMovementLimits = [(1,2),(2,12),(3,12)]
        return self.realize(fbRules).generateRandomRealization().show()
            
    def showAllRealizations(self):
        '''
        Displays all realizations of a figured bass as a musicxml in external software, 
        with the default rules set **and** a soprano line limited to stepwise motion.
        
        
        .. note:: Deprecated. Use :meth:`~music21.figuredBass.realizer.FiguredBassLine.realize`
            which returns a :class:`~music21.figuredBass.realizer.Realization`. Then, call :meth:`~music21.figuredBass.realizer.Realization.generateAllRealizations`
            followed by a call to :meth:`~music21.base.Music21Object.show`.
        

        .. warning:: This method is unoptimized, and may take a prohibitive amount
            of time for a Realization which has more than tens of unique realizations.
        '''
        _environRules = environment.Environment(_MOD)
        _environRules.warn("The method showAllRealizations() is deprecated. Use realize() instead and call generateAllRealizations().show() on the result.", DeprecationWarning)
        fbRules = rules.Rules()
        fbRules.partMovementLimits = [(1,2),(2,12),(3,12)]
        return self.realize(fbRules).generateAllRealizations().show()
    
    def _trimAllMovements(self, segmentList):
        '''
        Each :class:`~music21.figuredBass.segment.Segment` which resolves to another
        defines a list of movements, nextMovements. Keys for nextMovements are correct
        single possibilities of the current Segment. For a given key, a value is a list
        of correct single possibilities in the subsequent Segment representing acceptable
        movements between the two. There may be movements in a string of Segments which
        directly or indirectly lead nowhere. This method is designed to be called on
        a list of Segments **after** movements are found, as happens in 
        :meth:`~music21.figuredBass.realizer.FiguredBassLine.realize`.
        '''
        if len(segmentList) == 1 or len(segmentList) == 2:
            return True
        elif len(segmentList) >= 3:
            segmentList.reverse()
            for segmentIndex in range(1, len(segmentList) - 1):
                movementsAB = segmentList[segmentIndex + 1].movements
                movementsBC = segmentList[segmentIndex].movements
                eliminated = []
                for (possibB, possibCList) in movementsBC.items():
                    if len(possibCList) == 0:
                        del movementsBC[possibB]
                for (possibA, possibBList) in movementsAB.items():
                    movementsAB[possibA] = list(itertools.ifilter(lambda possibB: movementsBC.has_key(possibB), possibBList))

            for (possibA, possibBList) in movementsAB.items():
                if len(possibBList) == 0:
                    del movementsAB[possibA]
                    
            segmentList.reverse()
            return True

#FiguredBass = FiguredBassLine

class Realization(object):
    '''
    Returned by :class:`~music21.figuredBass.realizer.FiguredBassLine` after calling
    :meth:`~music21.figuredBass.realizer.FiguredBassLine.realize`. Allows for the 
    generation of realizations as a :class:`~music21.stream.Score`.
    
    
    See the :mod:`~music21.figuredBass.examples` module for examples on the generation
    of realizations.
    
    
    .. note:: A possibility progression is a valid progression through a string of 
        :class:`~music21.figuredBass.segment.Segment` instances.
        See :mod:`~music21.figuredBass.possibility` for more details on possibilities.
    '''
    _DOC_ORDER = ['getNumSolutions', 'generateRandomRealization', 'generateRandomRealizations', 'generateAllRealizations',
                  'getAllPossibilityProgressions', 'getRandomPossibilityProgression', 'generateRealizationFromPossibilityProgression']
    _DOC_ATTR = {'keyboardStyleOutput': '''True by default. If True, generated realizations are represented in keyboard style, with two staves. If False,
    realizations are represented in chorale style with n staves, where n is the number of parts. SATB if n = 4.'''}
    def __init__(self, **fbLineOutputs):
        # fbLineOutputs always will have three elements, checks are for sphinx documentation only.
        if 'realizedSegmentList' in fbLineOutputs:
            self._segmentList = fbLineOutputs['realizedSegmentList']
        if 'inKey' in fbLineOutputs:
            self._inKey = fbLineOutputs['inKey']
            self._keySig = key.KeySignature(self._inKey.sharps)
        if 'inTime' in fbLineOutputs:
            self._inTime = fbLineOutputs['inTime']
        self.keyboardStyleOutput = True

    def getNumSolutions(self):
        '''
        Returns the number of solutions (unique realizations) to a Realization by calculating
        the total number of paths through a string of :class:`~music21.figuredBass.segment.Segment`
        movements. This is faster and more efficient than compiling each unique realization into a 
        list, adding it to a master list, and then taking the length of the master list.
        
        >>> from music21.figuredBass import examples
        >>> fbLine = examples.exampleB()
        >>> fbRealization = fbLine.realize()
        >>> fbRealization.getNumSolutions()
        422
        >>> fbLine2 = examples.exampleC()
        >>> fbRealization2 = fbLine2.realize()
        >>> fbRealization2.getNumSolutions()
        833
        '''
        if len(self._segmentList) == 1:
            return len(self._segmentList[0].correctA)
        # What if there's only one (bassNote, notationString)?
        self._segmentList.reverse()
        pathList = {}
        for segmentIndex in range(1, len(self._segmentList)):
            segmentA = self._segmentList[segmentIndex]
            newPathList = {}
            if len(pathList.keys()) == 0:
                for possibA in segmentA.movements.keys():
                    newPathList[possibA] = len(segmentA.movements[possibA])
            else:
                for possibA in segmentA.movements.keys():
                    prevValue = 0
                    for possibB in segmentA.movements[possibA]:
                        prevValue += pathList[possibB]
                    newPathList[possibA] = prevValue
            pathList = newPathList

        numSolutions = 0
        for possibA in pathList.keys():
            numSolutions += pathList[possibA]  
        self._segmentList.reverse()
        return numSolutions
    
    def getAllPossibilityProgressions(self):
        '''
        Compiles each unique possibility progression, adding 
        it to a master list. Returns the master list.
        
        
        .. warning:: This method is unoptimized, and may take a prohibitive amount
            of time for a Realization which has more than 200,000 solutions.
        '''
        progressions = []
        if len(self._segmentList) == 1:
            for possibA in self._segmentList[0].correctA:
                progressions.append([possibA])
            return progressions
        
        currMovements = self._segmentList[0].movements
        for possibA in currMovements.keys():
            possibBList = currMovements[possibA]
            for possibB in possibBList:
                progressions.append([possibA, possibB])

        for segmentIndex in range(1, len(self._segmentList)-1):
            currMovements = self._segmentList[segmentIndex].movements
            for progIndex in range(len(progressions)):
                prog = progressions.pop(0)
                possibB = prog[-1]
                for possibC in currMovements[possibB]:
                    newProg = copy.copy(prog)
                    newProg.append(possibC)
                    progressions.append(newProg)
        
        return progressions
    
    def getRandomPossibilityProgression(self):
        '''
        Returns a random unique possibility progression.
        '''
        progression = []
        if len(self._segmentList) == 1:
            possibA = random.sample(self._segmentList[0].correctA, 1)[0]
            progression.append(possibA)
            return progression
        
        currMovements = self._segmentList[0].movements
        prevPossib = random.sample(currMovements.keys(), 1)[0]
        progression.append(prevPossib)
        
        for segmentIndex in range(0, len(self._segmentList)-1):
            currMovements = self._segmentList[segmentIndex].movements
            nextPossib = random.sample(currMovements[prevPossib], 1)[0]
            progression.append(nextPossib)
            prevPossib = nextPossib

        return progression

    def generateRealizationFromPossibilityProgression(self, possibilityProgression):
        '''
        Generates a realization as a :class:`~music21.stream.Score` given a possibility progression.        
        '''
        sol = stream.Score()
        
        bassLine = stream.Part()
        bassLine.append(copy.deepcopy(self._inTime))
        bassLine.append(copy.deepcopy(self._keySig))
        
        if self.keyboardStyleOutput:
            rightHand = stream.Part()
            sol.insert(0, rightHand)
            rightHand.append(copy.deepcopy(self._inTime))
            rightHand.append(copy.deepcopy(self._keySig))
    
            for segmentIndex in range(len(self._segmentList)):
                possibA = possibilityProgression[segmentIndex]
                bassNote = self._segmentList[segmentIndex].bassNote
                bassLine.append(copy.deepcopy(bassNote))  
                rhPitches = possibA[0:-1]                           
                rhChord = chord.Chord(rhPitches)
                rhChord.quarterLength = bassNote.quarterLength
                rightHand.append(rhChord)
            rightHand.insert(0, clef.TrebleClef()) 
        else: # Chorale-style output
            upperParts = []
            for partNumber in range(len(possibilityProgression[0]) - 1):
                fbPart = stream.Part()
                sol.insert(0, fbPart)
                fbPart.append(copy.deepcopy(self._inTime))
                fbPart.append(copy.deepcopy(self._keySig))
                upperParts.append(fbPart)

            for segmentIndex in range(len(self._segmentList)):
                possibA = possibilityProgression[segmentIndex]
                bassNote = self._segmentList[segmentIndex].bassNote
                bassLine.append(copy.deepcopy(bassNote))  

                for partNumber in range(len(possibA) - 1):
                    n1 = note.Note(possibA[partNumber])
                    n1.quarterLength = bassNote.quarterLength
                    upperParts[partNumber].append(n1)
                    
            for upperPart in upperParts:
                upperPart.insert(0, upperPart.bestClef(True)) 
                              
        bassLine.insert(0, clef.BassClef())             
        sol.insert(0, bassLine)
        return sol

    def generateAllRealizations(self):
        '''
        Generates all unique realizations as a :class:`~music21.stream.Score`.
        
        
        .. warning:: This method is unoptimized, and may take a prohibitive amount
            of time for a Realization which has more than 100 solutions.
        '''
        allSols = stream.Score()
        bassLine = stream.Part()
        possibilityProgressions = self.getAllPossibilityProgressions()
        if len(possibilityProgressions) == 0:
            raise FiguredBassLineException("zero realizations")
        if self.keyboardStyleOutput:
            rightHand = stream.Part()
            allSols.insert(0, rightHand)
            
            for possibilityProgression in possibilityProgressions:
                bassLine.append(copy.deepcopy(self._inTime))
                bassLine.append(copy.deepcopy(self._keySig))
                rightHand.append(copy.deepcopy(self._inTime))
                rightHand.append(copy.deepcopy(self._keySig))
                for segmentIndex in range(len(self._segmentList)):
                    possibA = possibilityProgression[segmentIndex]
                    bassNote = self._segmentList[segmentIndex].bassNote
                    bassLine.append(copy.deepcopy(bassNote))  
                    rhPitches = possibA[0:-1]                           
                    rhChord = chord.Chord(rhPitches)
                    rhChord.quarterLength = bassNote.quarterLength
                    rightHand.append(rhChord)
                rightHand.insert(0, clef.TrebleClef())
        else: # Chorale-style output
            upperParts = []
            possibilityProgression = self.getRandomPossibilityProgression()
            for partNumber in range(len(possibilityProgression[0]) - 1):
                fbPart = stream.Part()
                allSols.insert(0, fbPart)
                upperParts.append(fbPart)
                
            for possibilityProgression in possibilityProgressions:
                bassLine.append(copy.deepcopy(self._inTime))
                bassLine.append(copy.deepcopy(self._keySig))
                for upperPart in upperParts:
                    upperPart.append(copy.deepcopy(self._inTime))
                    upperPart.append(copy.deepcopy(self._keySig))

                for segmentIndex in range(len(self._segmentList)):
                    possibA = possibilityProgression[segmentIndex]
                    bassNote = self._segmentList[segmentIndex].bassNote
                    bassLine.append(copy.deepcopy(bassNote))
                    for partNumber in range(len(possibA) - 1):
                        n1 = note.Note(possibA[partNumber])
                        n1.quarterLength = bassNote.quarterLength
                        upperParts[partNumber].append(n1)
                        
                for upperPart in upperParts:
                    upperPart.insert(0, upperPart.bestClef(True)) 
  
        bassLine.insert(0, clef.BassClef())
        allSols.insert(0, bassLine)
        return allSols        

    def generateRandomRealization(self):
        '''
        Generates a random unique realization as a :class:`~music21.stream.Score`.
        '''
        return self.generateRandomRealizations(1)

    def generateRandomRealizations(self, amountToGenerate = 20):
        '''
        Generates *amountToGenerate* unique realizations as a :class:`~music21.stream.Score`.
        

        .. warning:: This method is unoptimized, and may take a prohibitive amount
            of time if amountToGenerate is more than 100.
        '''
        if amountToGenerate > self.getNumSolutions():
            return self.generateAllRealizations()
        allSols = stream.Score()
        bassLine = stream.Part()
        
        if self.keyboardStyleOutput:
            rightHand = stream.Part()
            allSols.insert(0, rightHand)
            
            for solutionCounter in range(amountToGenerate):
                bassLine.append(copy.deepcopy(self._inTime))
                bassLine.append(copy.deepcopy(self._keySig))
                rightHand.append(copy.deepcopy(self._inTime))
                rightHand.append(copy.deepcopy(self._keySig))
                possibilityProgression = self.getRandomPossibilityProgression()
                for segmentIndex in range(len(self._segmentList)):
                    possibA = possibilityProgression[segmentIndex]
                    bassNote = self._segmentList[segmentIndex].bassNote
                    bassLine.append(copy.deepcopy(bassNote))  
                    rhPitches = possibA[0:-1]                           
                    rhChord = chord.Chord(rhPitches)
                    rhChord.quarterLength = bassNote.quarterLength
                    rightHand.append(rhChord)
                rightHand.insert(0, clef.TrebleClef()) 
        else: # Chorale-style output
            upperParts = []
            possibilityProgression = self.getRandomPossibilityProgression()
            for partNumber in range(len(possibilityProgression[0]) - 1):
                fbPart = stream.Part()
                allSols.insert(0, fbPart)
                upperParts.append(fbPart)
                
            for solutionCounter in range(amountToGenerate):
                bassLine.append(copy.deepcopy(self._inTime))
                bassLine.append(copy.deepcopy(self._keySig))
                for upperPart in upperParts:
                    upperPart.append(copy.deepcopy(self._inTime))
                    upperPart.append(copy.deepcopy(self._keySig))

                possibilityProgression = self.getRandomPossibilityProgression()
                for segmentIndex in range(len(self._segmentList)):
                    possibA = possibilityProgression[segmentIndex]
                    bassNote = self._segmentList[segmentIndex].bassNote
                    bassLine.append(copy.deepcopy(bassNote))
                    for partNumber in range(len(possibA) - 1):
                        n1 = note.Note(possibA[partNumber])
                        n1.quarterLength = bassNote.quarterLength
                        upperParts[partNumber].append(n1)
                        
                for upperPart in upperParts:
                    upperPart.insert(0, upperPart.bestClef(True)) 
  
        bassLine.insert(0, clef.BassClef())
        allSols.insert(0, bassLine)
        return allSols        


_DOC_ORDER = [figuredBassFromStream, figuredBassFromStreamPart, addLyricsToBassNote, FiguredBassLine, Realization]

class FiguredBassLineException(music21.Music21Exception):
    pass
    
#-------------------------------------------------------------------------------
class Test(unittest.TestCase):

    def runTest(self):
        pass

if __name__ == "__main__":
    music21.mainTest(Test)

#------------------------------------------------------------------------------
# eof