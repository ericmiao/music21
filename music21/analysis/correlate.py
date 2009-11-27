#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:         correlate.py
# Purpose:      Stream analyizer designed to correlate and graph two properties
#
# Authors:      Christopher Ariza
#               Michael Scott Cuthbert
#
# Copyright:    (c) 2009 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------

import unittest, doctest, random
import sys

import music21
from music21 import common
from music21 import converter
from music21 import stream
from music21 import note
from music21 import dynamics
from music21 import pitch
from music21 import duration

from music21.analysis import graph

from music21 import environment
_MOD = 'correlate.py'
environLocal = environment.Environment(_MOD)








#-------------------------------------------------------------------------------
class CorrelateException(Exception):
    pass



#-------------------------------------------------------------------------------
# utilities for getting ticks

def ticksPitchSpace(pitchMin=36, pitchMax=100):
    ticks = []
    cVals = range(pitchMin,pitchMax,12)
    for i in cVals:
        name, acc = pitch.convertPsToStep(i)
        oct = pitch.convertPsToOct(i)
        ticks.append([i, '%s%s' % (name, oct)])
    return ticks

def ticksQuarterLength():
    ticks = []
    for qLen in (.25, .5, 1, 2, 4):
        # dtype, match = duration.
        # ticks.append([qLen, dc.convertQuarterLengthToType(qLen)]) 
        ticks.append([qLen, duration.Duration(qLen).type]) 
    return ticks

def ticksDynamics():
    ticks = []
    for i in range(len(dynamics.shortNames)):
        ticks.append([i, dynamics.shortNames[i]])
    return ticks



#-------------------------------------------------------------------------------
class ActivityMatch(object):

    '''Given a stream of note, find what other parameter is active at agiven time
    '''

    def __init__(self, streamObj):
        if not isinstance(streamObj, music21.stream.Stream):
            raise CorrelateException, 'non-stream provided as argument'
        self.streamObj = streamObj
        self.data = None


    def scatterGraph(self, fx=None, fy=None, *args, **keywords):
        # need a list of durations for each pitch, and a count of each duration
        '''
        Provide two functions that process an entity to return 
        the data to be analyzed
        '''
        if 'xLabel' in keywords:
            xLabel = keywords['xLabel']
        else: xLabel = None
        if 'yLabel' in keywords:
            yLabel = keywords['yLabel']
        else: yLabel = None
        if 'xTicks' in keywords:
            xTicks = keywords['xTicks']
        else: xTicks = None
        if 'yTicks' in keywords:
            yTicks = keywords['yTicks']
        else: yTicks = None
        if 'title' in keywords:
            title = keywords['title']
        else: title = None

        pairs = []
        for entry in self.data:
            entrySrc = entry['src']
            # there may be multiple dst:
            for entryDst in entry['dst']:
                pairs.append([fx(entrySrc), fy(entryDst)])

        xVals = [x for x,y in pairs]
        yVals = [y for x,y in pairs]

        g = graph.Graph2DScatter(**keywords)
        g.setData(pairs)
        g.setAxisLabel('y', yLabel)
        g.setAxisRange('y', (min(yVals)-1, max(yVals)+1), pad=True)
        g.setAxisLabel('x', xLabel)
        g.setAxisRange('x', (min(xVals)-1, max(xVals)+1), pad=True)
        g.setTicks('x', xTicks)
        g.setTicks('y', yTicks)

        g.process()


    def findActive(self, objNameSrc=None, objNameDst=None):
        '''
        returns an ordered list of dictionaries, in the form
        {'src': obj, 'dst': [objs]}

        '''        
        if objNameSrc == None:
            objNameSrc = note.Note
        if objNameDst == None:
            objNameDst = dynamics.Dynamic

        post = []
        streamFlat = self.streamObj.flat

        streamFlat = streamFlat.extendDuration(objNameDst)

        # get each src object; create a dictionary for each
        for element in streamFlat.getElementsByClass(objNameSrc):
            post.append({'src':element, 'dst':[]})

        # get each dst object, and find its start and end time
        # then, go through each source object, and see if this
        # dst object is within the source objects boundaries
        # if so, append it to the source object's dictionary
        for element in streamFlat.getElementsByClass(objNameDst):
            #print _MOD, 'dst', element
            dstStart = element.offset
            dstEnd = dstStart + element.duration.quarterLength

            for entry in post:
                # here, we are only looking if start times match
                if (entry['src'].offset >= dstStart and 
                    entry['src'].offset <= dstEnd):
                    # this is match; add a reference to the element
                    entry['dst'].append(element)            
                
        self.data = post


    def pitchToDynamic(self, *args, **keywords):
        '''
        '''
        objNameSrc = note.Note
        objNameDst = dynamics.Dynamic

        self.findActive(objNameSrc, objNameDst)

        fx = lambda e: e.midi
        xLabel = 'Pitch'
        xTicks = ticksPitchSpace()

        # need to store index position in shortNames list
        # as this is a number
        fy = lambda e: dynamics.shortNames.index(e.value)
        yLabel = 'Dynamics'
        # ticks here is the same index as used to get the values in fy
        # thus, the symbolc values can be seen clearly based on the numical 
        # representation
        yTicks = ticksDynamics()

        self.scatterGraph(fx, fy, xLabel=xLabel, yLabel=yLabel, 
                                  yTicks=yTicks, xTicks=xTicks, **keywords)





#-------------------------------------------------------------------------------
class NoteAnalysis(object):
    '''A collection of utilites for graphing and displaying attributes of notes
    '''
    def __init__(self, streamObj):
        if not isinstance(streamObj, music21.stream.Stream):
            raise CorrelateException, 'non-stream provided as argument'
        self.streamObj = streamObj
    


# ignoreMissing (which is set by default) means that if an element in the stream
# does not have one or both of the methods, it is ignored. ignoreNonNumeric
# ignores an element if either method returns a non-numeric response. If set to
# false, raises an error. (eventually we should have a default value that can be
# set instead).


# coefficient: returns the correlation coefficient. This is the actual answer to
# the question.
# lineSlope: returns the slope of the best linear fit
# lineYIntercept: returns the y-intercept of the best linear fit.
# scatterPlot: returns a scatterplot of the results (optional arguments would
# change the display)
# scatterPlotLine: returns a scatterplot of the results with the best fit line
# overlaid


    def _autoLambda(self, valueStr):
        '''If a user provudes a string instea of a lambda expression, assume 
        that it is a method of a note object
        '''
        #if common.isStr(value):
        label = valueStr
        lambdaExp = lambda n: getattr(n, valueStr)
        return lambdaExp, label        


    def noteAttributeCount(self, fx=None, fy=None, *args, **keywords):
        '''A 3d dimensional graph, of two paramters, with counts of the second parameters

        >>> a = stream.Stream()
        >>> b = NoteAnalysis(a)
        '''
        xLabel = None
        yLabel = None

        if fy == None:
            fy = lambda n: n.midi
            yLabel = 'MIDI Note Number'
        elif common.isStr(fy):
            fy, yLabel = self._autoLambda(fy)

        if fx == None:
            fx = lambda n:n.quarterLength
            xLabel = 'Quarter Length'
        elif common.isStr(fx):
            fx, xLabel = self._autoLambda(fx)

        if 'xLabel' in keywords:
            xLabel = keywords['xLabel']
        if 'yLabel' in keywords:
            yLabel = keywords['yLabel']
        if 'xTicks' in keywords:
            xTicks = keywords['xTicks']
        else: xTicks = None
        if 'yTicks' in keywords:
            yTicks = keywords['yTicks']
        else: yTicks = None
        if 'title' in keywords:
            title = keywords['title']
        else: title = None




        # need a list of durations for each pitch, and a count of each duration
        #qLenPos = [x*.25 for x in range(1,10)]
        data = {}
        xValues = []
        yValues = []
        for noteObj in self.streamObj.getElementsByClass(note.Note,
                                     unpackElement=True):
            x = fx(noteObj)
            if x not in xValues:
                xValues.append(x)
            y = fy(noteObj)
            if y not in yValues:
                yValues.append(y)
        xValues.sort()
        yValues.sort()
        # prepare data dictionary; need to pack all values
        # need to provide spacings even for zero values
        #for y in range(yValues[0], yValues[-1]+1):
        # better to use actual y values
        for y in yValues:
            data[y] = [[x, 0] for x in xValues]
        #print _MOD, 'data keys', data.keys()

        maxCount = 0
        for noteObj in self.streamObj.getElementsByClass(note.Note,
                                     unpackElement=True):
            indexToIncrement = xValues.index(fx(noteObj))
            # second position stores increment
            #print _MOD, fy(noteObj), indexToIncrement

            data[fy(noteObj)][indexToIncrement][1] += 1
            if data[fy(noteObj)][indexToIncrement][1] > maxCount:
                maxCount = data[fy(noteObj)][indexToIncrement][1] 


        g = graph.Graph3DPolygonBars(**keywords)
        g.setData(data)

        # this actually appears as the w
        g.setAxisRange('z', (0, maxCount))
        g.setAxisLabel('z', 'Count')
        # thi actually appearsa as the z
        g.setAxisRange('y', (yValues[0], yValues[-1]))
        g.setAxisLabel('y', yLabel)
        g.setAxisRange('x', (xValues[0], xValues[-1]))
        g.setAxisLabel('x', xLabel)
        g.process()


    def noteAttributeScatter(self, fx=None, fy=None, *args, **keywords):
        # need a list of durations for each pitch, and a count of each duration
        '''
        Provide two functions that process a noteObj and return the data
        to be analyzed
        '''
        xLabel = None
        yLabel = None

        if fy == None:
            fy = lambda n: n.midi
            yLabel = 'MIDI Note Number'
        elif common.isStr(fy):
            fy, yLabel = self._autoLambda(fy)

        if fx == None:
            fx = lambda n:n.quarterLength
            xLabel = 'Quarter Length'
        elif common.isStr(fx):
            fx, xLabel = self._autoLambda(fx)


        if 'xLabel' in keywords:
            xLabel = keywords['xLabel']
        if 'yLabel' in keywords:
            yLabel = keywords['yLabel']
        if 'xTicks' in keywords:
            xTicks = keywords['xTicks']
        else: xTicks = None
        if 'yTicks' in keywords:
            yTicks = keywords['yTicks']
        else: yTicks = None
        if 'title' in keywords:
            title = keywords['title']
        else: title = None

        data = []
        for noteObj in self.streamObj.getElementsByClass(note.Note,
                                     unpackElement=True):
            data.append([fx(noteObj), fy(noteObj)])

        xVals = [x for x,y in data]
        yVals = [y for x,y in data]

        g = graph.Graph2DScatter(**keywords)
        g.setData(data)
        g.setAxisLabel('y', yLabel)
        g.setAxisRange('y', (min(yVals)-1, max(yVals)+1), pad=True)
        g.setAxisLabel('x', xLabel)
        g.setAxisRange('x', (min(xVals)-1, max(xVals)+1), pad=True)
        g.setTicks('x', xTicks)
        g.setTicks('y', yTicks)
        g.setTitle(title)

        g.process()

    def pitchToLengthScatter(self, **keywords):
        if not 'xLabel' in keywords:
            keywords['xLabel'] = 'Duration'
        if not 'yLabel' in keywords:
            keywords['yLabel'] = 'Pitch'
        if not 'xTicks' in keywords:
            keywords['xTicks'] = ticksQuarterLength()
        if not 'yTicks' in keywords:
            keywords['yTicks'] = ticksPitchSpace()

        return self.noteAttributeScatter('quarterLength', 'midi', **keywords)


    def noteAttributeHistogram(self, fx=None, *args, **keywords):
        # need a list of durations for each pitch, and a count of each duration
        '''
        Provide two functions that process a noteObj and return the data
        to be analyzed
        '''

        xLabel = None
        yLabel = None

        if fx == None:
            fx = lambda n:n.midi
            xLabel = 'Pitch'
        elif common.isStr(fx):
            fx, xLabel = self._autoLambda(fx)

        if 'xLabel' in keywords:
            xLabel = keywords['xLabel']
        else: xLabel = None
        if 'yLabel' in keywords:
            yLabel = keywords['yLabel']
        else: yLabel = None

        if 'fxTick' in keywords:
            fxTick = keywords['fxTick']
            if common.isStr(fxTick):
                fxTick, junk = self._autoLambda(fxTick)
        else: fxTick = lambda n: n.nameWithOctave

        if 'title' in keywords:
            title = keywords['title']
        else: title = None


        data = {}
        dataTick = {}

        for noteObj in self.streamObj.getElementsByClass(note.Note,
                                     unpackElement=True):
            value = fx(noteObj)
            if value not in data.keys():
                data[value] = 0
                # this is the offset that is used to shift labels
                # into bars; this only is .5 if x values are integers 
                dataTick[value+.4] = fxTick(noteObj)
            data[value] += 1
        data = data.items()
        data.sort()

        dataTick = dataTick.items()
        dataTick.sort()

        g = graph.Graph2DHistogram(**keywords)
        g.setData(data) # convert to pairs
        g.setTicks('x', dataTick)
        g.setAxisLabel('x', xLabel)
        g.setAxisLabel('y', yLabel)
        g.setTitle(title)

        g.process()


















#-------------------------------------------------------------------------------

class TestExternal(unittest.TestCase):

    def runTest(self):
        pass


    def testStreamAttributeCount(self):
        from music21.musicxml import testFiles
        mxString = testFiles.ALL[1]
        a = converter.parse(mxString)
        a = NoteAnalysis(a.flat)
        a.noteAttributeCount(colors=['#aa46ff'], barWidth=.1, alpha=.7)

    
    def testStreamScatter(self):

        from music21.musicxml import testFiles
        mxString = testFiles.ALL[1]
#         a = stream.Score()
#         a.read(mxString)
        a = converter.parse(mxString)
        #a.loadPart('P1')
        b = NoteAnalysis(a.flat)

        fx = lambda n: n.quarterLength
        fy = lambda n: n.diatonicNoteNum
        b.noteAttributeScatter(fx, fy, 'ql', 'dnn')

        b = NoteAnalysis(a.flat)
        fx = lambda n: n.quarterLength
        fy = lambda n: n.midi
        b.noteAttributeScatter(fx, fy, 'ql', 'midi')


    def testStreamHistogram(self):

        from music21.musicxml import testFiles
        mxString = testFiles.ALL[1]
        a = converter.parse(mxString)

#         a = stream.Score()
#         a.read(mxString)
#         a.loadPart('P1')
#         a.loadPart('P2')
        #print a.getGroups()

        b = NoteAnalysis(a.getElementsByGroup('P1').flat)

        fx = lambda n: n.midi
        xLabel = 'Pitch'
        fxTick = lambda n: n.nameWithOctave
        title = 'DICHTERLIEBE 1. Im wunder...'
        b.noteAttributeHistogram(fx, xLabel=xLabel, fxTick=fxTick, title=title)

#         fx = lambda n: n.pitchClass
#         xLabel = 'Pitch Class'
#         fxTick = lambda n: n.name
#         title = 'DICHTERLIEBE 1. Im wunder...'
#         b.noteAttributeHistogram(fx, xLabel=xLabel, fxTick=fxTick, title=title)

    def processHistogram(self, fp=None, parameter='midi'):
        '''create a histogram from an external file'''
#         a = stream.Score()
        from music21 import corpus
        if fp == None:
            fp = corpus.mozart[0]

        a = converter.parse(fp)

#         a.open(fp)
#         a.load() # loads all parts
        b = NoteAnalysis(a.flat)

        if parameter == 'midi':
            fx = lambda n: n.midi
            xLabel = 'MIDI Pitch'
            fxTick = lambda n: n.nameWithOctave
        elif parameter == 'pc':
            fx = lambda n: n.pitchClass
            xLabel = 'Pitch Class'
            fxTick = lambda n: n.name

        elif parameter == 'ql':
            fx = lambda n: n.quarterLength
            xLabel = 'Quarter Length'
            fxTick = lambda n: n.quarterLength

        b.noteAttributeHistogram(fx, xLabel=xLabel, fxTick=fxTick)


    def testActivityMatchPitchToDynamic(self):
        from music21 import corpus
        # note: this causes an error
        # third movement is the smallest


        # third movements
        a = converter.parse(corpus.getWork('opus18no1')[2])
        #a = converter.parse(mxString)
        b = ActivityMatch(a.flat.sorted)
        b.pitchToDynamic()



class Test(unittest.TestCase):

    def runTest(self):
        pass


    def testBasic(self):

        from music21.musicxml import testFiles 
        mxString = testFiles.ALL[1]
        a = converter.parse(mxString)

        from music21.musicxml import testFiles

        mxString = testFiles.ALL[0]
        a = converter.parse(mxString)
        b = NoteAnalysis(a)




#-------------------------------------------------------------------------------
if __name__ == "__main__":

    if len(sys.argv) == 1:
        music21.mainTest(Test)

    elif len(sys.argv) == 3:
        t = TestExternal()
        # provide file path, output
        t.processHistogram(sys.argv[1], sys.argv[2])

