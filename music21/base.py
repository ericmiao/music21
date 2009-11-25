#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:         base.py
# Purpose:      Music21 base classes and important utilities
#
# Authors:      Michael Scott Cuthbert
#               Christopher Ariza
#
# Copyright:    (c) 2009 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------

'''
Music21 base classes and important utilities

base -- the convention within music21 is that __init__ files contain:

   from base import *
   
so everything in this file can be accessed as music21.XXXX

'''


import copy
import unittest, doctest
import sys
import types
import time

from music21 import common
from music21 import environment
_MOD = 'music21.base.py'
environLocal = environment.Environment(_MOD)


#-------------------------------------------------------------------------------
class Music21Exception(Exception):
    pass

class LocationException(Exception):
    pass

class Music21ObjectException(Exception):
    pass

class ElementException(Exception):
    pass

class GroupException(Exception):
    pass

#-------------------------------------------------------------------------------
# make subclass of set once that is defined properly
class Groups(list):   
    '''A list of strings used to identify associations that an element might 
    have. Enforces that all elements must be strings
    
    >>> g = Groups()
    >>> g.append("hello")
    >>> g[0]
    'hello'
    
    >>> g.append(5)
    Traceback (most recent call last):
    GroupException: Only strings can be used as list names
    '''
    def append(self, value):
        if isinstance(value, basestring):
            list.append(self, value)
        else:
            raise GroupException("Only strings can be used as list names")
            

    def __setitem__(self, i, y):
        if isinstance(y, basestring):
            list.__setitem__(self, i, y)
        else:
            raise GroupException("Only strings can be used as list names")
        

    def __eq__(self, other):
        '''Test Group equality. In normal lists, order matters; here it does not. 

        >>> a = Groups()
        >>> a.append('red')
        >>> a.append('green')
        >>> b = Groups()
        >>> b.append('green')
        >>> b.append('red')
        >>> a == b
        True
        '''
        if not isinstance(other, Groups):
            return False
        if (list.sort(self) == other.sort()):
            return True
        else:
            return False

    def __ne__(self, other):
        '''In normal lists, order matters; here it does not. 
        '''

        if other == None or not isinstance(other, Groups):
            return True
        if (list.sort(self) == other.sort()):
            return False
        else:
            return True


#-------------------------------------------------------------------------------
class Location(object):
    '''An object, stored within a Music21Object, that manages site/offset pairs. Site is an object that contains an object; site may be a parent. Sites are always stored as weak refs.
    '''
    def __init__(self):
        self._coordinates = [] # a list of dictionaries

    def __len__(self):
        '''Return a list of all offsets.
        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 843)
        >>> aLocation.add(bSite, 12) # can add at same ofst
        >>> len(aLocation)
        2
        '''
        return len(self._coordinates)


    def scrubEmptySites(self):
        '''If a parent has been deleted, we will still have an empty ref in 
        _coordinates; when called, this empty ref will return None.
        This method will remove all parents that deref to None

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 0)
        >>> aLocation.add(bSite, 234) # can add at same ofst
        >>> del aSite
        >>> len(aLocation)
        2
        >>> aLocation.scrubEmptySites()
        >>> len(aLocation)
        1
        '''
        delList = []
        for i in range(len(self._coordinates)):
            if common.unwrapWeakref(self._coordinates[i]['site']) == None:        
                delList.append(i)
        delList.reverse() # go in reverse from largest to maintain positions
        for i in delList:
            del self._coordinates[i]

    def clear(self):
        '''Clear all data.
        '''
        self._coordinates = []

    def getSites(self):
        '''Get parents; unwrap from weakrefs
        '''
        #environLocal.printDebug([self._coordinates])
        return [common.unwrapWeakref(x['site']) for x in self._coordinates]   

    def getOffsets(self):
        '''Return a list of all offsets.

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 0)
        >>> aLocation.add(bSite, 234) # can add at same ofst
        >>> aLocation.getOffsets()
        [0, 234]
        '''
        return [x['offset'] for x in self._coordinates]   

    def getTimes(self):
        return [x['time'] for x in self._coordinates]   

    def add(self, site, offset):
        '''Add a location to the object.

        If site already exists, this will update that entry. Note: this could be modified to support multiple instanes of one site in the list.

        Might check/force site to be a Stream?

        Might automatically create a weakref of site?

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 23)
        >>> aLocation.add(bSite, 23) # can add at same ofst
        >>> aLocation.add(aSite, 12) # will resset the offset
        >>> aSite == aLocation.getSiteByOffset(12)
        True
        '''
        # compare unwrapped first
        sites = self.getSites()
        if site in sites: 
            #environLocal.printDebug(['site already defined in this Location object', site])
            # order is the same as in _coordinates
            i = sites.index(site)
        else:
            siteRef = common.wrapWeakref(site)
            self._coordinates.append({}) # great new
            i = -1 #now the last
            # site here is wrapped in weakref
            self._coordinates[i]['site'] = siteRef

        self._coordinates[i]['offset'] = offset
        # store creation time in order to sort by time
        self._coordinates[i]['time'] = time.time()


    def remove(self, site):
        '''Remove the entry specified by sites

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 23)
        >>> len(aLocation)
        1
        >>> aLocation.remove(aSite)
        >>> len(aLocation)
        0
        
        '''
        sites = self.getSites()
        if not site in sites: 
            raise LocationException('an entry for this object is not stored: %s' % site)
        del self._coordinates[sites.index(site)]


    def getOffsetBySite(self, site):
        '''For a given site return an offset.

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> cParent = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 23)
        >>> aLocation.add(bSite, 121.5)
        >>> aLocation.getOffsetBySite(aSite)
        23
        >>> aLocation.getOffsetBySite(bSite)
        121.5
        >>> aLocation.getOffsetBySite(cParent)    
        Traceback (most recent call last):
        LocationException: ...
        '''
        sites = self.getSites()
        if not site in sites: 
            raise LocationException('an entry for this object is not stored: %s' % site)

        match = None
        # assume that last added offset is more likely the first needed
        # access index values in reverse from highest to 0
        for i in range(len(self._coordinates)-1, -1, -1):
            # compare site to unwrapped site list
            if sites[i] == site: 
                match = self._coordinates[i]['offset']
                break
        return match # will be None if not match; could raise exception


    def getOffsetByIndex(self, index):
        '''For a given parent return an offset.

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 23)
        >>> aLocation.add(bSite, 121.5)
        >>> aLocation.getOffsetByIndex(-1)
        121.5
        >>> aLocation.getOffsetByIndex(2)
        Traceback (most recent call last):
        IndexError: list index out of range
        '''
        return self._coordinates[index]['offset']



    def getSiteByOffset(self, offset):
        '''For a given offset return the parent

        More than one parent may have the same offset; thus, may need to sort
        by some parameter.

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> cParent = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 23)
        >>> aLocation.add(bSite, 121.5)
        >>> aSite == aLocation.getSiteByOffset(23)
        True
        '''
        match = None
        # assume that last added offset is more likely the first needed
        # access index values in reverse from highest to 0
        for i in range(len(self._coordinates)-1, -1, -1):
            # might need to use almost equals here
            if self._coordinates[i]['offset'] == offset:
                match = self._coordinates[i]['site']
                break
        if match != None:
            if not common.isWeakref(match):
                raise LocationException('site on _coordinates is not a weak ref: %s' % match)
            return common.unwrapWeakref(match)
        else:
            # will be None if not match; could alternatively exception
            return match 


    def getSiteByIndex(self, index):
        '''Get parent by index value, unwrapping weak ref.

        >>> class Mock(object): pass
        >>> aSite = Mock()
        >>> bSite = Mock()
        >>> aLocation = Location()
        >>> aLocation.add(aSite, 23)
        >>> aLocation.add(bSite, 121.5)
        >>> bSite == aLocation.getSiteByIndex(-1)
        True
        '''
        siteRef = self._coordinates[index]['site']
        if siteRef == None: # let None parents pass
            return siteRef
        elif not common.isWeakref(siteRef):
            raise LocationException('parent on _coordinates is not a weak ref: %s' % siteRef)
        else:
            return common.unwrapWeakref(siteRef)





#-------------------------------------------------------------------------------
class Music21Object(object):
    '''
    Base class for all music21 objects
    
    All music21 objects encode 7 pieces of information:
    
    (1) id       : unique identification string (optional)
    (2) groups   : list of strings identifying internal subcollections
                   (voices, parts, selections) to which this element belongs
    (3) parent   : a reference or weakreference to a single containing object
    (4) duration : Duration object representing the length of the object
    
    each of these may be passed in as a named keyword to any music21 object.
    Some of these may be intercepted by the subclassing object (e.g., duration within Note)

    '''

    _duration = None
    # while testing .location
    #_parent = None
    contexts = None
    id = None
    _overriddenLily = None

    def __init__(self, *arguments, **keywords):

        self.location = Location()

        # an offset keyword arg should set the offset in location
        # not in a local parameter
#         if "offset" in keywords and not self.offset:
#             self.offset = keywords["offset"]

        if "id" in keywords and not self.id:
            self.id = keywords["id"]            
        
        if "duration" in keywords and self.duration is None:
            self.duration = keywords["duration"]
        
        if "groups" in keywords and keywords["groups"] is not None and \
            (not hasattr(self, "groups") or self.groups is None):
            self.groups = keywords["groups"]
        elif not hasattr(self, "groups"):
            self.groups = Groups()
        elif self.groups is None:
            self.groups = Groups()

        if "parent" in keywords and self.parent is None:
            self.parent = keywords["parent"]
        
        if "contexts" in keywords and keywords["contexts"] is not None and self.contexts is None:
            self.contexts = keywords["contexts"]
        elif self.contexts is None:
            self.contexts = []
    

    def copy(self):
        '''Return a shallow copy, or a linked reference to the source.'''
        return copy.copy(self)
    
    def deepcopy(self):
        '''
        Return a deep copy of an object with no reference to the source.
        The parent is not deep copied!

        >>> from music21 import note, duration
        >>> n = note.Note('A')
        >>> n.offset = 1.0 #duration.Duration("quarter")
        >>> n.groups.append("flute")
        >>> n.groups
        ['flute']

        >>> b = n.deepcopy()
        >>> b.offset = 2.0 #duration.Duration("half")
        
        >>> n is b
        False
        >>> n.accidental = "-"
        >>> b.name
        'A'
        >>> n.offset
        1.0
        >>> b.offset
        2.0
        >>> n.groups[0] = "bassoon"
        >>> ("flute" in n.groups, "flute" in b.groups)
        (False, True)
        '''
        psave = self.parent
        self.parent = None
        myCopy = copy.deepcopy(self)
        self.parent = psave
        myCopy.parent = psave
        return myCopy
    
    def isClass(self, className):
        '''
        returns bool depending on if the object is a particular class or not
        
        here, it just returns isinstance, but for Elements it will return true
        if the embedded object is of the given class.  Thus, best to use it throughout
        music21 and only use isinstance if you really want to see if something is
        an Element or not.
        '''
        if isinstance(self, className):
            return True
        else:
            return False

    
    #---------------------------------------------------------------------------
    # look at this object for an atttribute; if not here
    # look up to parents



    def searchParent(self, attrName):
        '''If this element is contained within a Stream or other Music21 element, searchParent() permits searching attributes of higher-level
        objects. The first encounted match is returned, or None if no match.
        '''
        found = None
        try:
            found = getattr(self.parent, attrName)
        except AttributeError:
            # not sure of passing here is the best action
            environLocal.printDebug(['searchParent call raised attribute error for attribte:', attrName])
            pass
        if found == None:
            found = self.parent.searchParent(attrName)
        return found
        
    #---------------------------------------------------------------------------
    # properties

    def _getParent(self):
        # return the last parent added to this location
        if len(self.location) == 0:
            return None # return None if no sites set
        else: 
            return self.location.getSiteByIndex(-1) 

#         return common.unwrapWeakref(self._parent)
    
    def _setParent(self, value):
        # presently setting all offsets to zero and removing old parents
        self.location.clear()
        self.location.add(value, 0) 

#         self._parent = common.wrapWeakref(value)

    parent = property(_getParent, _setParent)



    def _getDuration(self):
        '''
        Gets the DurationObject of the object or None

        '''
        return self._duration

    def _setDuration(self, durationObj):
        '''
        Set the offset as a quarterNote length
        '''
        if hasattr(durationObj, "quarterLength"):
            # we cannot directly test to see isInstance(duration.DurationCommon) because of
            # circular imports; so we instead just take any object with a quarterLength as a
            # duration
            self._duration = durationObj
        else:
            # need to permit Duration object assignment here
            raise Exception, 'this must be a Duration object, not %s' % durationObj

    duration = property(_getDuration, _setDuration)


    #---------------------------------------------------------------------------
    def write(self, fmt='musicxml', fp=None):
        '''Write a file.
        
        A None file path will result in temporary file
        '''
        format, ext = common.findFormat(fmt)
        if format == None:
            raise Music21ObjectException('bad format (%s) provided to write()' % fmt)
        elif format == 'musicxml':
            if fp == None:
                fp = environLocal.getTempFile(ext)
            dataStr = self.musicxml
        else:
            raise Music21ObjectException('cannot support writing in this format, %s yet' % format)
        f = open(fp, 'w')
        f.write(dataStr)
        f.close()
        return fp

    def show(self, format='musicxml'):
        '''
        Displays an object in the given format (default: musicxml) using the default display
        tools.
        
        This might need to return the file path.
        '''
        environLocal.launch(format, self.write(format))






#-------------------------------------------------------------------------------
class BaseElement(object):
    '''
    contains all the positioning information of an Element, but NOT the object
    inherited by stream.
    '''
    _offset  = 0.0
    _id = None
    _unlinkedDuration = None
    _priority = 0

    def _getDuration(self):
        '''
        Gets the duration of the Element (if separately set), but
        normal returns the duration of the component object if available, otherwise
        returns None.

        >>> import note
        >>> el1 = Element()
        >>> n = note.Note('F#')
        >>> n.quarterLength = 2.0
        >>> n.duration.quarterLength 
        2.0
        >>> el1.obj = n
        >>> el1.duration.quarterLength
        2.0

        ADVANCED FEATURE TO SET DURATION OF ELEMENTS SEPARATELY
        >>> import music21.key
        >>> ks1 = Element(music21.key.KeySignature())
        >>> ks1.obj.duration
        Traceback (most recent call last):
        AttributeError: 'KeySignature' object has no attribute 'duration'
        
        >>> import duration
        >>> ks1.duration = duration.Duration("whole")
        >>> ks1.duration.quarterLength
        4.0
        >>> ks1.obj.duration  # still not defined
        Traceback (most recent call last):
        AttributeError: 'KeySignature' object has no attribute 'duration'
        '''
        if self._unlinkedDuration is not None:
            return self._unlinkedDuration
        elif hasattr(self.obj, 'duration'):
            return self.obj.duration
        else:
            return None

    def _setDuration(self, durationObj):
        '''
        Set the offset as a quarterNote length
        '''
        if (hasattr(durationObj, "quarterLength") and 
            hasattr(self.obj, 'duration')):
            # if a number assume it is a quarter length
            self.obj.duration = durationObj
        elif (hasattr(durationObj, "quarterLength")):
            self._unlinkedDuration = durationObj
        else:
            # need to permit Duration object assignment here
            raise Exception, 'this must be a Duration object, not %s' % durationObj

    duration = property(_getDuration, _setDuration)

    def _getOffset(self):
        return self._offset  # return self_offset.quarterLength

    def _setOffset(self, offset):
        '''Set the offset as a quarterNote length
        (N.B. offsets are quarterNote lengths, not Duration objects...)

        >>> import note
        >>> import duration
        >>> a = Element(note.Note('A#'))
        >>> a.offset = 23.0
        >>> a.offset
        23.0
        >>> a.offset = 4.0 # duration.Duration("whole")
        >>> a.offset
        4.0
        '''
        if common.isNum(offset):
            # if a number assume it is a quarter length
            # self._offset = duration.DurationUnit()
            # MSC: We can change this when we decide that we want to return
            #      something other than quarterLength

            self._offset = float(offset)
        elif hasattr(offset, "quarterLength"):
            ## probably a Duration object, but could be something else -- in any case, 
            ## we'll take it.
            self._offset = offset.quarterLength
        else:
            raise Exception, 'We cannot set  %s as an offset' % offset

    offset = property(_getOffset, _setOffset)

    def _getPriority(self):
        return self._priority

    def _setPriority(self, value):
        '''
        value is an int.
        
        Priority specifies the order of processing from 
        left (LOWEST #) to right (HIGHEST #) of objects at the
        same offset.  For instance, if you want a key change and a clef change
        to happen at the same time but the key change to appear
        first, then set: keySigElement.priority = 1; clefElement.priority = 2
        this might be a slightly counterintuitive numbering of priority, but
        it does mean, for instance, if you had two elements at the same 
        offset, an allegro tempo change and an andante tempo change, 
        then the tempo change with the higher priority number would 
        apply to the following notes (by being processed
        second).
        
        Default priority is 0; thus negative priorities are encouraged
        to have Elements that appear non-priority set elements.
        
        In case of tie, there are defined class sort orders defined in
        music21.stream.CLASS_SORT_ORDER.  For instance, a key signature
        change appears before a time signature change before a note at the
        same offset.  This produces the familiar order of materials at the
        start of a musical score.
        
        >>> a = Element()
        >>> a.priority = 3
        >>> a.priority = 'high'
        Traceback (most recent call last):
        ElementException: priority values must be integers.
        '''
        if not isinstance(value, int):
            raise ElementException('priority values must be integers.')
        self._priority = value

    priority = property(_getPriority, _setPriority)



#-------------------------------------------------------------------------------
class Element(BaseElement):
    '''
    An element wraps an object so that the same object can
    be positioned within a stream.
    
    The object is always available as element.obj -- however, calls to
    the Element will call 
    
    In addition to the properties that all Music21Objects have, Elements also
    have:
    (5) offset   : a float or duration specifying the distance from the 
                   start of the surrounding container (if any) 
    (6) contexts : a list of references or weakreferences for current contexts 
                   of the object (for searching after parent)
    (7) priority : int representing the position of an object among all
                   objects at the same offset.
    '''

    obj = None

    def __init__(self, obj=None, offset=None, priority = 0):
        self.obj = obj # object stored here        

    def getId(self):
        if self.obj is not None:
            if hasattr(self.obj, "id"):
                return self.obj.id
            else:
                return self._id
        else:
            return self._id

    def setId(self, newId):
        if self.obj is not None:
            if hasattr(self.obj, "id"):
                self.obj.id = newId
            else:
                self._id = newId
        else:
            self._id = newId

    id = property (getId, setId)

    def isClass(self, className):
        '''
        Returns true if the object embedded is a particular class.

        Used by getElementsByClass in Stream

        >>> import note
        >>> a = Element(None)
        >>> a.isClass(note.Note)
        False
        >>> a.isClass(types.NoneType)
        True
        >>> b = Element(note.Note('A4'))
        >>> b.isClass(note.Note)
        True
        >>> b.isClass(types.NoneType)
        False
        '''
        if isinstance(self.obj, className):
            return True
        else:
            return False
    def copy(self):
        '''
        Makes a copy of this element with a reference
        to the SAME object but with unlinked offset, priority
        and a cloned Groups object

        >>> import note
        >>> import duration
        >>> n = note.Note('A')
        
        >>> a = Element(obj = n)
        >>> a.offset = duration.Duration("quarter")
        >>> a.groups.append("flute")

        >>> b = a.copy()
        >>> b.offset = duration.Duration("half")
        
        '''
#         >>> a.obj.accidental = "-"
#         >>> b.name
#         'A-'
#         >>> a.obj is b.obj
#         True

#         >>> a.offset.quarterLength
#         1.0
#         >>> a.groups[0] = "bassoon"
#         >>> ("flute" in a.groups, "flute" in b.groups)
#         (False, True)

        newEl = copy.copy(self)
        
        if isinstance(self.obj, Music21Object):
            newEl.groups = copy.copy(self.groups)
            newEl.contexts = copy.copy(self.contexts)

        return newEl

    def deepcopy(self):
        '''
        similar to copy but also does a deepcopy of
        the object as well.
        
        (name is all lowercase to go with copy.deepcopy convention)

        >>> from music21 import note, duration
        >>> n = note.Note('A')
        
        >>> a = Element(obj = n)
        >>> a.offset = 1.0 # duration.Duration("quarter")
        >>> a.groups.append("flute")

        >>> b = a.deepcopy()
        >>> b.offset = 2.0 # duration.Duration("half")
        
        >>> a.obj is b.obj
        False
        >>> a.obj.accidental = "-"
        >>> b.obj.name
        'A'
        >>> a.offset
        1.0
        >>> b.offset
        2.0
        >>> a.groups[0] = "bassoon"
        >>> ("flute" in a.groups, "flute" in b.groups)
        (False, True)
        '''
        new = self.copy()
        if hasattr(self.obj, 'deepcopy'):
            new.obj = self.obj.deepcopy()
        elif hasattr(self.obj, 'clone'):
            new.obj = self.obj.clone()
        else:    
            new.obj = copy.deepcopy(self.obj)
        return new

    #---------------------------------------------------------------------------
    def __repr__(self):
        shortObj = (str(self.obj))[0:30]
        if len(str(self.obj)) > 30:
            shortObj += "..."
            
        if self.id is not None:
            return '<%s id=%s offset=%s obj="%s">' % \
                (self.__class__.__name__, self.id, self.offset, shortObj)
        else:
            return '<%s offset=%s obj="%s">' % \
                (self.__class__.__name__, self.offset, shortObj)


    def __eq__(self, other):
        '''Test Element equality

        >>> a = Element()
        >>> a.offset = 3.0
        >>> c = Element()
        >>> c.offset = 3.0
        >>> a == c
        True
        >>> a is not c
        True
        '''
        if not hasattr(other, "obj") or \
           not hasattr(other, "offset") or \
           not hasattr(other, "priority") or \
           not hasattr(other, "id"): # or \
            # not hasattr(other, "groups"):
            # not hasattr(other, "parent") or \
            # not hasattr(other, "duration") or \
            return False


        if (self.obj == other.obj and \
            self.offset == other.offset and \
            self.priority == other.priority and \
            self.id == other.id): # and \
            #  self.groups == other.groups):
            #  self.parent == other.parent and \
            #  self.duration == self.duration and \
            return True
        else:
            return False

    def __ne__(self, other):
        '''
        '''
        return not self.__eq__(other)



#     def __getattribute__(self, name):
#         try: # call the base class getattribute to avoid recursion
#             environLocal.printDebug('getting attribute from Element')
#             return object.__getattribute__(self, name)
#         except AttributeError: # look in the object
#             # this only get attributes; it will not get properties
#             #return self.obj.__dict__[name]
#             # this get properties
#             environLocal.printDebug('getting attribute from self.obj')
#             return self.obj.__getattribute__(name)

    def __setattr__(self, name, value):
        if name in self.__dict__:  # if in the Element already, set that first
            object.__setattr__(self, name, value)
        
        # if not, change the attribute in the stored object
        storedobj = object.__getattribute__(self, "obj")
        if name not in ['offset', '_offset'] and \
            storedobj is not None and hasattr(storedobj, name):
            setattr(storedobj, name, value)
        else:  # unless neither has the attribute, in which case add it to the Element
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        '''This method is only called when __getattribute__() fails.
        Using this also avoids the potential recursion problems of subclassing
        __getattribute__()_
        
        see: http://stackoverflow.com/questions/371753/python-using-getattribute-method for examples
         
        '''
        storedobj = Music21Object.__getattribute__(self, "obj")
        if storedobj is None:
            raise AttributeError("Could not get attribute '" + name + "' in an object-less element")
        else:
            return object.__getattribute__(storedobj, name)



    def isTwin(self, other):
        '''
        a weaker form of equality.  a.isTwin(b) is true if
        a and b store either the same object OR objects that are equal
        and a.groups == b.groups 
        and a.id == b.id (or both are none) and duration are equal.
        but does not require position, priority, or parent to be the same
        In other words, is essentially the same object in a different context
             
        >>> import note
        >>> aE = Element(obj = note.Note("A-"))
        >>> aE.id = "aflat-Note"
        >>> aE.groups.append("out-of-range")
        >>> aE.offset = 4.0
        >>> aE.priority = 4
        
        >>> bE = aE.copy()
        >>> aE is bE
        False
        >>> aE == bE
        True
        >>> aE.isTwin(bE)
        True

        >>> bE.offset = 14.0
        >>> bE.priority = -4
        >>> aE == bE
        False
        >>> aE.isTwin(bE)
        True
        '''
        if not hasattr(other, "obj") or \
           not hasattr(other, "id") or \
           not hasattr(other, "duration") or \
           not hasattr(other, "groups"):
            return False

        if (self.obj == other.obj and \
            self.id == other.id and \
            self.duration == self.duration and \
            self.groups == other.groups):
            return True
        else:
            return False





#-------------------------------------------------------------------------------
class TestMock(Music21Object):
    pass

class Test(unittest.TestCase):

    def runTest(self):
        pass

    def testObjectCreation(self):
        a = TestMock()
        a.groups.append("hello")
        a.id = "hi"
        a.offset = 2.0
        assert(a.offset == 2.0)

    def testElementEquality(self):
        a = Element()
        a.offset = 3.0
        c = Element()
        c.offset = 3.0
        assert (a == c)
        assert (a is not c)

    def testNoteCreation(self):
        from music21 import note, duration
        n = note.Note('A')
        n.offset = 1.0 #duration.Duration("quarter")
        n.groups.append("flute")

        b = n.deepcopy()
        b.offset = 2.0 # duration.Duration("half")
        
        self.assertFalse(n is b)
        n.accidental = "-"
        self.assertEqual(b.name, "A")
        self.assertEqual(n.offset, 1.0)
        self.assertEqual(b.offset, 2.0)
        n.groups[0] = "bassoon"
        self.assertFalse("flute" in n.groups)
        self.assertTrue("flute" in b.groups)

    def testOffsets(self):
        from music21 import note
        a = Element(note.Note('A#'))
        a.offset = 23.0
        self.assertEqual(a.offset, 23.0)

    def testObjectsAndElements(self):
        from music21 import note, stream
        note1 = note.Note("B-")
        note1.type = "whole"
        stream1 = stream.Stream()
        stream1.addNext(note1)
        stream1.addNext(note1)
        subStream = stream1.getNotes()

    def testLocationRefs(self):
        aMock = TestMock()
        bMock = TestMock()

        loc = Location()
        loc.add(aMock, 234)
        loc.add(bMock, 12)
        
        self.assertEqual(loc.getOffsetByIndex(-1), 12)
        self.assertEqual(loc.getOffsetBySite(aMock), 234)
        self.assertEqual(loc.getSiteByOffset(234), aMock)
        self.assertEqual(loc.getSiteByIndex(-1), bMock)

        del aMock
        # if the parent has been deleted, the None will be returned
        # even though there is still an entry
        self.assertEqual(loc.getSiteByIndex(0), None)


    def testLocationNone(self):
        '''Test assigning a None to parent
        '''
        loc = Location()
        loc.add(None, 0)

def mainTest(*testClasses):
    '''
    Takes as its arguments modules (or a string 'noDocTest')
    and runs all of these modules through a unittest suite
    
    unless 'noDocTest' is passed as a module, a docTest
    is also performed on __main__.  Hence the name "mainTest"
    
    run example (put at end of your modules)
    
        import unittest
        class Test(unittest.TestCase):
            def testHello(self):
                hello = "Hello"
                self.assertEqual("Hello", hello)
    
        import music21
        if __name__ == '__main__':
            music21.mainTest(Test)
    
    '''
    
    if ('noDocTest' in testClasses):
        s1 = unittest.TestSuite()
    else: 
        s1 = doctest.DocTestSuite('__main__', optionflags = (doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE))

    for thisClass in testClasses:
        if isinstance(thisClass, str) and thisClass == 'noDocTest':
            pass
        else:
            s2 = unittest.defaultTestLoader.loadTestsFromTestCase(thisClass)
            s1.addTests(s2) 
    runner = unittest.TextTestRunner()
    runner.run(s1)  

if __name__ == "__main__":
    mainTest(Test)