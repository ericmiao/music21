# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         medren.py
# Purpose:      classes for dealing with medieval and Renaissance Music
#
# Authors:      Michael Scott Cuthbert
#
# Copyright:    (c) 2011 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------
'''
Tools for working with medieval and Renaissance music -- see also the 
trecento directory which works particularly on 14th-century Italian
music.
'''
import copy
import music21
from music21 import common
from music21 import duration
from music21 import interval
from music21 import meter
from music21 import note
from music21 import tempo
import unittest, doctest

allowableStrettoIntervals = { 
        -8: [(3, True), 
             (-3, True),
             (5, False),
             (-4, False),
             (1, True)],
        8:  [(3, True), 
             (-3, True),
             (5, False),
             (4, False),
             (1, True)],
        -5: [(-3, True), 
             (-5, False),
             (2, True),
             (4, False),
             (1, True)],
        5:  [(3, True), 
             (5, False),
             (-2, True),
             (-4, False),
             (1, True)],
        -4: [(3, True), 
             (5, False),
             (2, False),
             (-2, True),
             (-4, False)],
        4:  [(-3, True), 
             (-5, False),
             (2, True),
             (-2, False),
             (4, False)],
    }

_validDivisiones = {(None, None):0, ('quaternaria','.q.'):4, ('senaria imperfecta', '.i.'):6, ('senaria perfecta', '.p.'):6, ('novenaria', '.n.'):9, ('octonaria', '.o.'):8, ('duodenaria', '.d.'):12}

_validMensuralTypes = [None,'maxima', 'longa', 'brevis', 'semibrevis', 'minima', 'semiminima']
_validMensuralAbbr = [None, 'Mx', 'L', 'B', 'SB', 'M', 'SM']
      
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------   
def _evaluateMeasure(mOrD, measure, lengths):
        ''':meth:`music21.medren._evaluateMeasure takes a mensuration or divisione, a measure's worth of mensural objects in a list, and a list of lengths corresponding to each of those objects as arguments.
        This method returns the ``strength'' of the measure based on those lengths. A ``strong'' measure has longer notes on its stronger beats. Only valid for Italian notation.'''
    
        typeStrength = {'semibrevis': 1.0, 'minima': 0.5, 'semiminima':0.25}
           
        beatStrength = 0
        strength = 0
        curBeat = 0
        for i in range(len(lengths)):
            if abs(curBeat - round(curBeat)) < 0.0001: #Rounding error
                curBeat = round(curBeat)
            
            if mOrD.standardSymbol in ['.i.', '.n.']:
                if abs(curBeat % 3) < 0.0001:
                    beatStrength = 1.0
                elif curBeat % 3 - 1 or i % 3 == 2:
                    beatStrength = float(1.0)/3
                else:
                    beatStrength = float(1.0)/9
            elif mOrD.standardSymbol in ['.q.', '.o.', '.d.']:
                if curBeat % 4 == 0:
                    beatStrength = 1.0
                elif curBeat % 4 == 2:
                    beatStrength = 0.5
                elif curBeat % 2 == 1:
                    beatStrength = 0.25
                else:
                    beatStrength = 0.125
            else:
                if curBeat % 6 == 0:
                    beatStrength = 1.0
                elif curBeat % 2 == 0 and curBeat % 3 != 0:
                    beatStrength = 0.5
                elif curBeat % 2 == 1:
                    beatStrength = 0.25
                else:
                    beatStrength = 0.125
            strength += typeStrength[measure[i].mensuralType]*beatStrength
            curBeat += lengths[i]
        strength -= abs(mOrD.minimaPerMeasure - curBeat)
        return strength

def _getTargetBeforeOrAtObj(music21Obj, targetClassList):
    '''
    Takes two arguments: music21Obj, targetObj
    If music21Obj has some set of context, returns the list of targetClass at or before music21Obj.
    If no such instance exists, of if the only context is None, returns None.
    NOTE: This has no other use than to act as an alternate way of getting the closest instance of a mensuration or divisione for :class:`music21.medren.GeneralMensuralNote`. 
    
    >>> from music21 import *
    >>> n = note.Note('A')
    >>> medren._getTargetBeforeOrAtObj(n, note.Note)
    []
    >>> n_1 = note.Note('B')
    >>> n_1.duration = duration.Duration(2.5)
    >>> n_2 = note.Note('C')
    >>> n_2.duration = duration.Duration(0.5)
    >>> s_1 = stream.Stream()
    >>> s_1.append(n_1)
    >>> s_1.append(n)
    >>> s_1.append(n_2)
    >>> medren._getTargetBeforeOrAtObj(n, note.Note)
    [<music21.note.Note B>, <music21.note.Note A>]
    >>> n_3 = note.Note('D')
    >>> n_3.duration = duration.Duration(1.0)
    >>> n_4 = note.Note('E')
    >>> n_4.duration = duration.Duration(1.5)
    >>> m = stream.Measure()
    >>> m.append(n_3)
    >>> m.append(n)
    >>> s = stream.Score()
    >>> s.append(n_4)
    >>> s.append(meter.TimeSignature())
    >>> s.append(m)
    >>> medren._getTargetBeforeOrAtObj(n, meter.TimeSignature)
    [<music21.meter.TimeSignature 4/4>]
    '''
    #Get contacts by class
    #Improve efficiency
    cList = []
    
    if not isinstance(targetClassList, list):
        targetClassList = [targetClassList]
    
    tempSites = music21Obj.getSites()[1:]
    if len(tempSites) > 0:
        for s in tempSites:
            for i in range(int(s.lowestOffset), int(s.getOffsetByElement(music21Obj))+1):
                cList += s.getElementsByOffset(i, i+1, classList = targetClassList).recurse()[1:]
        cList += music21.medren._getTargetBeforeOrAtObj(s, targetClassList)
    
    return list(set(cList))


class _TranslateMensuralMeasure:
    '''
    The class :class:`music21.medren._TranslateMensuralMeasure` takes a mensuration or divisione sign and a list comprising one measure's worth of mensural objects as arguments.
    The method :meth:`music21.medren._TranslateMensuralMeasure.getMinimaLengths` takes no arguments, and returns a list of floats corresponding to the length (in minima) of each object in the measure.
    The methods :meth:`music21.medren._TranslateMensuralMeasure._getLengthsItalian` and :meth:`music21.medren._getLengthsFrench` are there simply to aid :meth:`music21.medren._TranslateMensuralMeasure.getMinimaLengths`.
    Currently, this class is used only to improve the efficiency of :attr:`music21.medren.GeneralMensuralNote.duration`.
    
    Note: French notation and dragmas currently not supported.
    
    >>> from music21 import *
    >>> mOrD = medren.Divisione('.i.')
    >>> names = ['SB', 'M', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [2.0, 1.0, 3.0]
    >>>
    >>>
    >>> mOrD = medren.Divisione('.n.')
    >>> names = ['SB', 'M', 'M', 'M', 'SB', 'M']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [3.0, 1.0, 1.0, 1.0, 2.0, 1.0]
    >>> names = ['SB', 'M', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [2.0, 1.0, 6.0]
    >>> measure[0].setStem('down')
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [5.0, 1.0, 3.0]
    >>>
    >>>
    >>> mOrD = medren.Divisione('.q.')
    >>> names = ['M', 'SM', 'SM', 'SM', 'SM', 'SM']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> measure[4] = medren.MensuralRest('SM')
    >>> measure[1].setFlag('up','left')
    >>> measure[2].setFlag('up', 'left')
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [1.0, 0.5, 0.5, 0.66666666666666663, 0.66666666666666663, 0.66666666666666663]
    >>>
    >>>
    >>> mOrD = medren.Divisione('.p.')
    >>> names = ['M', 'SB', 'SM', 'SM']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> measure[1].setStem('down')
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [1.0, 4.0, 0.5, 0.5]
    >>> names = ['SM', 'SM', 'SM', 'SM', 'SM', 'SM', 'SM', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> measure[3] = medren.MensuralRest('SM')
    >>> for mn in measure[:3]:
    ...    mn.setFlag('up', 'left')
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [0.66666666666666663, 0.66666666666666663, 0.66666666666666663, 0.5, 0.5, 0.5, 0.5, 2.0]
    >>>
    >>>
    >>> mOrD = medren.Divisione('.o.')
    >>> names = ['SB', 'SB', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> measure[1].setStem('down')
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [2.0, 4.0, 2.0]
    >>> names = ['SM', 'SM', 'SM', 'SB', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [0.66666666666666663, 0.66666666666666663, 0.66666666666666663, 2.0, 4.0]
    >>>
    >>>
    >>> mOrD = medren.Divisione('.d.')
    >>> names = ['SB', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [4.0, 8.0]
    >>> names = ['SB', 'SB', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [4.0, 4.0, 4.0]
    >>> names = ['SB', 'SB', 'SB', 'SB']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [2.0, 2.0, 4.0, 4.0]
    >>> measure[1].setStem('down')
    >>> measure[2].setStem('down')
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [2.0, 4.0, 4.0, 2.0]
    >>> names = ['SM', 'SM', 'SM', 'SM', 'SB', 'SB', 'SB', 'SB', 'SB', 'SM', 'SM', 'SM']
    >>> measure = [medren.MensuralNote('A', n) for n in names]
    >>> measure[3] = medren.MensuralRest('SM')
    >>> for mn in measure[-3:]:
    ...    mn.setFlag('up', 'left')
    >>> for mn in measure[4:9]:
    ...    mn.setStem('down')
    >>> TMM = medren._TranslateMensuralMeasure(mOrD, measure)
    >>> TMM.getMinimaLengths()
    [0.5, 0.5, 0.5, 0.5, 4.0, 4.0, 4.0, 4.0, 4.0, 0.66666666666666663, 0.66666666666666663, 0.66666666666666663]
    '''
    
    def __init__(self, mensurationOrDivisione = None, measure = [], pDS = False):
                
        self.mOrD = mensurationOrDivisione
        self.mensuralMeasure = measure
        self.minimaLengthList = [0 for i in range(len(self.mensuralMeasure))]
        
        self.processing_downstems = pDS
        
    def getMinimaLengths(self):
        if isinstance(self.mOrD, music21.medren.Divisione):
           self.minimaLengthList = self._getLengthsItalian()
        elif isinstance(self.mOrD, music21.medren.Mensuration):
           self.minimaLengthList = self._getLengthsFrench()
        else:
           raise MedRenException('%s not recognized as mensuration or divisione' % mensurationOrDivisione)
        return self.minimaLengthList
       
    def _getLengthsItalian(self):
        #########################################################################################################################################
            
        def processMeasure(measure, lengths, change_list, change_nums, diff_list, lenRem, releases = None, multi = 0):
            '''
            Gets all possible length combinations. Returns the lengths combination of the "strongest" measure, along with the remaining length in the measure. 
            '''
            
            def allCombinations(list, num):
                combs = [[]]
                if num > 0:
                    for i in range(len(list)):
                        comb = [list[i]]
                        for c in allCombinations(list[(i+1):], num-1):
                            combs.append(comb + c)
                combs.reverse()
                return combs
            
            if isinstance(change_list, tuple):
                change = change_list[0]
            else:
                change = change_list
            if isinstance(change_nums, tuple):
                change_num = change_nums[0]
            else:
                change_num = change_nums
            if isinstance(diff_list, tuple):
                diff = diff_list[0]
            else:
                diff = diff_list
            if releases is not None and isinstance(releases, list):
                release = releases[0]
            else:
                release = releases
                
            strength = music21.medren._evaluateMeasure(self.mOrD, measure, lengths)
            lengths_changeable = lengths[:]
            lengths_static = lengths[:]
            remain = lenRem
            lenRem_final  = lenRem
            
            if multi == 0:
                for l in allCombinations(change, change_num):
                    l.reverse()
                    for i in l:
                        lengths_changeable[i] += diff
                        if release is not None:
                            lengths_changeable[release] -= diff
                        else:
                            remain -= diff
        
                    newStrength = music21.medren._evaluateMeasure(self.mOrD, measure, lengths_changeable)
                    if strength < newStrength and remain >= 0:
                        lengths = lengths_changeable[:]
                        strength = newStrength
                        lenRem_final = remain
                    lengths_changeable = lengths_static[:]
                    remain = lenRem
                return lengths, lenRem_final
            
            else:
                for l in allCombinations(change, change_num):
                    l.reverse()
                    for i in l:
                        lengths_changeable[i] += diff
                        if release is not None:
                            lengths_changeable[release] -= diff
                            lengths_changeable, remain = processMeasure(measure, lengths_changeable, change_list[1:], change_nums[1:], diff_list[1:], remain, releases[1:], multi-1)
                        else:
                            remain -= diff
                            lengths_changeable, remain = processMeasure(measure, lengths_changeable, change_list[1:], change_nums[1:], diff_list[1:], remain, multi-1)
                    
                    newStrength = music21.medren._evaluateMeasure(self.mOrD, measure, lengths_changeable)
                    if strength < newStrength and remain >= 0:
                        lengths = lengths_changeable[:]
                        strength = newStrength
                        lenRem_final = remain
                    lengths_changeable = lengths_static[:]
                    remain = lenRem
                return lengths, lenRem_final
        
        ##################################################################################################################################
            
        minRem = self.mOrD.minimaPerMeasure
        minRem_tracker = self.processing_downstems
        minimaLengths = self.minimaLengthList[:]
        
        semibrevis_list = []
        semibrevis_downstem = []
        
        semiminima_right_flag_list = []
        semiminima_left_flag_list = []
        semiminima_rest_list = []
        
        #Don't need these yet
        #===================================================================
        # dragmas_no_flag = []
        # dragmas_RNo_flag = []
        # dragmas_LNo_flag = []
        # dragmas_NoR_flag = []
        # dragmas_RR_flag = []
        # dragmas_RL_flag = []
        # dragmas_LR_flag = []
        # dragmas_LL_flag = []
        #===================================================================

        for i in range(len(self.mensuralMeasure)):
            obj = self.mensuralMeasure[i]
            minimaLength = 0
            #If its duration is set, doesn't need to be determined
            
            #Gets rid of everything known 
            if obj.mensuralType == 'maxima':
                minimaLength = float(4)*self.mOrD.minimaPerMeasure
            elif obj.mensuralType == 'longa':
                minimaLength = float(2)*self.mOrD.minimaPerMeasure
            elif obj.mensuralType == 'brevis':
                minimaLength = float(self.mOrD.minimaPerMeasure)
            elif minimaLengths[i] == 0 and \
            ( isinstance(obj, music21.medren.MensuralNote) or isinstance(obj, music21.medren.MensuralRest) ):
                #Dep on mOrD
                if obj.mensuralType == 'semibrevis':
                    if isinstance(obj, music21.medren.MensuralRest):
                        if self.mOrD.standardSymbol in ['.q.', '.i.']:
                            minimaLength = self.mOrD.minimaPerMeasure/float(2)
                        elif self.mOrD.standardSymbol in ['.p.', '.n.']:
                            minimaLength = self.mOrD.minimaPerMeasure/float(3)
                        else: 
                            semibrevis_list.append(i)
                    else:
                        if 'side' in obj.getStems():
                            minimaLength = 3.0
                        elif 'down' in obj.getStems():
                            semibrevis_downstem.append(i)
                        else:
                            semibrevis_list.append(i)
                if obj.mensuralType == 'minima':
                    if isinstance(obj, music21.medren.MensuralNote) and 'down' in obj.stems:
                        raise MedRenException('Dragmas currently not supported')
                    elif isinstance(obj, music21.medren.MensuralNote) and 'side' in obj.stems:
                        minimaLength = 1.5
                    else:
                        minimaLength = 1.0
                if obj.mensuralType == 'semiminima':
                    if isinstance(obj, music21.medren.MensuralNote):
                        if 'down' in obj.getStems():
                            raise MedRenException('Dragmas currently not supported')
                        elif obj.getFlags()['up'] == 'right':
                            semiminima_right_flag_list.append(i)
                        elif obj.getFlags()['up'] == 'left':
                            semiminima_left_flag_list.append(i)
                    if isinstance(obj, music21.medren.MensuralRest):
                        semiminima_rest_list.append(i) 
                minRem -= minimaLength
            minimaLengths[i] = minimaLength

        #Process everything else           
        if self.mOrD.standardSymbol == '.i.':
            if len(semibrevis_list) > 0:
                avgSBLength = minRem/len(semibrevis_list)
                for ind in semibrevis_list:
                    if avgSBLength == 2:
                        minimaLengths[ind] = 2.0
                        minRem -= 2.0
                    elif (2 < avgSBLength) and (avgSBLength < 3):
                        if ind < (len(self.mensuralMeasure)-1) and self.mensuralMeasure[ind+1].mensuralType == 'minima':
                            minimaLengths[ind] = 2.0
                            minRem -= 2.0
                        else:
                            minimaLengths[ind] = 3.0
                            minRem -= 3.0
                    elif avgSBLength == 3.0:
                        minimaLengths[ind] = 3.0
                        minRem -= 3.0
            minRem_tracker = minRem_tracker or (minRem > -0.0001) 
        
        elif self.mOrD.standardSymbol == '.n.':
            extend_list = [] #brevises able to be lengthened
            extend_num = 0
            if len(semibrevis_list) > 0:
                if semibrevis_list[-1] == (len(self.mensuralMeasure) - 1) and len(semibrevis_downstem) == 0:
                    for ind in semibrevis_list[:-1]:
                        if self.mensuralMeasure[ind+1].mensuralType == 'minima':
                            minimaLengths[ind] = 2.0
                            minRem -= 2.0
                            extend_list.append(ind)
                        else:
                            minimaLengths[ind] = 3.0
                            minRem -= 3.0
                    minimaLengths[-1] = max(minRem, 3.0)
                    minRem -= max(minRem, 3.0)
            
                    extend_num = min(minimaLengths[-1] - 3, len(extend_list))
                    if minRem >= 0:
                        minimaLengths, minRem = processMeasure(self.mensuralMeasure, minimaLengths, extend_list, extend_num, 1,  minRem, releases = -1)
                else:
                    for ind in semibrevis_list:
                        if ind < (len(self.mensuralMeasure)-1) and self.mensuralMeasure[ind+1].mensuralType == 'minima':
                            minimaLengths[ind] = 2.0
                            minRem -= 2.0
                            extend_list.append(ind)
                        else:
                            minimaLengths[ind] = 3.0
                            minRem -= 3.0
                    if len(semibrevis_downstem) == 0:
                        extend_num = min(minRem, len(extend_list))
                        if minRem >= 0:
                            minimaLengths, minRem = processMeasure(self.mensuralMeasure, minimaLengths, extend_list, extend_num, 1, minRem)
                    else:
                        semibrevis_downstem = semibrevis_downstem[0]
                        minimaLengths[semibrevis_downstem] = max(minRem, 3.0)
                        minRem -= max(minRem, 3.0)
                        extend_num = min(minimaLengths[semibrevis_downstem] - 4, len(extend_list))
                        if semibrevis_downstem != len(self.mensuralMeasure) - 1:
                            if minRem >= 0:
                                minimaLengths, minRem = processMeasure(self.mensuralMeasure, minimaLengths, extend_list, extend_num, 1, minRem, releases = semibrevis_downstem)
                minRem_tracker = minRem_tracker or (minRem > -0.0001)
                        
        elif self.mOrD.standardSymbol == '.q.' or self.mOrD.standardSymbol == '.p.':
            extend_list = []
            extend_num = 0
            
            if len(semibrevis_downstem) == 0:
                semibrevis_downstem = None
            else: #Only room for one downstem per measure
                semibrevis_downstem = semibrevis_downstem[0] 
                
            for ind in semibrevis_list[:-1]:
                minimaLengths[ind] = 2.0
                minRem -= 2.0
            
            if semibrevis_downstem == (len(self.mensuralMeasure) - 1):
                for ind in semiminima_right_flag_list+semiminima_left_flag_list+semiminima_rest_list:
                    minimaLengths[ind] = 0.5
                    minRem -= 0.5
                minimaLengths[semibrevis_downstem] = minRem
                minRem = 0
            else:
                strength = 0
                minimaLengths_changeable = minimaLengths[:]
                minimaLengths_static = minimaLengths[:]
                minRem_changeable = minRem 
                minRem_static = minRem
                
                if len(semiminima_right_flag_list) > 0 and len(semiminima_left_flag_list) > 0:
                    lengths = [(0.5,0.5), (float(2)/3, 0.5), (0.5, float(2)/3), (float(2)/3, float(2)/3)]
    
                    for (left_length, right_length) in lengths:
                        for ind in semiminima_left_flag_list:
                            minimaLengths_changeable[ind] = left_length
                            minRem_changeable -= left_length
                        for ind in semiminima_right_flag_list:
                            minimaLengths_changeable[ind] = right_length
                            minRem_changeable -= right_length
                            
                        if left_length == right_length:
                            for ind in semiminima_rest_list:
                                minimaLengths_changeable[ind] = left_length
                                minRem_changeable -= left_length
                            if semibrevis_downstem is not None:
                                if len(semibrevis_list) > 0:
                                    minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                    minRem_changeable -= 2.0
                                minimaLengths_changeable[semibrevis_downstem] = max(2.0, minRem_changeable)
                                minRem_changeable -= max(2.0, minRem_changeable)
                            else:
                                if len(semibrevis_list) > 0 and semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                                    minimaLengths_changeable[semibrevis_list[-1]] = max(2.0, minRem_changeable)
                                    minRem_changeable -= max(2.0, minRem_changeable)
                                else:
                                    if len(semibrevis_list) > 0:
                                        minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                        minRem_changeable -= 2.0
                        else:
                            master_list = semiminima_left_flag_list + semiminima_right_flag_list + semiminima_rest_list
                            
                            for ind in semiminima_rest_list:
                                curIndex = int(master_list.index(ind))
                                if ( curIndex == 0 and master_list[curIndex+1] in semiminima_left_flag_list ) or \
                                     ( curIndex == len(master_list) - 1 and master_list[curIndex - 1] in semiminima_left_flag_list ) or \
                                     ( master_list[curIndex-1] in semiminima_left_flag_list and master_list[curIndex+1] in semiminima_left_flag_list ):
                                    minimaLengths_changeable[ind] = left_length
                                    minRem_changeable -= left_length
                                elif ( (curIndex == 0 and master_list[curIndex+1] in semiminima_right_flag_list) or
                                     (curIndex == len(master_list) - 1 and master_list[curIndex - 1] in semiminima_right_flag_list) or
                                     (master_list[curIndex-1] in semiminima_right_flag_list and master_list[curIndex+1] in semiminima_right_flag_list) ):
                                    minimaLengths_changeable[ind] = right_length
                                    minRem_changeable -= right_length
                                else:
                                    minimaLengths_changeable[ind] = 0.5
                                    extend_list.append(ind)
                                extend_list = list(set(extend_list)) #repeated iterations
                            
                            if semibrevis_downstem is not None:
                                if len(semibrevis_list) > 0:
                                    minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                    minRem_changeable -= 2.0
                                minimaLengths_changeable[semibrevis_downstem] = max(minRem_changeable, 2.0)
                                extend_num = min(6*minRem_changeable - 15.0, len(extend_list))
                                minRem_changeable -= max(minRem_changeable, 2.0)
                                if minRem_changeable >= 0:
                                    minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list, extend_num, float(1)/6, minRem_changeable, releases = semibrevis_downstem)
                            else:
                                if len(semibrevis_list) > 0 and semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                                    minimaLengths_changeable[semibrevis_list[-1]] = max(minRem_changeable, 2.0)
                                    extend_num = min(6*minRem_changeable - 12.0, len(extend_list))
                                    minRem_changeable -= max(minRem_changeable, 2.0)
                                    if minRem_changeable >= 0:
                                        minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list, extend_num, float(1)/6, minRem_changeable, releases = -1)
                                else:
                                    if len(semibrevis_list) > 0:
                                        minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                        minRem_changeable -= 2.0
                                    
                                    extend_num = len(extend_list)
                                    if minRem_changeable >= 0:
                                        minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list, extend_num, float(1)/6, minRem_changeable)                                      
                                    
                        tempStrength = music21.medren._evaluateMeasure(self.mOrD, self.mensuralMeasure, minimaLengths_changeable)      

                        if (tempStrength > strength) and (minRem_changeable > -0.0001): #Technically, >= 0, but rounding error occurs.
                            minimaLengths = minimaLengths_changeable[:]
                            minRem = minRem_changeable
                            strength = tempStrength
                        minimaLengths_changeable = minimaLengths_static
                        minRem_tracker = minRem_tracker or (minRem_changeable > -0.0001)
                        minRem_changeable = minRem_static
                        
                elif len(semiminima_left_flag_list) == 0 and len(semiminima_right_flag_list) == 0:
                    
                    if semibrevis_downstem is not None:
                        if len(semibrevis_list) > 0:
                            minimaLengths[semibrevis_list[-1]] = 2.0
                            minRem -= 2.0
                        minimaLengths[semibrevis_downstem] = max(minRem, 2.0)
                        minRem -= max(minRem, 2.0)
                    else:
                        if len(semibrevis_list) > 0 and semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                            minimaLengths[semibrevis_list[-1]] = max(minRem, 2.0)
                            minRem -= max(minRem, 2.0)
                        else:
                            if len(semibrevis_list) > 0:
                                minimaLengths[semibrevis_list[-1]] = 2.0
                                minRem -= 2.0
                    minRem_tracker = minRem_tracker or (minRem > -0.0001)            
                else:
                    lengths = [0.5, float(2)/3]
                    master_list = semiminima_left_flag_list + semiminima_right_flag_list + semiminima_rest_list
                    
                    for length in lengths:
                        for ind in master_list:
                            minimaLengths_changeable[ind] = length
                            minRem_changeable -= length
                        
                        if semibrevis_downstem is not None:
                            if len(semibrevis_list) > 0:
                                minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                minRem_changeable -= 2.0

                            minimaLengths_changeable[semibrevis_downstem] = minRem_changeable
                        else:
                            if len(semibrevis_list) > 0 and semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                                minimaLengths_changeable[semibrevis_list[-1]] = max(minRem_changeable, 2.0)
                                minRem_changeable -= max(minRem_changeable, 2.0)
                            else:
                                if len(semibrevis_list) > 0:
                                    minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                    minRem_changeable -= 2.0
                                    
                        tempStrength = music21.medren._evaluateMeasure(self.mOrD, self.mensuralMeasure, minimaLengths_changeable)
                        
                        if (tempStrength > strength) and (minRem_changeable > -0.0001):
                            minimaLengths = minimaLengths_changeable[:]
                            minRem = minRem_changeable
                            strength = tempStrength
                        minimaLengths_changeable = minimaLengths_static  
                        minRem_tracker = minRem_tracker or (minRem_changeable > -0.0001)   
                        minRem_changeable = minRem_static 
                        
        else:
            extend_list_1 = []
            extend_num_1 = 0
            extend_list_2 = []
            extend_num_2 = 0
            
            for ind in semibrevis_list[:-1]:
                minimaLengths[ind] = 2.0
                extend_list_1.append(ind)
                minRem -= 2.0
            
            minimaLengths_changeable = minimaLengths[:]
            minRem_changeable = minRem
            minimaLengths_static = minimaLengths[:]
            minRem_static = minRem
               
            if len(semibrevis_downstem) < 2:
                if len(semibrevis_downstem) > 0 and semibrevis_downstem[0] == len(self.mensuralMeasure) - 1:
                    for ind in semiminima_left_flag_list + semiminima_right_flag_list + semiminima_rest_list:
                        minimaLengths[ind] = 0.5
                        minRem -= 0.5
                    if len(semibrevis_list) > 0:
                        for ind in semibrevis_list:
                            minimaLengths[ind] = 2.0
                            minRem -= 2.0
                            extend_list_1.append(ind)
                    minimaLengths[semibrevis_downstem[0]] = max(minRem, 2.0)
                    minRem -= max(minRem, 2.0)
                else:
                    if len(semiminima_left_flag_list) > 0 and len(semiminima_right_flag_list) > 0:
                        lengths = [(0.5,0.5), (float(2)/3, 0.5), (0.5, float(2)/3), (float(2)/3, float(2)/3)]
                        strength = 0
    
                        for (left_length, right_length) in lengths:
                            
                            for ind in semiminima_left_flag_list:
                                minimaLengths_changeable[ind] = left_length
                                minRem_changeable -= left_length
                            for ind in semiminima_right_flag_list:
                                minimaLengths_changeable[ind] = right_length
                                minRem_changeable -= right_length
                            
                            if left_length == right_length:
                                for ind in semiminima_rest_list:
                                    minimaLengths_changeable[ind] = left_length
                                    minRem_changeable -= left_length
                                
                                if len(semibrevis_downstem) > 0:
                                    downstem = semibrevis_downstem[0]
                                    if len(semibrevis_list) > 0:
                                        minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                        extend_list_1.append(semibrevis_list[-1])
                                        extend_list_1 = list(set(extend_list_1)) #For repeated iterations
                                        minRem_changeable -= 2.0
                                    
                                    avgSBLen = minRem_changeable/len(semibrevis_list)
                                    extend_num_1 = min(len(extend_list_1), 0.5*minRem_changeable - 2.0)
                                    minimaLengths_changeable[downstem] = max(minRem_changeable, 4.0)
                                    minRem -= max(minRem_changeable, 4.0)
                                    
                                    minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_1, extend_num_1, 2.0, minRem_changeable, releases = downstem)
                                
                                else:
                                    if len(semibrevis_list) > 0:
                                        if semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                                            minimaLengths_changeable[semibrevis_list[-1]] = max(minRem_changeable, 2.0)
                                            extend_num_1 = min(len(extend_list_1), int(0.5*minRem_changeable - 1.0))
                                            minRem -= max(minRem_changeable, 2.0)
                                            
                                            if minRem >= 0:
                                                minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_1, extend_num_1, 2.0, minRem_changeable, releases = -1)
                                        else:
                                            minimaLengths[semibrevis_list[-1]] = 2.0
                                            extend_list_1.append(semibrevis_list[-1])
                                            extend_list_1 = list(set(extend_list_1))
                                            extend_num_1 = len(extend_list_1)
                                            minRem -= 2.0
                                            
                                            if minRem >= 0:
                                                minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_1, extend_num_1, 2.0, minRem_changeable)
                                
                            else:
                                master_list = semiminima_left_flag_list + semiminima_right_flag_list + semiminima_rest_list
                                
                                for ind in semiminima_rest_list:
                                    curIndex = int(master_list.index(ind))
                                    if ( curIndex == 0 and master_list[curIndex+1] in semiminima_left_flag_list ) or \
                                         ( curIndex == len(master_list) - 1 and master_list[curIndex - 1] in semiminima_left_flag_list ) or \
                                         ( master_list[curIndex-1] in semiminima_left_flag_list and master_list[curIndex+1] in semiminima_left_flag_list ):
                                        minimaLengths_changeable[ind] = left_length
                                        minRem_changeable -= left_length
                                    elif ( curIndex == 0 and master_list[curIndex+1] in semiminima_right_flag_list ) or \
                                         ( curIndex == len(master_list) - 1 and master_list[curIndex - 1] in semiminima_right_flag_list ) or \
                                         ( master_list[curIndex-1] in semiminima_right_flag_list and master_list[curIndex+1] in semiminima_right_flag_list ):
                                        minimaLengths_changeable[ind] = right_length
                                        minRem_changeable -= right_length
                                    else:
                                        minimaLengths_changeable[ind] = 0.5
                                        extend_list_2.append(ind)
                                    extend_list_2 = list(set(extend_list_2))
                                
                                diff_list = (2.0, float(1)/6)
                                if len(semibrevis_downstem) > 0:
                                    downstem = semibrevis_downstem[0]
                                    releases = [downstem, downstem]
                                    
                                    if len(semibrevis_list) > 0:
                                        minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                        extend_list_1.append(semibrevis_list[-1])
                                        extend_list_1 = list(set(extend_list_1))
                                        change_nums = (len(extend_list_1), len(extend_list_2))
                                        minRem_changeable -= 2.0
                                    
                                    extend_num_1 = min(len(extend_list_1), int(0.5(minRem_changeable - 2.0)))
                                    extend_num_2 = min(len(extend_list_2), 6*minRem_changeable - 12.0)
                                    minimaLengths_changeable[downstem] = max(minRem_changeable, 4.0)
                                    minRem_changeable -= 4.0
                                    change_list = (extend_list_1, extend_list_2)
                                    change_nums = (extend_num_1, extend_num_2)
                                    
                                    minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, change_list, change_nums, diff_list, minRem_changeable, releases = releases, multi = 1)
                                    
                                else:
                                    if len(semibrevis_list) > 0:
                                        releases = [-1, -1]
                                        if semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                                            minimaLengths_changeable[semibrevis_list[-1]] = max(minRem_changeable, 2.0)
                                            extend_num_1 = min(len(extend_list_1),int(0.5*minRem_changeable - 1.0))
                                            extend_num_2 = min(len(extend_list_2), 6*minRem_changeable - 12.0)
                                            minRem_changeable -= max(minRem_changeable, 2.0)
                                            change_list = (extend_list_1, extend_list_2)
                                            change_nums = (extend_num_1, extend_num_2)
                                           
                                            minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, change_list, change_nums, diff_list, minRem_changeable, releases = releases, multi = 1)
                                        else:
                                            minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                            extend_list_1.append(semibrevis_list[-1])
                                            extend_list_1 = list(set(extend_list_1))
                                            change_list = (extend_list_1, extend_list_2)
                                            change_nums = (len(extend_list_1), len(extend_list_2))
                                            minRem_changeable -= 2.0
                                            
                                            minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, change_list, change_nums, diff_list, minRem_changeable, multi = 1)
                                    else:
                                        extend_num_2 = len(extend_list_2)
                                        minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_2, extend_num_2, float(1)/6, minRem_changeable)
                                          
                            tempStrength = music21.medren._evaluateMeasure(self.mOrD, self.mensuralMeasure, minimaLengths_changeable)
                            
                            if tempStrength > strength and minRem_changeable > -0.0001:
                                minimaLengths = minimaLengths_changeable[:]
                                minRem = minRem_changeable
                                strength = tempStrength
                            minimaLengths_changeable = minimaLengths_static
                            minRem_tracker = minRem_tracker or (minRem_changeable > -0.0001)
                            minRem_changeable = minRem_static
                    
                    elif len(semiminima_left_flag_list) == 0 and len(semiminima_right_flag_list) == 0:
                        if len(semibrevis_downstem) > 0:
                            semibrevis_downstem = semibrevis_downstem[0]
                            if len(semibrevis_list) > 0:
                                minimaLengths[semibrevis_list[-1]] = 2.0
                                extend_list_1.append(semibrevis_list[-1])
                                minRem -= 2.0

                            extend_num_1 = min(len(extend_list_1), int(0.5*minRem - 2.0))
                            minimaLengths[semibrevis_downstem] = max(minRem, 4.0)
                            minRem -= max(minRem, 4.0)                     
                            
                            if minRem >= 0:
                                minimaLengths, minRem = processMeasure(self.mensuralMeasure, minimaLengths, extend_list_1, extend_num_1, 2.0, minRem, releases = semibrevis_downstem)
                        
                        else:
                            if len(semibrevis_list) > 0:
                                if semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                                    minimaLengths[semibrevis_list[-1]] = max(minRem, 2.0)
                                    extend_num_1 = min(len(extend_list_1), int(0.5*minRem - 1.0))
                                    minRem -= max(minRem, 2.0)
                                    
                                    if minRem >= 0:
                                        minimaLengths, minRem = processMeasure(self.mensuralMeasure, minimaLengths, extend_list_1, extend_num_1, 2.0, minRem, releases = -1)
                                else:
                                    minimaLengths[semibrevis_list[-1]] = 2.0
                                    extend_list_1.append(semibrevis_list[-1])
                                    extend_num_1 = len(extend_list_1)
                                    minRem -= 2.0
                                                
                                    if minRem >= 0:
                                        minimaLengths, minRem = processMeasure(self.mensuralMeasure, minimaLengths, extend_list_1, extend_num_1, 2.0, minRem)
                        minRem_tracker = minRem_tracker or (minRem > -0.0001)
                    
                    else:
                        lengths = [0.5, float(2)/3]
                        strength = 0
                        semiminima_master_list = semiminima_left_flag_list + semiminima_right_flag_list + semiminima_rest_list
                        for length in lengths:
                            for ind in semiminima_master_list:
                                minimaLengths_changeable[ind] = length
                                minRem_changeable -= length
                            
                            if len(semibrevis_downstem) > 0:
                                downstem = semibrevis_downstem[0]
                                if len(semibrevis_list) > 0:
                                    minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                    extend_list_1.append(semibrevis_list[-1])
                                    extend_list_1 = list(set(extend_list_1))
                                    minRem_changeable -= 2.0
                                
                                extend_list_1 = list(set(extend_list_1))
                                extend_num_1 = min(len(extend_list_1), int(0.5*minRem_changeable - 2.0))
                                minimaLengths_changeable[downstem] = max(minRem_changeable, 4.0)
                                minRem_changeable -= max(minRem_changeable, 4.0)
                                
                                if minRem_changeable >= 0:
                                    minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_1, extend_num_1, minRem_changeable, releases = semibrevis_downstem)
                            
                            else:
                                if len(semibrevis_list) > 0: 
                                    if semibrevis_list[-1] == len(self.mensuralMeasure) - 1:
                                        minimaLengths_changeable[semibrevis_list[-1]] = max(minRem_changeable, 2.0)
                                        extend_num_1 = min(len(extend_list_1), int(0.5*minRem_changeable - 1.0))
                                        minRem_changeable -= max(minRem_changeable, 2.0)
                                        
                                        extend_list_1 = list(set(extend_list_1))
                                        
                                        if minRem_changeable >= 0:
                                            minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_1, extend_num_1, 2.0, minRem_changeable, releases = -1)
                                    else:
                                        minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                                        extend_list_1.append(semibrevis_list[-1])
                                        extend_num_1 = len(extend_list_1)
                                        minRem_changeable -= 2.0
                                        
                                        extend_list_1 = list(set(extend_list_1))
                                        
                                        if minRem_changeable >= 0:
                                            minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_1, extend_num_1, 2.0, minRem_changeable)
                            
                            tempStrength = music21.medren._evaluateMeasure(self.mOrD, self.mensuralMeasure, minimaLengths_changeable)
                            
                            if tempStrength > strength and minRem_changeable > -0.0001:
                                minimaLengths = minimaLengths_changeable[:]
                                minRem = minRem_changeable
                                strength = tempStrength
                            minimaLengths_changeable = minimaLengths_static
                            minRem_tracker = minRem_tracker or (minRem_changeable > -0.0001)
                            minRem_changeable = minRem_static
            
            elif len(semibrevis_downstem) >= 2:
                #Don't need to lengths other SBs, not enough room
                #Hence, skip straight to semiminima 
                
                lengths = [(0.5, 0.5), (float(2)/3, 0.5), (0.5, float(2)/3), (float(2)/3, float(2)/3)]
                strength = 0
                
                for length in lengths:
                    left_length, right_length  = length
                    
                    if len(semibrevis_list) > 0:
                        minimaLengths_changeable[semibrevis_list[-1]] = 2.0
                        minRem_changeable -= 2.0
                    
                    for ind in semiminima_left_flag_list:
                        minimaLengths_changeable[ind] = left_length
                        minRem_changeable -= left_length
                    for ind in semiminima_right_flag_list:
                        minimaLengths_changeable[ind] = right_length
                        minRem_changeable -= right_length
                    
                    if left_length == right_length:
                        for ind in semiminima_rest_list:
                            minimaLengths_changeable[ind] = left_length
                            minRem_changeable -= left_length
                    else:
                        master_list = semiminima_left_flag_list + semiminima_right_flag_list + semiminima_rest_list
                            
                        for ind in semiminima_rest_list:
                            curIndex = int(master_list.index(ind))
                            if ( curIndex == 0 and master_list[curIndex+1] in semiminima_left_flag_list ) or \
                                 ( curIndex == len(master_list) - 1 and master_list[curIndex - 1] in semiminima_left_flag_list ) or \
                                 ( master_list[curIndex-1] in semiminima_left_flag_list and master_list[curIndex+1] in semiminima_left_flag_list ):
                                minimaLengths_changeable[ind] = left_length
                                minRem_changeable -= left_length
                            elif ( curIndex == 0 and master_list[curIndex+1] in semiminima_right_flag_list ) or \
                                 ( curIndex == len(master_list) - 1 and master_list[curIndex - 1] in semiminima_right_flag_list ) or \
                                 ( master_list[curIndex-1] in semiminima_right_flag_list and master_list[curIndex+1] in semiminima_right_flag_list ):
                                minimaLengths_changeable[ind] = right_length
                                minRem_changeable -= right_length
                            else:
                                minimaLengths_changeable[ind] = 0.5
                                extend_list_2.append(ind)
                            
                            extend_num_2 = len(extend_list_2)
                            minimaLengths_changeable, minRem_changeable = minimaLengths_changeable, minRem_changeable = processMeasure(self.mensuralMeasure, minimaLengths_changeable, extend_list_2, extend_num_2, float(1)/6, minRem_changeable)
                    
                    newMensuralMeasure = [music21.medren.MensuralNote('A', 'SB') for i in range(len(semibrevis_downstem))]
                    
                    newMOrD = music21.medren.Divisione('.d.')
                    newMOrD.minimaPerMeasure = minRem_changeable
                        
                    tempTMM = music21.medren._TranslateMensuralMeasure(mensurationOrDivisione = newMOrD, measure = newMensuralMeasure, pDS = True)
                    for i in range(len(semibrevis_downstem)):
                        minimaLengths_changeable[semibrevis_downstem[i]] = max(tempTMM.getMinimaLengths()[i], 4.0)
                        minRem_changeable -= max(tempTMM.getMinimaLengths()[i], 4.0)
                    
                    tempStrength = music21.medren._evaluateMeasure(self.mOrD, self.mensuralMeasure, minimaLengths_changeable)
                    
                    if tempStrength > strength and minRem_changeable > -0.0001:
                        minimaLengths = minimaLengths_changeable[:]
                        minRem = minRem_changeable
                        strength = tempStrength
                    minimaLengths_changeable = minimaLengths_static[:]
                    minRem_tracker = minRem_tracker or (minRem_changeable > -0.0001)
                    minRem_changeable = minRem_static
                    
        
        if not minRem_tracker:
            newMOrD = music21.medren.Divisione(self.mOrD.standardSymbol)
            newMOrD.minimaPerMeasure = 2*self.mOrD.minimaPerMeasure
            tempTMM = music21.medren._TranslateMensuralMeasure(newMOrD, self.mensuralMeasure)
            minimaLengths = tempTMM.getMinimaLengths()
            
        for i in range(len(minimaLengths)): #Float errors
            ml = minimaLengths[i]
            if abs(ml - round(ml)) < 0.0001:
                minimaLengths[i] = round(ml)
        
        return minimaLengths
        
    def _getLengthsFrench(self):
        raise MedRenException('French notation currently not supported')
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class Mensuration(meter.TimeSignature):
    '''
    An object representing a mensuration sign in early music:
    
    >>> from music21 import *
    >>> ODot = medren.Mensuration(tempus = 'perfect', prolation = 'major')
    >>> ODot.standardSymbol
    'O-dot'
    >>> ODot.fontString
    '0x50'
    '''
    
    def __init__(self, tempus = 'perfect', prolation = 'minor', mode = 'perfect', maximode = None, scalingFactor = 4):
 
        self.tempus = tempus
        self.prolation = prolation
        self.mode = mode
        self.maximode = maximode
        # self._scalingFactor = scalingFactor still don't get why this is here...
        self._fontString = ''
        self.timeString = None
        self._minimaPerMeasure = 0
        
        if tempus == 'perfect' and prolation == 'major':
            self.timeString = '9/8'
            self.standardSymbol = 'O-dot'
            self._fontString = '0x50'
            self._minimaPerMeasure = 9
        elif tempus == 'perfect' and prolation == 'minor':
            self.timeString = '6/8'
            self.standardSymbol = 'C-dot'
            self._fontString = '0x63'
            self._minimaPerMeasure = 6
        elif tempus == 'imperfect' and prolation == 'major':
            self.timeString = '3/4'
            self.standardSymbol = 'O'
            self._fontString = '0x4f'
            self._minimaPerMeasure = 6
        elif tempus == 'imperfect' and prolation == 'minor':
            self.timeString = '2/4'
            self.standardSymbol = 'C'
            self._fontString = '0x43'
            self._minimaPerMeasure = 4
        else:
            raise MedRenException('cannot make out the mensuration from tempus %s and prolation %s' % (tempus, prolation)) 

        meter.TimeSignature.__init__(self, self.timeString)
        
    def __repr__(self):
        return '<music21.medren.Mensuration %s>' % self.standardSymbol
    
    def _getMinimaPerMeasure(self):
        return self._minimaPerMeasure
    
    def _setMinimaPerMeasure(self, mPM):
        self._minimaPerMeasure = mPM
    
    minimaPerMeasure = property(_getMinimaPerMeasure, _setMinimaPerMeasure,
                                doc = '''Returns the number of minima in a "measure" (the number of minims before a punctus occurs) for the given divisione.
                                The number of minima in a measure can also be set, but this is really only used for special cases of duration.
                                
                                >>> from music21 import *
                                >>> c = medren.Mensuration('imperfect', 'minor')
                                >>> c.minimaPerMeasure
                                4
                                >>> c.minimaPerMeasure = 8
                                >>> c.minimaPerMeasure
                                8
                                ''')
    
    def _getFontString(self):
        return self._fontString
    
    fontString = property(_getFontString, 
                          doc = '''The utf-8 code corresponding to the mensuration character in Ciconia font 
                          
                          >>> from music21 import *
                          >>> O = medren.Mensuration('imperfect', 'major')
                          >>> O.fontString
                          '0x4f'
                          ''')
#    def _getScalingFactor(self):
#        return self._scalingFactor
    
#    def _setScalingFactor(self, newScalingFactor):
#        pass
   
class Divisione(meter.TimeSignature):
    '''
    An object that represents a divisione found in Italian Notation:
    
    >>> from music21 import *
    >>> d = medren.Divisione('senaria imperfecta')
    >>> d.standardSymbol
    '.i.'
    '''    
    def __init__(self, nameOrSymbol = '.p.'):
        self.name = None
        self.standardSymbol = None
        self._minimaPerMeasure = 0
        
        for d in _validDivisiones:
            if nameOrSymbol in d:
                self.name = d[0]
                self.standardSymbol = d[1]
                self._minimaPerMeasure = _validDivisiones[d]
                
        if self.standardSymbol == None:
            self.timeString = None
        elif self.standardSymbol == '.q.':
            self.timeString = '2/4'
        elif self.standardSymbol == '.i.':
            self.timeString = '6/8'
        elif self.standardSymbol == '.p.':
            self.timeString = '3/4'
        elif self.standardSymbol == '.n.':
            self.timeString = '9/8'
        elif self.standardSymbol == '.o.':
            self.timeString = '2/4'
        elif self.standardSymbol == '.d.':
            self.timeString = '3/4'
        else:
            raise MedRenException('cannot make out the mensuration from name or symbol %s' % nameOrSymbol)
        
        if self.timeString is not None:    
            meter.TimeSignature.__init__(self, self.timeString)
    
    def __repr__(self):
        return '<music21.medren.Divisione %s>' % self.standardSymbol
    
    def _getMinimaPerMeasure(self):
        return self._minimaPerMeasure
    
    def _setMinimaPerMeasure(self, mPM):
        self._minimaPerMeasure = mPM 
    
    minimaPerMeasure = property(_getMinimaPerMeasure, _setMinimaPerMeasure, 
                                doc = '''Returns the number of minima in a "measure" (the number of minims before a punctus occurs) for the given divisione.
                                The number of minima in a measure can also be set, but this is really only used for special cases of duration.
                                
                                >>> from music21 import *
                                >>> n = medren.Divisione('.n.')
                                >>> n.minimaPerMeasure
                                9
                                >>> n.minimaPerMeasure = 18
                                >>> n.minimaPerMeasure
                                18
                                ''')
        
class Punctus(music21.base.Music21Object):
    '''
    An object that represents a punctus, found in Italian notation.
    '''
    def __init__(self):
        self._fontString = '0x70'
        music21.base.Music21Object.__init__(self)
    
    def _getFontString(self):
        return self._fontString
    
    fontString = property(_getFontString, 
                          doc = '''The utf-8 code corresponding the punctus in Cicionia font''')

class GeneralMensuralNote(music21.base.Music21Object):
    '''
    An object representing a generalized mensural note object (a note or a rest). This is arguably the most important mensural object, since it is responsible for getting the context and determining the contextual duration for both :class:`music21.medren.MensuralNote` and :class:`music21.medren.MensrualRest`.
    :class:`musci21.medren.GeneralMensuralNote` takes a mensural type ('longa', 'brevis', 'minima', etc.) or abbreviation ('L', 'B', 'M', etc.) as an argument. This defaults to 'brevis'.
    The object's mensural type can be set and accessed via the property :attr:`music21.medren.GeneralMensuralNote.mensuralType`
    The duration of a general mensural object can be set and accessed using the property :attr:`music21.medren.GeneralMensuralNote.duration`. If the duration cannot be determined, it is set to 0 (for more specific instances, see the :attr:`music21.medren.GeneralMensuralNote.duration` documentation).
    
    Two general mensural notes are considered equal if they have the same mensural type, are present in the same context, and have the same offset in the context (if it exists).
    
    The method :meth:`music21.medren.GeneralMensuralNote._determineMensurationOrDivisione` attempts to get the mensuration or divisione sign from a note's context.
    The method :meth:`music21.medren.GeneralMensualNote._getSurroundingMeasure` attempts to get the measure containing the general mensural note.
    '''
    def __init__(self, mensuralTypeOrAbbr = 'brevis'):
        music21.base.Music21Object.__init__(self)
        self._duration = None
            
        if mensuralTypeOrAbbr in _validMensuralTypes:
            self._mensuralType = mensuralTypeOrAbbr
        elif mensuralTypeOrAbbr in _validMensuralAbbr:
            self.mensuralType = _validMensuralTypes[_validMensuralAbbr.index(mensuralTypeOrAbbr)]
        else:
            raise MedRenException('%s is not a valid mensural type or abbreviation' % mensuralTypeOrAbbr)
    
    def __repr__(self):
        return '<music21.medren.GeneralMensuralNote %s>' % self.mensuralType
    
    def __eq__(self, other):
        '''
        Essentially the same as music21.base.Music21Object.__eq__, but equality of mensural type is tested rather than equality of duration
        
        >>> from music21 import *
        >>> m = medren.GeneralMensuralNote('minima')
        >>> n = medren.GeneralMensuralNote('brevis')
        >>> m == n
        False
        >>> n = medren.GeneralMensuralNote('minima')
        >>> m == n
        True
        >>> s_1 = stream.Stream()
        >>> s_1.append(m)
        >>> m == n
        False
        >>> s_1.append(n)
        >>> m == n
        True
        '''
        
        eq = hasattr(other, 'mensuralType')
        if eq:
            eq = eq and (self.mensuralType == other.mensuralType)
        if eq and hasattr(self, 'activeSite'):
            eq = eq and hasattr(other, 'activeSite')
            if eq:
                eq = eq and (self.activeSite == other.activeSite)
        if eq and hasattr(self, 'offset'):
            eq = eq and hasattr(other, 'offset')
            if eq:
                eq = eq and (self.offset == other.offset)
        return eq
    
    def _getMensuralType(self):
        return self._mensuralType
    
    def _setMensuralType(self, mensuralTypeOrAbbr):
        if mensuralTypeOrAbbr in _validMensuralTypes:
            self._mensuralType = mensuralTypeOrAbbr
        elif t in _validMensuralAbbr:
            self.mensuralType = _validMensuralTypes[_validMensuralAbbr.index(mensuralTypeOrAbbr)]
        else:
            raise MedRenException('%s is not a valid mensural type or abbreviation' % mensuralTypeOrAbbr)
    
    mensuralType = property(_getMensuralType, _setMensuralType,
                        doc = '''Name of the mensural length of the rest (brevis, longa, etc.):
                        
                        >>> from music21 import *
                        >>> gmn = medren.GeneralMensuralNote('maxima')
                        >>> gmn.mensuralType
                        'maxima'
                        >>> gmn_1 = medren.GeneralMensuralNote('SB')
                        >>> gmn_1.mensuralType
                        'semibrevis'
                        >>> gmn_2 = medren.GeneralMensuralNote('blah')
                        Traceback (most recent call last):
                        MedRenException: blah is not a valid mensural type or abbreviation
                        ''')
    
    def _getDuration(self):
        mLen, mDur = 0, 0
        mOrD = self._determineMensurationOrDivisione()
        index = self._getSurroundingMeasure()[1]
        if self._getTranslator() is not None:
            if mOrD.standardSymbol in ['.q.', '.p.', '.i.', '.n.']:
                mDur = 0.5
            else:
                mDur = 0.25
            tempTMM = self._getTranslator()
            mLen = tempTMM.getMinimaLengths()[index]
        self._duration = duration.Duration(mLen*mDur)
        return self._duration
    
    def _setDuration(self, dur):
        if isinstance(dur, music21.duration.Duration):
            self._duration = dur
        else:
            self._duration = duration.Duration(dur)
            
    duration = property(_getDuration, _setDuration,
                        doc = '''
                        The duration of an :class:`music21.medren.GeneralMensuralNote` can be access and set using the :attr:`music21.medren.GeneralMensuralNote.duration`. 
                        The duration of a general mensural note is by default 0. If a subclass is not specified (:class:`music21.medren.MensuralNote` or :class:music21.medren.MensuralRest`), the duration will remain 0 unless set to some other value.
                        If a mensural note or a mensural rest has no context (is not part of a stream), the duration will remain 0 unless set to some other value, since duration is dependant on context. 
                        Furthermore, if a mensural note or a mensural rest has context, but a mensuration or divisione cannot be found or determined from the context, the duration will remain 0.
                        
                        Note: no support yet for French notation.
                        
                        >>> from music21 import *
                        >>> mn = medren.GeneralMensuralNote('B')
                        >>> mn.duration.quarterLength
                        0.0
                        >>> mn = medren.MensuralNote('A', 'B')
                        >>> mn.duration.quarterLength
                        0.0
                        >>> s = stream.Stream()
                        >>> s.append(medren.Divisione('.p.'))
                        >>> for i in range(3):
                        ...    s.append(medren.MensuralNote('A', 'SB'))
                        >>> s.append(medren.Punctus())
                        >>> s.append(medren.MensuralNote('B', 'SB'))
                        >>> s.append(medren.MensuralNote('B', 'SB'))
                        >>> s.append(medren.Punctus())
                        >>> s.append(medren.MensuralNote('A', 'B'))
                        >>> for mn in s:
                        ...    if isinstance(mn, medren.GeneralMensuralNote):
                        ...        print mn.duration.quarterLength
                        1.0
                        1.0
                        1.0
                        1.0
                        2.0
                        3.0
                        >>>
                        >>>  
                        ''')
    
    def _getTranslator(self):
        mOrD = self._determineMensurationOrDivisione()
        measure, index = self._getSurroundingMeasure()
        TMM = None
        if len(measure) > 0 and mOrD is not None:
            if index == 0:
                TMM = music21.medren._TranslateMensuralMeasure(mOrD, measure)
            elif index != -1:
                TMM = measure[0]._getTranslator()
        return TMM
    
    #Using Music21Object.getContextByClass makes _getDuration go into an infinite loop. Thus, the alternative method. 
    def _determineMensurationOrDivisione(self):
        '''
        If the mensural rest has context which contains a mensuration sign or divisione, it returns the mensuration sign or divisione closest to but before itself.
        Otherwise, it tries to determine the mensuration sign from the context. If no mensuration sign can be determined, it throws an error.
        If no context is present, returns None. 
        
        >>> from music21 import *
        >>> gmn = medren.GeneralMensuralNote('longa')
        >>> gmn._determineMensurationOrDivisione()
        >>> 
        >>> s_1 = stream.Stream()
        >>> s_2 = stream.Stream()
        >>> s_3 = stream.Stream()
        >>> s_3.insert(3, gmn)
        >>> s_2.insert(1, medren.Divisione('.q.'))
        >>> s_1.insert(2, medren.Mensuration('perfect', 'major'))
        >>> s_2.insert(2, s_3)
        >>> s_1.insert(3, s_2)
        >>> gmn._determineMensurationOrDivisione()
        <music21.medren.Divisione .q.>
        '''
        
        mOrD = music21.medren._getTargetBeforeOrAtObj(self, [music21.medren.Mensuration, music21.medren.Divisione])
        #mOrD = self.getContextByClass((music21.medren.Mensuration, music21.medren.Divisione))
        if len(mOrD)> 0:
            mOrD = mOrD[0] #Gets most recent M or D
        else:
            mOrD = None #TODO: try to determine mensuration for French Notation
        
        return mOrD
    
    def _getSurroundingMeasure(self):
        '''
        Returns a list of the objects (ordered by offset) that are within the measure containing the mensural rest.
        If the mensural rest has no context, returns an empty list.
        If the mensural rest has more than one context, only the surrounding measure of the first context is returned.
        
        >>> from music21 import *
        >>> s_1 = stream.Stream()
        >>> s_1.append(medren.Divisione('.p.'))
        >>> l = medren.MensuralNote('A', 'longa')
        >>> s_1.append(l)
        >>> for i in range(4):
        ...     s_1.append(medren.MensuralNote('B', 'minima'))
        >>> gmn_1 = medren.GeneralMensuralNote('minima')
        >>> s_1.append(gmn_1)
        >>> s_1.append(medren.MensuralNote('C', 'minima'))
        >>> s_1.append(medren.Punctus())
        >>> gmn_1._getSurroundingMeasure()
        ([<music21.medren.MensuralNote minima B>, <music21.medren.MensuralNote minima B>, <music21.medren.MensuralNote minima B>, <music21.medren.MensuralNote minima B>, <music21.medren.GeneralMensuralNote minima>, <music21.medren.MensuralNote minima C>], 4) 
        >>> 
        >>> s_2 = stream.Stream()
        >>> s_2.append(medren.Divisione('.p.'))
        >>> s_2.append(medren.Punctus())
        >>> s_2.append(medren.MensuralNote('A', 'semibrevis'))
        >>> s_2.append(medren.MensuralNote('B', 'semibrevis'))
        >>> gmn_2 = medren.GeneralMensuralNote('semibrevis')
        >>> s_2.append(gmn_2)
        >>> s_2.append(medren.Ligature(['A','B']))
        >>> gmn_2._getSurroundingMeasure()
        ([<music21.medren.MensuralNote semibrevis A>, <music21.medren.MensuralNote semibrevis B>, <music21.medren.GeneralMensuralNote semibrevis>], 2)
        '''
        
        mList = []
        currentIndex, index = -1, -1
        if len(self.getSites()) > 1:
            site = self.getSites()[1]
            if self.mensuralType in ['brevis', 'longa', 'maxima']:
                mList = [self]
                currentindex = 0
            else:
                tempList = site.recurse()[1:]
                if isinstance(site, music21.stream.Measure):
                    mList += tempList
                else:
                    currentIndex = int(tempList.index(self)) 
                    for i in range(currentIndex-1, -1, -1):
                        # Punctus and ligature marks indicate a new measure
                        if isinstance(tempList[i], music21.medren.Punctus) or isinstance(tempList[i], music21.medren.Ligature):
                            break
                        if isinstance(tempList[i], music21.medren.GeneralMensuralNote):
                            # In Italian notation, brevis, longa, and maxima indicate a new measure
                            if (isinstance(self._determineMensurationOrDivisione(), music21.medren.Divisione) and
                                tempList[i].mensuralType in ['brevis', 'longa', 'maxima']):
                                break
                            else:
                                mList.insert(i, tempList[i])
                    mList.reverse()
                    mList.insert(currentIndex, self)
                    for j in range(currentIndex+1,len(tempList), 1):
                        if isinstance(tempList[j], music21.medren.Punctus) or isinstance(tempList[j], music21.medren.Ligature):
                            break
                        if isinstance(tempList[j], music21.medren.GeneralMensuralNote):
                            if (isinstance(self._determineMensurationOrDivisione(), music21.medren.Divisione) and
                                tempList[j].mensuralType in ['brevis', 'longa', 'maxima']):
                                break
                            else:
                                mList.insert(j, tempList[j])
            index = int(mList.index(self))
        
        return mList, index
            
class MensuralRest(GeneralMensuralNote, music21.note.Rest):
    '''
    An object representing a mensural rest. First argument is mensural type.
    The utf-8 code for the Ciconia font character can be accessed via the property :attr:`music21.medren.MensuralNote.fontString`
    
    Additional methods regarding color, duration, equality, and mensural type are inherited from :class:`music21.medren.GeneralMensuralNote`.
    '''
    
    # scaling?
    def __init__(self, *arguments, **keywords):
        music21.note.Rest.__init__(self, *arguments, **keywords)
        
        self._mensuralType = 'brevis'
        
        if len(arguments) > 0:
            tOrA = arguments[0]
            if tOrA in _validMensuralTypes:
                self._mensuralType = tOrA
            elif tOrA in _validMensuralAbbr:
                self._mensuralType = _validMensuralTypes[_validMensuralAbbr.index(tOrA)]
            else:
                raise MedRenException('%s is not a valid mensural type or abbreviation' % tOrA)
        
        self._duration = None
        self._fontString = ''
        if self.mensuralType == 'Longa':
            self._fontString = '0x30'
        elif self.mensuralType == 'brevis':
            self._fontString = '0x31'
        elif self.mensuralType == 'semibrevis':
            self._fontString = '0x32'
        elif self.mensuralType == 'minima':
            self._fontString = '0x33'
        
    def __repr__(self):
        return '<music21.medren.MensuralRest %s>' % self.mensuralType  
    
    def _getFullName(self):
        msg = []
        msg.append(self.mensuralType)
        msg.append(' rest')
        return ''.join(msg)
       
    fullName = property(_getFullName)
    
    def _getFontString(self):
        return self._fontString
    
    fontString  = property(_getFontString,
                           doc = ''' The utf-8 code corresponding to the mensural rest in Ciconia font.
                            Note that there is no character for a semiminima rest yet.
                            
                            >>> from music21 import *
                            >>> mr = medren.MensuralRest('SB')
                            >>> mr.fontString
                            '0x32'
                            ''')

class MensuralNote(GeneralMensuralNote, music21.note.Note):
    '''
    An object representing a mensural note commonly found in medieval and renaissance music.
    Takes pitch and mensural type as arguments, but defaults to 'C' and 'brevis'.
    Pitch and and mensural type can also be set using the properties :attr:`music21.medren.MensuralNote.pitch` and :attr:`music21.medren.MensuralNote.mensuralType` respectively.
    The utf-8 code for the Ciconia font character can be accessed via the propert:attr:r:`music21.medren.MensuralNote.fontString`

    The note stems can can be set using the method :meth:`music21.medren.MensuralNote.setStem`. A note's stems can be displayed using the method :meth:`music21.medren.MensuralNote.getStems`.
    Stems may only be added to notes shorter than a brevis. For additional detail, see the documentation for :meth:`music21.medren.MensuralNote.setStem`.
    
    The note flags can bej set using the method :meth:`music21.medren.MensuralNote.setFlag`. A note's flags can be displayed using the method :meth:`music21.medren.MensuralNote.getFlags`.
    Note the flags may be added to stems that exist for the given note. For addition, see the documentation for :meth:`music21.medren.MensuralNote.setFlag`.
    
    Two mensural notes are considered equal if they match in pitch, articulation, and are equal as general mensural notes.
    
    Additional methods regarding color, duration, mensural type are inherited from :class:`music21.medren.GeneralMensuralNote`.
    
    '''
    
    # scaling? 
    def __init__(self, *arguments, **keywords):
        music21.note.Note.__init__(self, *arguments, **keywords)
        
        self._mensuralType = 'brevis'    
        
        if len(arguments) > 1:
            tOrA = arguments[1]
            if tOrA in _validMensuralTypes:
                self._mensuralType = tOrA
            elif tOrA in _validMensuralAbbr:
                self._mensuralType = _validMensuralTypes[_validMensuralAbbr.index(tOrA)]
            else:
                raise MedRenException('%s is not a valid mensural type or abbreviation' % tOrA)
        
        if self.mensuralType in ['minima', 'semiminima']:
            self.stems = ['up']
        else:
            self.stems = []
        
        self.flags = dict((s, None) for s in self.stems)
        if self._mensuralType == 'semiminima':
            self.flags['up'] = 'right'
            
        self._duration = None
        self._fontString = ''
    
    def __repr__(self):
        return '<music21.medren.MensuralNote %s %s>' % (self.mensuralType, self.name)
    
    def __eq__(self, other):
        '''
        Same as music21.medren.GeneralNote.__eq__, but also tests equality of pitch and articulation.
        Only pitch is shown as a test. For other cases, please see the docs for music21.medren.GeneralMensuralNote.__eq__
        
        >>> from music21 import *
        >>> m = medren.MensuralNote('A', 'minima')
        >>> n = medren.MensuralNote('B', 'minima')
        >>> m == n
        False
        >>> s_2 = stream.Stream()
        >>> s_2.append(medren.Divisione('.q.'))
        >>> s_2.append(m)
        >>> s_2.append(n)
        >>> m == n
        False
        '''
        
        eq = music21.medren.GeneralMensuralNote.__eq__(self, other)
        eq  = eq and hasattr(other, 'pitch')
        if eq:
            eq = eq and (self.pitch == other.pitch)
        eq = eq and hasattr(other, 'articulations')
        if eq:
            eq = eq and ( sorted(list(set(self.articulations))) == sorted(list(set(other.articulations))) )
        return eq
    
    def _getFullName(self):
        msg = []
        msg.append(self.mensuralType)
        msg.append(' %s ' % self.pitch.fullName)
        return ''.join(msg)
    
    fullName = property(_getFullName)
    
    def _getFontString(self):
        if self.mensuralType == 'maxima':
            self._fontString = '0x58'
        elif self.mensuralType == 'Longa':
            self._fontString = '0x4c'
        elif self.mensuralType == 'brevis':
            self._fontString = '0x42'
        elif self.mensuralType == 'semibrevis':
            if 'down' in self.stems:
                self._fontString = '0x4e'
            elif 'side' in self.stems:
                self._fontString = '0x41'
            else:
                self._fontString = '0x53'
        elif self.mensuralType == 'minima':
            if 'down' in self.stems:
                if 'down' in self.flags and self.flags['down'] == 'left':
                    self._fontString = '0x46'
                elif 'down' in self.flags and self.flags['down'] == 'right':
                    self._fontString = '0x47'
                else:
                    self._fontString = '0x44'
            elif 'side' in self.stems:
                self._fontString = '0x61'
            else:
                self._fontString = '0x4d'
        else:
            if self.flags['up'] == 'left':
                self._fontString = '0x49'
            else:
                if 'down' in self.stems: 
                    if 'down' in self.flags and self.flags['down'] == 'left':
                        self._fontString = '0x48'
                    else:
                        self._fontString = '0x45'
                else:
                    self._fontString = '0x59'
        
        if self.color ==  'red':
            if self._fontString in ['41', '61']:
                self._fontString = ''
            else:
                self._fontString = hex(int(self._fontString, 16)+32)
        
        return self._fontString
    
    fontString = property(_getFontString, 
                          doc = ''' The utf-8 code corresponding to a mensural note in Ciconia font.
                          Note that semiminima with a left flag on the upper stem and any flag on the lower stem, semiminima with a right flag on the upperstem and on the lowerstem, and any red or unfilled notes with sidestems have no corresponding characters
                          
                          >>> from music21 import *
                          >>> mn = medren.MensuralNote('A', 'M')
                          >>> mn.setStem('down')
                          >>> mn.fontString
                          '0x44'
                          >>> mn.setFlag('down', 'right')
                          >>> mn.fontString
                          '0x47'
                          >>> mn.setFlag('down', None)
                          >>> mn.setStem(None)
                          >>> mn.fontString
                          '0x4d'
                          >>> mn.color = 'red'
                          >>> mn.fontString
                          '0x6d'
                          ''')
        
    def _setColor(self, value):
        if value in ['black', 'red']:
            music21.note.Note._setColor(self, value)
        else:
            raise MedRenException('color %s not supported for mensural notes' % value)
    
    color = property(music21.note.GeneralNote._getColor, _setColor,
                     doc = '''The only valid colors for mensural notes are red and black
                     
                     >>> from music21 import *
                     >>> n = medren.MensuralNote('A', 'brevis')
                     >>> n.color
                     >>> 
                     >>> n.color = 'red'
                     >>> n.color
                     'red'
                     >>> n.color = 'green'
                     Traceback (most recent call last):
                     MedRenException: color green not supported for mensural notes
                     ''')
    
    def getNumDots(self):
        ''' 
        Used for French notation. Not yet implemented
        '''
        return 0 #TODO: figure out how dots work
    
    def getStems(self):
        '''
        Returns a list of stem directions. If the note has no stem, returns an empty list
        '''
        return self.stems
    
    def setStem(self, direction):
        #NOTE: This method makes it possible to have a semibrevis with a sidestem and a downstem. This doesn't mean anything so far as I can tell.
        '''
        Takes one argument: direction
        Adds a stem to a note. Any note less than or equal to a minima gets an upstem by default.
        Any note can have at most two stems. Valid stem directions are "down", and "side". 
        Down stems can be applied to any note less than or equal to a brevis.
        Side stems in Italian notation are the equivalent of dots, but may only be applied to notes of the type semibrevis and minima (hence, a dotted note may not have a side stem,  and vice versa).
        Setting stem direction to None removes all but the default number of stems. 
        
        >>> from music21 import *
        >>> r_1 = medren.MensuralNote('A', 'brevis')
        >>> r_1.setStem('down')
        Traceback (most recent call last):
        MedRenException: A note of type brevis cannot be equipped with a stem
        >>> r_2 = medren.MensuralNote('A', 'semibrevis')
        >>> r_2.setStem('down')
        >>> r_2.setStem('side')
        >>> r_2.getStems()
        ['down', 'side']
        >>> r_3 = medren.MensuralNote('A', 'minima')
        >>> r_3.setStem('side')
        >>> r_3.getStems()
        ['up', 'side']
        >>> r_3.setStem('down')
        Traceback (most recent call last):
        MedRenException: This note already has the maximum number of stems
        >>> r_3.setStem(None)
        >>> r_3.getStems()
        ['up']
        '''
        
        if direction in [None, 'none', 'None']:
            if self.mensuralType in ['minima', 'semiminima']:
                self.stems = ['up']
            else:
                self.stems = []
        else:
            if self.mensuralType in ['brevis','longa', 'maxima']:
                raise MedRenException('A note of type %s cannot be equipped with a stem' % self.mensuralType)
            else:
                if direction in ['down', 'Down']:
                    direction = 'down'
                    if len(self.stems) > 1:
                        raise MedRenException('This note already has the maximum number of stems')
                    else:
                        self.stems.append(direction)
                            
                elif direction in ['side', 'Side']:
                    direction = 'side'
                    if (self.mensuralType not in ['semibrevis', 'minima']) or self.getNumDots() > 0:
                        raise MedRenException('This note may not have a stem of direction %s' % direction)
                    elif len(self.stems) > 1:
                        raise MedRenException('This note already has the maximum number of stems')
                    else:
                        self.stems.append(direction)
                else:
                    raise MedRenException('%s not recognized as a valid stem direction' % direction)
                
    def getFlags(self):
        '''
        Returns a dictionary of each stem with its corresponding flag. 
        '''
        return self.flags
    
    def setFlag(self, stemDirection, orientation):
        '''
        Takes two arguments: stemDirection and orientation
        stemDirection may be 'up' or 'down' (sidestems cannot have flags), and orientation may be 'left' or 'right'.
        If the note has a stem with direction stemDirection, a flag with the specified orientation is added.
        Any stem may only have up to one flag, so setting a flag overrides whatever flag was previously there.
        Setting the orientation of a flag to None returns that stem to its default flag setting ('right' for semiminima, None otherwise).
        
        A minima may not have a flag on its upstem, while a semiminima always has a flag on its upstem. The flag orientation for a semiminima is 'right' by default, but may be set to left. 
        Any note with a downstem may also have a flag on that stem. 
        
        >>> from music21 import *
        >>> r_1 = medren.MensuralNote('A', 'minima')
        >>> r_1.setFlag('up', 'right')
        Traceback (most recent call last):
        MedRenException: a flag may not be added to an upstem of note type minima
        >>> r_1.setStem('down')
        >>> r_1.setFlag('down', 'left')
        >>> r_1.getFlags()
        {'down': 'left', 'up': None}
        >>> r_2 = medren.MensuralNote('A', 'semiminima')
        >>> r_2.getFlags()
        {'up': 'right'}
        >>> r_2.setFlag('up', 'left')
        >>> r_2.getFlags()
        {'up': 'left'}
        >>> r_3 = medren.MensuralNote('A','semibrevis')
        >>> r_3.setStem('side')
        >>> r_3.setFlag('side','left')
        Traceback (most recent call last):
        MedRenException: a flag cannot be added to a stem with direction side
        '''
        
        if stemDirection == 'up':
            if self.mensuralType != 'semiminima':
                raise MedRenException('a flag may not be added to an upstem of note type %s' % self.mensuralType)
            else:
                if orientation in ['left', 'Left']:
                    orientation = 'left'
                    self.flags[stemDirection] = orientation
                elif orientation in ['right', 'Right']:
                    orientation = 'right'
                    self.flags[stemDirection] = orientation
                elif orientation in ['none', 'None', None]:
                    orientation = 'right'
                    self.flags[stemDirection] = orientation
                else:
                    raise MedRenException('a flag of orientation %s not supported' % orientation)
        elif stemDirection == 'down':
            if stemDirection in self.stems:
                if orientation in ['left', 'Left']:
                    orientation = 'left'
                    self.flags[stemDirection] = orientation
                elif orientation in ['right', 'Right']:
                    orientation = 'right'
                    self.flags[stemDirection] = orientation
                elif orientation in ['none', 'None', None]:
                    orientation = None
                    self.flags[stemDirection] = orientation
                else:
                    raise MedRenException('a flag of orientation %s not supported' % orientation)
            else:
                raise MedRenException('this note does not have a stem with direction %s' % stemDirection)
        else:
            raise MedRenException('a flag cannot be added to a stem with direction %s' % stemDirection)  
        
        
class Ligature(music21.base.Music21Object):
  
    '''
    An object that represents a ligature commonly found in medieval and Renaissance music. 
    Initialization takes a list of the pitches in the ligature as a required argument.
    Color of the ligature is an optional argument (default is 'black'). Color can also be set with the :meth:`music21.medren.Ligature.setColor` method. 
    Color of a ligature can be determined with the :meth:`music21.medren.Ligature.getColor` method.
    Whether the noteheads of the ligature are filled is an optional argument (default is 'yes'). Noteheads can be also filled with the :meth:`music21.medren.Ligature.setFillStatus` method. 
    Fill status of a ligature can be determined with the :meth:`music21.medren.Ligature.getFillStatus` method.
    
    The notes of the ligature can be accessed via the property :attr:`music21.medren.Ligature.notes`.
    The mensural length of each note is calculated automatically. 
    To determine if a ligature is cum proprietate, use the :meth:`music21.medren.Ligature.isCumProprietate` method.
    Similarly, to determine if a ligautre is cum perfectione, use the :meth:`music21.medren.Ligature.isCumPerfectione` method.
    Finally, to determine if a ligature is cum opposite proprietate (C.O.P), use the :meth:`music21.medren.Ligature.isCOP` method. 
    
    Noteheads can be set to have oblique shape using the :meth:`music21.medren.Ligature.makeOblique` method. Similarly, oblique noteheads can be set to have a square shape using the :meth:`music21.medren.Ligature.makeSquare` method. 
    The shape of a notehead can be determined using the :meth:`music21.medren.Ligature.getNoteheadShape` method. By default, all noteheads in a ligature are square.
    
    A note in the ligature can be made to be maxima by the :meth:`music21.medren.Ligature.setMaxima` method. It can be determined whether a note is a maxima by the :meth:`music21.medren.Ligature.isMaxima` method.
    By default, no notes in a ligature are maxima.
    
    A note in the ligature can be set to have an upstem, a downstem, or no stem by the :meth:`music21.medren.Ligature.setStem` method.
    It can be determined whether a note has a stem by the :meth:`music21.medren.Ligature.getStem` method. By default, no notes in a ligature have stems.
    
    A note in the ligature can be 'reversed' by the `music21.medren.Ligature.setReverse` method. A 'reversed' note is displayed as stacked upon the preceding note (see the second note in the example).
    It can be determined whether a note is reversed by the `music21.medren.Ligature.isReversed` method. By default, no notes in a ligature are reversed. 
    -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    Example:
    >>> #_DOCS_SHOW mergedStreams.show()
    
    
    .. image:: images/medren_Ligature_Mensural-Example.*
        :width: 600
    
    
    Roman de Fauvel.  f. 1r.  Paris, Bibliothèque Nationale de France, MS fr.

    The ligatures outlined in blue would be constructed as follows:
    
    >>> from music21 import *
    >>> l1 = medren.Ligature(['A4','F4','G4','A4','B-4'])
    >>> l1.makeOblique(0)
    >>> l1.setStem(0, 'down', 'left')
    >>> print [n.fullName for n in l1.notes]
    ['brevis A4 ', 'brevis F4 ', 'brevis G4 ', 'brevis A4 ', 'brevis B4-flat ']
    >>>
    >>> l2 = medren.Ligature(['F4','G4','A4','B-4','D5'])
    >>> l2.setStem(4, 'down', 'left')
    >>> l2.setReverse(4, True)
    >>> print [n.fullName for n in l2.notes]
    ['brevis F4 ', 'brevis G4 ', 'brevis A4 ', 'brevis B4-flat ', 'longa D5 ']
    
    '''

    def __init__(self, pitches = [], color = 'black', filled = 'yes'):
        self.pitches = []
        
        for p in pitches:
            if isinstance(p, music21.pitch.Pitch):
                self.pitches.append(p)
            else:
                self.pitches.append(music21.pitch.Pitch(p))
        
        self.filled = filled
        self.color = color
        self.noteheadShape = dict([(ind, 'square') for ind in range(self._ligatureLength())])
        self.stems = dict([(ind, (None,None)) for ind in range(self._ligatureLength())])
        self.maximaNotes = dict([(ind, False) for ind in range(self._ligatureLength())])
        self.reversedNotes = dict([(ind, False) for ind in range(self._ligatureLength())])
        
        self._notes = []
        
        music21.base.Music21Object.__init__(self)
    
    def _getNotes(self):
        if self._notes == []:
            self._notes = self._expandLigature()
        return self._notes
    
    notes = property(_getNotes,
                     doc = '''Returns the ligature as a list of mensural notes
                     
                     >>> from music21 import *
                     >>> l = medren.Ligature(['A4','B4'])
                     >>> print [n.mensuralType for n in l.notes]
                     ['brevis', 'brevis']
                     >>> l.makeOblique(0)
                     >>> print [n.mensuralType for n in l.notes]
                     ['longa', 'brevis']
                     >>> l = medren.Ligature(['B4','A4'])
                     >>> print [n.mensuralType for n in l.notes]
                     ['longa', 'longa']
                     >>> l.makeOblique(0)
                     >>> print [n.mensuralType for n in l.notes]
                     ['longa', 'brevis']
                     >>> l.setStem(0, 'down','left')
                     >>> print [n.mensuralType for n in l.notes]
                     ['brevis', 'brevis']
                     >>> l = medren.Ligature(['G4','A4','B4','A4'])
                     >>> l.setStem(2, 'up','left')
                     >>> print [n.mensuralType for n in l.notes]
                     ['brevis', 'brevis', 'semibrevis', 'semibrevis']
                     >>> l = medren.Ligature(['B4','A4','G4','A4','G4','A4','F4'])
                     >>> l.makeOblique(0)
                     >>> l.makeOblique(4)
                     >>> l.setStem(2, 'down', 'left')
                     >>> l.setStem(4, 'up','left')
                     >>> l.setMaxima(6, True)
                     >>> print [n.mensuralType for n in l.notes]
                     ['longa', 'brevis', 'longa', 'brevis', 'semibrevis', 'semibrevis', 'maxima']
                     ''')
        
    def _ligatureLength(self):
        return len(self.pitches)
    
    #def _getDuration(self):
        #return sum[n.duration for n in self.notes]
        
    def isCumProprietate(self):
        '''
        Takes no arguments.
        
        Returns True if the ligature is cum proprietate, and False if the ligature is sine proprietate.
        '''
        return self.notes[0].mensuralType == 'brevis'
    
    def isCumPerfectione(self):
        '''
        Takes no arguments.
        
        Returns True if the ligature is cum perfectione, and False if the ligature is sine perfectione.
        '''
        return self.notes[self._ligatureLength()-1].mensuralType == 'longa'
    
    def isCOP(self):
        '''
        Takes no arguments
        
        Returns True if the ligature is cum oposita proprietate (C.O.P), and False otherwise
        '''
        return self.notes[0].mensuralType == 'semibrevis'
    
    def getColor(self, index = None):
        '''
        Take one argument: index (optional, default is None).
        
        Returns the color of the note at the given index. If no index specified, returns the color of the ligature.
        If multiple colors are present, returns mixed.
        '''
        if index == 'None' or index == 'none':
            index = None
        if index != None:
            if index < self._ligatureLength():
                return self.notes[index]._getColor()
            else:
                raise MedRenException('no note exists at index %d' % index)
        else: 
            return self.color
        
    def setColor(self, value, index = None):
        '''
        Takes two arguments: value, index (optional, default is None).
        
        Sets the color of note at index to value. If no index is specified, or index is set to None, every note in the ligature is given value as a color. 
        
        >>> from music21 import *
        >>> l = medren.Ligature(['A4','C5','B4'])
        >>> l.setColor('red')
        >>> l.getColor()
        'red'
        >>> l.setColor('black',1)
        >>> l.getColor()
        'mixed'
        '''
        tempColor = self.getColor()
        if index == 'None' or index == 'none':
            index = None
        if index != None:
            if index < self._ligatureLength():
                if value != tempColor:
                    self.color = 'mixed'
                    self.notes[index]._setColor(value)
            else:
                raise MedRenException('no note exists at index %d' % index)
        else:
            if value in ['black', 'red']:
                self.color = value
                for n in self.notes:
                    n._setColor(value)
            else:
                raise MedRenException('color %s not supported for ligatures' % value)
    
    def getFillStatus(self, index = None):
        '''
        Take one argument: index (optional, default is None).
        
        Returns whether the notehead is filled at the given index. If no index specified, returns whether fill status of the ligature.
        If noteheads are not consistent throughout the ligature, returns mixed.
        '''
        if index == 'None' or index == 'none':
            index = None
        if index != None:
            if index < self._ligatureLength():
                return self.notes[index]._getNoteheadFill()
            else:
                raise MedRenException('no note exists at index %d' % index) 
        else:
            return self.filled
    
    def setFillStatus(self, value, index = None):
        '''
        Takes two arguments: value, index (optional, default is None).
        
        Sets the fill status of the notehead at index to value. If no index is specified, or if index is set to None, every notehead is give fill status value.
        To set a notehead as filled, value should be 'yes' or 'filled'. To set a notehead as empty, value should be 'no' or 'empty' .
        
        >>> from music21 import *
        >>> l = medren.Ligature(['A4','C5','B4'])
        >>> l.setFillStatus('filled')
        >>> l.getFillStatus()
        'yes'
        >>> l.setFillStatus('no', 1)
        >>> l.getFillStatus()
        'mixed'
        '''
        tempFillStatus = self.getFillStatus()
        if index == 'None' or index == 'none':
            index = None
        if index != None:
            if index < self._ligatureLength():
                if value != tempFillStatus:
                    self.filled = 'mixed'
                    self.notes[index]._setNoteheadFill(value)
            else:
                raise MedRenException('no note exists at index %d' % index)
        else:
            if value in ['yes','fill','filled']:
                value = 'yes'
                self.filled = value
                for n in self.notes:
                    n._setNoteheadFill(value)
            elif value in ['no', 'empty']:
                value = 'no'
                self.fill = value
                for note in self.notes:
                    note._setNoteheadFill(value)
            else:
                raise MedRenException('color %s not supported for ligatures' % color)
                    
    
    def getNoteheadShape(self, index):
        '''
        Takes one argument: index.
        
        Returns the notehead shape (either square or oblique) of the note at index
        '''
        if index < self._ligatureLength():
            return self.noteheadShape[index][0]
        else:
            raise MedRenException('no note exists at index %d' % index)
            
    def makeOblique(self, startIndex):
        '''
        Takes one argument: startIndex.
        
        Make the notes at startIndex and the note following startIndex into an oblique notehead. 
        Note that an oblique notehead cannot start on the last note of a ligature.
        Also, a note that is a maxima cannot be the start or end of an oblique notehead.
        
        >>> from music21 import *
        >>> l = medren.Ligature(['A4','C5','B4','A4'])
        >>> l.makeOblique(1)
        >>> l.getNoteheadShape(1)
        'oblique'
        >>> l.getNoteheadShape(2)
        'oblique'
        >>> l.makeOblique(0)
        Traceback (most recent call last):
        MedRenException: cannot start oblique notehead at index 0
        >>> l.makeOblique(2)
        Traceback (most recent call last):
        MedRenException: cannot start oblique notehead at index 2
        >>> l.makeOblique(3)
        Traceback (most recent call last):
        MedRenException: no note exists at index 4
        '''
        if startIndex < self._ligatureLength() - 1:
            currentShape = self.noteheadShape[startIndex]
            nextShape = self.noteheadShape[startIndex+1]
            if  ((currentShape == ('oblique','end') or nextShape == ('oblique', 'start')) or
                 (self.isMaxima(startIndex) or self.isMaxima(startIndex+1))): 
                raise MedRenException('cannot start oblique notehead at index %d' % startIndex)
            
            else:
                self.noteheadShape[startIndex] = ('oblique', 'start')
                self.noteheadShape[startIndex+1] = ('oblique', 'end')
        else:
            raise MedRenException('no note exists at index %d' % (startIndex+1))
        self._notes = []
    
    def makeSquare(self, index):
        '''
        Takes one argument: index.
        
        Sets the note at index to have a square notehead. If the note at index is part of an oblique notehead, all other notes that are part of that notehead are also set to have square noteheads.
        
        >>> from music21 import *
        >>> l = medren.Ligature(['A4','C5','B4','A4'])
        >>> l.makeOblique(1)
        >>> l.makeSquare(2)
        >>> l.getNoteheadShape(2)
        'square'
        >>> l.getNoteheadShape(1)
        'square'
        '''
        if index < self._ligatureLength():
            currentShape = self.noteheadShape[index]
            if currentShape[0] == 'oblique':
                self.noteheadShape[index] = 'square',
                if currentShape[1] == 'start':
                    self.noteheadShape[index+1] = 'square',
                else:
                    self.noteheadShape[index-1] = 'square',
            else:
                pass #Already square
        else:
            raise MedRenException('no note exists at index %d' % startIndex)
        self._notes = []
    
    def isMaxima(self, index):
        '''
        Takes one argument: index.
        
        If the note at index is a maxima, returns True. Otherwise, it returns False.
        '''
        if index < self._ligatureLength():
            return self.maximaNotes[index]
        else:
            raise MedRenException('no note exists at index %d' % index)
    
    def setMaxima(self, index, value):
        '''
        Takes two arguments: index, value.
        
        Sets the note at index to value. If value is True, that note is a maxima. If value if False, that note is not.
        A note with an oblique notehead cannot be a maxima. 
        A note cannot be a maxima if that note has a stem. A note cannot be a maxima if the previous note has an up-stem.
        
        >>> from music21 import *
        >>> l = medren.Ligature(['A4','C5','B4'])
        >>> l.setStem(0, 'up', 'left')
        >>> l.setMaxima(2, True)
        >>> l.isMaxima(2)
        True
        >>> l.setMaxima(1, True)
        Traceback (most recent call last):
        MedRenException: cannot make note at index 1 a maxima
        >>> l.setMaxima(0, True)
        Traceback (most recent call last):
        MedRenException: cannot make note at index 0 a maxima
        >>> l.setMaxima(2, False)
        >>> l.isMaxima(2)
        False
        '''
        if index < self._ligatureLength():
            if value == True or value == 'True' or value == 'true':
                if (self.getNoteheadShape(index) == 'oblique') or (self.getStem(index) != (None, None)) or (index > 0 and self.getStem(index-1)[0] == 'up'):
                    raise MedRenException('cannot make note at index %d a maxima' % index)
                else:
                    self.maximaNotes[index] = value
            elif value == False or value == 'False' or value == 'false':
                self.maximaNotes[index] = value
            else:
                raise MedRenException('%s is not a valid value' % value)
        else:
            raise MedRenException('no note exists at index %d' % index)
        self._notes = []
    
    def getStem(self, index):
        '''
        Takes one argument: index
        If the note at index has a stem, it returns direction (up or down) and orientation (left, right)
        '''
        if index < self._ligatureLength():
            return self.stems[index]
        else:
            raise MedRenException('no note exists at index %d' % index)
                
    def setStem(self, index, direction, orientation):
        '''
        Takes three arguments: index, direction, orientation.
        
        Index determines which note in the ligature the stem will be placed on.
        Direction determines which way the stem faces. Permitted directions are 'up','down', and 'none'.
        Orientation determines on which side of the note the stem sits. Permitted orientations are 'left', 'right', and 'none'. 
        Setting the direction and orientation of a stem to 'none' removes the stem from the note.
        
        Note that if the direction of a stem is 'none', then no stem is present on that note. So the orientation must also be 'none'.
        Also note that an up-stem followed consecutively by a stemmed note is not permitted. An up-stem cannot be on the last note of a ligature.
        Stems may also not overlap. So two consecutive notes may note have stem orientations 'right' and 'left' respectively.
        Finally, a stem cannot be set on a note that is a maxima. An up-stem cannot be set on a note preceding a maxima.
        
        >>> from music21 import *
        >>> l = medren.Ligature(['A4','C5','B4','A4','B4'])
        >>> l.setStem(0, 'none','left')
        Traceback (most recent call last):
        MedRenException: direction None and orientation left not supported for ligatures
        >>> l.setStem(1,'up', 'left')
        >>> l.getStem(1)
        ('up', 'left')
        >>> l.setStem(2, 'down', 'right')
        Traceback (most recent call last):
        MedRenException: a stem with direction down not permitted at index 2
        >>> l.setMaxima(4, True)
        >>> l.setStem(4, 'up', 'left')
        Traceback (most recent call last):
        MedRenException: cannot place stem at index 4
        >>> l.setStem(3, 'up','left')
        Traceback (most recent call last):
        MedRenException: a stem with direction up not permitted at index 3
        '''
        if direction == 'None' or direction == 'none':
            direction = None
        if orientation == 'None' or direction == 'none':
            index = None
        if index < self._ligatureLength():
            if self.isMaxima(index):
                raise MedRenException('cannot place stem at index %d' % index)
            else:
                if orientation == None and direction == None:
                    self.stems[index] = (direction, orientation)
                elif orientation in ['left', 'right']:
                    if index == 0:
                        prevStem = (None,None)
                        nextStem = self.getStem(1)
                    elif index == self._ligatureLength() - 1:
                        prevStem = self.getStem(self._ligatureLength()-2)
                        nextStem = (None,None)
                    else:
                        prevStem = self.getStem(index-1)
                        nextStem = self.getStem(index+1)
                    if (orientation == 'left' and prevStem[1] != 'right') or (orientation == 'right' and nextStem[1] != 'left'):
                        if direction == 'down':
                            if prevStem[0] != 'up':
                                self.stems[index] = (direction, orientation)
                            else:
                                raise MedRenException('a stem with direction %s not permitted at index %d' % (direction, index))
                        elif direction == 'up':
                            if (index < self._ligatureLength()-1) and (prevStem[0] != 'up') and (nextStem[0] == None) and not self.isMaxima(index+1):
                                self.stems[index] = (direction, orientation)
                            else:
                                raise MedRenException('a stem with direction %s not permitted at index %d' % (direction, index))
                        else:
                            raise MedRenException('direction %s and orientation %s not supported for ligatures' % (direction, orientation))
                    else:
                        raise MedRenException('a stem with orientation %s not permitted at index %d' % (orientation,index))
                else:
                    raise MedRenException('direction %s and orientation %s not supported for ligatures' % (direction,orientation))
        else:
            raise MedRenException('no note exists at index %d' % index)
        self._notes = []     
       
    def isReversed(self, index):
        '''
        Takes one argument: index.
        
        If the note at index is reversed, returns True. Otherwise, it returns False.
        '''
        if index < self._ligatureLength():
            return self.reversedNotes[index]
        else:
            raise MedRenException('no note exists at index %d' % index)
        
    def setReverse(self, endIndex, value):
        '''
        Takes two arguments: startIndex, value.
        
        endIndex designates the note to be reversed. value may be True or False.
        Setting value to True reverses the note at endIndex. Setting value to false 'de-reverses' the note at endIndex.
         
        If the note at endIndex has a stem with direction 'down' and orientation 'left', and is at least a step above the preceding note, it can be reversed.
        No two consecutive notes can be reversed. Also, if the note at endIndex is preceded by a note with an upstem, it cannot be reversed.
        
        A reversed note is displayed directly on top of the preceeding note in the ligature. 
        
        >>> from music21 import *
        >>> l = medren.Ligature(['A4','C5','F5','F#5'])
        >>> l.setStem(1, 'down', 'left')
        >>> l.setStem(2, 'down', 'left')
        >>> l.setStem(3, 'down', 'left')
        >>> l.setReverse(1,True)
        >>> l.isReversed(1)
        True
        >>> l.setReverse(2,True)
        Traceback (most recent call last):
        MedRenException: the note at index 2 cannot be given reverse value True
        >>> l.setReverse(3,True)
        Traceback (most recent call last):
        MedRenException: the note at index 3 cannot be given reverse value True
        '''
        if value == 'True' or value == 'true':
            value = True
        if value == 'False' or value == 'false':
            value = False
            
        if endIndex < self._ligatureLength():
            if value in [True, False]:
                if not value:
                    self.reversedNotes[index] = value
                else:
                    if endIndex > 0:
                        tempPitchCurrent = copy.copy(self.pitches[endIndex])
                        tempPitchPrev = copy.copy(self.pitches[endIndex-1])
                       
                        tempPitchCurrent._setAccidental(None)
                        tempPitchPrev._setAccidental(None)
                        if (not self.isReversed(endIndex-1)) and (self.getStem(endIndex-1)[0] != 'up') and (self.getStem(endIndex) == ('down','left')) and (tempPitchCurrent > tempPitchPrev):
                                self.reversedNotes[endIndex] = True
                        else:
                            raise MedRenException('the note at index %d cannot be given reverse value %s' % (endIndex, value))
                    else:
                        raise MedRenException('no note exists at index %d' % (endIndex-1)) 
            else:
                raise MedRenException('reverse value %s not supported for ligatures %' % value)
        else:
            raise MedRenException('no note exists at index %d' % endIndex)
    
    def _expandLigature(self):
        '''
        Given pitch, notehead, and stem information, assigns a mensural note to each note of the ligature.
        '''
        
        ind = 0
        notes = []
        
        if self._ligatureLength() < 2:
            raise MedRenException('Ligatures must contain at least two notes')
            
        if self.getStem(ind)[0] == 'up':
            notes.append(music21.medren.MensuralNote(self.pitches[ind], 'semibrevis'))
            notes.append(music21.medren.MensuralNote(self.pitches[ind+1], 'semibrevis'))
            ind += 2
        elif self.getStem(ind)[0] == 'down':
            if self.getNoteheadShape(ind) == 'oblique':
                notes.append(music21.medren.MensuralNote(self.pitches[ind], 'brevis'))
            else:
                if self.pitches[ind+1] < self.pitches[ind]:
                    notes.append(music21.medren.MensuralNote(self.pitches[ind], 'brevis'))
                else:
                    notes.append(music21.medren.MensuralNote(self.pitches[ind], 'longa'))
            ind += 1
        else:
            if self.isMaxima(ind):
                notes.append(music21.medren.MensuralNote(self.pitches[ind], 'maxima'))
            else:
                if self.getNoteheadShape(ind) == 'oblique':
                    notes.append(music21.medren.MensuralNote(self.pitches[ind], 'longa'))
                else:
                    if self.pitches[ind+1] < self.pitches[ind]:
                        notes.append(music21.medren.MensuralNote(self.pitches[ind], 'longa'))
                    else:
                        notes.append(music21.medren.MensuralNote(self.pitches[ind], 'brevis'))
            ind += 1
            
        while ind < self._ligatureLength()-1:
            if self.getStem(ind)[0] == 'up':
                notes.append(music21.medren.MensuralNote(self.pitches[ind],  'semibrevis'))
                notes.append(music21.medren.MensuralNote(self.pitches[ind+1], 'semibrevis'))
                ind += 2
            elif self.getStem(ind)[0] == 'down':
                notes.append(music21.medren.MensuralNote(self.pitches[ind], 'longa'))
                ind += 1
            else:
                if self.isMaxima(ind):
                    notes.append(music21.medren.MensuralNote(self.pitches[ind], 'maxima'))
                else:
                    notes.append(music21.medren.MensuralNote(self.pitches[ind], 'brevis'))
                ind += 1
        
        if ind == self._ligatureLength() - 1:
            if self.getStem(ind)[0] == 'down':
                if self.getNoteheadShape(ind) == 'oblique':
                    notes.append(music21.medren.MensuralNote(self.pitches[ind], 'longa'))
                else:
                    if self.pitches[ind-1] < self.pitches[ind]:
                        notes.append(music21.medren.MensuralNote(self.pitches[ind], 'longa'))
                    else:
                        notes.append(music21.medren.MensuralNote(self.pitches[ind], 'brevis'))
            else:
                if self.isMaxima(ind):
                    notes.append(music21.medren.MensuralNote(self.pitches[ind], 'maxima'))
                else:
                    if self.getNoteheadShape(ind) == 'oblique':
                        notes.append(music21.medren.MensuralNote(self.pitches[ind], 'brevis'))
                    else:
                        if self.pitches[ind-1] < self.pitches[ind]:
                            notes.append(music21.medren.MensuralNote(self.pitches[ind], 'brevis'))
                        else:
                            notes.append(music21.medren.MensuralNote(self.pitches[ind], 'longa'))
            
        return notes
#-----------------------------------------------------------------------------------------------------------------------------------------
                     
def setBarlineStyle(score, newStyle, oldStyle = 'regular', inPlace = True):
    '''
    Converts any right barlines in the previous style (oldStyle; default = 'regular')
    to have the newStyle (such as 'tick', 'none', etc., see bar.py).  
    Leaves alone any other barline types (such as
    double bars, final bars, etc.).  Also changes any measures with no specified
    barlines (which come out as 'regular') to have the new style.

    returns the Score object.
    '''
    if inPlace is False:
        score = copy.deepcopy(score)
    
    oldStyle = oldStyle.lower()
    for m in score.semiFlat:
        if isinstance(m, music21.stream.Measure):
            barline = m.rightBarline
            if barline is None:
                m.rightBarline = music21.bar.Barline(style = newStyle)
            else:
                if barline.style == oldStyle:
                    barline.style = newStyle
    return score

def scaleDurations(score, scalingNum = 1, inPlace = True, scaleUnlinked = True):
    '''
    scale all notes and TimeSignatures by the scaling amount.
    
    returns the Score object
    '''
    if inPlace is False:
        score = copy.deepcopy(score)

    for el in score.recurse():
        el.offset = el.offset * scalingNum
        if el.duration is not None:
            el.duration.quarterLength = el.duration.quarterLength * scalingNum
            if hasattr(el.duration, 'linkStatus') and el.duration.linkStatus is False and scaleUnlinked is True:
                raise MedRenException('scale unlinked is not yet supported')
        if isinstance(el, tempo.MetronomeMark):
            el.value = el.value * scalingNum
        elif isinstance(el, meter.TimeSignature):
            newNum = el.numerator
            newDem = el.denominator / (1.0 * scalingNum) # float division
            iterationNum = 0
            while (newDem != int(newDem)):
                newNum = newNum * 2
                newDem = newDem * 2
                iterationNum += 1
                if iterationNum > 4:
                    raise MedRenException('cannot create a scaling of the TimeSignature for this ratio')
            newDem = int(newDem)
            el.loadRatio(newNum, newDem)
    
    for p in score.parts:
        p.makeBeams()
    return score

def transferTies(score, inPlace = True):
    '''
    transfer the duration of tied notes (if possible) to the first note and fill the remaining places
    with invisible rests:
    
    returns the new Score object
    '''
    if inPlace is False:
        score = copy.deepcopy(score)
    tiedNotes = []
    tieBeneficiary = None 
    for el in score.recurse():
        if not isinstance(el, note.Note):
            continue
        if el.tie is not None:
            if el.tie.type == 'start':
                tieBeneficiary = el
            elif el.tie.type == 'continue':
                tiedNotes.append(el)
            elif el.tie.type == 'stop':
                tiedNotes.append(el)
                tiedQL = tieBeneficiary.duration.quarterLength
                for tiedEl in tiedNotes:
                     tiedQL += tiedEl.duration.quarterLength
                tempDuration = duration.Duration(tiedQL)
                if (tempDuration.type != 'complex' and 
                    len(tempDuration.tuplets) == 0):
                    # successfully can combine these notes into one unit
                    ratioDecimal = tiedQL/float(tieBeneficiary.duration.quarterLength)
                    (tupAct, tupNorm) = common.decimalToTuplet(ratioDecimal)
                    if (tupAct != 0): # error...
                        tempTuplet = duration.Tuplet(tupAct, tupNorm, copy.deepcopy(tempDuration.components[0]))
                        tempTuplet.tupletActualShow = "none"
                        tempTuplet.bracket = False
                        tieBeneficiary.duration = tempDuration
                        tieBeneficiary.duration.tuplets = (tempTuplet,)
                        tieBeneficiary.tie = None #.style = 'hidden'
                        for tiedEl in tiedNotes:
                            tiedEl.tie = None #.style = 'hidden'
                            tiedEl.hideObjectOnPrint = True
                tiedNotes = []

    return score

def convertHouseStyle(score, durationScale = 2, barlineStyle = 'tick', tieTransfer = True, inPlace = False):
    '''
    The :meth:`music21.medren.convertHouseStyle` method is best explained by the following images:
    >>> #_DOCS_SHOW mergedStreams.show()

    .. image:: images/medren_convertHouseStyle_1.*
        :width: 600
    
    >>> #_DOCS_SHOW mergedStreams.show()

    .. image:: images/medren_convertHouseStyle_2.*
        :width: 600
    
    >>> #_DOCS_SHOW mergedStreams.show()

    .. image:: images/medren_convertHouseStyle_3.*
        :width: 600
    
    '''
    
    if inPlace is False:
        score = copy.deepcopy(score)
    if durationScale != False:
        scaleDurations(score, durationScale, inPlace = True)
    if barlineStyle != False:
        setBarlineStyle(score, barlineStyle, inPlace = True)
    if tieTransfer != False:
        transferTies(score, inPlace = True)
    
    return score

 


def cummingSchubertStrettoFuga(score):
    '''
    evaluates how well a given score works as a Stretto fuga would work at different intervals
    '''
    lastInterval = None
    sn = score.flat.notes
    strettoKeys = {8: 0, -8: 0, 5: 0, -5: 0, 4: 0, -4: 0}
    
    for i in range(len(sn)-1):
        thisInt = interval.notesToInterval(sn[i], sn[i+1])
        thisGeneric = thisInt.generic.directed
        for strettoType in [8, -8, 5, -5, 4, -4]:
            strettoAllowed = [x[0] for x in allowableStrettoIntervals[strettoType]] #inefficent but who cares
            repeatAllowed = [x[1] for x in allowableStrettoIntervals[strettoType]]
            for j in range(len(strettoAllowed)):
                thisStrettoAllowed = strettoAllowed[j]
                if thisGeneric == thisStrettoAllowed:
                    if thisGeneric != lastInterval:
                        strettoKeys[strettoType] += 1
                    elif thisGeneric == lastInterval and repeatAllowed[j] is True:
                        strettoKeys[strettoType] += 1
            
        lastInterval = thisGeneric
    if score.title:
        print score.title
    
    print "intv.\tcount\tpercent"
    for l in sorted(strettoKeys.keys()):
        print ("%2d\t%3d\t%2d%%" % (l, strettoKeys[l], strettoKeys[l]*100/len(sn)-1))
    print "\n"
        
class MedRenException(music21.Music21Exception):
    pass

class Test(unittest.TestCase):
    
    def runTest(self):
        pass
   
class TestExternal(unittest.TestCase):
        
    def runTest(self):
        pass    
    
    def xtestBarlineConvert(self):
        from music21 import corpus
        self.testPiece = corpus.parse('luca/gloria')
        setBarlineStyle(self.testPiece, 'tick')
        self.testPiece.show()

    def xtestScaling(self):
        from music21 import corpus
        self.testPiece = corpus.parse('luca/gloria')
        scaleDurations(self.testPiece, .5)
        self.testPiece.show()

    def xtestTransferTies(self):
        from music21 import corpus
        self.testPiece = corpus.parse('luca/gloria')
        transferTies(self.testPiece)
        self.testPiece.show()

    def xtestUnlinked(self):
        from music21 import stream, note, meter
        s = stream.Stream()
        m = meter.TimeSignature('4/4')
        s.append(m)
        n1 = note.WholeNote('C4')
        n2 = note.HalfNote('D4')
        n1.duration.unlink()
        n1.duration.quarterLength = 2.0
        s.append([n1, n2])

    def xtestPythagSharps(self):
        from music21 import corpus
        gloria = corpus.parse('luca/gloria')
        p = gloria.parts[0].flat
        for n in p.notes:
            if n.name == 'F#':
                n.pitch.microtone = 20
            elif n.name == 'C#':
                n.pitch.microtone = 20
            elif n.step != 'B' and n.accidental is not None and n.accidental.name == 'flat':
                n.pitch.microtone = -20
        mts = music21.midi.translate.streamsToMidiTracks(p)

        p.show('midi')

    def testHouseStyle(self):
        from music21 import corpus
        gloria = corpus.parse('luca/gloria')
        gloriaNew = convertHouseStyle(gloria)
        gloriaNew.show()


def testStretto():
    from music21 import converter
    salve = converter.parse("A4 A G A D A G F E F G F E D", '4/4') # salveRegina liber 276 (pdf 400)
    adTe = converter.parse("D4 F A G G F A E G F E D G C D E D G F E D", '4/4') # ad te clamamus
    etJesum = converter.parse("D4 AA C D D D E E D D C G F E D G F E D C D", '4/4') 
    salve.title = "Salve Regina (opening)LU p. 276"
    adTe.title = "...ad te clamamus"
    etJesum.title = "...et Jesum"
    for piece in [salve, adTe, etJesum]:
        cummingSchubertStrettoFuga(piece)        


if __name__ == '__main__':
    music21.mainTest(TestExternal)
#    almaRedemptoris = converter.parse("C4 E F G A G G G A B c G", '4/4') #liber 277 (pdf401)
#    puer = converter.parse('G4 d d d e d c c d c e d d', '4/4') # puer natus est 408 (pdf 554)
#    almaRedemptoris.title = "Alma Redemptoris Mater LU p. 277"
#    puer.title = "Puer Natus Est Nobis"
