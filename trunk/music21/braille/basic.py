# -*- coding: UTF-8 -*-
#-------------------------------------------------------------------------------
# Name:         basic.py
# Purpose:      music21 class which allows transcription of music21Object instances to braille.
# Authors:      Jose Cabal-Ugaz
#
# Copyright:    (c) 2011 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------

import music21
import unittest

from music21 import articulations
from music21 import clef
from music21 import interval
from music21 import note

from music21.braille import lookup

# pitches with duration
pitchNameToNotes = lookup.pitchNameToNotes

# other print symbols
accidentals = lookup.accidentals
alphabet = lookup.alphabet
ascii_chars = lookup.ascii_chars
barlines = lookup.barlines
beatUnits = lookup.beatUnits
beforeNoteExpr = lookup.beforeNoteExpr
clefSigns = lookup.clefSigns
fingerMarks = lookup.fingerMarks
intervals = lookup.intervals
keySignatures = lookup.keySignatures
naturals = lookup.naturals
numbers = lookup.numbers
octaves = lookup.octaves
rests = lookup.rests
symbols = lookup.symbols
textExpressions = lookup.textExpressions

#-------------------------------------------------------------------------------
# music21Object to braille unicode methods

def barlineToBraille(music21Barline):
    '''
    Takes in a :class:`~music21.bar.Barline` and returns its representation
    as a braille string in UTF-8 unicode.
    
    
    .. note:: Only double barlines and final barlines can be transcribed.
        
    >>> from music21.braille import basic
    >>> from music21 import bar
    >>> doubleBarline = bar.Barline('double')
    >>> print basic.barlineToBraille(doubleBarline)
    ⠣⠅⠄
    >>> finalBarline = bar.Barline('final')
    >>> print basic.barlineToBraille(finalBarline)
    ⠣⠅
    '''
    try:
        return barlines[music21Barline.style]
    except KeyError:
        return BrailleBasicException("Barline type cannot be shown in braille.")

def chordToBraille(music21Chord, descending = True, showOctave = True):
    '''
    Takes in a :class:`~music21.chord.Chord` and returns its representation
    as a braille string in UTF-8 unicode.

    
    In braille, only one pitch of a chord is brailled, with the rest represented
    as numeric intervals from that one pitch. If descending is True, the highest
    (sounding) pitch is brailled, and intervals are labeled in descending order;
    if descending is False, the lowest (sounding) pitch is brailled, and the
    intervals are labeled in ascending order. Convention dictates that chords
    found in the treble clef are brailled descending, and those found in the bass 
    clef are brailled ascending.
    

    If showOctave is True, the octave of the brailled pitch is shown. Other
    octave marks are shown in context relative to the brailled pitch.
    
    >>> from music21.braille import basic
    >>> from music21 import chord
    >>> gMajorTriadA = chord.Chord(['G4','B4','D5','G5'], quarterLength = 4.0)
    >>> print basic.chordToBraille(gMajorTriadA, descending = True)
    ⠨⠷⠼⠴⠤
    >>> gMajorTriadB = chord.Chord(['G2','B2','D3','G3'], quarterLength = 4.0)
    >>> print basic.chordToBraille(gMajorTriadB, descending = False)
    ⠘⠷⠬⠔⠤
    >>> gMajorTriadRightHand = chord.Chord(['D4','B4','G5'], quarterLength = 4.0)  
    >>> print basic.chordToBraille(gMajorTriadRightHand, descending = True)
    ⠨⠷⠴⠼
    >>> gMajorTriadLeftHand = chord.Chord(['G2','D3','B3'], quarterLength = 4.0)
    >>> print basic.chordToBraille(gMajorTriadLeftHand, descending = False)
    ⠘⠷⠔⠬
    >>> cMajorTriadRightHand = chord.Chord(['C4','E5'], quarterLength = 4.0)
    >>> print basic.chordToBraille(cMajorTriadRightHand, descending = True)
    ⠨⠯⠐⠬
    >>> cMajorTriadLeftHand = chord.Chord(['C2','E3'], quarterLength = 4.0)
    >>> print basic.chordToBraille(cMajorTriadLeftHand, descending = False)
    ⠘⠽⠸⠬
    >>> cMajorSeventhRightHand = chord.Chord(['C6','E5','B4'], quarterLength = 4.0)
    >>> print basic.chordToBraille(cMajorSeventhRightHand, descending = True)
    ⠰⠽⠴⠌
    >>> cMajorSeventhLeftHand = chord.Chord(['G2','E3','E4'], quarterLength = 4.0)
    >>> print basic.chordToBraille(cMajorSeventhLeftHand, descending = False)
    ⠘⠷⠴⠐⠴
    '''
    allPitches = sorted(music21Chord.pitches)
    if descending:
        allPitches.reverse()
    
    chordTrans = []
    basePitch = allPitches[0]
    initNote = note.Note(basePitch, quarterLength = music21Chord.quarterLength)
    chordTrans.append(noteToBraille(music21Note=initNote,showOctave=showOctave))
    
    for currentPitchIndex in range(1, len(allPitches)):
        currentPitch = allPitches[currentPitchIndex]        
        intervalDistance = interval.notesToInterval(basePitch, currentPitch).generic.undirected
        if intervalDistance > 8:
            intervalDistance = intervalDistance % 8 + 1
            if currentPitchIndex == 1:
                chordTrans.append(octaves[currentPitch.octave])
            else:
                previousPitch = allPitches[currentPitchIndex - 1]
                relativeIntervalDist = interval.notesToInterval(previousPitch, currentPitch).generic.undirected
                if relativeIntervalDist >= 8:
                    chordTrans.append(octaves[currentPitch.octave])
        chordTrans.append(intervals[intervalDistance])
            
    return u''.join(chordTrans)

def clefToBraille(music21Clef):
    '''
    Takes in a :class:`~music21.clef.Clef` and returns its representation
    as a braille string in UTF-8 unicode.
    
    
    .. note:: Only :class:`~music21.clef.TrebleClef`, :class:`~music21.clef.BassClef`,
    :class:`~music21.clef.AltoClef`, and :class:`~music21.clef.TenorClef` can be transcribed.
    
    >>> from music21.braille import basic
    >>> from music21 import clef
    >>> trebleClef = clef.TrebleClef()
    >>> print basic.clefToBraille(trebleClef)
    ⠜⠌⠇
    >>> bassClef = clef.BassClef()
    >>> print basic.clefToBraille(bassClef)
    ⠜⠼⠇
    >>> altoClef = clef.AltoClef()
    >>> print basic.clefToBraille(altoClef)
    ⠜⠬⠇
    >>> tenorClef = clef.TenorClef()
    >>> print basic.clefToBraille(tenorClef)
    ⠜⠬⠐⠇
    '''
    if isinstance(music21Clef, clef.TrebleClef):
        return clefSigns['treble']
    elif isinstance(music21Clef, clef.BassClef):
        return clefSigns['bass']
    elif isinstance(music21Clef, clef.AltoClef):
        return clefSigns['alto']
    elif isinstance(music21Clef, clef.TenorClef):
        return clefSigns['tenor']
    else:
        raise BrailleBasicException("Clef type cannot be shown in braille.")

def dynamicToBraille(music21Dynamic, precedeByWordSign = True):
    '''
    Takes in a :class:`~music21.dynamics.Dynamic` and returns its 
    :attr:`~music21.dynamics.Dynamic.value` as a braille string in
    UTF-8 unicode.

    
    If precedeByWordSign is True, the value is preceded by a word
    sign (⠜).
    
    
    >>> from music21.braille import basic
    >>> from music21 import dynamics
    >>> print basic.dynamicToBraille(dynamics.Dynamic('f'))
    ⠜⠋
    >>> print basic.dynamicToBraille(dynamics.Dynamic('pp'))
    ⠜⠏⠏
    '''
    try:
        dynamicTrans = []
        if precedeByWordSign:
            dynamicTrans.append(symbols['word'])
        dynamicTrans.append(wordToBraille(music21Dynamic.value, isTextExpression = True))
        return u"".join(dynamicTrans)
    except KeyError:
        raise BrailleBasicException("Dynamic type cannot be shown in braille.")

def instrumentToBraille(music21Instrument):
    '''
    Takes in a :class:`~music21.instrument.Instrument` and returns its "best name"
    as a braille string in UTF-8 unicode.
    
    
    >>> from music21.braille import basic
    >>> from music21 import instrument
    >>> print basic.instrumentToBraille(instrument.Bassoon())
    ⠠⠃⠁⠎⠎⠕⠕⠝
    >>> print basic.instrumentToBraille(instrument.BassClarinet())
    ⠠⠃⠁⠎⠎⠀⠉⠇⠁⠗⠊⠝⠑⠞
    '''
    allWords = music21Instrument.bestName().split()
    trans = []
    for word in allWords:
        trans.append(wordToBraille(sampleWord = word))
        trans.append(symbols['space'])
    return u''.join(trans[0:-1])

def keySigToBraille(music21KeySignature, outgoingKeySig = None):
    '''
    Takes in a :class:`~music21.key.KeySignature` and returns its representation 
    in braille as a string in UTF-8 unicode.
    
    >>> from music21.braille import basic
    >>> from music21 import key
    >>> print basic.keySigToBraille(key.KeySignature(4))
    ⠼⠙⠩
       
    
    If given an old key signature, then its cancellation will be applied before
    and in relation to the new key signature.
     

    >>> print basic.keySigToBraille(key.KeySignature(0), outgoingKeySig = key.KeySignature(-3))
    ⠡⠡⠡
    '''
    if music21KeySignature == None:
        raise BrailleBasicException("No key signature provided!")
    ks_braille = keySignatures[music21KeySignature.sharps]
    if outgoingKeySig == None:
        return ks_braille

    trans = []
    if music21KeySignature.sharps == 0 or outgoingKeySig.sharps == 0 or \
        not (outgoingKeySig.sharps / abs(outgoingKeySig.sharps) == music21KeySignature.sharps / abs(music21KeySignature.sharps)):
        trans.append(naturals[abs(outgoingKeySig.sharps)])
    elif not (abs(outgoingKeySig.sharps) < abs(music21KeySignature.sharps)):
        trans.append(naturals[abs(outgoingKeySig.sharps - music21KeySignature.sharps)])

    trans.append(ks_braille)
    return u''.join(trans)

def metronomeMarkToBraille(music21MetronomeMark):
    '''
    Takes in a :class:`~music21.tempo.MetronomeMark` and returns it as a braille string in UTF-8 unicode.
    The format is (note C with duration of metronome's referent)(metronome symbol)(number/bpm).
    
    >>> from music21.braille import basic
    >>> from music21 import tempo
    >>> print basic.metronomeMarkToBraille(tempo.MetronomeMark(number = 80, referent = note.HalfNote())) 
    ⠝⠶⠼⠓⠚
    >>> print basic.metronomeMarkToBraille(tempo.MetronomeMark(number = 135, referent = note.Note(quarterLength = 0.5)))
    ⠙⠶⠼⠁⠉⠑
    '''
    if music21MetronomeMark == None:
        raise BrailleBasicException("No metronome mark provided!")
    metroTrans = []
    metroTrans.append(noteToBraille(note.Note('C4', quarterLength = music21MetronomeMark.referent.quarterLength), showOctave = False))
    metroTrans.append(symbols['metronome'])
    metroTrans.append(numberToBraille(music21MetronomeMark.number))
    
    return ''.join(metroTrans)

def noteToBraille(music21Note, showOctave = True, upperFirstInFingering = True):
    '''
    Given a :class:`~music21.note.Note`, returns the appropriate braille 
    characters as a string in UTF-8 unicode.
    
    
    The format for note display in braille is the accidental (if necessary)
    + octave (if necessary) + pitch name with length.
    
    
    If the note has an :class:`~music21.pitch.Accidental`, the accidental is always 
    displayed unless its :attr:`~music21.pitch.Accidental.displayStatus` is set to 
    False. The octave of the note is only displayed if showOctave is set to True.
    
    
    >>> from music21.braille import basic
    >>> from music21 import note
    >>> C4 = note.Note('C4')
    >>> print basic.noteToBraille(C4)
    ⠐⠹
    >>> C4.quarterLength = 2.0
    >>> print basic.noteToBraille(C4)
    ⠐⠝
    >>> Ds4 = note.Note('D#4')
    >>> print basic.noteToBraille(Ds4)
    ⠩⠐⠱
    >>> print basic.noteToBraille(Ds4, showOctave = False)
    ⠩⠱
    >>> Ds4.pitch.setAccidentalDisplay(False)
    >>> print basic.noteToBraille(Ds4)
    ⠐⠱
    >>> A2 = note.Note('A2')
    >>> A2.quarterLength = 3.0
    >>> print basic.noteToBraille(A2)
    ⠘⠎⠄
    '''
    noteTrans = []
    beginLongBracketSlur = False
    endLongBracketSlur = False
    beginLongDoubleSlur = False
    endLongDoubleSlur = False
    shortSlur = False
    beamStart = False
    beamContinue = False
    
    try:
        beginLongBracketSlur = music21Note.beginLongBracketSlur
    except AttributeError:
        pass
    try:
        endLongBracketSlur = music21Note.endLongBracketSlur
    except AttributeError:
        pass
    try:
        beginLongDoubleSlur = music21Note.beginLongDoubleSlur
    except AttributeError:
        pass
    try:
        endLongDoubleSlur = music21Note.endLongDoubleSlur
    except AttributeError:
        pass

    try:
        shortSlur = music21Note.shortSlur
    except AttributeError:
        pass
    try:
        beamStart = music21Note.beamStart
    except AttributeError:
        pass
    try:
        beamContinue = music21Note.beamContinue
    except AttributeError:
        pass
    
    # opening double slur (before second note, after first note)
    # opening bracket slur
    # closing bracket slur (if also beginning of next long slur)
    # --------------------
    if beginLongBracketSlur:
        noteTrans.append(symbols['opening_bracket_slur'])
    elif beginLongDoubleSlur:
        noteTrans.append(symbols['opening_double_slur'])
    if endLongBracketSlur and beginLongBracketSlur:
        noteTrans.append(symbols['closing_bracket_slur'])

    if beamStart:
        allTuplets = music21Note.duration.tuplets
        if len(allTuplets) > 0:
            if allTuplets[0].fullName == 'Triplet':
                noteTrans.append(symbols['triplet'])

    # signs of expression or execution that precede a note
    # articulations
    # -------------
    if not len(music21Note.articulations) == 0:
        # "When a staccato or staccatissimo is shown with any of the other [before note expressions]
        # it is brailled first.
        # This is buggy, but since I can't handle after note expressions, let's fly with this for now.
        if articulations.Staccato() in music21Note.articulations:
            music21Note.articulations.remove(articulations.Staccato())
            noteTrans.append(beforeNoteExpr['staccato'])
            try:
                music21Note.articulations.remove(articulations.Staccato())
                noteTrans.append(beforeNoteExpr['staccato'])
            except ValueError:
                pass
        if articulations.Staccatissimo() in music21Note.articulations:
            music21Note.articulations.remove(articulations.Staccatissimo())
            noteTrans.append(beforeNoteExpr['staccatissimo'])
            try:
                music21Note.articulations.remove(articulations.Staccatissimo())
                noteTrans.append(beforeNoteExpr['staccatissimo'])
            except ValueError:
                pass
        music21Note.articulations.sort()
        # "When an accent is shown with a tenuto, the accent is brailled first."
        if articulations.Accent() in music21Note.articulations and articulations.Tenuto() in music21Note.articulations:
            music21Note.articulations.remove(articulations.Accent())
            noteTrans.append(beforeNoteExpr['accent'])
            try:
                music21Note.articulations.remove(articulations.Accent())
                noteTrans.append(beforeNoteExpr['accent'])
            except ValueError:
                pass
        for a in music21Note.articulations:
            try:
                noteTrans.append(beforeNoteExpr[a._mxName])
            except KeyError:
                pass
        
    # accidental
    # ----------
    if not(music21Note.accidental == None):
        if not(music21Note.accidental.displayStatus == False):
            try:
                noteTrans.append(accidentals[music21Note.accidental.name])
            except KeyError:
                raise BrailleBasicException("Accidental type cannot be translated to braille.")  
    
    # octave mark
    # -----------
    if showOctave:
        noteTrans.append(octaves[music21Note.octave])

    notesInStep = pitchNameToNotes[music21Note.step]  
    try:
        # note name with duration
        # -----------------------
        if beamContinue:
            nameWithDuration = notesInStep['eighth']
        else:
            nameWithDuration = notesInStep[music21Note.duration.type]
        noteTrans.append(nameWithDuration)
        # dot(s)
        # ------
        for dot in range(music21Note.duration.dots):
            noteTrans.append(symbols['dot'])
        # finger mark
        # -----------
        try:
            noteTrans.append(transcribeNoteFingering(music21Note.fingering, upperFirstInFingering = upperFirstInFingering))
        except AttributeError:
            pass
        # single slur
        # closing double slur (after second to last note, before last note)
        # opening double slur
        # closing bracket slur (unless note also has beginning long slur)
        # ----------------------------------
        if shortSlur:
            noteTrans.append(symbols['opening_single_slur'])
        if not(endLongBracketSlur and beginLongBracketSlur):
            if endLongDoubleSlur:
                noteTrans.append(symbols['closing_double_slur'])
            elif endLongBracketSlur:
                noteTrans.append(symbols['closing_bracket_slur'])
        # tie
        # ---
        if not music21Note.tie == None and not music21Note.tie.type == 'stop':
            noteTrans.append(symbols['tie'])
        return ''.join(noteTrans)
    except KeyError:
        raise BrailleBasicException("Note duration '" + music21Note.duration.type + "' cannot be translated to braille.")

def restToBraille(music21Rest):
    '''
    Given a :class:`~music21.note.Rest`, returns the appropriate braille 
    characters as a string in UTF-8 unicode.
    
    
    Currently, only supports single rests with or without dots.
    Complex rests are not supported.
    
    >>> from music21.braille import basic
    >>> from music21 import note
    >>> dottedQuarter = note.Rest(quarterLength = 1.5)
    >>> print basic.restToBraille(dottedQuarter)
    ⠧⠄
    >>> whole = note.Rest(quarterLength = 4.0)
    >>> print basic.restToBraille(whole)
    ⠍
    >>> quarterPlusSixteenth = note.Rest(quarterLength = 1.25)
    >>> print basic.restToBraille(quarterPlusSixteenth)
    Traceback (most recent call last):
    BrailleBasicException: Rest duration cannot be translated to braille.
    '''
    try:
        restTrans = []
        simpleRest = rests[music21Rest.duration.type]
        restTrans.append(simpleRest)
        for dot in range(music21Rest.duration.dots):
            restTrans.append(symbols['dot'])
        return ''.join(restTrans)
    except KeyError:
        raise BrailleBasicException("Rest duration cannot be translated to braille.")

def tempoTextToBraille(music21TempoText):
    '''
    Takes in a :class:`~music21.tempo.TempoText` and returns its representation in braille 
    as a string in UTF-8 unicode. The tempo text is returned uncentered, and is split around
    the comma, each split returned on a separate line. The literary period required at the end
    of every tempo text expression in braille is also included.
    
    
    >>> from music21.braille import basic
    >>> from music21 import tempo
    >>> print basic.tempoTextToBraille(tempo.TempoText("Lento assai, cantante e tranquillo"))
    ⠠⠇⠑⠝⠞⠕⠀⠁⠎⠎⠁⠊⠂
    ⠉⠁⠝⠞⠁⠝⠞⠑⠀⠑⠀⠞⠗⠁⠝⠟⠥⠊⠇⠇⠕⠲
    >>> print basic.tempoTextToBraille(tempo.TempoText("Andante molto grazioso"))
    ⠠⠁⠝⠙⠁⠝⠞⠑⠀⠍⠕⠇⠞⠕⠀⠛⠗⠁⠵⠊⠕⠎⠕⠲
    '''
    if music21TempoText == None:
        raise BrailleBasicException("No tempo text provided!")
        
    allPhrases = music21TempoText.text.split(",")
    braillePhrases = []
    for samplePhrase in allPhrases:
        allWords = samplePhrase.split()
        phraseTrans = []
        for sampleWord in allWords:
            brailleWord = wordToBraille(sampleWord)
            if not (len(phraseTrans) + len(brailleWord) + 1 > 34):
                phraseTrans.append(brailleWord)
                phraseTrans.append(symbols['space'])
            else:
                phraseTrans.append(u"\n")
                phraseTrans.append(brailleWord)
                phraseTrans.append(symbols['space'])
        braillePhrases.append(u"".join(phraseTrans[0:-1]))
    
    brailleText = []
    for braillePhrase in braillePhrases:
        brailleText.append(braillePhrase)
        brailleText.append(alphabet[","])
        brailleText.append(u"\n")
        
    brailleText = brailleText[0:-2]
    brailleText.append(alphabet["."]) # literary period
    return u"".join(brailleText)

def textExpressionToBraille(music21TextExpression, precedeByWordSign = True):    
    '''
    
    
    music21TextExpression = expressions.TextExpression('dim. e rall.')
    '''
    try:
        return textExpressions[music21TextExpression.content]
    except KeyError:
        allExpr = music21TextExpression.content.split()
        textExpressionTrans = []
        if precedeByWordSign:
            textExpressionTrans.append(symbols['word'])
        if len(allExpr) == 1:
            textExpressionTrans.append(wordToBraille(allExpr[0], isTextExpression = True))
        else:
            for expr in allExpr[0:-1]:
                textExpressionTrans.append(wordToBraille(expr, isTextExpression = True))
                textExpressionTrans.append(symbols['space'])
            textExpressionTrans.append(wordToBraille(allExpr[-1], isTextExpression = True))
            textExpressionTrans.append(symbols['word'])
        return u''.join(textExpressionTrans)

def timeSigToBraille(music21TimeSignature):
    '''
    Takes in a :class:`~music21.meter.TimeSignature` and returns its
    representation in braille as a string in UTF-8 unicode.
    

    >>> from music21.braille import basic
    >>> from music21 import meter
    >>> print basic.timeSigToBraille(meter.TimeSignature('4/4'))
    ⠼⠙⠲
    >>> print basic.timeSigToBraille(meter.TimeSignature('3/4'))
    ⠼⠉⠲
    >>> print basic.timeSigToBraille(meter.TimeSignature('12/8'))
    ⠼⠁⠃⠦
    >>> print basic.timeSigToBraille(meter.TimeSignature('c'))
    ⠨⠉
    '''
    if music21TimeSignature == None:
        raise BrailleBasicException("No time signature provided!")
    if len(music21TimeSignature.symbol) != 0:
        try:
            return symbols[music21TimeSignature.symbol]
        except KeyError:
            pass

    timeSigTrans = []
    timeSigTrans.append(numberToBraille(music21TimeSignature.numerator))    
    timeSigTrans.append(beatUnits[music21TimeSignature.denominator])
    return u''.join(timeSigTrans)

#-------------------------------------------------------------------------------
# Helper methods

def showOctaveWithNote(previousNote, currentNote):
    '''
    Determines whether a currentNote carries an octave designation in relation to a previousNote.
    
    
    Rules:
    
    * If currentNote is found within a second or third 
      of previousNote, currentNote does not
      carry an octave designation.
    
    * If currentNote is found a sixth or 
      more away from previousNote, currentNote does carry 
      an octave designation.
    
    * If currentNote is found within a fourth or fifth 
      of previousNote, currentNote carries
      an octave designation if and only if currentNote and 
      previousNote are not found in the
      same octave.
    
    
    Of course, these rules cease to apply in quite a few cases, which are not directly reflected
    in the results of this method:
    
        
    1) If a braille measure goes to a new line, the first note in the measure carries an 
       octave designation regardless of what the previous note was. 
    
    
    2) If a braille measure contains a new key or time signature, the first note carries
       an octave designation regardless of what the previous note was.
    
    
    3) If a new key or time signature occurs in the middle of a measure, or if a double bar
       line is encountered, both of which would necessitate a music hyphen, the next note after
       those cases needs an octave marking. 
    
    
    If any special case happens, previousNote can be set to None and the method will return
    True.
    
    
    >>> from music21.braille import basic
    >>> from music21 import note
    >>> basic.showOctaveWithNote(note.Note('C4'), note.Note('E4'))
    False
    >>> basic.showOctaveWithNote(note.Note('C4'), note.Note('F4'))
    False
    >>> basic.showOctaveWithNote(note.Note('C4'), note.Note('F3'))
    True
    >>> basic.showOctaveWithNote(note.Note('C4'), note.Note('A4'))
    True
    '''
    if previousNote == None:
        return True
    i = interval.notesToInterval(previousNote, currentNote)
    isSixthOrGreater = i.generic.undirected >= 6
    isFourthOrFifth = i.generic.undirected == 4 or i.generic.undirected == 5
    sameOctaveAsPrevious = previousNote.octave == currentNote.octave
    doShowOctave = False
    if isSixthOrGreater or (isFourthOrFifth and not sameOctaveAsPrevious):
        doShowOctave = True
        
    return doShowOctave

def transcribeHeading(music21KeySignature = None, music21TimeSignature = None, music21TempoText = None, music21MetronomeMark = None, maxLineLength = 40):
    '''
    Takes in a :class:`~music21.key.KeySignature`, :class:`~music21.meter.TimeSignature`, :class:`~music21.tempo.TempoText`, and
    :class:`~music21.tempo.MetronomeMark` and returns its representation in braille as a string in UTF-8 unicode. The contents
    are always centerd on a line, whose width is 40 by default.
    
    
    In most cases, the format is (tempo text)(space)(metronome mark)(space)(key/time signature), centered, although all of
    these need not be included. If all the contents do not fit on one line with at least 3 blank characters on each side, then
    the tempo text goes on the first line (and additional lines if necessary), and the metronome mark + key and time signature
    goes on the last line. 
    
    If the resulting heading is of length zero, a BrailleBasicException is raised.
    
    >>> from music21.braille import basic
    >>> from music21 import key
    >>> from music21 import meter
    >>> from music21 import note
    >>> from music21 import tempo
    >>> print basic.transcribeHeading(key.KeySignature(5), meter.TimeSignature('3/8'), tempo.TempoText("Allegretto"),\
    tempo.MetronomeMark(number = 135, referent = note.EighthNote()))    
    ⠀⠀⠀⠀⠀⠀⠀⠠⠁⠇⠇⠑⠛⠗⠑⠞⠞⠕⠲⠀⠙⠶⠼⠁⠉⠑⠀⠼⠑⠩⠼⠉⠦⠀⠀⠀⠀⠀⠀⠀
    >>> print basic.transcribeHeading(key.KeySignature(-2), meter.TimeSignature('common'),\
    tempo.TempoText("Lento assai, cantante e tranquillo"), None)
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⠇⠑⠝⠞⠕⠀⠁⠎⠎⠁⠊⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠁⠝⠞⠁⠝⠞⠑⠀⠑⠀⠞⠗⠁⠝⠟⠥⠊⠇⠇⠕⠲⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠣⠣⠨⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    '''
    if music21KeySignature is None and music21TimeSignature is None and music21TempoText is None and music21MetronomeMark is None:
        raise BrailleBasicException("No heading can be made.")
    # Tempo Text
    tempoTextTrans = None
    if not (music21TempoText is None):
        tempoTextTrans = tempoTextToBraille(music21TempoText)
        
    if music21KeySignature is None and music21TimeSignature is None and music21MetronomeMark is None:
        tempoTextLines = tempoTextTrans.splitlines()
        headingTrans = []
        for ttline in tempoTextLines:
            headingTrans.append(ttline)
        if len(tempoTextTrans) <= (maxLineLength - 6):
            headingTrans = u"".join(headingTrans)
            return headingTrans.center(maxLineLength, symbols['space'])
        else:
            for hlineindex in range(len(headingTrans)):
                headingTrans[hlineindex] = headingTrans[hlineindex].center(maxLineLength, symbols['space'])
            return u"\n".join(headingTrans)
        
    otherTrans = []
    # Metronome Mark
    if not (music21MetronomeMark is None):
        metronomeMarkTrans = metronomeMarkToBraille(music21MetronomeMark)
        otherTrans.append(metronomeMarkTrans)
    # Key Signature and Time Signature
    try:
        keyAndTimeSig = transcribeSignatures(music21KeySignature, music21TimeSignature)
        if not (music21MetronomeMark is None):
            otherTrans.append(symbols['space'])
        otherTrans.append(keyAndTimeSig)
    except BrailleBasicException:
        if music21MetronomeMark is None and music21TempoText is None:
            raise BrailleBasicException("No heading can be made.")
    otherTrans = u"".join(otherTrans)
    
    if tempoTextTrans is None:
        return otherTrans.center(maxLineLength, symbols['space'])
    else:
        tempoTextLines = tempoTextTrans.splitlines()
        headingTrans = []
        for ttline in tempoTextLines:
            headingTrans.append(ttline)
        headingTrans.append(otherTrans)
        if len(tempoTextTrans) + len(otherTrans) + 1 <= (maxLineLength - 6):
            headingTrans = symbols['space'].join(headingTrans)
            return headingTrans.center(maxLineLength, symbols['space'])
        else:
            for hlineindex in range(len(headingTrans)):
                headingTrans[hlineindex] = headingTrans[hlineindex].center(maxLineLength, symbols['space'])
            return u"\n".join(headingTrans)

def transcribeNoteFingering(sampleNoteFingering = '1', upperFirstInFingering = True):
    if len(sampleNoteFingering) == 1:
        return fingerMarks[sampleNoteFingering]
    trans = []
    change = sampleNoteFingering.split('-')
    if len(change) == 2:
        trans.append(fingerMarks[change[0]])
        trans.append(symbols['finger_change'])
        trans.append(fingerMarks[change[1]])
    
    choice = sampleNoteFingering.split('|')
    if len(choice) == 2:
        if upperFirstInFingering:
            trans.append(fingerMarks[choice[0]])
            trans.append(fingerMarks[choice[1]])
        else: # lower fingering first
            trans.append(fingerMarks[choice[1]])
            trans.append(fingerMarks[choice[0]])
        
    pair = sampleNoteFingering.split(',')
    if len(pair) == 2:
        try:
            upper = fingerMarks[pair[0]]
        except KeyError:
            upper = symbols['first_set_missing_fingermark']
        try:
            lower = fingerMarks[pair[1]]
        except KeyError:
            lower = symbols['second_set_missing_fingermark']
            
        if upperFirstInFingering:
            trans.append(upper)
            trans.append(lower)
        else: # lower fingering first
            trans.append(lower)
            trans.append(upper)
            
    if len(trans) == 0:
        raise BrailleBasicException("Cannot translate note fingering: " + sampleNoteFingering)

    return u"".join(trans)

def transcribeSignatures(music21KeySignature, music21TimeSignature, outgoingKeySig = None):
    '''
    Takes in a :class:`~music21.key.KeySignature` and :class:`~music21.meter.TimeSignature` and returns its representation 
    in braille as a string in UTF-8 unicode. If given an old key signature, then its cancellation will be applied before
    and in relation to the new key signature.
    
    
    Raises a BrailleBasicException if the resulting key and time signature is empty, which happens if the time signature
    is None and (a) the key signature is None or (b) the key signature has zero sharps and there is no previous key signature.
    
    >>> from music21.braille import basic
    >>> from music21 import key
    >>> from music21 import meter
    >>> print basic.transcribeSignatures(key.KeySignature(5), meter.TimeSignature('3/8'), None)
    ⠼⠑⠩⠼⠉⠦
    >>> print basic.transcribeSignatures(key.KeySignature(0), None, key.KeySignature(-3))
    ⠡⠡⠡
    '''
    if music21TimeSignature == None and (music21KeySignature == None or (music21KeySignature.sharps == 0 and outgoingKeySig == None)):
            raise BrailleBasicException("No key or time signature to transcribe!")
    
    trans = []
    if not music21KeySignature == None:
        trans.append(keySigToBraille(music21KeySignature, outgoingKeySig = outgoingKeySig))
    if not music21TimeSignature == None:
        trans.append(timeSigToBraille(music21TimeSignature))
        
    return u"".join(trans)

#-------------------------------------------------------------------------------
# Translation between braille unicode and ASCII/other symbols.

def brailleUnicodeToBrailleAscii(brailleUnicode):
    '''
    translates a braille UTF-8 unicode string into braille ASCII,
    which is the format compatible with most braille embossers.
    
    
    .. note:: The method works by corresponding braille symbols to ASCII symbols.
        The table which corresponds said values can be found 
        `here <http://en.wikipedia.org/wiki/Braille_ASCII#Braille_ASCII_values>`_.
        Because of the way in which the braille symbols translate2, the resulting
        ASCII string will look like gibberish. Also, the eighth-note notes in braille 
        music are one-off their corresponding letters in both ASCII and written braille.
        The written D is really a C eighth-note, the written E is really a 
        D eighth note, etc. 
    
    
    >>> from music21.braille import basic
    >>> from music21 import note
    >>> basic.brailleUnicodeToBrailleAscii(u'\u2800')
    ' '
    >>> Cs8 = note.Note('C#4', quarterLength = 0.5)
    >>> Cs8_braille = basic.noteToBraille(Cs8)
    >>> basic.brailleUnicodeToBrailleAscii(Cs8_braille)
    '%"D'
    >>> Eb8 = note.Note('E-4', quarterLength = 0.5)
    >>> Eb8_braille = basic.noteToBraille(Eb8)
    >>> basic.brailleUnicodeToBrailleAscii(Eb8_braille)
    '<"F'
    '''
    brailleLines = brailleUnicode.splitlines()
    asciiLines = []
    
    for sampleLine in brailleLines:
        allChars = []
        for char in sampleLine:
            allChars.append(ascii_chars[char])
        asciiLines.append(''.join(allChars))
        
    return '\n'.join(asciiLines)

def brailleAsciiToBrailleUnicode(brailleAscii):
    '''
    translates a braille ASCII string to braille UTF-8 unicode, which
    can then be displayed on-screen in braille on compatible systems.
    
    
    .. note:: The method works by corresponding ASCII symbols to braille
        symbols in a very direct fashion. It is not a translator from plain
        text to braille, because ASCII symbols may not correspond to their
        equivalents in braille. For example, a literal period is a 4 in 
        braille ASCII. Also, all letters are translated into their lowercase
        equivalents, and any capital letters are indicated by preceding them
        with a comma.
        
    
    >>> from music21.braille import basic
    >>> from music21 import tempo
    >>> t1 = basic.brailleAsciiToBrailleUnicode(",ANDANTE ,MAESTOSO4")
    >>> t2 = basic.tempoTextToBraille(tempo.TempoText("Andante Maestoso"))
    >>> t1 == t2
    True
    '''
    braille_chars = {}
    for key in ascii_chars:
        braille_chars[ascii_chars[key]] = key
        
    asciiLines = brailleAscii.splitlines()
    brailleLines = []
    
    for sampleLine in asciiLines:
        allChars = []
        for char in sampleLine:
            allChars.append(braille_chars[char.upper()])
        brailleLines.append(u''.join(allChars))
    
    return u'\n'.join(brailleLines)

def brailleUnicodeToSymbols(brailleUnicode, filledSymbol = 'o', emptySymbol = u'\u00B7'):
    '''
    translates a braille unicode string into symbols (ASCII or UTF-8).
    '''
    symbolTrans = {'00': '{symbol1}{symbol2}'.format(symbol1 = emptySymbol, symbol2 = emptySymbol),
                   '01': '{symbol1}{symbol2}'.format(symbol1 = emptySymbol, symbol2 = filledSymbol),
                   '10': '{symbol1}{symbol2}'.format(symbol1 = filledSymbol, symbol2 = emptySymbol),
                   '11': '{symbol1}{symbol2}'.format(symbol1 = filledSymbol, symbol2 = filledSymbol)}
    
    brailleLines = brailleUnicode.splitlines()
    binaryLines = []

    for sampleLine in brailleLines:
        binaryLine1 = []
        binaryLine2 = []
        binaryLine3 = []
        for char in sampleLine:
            (dots14, dots25, dots36) = binary_dots[char]
            binaryLine1.append(symbolTrans[dots14])
            binaryLine2.append(symbolTrans[dots25])
            binaryLine3.append(symbolTrans[dots36])
        binaryLines.append(u'  '.join(binaryLine1))
        binaryLines.append(u'  '.join(binaryLine2))
        binaryLines.append(u'  '.join(binaryLine3))
        binaryLines.append(u'')
        
    return u'\n'.join(binaryLines[0:-1])

#-------------------------------------------------------------------------------
# Translation of words and numbers.

def wordToBraille(sampleWord, isTextExpression = False):
    '''
    >>> from music21.braille import basic
    >>> print basic.wordToBraille('Andante')
    ⠠⠁⠝⠙⠁⠝⠞⠑
    >>> print basic.wordToBraille('Fagott')
    ⠠⠋⠁⠛⠕⠞⠞
    '''
    wordTrans = []
    
    if not isTextExpression:
        for letter in sampleWord:
            if letter.isupper():
                wordTrans.append(symbols['uppercase'] + alphabet[letter.lower()])
            else:
                wordTrans.append(alphabet[letter])
    else:
        for letter in sampleWord:
            if letter.isupper():
                wordTrans.append(alphabet[letter.lower()])
            elif letter == '.':
                wordTrans.append(symbols['dot'])
            else:
                wordTrans.append(alphabet[letter])
        
    return u''.join(wordTrans)

def numberToBraille(sampleNumber):
    '''
    >>> from music21.braille import basic
    >>> print basic.numberToBraille(12)
    ⠼⠁⠃
    >>> print basic.numberToBraille(7)
    ⠼⠛
    >>> print basic.numberToBraille(37)
    ⠼⠉⠛
    '''
    numberTrans = []
    numberTrans.append(symbols['number'])
    for digit in str(sampleNumber):
        numberTrans.append(numbers[int(digit)])
    
    return u''.join(numberTrans)


#-------------------------------------------------------------------------------

class BrailleBasicException(music21.Music21Exception):
    pass
    
#-------------------------------------------------------------------------------
class Test(unittest.TestCase):

    def runTest(self):
        pass


if __name__ == "__main__":
    import sys
    reload(sys)
    sys.setdefaultencoding("UTF-8")
    music21.mainTest(Test)

#------------------------------------------------------------------------------
# eof