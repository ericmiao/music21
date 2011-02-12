#-------------------------------------------------------------------------------
# Name:         romanText/translate.py
# Purpose:      Translation routines for roman numeral analysis text files
#
# Authors:      Christopher Ariza
#               Michael Scott Cuthbert
#
# Copyright:    (c) 2011 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------


'''Translation routines for roman numeral analysis text files, as defined and demonstrated by Dmitri Tymoczko.
'''
import unittest
import music21
import copy


from music21.romanText import base as romanTextModule

from music21 import environment
_MOD = 'romanText.translate.py'
environLocal = environment.Environment(_MOD)


#-------------------------------------------------------------------------------
class TranslateRomanTextException(Exception):
    pass


def _copySingleMeasure(t, p, kCurrent):
    '''Given a RomanText token, a Part used as the current container, and the current Key, return a Measure copied from the past of the Part. 
    '''
    # copy from a past location; need to change key
    targetNumber, targetRepeat = t.getCopyTarget()
    if len(targetNumber) > 1: # this is an encoding error
        raise TranslateRomanTextException('a single measure cannot define a copy operation for multiple measures')
    # TODO: ignoring repeat letters
    target = targetNumber[0]
    for mPast in p.getElementsByClass('Measure'):
        if mPast.number == target:
            m = copy.deepcopy(mPast)
            m.number = t.number[0]
            # update all keys
            for rnPast in m.getElementsByClass('RomanNumeral'):
                if kCurrent is None: # should not happen
                    raise TranslateRomanTextException('attempting to copy a measure but no past key definitions are found')
                rnPast.setKeyOrScale(kCurrent)
            break
    return m

def _copyMultipleMeasures(t, p, kCurrent):
    '''Given a RomanText token for a RTMeasure, a Part used as the current container, and the current Key, return a Measure range copied from the past of the Part.
    '''
    from music21 import stream
    # the key provided needs to be the current key

    targetNumbers, targetRepeat = t.getCopyTarget()
    if len(targetNumbers) == 1: # this is an encoding error
        raise TranslateRomanTextException('a multiple measure range cannot copy a single measure')
    # TODO: ignoring repeat letters
    # TODO: check for overlap:  m20-25 = m17-22
    # check for range equality: m20-30 = m10-19
    if t.number[1] - t.number[0] != targetNumbers[1] - targetNumbers[0]:
        raise TranslateRomanTextException('a multiple measure range copy attempting to copy an unequal sized region')

    targetStart = targetNumbers[0]
    targetEnd = targetNumbers[1]
    measures = []
    for mPast in p.getElementsByClass('Measure'):
        if mPast.number in range(targetStart, targetEnd +1):
            m = copy.deepcopy(mPast)
            m.number = t.number[0] + mPast.number - targetStart
            measures.append(m)
            # update all keys
            for rnPast in m.getElementsByClass('RomanNumeral'):
                if kCurrent is None: # should not happen
                    raise TranslateRomanTextException('attempting to copy a measure but no past key definitions are found')
                rnPast.setKeyOrScale(kCurrent)
        if mPast.number == targetEnd:
            break
    return measures



def romanTextToStreamScore(rtHandler, inputM21=None):
    '''Given a roman text handler, return or fill a Score Stream.
    '''
    # this could be just a Stream, but b/c we are creating metadata, perhaps better to match presentation of other scores. 

    from music21 import metadata
    from music21 import stream
    from music21 import note
    from music21 import meter
    from music21 import key
    from music21 import roman
    from music21 import tie


    if inputM21 == None:
        s = stream.Score()
    else:
        s = inputM21

    # metadata can be first
    md = metadata.Metadata()
    s.insert(0, md)

    p = stream.Part()
    # ts indication are found in header, and also found elsewhere
    tsCurrent = None # store initial time signature
    tsSet = False # store if set to a measure
    lastMeasureNumber = 0
    previousRn = None
    kCurrent = None # key is set inside of measure
    prefixToLyric = ""

    for t in rtHandler.tokens:
        if t.isTitle():
            md.title = t.data            
        elif t.isWork():
            md.alternativeTitle = t.data
        elif t.isComposer():
            md.composer = t.data
        elif t.isTimeSignature():
            tsCurrent = meter.TimeSignature(t.data)
            tsSet = False
            environLocal.printDebug(['tsCurrent:', tsCurrent])
            
        elif t.isMeasure():
            if t.variantNumber is not None:
                environLocal.printDebug(['skipping variant: %s' % t])
                continue
            # if this measure number is more than 1 greater than the last
            # defined measure number, and the previous chord is not None, 
            # then fill with copies of the last-defined measure
            if ((t.number[0] > lastMeasureNumber + 1) and 
                (previousRn is not None)):
                for i in range(lastMeasureNumber + 1, t.number[0]):
                    mFill = stream.Measure()
                    mFill.number = i
                    newRn = copy.deepcopy(previousRn)
                    newRn.lyric = ""
                    # set to entire bar duration and tie 
                    newRn.duration = copy.deepcopy(tsCurrent.barDuration)
                    if previousRn.tie == None:
                        previousRn.tie = tie.Tie('start')
                    else:
                        previousRn.tie.type = 'continue'
                    # set to stop for now; may extend on next iteration
                    newRn.tie = tie.Tie('stop')
                    previousRn = newRn
                    mFill.append(newRn)
                    p.append(mFill)
                lastMeasureNumber = t.number[0] - 1
            # create a new measure or copy a past measure
            if len(t.number) == 1 and t.isCopyDefinition: # if not a range
                m = _copySingleMeasure(t, p, kCurrent)
                p.append(m)
                lastMeasureNumber = m.number
                romans = m.getElementsByClass(roman.RomanNumeral)
                if len(romans) > 0:
                    previousRn = romans[-1] 
            elif len(t.number) > 1:
                measures = _copyMultipleMeasures(t, p, kCurrent)
                p.append(measures)
                lastMeasureNumber = measures[-1].number
                romans = measures[-1].getElementsByClass(roman.RomanNumeral)
                if len(romans) > 0:
                    previousRn = romans[-1]
            else:
                m = stream.Measure()
                m.number = t.number[0]
                lastMeasureNumber = t.number[0]
                
                if not tsSet:
                    m.timeSignature = tsCurrent
                    tsSet = True # only set when changed
    
                o = 0.0 # start offsets at zero
                previousChordInMeasure = None
                for i, a in enumerate(t.atoms):
                    if isinstance(a, romanTextModule.RTKey):
                        kCurrent = a.getKey()
                        prefixLyric = kCurrent.tonic + ": "
                    if isinstance(a, romanTextModule.RTBeat):
                        # set new offset based on beat
                        o = a.getOffset(tsCurrent)
                        if (previousChordInMeasure is None and 
                            previousRn is not None):
                            # setting a new beat before giving any chords
                            firstChord = copy.deepcopy(previousRn)
                            firstChord.quarterLength = o
                            firstChord.lyric = ""
                            if previousRn.tie == None:
                                previousRn.tie = tie.Tie('start')
                            else:
                                previousRn.tie.type = 'continue'    
                            firstChord.tie = tie.Tie('stop')
                            previousRn = firstChord
                            previousChordInMeasure = firstChord
                            m.insert(0, firstChord)
                            
                    if isinstance(a, romanTextModule.RTChord):
                        # probably best to find duration
                        if previousChordInMeasure is None:
                            pass # use default duration
                        else: # update duration of previous chord in Measure
                            oPrevious = previousChordInMeasure.getOffsetBySite(m)
                            previousChordInMeasure.quarterLength = o - oPrevious
                        # use source to evaluation roman 
                        try:
                            useFigure = a.src
                            if useFigure == 'III':
                                pass
                            rn = roman.RomanNumeral(useFigure, kCurrent)
                        except:
                            environLocal.printDebug('cannot create RN from: %s' % a.src)
                            rn = note.Note() # create placeholder 
                        rn.addLyric(prefixLyric + a.src)
                        prefixLyric = ""
                        m.insert(o, rn)
                        previousChordInMeasure = rn
                        previousRn = rn
                # may need to adjust duration of last chord added
                previousRn.quarterLength = tsCurrent.barDuration.quarterLength - o
                p.append(m)
    p.makeBeams()
    s.insert(0,p)
    return s




                

def romanTextStringToStreamScore(rtString, inputM21=None):
    '''Convenience routine for geting a score from string, not a handler
    '''
    # create an empty file obj to get handler from string
    rtf = romanTextModule.RTFile()
    rth = rtf.readstr(rtString) # return handler, processes tokens
    s = romanTextToStreamScore(rth, inputM21=inputM21)
    return s


#-------------------------------------------------------------------------------
class TestExternal(unittest.TestCase):

    def runTest(self):
        pass
 
    def testExternalA(self):
        from music21 import romanText
        from music21.romanText import testFiles

        for tf in testFiles.ALL:
            rtf = romanText.RTFile()
            rth = rtf.readstr(tf) # return handler, processes tokens
            s = romanTextToStreamScore(rth)
            s.show()


class Test(unittest.TestCase):
    
    def runTest(self):
        pass
    
    def testBasicA(self):
        from music21 import romanText
        from music21.romanText import testFiles

        for tf in testFiles.ALL:
            rtf = romanText.RTFile()
            rth = rtf.readstr(tf) # return handler, processes tokens
            s = romanTextToStreamScore(rth)
            #s.show()

        
        s = romanTextStringToStreamScore(testFiles.swv23)
        self.assertEqual(s.metadata.composer, 'Heinrich Schutz')
        # this is defined as a Piece tag, but shows up here as a title, after
        # being set as an alternate title
        self.assertEqual(s.metadata.title, 'Warum toben die Heiden, Psalmen Davids no. 2, SWV 23')
        

        s = romanTextStringToStreamScore(testFiles.riemenschneider001)
        self.assertEqual(s.metadata.composer, 'J. S. Bach')
        self.assertEqual(s.metadata.title, 'Aus meines Herzens Grunde')

        s = romanTextStringToStreamScore(testFiles.monteverdi_3_13)
        self.assertEqual(s.metadata.composer, 'Claudio Monteverdi')

    def testBasicB(self):
        from music21 import romanText
        from music21.romanText import testFiles

        s = romanTextStringToStreamScore(testFiles.riemenschneider001)
        #s.show()

    def testMeasureCopying(self):
        from music21 import romanText
        from music21.romanText import testFiles

        s = romanTextStringToStreamScore(testFiles.swv23)
        mStream = s.parts[0].getElementsByClass('Measure')
        # the first four measures should all have the same content
        rn1 = mStream[1].getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn1.pitches), '[D5, F#5, A5]')
        self.assertEqual(str(rn1.figure), 'V')
        rn2 = mStream[1].getElementsByClass('RomanNumeral')[1]
        self.assertEqual(str(rn2.figure), 'i')

        # make sure that m2, m3, m4 have the same values
        rn1 = mStream[2].getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn1.figure), 'V')
        rn2 = mStream[2].getElementsByClass('RomanNumeral')[1]
        self.assertEqual(str(rn2.figure), 'i')

        rn1 = mStream[3].getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn1.figure), 'V')
        rn2 = mStream[3].getElementsByClass('RomanNumeral')[1]
        self.assertEqual(str(rn2.figure), 'i')


        # test multiple measure copying
        s = romanTextStringToStreamScore(testFiles.monteverdi_3_13)
        mStream = s.parts[0].getElementsByClass('Measure')
        for m in mStream:
            if m.number == 41: #m49-51 = m41-43
                m1a = m
            elif m.number == 42: #m49-51 = m41-43
                m2a = m
            elif m.number == 43: #m49-51 = m41-43
                m3a = m
            elif m.number == 49: #m49-51 = m41-43
                m1b = m
            elif m.number == 50: #m49-51 = m41-43
                m2b = m
            elif m.number == 51: #m49-51 = m41-43
                m3b = m

        rn = m1a.getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn.figure), 'IV')        
        rn = m1a.getElementsByClass('RomanNumeral')[1]
        self.assertEqual(str(rn.figure), 'I')        

        rn = m1b.getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn.figure), 'IV')        
        rn = m1b.getElementsByClass('RomanNumeral')[1]
        self.assertEqual(str(rn.figure), 'I')        

        rn = m2a.getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn.figure), 'I')        
        rn = m2a.getElementsByClass('RomanNumeral')[1]
        self.assertEqual(str(rn.figure), 'ii')        

        rn = m2b.getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn.figure), 'I')        
        rn = m2b.getElementsByClass('RomanNumeral')[1]
        self.assertEqual(str(rn.figure), 'ii')        

        rn = m3a.getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn.figure), 'V/ii')        
        rn = m3b.getElementsByClass('RomanNumeral')[0]
        self.assertEqual(str(rn.figure), 'V/ii')        





#-------------------------------------------------------------------------------
# define presented order in documentation
_DOC_ORDER = []


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1: # normal conditions
        music21.mainTest(Test)
    elif len(sys.argv) > 1:
        t = Test()
        # arg[1] is test to launch
        if hasattr(t, sys.argv[1]): getattr(t, sys.argv[1])()

#------------------------------------------------------------------------------
# eof
