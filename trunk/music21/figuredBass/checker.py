#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:         checker.py
# Purpose:      music21 class which can parse a stream of parts and check your homework
# Authors:      Jose Cabal-Ugaz
#
# Copyright:    (c) 2011 The music21 Project    
# License:      LGPL
#-------------------------------------------------------------------------------

import itertools
import collections
import copy
import music21
    
from music21 import corpus
from music21 import voiceLeading

from music21.figuredBass import possibility

# Takes in a Stream, highlights notes which violate single harmony rules
def checkSinglePossibilities(music21Stream, functionToApply, color = "#FF0000", debug = False):
    currentMapping = extractHarmonies(music21Stream)
    violations = collections.defaultdict(list)
    for currentKey in sorted(currentMapping.keys()):
        possibA = [noteOrRestToPitch(n) for n in currentMapping[currentKey]]
        for partViolation in functionToApply(possibA):
            startTimeA = currentKey[0]
            if debug == True:
                print str(startTimeA) + ": " + str(partViolation) 
            violations[startTimeA].append(partViolation)

    allParts = [p.flat.notesAndRests for p in music21Stream.getElementsByClass('Part')]
    measureNumbers = []
    for startTime in sorted(violations.keys()):
        for partTuple in violations[startTime]:
            for partNumber in partTuple:
                noteA1 = allParts[partNumber-1].getElementsByOffset(startTime, startTime, mustBeginInSpan = False)[0]
                noteA1.color = color
            if not noteA1.measureNumber in measureNumbers:
                measureNumbers.append(noteA1.measureNumber)
    
    return measureNumbers
  
# Takes in a Stream, highlights notes which violate consecutive harmony rules  
def checkConsecutivePossibilities(music21Stream, functionToApply, color = "#FF0000", debug = False):
    currentMapping = extractHarmonies(music21Stream)
    violations = collections.defaultdict(list)  
    allKeys = sorted(currentMapping.keys())
    previousKey = allKeys[0]
    possibA = [noteOrRestToPitch(n) for n in currentMapping[previousKey]]
    for currentKey in allKeys[1:]:
        possibB = [noteOrRestToPitch(n) for n in currentMapping[currentKey]]
        for partViolation in functionToApply(possibA, possibB):
            startTimeA = previousKey[0]
            startTimeB = currentKey[0]
            if debug == True:
                print str((startTimeA, startTimeB)) + ": " + str(partViolation) 
            violations[(startTimeA, startTimeB)].append(partViolation)
        possibA = possibB
        previousKey = currentKey

    allParts = [p.flat.notesAndRests for p in music21Stream.getElementsByClass('Part')]
    measureNumbers = []
    for k in sorted(violations.keys()):
        (startTimeA, startTimeB) = k
        for partTuple in violations[k]:
            for partNumber in partTuple:
                noteA1 = allParts[partNumber-1].getElementsByOffset(startTimeA, startTimeA, mustBeginInSpan = False)[0]
                noteA2 = allParts[partNumber-1].getElementsByOffset(startTimeB, startTimeB, mustBeginInSpan = False)[0]
                noteA1.color = color
                noteA2.color = color
            if not noteA1.measureNumber in measureNumbers:
                measureNumbers.append(noteA1.measureNumber)

    return measureNumbers

# Creates a complete offset mapping of a Stream Part
def extractHarmonies(music21Stream):
    allParts = music21Stream.getElementsByClass(['Part','TinyNotationStream'])
    if len(allParts) < 2:
        raise Exception()
    currentMapping = createOffsetMapping(allParts[0])
    for music21Part in allParts[1:]:
        correlateHarmonies(currentMapping, music21Part)
    return currentMapping

# Creates an initial offset mapping of a Stream Part
def createOffsetMapping(music21Part):
    partToCorrelate = music21Part.sliceByBeat()
    partToCorrelate = partToCorrelate.flat.notesAndRests
    currentMapping = {}
    for music21Object in partToCorrelate:
        startTime = music21Object.offset
        endTime = startTime + music21Object.quarterLength
        currentMapping[(startTime, endTime)] = [music21Object]
    return currentMapping

# Appends another Stream Part to an existing offset mapping
def correlateHarmonies(currentMapping, music21Part):
    partToCorrelate = music21Part.sliceByBeat()
    partToCorrelate = partToCorrelate.flat.notesAndRests
    for k in sorted(currentMapping.keys()):
        (startTime, endTime) = k
        notesInRange = partToCorrelate.getElementsByOffset(startTime, offsetEnd = endTime,\
                        includeEndBoundary = False, mustFinishInSpan = False, mustBeginInSpan = False)
        if len(notesInRange) == 1:
            currentMapping[k].append(notesInRange[0])
        elif len(notesInRange) > 1:
            allNotesSoFar = currentMapping[k]
            del currentMapping[k]
            for music21Note in notesInRange:
                startTime = music21Note.offset
                endTime = startTime + music21Note.quarterLength
                allNotesCopy = copy.copy(allNotesSoFar)
                allNotesCopy.append(music21Note)
                currentMapping[(startTime, endTime)] = allNotesCopy      

parallelFifthsTable = {}
hiddenFifthsTable = {}
parallelOctavesTable = {}
hiddenOctavesTable = {}

# Takes in two possibilities, returns (partNumberA, partNumberB) which represent
# voices between the two possibilities which form parallel fifths
def parallelFifths(possibA, possibB):
    pairsList = possibility.partPairs(possibA, possibB)
    partViolations = []
    
    for pair1Index in range(len(pairsList)):
        (higherPitchA, higherPitchB) = pairsList[pair1Index]
        for pair2Index in range(pair1Index +  1, len(pairsList)):
            (lowerPitchA, lowerPitchB) = pairsList[pair2Index]
            try:
                if not abs(higherPitchA.ps - lowerPitchA.ps) % 12 == 7:
                    continue
                if not abs(higherPitchB.ps - lowerPitchB.ps) % 12 == 7:
                    continue
            except AttributeError:
                continue
            #Very high probability of ||5, but still not certain.
            pitchQuartet = (lowerPitchA, lowerPitchB, higherPitchA, higherPitchB)
            if parallelFifthsTable.has_key(pitchQuartet):
                hasParallelFifths = parallelFifthsTable[pitchQuartet]
                if hasParallelFifths: 
                    partViolations.append((pair1Index+1, pair2Index+1))
            vlq = voiceLeading.VoiceLeadingQuartet(*pitchQuartet)
            if vlq.parallelFifth():
                partViolations.append((pair1Index+1, pair2Index+1))
                parallelFifthsTable[pitchQuartet] = True
            parallelFifthsTable[pitchQuartet] = False

    return partViolations

# Takes in two possibilities, returns a (partNumberA, partNumberB) in a list, 
# where it corresponds to the first and last voice if they form a hidden octave.
def hiddenFifth(possibA, possibB):
    partViolations = []
    pairsList = possibility.partPairs(possibA, possibB)
    (highestPitchA, highestPitchB) = pairsList[0]
    (lowestPitchA, lowestPitchB) = pairsList[-1]

    try:
        if abs(highestPitchB.ps - lowestPitchB.ps) % 12 == 7:
            #Very high probability of hidden fifth, but still not certain.
            pitchQuartet = (lowestPitchA, lowestPitchB, highestPitchA, highestPitchB)
            if hiddenFifthsTable.has_key(pitchQuartet):
                hasHiddenFifth = hiddenFifthsTable[pitchQuartet]
                if hasHiddenFifth:
                    partViolations.append((1,len(possibB)))
                return partViolations
            vlq = voiceLeading.VoiceLeadingQuartet(*pitchQuartet)
            if vlq.hiddenFifth():
                partViolations.append((1,len(possibB)))
                hiddenFifthsTable[pitchQuartet] = True
            hiddenFifthsTable[pitchQuartet] = False
            return partViolations
    except AttributeError:
        pass
    
    return partViolations

# Takes in two possibilities, returns (partNumberA, partNumberB) which represent
# voices between the two possibilities which form parallel octaves
def parallelOctaves(possibA, possibB):
    iter1 = itertools.combinations([1,2,3,4], 2)
    partViolations = []
    
    
    pairsList = possibility.partPairs(possibA, possibB)
    partViolations = []
    
    for pair1Index in range(len(pairsList)):
        (higherPitchA, higherPitchB) = pairsList[pair1Index]
        for pair2Index in range(pair1Index +  1, len(pairsList)):
            (lowerPitchA, lowerPitchB) = pairsList[pair2Index]
            try:
                if not abs(higherPitchA.ps - lowerPitchA.ps) % 12 == 0:
                    continue
                if not abs(higherPitchB.ps - lowerPitchB.ps) % 12 == 0:
                    continue
            except AttributeError:
                continue
            #Very high probability of ||8, but still not certain.
            pitchQuartet = (lowerPitchA, lowerPitchB, higherPitchA, higherPitchB)
            if parallelOctavesTable.has_key(pitchQuartet):
                hasParallelOctaves = parallelOctavesTable[pitchQuartet]
                if hasParallelOctaves: 
                    partViolations.append((pair1Index+1, pair2Index+1))
            vlq = voiceLeading.VoiceLeadingQuartet(*pitchQuartet)
            if vlq.parallelOctave():
                partViolations.append((pair1Index+1, pair2Index+1))
                parallelOctavesTable[pitchQuartet] = True
            parallelOctavesTable[pitchQuartet] = False

    return partViolations

# Takes in two possibilities, returns a (partNumberA, partNumberB) in a list, 
# where it corresponds to the first and last voice if they form a hidden octave.
def hiddenOctave(possibA, possibB):
    partViolations = []
    pairsList = possibility.partPairs(possibA, possibB)
    (highestPitchA, highestPitchB) = pairsList[0]
    (lowestPitchA, lowestPitchB) = pairsList[-1]

    try:
        if abs(highestPitchB.ps - lowestPitchB.ps) % 12 == 0:
            #Very high probability of hidden fifth, but still not certain.
            pitchQuartet = (lowestPitchA, lowestPitchB, highestPitchA, highestPitchB)
            if hiddenOctavesTable.has_key(pitchQuartet):
                hasHiddenOctave = hiddenOctavesTable[pitchQuartet]
                if hasHiddenOctave:
                    partViolations.append((1,len(possibB)))
                return partViolations
            vlq = voiceLeading.VoiceLeadingQuartet(*pitchQuartet)
            if vlq.hiddenOctave():
                partViolations.append((1,len(possibB)))
                hiddenOctavesTable[pitchQuartet] = True
            hiddenOctavesTable[pitchQuartet] = False
            return partViolations
    except AttributeError:
        pass
    
    return partViolations
  
# Takes in a possibility, returns (partNumberA, partNumberB) which
# represent two voices which form a voice crossing.
def voiceCrossing(possibA):
    partViolations = []
    for part1Index in range(len(possibA)):
        try:
            higherPitch = possibA[part1Index]
            higherPitch.ps
        except AttributeError:
            continue
        for part2Index in range(part1Index + 1, len(possibA)):
            try:
                lowerPitch = possibA[part2Index]
                lowerPitch.ps
            except AttributeError:
                continue
            if higherPitch < lowerPitch:
                partViolations.append((part1Index+1, part2Index+1))
    return partViolations

# Returns a pitch from a note; rests and chords are represented as rests
def noteOrRestToPitch(music21NoteOrRest):
    if music21NoteOrRest.isNote == True:
        return music21NoteOrRest.pitch
    else:
        return "RT"

#------------------------------------------------------------------------------

def playWithIterators():
    from music21 import pitch
    C4 = pitch.Pitch('C4')
    D4 = pitch.Pitch('D4')
    E4 = pitch.Pitch('E4')
    F4 = pitch.Pitch('F4')
    G4 = pitch.Pitch('G4')
    B4 = pitch.Pitch('B4')
    C5 = pitch.Pitch('C5')
    possibA1 = (C5, G4, E4, C4)
    possibB1 = (B4, F4, D4, D4)
    iter1 = itertools.izip(possibA1, possibB1)
    print list(itertools.combinations([1,2,3,4], 1)) # one voice
    print list(itertools.combinations([1,2,3,4], 2)) # two voices
    print list(itertools.combinations([1,2,3,4], 3)) # three voices


    print list(itertools.combinations(iter1, 2))
    print possibility.partPairs(possibA1, possibB1)

def playWithHarmonies():
    from music21.figuredBass import examples
    from music21.figuredBass import rules
    from music21 import converter
    fbLine = examples.exampleD()
    fbRules = rules.Rules()
    fbRules.forbidParallelFifths = False
    fbRules.forbidParallelOctaves = False
    #fbRules.upperPartsMaxSemitoneSeparation = None
    fbRules.partMovementLimits.append((1,4))
    r1 = fbLine.realize(fbRules)
    r1.keyboardStyleOutput = False
    #music21Stream = converter.parse('/Users/Jose/Documents/demo.xml')
    music21Stream = corpus.parseWork('bach/bwv56.5.xml')
    music21Stream.show()
    #music21Stream.show('text')
    for music21Part in music21Stream.getElementsByClass('Part'):
        music21Part.makeNotation(inPlace=True, cautionaryNotImmediateRepeat=False)
    #music21Stream.show('text')
    print checkConsecutivePossibilities(music21Stream, parallelFifths)
    print checkConsecutivePossibilities(music21Stream, parallelOctaves, color = "#0000FF")
    music21Stream.show()
    return
    #hallelujah = corpus.parseWork('handel/hwv56/movement2-21.md').getElementsByClass('Part')
    #music21Stream = hallelujah
    #smusic21Stream = converter.parse('/Users/Jose/Downloads/Selective Defrostingv2.xml')
    music21Stream = converter.parse("corelli/op3no1/1grave")
    #music21Stream = corpus.parseWork('mozart/k421/movement1')
    #music21Stream = corpus.parseWork('bach/bwv144.3.xml')
    #print checkSinglePossibilities(music21Stream, voiceCrossing, color = "#0000FF")
    print checkConsecutivePossibilities(music21Stream, hiddenOctave, debug = True)
    music21Stream.show()

if __name__ == "__main__":
    pass
    playWithIterators()
    #playWithHarmonies()

#------------------------------------------------------------------------------
# eof