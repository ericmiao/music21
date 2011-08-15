# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         audioSearch.base.py
# Purpose:      base subroutines for all audioSearching and score following routines
#
# Authors:      Jordi Bartolome
#               Michael Scott Cuthbert
#
# Copyright:    (c) 2011 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------

import copy
import math
import wave
import unittest, doctest

import music21.scale
import music21.pitch
from music21 import search
from music21 import environment, converter
from music21 import metadata, note, stream
from music21.audioSearch import recording
_MOD = 'audioSearch/base.py'
environLocal = environment.Environment(_MOD)

audioChunkLength = 1024
recordSampleRate = 44100

_missingImport = []
try:
    import matplotlib.mlab # for find
    import matplotlib.pyplot
except ImportError:
    _missingImport.append('matplotlib')

try:    
    import numpy
except ImportError:
    _missingImport.append('numpy')

try:
    import scipy.signal 
except ImportError:
    _missingImport.append('scipy')

if len(_missingImport) > 0:
    if environLocal['warnings'] in [1, '1', True]:
        pass
        #environLocal.warn(common.getMissingImportStr(_missingImport), header='music21:')



def freq_from_autocorr(sig, fs):
    '''  
    It converts the temporal domain into a frequency domain. In order to do that, it
    uses the autocorrelation function, which finds the periodicities of the signal
    in the temporal domain and, consequently, obtains the frequency in each instant 
    of time.
    
    I took part of this code from internet, and I modified a little bit to 
    adapt it to our algorithm.
    '''
    
    # Calculate autocorrelation (same thing as convolution, but with one input 
    # reversed in time), and throw away the negative lags
    sig = numpy.array(sig)
    #print str(sig)
    corr = scipy.signal.fftconvolve(sig, sig[::-1], mode='full')
    corr = corr[len(corr) / 2:]
    
    # Find the first low point
    d = numpy.diff(corr)
    start = matplotlib.mlab.find(d > 0)[0]
    
    # Find the next peak after the low point (other than 0 lag).  This bit is 
    # not reliable for long signals, due to the desired peak occurring between 
    # samples, and other peaks appearing higher.
    peak = numpy.argmax(corr[start:]) + start
    px, py = parabolic(corr, peak)
    return fs / px

def prepareThresholds(useScale=music21.scale.ChromaticScale('C4')):
    '''
    returns two elements.  The first is a list of threshold values
    for one octave of a given scale, `useScale`, 
    (including the octave repetition) (Default is a ChromaticScale).
    The second is the pitches of the scale.
    
    
    A threshold value is the fractional part of the log-base-2 value of the
    frequency.
    
    
    For instance if A = 440 and B-flat = 460, then the threshold between
    A and B-flat will be 450.  Notes below 450 should be considered As and those
    above 450 should be considered B-flats.
    
    
    Thus the list returned has one less element than the number of notes in the
    scale + octave repetition.  If useScale is a ChromaticScale, `prepareThresholds`
    will return a 12 element list.  If it's a diatonic scale, it'll have 7 elements.
    
    
    >>> from music21 import *
    >>> l, p = music21.audioSearch.prepareThresholds(scale.MajorScale('A3'))
    >>> for i in range(len(l)):
    ...    print "%s < %.2f < %s" % (p[i], l[i], p[i+1])
    A3 < 0.86 < B3
    B3 < 0.53 < C#4
    C#4 < 0.16 < D4
    D4 < 0.28 < E4
    E4 < 0.45 < F#4
    F#4 < 0.61 < G#4
    G#4 < 1.24 < A4
    '''
    scPitches = useScale.pitches
    scPitchesRemainder = []
   
    for p in scPitches:
        pLog2 = math.log(p.frequency, 2)
        scPitchesRemainder.append(math.modf(pLog2)[0])
   
    scPitchesRemainder[-1] += 1
   
    scPitchesThreshold = []
    for i in range(len(scPitchesRemainder) - 1):
        scPitchesThreshold.append((scPitchesRemainder[i] + scPitchesRemainder[i + 1]) / 2)
 
    return scPitchesThreshold, scPitches


def parabolic(f, x):
    '''
    Quadratic interpolation for estimating the true position of an
    inter-sample maximum when nearby samples are known.

   
    f is a vector and x is an index for that vector.

   
    Returns (vx, vy), the coordinates of the vertex of a parabola that goes
    through point x and its two neighbors.
   

    Example:
    Defining a vector f with a local maximum at index 3 (= 6), find local
    maximum if points 2, 3, and 4 actually defined a parabola.


    >>> from music21 import *
    >>> import numpy
    >>> f = [2, 3, 1, 6, 4, 2, 3, 1]
    >>> audioSearch.parabolic(f, numpy.argmax(f))
    (3.214285714285..., 6.160714285714...)
   
    '''
    xv = 1.0 / 2.0 * (f[x - 1] - f[x + 1]) / (f[x - 1] - 2.0 * f[x] + f[x + 1]) + x
    yv = f[x] - 1.0 / 4.0 * (f[x - 1] - f[x + 1]) * (xv - x)
    return (xv, yv)



def normalizeInputFrequency(inputPitchFrequency, thresholds=None, pitches=None):
    '''
    Takes in an inputFrequency, a set of threshold values, and a set of allowable pitches
    (given by prepareThresholds) and returns a tuple of the normalized frequency and the 
    pitch detected (as a :class:`~music21.pitch.Pitch` object)
    
    
    It will convert the frequency to be within the range of the default frequencies
    (usually C4 to C5) but the pitch object will have the correct octave.
    
    
    >>> from music21 import *
    >>> audioSearch.normalizeInputFrequency(441.72)
    (440.0, A4)
    
    
    If you will be doing this often, it's best to cache your thresholds and
    pitches by running `prepareThresholds` once first:
    
    
    >>> thresholds, pitches = audioSearch.prepareThresholds(scale.ChromaticScale('C4'))
    >>> for fq in [450, 510, 550, 600]:
    ...      print normalizeInputFrequency(fq, thresholds, pitches)
    (440.0, A4)
    (523.25113..., C5)
    (277.18263..., C#5)
    (293.66476..., D5)
    '''
    if ((thresholds is None and pitches is not None)
         or (thresholds is not None and pitches is None)):
        raise AudioSearchException("Cannot normalize input frequency if thresholds are given and pitches are not, or vice-versa")   
    elif thresholds == None:
        (thresholds, pitches) = prepareThresholds()
   
    inputPitchLog2 = math.log(inputPitchFrequency, 2)
    (remainder, oct) = math.modf(inputPitchLog2)
    oct = int(oct)
    for i in range(len(thresholds)):
        threshold = thresholds[i]
        if remainder < threshold:
            returnPitch = copy.deepcopy(pitches[i])            
            returnPitch.octave = oct - 4 ## PROBLEM
            #returnPitch.inputFrequency = inputPitchFrequency
            name_note = music21.pitch.Pitch(str(pitches[i]))
            return name_note.frequency, returnPitch
    # else:
    # above highest threshold
    returnPitch = copy.deepcopy(pitches[-1])
    returnPitch.octave = oct - 3
    returnPitch.inputFrequency = inputPitchFrequency
    name_note = music21.pitch.Pitch(str(pitches[-1]))
    return name_note.frequency, returnPitch      

def pitchFrequenciesToObjects(detectedPitchesFreq, useScale=music21.scale.MajorScale('C4')):
    '''
    Takes in a list of detected pitch frequencies and returns a tuple where the first element
    is a list of :class:~`music21.pitch.Pitch` objects that best match these frequencies 
    and the second element is a list of the frequencies of those objects that can
    be plotted for matplotlib
    
    
    To-do: only return the former.  The latter can be generated in other ways.
    
    '''
    
    detectedPitchObjects = []
    (thresholds, pitches) = prepareThresholds(useScale)

    for i in range(len(detectedPitchesFreq)):    
        inputPitchFrequency = detectedPitchesFreq[i]
        freq, pitch_name = normalizeInputFrequency(inputPitchFrequency, thresholds, pitches)       
        detectedPitchObjects.append(pitch_name)
    
    listplot = []
    i = 0
    while i < len(detectedPitchObjects) - 1:
        name = detectedPitchObjects[i].name
        hold = i
        tot_octave = 0
        while i < len(detectedPitchObjects) - 1 and detectedPitchObjects[i].name == name:
            tot_octave = tot_octave + detectedPitchObjects[i].octave
            i = i + 1
        tot_octave = round(tot_octave / (i - hold))
        for j in range(i - hold):
            detectedPitchObjects[hold + j - 1].octave = tot_octave
            listplot.append(detectedPitchObjects[hold + j - 1].frequency)
    return detectedPitchObjects, listplot


def getFrequenciesFromAudio(record=True, length=10.0, waveFilename='xmas.wav', wholeFile=True, wv=None, totsamples=None):
    '''
    It calculates the fundamental frequency at every instant of time of an audio signal 
    extracted either from the microphone or from an already recorded song. 
    It uses a period of time defined by the variable "length" in seconds.
    
    It returns a list with the frequencies and a variable with the file descriptor either 
    of the audio file or the microphone.
    
    >>> from music21 import *
    >>> audioChunkLength = 1024
    >>> recordSampleRate = 44100
    >>> frequencyList, fd, totsamples, samplesFile= getFrequenciesFromAudio(record=False, length=1.0, waveFilename='pachelbel.wav', wholeFile=False,totsamples=0)
    >>> for i in range(5):
    ...     print frequencyList[i]
    143.627689055
    99.0835452019
    211.004784689
    4700.31347962
    2197.94311194
    '''
    storedWaveSampleList = []
    if record == True:
        environLocal.printDebug("* start recording")
        storedWaveSampleList = recording.samplesFromRecording(seconds=length,
                                                              storeFile=waveFilename,
                                                              recordChunkLength=audioChunkLength)
        environLocal.printDebug("* stop recording")
        
        freqFromAQList = []
        
        for data in storedWaveSampleList:
            samps = numpy.fromstring(data, dtype=numpy.int16)
            freqFromAQList.append(freq_from_autocorr(samps, recordSampleRate))  
        return freqFromAQList, wv , 0, 10
        
    elif wholeFile == True:
        environLocal.printDebug("* reading entire file from disk")
        try:
            wv = wave.open(waveFilename, 'r')
        except IOError:
            raise AudioSearchException("Cannot open %s for reading, does not exist" % waveFilename)
        
        #modify it to read the entire file
        for i in range(wv.getnframes() / audioChunkLength):        
            data = wv.readframes(audioChunkLength)
            storedWaveSampleList.append(data)
        
        freqFromAQList = []        
        for data in storedWaveSampleList:
            samps = numpy.fromstring(data, dtype=numpy.int16)
            freqFromAQList.append(freq_from_autocorr(samps, recordSampleRate))  
        return freqFromAQList, wv   
    
    else:   
        environLocal.printDebug("* reading file from disk a part of the song")
        if wv == None:
            try:
                wv = wave.open(waveFilename, 'r')
            except IOError:
                raise AudioSearchException("Cannot open %s for reading, does not exist" % waveFilename)
        for i in range(int(math.floor(length * recordSampleRate / audioChunkLength))):        
            totsamples = totsamples + audioChunkLength
            if totsamples < wv.getnframes():
                data = wv.readframes(audioChunkLength)
                storedWaveSampleList.append(data)
        freqFromAQList = []
        
        for data in storedWaveSampleList:
            samps = numpy.fromstring(data, dtype=numpy.int16)
            freqFromAQList.append(freq_from_autocorr(samps, recordSampleRate))  
        return freqFromAQList, wv, totsamples, wv.getnframes()

def detectPitchFrequencies(freqFromAQList, useScale=music21.scale.MajorScale('C4')):
    '''
    It detects the pitches of the notes from a list of frequencies, using thresholds which
    depend on the used scale. The default value is the major scale C4.
    
    >>> from music21 import *
    >>> freqFromAQList=[143.627689055,99.0835452019,211.004784689,4700.31347962,2197.9431119]
    >>> pitchesList = detectPitchFrequencies(freqFromAQList, useScale=music21.scale.MajorScale('C4'))
    >>> for i in range(5):
    ...     print pitchesList[i]
    146.832383959
    97.9988589954
    220.0
    4698.63628668
    2093.0045224
    '''
    (thresholds, pitches) = prepareThresholds(useScale)
    
    detectedPitchesFreq = []
    
    for i in range(len(freqFromAQList)):    # to find thresholds and frequencies
        inputPitchFrequency = freqFromAQList[i]
        freq, pitch_name = normalizeInputFrequency(inputPitchFrequency, thresholds, pitches)     
        detectedPitchesFreq.append(pitch_name.frequency)    
    return detectedPitchesFreq

def smoothFrequencies(detectedPitchesFreq, smoothLevels=7, inPlace=True):
    '''
    It smooths the shape of the signal in order to avoid false detections in the fundamental
    frequency.
    '''
    dpf = detectedPitchesFreq
    if inPlace == True:
        detectedPitchesFreq = dpf
    else:
        detectedPitchesFreq = copy.copy(dpf)

    ### Jordi -- are you sure that this does what you want it to?
    
    ## Now yes! I forgot to implement the beginning and the end
    # I could implement it in a better way, but I think it doesn't affect too much
    # Are only 7+7 samples ... i'll implement it better in the future! 
    #smoothing
    
    beginning = 0
    ends = 0
    
    for i in range(smoothLevels):
        beginning = beginning + detectedPitchesFreq[i]
    beginning = beginning / smoothLevels
    
    for i in range(smoothLevels):
        ends = ends + detectedPitchesFreq[len(detectedPitchesFreq) - 1 - i] 
    ends = ends / smoothLevels
    
    for i in range(len(detectedPitchesFreq)):
        if i < int(math.floor(smoothLevels / 2.0)):
            detectedPitchesFreq[i] = beginning
        elif i > len(detectedPitchesFreq) - int(math.ceil(smoothLevels / 2.0)) - 1:
            detectedPitchesFreq[i] = ends
        else:
            t = 0
            for j in range(smoothLevels):
                t = t + detectedPitchesFreq[i + j - int(math.floor(smoothLevels / 2.0))]
            detectedPitchesFreq[i] = t / smoothLevels
    return detectedPitchesFreq



#-------------------------------------------------------
# Duration related routines


def joinConsecutiveIdenticalPitches(detectedPitchObjects):
    '''
    takes a list of equally-spaced :class:`~music21.pitch.Pitch` objects
    and returns a tuple of two lists, the first a list of 
    :class:`~music21.note.Note` 
    or :class:`~music21.note.Rest` objects (each of quarterLength 1.0) 
    and a list of how many were joined together to make that object.
    
    
    N.B. the returned list is NOT a :class:`~music21.stream.Stream`.    
    '''
    # detecting notes
    #environLocal.printDebug("* joining identical consecutive pitches")
    
    #initialization
    REST_FREQUENCY = 10
    detectedPitchObjects[0].frequency = REST_FREQUENCY
    #JUST_PITCHES = False # If you only want the pitches define it True
    
    #detecting the length of each note 
    j = 0
    good = 0
    bad = 0
    valid_note = False
    
    total_notes = 0
    total_rests = 0
    notesList = []
    durationList = []
    
    while j < len(detectedPitchObjects):
        fr = detectedPitchObjects[j].frequency

        # detect consecutive instances of the same frequency
        while j < len(detectedPitchObjects) and fr == detectedPitchObjects[j].frequency:
            good = good + 1
            
            # if more than 6 consecutive identical samples, it might be a note
            if good >= 6:
                valid_note = True
                
                # if we've gone 15 or more samples without getting something constant, assume it's a rest
                if bad >= 15:
                    durationList.append(bad)   
                    total_rests = total_rests + 1    
                    notesList.append(note.Rest())
                bad = 0       
            j = j + 1
        if valid_note == True:
            durationList.append(good)        
            total_notes = total_notes + 1    
            ### doesn't this unnecessarily create a note that it doesn't need?
            ### notesList.append(detectedPitchObjects[j-1].frequency) should work
            n = note.Note()
            n.pitch = detectedPitchObjects[j - 1]
            notesList.append(n)
        else:
            bad = bad + good
        good = 0
        valid_note = False
        j = j + 1

#    environLocal.printDebug("Total notes recorded %d " % total_notes)
#    environLocal.printDebug("Total rests recorded %d " % total_rests)
    
    return notesList, durationList, total_notes


def quantizeDuration(length):
    '''
    round an approximately transcribed quarterLength to a better one in
    music21.
    
    
    Should be replaced by a full-featured routine in midi or stream.
    
    
    See :meth:`~music21.stream.Stream.quantize` for more information
    on the standard music21 methodology.
    
    
    >>> from music21 import *
    >>> audioSearch.quantizeDuration(1.01)
    1.0
    >>> audioSearch.quantizeDuration(1.70)
    1.5
    '''
    length = length * 100
    typicalLengths = [25.00, 50.00, 100.00, 150.00, 200.00, 400.00]
    thresholds = []
    for i in range(len(typicalLengths) - 1):
        thresholds.append((typicalLengths[i] + typicalLengths[i + 1]) / 2)
    
    finalLength = typicalLengths[0]   
    for i in range(len(thresholds)):        
        threshold = thresholds[i]
        if length > threshold:
            finalLength = typicalLengths[i + 1]
    return finalLength / 100


def quarterLengthEstimation(durationList, musicalFigure=None):
    '''
    takes a list of lengths of notes (measured in
    audio samples) and tries to estimate using
    matplotlib.pyplot.hist what the length of a
    quarter note should be in this list.
    
    
    Returns a float -- and not an int.
    
    
    >>> from music21 import *
    >>> durationList = [20, 19, 10, 30, 6, 21]
    >>> audioSearch.quarterLengthEstimation(durationList)
    20.625    
    ''' 
    dl = copy.copy(durationList)
    dl.append(0)
    pdf, bins, patches = matplotlib.pyplot.hist(dl, bins=8)        
    #environLocal.printDebug("HISTOGRAMA %s %s" % (pdf, bins))
    
    i = len(pdf) - 1 # backwards! it has more sense
    while pdf[i] != max(pdf):
        i = i - 1
    qle = (bins[i] + bins[i + 1]) / 2.0
    
    if musicalFigure == None:
        musicalFigure = 2 # Default: quarter note
        
    qle = qle * math.pow(2, musicalFigure) / 4 # it normalizes the length to a quarter note
        
    #environLocal.printDebug("QUARTER ESTIMATION")
    #environLocal.printDebug("bins %s " % bins)
    #environLocal.printDebug("pdf %s" % pdf)
    #environLocal.printDebug("quarterLengthEstimate %f" % qle)
    return qle



    
def notesAndDurationsToStream(notesList, durationList, scNotes=None, lastNotePosition=None, BEGINNING=None, lengthFixed=None, qle=None):
    '''
    take a list of :class:`~music21.note.Note` objects or rests
    and an equally long list of how long
    each ones lasts in terms of samples and returns a
    Stream using the information from quarterLengthEstimation
    and quantizeDurations.
    
    
    returns a :class:`~music21.stream.Score` object, containing
    a metadata object and a single :class:`~music21.stream.Part` object, which in turn
    contains the notes, etc.  Does not run :meth:`~music21.stream.Stream.makeNotation`
    on the Score.
    
    
    >>> from music21 import *
    >>> durationList = [20, 19, 10, 30, 6, 21]
    >>> n = note.Note
    >>> noteList = [n('C#4'), n('D5'), n('B4'), n('F#5'), n('C5'), note.Rest()]
    >>> s,lengthPart = audioSearch.notesAndDurationsToStream(noteList, durationList)
    >>> s.show('text')
    {0.0} <music21.metadata.Metadata object at ...>
    {0.0} <music21.stream.Part ...>
        {0.0} <music21.note.Note C#>
        {1.0} <music21.note.Note D>
        {2.0} <music21.note.Note B>
        {2.5} <music21.note.Note F#>
        {4.0} <music21.note.Note C>
        {4.25} <music21.note.Rest rest>    
    '''
    
    # rounding lengths    
    p2 = stream.Part() 
    
    # If the score is available, the quarter estimation is better:
    # It could take into account the changes of tempo during the song, but it
    # will take more processing time
    if scNotes != None and lengthFixed == False:
        i = 0    
        n16 = 0
        n8 = 0
        n4 = 0
        n2 = 0
        n1 = 0
        while i + lastNotePosition < len(scNotes) and i < len(notesList):
            if scNotes[i + lastNotePosition + 1].quarterLength == 4:
                n1 = n1 + 1
            elif scNotes[i + lastNotePosition + 1].quarterLength == 2:
                n2 = n2 + 1
            elif scNotes[i + lastNotePosition + 1].quarterLength == 1:
                n4 = n4 + 1
            elif scNotes[i + lastNotePosition + 1].quarterLength == 0.5:
                n8 = n8 + 1
            elif scNotes[i + lastNotePosition + 1].quarterLength == 0.25:
                n16 = n16 + 1
            i = i + 1
        i = 0
        block = [n1, n2, n4, n8, n16]
        valueMax = max(block)
        while block[i] != max(block):
            i = i + 1
        block.pop(i)
        if max(block) < 0.5 * valueMax and len(notesList) > 5: #it means there are the double of one type.            
            musicalFigure = i # i=0 -> sixteenth note, i=1 -> eighth note, i=2 -> quarter...
            print "LENGTH FIXED!!!!!!!!!!!!!!!!!!!!! "
            # quarterLengthEstimation     
            lengthFixed = True
            qle = quarterLengthEstimation(durationList, musicalFigure)
        else:
            qle = quarterLengthEstimation(durationList)
            print "NOT DEFINED"
    else: 
        "ALREADY DEFINED"
        
    if scNotes == None: # this is for the transcriber 
        qle = quarterLengthEstimation(durationList)    

    if BEGINNING == None: # to avoid rests at the beginning of the score! - for the transcriber
        BEGINNING = False
    for i in range(len(durationList)): 
        actualDuration = quantizeDuration(durationList[i] / qle)
        notesList[i].quarterLength = actualDuration
        if (BEGINNING == True) and (notesList[i].name == "rest"):
            #print "SILENCE!!"
            pass
        else: 
            p2.append(notesList[i])
            BEGINNING = False        
    sc = stream.Score()
    sc.metadata = metadata.Metadata()
    sc.metadata.title = 'Automatic Music21 Transcription'
    sc.insert(0, p2)  
    
    if scNotes == None:   # Case transcriber
        return sc, len(p2)
    else: #case follower
        print "LENGTH?", lengthFixed
        return sc, len(p2), lengthFixed, qle

def decisionProcess(list, notePrediction, beginningData, lastNotePosition, countdown):
    '''
    It decides which one of the given parts of the score matches better with recorded part of the song.
    If there is not a part of the score with a good probability to be the correct part,
    it starts a "countdown" in order stop the score following if the bad matching persists.   
    In this case, it does not match the recorded part of the song with any part of the score.
    '''
    i = 0
    position = 0
    while i < len(list) and beginningData[int(list[i].id)] < notePrediction:
        i = i + 1
        position = i
    if len(list) == 1: # it happens when you don't play anything during recording period
        position = 0

    dist = math.fabs(beginningData[0] - notePrediction)
    for i in range(len(list)):
        #print "UU", beginningData[int(list[i].id)], lastNotePosition, notePrediction
        if (list[i].matchProbability >= 0.9 * list[0].matchProbability) and (beginningData[int(list[i].id)] > lastNotePosition): #let's take a 90%
            if math.fabs(beginningData[int(list[i].id)] - notePrediction) < dist:
                dist = math.fabs(beginningData[int(list[i].id)] - notePrediction)
                position = i  
                print "NICE!"
    #print "ERRORS", position, len(list), lastNotePosition, list[position].matchProbability , beginningData[int(list[position].id)]
    if position < len(list) and beginningData[int(list[position].id)] <= lastNotePosition:
        print " error ? ", beginningData[int(list[position].id)], lastNotePosition    
    print "DECISION: %d amb prob %f i dist %f i comenca a %f" % (position, list[position].matchProbability, dist, beginningData[int(list[position].id)])
    if list[position].matchProbability < 0.6 or len(list) == 1: #the latter for the all-rest case
        print "ARE YOU SURE YOU ARE PLAYING THE RIGHT SONG??"
        countdown = countdown + 1
    else:
        countdown = 0
    if dist > 20:
        print "Excessive distance....? dist=%d" % dist
    return position, countdown


def matchingNotes(scoreNotes, myScore, numberNotesRecording, notePrediction, lastNotePosition, result, countdown):
    '''
    '''
    # Analyzing streams
    tn_recording = int(numberNotesRecording)
    totScores = []
    beginningData = []
    lengthData = []
    END_OF_SCORE = False
    tn_window = int(math.ceil(tn_recording * 1.1)) # take 10% more of samples
    hop = int(math.ceil(tn_window / 4))
    if hop == 0:
        iterations = 1
    else:
        iterations = int((math.floor(len(scoreNotes) / hop)) - math.ceil(tn_window / hop)) 
    print "number of iterations", iterations, hop, tn_window, len(scoreNotes)

    
    for i in range(iterations):
        scNotes = copy.deepcopy(scoreNotes)
        scNotes = converter.parse(" ".join(scNotes), "4/4")
        scNotes.elements = scNotes.elements[i * hop + 1 :i * hop + tn_recording + 1 ] #the [0] is the key 
        name = "%d" % i
        #print "inici", i * hop + 1, i * hop + tn_recording + 1 
        beginningData.append(i * hop + 1)
        lengthData.append(tn_recording)
        scNotes.id = name
        totScores.append(scNotes)  

    l = search.approximateNoteSearch(myScore.flat.notes, totScores)
#    print "printo prob", len(totScores)  
#    for i in l:
#        print i.id, i.matchProbability#, totScores[i]
        
    #decision process    
    if notePrediction > len(scoreNotes) - tn_recording - hop - 1:
        print "PETARIA", notePrediction, len(scoreNotes) - tn_recording - hop - 1, len(scoreNotes), tn_recording, hop
        notePrediction = len(scoreNotes) - tn_recording - hop - 1
        END_OF_SCORE = True
        print "************++++ LAST PART OF THE SCORE ++++**************"
    position, countdown = decisionProcess(l, notePrediction, beginningData, lastNotePosition, countdown)
        
    totalLength = 0
    
    number = int(l[position].id)
    result.append(l[number])
    #print "APPEND", l[number]
    #print "TROS SCORE", lengthData[number], "LEN DATA[number]", len(totScores[number]), "length totScores[number]"

#    for t in range(len(totScores[number])):
#        print totScores[number][t]
#    print "beginningData", beginningData[number], "lenTotScores"
    for i in range(len(totScores[number])):
        totalLength = totalLength + totScores[number][i].quarterLength

    if countdown == 0:   
        lastNotePosition = beginningData[number] + lengthData[number] #- 1
    if lastNotePosition < len(scoreNotes) / 4:
        print "--------------------------1", lastNotePosition, len(scoreNotes) / 4, len(scoreNotes)
    elif lastNotePosition < len(scoreNotes) / 2:
        print "--------------------------2", lastNotePosition, len(scoreNotes) / 2, len(scoreNotes)
    elif lastNotePosition < len(scoreNotes) * 3 / 4:
        print "--------------------------2", lastNotePosition, len(scoreNotes) * 3 / 4, len(scoreNotes)
    else: 
        print "--------------------------2", lastNotePosition, len(scoreNotes), len(scoreNotes)
        
    return totalLength, lastNotePosition, l[0].matchProbability, END_OF_SCORE, result, countdown
    
class AudioSearchException(music21.Music21Exception):
    pass

#------------------------------------------
class Test(unittest.TestCase):
    
    def runTest(self):
        pass


#-------------------------------------------------------------------------------
# define presented order in documentation
_DOC_ORDER = []


if __name__ == "__main__":
    music21.mainTest(Test)


#------------------------------------------------------------------------------
# eof
