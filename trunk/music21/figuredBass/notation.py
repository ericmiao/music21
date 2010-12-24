import music21
import unittest
import copy
import re

from music21 import pitch

shorthandNotation = {(None,) : (5,3),
                     (5,) : (5,3),
                     (6,) : (6,3),
                     (7,) : (7,5,3),
                     (6,5) : (6,5,3),
                     (4,3) : (6,4,3),
                     (4,2) : (6,4,2)
                     }

class Notation:
    '''
    Convenience class for representing a figured bass notation column.
    
    >>> from music21 import *
    >>> from music21.figuredBass import notation as n
    >>> n1 = n.Notation('')
    >>> n1.figures
    [<music21.figuredBass.notation.Figure 5 <modifier None None>>, <music21.figuredBass.notation.Figure 3 <modifier None None>>]
    >>> n2 = n.Notation('#')
    >>> n2.figures
    [<music21.figuredBass.notation.Figure 5 <modifier None None>>, <music21.figuredBass.notation.Figure 3 <modifier # <accidental sharp>>>]
    >>> n3 = n.Notation('-6,-')
    >>> n3.figures
    [<music21.figuredBass.notation.Figure 6 <modifier - <accidental flat>>>, <music21.figuredBass.notation.Figure 3 <modifier - <accidental flat>>>]
    
    OMIT_FROM_DOCS
    >>> n4 = n.Notation('4,2+')
    >>> n4.figures[0]
    <music21.figuredBass.notation.Figure 6 <modifier None None>>
    >>> n4.figures[1]
    <music21.figuredBass.notation.Figure 4 <modifier None None>>
    >>> n4.figures[2]
    <music21.figuredBass.notation.Figure 2 <modifier + <accidental sharp>>>
    '''
    def __init__(self, notationColumn):
        self.notationColumn = notationColumn
        self.origNumbers = None
        self.origModStrings = None
        self.numbers = None
        self.modifierStrings = None
        self.figures = None
        self._parseNotationColumn()
        self._translateToLonghand()
        self._getFigures()            
        
    def _parseNotationColumn(self):
        '''
        Given a notation column below a pitch, defines both self.numbers
        and self.modifierStrings, which provide the intervals above the
        bass and (if necessary) how to modify the corresponding pitches
        accordingly.
    
        >>> from music21 import *
        >>> from music21.figuredBass import notation as n
        >>> notation1 = n.Notation('#6,5') #__init__ method calls _parseNotationColumn()
        >>> notation1.origNumbers
        (6, 5)
        >>> notation1.origModStrings
        ('#', None)
        >>> notation2 = n.Notation('-6,-')
        >>> notation2.origNumbers
        (6, None)
        >>> notation2.origModStrings
        ('-', '-')
        '''
        delimiter = '[,]'
        figures = re.split(delimiter, self.notationColumn)
        patternA1 = '([0-9]*)'
        patternA2 = '([^0-9]*)'
        numbers = []
        modifierStrings = []
        
        for figure in figures:
            figure = figure.strip()
            m1 = re.findall(patternA1, figure)
            m2 = re.findall(patternA2, figure)        
            for i in range(m1.count('')):
                m1.remove('')
            for i in range(m2.count('')):
                m2.remove('')
            if not (len(m1) <= 1 or len(m2) <= 1):
                raise NotationException("Invalid Notation: " + figure)
            
            number = None
            modifierString = None
            if not len(m1) == 0:
                number = int(m1[0].strip())
            if not len(m2) == 0:
                modifierString = m2[0].strip()
                
            numbers.append(number)
            modifierStrings.append(modifierString)
    
        numbers = tuple(numbers)
        modifierStrings = tuple(modifierStrings)
        
        self.origNumbers = numbers #Keep original numbers
        self.numbers = numbers #Will be converted to longhand
        self.origModStrings = modifierStrings #Keep original modifier strings
        self.modifierStrings = modifierStrings #Will be converted to longhand

    def _translateToLonghand(self):
        '''
        Provided the numbers and modifierStrings of a parsed notation column, 
        translates it to longhand.
        
        >>> from music21 import *
        >>> from music21.figuredBass import notation as n
        >>> notation1 = n.Notation('#6,5') #__init__ method calls _parseNotationColumn()
        >>> str(notation1.origNumbers) + " -> " + str(notation1.numbers)
        '(6, 5) -> (6, 5, 3)'
        >>> str(notation1.origModStrings) + " -> " + str(notation1.modifierStrings)
        "('#', None) -> ('#', None, None)"
        >>> notation2 = n.Notation('-6,-')        
        >>> notation2.numbers
        (6, 3)
        >>> notation2.modifierStrings
        ('-', '-') 
        '''
        oldNumbers = self.numbers
        newNumbers = oldNumbers
        oldModifierStrings = self.modifierStrings
        newModifierStrings = oldModifierStrings
    
        try:
            newNumbers = shorthandNotation[oldNumbers]
            newModifierStrings = []
            
            oldNumbers = list(oldNumbers)
            temp = []
            for number in oldNumbers:
                if number == None:
                    temp.append(3)
                else:
                    temp.append(number)
            
            oldNumbers = tuple(temp)
                  
            for number in newNumbers:
                newModifierString = None
                if number in oldNumbers:
                    modifierStringIndex = oldNumbers.index(number)
                    newModifierString = oldModifierStrings[modifierStringIndex]
                newModifierStrings.append(newModifierString)
        
            newModifierStrings = tuple(newModifierStrings)
        except KeyError:
            newNumbers = list(newNumbers)
            temp = []
            for number in newNumbers:
                if number == None:
                    temp.append(3)
                else:
                    temp.append(number)
            
            newNumbers = tuple(temp)
        
        self.numbers = newNumbers
        self.modifierStrings = newModifierStrings
    
    def _getFigures(self):
        '''
        >>> from music21 import *
        >>> from music21.figuredBass import notation as n
        >>> notation2 = n.Notation('-6,-') #__init__ method calls _getFigures()
        >>> notation2.figures[0] 
        <music21.figuredBass.notation.Figure 6 <modifier - <accidental flat>>>
        >>> notation2.figures[1]
        <music21.figuredBass.notation.Figure 3 <modifier - <accidental flat>>>
        '''
        figures = []

        for i in range(len(self.numbers)):
            number = self.numbers[i]
            modifierString = self.modifierStrings[i]
            modifier = Modifier(modifierString)
            figure = Figure(number, modifier)
            figures.append(figure)
        
        self.figures = figures

class NotationException(music21.Music21Exception):
    pass

#-------------------------------------------------------------------------------
class Figure:
    '''
    A figure consists of a number with its modifier,
    if applicable.
    '''
    def __init__(self, number, modifier=None):
        self.number = number
        self.modifier = modifier
    
    def getPitch(self, scale, bassPitch):
        bassSD = scale.getScaleDegreeFromPitch(bassPitch)
        if bassSD == None:
            #Get "pseudo scale degree"
            pass
        
        pitchSD = bassSD + self.number - 1
        pitchAtInterval = scale.pitchFromDegree(pitchSD)
        return self.modifier.modifyPitch(pitchAtInterval)
              
    def __repr__(self):
        return '<music21.figuredBass.notation.%s %s %s>' % (self.__class__.__name__, self.number, self.modifier)

class FigureException(music21.Music21Exception):
    pass

#-------------------------------------------------------------------------------
specialModifiers = {'+' : '#',
                    '/' : '-',
                    '\\' : '#'}

class Modifier:
    def __init__(self, modifierString):
        self.modifierString = modifierString
        self.accidental = self._toAccidental()
    
    def __repr__(self):
        return '<modifier %s %s>' % (self.modifierString, self.accidental)
    
    def _toAccidental(self):
        '''
        >>> from music21 import *
        >>> from music21.figuredBass import notation as n
        >>> m1 = n.Modifier('#')
        >>> m2 = n.Modifier('-')
        >>> m3 = n.Modifier('n')
        >>> m4 = n.Modifier('+') #Raises pitch by semitone
        >>> m1.accidental        
        <accidental sharp>
        >>> m2.accidental  
        <accidental flat>
        >>> m3.accidental  
        <accidental natural>
        >>> m4.accidental
        <accidental sharp>
        '''
        if self.modifierString == None:
            return None
        
        a = pitch.Accidental()
        try:
            a.set(self.modifierString)
        except pitch.AccidentalException:
            try:
                newModifierString = specialModifiers[self.modifierString]
                a.set(newModifierString)
            except KeyError:
                raise ModifierException("Figure modifier unsupported in music21.")
        
        return a
    
    def modifyPitch(self, pitchToAlter, inPlace=True):
        '''
        Given a pitch, modify its accidental accordingly.
        
        >>> from music21 import *
        >>> from music21.figuredBass import notation as n
        >>> m1 = n.Modifier('#')
        >>> m2 = n.Modifier('-')
        >>> m3 = n.Modifier('n')
        >>> p1 = pitch.Pitch('D-5')
        >>> m3.modifyPitch(p1) #Natural
        D5
        >>> m1.modifyPitch(p1) #Sharp
        D#5
        >>> m3.modifyPitch(p1) #Natural
        D5
        >>> m2.modifyPitch(p1) #Flat
        D-5
         
        OMIT_FROM_DOCS
        >>> m4 = n.Modifier('##')
        >>> m5 = n.Modifier('--')
        >>> p2 = pitch.Pitch('F5')
        >>> m4.modifyPitch(p2) #Double Sharp
        F##5
        >>> m3.modifyPitch(p2) #Natural
        F5
        >>> m5.modifyPitch(p2) #Double Flat
        F--5
        '''
        if self.accidental == None:
            return None
        
        if not inPlace:
            pitchToAlter = copy.deepcopy(pitchToAlter)
        if self.accidental.alter == 0.0:
            pitchToAlter.accidental = self.accidental
        else:
            if pitchToAlter.accidental == None:
                pitchToAlter.accidental = self.accidental
            else:
                newAccidental = pitch.Accidental()
                newAlter = pitchToAlter.accidental.alter + self.accidental.alter
                try:
                    newAccidental.set(newAlter)
                    pitchToAlter.accidental = newAccidental
                except pitch.AccidentalException:
                    raise ModifierException("Resulting pitch accidental unsupported in music21.")
    
        return pitchToAlter
    
class ModifierException(music21.Music21Exception):
    pass   

#-------------------------------------------------------------------------------
class Test(unittest.TestCase):

    def runTest(self):
        pass

if __name__ == "__main__":
    notation = Notation("")
    print notation.figures
    music21.mainTest(Test)
