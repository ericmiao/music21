#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:         pitch.py
# Purpose:      music21 classes for representing pitches
#
# Authors:      Michael Scott Cuthbert
#               Christopher Ariza
#
# Copyright:    (c) 2009-2011 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------
'''
Classes and functions for creating and manipulating pitches, pitch-space, and accidentals.
Used extensively by note.py
'''

import os
import string, copy, math
import unittest, doctest

import music21
from music21 import common
from music21 import musicxml
musicxmlMod = musicxml # alias as to avoid name conflict below
from music21 import defaults
from music21 import interval
from music21.musicxml import translate as musicxmlTranslate


from music21 import environment
_MOD = "pitch.py"
environLocal = environment.Environment(_MOD)



STEPREF = {
           'C' : 0,
           'D' : 2, #2
           'E' : 4,
           'F' : 5,
           'G' : 7,
           'A' : 9, #9
           'B' : 11,
               }
STEPNAMES = ['C','D','E','F','G','A','B']

TWELFTH_ROOT_OF_TWO = 2.0 ** (1.0/12)

# basic accidental string and symbol definitions; additional symbolic and text-based alternatives are given in the set Accidental.set() method
MICROTONE_OPEN = '('
MICROTONE_CLOSE = ')'
accidentalNameToModifier = {
    'natural' : '',
    'sharp' : '#',
    'double-sharp':'##',
    'triple-sharp':'###',
    'quadruple-sharp':'####',
    'flat':'-',
    'double-flat':'--',
    'triple-flat':'---',
    'quadruple-flat':'----',
    'half-sharp':'~',
    'one-and-a-half-sharp':'#~',
    'half-flat':'`',
    'one-and-a-half-flat':'-`',
}

# sort modifiers by length, from longest to shortest
accidentalModifiersSorted = []
for i in (4,3,2,1):
    for sym in accidentalNameToModifier.values():
        if len(sym) == i:
            accidentalModifiersSorted.append(sym)


#-------------------------------------------------------------------------------
# utility functions
def convertPitchClassToNumber(ps):
    '''Given a pitch class or pitch class value, 
    look for strings. If a string is found, 
    replace it with the default pitch class representation.

    >>> from music21 import *
    >>> convertPitchClassToNumber(3)
    3
    >>> convertPitchClassToNumber('a')
    10
    >>> convertPitchClassToNumber('B')
    11
    >>> convertPitchClassToNumber('3')
    3
    '''
    if common.isNum(ps):
        return ps
    else: # assume is is a string
        if ps in ['a', 'A']:
            return 10
        if ps in ['b', 'B']:
            return 11
        # maybe its a string of an integer?
        return int(ps)
        
def convertPitchClassToStr(pc):
    '''Given a pitch class number, return a string. 

    >>> convertPitchClassToStr(3)
    '3'
    >>> convertPitchClassToStr(10)
    'A'
    '''
    pc = pc % 12 # do just in case
    # replace 10 with A and 11 with B
    return '%X' % pc  # using hex conversion, good up to 15
        

def convertNameToPitchClass(pitchName):
    '''Utility conversion: from a pitch name to a pitch class integer between 0 and 11.

    >>> convertNameToPitchClass('c4')
    0
    >>> convertNameToPitchClass('c#')
    1
    >>> convertNameToPitchClass('d-')
    1
    >>> convertNameToPitchClass('e--')
    2
    >>> convertNameToPitchClass('b2##')
    1
    '''
    # use pitch name reading in Pitch object, 
    # as an Accidental object is created.
    p = Pitch(pitchName)
    return p.pitchClass

def convertNameToPs(pitchName):
    '''Utility conversion: from a pitch name to a pitch space number (floating point MIDI pitch values).

    >>> from music21 import *
    >>> pitch.convertNameToPs('c4')
    60.0
    >>> pitch.convertNameToPs('c2#')
    37.0
    >>> pitch.convertNameToPs('d7-')
    97.0
    >>> pitch.convertNameToPs('e1--')
    26.0
    >>> pitch.convertNameToPs('b2##')
    49.0
    >>> pitch.convertNameToPs('c~4')
    60.5
    '''
    # use pitch name reading in Pitch object, 
    # as an Accidental object is created.
    p = Pitch(pitchName)
    return p.ps

def convertPsToOct(ps):
    '''Utility conversion; does not process internals.
    Converts a midiNote number to an octave number.
    Assume C4 middle C, so 60 returns 4
    >>> [convertPsToOct(59), convertPsToOct(60), convertPsToOct(61)]
    [3, 4, 4]
    >>> [convertPsToOct(12), convertPsToOct(0), convertPsToOct(-12)]
    [0, -1, -2]
    >>> convertPsToOct(135)
    10
    '''
    return int(math.floor(ps / 12.)) - 1

def convertPsToStep(ps):
    '''Utility conversion; does not process internals.
    Takes in a midiNote number (Assume C4 middle C, so 60 returns 4)
    Returns a tuple of Step name and either a natural or a sharp
    
    >>> convertPsToStep(60)
    ('C', <accidental natural>)
    >>> convertPsToStep(66)
    ('F', <accidental sharp>)
    >>> convertPsToStep(67)
    ('G', <accidental natural>)
    >>> convertPsToStep(68)
    ('G', <accidental sharp>)
    >>> convertPsToStep(-2)
    ('B', <accidental flat>)

    >>> convertPsToStep(60.5)
    ('C', <accidental half-sharp>)
    >>> convertPsToStep(61.5)
    ('C', <accidental one-and-a-half-sharp>)
    >>> convertPsToStep(62)
    ('D', <accidental natural>)
    >>> convertPsToStep(62.5)
    ('D', <accidental half-sharp>)
    >>> convertPsToStep(135)
    ('E', <accidental flat>)
    '''
    # if this is a microtone it may have floating point vals
    pcReal = ps % 12 
    pc, micro = divmod(pcReal, 1)
    if round(micro, 1) == 0.5:
        micro = 0.5
    else:
        micro = 0

    pc = int(pc)
    # its a natural; nothing to do
    if pc in STEPREF.values():
        acc = Accidental(0+micro)
        pcName = pc 
    # if we take the pc down a half-step, do we get a stepref (natural) value
    elif pc-1 in [0, 5, 7]: # c, f, g: can be sharped
    #elif pc-1 in STEPREF.values():
        # then we need an accidental to accommodate; here, a sharp
        acc = Accidental(1+micro)
        pcName = pc-1
    # if we take the pc up a half-step, do we get a stepref (natural) value
    elif pc+1 in [11, 4]: # b, e: can be flattened
    #elif pc+1 in STEPREF.values():
        # then we need an accidental to accommodate; here, a flat
        acc = Accidental(-1+micro) 
        pcName = pc+1

    for key, value in STEPREF.items():
        if pcName == value:
            name = key
            break
    return name, acc

def convertStepToPs(step, oct, acc=None):
    '''Utility conversion; does not process internals.
    Takes in a note name string, octave number, and optional 
    Accidental object.

    Returns a floating point midiNote number.

    >>> from music21 import *
    >>> pitch.convertStepToPs('c', 4, pitch.Accidental('sharp'))
    61.0
    >>> pitch.convertStepToPs('d', 2, pitch.Accidental(-2))
    36.0
    >>> pitch.convertStepToPs('b', 3, pitch.Accidental(3))
    62.0
    >>> pitch.convertStepToPs('c', 4, pitch.Accidental('half-flat'))
    59.5
    '''
    step = step.strip().upper()
    ps = ((oct + 1) * 12) + STEPREF[step]
    if acc is None:
        return float(ps) # always returns a float
    else: # assume that this is an accidental object
        return ps + acc.alter

def convertPsToFq(ps):
    '''Utility conversion; does not process internals.
    
    Converts a midiNote number to a frequency in Hz.
    Assumes A4 = 440 Hz
    
    
    >>> from music21 import *
    >>> pitch.convertPsToFq(69)
    440.0
    >>> str(pitch.convertPsToFq(60))
    '261.625565301'
    >>> str(pitch.convertPsToFq(2))
    '9.17702399742'
    >>> str(pitch.convertPsToFq(135))
    '19912.1269582'

    OMIT_FROM_DOCS
    NOT CURRENTLY USED: since freq440 had its own conversion
    methods, and wanted the numbers to be EXACTLY the same
    either way
    '''
    try:
        fq = 440.0 * pow(2, (((ps-60)-9)/12.0))
    except OverflowError:
        fq = 0
    return fq

def convertFqToPs(fq):
    '''Utility conversion; does not process internals.
    Converts a frequency in Hz into a midiNote number.
    Assumes A4 = 440 Hz
    >>> convertFqToPs(440)
    69.0
    >>> convertFqToPs(261.62556530059862)
    60.0
    '''
    return 12 * (math.log(fq / 440.0) / math.log(2)) + 69   

# def convertMicrotoneToCents(value, acc=None):
#     '''Convert a variety of microtone representations into a numerical cents deviation value. Numerical values are treated like other alter values, where 1 is 1 half-step. An Accidental object, or string representation, may be provided with the `acc` argument. 
# 
#     Returns None if no conversion is available. 
# 
#     >>> from music21 import *
#     >>> convertMicrotoneToCents(.5) # numbers are half-step scalars
#     50.0
#     >>> convertMicrotoneToCents(-.5) # numbers are half-step scalars
#     -50.0
#     >>> convertMicrotoneToCents('(+20)') # strings are cents
#     20.0
#     >>> convertMicrotoneToCents('20.53') # strings are cents
#     20.53...
#     >>> convertMicrotoneToCents('-20') # strings are cents
#     -20.0
# 
#     >>> convertMicrotoneToCents('25', '#') # providing an accidental
#     125.0
#     >>> convertMicrotoneToCents('25', '-') 
#     -75.0
#     >>> convertMicrotoneToCents('-25', '-') 
#     -125.0
#     >>> convertMicrotoneToCents('-25', '##')
#     175.0
#     >>> convertMicrotoneToCents('-50', '~')  # negates to zero
#     0.0
#     >>> convertMicrotoneToCents('50', '`')  # negates to zero
#     0.0
# 
#     '''
#     # if a number, assume that the number is halfsteps
#     # this is consistent with other accidental notations, where
#     # .5 is a quarter tone
#     if acc is not None:
#         if common.isStr(acc):
#             acc = Accidental(acc)
# 
#     centValue = None
#     if common.isNum(value):
#         # these are practical, though not necessary, limits,
#         # from -300 to 300 cents
#         if value < -3 or value > 3:
#             return None 
#         centValue = value * 100
#     elif common.isStr(value) and len(value) > 0:
#         # strip any delimiters
#         value = value.replace(MICROTONE_OPEN, '')
#         value = value.replace(MICROTONE_CLOSE, '')
# 
#         if value[0] in ['+'] or value[0].isdigit():
#             # positive cent representation
#             num, junk = common.getNumFromStr(value, numbers='0123456789.')
#             if num == '':
#                 return None
#             else:
#                 centValue = float(num)
#         elif value[0] in ['-']:
#             num, junk = common.getNumFromStr(value[1:], numbers='0123456789.')
#             centValue = float(num) * -1
# 
#     if centValue is not None:
#         if acc is None:
#             return centValue
#         else: # add accidental difference
#             return centValue + (acc.alter * 100)
#     return None # no conversions are available
# 
# def convertMicrotoneToCentsStr(value, roundedDigits=1):
#     '''Provide a string representation for a microtone expressed in cents, with a mandatory +/- sign used to show that this a cent notation.
# 
#     Numerical values are treated like other alter values, where 1 is 1 half-step. 
# 
#     >>> from music21 import *
#     >>> pitch.convertMicrotoneToCentsStr('0.0')
#     '+0'
#     >>> pitch.convertMicrotoneToCentsStr('20')
#     '+20'
#     >>> pitch.convertMicrotoneToCentsStr('20.2')
#     '+20.2'
#     >>> pitch.convertMicrotoneToCentsStr('20.25')
#     '+20.3'
#     >>> pitch.convertMicrotoneToCentsStr('-20')
#     '-20'
#     >>> pitch.convertMicrotoneToCentsStr('-20.2')
#     '-20.2'
#     >>> pitch.convertMicrotoneToCentsStr('-20.25')
#     '-20.3'
# 
#     >>> pitch.convertMicrotoneToCentsStr(.5)
#     '+50'
#     >>> pitch.convertMicrotoneToCentsStr(.25)
#     '+25'
# 
#     '''
#     # do not pass accidental to conversion, as, for display, we want the value
#     # cent deviation without the additional change of the accidental
#     centNumber = convertMicrotoneToCents(value)
#     if centNumber is None:
#         return None
#     # get floating-point portion
#     centInt, centDecimal = divmod(centNumber, 1)
#     if centDecimal == 0:
#         num = int(centInt)
#     else: # what to round to?
#         num = float(round(centNumber, roundedDigits))
# 
#     if centNumber >= 0:
#         return '+%s' % num
#     elif centNumber < 0:
#         # negative sign will automatically be included
#         return '%s' % num
# 
# def convertCentsToAlter(value, acc=None):
#     '''Given a numerical or string cents value, expressed as string or a number, return a floating point alter value, where 1 is 1 half-step.
# 
#     >>> from music21 import *
#     >>> pitch.convertCentsToAlter('+50')
#     0.5...
#     >>> pitch.convertCentsToAlter('+1')
#     0.01...
#     >>> pitch.convertCentsToAlter('-50')
#     -0.5...
#     >>> pitch.convertCentsToAlter(-50) # numerical values are treated as alters
#     -0.5...
# 
#     >>> pitch.convertCentsToAlter('-25', '-') # passing an accidental as well
#     -1.25
#     >>> pitch.convertCentsToAlter('-25', '##') # passing an accidental as well
#     1.75
# 
#     '''
#     # this function handles strings and returns a numerical value
#     if common.isStr(value):
#         # may return None
#         value = convertMicrotoneToCents(value, acc=acc)
#         if value is None:
#             return value
#     return value * .01


def convertHarmonicToCents(value):
    '''Given a harmonic number, return the total number shift in cents assuming 12 tone equal temperament. 
    
    >>> convertHarmonicToCents(8)
    3600
    >>> [convertHarmonicToCents(x) for x in [5, 6, 7, 8]]
    [2786, 3102, 3369, 3600]
    >>> [convertHarmonicToCents(x) for x in [16, 17, 18, 19]]
    [4800, 4905, 5004, 5098]

    >>> [convertHarmonicToCents(x) for x in range(1, 32)]
    [0, 1200, 1902, 2400, 2786, 3102, 3369, 3600, 3804, 3986, 4151, 4302, 4441, 4569, 4688, 4800, 4905, 5004, 5098, 5186, 5271, 5351, 5428, 5502, 5573, 5641, 5706, 5769, 5830, 5888, 5945]
    '''
    # table employed: http://en.wikipedia.org/wiki/Harmonic_series_(music)s
    hs = 100 # halfstep is 100 cents

    # octaves
    if value == 1:
        return 0
    elif value == 2:
        return (1200 * 1)
    elif value == 4:
        return (1200 * 2)
    elif value == 8:
        return (1200 * 3)
    elif value == 16:
        return (1200 * 4)

    elif value == 17:
        return ((100 * 1)+(1200 * 4)) + 5

    elif value == 9:
        return ((100 * 2)+(1200 * 3)) + 4
    elif value == 18:
        return ((100 * 2)+(1200 * 4)) + 4

    elif value == 19:
        return ((100 * 3)+(1200 * 4)) - 2

    elif value == 5:
        return ((100 * 4)+(1200 * 2)) - 14
    elif value == 10:
        return ((100 * 4)+(1200 * 3)) - 14
    elif value == 20:
        return ((100 * 4)+(1200 * 4)) - 14

    elif value == 21:
        return ((100 * 5)+(1200 * 4)) - 29

    elif value == 11:
        return ((100 * 6)+(1200 * 3)) - 49
    elif value == 22:
        return ((100 * 6)+(1200 * 4)) - 49

    elif value == 23:
        return ((100 * 6)+(1200 * 4)) + 28

    elif value == 3:
        return ((100 * 7)+(1200 * 1)) + 2
    elif value == 6:
        return ((100 * 7)+(1200 * 2)) + 2
    elif value == 12:
        return ((100 * 7)+(1200 * 3)) + 2
    elif value == 24:
        return ((100 * 7)+(1200 * 4)) + 2

    elif value == 25:
        return ((100 * 8)+(1200 * 4)) - 27

    elif value == 13:
        return ((100 * 8)+(1200 * 3)) + 41
    elif value == 26:
        return ((100 * 8)+(1200 * 4)) + 41

    elif value == 27:
        return ((100 * 9)+(1200 * 4)) + 6

    elif value == 7:
        return ((100 * 10)+(1200 * 2)) - 31
    elif value == 14:
        return ((100 * 10)+(1200 * 3)) - 31
    elif value == 28:
        return ((100 * 10)+(1200 * 4)) - 31

    elif value == 29:
        return ((100 * 10)+(1200 * 4)) + 30

    elif value == 15:
        return ((100 * 11)+(1200 * 3)) - 12
    elif value == 30:
        return ((100 * 11)+(1200 * 4)) - 12

    elif value == 31:
        return ((100 * 11)+(1200 * 4)) + 45

    else:
        raise Exception('no such harmonic defined: %s' % value)




#-------------------------------------------------------------------------------
class AccidentalException(Exception):
    pass

class PitchException(Exception):
    pass

class MicrotoneException(Exception):
    pass

#-------------------------------------------------------------------------------
class Microtone(object):
    '''
    The Microtone object defines a pitch transformation above or below a standard Pitch

    >>> m = Microtone(20)
    >>> m.cents
    20
    >>> m.alter
    0.200...
    >>> m
    (+20c)
    >>> m.harmonicShift = 3
    >>> m
    (+20c+3rdH)
    >>> m.cents
    1922
    >>> m.alter
    19.2...

    >>> m = Microtone('(-33.333333)')
    >>> m
    (-33c)
    >>> m = Microtone('33.333333')
    >>> m
    (+33c)
    >>> m.alter
    0.3333...
    '''
    _validHarmonics = range(1, 32)

    def __init__(self, centsOrString=0):

        self._centShift = 0
        self._harmonicShift = 1 # the first harmonic is the start

        if common.isNum(centsOrString):
            self._centShift = centsOrString # specify harmonic in cents
        else:
            self._parseString(centsOrString)

        # need to additional store a reference to a position in a 
        # another pitches overtone series? 
        # such as: A4(+69c [7thH/C3])?

    def _parseString(self, value):
        '''Parse a string representation.
        '''
        # strip any delimiters
        value = value.replace(MICROTONE_OPEN, '')
        value = value.replace(MICROTONE_CLOSE, '')

        # need to look for and split off harmonic definitions

        if value[0] in ['+'] or value[0].isdigit():
            # positive cent representation
            num, junk = common.getNumFromStr(value, numbers='0123456789.')
            if num == '':
                raise MicrotoneException('no numbers found in string value: %s' % value)
            else:
                centValue = float(num)
        elif value[0] in ['-']:
            num, junk = common.getNumFromStr(value[1:], numbers='0123456789.')
            centValue = float(num) * -1
        
        self._centShift = centValue


    def __repr__(self):
        '''Return a string representation
        '''
        # cent values may be of any resolution, but round to nearest int
        
        if self._centShift >= 0:
            sub = '+%sc' % int(round(self._centShift))
        elif self._centShift < 0:
            sub = '%sc' % int(round(self._centShift))

        # only show a harmonic if present
        if self._harmonicShift != 1:
            sub += '+%s%sH' % (self._harmonicShift,
                            common.ordinalAbbreviation(self._harmonicShift))
        return '%s%s%s' % (MICROTONE_OPEN, sub, MICROTONE_CLOSE)




    def _getHarmonicShift(self):
        return self._harmonicShift

    def _setHarmonicShift(self, value):
        if value not in self._validHarmonics:
            raise MicrotoneException('not a valud harmonic: %s' % value)
        self._harmonicShift = value

    harmonicShift = property(_getHarmonicShift, _setHarmonicShift, 
        doc = '''Set or get the harmonic shift.
        ''')



    def _getCents(self):
        '''Return the cents.
        '''
        return convertHarmonicToCents(self._harmonicShift) + self._centShift

    cents = property(_getCents, 
        doc = '''Return the microtone value in cents.
        ''')

    def _getAlter(self):
        '''Return the value as an alter value, where 1 is 1 half step.
        '''
        return self._getCents() * .01
        
    alter = property(_getAlter, 
        doc = '''Return the microtone value in accidental alter values. 
        ''')



#-------------------------------------------------------------------------------
class Accidental(music21.Music21Object):
    '''
    Accidental class, representing the symbolic and numerical representation of pitch deviation from a pitch name (e.g., G, B). 
    
    Two accidentals are considered equal if their names are equal.

    Accidentals have three defining attributes: a name, a modifier, and an alter. For microtonal specifications, the name and modifier are the same'

    >>> from music21 import pitch
    >>> a = pitch.Accidental('sharp')
    >>> a.name, a.alter, a.modifier
    ('sharp', 1.0, '#')

    '''
    # manager by properties
    _displayType = "normal" # always, never, unless-repeated, even-tied
    _displayStatus = None # None, True, False

    # not yet managed by properties: TODO
    displayStyle = "normal" # "parentheses", "bracket", "both"
    displaySize  = "full"   # "cue", "large", or a percentage
    displayLocation = "normal" # "normal", "above" = ficta, "below"
    # above and below could also be useful for gruppetti, etc.

    # define order to present names in documentation; use strings
    _DOC_ORDER = ['name', 'modifier', 'alter', 'set']
    # documentation for all attributes (not properties or methods)
    _DOC_ATTR = {
    'name': '''A string name of the Accidental, such as "sharp" or 
        "double-flat".''',
    'modifier': '''A string symbol used to modify the pitch name, such as "#" or 
        "-" for sharp and flat, respectively.''',
    'alter': '''A signed decimal representing the number of half-steps shifted
         by this Accidental, such as 1.0 for a sharp and -.5 for a quarter tone flat.''',
    'displaySize': 'Size in display: "cue", "large", or a percentage.',
    'displayStyle': 'Style of display: "parentheses", "bracket", "both".',
    'displayStatus': 'Determines if this Accidental is to be displayed; can be None (for not set), True, or False.',
    'displayLocation': 'Location of accidental: "normal", "above", "below".'
    }

    def __init__(self, specifier='natural'):
        self.name = None
        self.modifier = ''
        self.alter = 0.0     # semitones to alter step
        #alterFrac = [0,0]   # fractional alteration 
        # (e.g., 1/6); fraction class in 2.6
        #alterExp  = [0,0,0] # exponental alteration 
        # (e.g., [2,3,19] = 2**(3/19))
        #alterHarm = 0       # altered according to a harmonic
        #environLocal.printDebug(['specifier', specifier])
        self.set(specifier)

    def __repr__(self):
        return '<accidental %s>' % self.name
        

    def __eq__(self, other):
        '''Equality. Needed for pitch comparisons.

        >>> from music21 import *
        >>> a = pitch.Accidental('double-flat')
        >>> b = pitch.Accidental('double-flat')
        >>> c = pitch.Accidental('double-sharp')
        >>> a == b   
        True
        >>> a == c
        False

        '''
        if other is None or not isinstance(other, Accidental):
            return False
        if self.name == other.name: 
            return True
        else: 
            return False

    def __ne__(self, other):
        '''Inequality. Needed for pitch comparisons.
        '''
        if other is None:
            return True
        if self.name == other.name: 
            return False
        else: 
            return True


    def __gt__(self, other):
        '''Greater than.  Based on the accidentals' alter function.

        >>> from music21 import *
        >>> a = pitch.Accidental('sharp')
        >>> b = pitch.Accidental('flat')
        >>> a < b   
        False
        >>> a > b
        True
        '''
        if other is None:
            return False
        if self.alter > other.alter: 
            return True
        else: 
            return False

    def __lt__(self, other):
        '''Less than

        >>> from music21 import *
        >>> a = pitch.Accidental('natural')
        >>> b = pitch.Accidental('flat')
        >>> a > b   
        True
        >>> a < b
        False
        '''
        if other is None:
            return True
        if self.alter < other.alter: 
            return True
        else: 
            return False

    def set(self, name):
        '''
        Provide a value to the Accidental. Strings values, numbers, and Lilypond
        Abbreviations are all accepted.  

        >>> from music21 import *
        >>> a = pitch.Accidental()
        >>> a.set('sharp')
        >>> a.alter == 1
        True

        >>> a = pitch.Accidental()
        >>> a.set(2)
        >>> a.modifier == "##"
        True

        >>> a = pitch.Accidental()
        >>> a.set(2.0)
        >>> a.modifier == "##"
        True

        >>> a = pitch.Accidental('--')
        >>> a.alter
        -2.0
        '''
        if common.isStr(name):
            name = name.lower() # sometimes args get capitalized
        if name in ['natural', "n", 0]: 
            self.name = 'natural'
            self.alter = 0.0
        elif name in ['sharp', accidentalNameToModifier['sharp'], "is", 1, 1.0]:
            self.name = 'sharp'
            self.alter = 1.0
        elif name in ['double-sharp', accidentalNameToModifier['double-sharp'], 
            "isis", 2]:
            self.name = 'double-sharp'
            self.alter = 2.0
        elif name in ['flat', accidentalNameToModifier['flat'], "es", -1]:
            self.name = 'flat'
            self.alter = -1.0
        elif name in ['double-flat', accidentalNameToModifier['double-flat'], 
            "eses", -2]:
            self.name = 'double-flat'
            self.alter = -2.0
        
        elif name in ['half-sharp', accidentalNameToModifier['half-sharp'], 
            'quarter-sharp', 'ih', 'semisharp', .5]:
            self.name = 'half-sharp'
            self.alter = 0.5
        elif name in ['one-and-a-half-sharp', 
            accidentalNameToModifier['one-and-a-half-sharp'],
            'three-quarter-sharp', 'three-quarters-sharp', 'isih', 
            'sesquisharp', 1.5]:
            self.name = 'one-and-a-half-sharp'
            self.alter = 1.5  
        elif name in ['half-flat', accidentalNameToModifier['half-flat'], 
            'quarter-flat', 'eh', 'semiflat', -.5]:
            self.name = 'half-flat'
            self.alter = -0.5
        elif name in ['one-and-a-half-flat', 
            accidentalNameToModifier['one-and-a-half-flat'],
            'three-quarter-flat', 'three-quarters-flat', 'eseh', 
            'sesquiflat', -1.5]:
            self.name = 'one-and-a-half-flat'
            self.alter = -1.5
        elif name in ['triple-sharp', accidentalNameToModifier['triple-sharp'], 
            'isisis', 3]:
            self.name = 'triple-sharp'
            self.alter = 3.0
        elif name in ['quadruple-sharp', 
            accidentalNameToModifier['quadruple-sharp'], 'isisisis', 4]:
            self.name = 'quadruple-sharp'
            self.alter = 4.0
        elif name in ['triple-flat', accidentalNameToModifier['triple-flat'],
            'eseses', -3]:
            self.name = 'triple-flat'
            self.alter = -3.0
        elif name in ['quadruple-flat', 
            accidentalNameToModifier['quadruple-flat'], 'eseseses', -4]:
            self.name = 'quadruple-flat'
            self.alter = -4.0
        # support microtones notated with +/ notation
        # first, check if it can be converted
#         elif convertMicrotoneToCents(name) is not None:
#             self.name = convertMicrotoneToCentsStr(name)
#             self.alter = convertCentsToAlter(convertMicrotoneToCents(name))
        else:
            raise AccidentalException('%s is not a supported accidental type' % name)

        # always set modifier from dictionary
#         if self.name.startswith('+') or self.name.startswith('-'):
#             self.modifier = self.name
#         else:
        self.modifier = accidentalNameToModifier[self.name]



    #---------------------------------------------------------------------------
    # main properties

    def _getDisplayType(self):
        return self._displayType

    def _setDisplayType(self, value):
        if value not in ['normal', 'always', 'never', 
            'unless-repeated', 'even-tied']:
            raise AccidentalException('supplied display type is not supported: %s' % value)
        self._displayType = value
    
    displayType = property(_getDisplayType, _setDisplayType, 
        doc = '''Display if first in measure; other valid terms:
        "always", "never", "unless-repeated" (show always unless
        the immediately preceding note is the same), "even-tied"
        (stronger than always: shows even if it is tied to the
        previous note)
        ''')


    def _getDisplayStatus(self):
        return self._displayStatus

    def _setDisplayStatus(self, value):
        if value not in [True, False, None]:
            raise AccidentalException('supplied display status is not supported: %s' % value)
        self._displayStatus = value
    
    displayStatus = property(_getDisplayStatus, _setDisplayStatus, 
        doc = '''Given the displayType, should 
        this accidental be displayed?
        Can be True, False, or None if not defined. For contexts where
        the next program down the line cannot evaluate displayType
        ''')


    def _getUnicode(self):
        '''Return a unicode representation of this accidental.
        '''
        # all unicode musical symbols can be found here:
        # http://www.fileformat.info/info/unicode/block/musical_symbols/images.htm

        if self.name == 'natural':
            # 266E
            return u'\u266e'

        elif self.name == 'sharp':
            # 266F
            return u'\u266f'
        # http://www.fileformat.info/info/unicode/char/1d12a/index.htm
        elif self.name == 'double-sharp':
            # 1D12A
            # note that this must be expressed as a surrogate pair
            return u'\uD834\uDD2A'
        elif self.name == 'half-sharp':
            # 1D132
            return u"\uD834\uDD32"

        elif self.name == 'flat':
            # 266D
            return u'\u266D'
        elif self.name == 'double-flat':
            # 1D12B
            return u'\uD834\uDD2B'
        elif self.name == 'half-flat':
            # 1D133
            # raised flat: 1D12C
            return u"\uD834\uDD33" 

        else: # get our best ascii representation
            return self.modifier

    unicode = property(_getUnicode, 
        doc = '''Return a unicode representation of this accidental. 
        ''')

    #---------------------------------------------------------------------------
    def inheritDisplay(self, other):
        '''Given another Accidental object, inherit all the display properites
        of that object. 

        This is needed when transposing Pitches: we need to retain accidental display properties. 

        >>> from music21 import *
        >>> a = pitch.Accidental('double-flat')
        >>> a.displayType = 'always'
        >>> b = pitch.Accidental('sharp')
        >>> b.inheritDisplay(a)
        >>> b.displayType
        'always'
        '''        
        if other != None: # empty accidental attributes are None
            for attr in ['displayType', 'displayStatus', 
                        'displayStyle', 'displaySize', 'displayLocation']:
                value = getattr(other, attr)
                setattr(self, attr, value)

    def _getLily(self):
        lilyRet = ""
        if (self.name == "sharp"): lilyRet = "is"
        if (self.name == "double-sharp"): lilyRet = "isis"
        if (self.name == "flat"): lilyRet = "es"
        if (self.name == "double-flat"): lilyRet = "eses"
        if (self.name == "natural"): lilyRet = ""
        if (self.name == "half-sharp"): lilyRet = "ih"
        if (self.name == "one-and-a-half-sharp"): lilyRet = "isih"
        if (self.name == "half-flat"): lilyRet = "eh"
        if (self.name == "one-and-a-half-flat"): lilyRet = "eseh"
        return lilyRet
        
    def _setLily(self, value):
        if (value.count("isis") > 0): self.setAccidental("double-sharp")
        elif (value.count("eses") > 0): self.setAccidental("double-flat")
        elif (value.count("isih") > 0): 
            self.setAccidental("one-and-a-half-sharp")
        elif (value.count("eseh") > 0): 
            self.setAccidental("one-and-a-half-flat")
        elif (value.count("is") > 0): self.setAccidental("sharp")
        elif (value.count("es") > 0): self.setAccidental("flat")
        elif (value.count("ih") > 0): self.setAccidental("half-sharp")
        elif (value.count("eh") > 0): self.setAccidental("half-flat")

        if value.count("!") > 0:
            self.displayType = "always"            
        if value.count("?") > 0:
            self.displayStyle = "parentheses"

    # property
    lily = property(_getLily, _setLily, doc =
                    '''From music21 to Lilypond notation.''')

    def lilyDisplayType(self):
        lilyRet = ""
        if self.displayStatus == True or self.displayType == "always" \
           or self.displayType == "even-tied":
            lilyRet += "!"
        
        if self.displayStyle == "parentheses" or self.displayStyle == "both":
            lilyRet += "?"
            ## no brackets for now

        return lilyRet


    def _getMx(self):
        """From music21 to MusicXML

        >>> from music21 import *
        >>> a = pitch.Accidental()
        >>> a.set('half-sharp')
        >>> a.alter == .5
        True
        >>> mxAccidental = a.mx
        >>> mxAccidental.get('content')
        'quarter-sharp'
        """
        if self.name == "half-sharp": 
            mxName = "quarter-sharp"
        elif self.name == "one-and-a-half-sharp": 
            mxName = "three-quarters-sharp"
        elif self.name == "half-flat": 
            mxName = "quarter-flat"
        elif self.name == "one-and-a-half-flat": 
            mxName = "three-quarters-flat"
        else: # all others are the same
            mxName = self.name

        mxAccidental = musicxmlMod.Accidental()
# need to remove display in this case and return None
#         if self.displayStatus == False:
#             pass
        mxAccidental.set('charData', mxName)
        return mxAccidental


    def _setMx(self, mxAccidental):
        """From MusicXML to Music21
        
        >>> from music21 import *
        >>> a = musicxml.Accidental()
        >>> a.set('content', 'half-flat')
        >>> a.get('content')
        'half-flat'
        >>> b = pitch.Accidental()
        >>> b.mx = a
        >>> b.name
        'half-flat'
        """
        mxName = mxAccidental.get('charData')
        if mxName == "quarter-sharp": 
            name = "half-sharp"
        elif mxName == "three-quarters-sharp": 
            name = "one-and-a-half-sharp"
        elif mxName == "quarter-flat": 
            name = "half-flat"
        elif mxName == "three-quarters-flat": 
            name = "one-and-a-half-flat"
        elif mxName == "flat-flat": 
            name = "double-flat"
        elif mxName == "sharp-sharp": 
            name = "double-sharp"
        else:
            name = mxName
        # need to use set her to get all attributes up to date
        self.set(name)

    # property
    mx = property(_getMx, _setMx)








#-------------------------------------------------------------------------------
class Pitch(music21.Music21Object):
    '''
    An object for storing pitch values. 
    All values are represented internally as a 
    scale step (self.step), and octave and an 
    accidental object. In addition, pitches know their 
    pitch space representation (self.ps); altering any 
    of the first three changes the pitch space (ps) representation. 
    Similarly, altering the .ps representation 
    alters the first three.
    
    
    Two Pitches are equal if they represent the same
    pitch and are spelled the same.  A Pitch is greater
    than another Pitch if its pitchSpace is greater than
    the other.  Thus C##4 > D-4.
    
    '''
    # define order to present names in documentation; use strings
    _DOC_ORDER = ['name', 'nameWithOctave', 'step', 'pitchClass', 'octave', 'midi']
    # documentation for all attributes (not properties or methods)
    _DOC_ATTR = {
    }
    def __init__(self, name=None):
        '''Create a Pitch.

        Optional parameter name should include a step and accidental character(s)

        it can also include an octave number ("C#4", "B--3", etc.) so long 
        as it's 0 or higher.

        >>> from music21 import *
        >>> p1 = pitch.Pitch('a#')
        >>> p1
        A#
        >>> p2 = pitch.Pitch(3)
        >>> p2
        E-
        
        
        This is B-double flat in octave 3, not B- in octave -3.
        
        
        >>> p3 = pitch.Pitch("B--3")
        >>> p3.accidental
        <accidental double-flat>
        >>> p3.octave
        3
        '''
        music21.Music21Object.__init__(self)

        # this should not be set, as will be updated when needed
        self._ps = None # pitch space representation, w C4=60 (midi)
        # self._ps must correspond to combination of step and alter
        self._step = defaults.pitchStep # this is only the pitch step
        # keep an accidental object based on self._alter
        
        self._overridden_freq440 = None
        self._twelfth_root_of_two = TWELFTH_ROOT_OF_TWO
        self._accidental = None

        # should this remain an attribute or only refer to value in defaults
        self.defaultOctave = defaults.pitchOctave
        self._octave = None
        self._pitchSpaceNeedsUpdating = True

        # if True, accidental is not known; is determined algorithmically
        # likely due to pitch data from midi or pitch space/class numbers
        self.implicitAccidental = False

        # name combines step, octave, and accidental
        if name is not None:
            if not common.isNum(name):       
                self._setName(name) # set based on string
            else: # is a number
                self._setPitchClass(name)

    def __repr__(self):
        return self.nameWithOctave

    def __eq__(self, other):
        '''Do not accept enharmonic equivalance.
        
        >>> from music21 import *
        >>> a = pitch.Pitch('c2')
        >>> a.octave
        2
        >>> b = pitch.Pitch('c#4')
        >>> b.octave
        4
        >>> a == b
        False
        >>> a != b
        True
        
        >>> c = 7
        >>> a == c
        False
        
        >>> a != c
        True
        
        >>> d = pitch.Pitch('d-4')
        >>> b == d
        False
        
        '''
        if other is None:
            return False
        elif (hasattr(other, 'octave') == False or hasattr(other, 'step') == False or
              hasattr(other, 'step') == False):
            return False
        elif (self.octave == other.octave and self.step == other.step and 
            self.accidental == other.accidental):
            return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        '''Do not accept enharmonic equivalence. Based entirely on pitch space 
        representation.
        
        >>> from music21 import *
        >>> a = pitch.Pitch('c4')
        >>> b = pitch.Pitch('c#4')
        >>> a < b
        True
        '''
        if self.ps < other.ps:
            return True
        else:
            return False

    def __gt__(self, other):
        '''Do not accept enharmonic equivialance. Based entirely on pitch space 
        representation.
        
        >>> from music21 import *
        >>> a = pitch.Pitch('d4')
        >>> b = pitch.Pitch('d8')
        >>> a > b
        False
        '''
        if self.ps > other.ps:
            return True
        else:
            return False

    #---------------------------------------------------------------------------
    def _getAccidental(self):
        return self._accidental
    
    def _setAccidental(self, value):
        if (isinstance(value, basestring) or common.isNum(value)):
            self._accidental = Accidental(value)
        else: # assume an accidental object
            self._accidental = value
        self._pitchSpaceNeedsUpdating = True
    
    accidental = property(_getAccidental, _setAccidental,
        doc='''
        Stores an optional accidental object contained within the
        Pitch object.  This might return None.

        >>> from music21 import *
        >>> a = pitch.Pitch('E-')
        >>> a.accidental.alter
        -1.0
        >>> a.accidental.modifier
        '-'
        
        >>> b = pitch.Pitch('C4')
        >>> b.accidental is None
        True
        >>> b.accidental = pitch.Accidental('natural')
        >>> b.accidental is None
        False
        >>> b.accidental
        <accidental natural>
        
        ''')

    def _getPs(self):
        if self._pitchSpaceNeedsUpdating:
            self._updatePitchSpace()
        return self._ps
    
    def _setPs(self, value):
        '''
        >>> from music21 import *
        >>> p = pitch.Pitch()
        >>> p.ps = 61
        >>> p.ps
        61.0
        >>> p.implicitAccidental
        True
        '''
        # set default enharmonics to minor key names

        self._ps = float(value)
        self._pitchSpaceNeedsUpdating = False

        ### this should eventually change to "stepEtcNeedsUpdating"
        ### but we'll see if it's a bottleneck
        self.step, acc = convertPsToStep(value)
        # replace a natural with a None
        if acc.name == 'natural':
            self.accidental = None
        else:
            self.accidental = acc
        self.octave = convertPsToOct(value)

        # all ps settings must set implicit to True, as we do not know
        # what accidental this is
        self.implicitAccidental = True


    ps = property(_getPs, _setPs, 
        doc='''
        The ps property permits getting and setting 
        a pitch space value, a floating point number 
        representing pitch space, where 60.0 is C4, middle C, 
        61.0 is C#4 or D-4, and floating point values are 
        microtonal tunings (.01 is equal to one cent), so
        a quarter-tone sharp above C5 is 72.5.
        
        Note that the choice of 60.0 for C4 makes it identical
        to the integer value of 60 for .midi, but .midi
        does not allow for microtones and is limited to 0-127
        while .ps allows for notes before midi 0 or above midi 127.
        

        >>> from music21 import *
        >>> a = pitch.Pitch("C4")
        >>> a.ps
        60.0
        
        
        Changing the ps value for
        A will change the step and octave:
        
        
        >>> a.ps = 45
        >>> a
        A2
        >>> a.ps
        45.0

        
        Notice that ps 61 represents both
        C# and D-flat.  Thus "implicitAccidental"
        will be true after setting our pitch to 61:
        
        
        >>> a.ps = 61
        >>> a
        C#4
        >>> a.ps
        61.0
        >>> a.implicitAccidental
        True
        
        
        Microtones are allowed, as are extreme ranges:
        
        
        >>> b = pitch.Pitch('B9')
        >>> b.accidental = pitch.Accidental('half-flat')
        >>> b
        B`9
        >>> b.ps
        130.5
        
        ''')

    def _updatePitchSpace(self):
        '''
        recalculates the pitchSpace number (called when self.step, self.octave 
        or self.accidental are changed.
        '''
        self._ps = convertStepToPs(self._step, self.implicitOctave,
                                   self.accidental)

    def _getMidi(self):
        '''
        see docs below, under property midi
        '''
        if self._pitchSpaceNeedsUpdating:
            self._updatePitchSpace()
            self._pitchSpaceNeedsUpdating = False
        roundedPS = int(round(self.ps))
        if roundedPS > 127:
            value = (12 * 9) + (roundedPS % 12)
            if value < (127-12):
                value += 12
        elif roundedPS < 0:
            value = 0 + (roundedPS % 12)
        else:
            value = roundedPS
        return value

    def _setMidi(self, value):
        '''
        midi values are constrained within the range of 0 to 127
        floating point values,
        '''
        value = int(round(value))
        if value > 127:
            value = (12 * 9) + (value % 12) # highest oct plus modulus
            if value < (127-12):
                value += 12
        elif value < 0:
            value = 0 + (value % 12) # lowest oct plus modulus            
        self._setPs(value)
        self._pitchSpaceNeedsUpdating = True

        # all midi settings must set implicit to True, as we do not know
        # what accidental this is
        self.implicitAccidental = True

    
    midi = property(_getMidi, _setMidi, 
        doc=''' 
        Get or set a pitch value in MIDI. 
        MIDI pitch values are like ps values (pitchSpace) rounded to 
        the nearest integer; while the ps attribute will accommodate floats.


        >>> from music21 import *
        >>> c = pitch.Pitch('C4')
        >>> c.midi
        60
        >>> c.midi =  23.5
        >>> c.midi
        24



        Midi values are also constrained to the space 0-127.  Higher or lower
        values will be transposed octaves to fit in this space.


        
        >>> veryHighFHalfFlat = pitch.Pitch("F")
        >>> veryHighFHalfFlat.octave = 12
        >>> veryHighFHalfFlat.accidental = pitch.Accidental('half-flat')
        >>> veryHighFHalfFlat.ps
        160.5
        >>> veryHighFHalfFlat.midi
        125


        Note that the conversion of improper midi values to proper
        midi values is done before assigning .ps:


        >>> a = pitch.Pitch()
        >>> a.midi = -10
        >>> a.midi
        2
        >>> a.ps
        2.0
        >>> a.implicitAccidental
        True
        ''')

    def _getName(self):
        '''Name presently returns pitch name and accidental without octave.

        >>> from music21 import *
        >>> a = pitch.Pitch('G#')
        >>> a.name
        'G#'
        '''
        if self.accidental is not None:
            return self.step + self.accidental.modifier
        else:
            return self.step
        
    def _setName(self, usrStr):
        '''
        Set name, which may be provided with or without octave values. C4 or D-3
        are both accepted.         
        '''
        usrStr = usrStr.strip().upper()
        # extract any numbers that may be octave designations
        octFound = []
        octNot = []
        for char in usrStr:
            if char in [str(x) for x in range(10)]:
                octFound.append(char)
            else:
                octNot.append(char)
        usrStr = ''.join(octNot)
        octFound = ''.join(octFound)
        # we have nothing but pitch specification
        if len(usrStr) == 1 and usrStr in STEPREF.keys():
            self._step = usrStr
            self.accidental = None
        # assume everything following pitch is accidental specification
        elif len(usrStr) > 1 and usrStr[0] in STEPREF.keys():
            self._step = usrStr[0]
            self.accidental = Accidental(usrStr[1:])
        else:
            raise PitchException("Cannot make a name out of %s" % repr(usrStr))
        if octFound != '': 
            octave = int(octFound)
            self.octave = octave

        # when setting by name, we assume that the accidental intended
        self.implicitAccidental = False

        self._pitchSpaceNeedsUpdating = True
    
    name = property(_getName, _setName, doc='''
        Gets or sets the name (pitch name with accidental but
        without octave) of the Pitch.


        >>> from music21 import *
        >>> p = pitch.Pitch()
        >>> p.name = 'C#'
        >>> p.implicitAccidental 
        False
        >>> p.ps = 61
        >>> p.implicitAccidental 
        True
        >>> p.name
        'C#'
        >>> p.ps = 58
        >>> p.name
        'B-'

        >>> p.name = 'C#'
        >>> p.implicitAccidental 
        False

    ''')


    def _getUnicodeName(self):
        '''Name presently returns pitch name and accidental without octave.

        >>> from music21 import *
        >>> a = pitch.Pitch('G#')
        >>> a.name
        'G#'
        '''
        if self.accidental is not None:
            return self.step + self.accidental.unicode
        else:
            return self.step

    unicodeName = property(_getUnicodeName, 
        doc = '''Return the pitch name in a unicode encoding. 
        ''')

    def _getNameWithOctave(self):
        '''Returns pitch name with octave

        '''
        if self.octave is None:
            return self.name
        else:
            return self.name + str(self.octave)

    nameWithOctave = property(_getNameWithOctave, 
        doc = '''
        The pitch name with an octave designation. 
        If no octave as been set, no octave value is returned. 

        
        Read only attribute.  Set name and octave separately (TODO: Change).

        >>> from music21 import *
        >>> a = pitch.Pitch('G#4')
        >>> a.nameWithOctave
        'G#4'
        >>> a.name = 'A-'
        >>> a.octave = -1
        >>> a.nameWithOctave
        'A--1'
        
        
        ''')

    def _getUnicodeNameWithOctave(self):
        '''Returns pitch name with octave and unicode accidentals
        '''
        if self.octave is None:
            return self.unicodeName
        else:
            return self.unicodeName + str(self.octave)

    unicodeNameWithOctave = property(_getUnicodeNameWithOctave, 
        doc = '''Return the pitch name with octave with unicode accidental symbols, if available. 
        ''')

    def _getStep(self):
        '''
        >>> from music21 import *
        >>> a = pitch.Pitch('C#3')
        >>> a._getStep()
        'C'
        '''
        return self._step

    def _setStep(self, usrStr):
        '''This does not change octave or accidental, only step
        '''
        usrStr = usrStr.strip().upper()
        if len(usrStr) == 1 and usrStr in STEPNAMES:
            self._step = usrStr
        else:
            raise PitchException("Cannot make a step out of '%s'" % usrStr)
        self._pitchSpaceNeedsUpdating = True

    step = property(_getStep, _setStep,
        doc='''The diatonic name of the note; i.e. does not give the 
        accidental or octave.  Is case insensitive.


        >>> from music21 import *
        >>> a = pitch.Pitch('B-3')
        >>> a.step
        'B'
        
        >>> a.step = "c"
        >>> a.nameWithOctave
        'C-3'
        
        
        Giving a name with an accidental raises a PitchException.
        Use .name instead.
        
        >>> from music21 import *
        >>> b = pitch.Pitch('E4')
        >>> b.step = "E-"
        Traceback (most recent call last):
        PitchException: Cannot make a step out of 'E-'
        ''')


    def _getStepWithOctave(self):
        if self.octave is None:
            return self.step
        else:
            return self.step + str(self.octave)

    stepWithOctave = property(_getStepWithOctave, 
        doc = '''
        Returns the pitch step (F, G, etc) with 
        octave designation. If no octave has been set, 
        no octave value is returned. 

        >>> from music21 import *
        >>> a = pitch.Pitch('G#4')
        >>> a.stepWithOctave
        'G4'


        >>> a = pitch.Pitch('A#')
        >>> a.stepWithOctave
        'A'

        ''')


    def _getPitchClass(self):
        return int(round(self.ps % 12))

    def _setPitchClass(self, value):
        '''Set the pitchClass.

        >>> from music21 import *
        >>> a = pitch.Pitch('a3')
        >>> a.pitchClass = 3
        >>> a
        E-3
        >>> a.implicitAccidental
        True
        >>> a.pitchClass = 'A'
        >>> a
        B-3
        '''
        # permit the submission of strings, like A an dB
        value = convertPitchClassToNumber(value)
        # get step and accidental w/o octave
        self._step, self._accidental = convertPsToStep(value)  
        self._pitchSpaceNeedsUpdating = True

        # do not know what accidental is
        self.implicitAccidental = True

        #self.ps = convertStepToPs(self.step, self.implicitOctave, self.accidental)
      
    pitchClass = property(_getPitchClass, _setPitchClass,
        doc='''
        Returns or sets the integer value for the pitch, 0-11, where C=0,
        C#=1, D=2...B=11. Can be set using integers (0-11) or 'A' or 'B'
        for 10 or 11.
        
        
        >>> from music21 import *
        >>> a = pitch.Pitch('a3')
        >>> a.pitchClass
        9
        >>> dis = pitch.Pitch('d3')
        >>> dis.pitchClass
        2
        >>> dis.accidental = pitch.Accidental("#")
        >>> dis.pitchClass
        3
        >>> dis.pitchClass = 11
        >>> dis.pitchClass
        11
        >>> dis.name
        'B'
        ''')


    def _getPitchClassString(self):
        '''
        >>> from music21 import *

        >>> a = pitch.Pitch('a3')
        >>> a._getPitchClassString()
        '9'
        >>> a = pitch.Pitch('a#3')
        >>> a._getPitchClassString()
        'A'
        '''
        return convertPitchClassToStr(self._getPitchClass())

    pitchClassString = property(_getPitchClassString, _setPitchClass, 
        doc = '''
        Returns or sets a string representation of the pitch class, 
        where integers greater than 10 are replaced by A and B, 
        respectively. Can be used to set pitch class by a 
        string representation as well (though this is also 
        possible with :attr:`~music21.pitch.Pitch.pitchClass`.
    
    
        >>> from music21 import *
        >>> a = pitch.Pitch('a3')
        >>> a.pitchClassString = 'B'
        >>> a.pitchClass
        11
        >>> a.pitchClassString
        'B'
        ''')

    def _getOctave(self): 
        '''
        This is _octave, not implicitOctave
        '''
        return self._octave

    def _setOctave(self,value):
        if value is not None:
            self._octave = int(value)
        else:
            self._octave = None
        self._pitchSpaceNeedsUpdating = True

    octave = property(_getOctave, _setOctave, doc='''
        Returns or sets the octave of the note.  
        Setting the octave
        updates the pitchSpace attribute.

        >>> from music21 import *

        >>> a = pitch.Pitch('g')
        >>> a.octave is None
        True
        >>> a.implicitOctave
        4
        >>> a.ps  ## will use implicitOctave
        67.0
        >>> a.name
        'G'

        >>> a.octave = 14
        >>> a.octave
        14
        >>> a.implicitOctave
        14
        >>> a.name
        'G'
        >>> a.ps
        187.0
    ''')

    def _getImplicitOctave(self):
        if self.octave is None: return self.defaultOctave
        else: return self.octave
        
    implicitOctave = property(_getImplicitOctave, doc='''
    Returns the octave of the Pitch, or defaultOctave if 
    octave was never set. To set an octave, use .octave.
    Default octave is usually 4.
    ''')


    def _getGerman(self):
        if self.accidental is not None:
            tempAlter = self.accidental.alter
        else:
            tempAlter = 0
        tempStep = self.step
        if tempAlter != int(tempAlter):
            raise PitchException('Es geht nicht "german" zu benutzen mit Microtoenen.  Schade!')
        else:
            tempAlter = int(tempAlter)
        if tempStep == 'B':
            if tempAlter != -1:
                tempStep = 'H'
            else:
                tempAlter += 1
        if tempAlter == 0:
            return tempStep
        elif tempAlter > 0:
            tempName = tempStep + (tempAlter * 'is')
            return tempName
        else: # flats
            if tempStep in ['C','D','F','G','H']:
                firstFlatName = 'es'
            else: # A, E.  Bs should never occur...
                firstFlatName = 's'
            multipleFlats = abs(tempAlter) - 1
            tempName =  tempStep + firstFlatName + (multipleFlats * 'es')
            return tempName
    
    german = property(_getGerman, doc ='''
    Read-only attribute. Returns the name 
    of a Pitch in the German system 
    (where B-flat = B, B = H, etc.)
    (Microtones raise an error).  Note that 
    Ases is used instead of the also acceptable Asas.
    
    >>> from music21 import *
    >>> print pitch.Pitch('B-').german
    B
    >>> print pitch.Pitch('B').german
    H
    >>> print pitch.Pitch('E-').german
    Es
    >>> print pitch.Pitch('C#').german
    Cis
    >>> print pitch.Pitch('A--').german
    Ases
    >>> p1 = pitch.Pitch('C')
    >>> p1.accidental = pitch.Accidental('half-sharp')
    >>> p1.german
    Traceback (most recent call last):
    PitchException: Es geht nicht "german" zu benutzen mit Microtoenen.  Schade!

    
    Note these rarely used pitches:
    
    
    >>> print pitch.Pitch('B--').german
    Heses
    >>> print pitch.Pitch('B#').german
    His
    ''')


    def _getFrequency(self):        
        return self._getfreq440()

    def _setFrequency(self, value):     
        # store existing octave
        ps = convertFqToPs(value)
        # should get microtones
        self.ps = int(round(ps))
        self.step, self.accidental = convertPsToStep(self.ps)  
        self.octave = convertPsToOct(self.ps)
      
        # do not know what accidental is
        self.implicitAccidental = True


    frequency = property(_getFrequency, _setFrequency, doc='''
        The frequency property gets or sets the frequency of
        the pitch in hertz.  
        If the frequency has not been overridden, then
        it is computed based on A440Hz and equal temperament

        >>> from music21 import *
        >>> a = pitch.Pitch()
        >>> a.frequency = 440.0
        >>> a.frequency
        440.0
        >>> a.name
        'A'
        >>> a.octave
        4


    ''')


    # these methods may belong in in a temperament object
    # name of method and property could be more clear
    def _getfreq440(self):
        '''
        >>> from music21 import *
        >>> a = pitch.Pitch('A4')
        >>> a.freq440
        440.0
        '''
        if self._overridden_freq440:
            return self._overridden_freq440
        else:
            A4offset = self.ps - 69
            return 440.0 * (self._twelfth_root_of_two ** A4offset)
            
    def _setfreq440(self, value):
        self._overridden_freq440 = value

    freq440 = property(_getfreq440, _setfreq440, doc='''
    Gets the frequency of the note as if it's in an equal temperment
    context where A4 = 440hz.  The same as .frequency so long
    as no other temperments are currently being used.
    
    
    Since we don't have any other temperament objects as
    of alpha 7, this is the same as .frequency always.
    
    ''')


    def _getMX(self):
        return musicxmlTranslate.pitchToMx(self)
#         '''
#         Returns a musicxml.Note() object
# 
#         >>> a = Pitch('g#4')
#         >>> c = a.mx
#         >>> c.get('pitch').get('step')
#         'G'
#         '''
#         mxPitch = musicxmlMod.Pitch()
#         mxPitch.set('step', self.step)
#         if self.accidental is not None:
#             # need to use integers when possible in order to support
#             # xml readers that force alter to be an integer
#             mxPitch.set('alter', common.numToIntOrFloat(self.accidental.alter))
#         mxPitch.set('octave', self.implicitOctave)
# 
#         mxNote = musicxmlMod.Note()
#         mxNote.setDefaults()
#         mxNote.set('pitch', mxPitch)
# 
#         if (self.accidental is not None and 
#             self.accidental.displayStatus in [True, None]):
#             mxNote.set('accidental', self.accidental.mx)
#         # should this also return an xml accidental object
#         return mxNote # return element object

    def _setMX(self, mxNote):
        return musicxmlTranslate.mxToPitch(mxNote, self)

#         '''
#         Given a MusicXML Note object, set this Pitch object to its values. 
# 
#         >>> b = musicxml.Pitch()
#         >>> b.set('octave', 3)
#         >>> b.set('step', 'E')
#         >>> b.set('alter', -1)
#         >>> c = musicxml.Note()
#         >>> c.set('pitch', b)
#         >>> a = Pitch('g#4')
#         >>> a.mx = c
#         >>> print(a)
#         E-3
#         '''
#         # assume this is an object
#         mxPitch = mxNote.get('pitchObj')
#         mxAccidental = mxNote.get('accidentalObj')
# 
#         self.step = mxPitch.get('step')
# 
#         # sometimes we have an accidental defined but no alter value, due to 
#         # a natural; need to look at mxAccidental directly
#         mxAccidentalCharData = None
#         if mxAccidental != None:
#             mxAccidentalCharData = mxAccidental.get('charData')
#             #environLocal.printDebug(['found mxAccidental charData', mxAccidentalCharData])
# 
#         acc = mxPitch.get('alter')
#         # None is used in musicxml but not in music21
#         if acc != None or mxAccidentalCharData != None: 
#             if mxAccidental is not None: # the source had wanted to show alter
#                 accObj = Accidental()
#                 accObj.mx = mxAccidental
#             # used to to just use acc value
#             #self.accidental = Accidental(float(acc))
#             # better to use accObj if possible
#                 self.accidental = accObj
#                 self.accidental.displayStatus = True
#             else:
#                 # here we generate an accidental object from the alter value
#                 # but in the source, there was not a defined accidental
#                 self.accidental = Accidental(float(acc))
#                 self.accidental.displayStatus = False
#         self.octave = int(mxPitch.get('octave'))
#         self._pitchSpaceNeedsUpdating = True

    mx = property(_getMX, _setMX)



    def _getMusicXML(self):
        '''Provide a complete MusicXML representation. Presently, this is based on 
        '''
        return musicxmlTranslate.pitchToMusicXML(self)

#         mxNote = self._getMX()
#         mxMeasure = musicxml.Measure()
#         mxMeasure.setDefaults()
#         mxMeasure.append(mxNote)
#         mxPart = musicxml.Part()
#         mxPart.setDefaults()
#         mxPart.append(mxMeasure)
# 
#         mxScorePart = musicxml.ScorePart()
#         mxScorePart.setDefaults()
#         mxPartList = musicxml.PartList()
#         mxPartList.append(mxScorePart)
# 
#         mxIdentification = musicxml.Identification()
#         mxIdentification.setDefaults() # will create a composer
# 
#         mxScore = musicxml.Score()
#         mxScore.setDefaults()
#         mxScore.set('partList', mxPartList)
#         mxScore.set('identification', mxIdentification)
#         mxScore.append(mxPart)
# 
#         return mxScore.xmlStr()

    musicxml = property(_getMusicXML)

    def lilyNoOctave(self):
        '''
        returns the lilypond representation of the pitch
        (with accidentals) but without octave.
        '''
        
        baseName = self.step.lower()
        if (self.accidental):
            baseName += self.accidental.lily
        return baseName
    


    #---------------------------------------------------------------------------
    def isEnharmonic(self, other):
        '''Return True if other is an enharmonic equivalent of self. 

        >>> from music21 import *
        >>> p1 = pitch.Pitch('C#3')
        >>> p2 = pitch.Pitch('D-3')
        >>> p3 = pitch.Pitch('D#3')
        >>> p1.isEnharmonic(p2)
        True
        >>> p2.isEnharmonic(p1)
        True
        >>> p3.isEnharmonic(p1)
        False
        
        OMIT_FROM_DOCS
        >>> p4 = pitch.Pitch('B##3')
        >>> p5 = pitch.Pitch('D-4')
        >>> p4.isEnharmonic(p5)
        True
        '''
        # if pitch space are equal, these are enharmonics
        if other.ps == self.ps:
            return True
        return False

    def getHigherEnharmonic(self, inPlace=False):
        '''Returns a Pitch enharmonic note that a dim-second above the current note.

        >>> from music21 import *
        >>> p1 = pitch.Pitch('C#3')
        >>> p2 = p1.getHigherEnharmonic()
        >>> p2
        D-3

        >>> p1 = pitch.Pitch('C#3')
        >>> p1.getHigherEnharmonic(inPlace=True)
        >>> p1
        D-3
        
        
        
        The method even works for certain CRAZY enharmonics
        
        
        >>> p3 = pitch.Pitch('D--3')
        >>> p4 = p3.getHigherEnharmonic()
        >>> p4
        E----3
        
        
        But not for things that are just utterly insane:
        
        
        >>> p4.getHigherEnharmonic()
        Traceback (most recent call last):
        AccidentalException: -5 is not a supported accidental type
        
        '''
        intervalObj = interval.Interval('d2')
        octaveStored = self.octave # may be None
        if not inPlace:
            post = intervalObj.transposePitch(self, maxAccidental=None)
            if octaveStored is None:
                post.octave = None
            return post
        else:
            p = intervalObj.transposePitch(self, maxAccidental=None)
            self._setName(p.nameWithOctave)
            self.accidental = p.accidental
            if octaveStored is None:
                self.octave = None
            return None
    
    def getLowerEnharmonic(self, inPlace=False):
        '''
        returns a Pitch enharmonic note that is a diminished second 
        below the current note
        
        If `inPlace` is set to true, changes the current Pitch.
        
        
        >>> from music21 import *
        >>> p1 = pitch.Pitch('C-3')
        >>> p2 = p1.getLowerEnharmonic()
        >>> p2
        B2

        >>> p1 = pitch.Pitch('C#3')
        >>> p1.getLowerEnharmonic(inPlace=True)
        >>> p1
        B##2
        '''
        intervalObj = interval.Interval('-d2')
        octaveStored = self.octave # may be None
        if not inPlace:
            post = intervalObj.transposePitch(self)
            if octaveStored is None:
                post.octave = None
            return post
        else:
            p = intervalObj.transposePitch(self)
            self._setName(p.nameWithOctave)
            self.accidental = p.accidental
            if octaveStored is None:
                self.octave = None
            return None

    def simplifyEnharmonic(self, inPlace=False):
        '''
        Returns a new Pitch (or sets the current one if inPlace is True)
        that is either the same as the current pitch or has fewer
        sharps or flats if possible.  For instance, E# returns F,
        while A# remains A# (i.e., does not take into account that B- is
        more common than A#).  Useful to call if you ever have an
        algorithm that might take your piece far into the realm of
        double or triple flats or sharps.
        
        TODO: should be called automatically after ChromaticInterval
        transpositions.
        
        >>> from music21 import *
        >>> p1 = pitch.Pitch("B#5")
        >>> p1.simplifyEnharmonic().nameWithOctave
        'C6'
        
        >>> p2 = pitch.Pitch("A#2")
        >>> p2.simplifyEnharmonic(inPlace = True)
        >>> p2
        A#2
        
        >>> p3 = pitch.Pitch("E--3")
        >>> p4 = p3.transpose(interval.Interval('-A5'))
        >>> p4.simplifyEnharmonic()
        F#2

        
        Note that pitches with implicit octaves retain their implicit octaves.
        This might change the pitch space for B#s and C-s.


        >>> pList = [pitch.Pitch("B"), pitch.Pitch("C#"), pitch.Pitch("G"), pitch.Pitch("A--")]
        >>> [p.simplifyEnharmonic() for p in pList]
        [B, C#, G, G]


        >>> pList = [pitch.Pitch("C-"), pitch.Pitch("B#")]
        >>> [p.ps for p in pList]
        [59.0, 72.0]
        >>> [p.simplifyEnharmonic().ps for p in pList]
        [71.0, 60.0]

        '''

        if inPlace:
            returnObj = self
        else:
            returnObj = copy.deepcopy(self)

        if returnObj.accidental != None:
            if abs(returnObj.accidental.alter) < 2.0 and \
                returnObj.name not in ('E#', 'B#', 'C-', 'F-'):
                pass
            else:
                # by reseting the pitch space value, we will get a simplyer
                # enharmonic spelling
                saveOctave = self.octave
                returnObj.ps = self.ps
                if saveOctave is None:
                    returnObj.octave = None
        if inPlace:
            return None
        else:
            return returnObj


    def getEnharmonic(self, inPlace=False):
        '''Returns a new Pitch that is the(/an) enharmonic equivalent of this Pitch.
    
        N.B.: n1.name == getEnharmonic(getEnharmonic(n1)).name is not necessarily true.
        For instance: getEnharmonic(E##) => F#; getEnharmonic(F#) => G-
                  or: getEnharmonic(A--) => G; getEnharmonic(G) => F##
        However, for all cases not involving double sharps or flats (and even many that do)
        getEnharmonic(getEnharmonic(n)) = n
    
        Enharmonics of the following are defined:
               C <-> B#, D <-> C##, E <-> F-; F <-> E#, G <-> F##, A <-> B--, B <-> C-
    
        However, isEnharmonic() for A## and B certainly returns true.
    
        OMIT_FROM_DOCS
        Perhaps a getFirstNEnharmonics(n) needs to be defined which returns a list of the
        first n Enharmonics according to a particular algorithm, moving into triple sharps, etc.
        if need be.  Or getAllCommonEnharmonics(note) which returns all possible enharmonics that
        do not involve triple or more accidentals.

        >>> from music21 import *
        >>> p = pitch.Pitch('d#')
        >>> p.getEnharmonic()
        E-
        >>> p = pitch.Pitch('e-8')
        >>> p.getEnharmonic()
        D#8
        >>> pitch.Pitch('c-3').getEnharmonic()
        B2
        >>> pitch.Pitch('e#2').getEnharmonic()
        F2
        >>> pitch.Pitch('f#2').getEnharmonic()
        G-2
        >>> pitch.Pitch('c##5').getEnharmonic()
        D5
        >>> pitch.Pitch('g3').getEnharmonic() # presently does not alter
        G3
        >>> p = pitch.Pitch('a-')
        >>> p.getEnharmonic() # should not have octave
        G#
        '''
        psRef = self.ps
        if inPlace:
            post = self
        else:
            post = copy.deepcopy(self)

        if post.accidental != None:
            if post.accidental.alter > 0:
                # we have a sharp, need to get the equivalent flat
                post.getHigherEnharmonic(inPlace=True)
            elif post.accidental.alter < 0:
                post.getLowerEnharmonic(inPlace=True)
            else: # assume some direction, perhaps using a dictionary
                post.getLowerEnharmonic(inPlace=True)

        if inPlace:
            return None
        else:
            return post
        

# not sure these are necessary
# def getQuarterToneEnharmonic(note1):
#     '''like getEnharmonic but handles quarterTones as well'''
#     pass
# 
# def flipQuarterToneEnharmonic(note1):
#     pass
# 
# def areQuarterToneEnharmonics(note1, note2):
#     pass



    #---------------------------------------------------------------------------
    def _getDiatonicNoteNum(self):
        '''
        Returns (or takes) an integer that uniquely identifies the 
        diatonic version of a note, that is ignoring accidentals.
        The number returned is the diatonic interval above C0 (the lowest C on
        a Boesendorfer Imperial Grand), so G0 = 5, C1 = 8, etc.
        Numbers can be negative for very low notes.        
        
        C4 (middleC) = 29, C#4 = 29, C##4 = 29, D-4 = 30, D4 = 30, etc.
        
        >>> from music21 import *
        >>> c = pitch.Pitch('c4')
        >>> c.diatonicNoteNum
        29
        >>> c = pitch.Pitch('c#4')
        >>> c.diatonicNoteNum
        29
        >>> d = pitch.Pitch('d--4')
        >>> d.accidental.name
        'double-flat'
        >>> d.diatonicNoteNum
        30
        >>> lowc = pitch.Pitch('c1')
        >>> lowc.diatonicNoteNum
        8

        >>> b = pitch.Pitch()
        >>> b.step = "B"
        >>> b.octave = -1 
        >>> b.diatonicNoteNum
        0
        >>> c = pitch.Pitch("C")
        >>> c.diatonicNoteNum  #implicitOctave
        29

        >>> lowDSharp = pitch.Pitch("C#7") # start high !!!
        >>> lowDSharp.diatonicNoteNum = 9  # move low
        >>> lowDSharp.octave
        1
        >>> lowDSharp.name
        'D#'

        OMIT_FROM_DOCS
        
        >>> lowlowA = pitch.Pitch("A")
        >>> lowlowA.octave = -1
        >>> lowlowA.diatonicNoteNum
        -1
        
        >>> lowlowlowD = pitch.Pitch("D")
        >>> lowlowlowD.octave = -3
        >>> lowlowlowD.diatonicNoteNum
        -19
        
        '''
        if ['C','D','E','F','G','A','B'].count(self.step.upper()):
            noteNumber = ['C','D','E','F','G','A','B'].index(self.step.upper())
            return (noteNumber + 1 + (7 * self.implicitOctave))
        else:
            raise PitchException("Could not find " + self.step + " in the index of notes") 

    def _setDiatonicNoteNum(self, newNum):
        octave = int((newNum-1)/7)
        noteNameNum = newNum - 1 - (7*octave)
        pitchList = ['C','D','E','F','G','A','B']
        noteName = pitchList[noteNameNum]
        self.octave = octave
        self.step = noteName
        return self

    diatonicNoteNum = property(_getDiatonicNoteNum, _setDiatonicNoteNum,
        doc = _getDiatonicNoteNum.__doc__)

                                    
    def transpose(self, value, inPlace=False):
        '''Transpose the pitch by the user-provided value. 
        If the value is an integer, the transposition is 
        treated in half steps. If the value is a string, 
        any Interval string specification can be provided. 
        Alternatively, a :class:`music21.interval.Interval` 
        object can be supplied.

        >>> from music21 import *
        >>> aPitch = pitch.Pitch('g4')
        >>> bPitch = aPitch.transpose('m3')
        >>> bPitch
        B-4
        >>> aInterval = interval.Interval(-6)
        >>> bPitch = aPitch.transpose(aInterval)
        >>> bPitch
        C#4
        
        >>> aPitch
        G4
        >>> aPitch.transpose(aInterval, inPlace=True)
        >>> aPitch
        C#4
        
        OMIT_FROM_DOCS
        
        Test to make sure that extreme ranges work
        >>> dPitch = pitch.Pitch('D2')
        >>> lowC = dPitch.transpose('m-23')
        >>> lowC
        C#-1
        '''
        #environLocal.printDebug(['Pitch.transpose()', value])
        if hasattr(value, 'diatonic'): # its an Interval class with a DiatonicInterval class
            intervalObj = value
        else: # try to process
            intervalObj = interval.Interval(value)
        if not inPlace:
            return intervalObj.transposePitch(self)
        else:
            p = intervalObj.transposePitch(self)
            # can setName with nameWithOctave to recreate all essential
            # pitch attributes
            # NOTE: in some cases this may not return exactly the proper config
            
            # TODO -- DOES NOT WORK IF OCTAVE IS NEGATIVE.  A, -2 = A-flat 2!
            self._setName(p.name)
            self._setOctave(p.octave)
            # manually copy accidental object
            self.accidental = p.accidental
            return None

    #---------------------------------------------------------------------------
    # utilities for pitch object manipulation

    def transposeBelowTarget(self, target, minimize=False):
        '''Given a source Pitch, shift it down octaves until it is below the target. Note: this manipulates src inPlace.
    
        If `minimize` is True, a pitch below the the target will move up to the nearest octave. 

        >>> from music21 import *
        >>> pitch.Pitch('g5').transposeBelowTarget(pitch.Pitch('c#4'))
        G3
        >>> # if already below the target, make no change
        >>> pitch.Pitch('g#3').transposeBelowTarget(pitch.Pitch('c#6'))
        G#3
        >>> # accept the same pitch
        >>> pitch.Pitch('g#8').transposeBelowTarget(pitch.Pitch('g#1'))
        G#1

        >>> pitch.Pitch('g#2').transposeBelowTarget(pitch.Pitch('f#8'))
        G#2
        >>> pitch.Pitch('g#2').transposeBelowTarget(pitch.Pitch('f#8'), minimize=True)
        G#7
        >>> pitch.Pitch('f#2').transposeBelowTarget(pitch.Pitch('f#8'), minimize=True)
        F#8
        '''
        # TODO: add inPlace as an option, default is True
        src = self
        while True:
            # ref 20, min 10, lower ref
            # ref 5, min 10, do not lower
            if src.ps - target.ps <= 0:
                break
            # lower one octave
            src.octave -= 1

        # case where self is below target and minimize is True
        if minimize:
            while True:
                if target.ps - src.ps < 12:
                    break
                else:
                    src.octave += 1


        return src
    
    
    def transposeAboveTarget(self, target, minimize=False):
        '''Given a source Pitch, shift it up octaves until it is above the target. Note: this manipulates src inPlace.

        If `minimize` is True, a pitch above the the target will move down to the nearest octave. 

        >>> from music21 import *
        >>> pitch.Pitch('d2').transposeAboveTarget(pitch.Pitch('e4'))
        D5
        >>> # if already above the target, make no change
        >>> pitch.Pitch('d7').transposeAboveTarget(pitch.Pitch('e2'))
        D7
        >>> # accept the same pitch
        >>> pitch.Pitch('d2').transposeAboveTarget(pitch.Pitch('d8'))
        D8

        >>> # if minimize is True, we go the closest position
        >>> pitch.Pitch('d#8').transposeAboveTarget(pitch.Pitch('d2'), minimize=True)
        D#2
        >>> pitch.Pitch('d7').transposeAboveTarget(pitch.Pitch('e2'), minimize=True)
        D3
        >>> pitch.Pitch('d0').transposeAboveTarget(pitch.Pitch('e2'), minimize=True)
        D3

        '''
        src = self
        # case where self is below target
        while True:
            # ref 20, max 10, do not raise ref
            # ref 5, max 10, raise ref to above max
            if src.ps - target.ps >= 0:
                break
            # raise one octave
            src.octave += 1

        # case where self is above target and minimize is True
        if minimize:
            while True:
                if src.ps - target.ps < 12:
                    break
                else:
                    src.octave -= 1 


        return src
    
    

    #---------------------------------------------------------------------------

    def inheritDisplay(self, other):
        '''Inherit display properties from another Pitch, including those found on the Accidental object.

        >>> from music21 import *

        >>> a = pitch.Pitch('c#')
        >>> a.accidental.displayType = 'always'
        >>> b = pitch.Pitch('c-')
        >>> b.inheritDisplay(a)
        >>> b.accidental.displayType
        'always'

        '''
        # if other.accidental is None no problem
        if self._accidental != None:
            self._accidental.inheritDisplay(other.accidental)



#     def updateAccidentalKeySignature(self, alteredPitches=[], 
#         overrideStatus=False):
#         '''Given the pitches in a key signature, adjust the display of
#         this accidental. To get the pitches from a :class:`music21.key.KeySignature`, use the :attr:`~music21.key.KeySignature.alteredPitches` property.
# 
#         Note: this will only set the status of the present Accidental; this will not provide cautionary Accidentals. for that, use updateAccidentalDisplay() method.
#         '''
#         if overrideStatus == False: # go with what we have defined
#             if self.accidental == None:
#                 pass # no accidental defined; we may need to add one
#             elif (self.accidental != None and 
#             self.accidental.displayStatus == None): # not set; need to set  
#                 # configure based on displayStatus alone, continue w/ normal
#                 pass
#             elif (self.accidental != None and 
#             self.accidental.displayStatus in [True, False]): 
#                 return # exit: already set, do not override
# 
#         for p in alteredPitches: # all are altered tones, must have acc
#             if p.step == self.step: # A# to A or A# to A-, etc
#                 # we have an altered tone in key sig but none here;
#                 # we need a natural 
#                 if self.accidental == None: 
#                     self.accidental = Accidental('natural')
#                     self.accidental.displayStatus = True 
#                 # a different accidental, do need to show
#                 elif self.accidental.name != p.accidental.name: 
#                     self.accidental.displayStatus = True 
#                 # the same accidental, do not need to show
#                 elif self.accidental.name == p.accidental.name: 
#                     self.accidental.displayStatus = False
#                 break # only looking for one match
#                 

    def _nameInKeySignature(self, alteredPitches):
        '''Determine if this pitch is in the collection of supplied altered pitches, derived from a KeySignature object

        >>> from music21 import *
        >>> a = pitch.Pitch('c#')
        >>> b = pitch.Pitch('g#')
        >>> ks = key.KeySignature(2)
        >>> a._nameInKeySignature(ks.alteredPitches)
        True
        >>> b._nameInKeySignature(ks.alteredPitches)
        False
        ''' 
        for p in alteredPitches: # all are altered tones, must have acc
            if p.step == self.step: # A# to A or A# to A-, etc
                if p.accidental.name == self.accidental.name:
                    return True
        return False

    def _stepInKeySignature(self, alteredPitches):
        '''Determine if this pitch is in the collection of supplied altered pitches, derived from a KeySignature object

        >>> from music21 import *
        >>> a = pitch.Pitch('c')
        >>> b = pitch.Pitch('g')
        >>> ks = key.KeySignature(2)
        >>> a._stepInKeySignature(ks.alteredPitches)
        True
        >>> b._stepInKeySignature(ks.alteredPitches)
        False
        ''' 
        for p in alteredPitches: # all are altered tones, must have acc
            if p.step == self.step: # A# to A or A# to A-, etc
                return True
        return False



    def setAccidentalDisplay(self, value=None):
        '''If this Pitch has an accidental, set its displayStatus, which can be True, False, or None. 

        >>> from music21 import *

        >>> a = pitch.Pitch('a')
        >>> past = [pitch.Pitch('a#'), pitch.Pitch('c#'), pitch.Pitch('c')]
        >>> a.updateAccidentalDisplay(past, cautionaryAll=True)
        >>> a.accidental, a.accidental.displayStatus
        (<accidental natural>, True)
        >>> a.setAccidentalDisplay(None)
        >>> a.accidental, a.accidental.displayStatus
        (<accidental natural>, None)
        '''
        if self.accidental != None:
            self.accidental.displayStatus = value 


    def updateAccidentalDisplay(self, pitchPast=[], alteredPitches=[],
            cautionaryPitchClass=True, cautionaryAll=False, 
            overrideStatus=False, cautionaryNotImmediateRepeat=True):
        '''
        Given a list of Pitch objects in `pitchPast`, 
        determine if this pitch's Accidental object needs 
        to be created or updated with a natural or other cautionary accidental.


        Changes to this Pitch object's Accidental object are made in-place.


        The `alteredPitches` list supplies pitches from a :class:`music21.key.KeySignature` object using the :attr:`~music21.key.KeySignature.alteredPitches` property. 


        If `cautionaryPitchClass` is True, comparisons to past accidentals are made regardless of register. That is, if a past sharp is found two octaves above a present natural, a natural sign is still displayed. 


        If `overrideStatus` is True, this method will ignore any current `displayStatus` stetting found on the Accidental. By default this does not happen. If `displayStatus` is set to None, the Accidental's `displayStatus` is set. 


        If `cautionaryNotImmediateRepeat` is True, cautionary accidentals will be displayed for an altered pitch even if that pitch had already been displayed as altered. 

        >>> from music21 import *

        >>> a = pitch.Pitch('a')
        >>> past = [pitch.Pitch('a#'), pitch.Pitch('c#'), pitch.Pitch('c')]
        >>> a.updateAccidentalDisplay(past, cautionaryAll=True)
        >>> a.accidental, a.accidental.displayStatus
        (<accidental natural>, True)

        >>> b = pitch.Pitch('a')
        >>> past = [pitch.Pitch('a#'), pitch.Pitch('c#'), pitch.Pitch('c')]
        >>> b.updateAccidentalDisplay(past) # should add a natural
        >>> b.accidental, b.accidental.displayStatus
        (<accidental natural>, True)

        >>> c = pitch.Pitch('a4')
        >>> past = [pitch.Pitch('a#3'), pitch.Pitch('c#'), pitch.Pitch('c')]
        >>> # will not add a natural because match is pitchSpace
        >>> c.updateAccidentalDisplay(past, cautionaryPitchClass=False)
        >>> c.accidental == None
        True

        '''
        # TODO: this presently deals with chords as simply a list
        # we might permit pitchPast to contain a list of pitches, to represent
        # a simultaneity?


        if overrideStatus == False: # go with what we have defined
            if self.accidental == None:
                pass # no accidental defined; we may need to add one
            elif (self.accidental != None and 
                self.accidental.displayStatus == None): # not set; need to set  
                # configure based on displayStatus alone, continue w/ normal
                pass
            elif (self.accidental != None and 
                self.accidental.displayStatus in [True, False]): 
                return # exit: already set, do not override

        if len(pitchPast) == 0:
            # if we have no past, we always need to show the accidental, 
            # unless this accidental is in the alteredPitches list
            if (self.accidental != None 
            and self.accidental.displayStatus in [False, None]):
                if not self._nameInKeySignature(alteredPitches):
                    self.accidental.displayStatus = True
                else:
                    self.accidental.displayStatus = False

            # in case display set to True and in alteredPitches, makeFalse
            elif (self.accidental != None and 
            self.accidental.displayStatus == True and
            self._nameInKeySignature(alteredPitches)):
                self.accidental.displayStatus = False

            # if no accidental or natural but matches step in key sig
            # we need to show or add or an accidental
            elif ((self.accidental == None or self.accidental.name == 'natural')
            and self._stepInKeySignature(alteredPitches)):
                if self.accidental == None:
                    self.accidental = Accidental('natural')
                self.accidental.displayStatus = True

            return # do not search past

        # here tied and always are treated the same; we assume that
        # making ties sets the displayStatus, and thus we would not be 
        # overriding that display status here
        if cautionaryAll or (self.accidental != None 
        and self.accidental.displayType in ['even-tied', 'always']): 
            # show all no matter
            if self.accidental == None:
                self.accidental = Accidental('natural')
            # show all accidentals, even if past encountered
            self.accidental.displayStatus = True
            return # do not search past

        iNearest = len(pitchPast) - 1
        # store if a match was found and display set from past pitches
        setFromPitchPast = False 

        # need to step through pitchPast in reverse
        # comparing this pitch to the past pitches; if we find a match
        # in terms of name, then decide what to do
        for i in reversed(range(len(pitchPast))): 
            # create Pitch objects for comparison; remove pitch space
            # information if we are only doing a pitch class comparison
            if cautionaryPitchClass: # no octave; create new without oct
                pPast = Pitch(pitchPast[i].name)
                pSelf = Pitch(self.name)
                # must manually assign reference to the same accidentals
                # as name alone will not transfer display status
                pPast.accidental = pitchPast[i].accidental
                pSelf.accidental = self.accidental
            else: # cautionary in terms of pitch space; must match exact
                pPast = pitchPast[i]
                pSelf = self

            # if we do not match steps (A and A#), we can continue
            if pPast.stepWithOctave != pSelf.stepWithOctave:
                continue

            # store whether these match at the same octave; needed for some
            # comparisons even if not matching pitchSpace
            if self.octave == pitchPast[i].octave:
                octaveMatch = True
            else:
                octaveMatch = False

            # repeats of the same accidentally immediately following
            # if An to An or A# to A#: do not need unless repeats requested
            # regardless of if 'unless-repeated' is set, this will catch 
            # a repeated case
            
            if (i == iNearest and pPast.accidental != None 
            and pSelf.accidental != None 
            and pPast.accidental.name == pSelf.accidental.name):
                # if not in the same octave, and not in the key sig, do show accidental
                if (not self._nameInKeySignature(alteredPitches) 
                and not octaveMatch):
                    self.accidental.displayStatus = True
                else:
                    self.accidental.displayStatus = False
                setFromPitchPast = True
                break

            # if An to A: do not need another natural
            # yet, if we are against the key sig, then we need another natural
            # this may or may not be an immediate repeat of the same pitch
            elif (pPast.accidental != None 
            and pPast.accidental.name == 'natural' 
            and (pSelf.accidental == None 
            or pSelf.accidental.name == 'natural')):
                if i == iNearest: # an immediate repeat; do not show
                    # unless we are altering the key signature and in 
                    # a different register
                    if (self._stepInKeySignature(alteredPitches) 
                    and not octaveMatch):
                        if self.accidental == None:
                            self.accidental = Accidental('natural')
                        self.accidental.displayStatus = True
                    else:
                        if self.accidental != None:
                            self.accidental.displayStatus = False
                # if we match the step in a key signature and we want 
                # cautionary not immediate repeated
                elif (self._stepInKeySignature(alteredPitches) 
                and cautionaryNotImmediateRepeat):
                    if self.accidental == None:
                        self.accidental = Accidental('natural')
                    self.accidental.displayStatus = True
                # other cases: already natural in past usage, do not need 
                # natural again (and not in key sig)
                else:
                    if self.accidental != None:
                        self.accidental.displayStatus = False
                setFromPitchPast = True
                break

            # if A# to A, or A- to A, but not A# to A#
            # we use stepWithOctave though not necessarily a ps comparison
            elif (pPast.accidental != None 
            and pPast.accidental.name != 'natural' 
            and (pSelf.accidental == None 
            or pSelf.accidental.displayStatus == False)):
                if self.accidental == None:
                    self.accidental = Accidental('natural')
                self.accidental.displayStatus = True
                setFromPitchPast = True
                break

            # if An or A or to A#: need to make sure display is set
            elif ((pPast.accidental == None 
            or pPast.accidental.name == 'natural') and pSelf.accidental != None 
            and pSelf.accidental.name != 'natural'):
                self.accidental.displayStatus = True
                setFromPitchPast = True
                break

            # if A- or An to A#: need to make sure display is set
            elif (pPast.accidental != None and pSelf.accidental != None 
            and pPast.accidental.name != pSelf.accidental.name):
                self.accidental.displayStatus = True
                setFromPitchPast = True
                break

            # going from a natural to an accidental, we should already be
            # showing the accidental, but just to check
            # if A to A#, or A to A-, but not A# to A
            elif (pPast.accidental == None and pSelf.accidental != None):
                self.accidental.displayStatus = True
                #environLocal.printDebug(['match previous no mark'])
                setFromPitchPast = True
                break

            # if A# to A# and not immediately repeated:
            # default is to show accidental
            # if cautionaryNotImmediateRepeat is False, will not be shown
            elif (i != iNearest and pPast.accidental != None and
                pSelf.accidental != None and pPast.accidental.name == 
                pSelf.accidental.name):
                if not cautionaryNotImmediateRepeat: # do not show
                    # result will be False, do not need to check altered tones
                    self.accidental.displayStatus = False
                else:
                    if not self._nameInKeySignature(alteredPitches):
                        self.accidental.displayStatus = True
                    else:
                        self.accidental.displayStatus = False
                setFromPitchPast = True
                break
            else:
                pass

        # if we have no previous matches for this pitch and there is 
        # an accidental: show, unless in alteredPitches
        # cases of displayAlways and related are matched above
        if not setFromPitchPast and self.accidental != None:
            if not self._nameInKeySignature(alteredPitches):
                self.accidental.displayStatus = True
            else:
                self.accidental.displayStatus = False

        # if we have natural that alters the key sig, create a natural
        elif not setFromPitchPast and self.accidental == None:
            if self._stepInKeySignature(alteredPitches):
                self.accidental = Accidental('natural')
                self.accidental.displayStatus = True



#-------------------------------------------------------------------------------
class TestExternal(unittest.TestCase):
    
    def runTest(self):
        pass
    
    def testSingle(self):
        a = Pitch()
        a.name = 'c#'
        a.show()



class Test(unittest.TestCase):
    
    def runTest(self):
        pass

    def testCopyAndDeepcopy(self):
        '''Test copying all objects defined in this module
        '''
        import sys, types, copy
        for part in sys.modules[self.__module__].__dict__.keys():
            match = False
            for skip in ['_', '__', 'Test', 'Exception']:
                if part.startswith(skip) or part.endswith(skip):
                    match = True
            if match:
                continue
            name = getattr(sys.modules[self.__module__], part)
            if callable(name) and not isinstance(name, types.FunctionType):
                try: # see if obj can be made w/ args
                    obj = name()
                except TypeError:
                    continue
                a = copy.copy(obj)
                b = copy.deepcopy(obj)

        p1 = Pitch("C#3")
        p2 = copy.deepcopy(p1)
        self.assertTrue(p1 is not p2)
        self.assertTrue(p1.accidental is not p2.accidental)


    def testOctave(self):
        b = Pitch("B#3")
        self.assertEqual(b.octave, 3)
    

    def testAccidentalImport(self):
        '''Test that we are getting the properly set accidentals
        '''
        from music21 import corpus
        s = corpus.parseWork('bwv438.xml')
        tenorMeasures = s[2].getElementsByClass('Measure')
        pAltered = tenorMeasures[0].pitches[1]
        self.assertEqual(pAltered.accidental.name, 'flat')
        self.assertEqual(pAltered.accidental.displayType, 'normal')
        # in key signature, so shuold not be shown
        self.assertEqual(pAltered.accidental.displayStatus, False)

        altoMeasures = s[1].getElementsByClass('Measure')
        pAltered = altoMeasures[6].pitches[2]
        self.assertEqual(pAltered.accidental.name, 'sharp')
        self.assertEqual(pAltered.accidental.displayStatus, True)


    def testUpdateAccidentalDisplaySimple(self):
        '''Test updating accidental display.
        '''

        past = [Pitch('a3#'), Pitch('c#'), Pitch('c')]

        a = Pitch('c')
        a.accidental = Accidental('natural')
        a.accidental.displayStatus = False # hide
        self.assertEqual(a.name, 'C')
        self.assertEqual(a.accidental.displayStatus, False)

        a.updateAccidentalDisplay(past, overrideStatus=True)
        self.assertEqual(a.accidental.displayStatus, True)


        b = copy.deepcopy(a)
        self.assertEqual(b.accidental.displayStatus, True)
        self.assertEqual(b.accidental.name, 'natural')




    def testUpdateAccidentalDisplaySeries(self):
        '''Test updating accidental display.
        '''

        def proc(pList, past=[]):
            for p in pList:
                p.updateAccidentalDisplay(past)
                past.append(p)

        def compare(past, result):
            #environLocal.printDebug(['accidental compare'])
            for i in range(len(result)):
                p = past[i]
                if p.accidental == None:
                    pName = None
                    pDisplayStatus = None
                else:
                    pName = p.accidental.name
                    pDisplayStatus = p.accidental.displayStatus

                targetName = result[i][0]
                targetDisplayStatus = result[i][1]

                #environLocal.printDebug(['accidental test:', p, pName, pDisplayStatus, 'target:', targetName, targetDisplayStatus]) # test
                self.assertEqual(pName, targetName)
                self.assertEqual(pDisplayStatus, targetDisplayStatus)

        # alternating, in a sequence, same pitch space
        pList = [Pitch('a#3'), Pitch('a3'), Pitch('a#3'), 
        Pitch('a3'), Pitch('a#3')]
        result = [('sharp', True), ('natural', True), ('sharp', True), 
        ('natural', True), ('sharp', True)]
        proc(pList, [])        
        compare(pList, result)

        # alternating, in a sequence, different pitch space
        pList = [Pitch('a#2'), Pitch('a6'), Pitch('a#1'), 
        Pitch('a5'), Pitch('a#3')]
        result = [('sharp', True), ('natural', True), ('sharp', True), 
        ('natural', True), ('sharp', True)]
        proc(pList, [])        
        compare(pList, result)

        # alternating, after gaps
        pList = [Pitch('a-2'), Pitch('g3'), Pitch('a5'), 
        Pitch('a#5'), Pitch('g-3'), Pitch('a3')]
        result = [('flat', True), (None, None), ('natural', True), 
        ('sharp', True), ('flat', True), ('natural', True)]
        proc(pList, [])        
        compare(pList, result)

        # repeats of the same: show at different registers
        pList = [Pitch('a-2'), Pitch('a-2'), Pitch('a-5'), 
        Pitch('a#5'), Pitch('a#3'), Pitch('a3'), Pitch('a2')]
        result = [('flat', True), ('flat', False), ('flat', True), 
        ('sharp', True), ('sharp', True), ('natural', True), (None, None)]
        proc(pList, [])        
        compare(pList, result)

        #the always- 'unless-repeated' setting 
        # first, with no modification, repeated accidentals are not shown
        pList = [Pitch('a-2'), Pitch('a#3'), Pitch('a#5')]
        result = [('flat', True), ('sharp', True), ('sharp', True)]
        proc(pList, [])        
        compare(pList, result)

        # second, with status set to always 
        pList = [Pitch('a-2'), Pitch('a#3'), Pitch('a#3')]
        pList[2].accidental.displayType = 'always'
        result = [('flat', True), ('sharp', True), ('sharp', True)]
        proc(pList, [])        
        compare(pList, result)

        # status set to always 
        pList = [Pitch('a2'), Pitch('a3'), Pitch('a5')]
        pList[2].accidental = Accidental('natural')
        pList[2].accidental.displayType = 'always'
        result = [(None, None), (None, None), ('natural', True)]
        proc(pList, [])        
        compare(pList, result)

        # first use after other pitches in different register
        # note: this will force the display of the accidental
        pList = [Pitch('a-2'), Pitch('g3'), Pitch('a-5')]
        result = [('flat', True), (None, None), ('flat', True)]
        proc(pList, [])        
        compare(pList, result)

        # first use after other pitches in different register
        # note: this will force the display of the accidental
        pList = [Pitch('a-2'), Pitch('g3'), Pitch('a-2')]
        # pairs of accidental, displayStatus
        result = [('flat', True), (None, None), ('flat', True)]
        proc(pList, [])        
        compare(pList, result)


        # accidentals, first usage, not first pitch
        pList = [Pitch('a2'), Pitch('g#3'), Pitch('d-2')]
        result = [(None, None), ('sharp', True), ('flat', True)]
        proc(pList, [])        
        compare(pList, result)



    def testUpdateAccidentalDisplaySeriesKeySignature(self):
        '''Test updating accidental display.
        '''
        from music21 import key

        def proc(pList, past=[], alteredPitches=[]):
            for p in pList:
                p.updateAccidentalDisplay(past, alteredPitches=alteredPitches)
                past.append(p)

        def compare(past, result):
            #environLocal.printDebug(['accidental compare'])
            for i in range(len(result)):
                p = past[i]
                if p.accidental == None:
                    pName = None
                    pDisplayStatus = None
                else:
                    pName = p.accidental.name
                    pDisplayStatus = p.accidental.displayStatus

                targetName = result[i][0]
                targetDisplayStatus = result[i][1]

                #environLocal.printDebug(['accidental test:', p, pName, pDisplayStatus, 'target:', targetName, targetDisplayStatus]) # test
                self.assertEqual(pName, targetName)
                self.assertEqual(pDisplayStatus, targetDisplayStatus)

        # chromatic alteration of key
        pList = [Pitch('f#3'), Pitch('f#2'), Pitch('f3'), 
            Pitch('f#3'), Pitch('f#3'), Pitch('g3'), Pitch('f#3')]
        result = [('sharp', False), ('sharp', False), ('natural', True), 
            ('sharp', True), ('sharp', False), (None, None), ('sharp', False)]
        ks = key.KeySignature(1) # f3
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)

        # non initial scale tones
        pList = [Pitch('a3'), Pitch('b2'), Pitch('c#3'), 
            Pitch('f#3'), Pitch('g#3'), Pitch('f#3'), Pitch('a4')]
        result = [(None, None), (None, None), ('sharp', False), 
            ('sharp', False), ('sharp', False), ('sharp', False), (None, None)]
        ks = key.KeySignature(3) 
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)

        # non initial scale tones with chromatic alteration
        pList = [Pitch('a3'), Pitch('c#3'), Pitch('g#3'), 
        Pitch('g3'), Pitch('c#4'), Pitch('g#4')]
        result = [(None, None), ('sharp', False), ('sharp', False), 
            ('natural', True), ('sharp', False), ('sharp', True)]
        ks = key.KeySignature(3) 
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)

        # non initial scale tones with chromatic alteration
        pList = [Pitch('a3'), Pitch('c#3'), Pitch('g#3'), 
        Pitch('g3'), Pitch('c#4'), Pitch('g#4')]
        result = [(None, None), ('sharp', False), ('sharp', False), 
            ('natural', True), ('sharp', False), ('sharp', True)]
        ks = key.KeySignature(3) 
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)

        # initial scale tones with chromatic alteration, repeated tones
        pList = [Pitch('f#3'), Pitch('f3'), Pitch('f#3'), 
        Pitch('g3'), Pitch('f#4'), Pitch('f#4')]
        result = [('sharp', False), ('natural', True), ('sharp', True), 
            (None, None), ('sharp', False), ('sharp', False)]
        ks = key.KeySignature(1) 
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)

        # initial scale tones with chromatic alteration, repeated tones
        pList = [Pitch('d3'), Pitch('e3'), Pitch('f#3'), 
        Pitch('g3'), Pitch('f4'), Pitch('g#4'),
        Pitch('c#3'), Pitch('f#4'), Pitch('c#4')]
        result = [(None, None), (None, None), ('sharp', False), 
            (None, None), ('natural', True), ('sharp', True),
            ('sharp', False), ('sharp', True), ('sharp', False)]
        ks = key.KeySignature(2) 
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)

        # altered tones outside of key
        pList = [Pitch('b3'), Pitch('a3'), Pitch('e3'), 
        Pitch('b-3'), Pitch('a-3'), Pitch('e-3'), 
        Pitch('b-3'), Pitch('a-3'), Pitch('e-3'),
        Pitch('b-3'), Pitch('a-3'), Pitch('e-3')]
        result = [('natural', True), ('natural', True), ('natural', True), 
            ('flat', True), ('flat', True), ('flat', True),
            ('flat', False), ('flat', False), ('flat', False),
            ('flat', False), ('flat', False), ('flat', False),]
        ks = key.KeySignature(-3) # b-, e-, a- 
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)


        # naturals against the key signature are required for each and every use
        pList = [Pitch('b3'), Pitch('a3'), Pitch('e3'), 
        Pitch('b4'), Pitch('a-3'), Pitch('e-3'), 
        Pitch('b3'), Pitch('a3'), Pitch('e3')]
        result = [('natural', True), ('natural', True), ('natural', True), 
            ('natural', True), ('flat', True), ('flat', True),
            ('natural', True), ('natural', True), ('natural', True)]
        ks = key.KeySignature(-3) # b-, e-, a- 
        proc(pList, [], ks.alteredPitches)        
        compare(pList, result)






    def testPitchEquality(self):
        '''Test updating accidental display.
        '''
        data = [('a', 'b', False), ('a', 'a', True), ('a#', 'a', False),
                ('a#', 'b-', False), ('a#', 'a-', False), ('a##', 'a#', False),
            ('a#4', 'a#4', True), ('a-3', 'a-4', False), ('a#3', 'a#4', False),
            ]
        for x, y, match in data:
            p1 = Pitch(x)
            p2 = Pitch(y)
            self.assertEqual(p1==p2, match)

        # specific case of changing octave
        p1 = Pitch('a#')
        p2 = Pitch('a#')
        self.assertEqual(p1==p2, True)

        p1.octave = 4
        p2.octave = 3
        self.assertEqual(p1==p2, False)
        p1.octave = 4
        p2.octave = 4
        self.assertEqual(p1==p2, True)

    def testLowNotes(self):
        dPitch = Pitch('D2')
        lowC = dPitch.transpose('M-23')
        self.assertEqual(lowC.name, "C")
        self.assertEqual(lowC.octave, -1)


    def testQuarterToneA(self):
        import stream, note, scale, pitch

        p1 = Pitch('D#~')
        #environLocal.printDebug([p1, p1.accidental])
        self.assertEqual(str(p1), 'D#~')
        # test generation of raw musicxml output
        xmlout = p1.musicxml
        #p1.show()
        match = '<step>D</step><alter>1.5</alter><octave>4</octave>'
        xmlout = xmlout.replace(' ', '')
        xmlout = xmlout.replace('\n', '')
        self.assertEqual(xmlout.find(match), 621)

        s = stream.Stream()
        for pStr in ['A~', 'A#~', 'A`', 'A-`']:
            p = Pitch(pStr)
            self.assertEqual(str(p), pStr)
            n = note.Note()
            n.pitch = p
            s.append(n)
        self.assertEqual(len(s), 4)
        match = [e.ps for e in s]
        self.assertEqual(match, [69.5, 70.5, 68.5, 67.5] )

        s = stream.Stream()
        alterList = [None, .5, 1.5, -1.5, -.5, 'half-sharp', 'one-and-a-half-sharp', 'half-flat', 'one-and-a-half-flat', '~']
        sc = scale.MajorScale('c4')
        for x in range(1, 10):
            n = note.Note(sc.pitchFromDegree(x % sc.getDegreeMaxUnique()))
            n.quarterLength = .5
            n.pitch.accidental = pitch.Accidental(alterList[x])
            s.append(n)

        match = [str(n.pitch) for n in s.notes]
        self.assertEqual(match, ['C~4', 'D#~4', 'E-`4', 'F`4', 'G~4', 'A#~4', 'B`4', 'C-`4', 'D~4'])

        
        match = [e.ps for e in s]
        self.assertEqual(match, [60.5, 63.5, 62.5, 64.5, 67.5, 70.5, 70.5, 58.5, 62.5] )


    def testMicrotoneA(self):
        
        from music21 import pitch


        #p = pitch.Pitch('a+25')
        
        
        #for name, ps in (['a+20', ])



#-------------------------------------------------------------------------------
# define presented order in documentation
_DOC_ORDER = [Pitch, Accidental]


if __name__ == "__main__":
    # sys.arg test options will be used in mainTest()
    music21.mainTest(Test)


#------------------------------------------------------------------------------
# eof

