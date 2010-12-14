#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:         intervalNetwork.py
# Purpose:      A graph of intervals, for scales and harmonies. 
#
# Authors:      Christopher Ariza
#
# Copyright:    (c) 2010 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------


'''An IntervalNetwork defines a scale or harmonic unit as a (weighted) digraph, or directed graph, where pitches are nodes and intervals are edges. Nodes, however, are not stored; instead, an ordered list of edges (Intervals) is provided as an archetype of adjacent nodes. 

IntervalNetworks are unlike conventional graphs in that each graph must define a low and high terminus. These points are used to create a cyclic graph and are treated as point of cyclical overlap. 

IntervalNetwork permits the definition of conventional octave repeating scales or harmonies (abstract chords), non-octave repeating scales and chords, and ordered interval sequences that might move in multiple directions. 

A scale or harmony may be composed of one or more IntervalNetwork objects. 

Both nodes and edges can be weighted to suggest tonics, dominants, finals, or other attributes of the network. 
'''

import unittest, doctest
import copy

import music21
from music21 import interval
from music21 import common
from music21 import pitch

from music21 import environment
_MOD = "intervalNetwork.py"
environLocal = environment.Environment(_MOD)


try:
    import networkx
except ImportError:
    # lacking this does nothing
    pass
    #_missingImport.append('networkx')


# these are just symbols/place holders; values do not matter as long
# as they are not positive ints
TERMINUS_LOW = 'terminusLow'
TERMINUS_HIGH = 'terminusHigh'
DIRECTION_BI = 'bi'
DIRECTION_ASCENDING = 'ascending'
DIRECTION_DESCENDING = 'descending'



class EdgeException(Exception):
    pass


class Edge(object):
    '''Abstraction of an Interval as an Edge. 

    Edges store an Interval object as well as a direction specification.

    For directed Edges, the direction of the Interval may be used to suggest non-pitch ascending movements (even if the direction is ascending). 

    Weight values, as well as other attributes, can be stored. 

    >>> from music21 import *
    >>> i = interval.Interval('M3')
    >>> e = intervalNetwork.Edge(i)
    >>> i is e.interval
    True
    '''
    def __init__(self, intervalData=None, id=None, direction='bi'):
        if common.isStr(intervalData):
            i = interval.Interval(intervalData)
        else:
            i = intervalData
        self._interval = i
        # direction will generally be set when connections added 
        self._direction = DIRECTION_BI # can be ascending, descending
        self.weight = 1.0
        # store id
        self.id = id

        # one or two pairs of Node ids that this Edge connects
        # if there are two, it is a bidirectional, w/ first ascending
        self._connections = []



    def __eq__(self, other):
        ''' 
        >>> from music21 import *
        >>> i1 = interval.Interval('M3')
        >>> i2 = interval.Interval('M3')
        >>> i3 = interval.Interval('m3')
        >>> e1 = intervalNetwork.Edge(i1)
        >>> e2 = intervalNetwork.Edge(i2)
        >>> e3 = intervalNetwork.Edge(i3)
        >>> e1 == e2
        True
        >>> e1 == e3
        False
        '''
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


    def __repr__(self):
        return '<music21.intervalNetwork.Edge %s %s %s>' % (self._direction, 
             self._interval.name, repr(self._connections).replace(' ', ''))

    def _getInterval(self):
        return self._interval

    interval = property(_getInterval, 
        doc = '''Return the stored Interval object

        >>> from music21 import *
        >>> i = interval.Interval('M3')
        >>> e1 = intervalNetwork.Edge(i, id=0)
        >>> n1 = Node(id=0)
        >>> n2 = Node(id=1)
        >>> e1.addDirectedConnection(n1, n2, 'ascending')
        >>> e1.interval
        <music21.interval.Interval M3>
        ''')

    def _geDirection(self):
        return self._direction

    direction = property(_geDirection, 
        doc = '''Return the direction of the Edge.

        >>> from music21 import *
        >>> i = interval.Interval('M3')
        >>> e1 = intervalNetwork.Edge(i, id=0)
        >>> n1 = Node(id=0)
        >>> n2 = Node(id=1)
        >>> e1.addDirectedConnection(n1, n2, 'ascending')
        >>> e1.direction
        'ascending'
        ''')


    def addDirectedConnection(self, n1, n2, direction=None):
        '''Provide two Node objects that connect this Edge, in the direction from the first to the second. 
        
        When calling directly, a direction, either ascending or descending, should be set here; this will override whatever the interval is.  If None, this will not be set. 

        >>> from music21 import *
        >>> i = interval.Interval('M3')
        >>> e1 = intervalNetwork.Edge(i, id=0)
        >>> n1 = Node(id=0)
        >>> n2 = Node(id=1)

        >>> e1.addDirectedConnection(n1, n2, 'ascending')
        >>> e1.connections
        [(0, 1)]
        >>> e1
        <music21.intervalNetwork.Edge ascending M3 [(0,1)]>
        '''
        # may be Node objects, or number, or string
        if common.isStr(n1) or common.isNum(n1):
            n1Id = n1
        else: # assume an Node
            n1Id = n1.id

        if common.isStr(n2) or common.isNum(n2):
            n2Id = n2
        else: # assume an Node
            n2Id = n2.id

        self._connections.append((n1Id, n2Id))

        # must specify a direction
        if (direction not in [DIRECTION_ASCENDING, DIRECTION_DESCENDING]):
            raise EdgeException('must request a direction')
        self._direction = direction


    def addBiDirectedConnections(self, n1, n2):
        '''Provide two Edge objects that pass through this Node, in the direction from the first to the second. 

        >>> from music21 import *
        >>> i = interval.Interval('M3')
        >>> e1 = intervalNetwork.Edge(i, id=0)
        >>> e2 = intervalNetwork.Edge(i, id=1)
        >>> n1 = Node(id='terminusLow')
        >>> n2 = Node(id=1)
        >>> n3 = Node(id=2)
        >>> n4 = Node(id=2)

        >>> e1.addBiDirectedConnections(n1, n2)
        >>> e1.connections
        [('terminusLow', 1), (1, 'terminusLow')]
        >>> e1
        <music21.intervalNetwork.Edge bi M3 [('terminusLow',1),(1,'terminusLow')]>
        '''
        # must assume here that n1 to n2 is ascending; need to know
        self.addDirectedConnection(n1, n2, DIRECTION_ASCENDING)
        self.addDirectedConnection(n2, n1, DIRECTION_DESCENDING)
        self._direction = DIRECTION_BI # can be ascending, descending


    def getConnections(self, direction=None):
        '''
        Return a list of connections between Nodes, represented as pairs of Node ids. If a direction is specified, and if the Edge is directional, only the desired directed values will be returned. 

        >>> from music21 import *
        >>> i = interval.Interval('M3')
        >>> e1 = intervalNetwork.Edge(i, id=0)
        >>> e2 = intervalNetwork.Edge(i, id=1)
        >>> n1 = Node(id='terminusLow')
        >>> n2 = Node(id=1)
        >>> n3 = Node(id=2)
        >>> n4 = Node(id=2)

        >>> e1.addBiDirectedConnections(n1, n2)
        >>> e1.getConnections()
        [('terminusLow', 1), (1, 'terminusLow')]
        >>> e1.getConnections('ascending')
        [('terminusLow', 1)]
        >>> e1.getConnections('descending')
        [(1, 'terminusLow')]

        '''
        if direction == None:
            direction = self._direction

        # do not need to supply direction, because direction is defined
        # in this Edge.
        if self._direction == direction:
            return self._connections
        
        # if requesting bi from a mono directional edge is an error
        if (direction in [DIRECTION_BI] and self._direction in [DIRECTION_ASCENDING, DIRECTION_DESCENDING]):
            raise EdgeException('cannot request a bi direction from a mono direction')

        # if bi and we get an ascending/descending request
        if (direction in [DIRECTION_ASCENDING, DIRECTION_DESCENDING] and self._direction in [DIRECTION_BI]):

            # assume that in a bi-representiaton, the first is ascending
            # the second is descending
            # NOTE: this may not mean that we are actually ascending, we may
            # use the direction of the interval to determine
            if direction == DIRECTION_ASCENDING:
                return [self._connections[0]]
            elif direction == DIRECTION_DESCENDING:
                return [self._connections[1]]
        # if no connections are possible, return none
        return None

    connections = property(getConnections, 
        doc = '''Return a list of stored connections that pass through this node. Connections are stored as directed pairs of Edge indices. 
        ''')


class Node(object):
    '''Abstraction of an unrealized Pitch Node.

    The Node id is used to storing connections in Edges.

    Terminal Nodes have special ids: terminusLow, terminusHighs
    '''
    def __init__(self, id=None, step=None):
        # store id, either as string, such as terminusLow, or a number. 
        # ids are unique to any node in the network
        self.id = id
        # the step is used to define ordered node counts from the bottom
        # the step is analogous to scale step. 
        # more than one node may have the same step
        self.step = step
        # node weight might be used to indicate importance of scale positions
        self.weight = 1.0

    def __eq__(self, other):
        ''' 
        >>> from music21 import *
        >>> n1 = intervalNetwork.Node(id=3)
        >>> n2 = intervalNetwork.Node(id=3)
        >>> n3 = intervalNetwork.Node(id=2)
        >>> n1 == n2
        True
        >>> n1 == n3
        False
        '''
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<music21.intervalNetwork.Node id=%s>' % (repr(self.id))




#-------------------------------------------------------------------------------
class IntervalNetworkException(Exception):
    pass


# presently edges are interval objects, can be marked as 
# ascending, descending, or bi-directional
# edges are stored in dictionary by index values 

# nodes are undefined pitches; pitches are realized on demand
# nodes are stored as an unordered list of coordinate pairs
# pairs are edge indices: showing which edges connect to this node
# could model multiple connections within an object

# up:    a M2 b m2 C M2 D
# down:  a M2 b   m3    D 

# edges M2(1+-), m2(2+), M2(3+)
# edges m3(4-)


class IntervalNetwork(object):
    '''A graph of undefined Pitch nodes connected by a defined, ordered list of Interval objects as edges. 
    '''

    def __init__(self, edgeList=None):
        # store each edge with and index that is incremented when added
        # these values have no fixed meaning but are only for reference
        self._edgeIdCount = 0
        self._nodeIdCount = 0

        # a dictionary of Edge object, where keys are _edgeIdCount values
        # Edges store directed connections between Node ids
        self._edges = {}

        # nodes suggest Pitches, but Pitches are not stored
        self._nodes = {}

        if edgeList != None: # auto initialize
            self.fillBiDirectedEdges(edgeList)


    def clear(self):
        '''Remove and reset all Nodes and Edges. 
        '''
        self._edgeIdCount = 0
        self._nodeIdCount = 0
        self._edges = {}
        self._nodes = {}



    def __eq__(self, other):
        '''
        >>> from music21 import *
        >>> edgeList1 = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> edgeList2 = ['M2', 'M2', 'm2', 'M2', 'A3', 'm2']

        >>> net1 = intervalNetwork.IntervalNetwork()
        >>> net1.fillBiDirectedEdges(edgeList1)

        >>> net2 = intervalNetwork.IntervalNetwork()
        >>> net2.fillBiDirectedEdges(edgeList1)

        >>> net3 = intervalNetwork.IntervalNetwork()
        >>> net3.fillBiDirectedEdges(edgeList2)

        >>> net1 == net2
        True
        >>> net1 == net3
        False
        '''
        # compare all nodes and edges; if the same, and all keys are the same,
        # then matched
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


    def fillBiDirectedEdges(self, edgeList):
        '''Given an ordered list of bi-directed edges given as Interval specifications, create and define appropriate Nodes. This assumes that all edges are bidirected and all all edges are in order.
    
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.realizePitch('g4')
        [G4, A4, B4, C5, D5, E5, F#5, G5]
        >>> net.stepMin, net.stepMax
        (1, 8)

        >>> # using another fill method creates a new network
        >>> net.fillBiDirectedEdges(['M3', 'M3', 'M3'])
        >>> net.realizePitch('g4')
        [G4, B4, D#5, G5]
        >>> net.stepMin, net.stepMax
        (1, 4)
        '''
        self.clear()

        stepCount = 1 # steps start from one

        nLow = Node(id=TERMINUS_LOW, step=stepCount)        
        stepCount += 1
        self._nodes[nLow.id] = nLow

        nPrevious = nLow
        for i, eName in enumerate(edgeList):
            
            # first, create the next node
            if i < len(edgeList) - 1: # if not last
                n = Node(id=self._nodeIdCount, step=stepCount)        
                self._nodeIdCount += 1
                stepCount += 1
                nFollowing = n
            else: # if last
                nHigh = Node(id=TERMINUS_HIGH, step=stepCount)  # step is same as start
                nFollowing = nHigh
    
            # add to node dictionary
            self._nodes[nFollowing.id] = nFollowing

            # then, create edge and connection
            e = Edge(eName, id=self._edgeIdCount)
            self._edges[e.id] = e # store
            self._edgeIdCount += 1

            e.addBiDirectedConnections(nPrevious, nFollowing)
            # update previous with the node created after this edge
            nPrevious = nFollowing


    def fillDirectedEdges(self, ascendingEdgeList, descendingEdgeList):
        '''Given two lists of edges, one for ascending intervals and another for  descending, construct appropriate Nodes and Edges.

        Note that the descending intervals should be given in ascending form. 
        '''
        self.clear()

        # if both are equal, than assigning steps is easy
        if len(ascendingEdgeList) != len(descendingEdgeList):
            raise IntervalNetworkException('cannot manage unequawl sized directed edges')

        stepCount = 1 # steps start from one
        nLow = Node(id=TERMINUS_LOW, step=stepCount)        
        stepCount += 1
        self._nodes[nLow.id] = nLow

        nPrevious = nLow
        for i, eName in enumerate(ascendingEdgeList):
            
            # first, create the next node
            if i < len(ascendingEdgeList) - 1: # if not last
                n = Node(id=self._nodeIdCount, step=stepCount)        
                self._nodeIdCount += 1
                stepCount += 1
                nFollowing = n
            else: # if last
                nHigh = Node(id=TERMINUS_HIGH, step=stepCount)  # step is same as start
                nFollowing = nHigh
    
            # add to node dictionary
            self._nodes[nFollowing.id] = nFollowing

            # then, create edge and connection; eName is interval
            e = Edge(eName, id=self._edgeIdCount)
            self._edges[e.id] = e
            self._edgeIdCount += 1

            e.addDirectedConnection(nPrevious, nFollowing,
                direction='ascending')
            # update previous with the node created after this edge
            nPrevious = nFollowing

        # repeat for descending, but reverse direction, and use
        # same low and high nodes
        stepCount = 1 # steps start from one
        nLow = self._nodes[TERMINUS_LOW] # get node; do not need to add
        stepCount += 1
        nPrevious = nLow
        for i, eName in enumerate(descendingEdgeList):
            
            # first, create the next node
            if i < len(descendingEdgeList) - 1: # if not last
                n = Node(id=self._nodeIdCount, step=stepCount)        
                self._nodeIdCount += 1
                stepCount += 1
                nFollowing = n
                # add to node dictionary
                self._nodes[nFollowing.id] = nFollowing
            else: # if last
                nHigh = self._nodes[TERMINUS_HIGH]
                nFollowing = nHigh
    
            # then, create edge and connection
            e = Edge(eName, id=self._edgeIdCount)
            self._edges[e.id] = e
            self._edgeIdCount += 1

            # order here is reversed from above
            e.addDirectedConnection(nFollowing, nPrevious, direction='descending')
            # update previous with the node created after this edge
            nPrevious = nFollowing



    def fillArbitrary(self, nodes, edges):
        '''Fill any arbitrary network given node and edge definitions.

        Nodes must be defined by a dictionary of id and step values. There must be a terminusLow and terminusHigh id as string.

        nodes = ({'id':'terminusLow', 'step':1},
                 {'id':0, 'step':2},
                 {'id':'terminusHigh', 'step':3},
                )

        Edges must be defined by a dictionary of interval strings and connections. Id values will be automatically assigned. Each connection must define direction and pairs of valid node ids. 

        edges = ({'interval':'m2', connections:(
                        ['terminusLow', 0, 'bi'],
                    )},
                {'interval':'M3', connections:(
                        [0, 'terminusHigh', 'bi'],
                    )},
                )
        >>> from music21 import *
        >>> nodes = ({'id':'terminusLow', 'step':1}, {'id':0, 'step':2}, {'id':'terminusHigh', 'step':3})
        >>> edges = ({'interval':'m2', 'connections':(['terminusLow', 0, 'bi'],)},{'interval':'M3', 'connections':([0, 'terminusHigh', 'bi'],)},)

        >>> net = IntervalNetwork()
        >>> net.fillArbitrary(nodes, edges)
        >>> net.realizePitch('c4', 1)
        [C4, D-4, F4]
        '''

        self.clear()

        for nDict in nodes:
            n = Node(id=nDict['id'], step=nDict['step'])        
            self._nodes[n.id] = n

        eId = 0
        for eDict in edges:
            e = Edge(eDict['interval'], id=eId)        
            for nId1, nId2, direction in eDict['connections']:
                # do not need to access from _nodes dictionary here
                # but useful as a check that the node has been defined. 
                if direction == DIRECTION_BI:
                    e.addBiDirectedConnections(self._nodes[nId1], self._nodes[nId2])
                else:
                    e.addDirectedConnection(self._nodes[nId1],
                    self._nodes[nId2], direction=direction)
            self._edges[e.id] = e
            eId += 1



    #---------------------------------------------------------------------------
    def _getStepMin(self):
        '''
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net._getStepMin()
        1
        '''
        x = None
        for n in self._nodes.values():
            if x == None:
                x = n.step
            if n.step < x:
                x = n.step
        return x

    stepMin = property(_getStepMin, 
        doc = '''Return the lowest step value.

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.stepMin    
        1
        ''')

    def _getStepMax(self):
        '''
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net._getStepMax() # returns eight, as this is the last node
        8
        '''
        x = None
        for n in self._nodes.values():
            if x == None:
                x = n.step
            if n.step > x:
                x = n.step
        return x

    stepMax = property(_getStepMax, 
        doc = '''Return the largest step value.

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.stepMax    
        8
        ''')

    
    def _getStepMaxUnique(self):
        x = None
        for nId, n in self._nodes.items():
            # reject terminus high, as this duplicates terminus low
            if nId == TERMINUS_HIGH:
                continue
            if x == None:
                x = n.step
            if n.step > x:
                x = n.step
        return x

    stepMaxUnique = property(_getStepMaxUnique, 
        doc = '''Return the largest step value that represents a pitch level that is not a terminus of the scale. 

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.stepMaxUnique
        7
        ''')



    def _getTerminusLowNodes(self):
        '''
        '''
        post = []
        # for now, there is only one
        post.append(self._nodes[TERMINUS_LOW])
        return post
    
    terminusLowNodes = property(_getTerminusLowNodes, 
        doc='''Return a list of first Nodes, or Nodes that contain "terminusLow". Nodes are not stored, but are encoded as pairs, index values, to stored edges. Indices are either integers or the strings 

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.terminusLowNodes[0]
        <music21.intervalNetwork.Node id='terminusLow'>
        ''')

    def _getTerminusHighNodes(self):
        post = []
        # for now, there is only one
        post.append(self._nodes[TERMINUS_HIGH])
        return post

    
    terminusHighNodes = property(_getTerminusHighNodes, 
        doc='''Return a list of last Nodes, or Nodes that contain "end". Return the coordinates of the last Node. Nodes are not stored, but are encoded as pairs, index values, to stored edges. Indices are either integers or the

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.terminusHighNodes[0]
        <music21.intervalNetwork.Node id='terminusHigh'>
        ''')


    #---------------------------------------------------------------------------
    def _getNodeStepDictionary(self, direction=None, equateTerminals=True):
        '''Return a dictionary of node id, node step pairs. The same step may be given for each node 

        There may not be unambiguous way to determine step. Or, a step may have different meanings when ascending or descending.

        If `equateTerminals` is True, the terminals will be given the same step. 
        '''
        # TODO: this should be cached after network creation
        post = {}
        for nId, n in self._nodes.items():
            if equateTerminals:
                if nId == TERMINUS_HIGH:
                    # get the same step as the low
                    post[nId] = self._nodes[TERMINUS_LOW].step
                else:
                    post[nId] = n.step
            else: # directly assign from attribute
                post[nId] = n.step
        return post


    def _nodeIdToNodeStep(self, nId, direction=None):
        '''Given a strict node id (the .id attribute of the Node), return the step.

        There may not be unambiguous way to determine step. Or, a step may have different meanings when ascending or descending.
        '''
        nodeStep = self._getNodeStepDictionary(direction=direction)
        return nodeStep[nId] # gets step integer
        

    def _stepModulus(self, step):
        '''Return the modulus of the step.

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net._stepModulus(3)
        3
        >>> net._stepModulus(8)
        1
        >>> net._stepModulus(9)
        2
        >>> net._stepModulus(0)
        7
        '''
        # TODO: these need to be cached
        sMin = self._getStepMin()
        sMax = self._getStepMax()
        # the number of unique values; assumes redundancy in 
        # top and bottom value, so 8 steps, from 1 to 8, have
        # seven unique values
        spanCount = sMax-sMin
        # assume continuous span, assume start at min
        # example for diatonic scale step 3:
        # ((3-1) % 7)+1
        #if (((id-1) % spanCount) + sMin) == nStep:

        return ((step-1) % spanCount) + sMin

    def _nodeNameToNodes(self, id, equateTerminals=True, permitStepModuli=True):
        '''A node name may be an id, a string, or integer step count of nodes position (steps). Return a list of Nodes that match this identifications. 

        If `equateTerminals` is True, and the name given is a step number, then the first terminal will return both the first and last.

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net._nodeNameToNodes(1)[0]
        <music21.intervalNetwork.Node id='terminusLow'>
        >>> net._nodeNameToNodes('high')
        [<music21.intervalNetwork.Node id='terminusHigh'>]
        >>> net._nodeNameToNodes('low')
        [<music21.intervalNetwork.Node id='terminusLow'>]

        >>> # test using a nodeStep, or an integer nodeName
        >>> net._nodeNameToNodes(1)
        [<music21.intervalNetwork.Node id='terminusLow'>, <music21.intervalNetwork.Node id='terminusHigh'>]
        >>> net._nodeNameToNodes(1, equateTerminals=False)
        [<music21.intervalNetwork.Node id='terminusLow'>]
        >>> net._nodeNameToNodes(2)
        [<music21.intervalNetwork.Node id=0>]
        >>> # with step moduli, step zero is the top-most non-terminal (as terminals are redundant
        >>> net._nodeNameToNodes(0)
        [<music21.intervalNetwork.Node id=5>]
        >>> net._nodeNameToNodes(-1)
        [<music21.intervalNetwork.Node id=4>]
        >>> net._nodeNameToNodes(8)
        [<music21.intervalNetwork.Node id='terminusLow'>, <music21.intervalNetwork.Node id='terminusHigh'>]

        '''
        if common.isNum(id):
            post = []
            nodeStep = self._getNodeStepDictionary(
                equateTerminals=equateTerminals)
            for nId, nStep in nodeStep.items():
                if id == nStep:
                    post.append(self._nodes[nId])
            # if no matches, and moduli comparisons are permitted
            if post == [] and permitStepModuli:
                for nId, nStep in nodeStep.items():
                    if self._stepModulus(id) == nStep:
                        post.append(self._nodes[nId])

            return post
        elif common.isStr(id):
            if id.lower() in ['terminuslow', 'low']:
                return self._getTerminusLowNodes() # returns a list
            elif id.lower() in ['terminushigh', 'high']:
                return self._getTerminusHighNodes()# returns a list
            else:
                raise IntervalNetworkException('got a strin that has no match:', id)
        elif isinstance(id, Node):
            # look for direct match     
            for nId in self._nodes.keys():
                n = self._nodes[nId]
                if n is id: # could be a == comparison?
                    return [n]
        else: # match coords
            raise IntervalNetworkException('cannot filter by: %s', id)


    def _getNext(self, nodeStart, direction):
        '''Given a Node, get two lists, one of next Edges, and one of next Nodes, searching all Edges to find the best matcsh. 

        There may be more than one possibility. If so, the caller must look at the Edges and determine which to use

        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net._nodeNameToNodes(1)[0]
        <music21.intervalNetwork.Node id='terminusLow'>
        '''

        postEdge = []
        postNodeId = []
        # search all edges to find Edges that start with this node id
        srcId = nodeStart.id

        # if we are at terminus low and descending, must wrap around
        if srcId == TERMINUS_LOW and direction == DIRECTION_DESCENDING:
            srcId = TERMINUS_HIGH
        # if we are at terminus high and ascending, must wrap around
        elif srcId == TERMINUS_HIGH and direction == DIRECTION_ASCENDING:
            srcId = TERMINUS_LOW

        for k in self._edges.keys():
            e = self._edges[k]
            # only getting ascending connections
            pairs = e.getConnections(direction)
            if pairs is None:
                continue
            for src, dst in pairs:
                if src == srcId:
                    postEdge.append(e)
                    postNodeId.append(dst)

        if len(postEdge) == 0:
            environLocal.printDebug(['nodeStart', nodeStart, 'direction', direction, 'postEdge', postEdge])
            return None
            #raise IntervalNetworkException('could not find any edges')
        
        # if we have multiple edges, we may need to select based on weight
        postNode = [self._nodes[nId] for nId in postNodeId]
        return postEdge, postNode





    def _processAlteredNodes(self, alteredNodes, n, p, direction):
        '''Return an altered pitch for given node, if an alteration is specified
        in the alteredNodes dictionary
        '''
        if n.step in alteredNodes.keys():
            # check if this direction is the list of directions

            directionSpec = alteredNodes[n.step]['direction']
            #environLocal.printDebug(['processing altered node', n, p, 'direction', direction, 'directionSpec', directionSpec])

            match = False
            # if ascending or descending, and this is a bidirectinonal alt
            # then applyt

            if (direction == directionSpec):
                match = True
            # if request is bidrectional and the spec is for ascending and
            # descending
            elif (direction in [DIRECTION_BI] and directionSpec in [DIRECTION_ASCENDING, DIRECTION_DESCENDING]):
                match = True

            elif (direction in [DIRECTION_ASCENDING, DIRECTION_DESCENDING] and directionSpec == DIRECTION_BI):
                match = True

            if match:
                #environLocal.printDebug(['matched direction', direction])
                pPost = alteredNodes[n.step]['interval'].transposePitch(p, maxAccidental=1)
                return pPost
        # return pitch unaltered
        else:
            pass
            #environLocal.printDebug(['not processing altered node', n, p, 'direction', direction])
        return p

    def _getUnalteredPitch(self, pitchObj, nodeObj, direction=DIRECTION_BI, 
        alteredNodes={}):
        '''Given a node, get the unaltered pitch.
        '''
        if alteredNodes != {}:
            #TODO: need to take direction into account
            # do reverse transposition
            if nodeObj.step in alteredNodes.keys():
                p = alteredNodes[nodeObj.step][
                    'interval'].reverse().transposePitch(pitchObj, maxAccidental=1)
                return p

        return None


    def nextPitch(self, pitchReference, nodeName, pitchOrigin, 
        direction=DIRECTION_ASCENDING, stepSize=1, alteredNodes={}, 
        getNeighbor=True):
        '''Given a pitchReference, nodeName, and a pitch origin, return the next pitch. 

        The `step` attribute can be configured to permit different sized steps.


        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.nextPitch('g', 1, 'f#5', 'ascending')
        G5
        >>> net.nextPitch('g', 1, 'f#5', 'descending')
        E5
        >>> net.nextPitch('g', 1, 'f#5', 'ascending', 2) # two steps
        A5
        >>> alteredNodes = {2:{'direction':'bi', 'interval':interval.Interval('-a1')}}
        >>> net.nextPitch('g', 1, 'g2', 'ascending', alteredNodes=alteredNodes)
        A-2
        >>> net.nextPitch('g', 1, 'a-2', 'ascending', alteredNodes=alteredNodes)
        B2
        '''
        if common.isStr(pitchOrigin):
            pitchObj = pitch.Pitch(pitchOrigin)
        else:
            pitchObj = copy.deepcopy(pitchOrigin)

        # get the node that we are looking for 
        nodeId = self.getRelativeNodeId(pitchReference, nodeName, 
                    pitchTarget=pitchOrigin, alteredNodes=alteredNodes)

        # realize the pitch from the raw node; we may be getting an altered
        # tone, and we need to transpose an unaltered tone
        # leave out altered nodes argument
        p = self.getPitchFromNodeStep(pitchReference=pitchReference, 
            nodeName=nodeName, 
            nodeStepTarget=self._nodes[nodeId].step, 
            direction=direction, 
            minPitch=None, 
            maxPitch=None, alteredNodes={}
            )
        # transfer octave
        p.octave = pitchObj.octave
        pitchObj = p

        # if no match, get the neighbor
        if nodeId is None and getNeighbor in [True,     
            DIRECTION_ASCENDING, DIRECTION_DESCENDING, DIRECTION_BI]:
            lowId, highId = self.getNeighborNodeIds(
                pitchReference=pitchReference, 
                nodeName=nodeName, 
                pitchTarget=pitchOrigin)
            # replace the node with the nearest neighbor
            if getNeighbor in [True, DIRECTION_ASCENDING, DIRECTION_BI]:
                nodeId = highId
            else:
                nodeId = lowId
            environLocal.printDebug(['looking for neighbor', 'nodeId', nodeId])

            # TODO: need to adjust pitch object here to non altered
            # pitchObj

        n = self._nodes[nodeId]
        p = pitchObj
        pCollect = p # usually p, unles altered
        for x in range(stepSize):
            postEdge, postNode = self._getNext(n, direction)
            # already working with a copy
            n = postNode[0]
            # for now, only taking first edge
            if direction == DIRECTION_ASCENDING:
                p = postEdge[0].interval.transposePitch(p, maxAccidental=1)
            else:
                p = postEdge[0].interval.reverse().transposePitch(p, maxAccidental=1)
            
            pCollect = self._processAlteredNodes(alteredNodes=alteredNodes, 
                       n=n, p=p, direction=direction)

        return pCollect








    # TODO: need to collect intervals as well 


    def _realizeAscending(self, pitchReference, nodeId=None, 
        minPitch=None, maxPitch=None, alteredNodes={}):
        '''Given a reference pitch, realize downward to a minimum.
        '''
        # get first node if no node is provided
        if isinstance(nodeId, Node):
            nodeObj = nodeId
        elif nodeId is None: # assume first
            nodeObj = self._getTerminusLowNodes()[0]
        else:
            nodeObj = self._nodeNameToNodes(nodeId)[0]
            
        if common.isStr(pitchReference):
            pitchReference = pitch.Pitch(pitchReference)
        else:
            pitchReference = copy.deepcopy(pitchReference)

        if common.isStr(minPitch):
            minPitch = pitch.Pitch(minPitch)
        if common.isStr(maxPitch):
            maxPitch = pitch.Pitch(maxPitch)

#         if maxPitch is not None and maxPitch.ps < pitchReference.ps:
#             raise IntervalNetworkException('min pitch is not less than or equal to the reference pitch')

        # when the pitch reference is altered, we need to get the
        # unaltered version of this pitch. 
        pUnaltered = self._getUnalteredPitch(pitchReference, nodeObj,
                     direction=DIRECTION_ASCENDING, alteredNodes=alteredNodes)
        if pUnaltered is not None:
            pitchReference = pUnaltered

        # first, go upward from this pitch to the high terminus
        n = nodeObj
        p = pitchReference # we start with the pitch that is the reference
        pCollect = p # usually p, unless the tone has been altered
        post = []
        postNodeId = [] # store node ids as well

        while True:
            #environLocal.printDebug(['here', p])
            appendPitch = False
            if (minPitch is not None and pCollect.ps >= minPitch.ps and 
                maxPitch is not None and pCollect.ps <= maxPitch.ps):
                appendPitch = True
            elif (minPitch is not None and pCollect.ps >= minPitch.ps and 
                maxPitch is None):
                appendPitch = True
            elif (maxPitch is not None and pCollect.ps <= maxPitch.ps and 
                minPitch is None):
                appendPitch = True
            elif minPitch is None and maxPitch is None: 
                appendPitch = True

            if appendPitch:
                post.append(pCollect)
                postNodeId.append(n.id)

            if maxPitch is not None and p.ps >= maxPitch.ps:
                break

            # must check first, and at end
            if n.id == TERMINUS_HIGH:
                if maxPitch is None: # if not defined, stop at terminus high
                    break
                n = self._getTerminusLowNodes()[0]

            # this returns a list of possible edges and nodes
            nextBundle = self._getNext(n, DIRECTION_ASCENDING)
            # if we cannot continue to ascend, then we must break
            if nextBundle is None:
                break

            postEdge, postNode = nextBundle
            intervalObj = postEdge[0].interval # get first
            p = intervalObj.transposePitch(p, maxAccidental=1)
            pCollect = p
            n = postNode[0]

            pCollect = self._processAlteredNodes(alteredNodes=alteredNodes, 
                       n=n, p=p, direction=DIRECTION_ASCENDING)

        return post, postNodeId



    def _realizeDescending(self, pitchReference, nodeId=None, 
        minPitch=None, maxPitch=None, alteredNodes={}, includeReference=False):
        '''Given a reference pitch, realize downward to a minimum.

        If no minimum is is given, the terminus is used.

        If `includeReference` is False, the reference pitch will not be included.        

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net._realizeDescending('c2', 1, 'c3')
        ([], [])
        >>> net._realizeDescending('c3', 1, 'c2')
        ([C2, D2, E2, F2, G2, A2, B2], ['terminusLow', 0, 1, 2, 3, 4, 5])
        >>> net._realizeDescending('c3', 1, 'c2', includeReference=True)
        ([C2, D2, E2, F2, G2, A2, B2, C3], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusLow'])

        >>> net._realizeDescending('a6', 'high')
        ([A5, B5, C#6, D6, E6, F#6, G#6], ['terminusLow', 0, 1, 2, 3, 4, 5])
        >>> net._realizeDescending('a6', 'high', includeReference=True)
        ([A5, B5, C#6, D6, E6, F#6, G#6, A6], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh'])
        '''

        # get first node if no node is provided
        if isinstance(nodeId, Node):
            nodeObj = nodeId
        elif nodeId is None: # assume first
            #nodeObj = self._getTerminusHighNodes()[0]
            nodeObj = self._getTerminusLowNodes()[0]
        else:
            nodeObj = self._nodeNameToNodes(nodeId)[0]
            
        if common.isStr(pitchReference):
            pitchReference = pitch.Pitch(pitchReference)
        else:
            pitchReference = copy.deepcopy(pitchReference)

        if common.isStr(minPitch):
            minPitch = pitch.Pitch(minPitch)
        if common.isStr(maxPitch):
            maxPitch = pitch.Pitch(maxPitch)

#         if minPitch is not None and minPitch.ps > pitchReference.ps:
#             raise IntervalNetworkException('min pitch is not less than or equal to the reference pitch')

        # when the pitch reference is altered, we need to get the
        # unaltered version of this pitch. 
        pUnaltered = self._getUnalteredPitch(pitchReference, nodeObj,
                     direction=DIRECTION_DESCENDING, alteredNodes=alteredNodes)
        if pUnaltered is not None:
            pitchReference = pUnaltered

        n = nodeObj
        p = pitchReference
        pCollect = p # usually p, unless the tone has been altered
        pre = []
        preNodeId = [] # store node ids as well

        if includeReference:
            pre.append(pCollect)
            preNodeId.append(n.id)

        while True:
            #if n.id == TERMINUS_LOW and minPitch is not None:
            if n.id == TERMINUS_LOW:
                if minPitch is None: # if not defined, stop at terminus high
                    break

            nextBundle = self._getNext(n, DIRECTION_DESCENDING)
            if nextBundle is None:
                #environLocal.printDebug(['realize():', 'cannot descend from n', n])
                break
            postEdge, postNode = nextBundle
            intervalObj = postEdge[0].interval # get first
            p = intervalObj.reverse().transposePitch(p, maxAccidental=1)
            pCollect = p
            n = postNode[0]

            pCollect = self._processAlteredNodes(alteredNodes=alteredNodes, 
                       n=n, p=p, direction=DIRECTION_DESCENDING)

            appendPitch = False
            if (minPitch is not None and p.ps >= minPitch.ps and 
                maxPitch is not None and p.ps <= maxPitch.ps):
                appendPitch = True
            elif (minPitch is not None and p.ps >= minPitch.ps and 
                maxPitch is None):
                appendPitch = True
            elif (maxPitch is not None and p.ps <= maxPitch.ps and 
                minPitch is None):
                appendPitch = True
            elif minPitch is None and maxPitch is None: 
                appendPitch = True

            if appendPitch:
                pre.append(pCollect)
                preNodeId.append(n.id)

            if minPitch is not None and p.ps <= minPitch.ps:
                break

            if n.id == TERMINUS_LOW:
                if minPitch is None: # if not defined, stop at terminus high
                    break
                # get high and continue
                n = self._getTerminusHighNodes()[0]
        pre.reverse()
        preNodeId.reverse()
        return pre, preNodeId




    def realize(self, pitchReference, nodeId=None, minPitch=None, maxPitch=None, 
        direction=DIRECTION_BI, alteredNodes={}):
        '''Realize the nodes of this network based on a pitch assigned to a valid `nodeId`, where `nodeId` can be specified by integer (starting from 1) or key (a tuple of origin, destination keys). 

        Without a min or max pitch, the given pitch reference is assigned to the designated node, and then both ascends to the terminus and descends to the terminus.

        The `alteredNodes` dictionary permits creating mappings between node step and direction and interval transposition of intervals. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.realize('c2', 1, 'c2', 'c3')
        ([C2, D2, E2, F2, G2, A2, B2, C3], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh'])
        >>> alteredNodes = {7:{'direction':'bi', 'interval':interval.Interval('-a1')}}
        >>> net.realize('c2', 1, 'c2', 'c4', alteredNodes=alteredNodes)
        ([C2, D2, E2, F2, G2, A2, B-2, C3, D3, E3, F3, G3, A3, B-3, C4], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh', 0, 1, 2, 3, 4, 5, 'terminusHigh'])

        '''
        # get first node if no node is provided
#         if isinstance(nodeId, Node):
#             nodeObj = nodeId
#         elif nodeId == None: # assume first
#             nodeObj = self._getTerminusLowNodes()[0]
#         else:
#             nodeObj = self._nodeNameToNodes(nodeId)[0]
#             
#         if common.isStr(pitchReference):
#             pitchReference = pitch.Pitch(pitchReference)
#         if common.isStr(maxPitch):
#             maxPitch = pitch.Pitch(maxPitch)
#         if common.isStr(minPitch):
#             minPitch = pitch.Pitch(minPitch)
# 
#         post = []
#         postNodeId = [] # store node ids as well
# 
#         # when the pitch reference is altered, we need to get the
#         # unaltered version of this pitch. 
#         pUnaltered = self._getUnalteredPitch(pitchReference, nodeObj,
#                      direction=direction, alteredNodes=alteredNodes)
#         if pUnaltered is not None:
#             pitchReference = pUnaltered
#         #environLocal.printDebug(['realize()', 'pitchReference', pitchReference, 'nodeId', nodeId, 'pUnaltered', pUnaltered])
# 
#         # first, go upward from this pitch to the high terminus
#         n = nodeObj
#         p = pitchReference # we start with the pitch that is the reference
#         pCollect = p # usually p, unless the tone has been altered
#         while True:
#             #environLocal.printDebug(['here', p])
#             appendPitch = False
#             if (minPitch is not None and pCollect.ps >= minPitch.ps and 
#                 maxPitch is not None and pCollect.ps <= maxPitch.ps):
#                 appendPitch = True
#             elif (minPitch is not None and pCollect.ps >= minPitch.ps and 
#                 maxPitch is None):
#                 appendPitch = True
#             elif (maxPitch is not None and pCollect.ps <= maxPitch.ps and 
#                 minPitch is None):
#                 appendPitch = True
#             elif minPitch is None and maxPitch is None: 
#                 # for now, just include when not defined
#                 appendPitch = True
# 
#             if appendPitch:
#                 post.append(pCollect)
#                 postNodeId.append(n.id)
# 
#             if maxPitch is not None and p.ps >= maxPitch.ps:
#                 break
# 
#             # must check first, and at end
#             if n.id == TERMINUS_HIGH:
#                 if maxPitch is None: # if not defined, stop at terminus high
#                     break
#                 n = self._getTerminusLowNodes()[0]
# 
#             # this returns a list of possible edges and nodes
#             nextBundle = self._getNext(n, DIRECTION_ASCENDING)
#             # if we cannot continue to ascend, then we must break
#             if nextBundle is None:
#                 break
# 
#             postEdge, postNode = nextBundle
#             intervalObj = postEdge[0].interval # get first
#             p = intervalObj.transposePitch(p, maxAccidental=1)
#             pCollect = p
#             n = postNode[0]
# 
#             pCollect = self._processAlteredNodes(alteredNodes=alteredNodes, 
#                        n=n, p=p, direction=direction)
# 
#         #environLocal.printDebug(['got post pitch:', post])
#         #environLocal.printDebug(['got post node id:', postNodeId])
# 
#         n = nodeObj
#         p = pitchReference
#         pCollect = p # usually p, unless the tone has been altered
#         pre = []
#         preNodeId = [] # store node ids as well
#         while True:
#             if n.id == TERMINUS_LOW:
#                 if minPitch is None: # if not defined, stop at terminus high
#                     break
# 
#             nextBundle = self._getNext(n, DIRECTION_DESCENDING)
#             if nextBundle is None:
#                 environLocal.printDebug(['realize():', 'cannot descend from n', n])
#                 break
#             postEdge, postNode = nextBundle
#             intervalObj = postEdge[0].interval # get first
#             p = intervalObj.reverse().transposePitch(p, maxAccidental=1)
#             pCollect = p
#             n = postNode[0]
# 
#             pCollect = self._processAlteredNodes(alteredNodes=alteredNodes, 
#                        n=n, p=p, direction=direction)
# 
#             appendPitch = False
#             if (minPitch is not None and p.ps >= minPitch.ps and 
#                 maxPitch is not None and p.ps <= maxPitch.ps):
#                 appendPitch = True
#             elif (minPitch is not None and p.ps >= minPitch.ps and 
#                 maxPitch is None):
#                 appendPitch = True
#             elif (maxPitch is not None and p.ps <= maxPitch.ps and 
#                 minPitch is None):
#                 appendPitch = True
#             elif minPitch is None and maxPitch is None: 
#                 # for now, just include when not defined
#                 appendPitch = True
# 
#             if appendPitch:
#                 pre.append(pCollect)
#                 preNodeId.append(n.id)
# 
#             if minPitch is not None and p.ps <= minPitch.ps:
#                 break
# 
#             if n.id == TERMINUS_LOW:
#                 if minPitch is None: # if not defined, stop at terminus high
#                     break
#                 # get high and continue
#                 n = self._getTerminusHighNodes()[0]
#         pre.reverse()
#         preNodeId.reverse()

        #environLocal.printDebug(['got pre pitch:', pre])
        #environLocal.printDebug(['got pre node:', preNodeId])


        if common.isStr(pitchReference):
            pitchReference = pitch.Pitch(pitchReference)
        if common.isStr(minPitch):
            minPitch = pitch.Pitch(minPitch)
        if common.isStr(maxPitch):
            maxPitch = pitch.Pitch(maxPitch)

        # use great or eq
#         if (maxPitch is not None and maxPitch.ps >= pitchReference.ps) or maxPitch is None:
#             post, postNodeId = self._realizeAscending(pitchReference=pitchReference, nodeId=nodeId, minPitch=minPitch, maxPitch=maxPitch, alteredNodes=alteredNodes)
#         else:
#             post, postNodeId = [], []


        post, postNodeId = self._realizeAscending(pitchReference=pitchReference, nodeId=nodeId, minPitch=minPitch, maxPitch=maxPitch, alteredNodes=alteredNodes)

        #environLocal.printDebug(['realize()', 'post', post, postNodeId])

#         if (minPitch is not None and minPitch.ps < pitchReference.ps) or minPitch is None:
#             pre, preNodeId = self._realizeDescending(pitchReference=pitchReference, nodeId=nodeId, minPitch=minPitch, maxPitch=maxPitch, alteredNodes=alteredNodes, includeReference=False)
#         else:
#             pre, preNodeId = [], []

        pre, preNodeId = self._realizeDescending(pitchReference=pitchReference, nodeId=nodeId, minPitch=minPitch, maxPitch=maxPitch, alteredNodes=alteredNodes, includeReference=False)

        #environLocal.printDebug(['realize()', 'pre', pre, preNodeId])

        return pre + post, preNodeId + postNodeId


    def realizePitch(self, pitchReference, nodeId=None, minPitch=None,
        maxPitch=None, direction=DIRECTION_BI, alteredNodes={}):
        '''Realize the native nodes of this network based on a pitch assigned to a valid `nodeId`, where `nodeId` can be specified by integer (starting from 1) or key (a tuple of origin, destination keys). 

        The nodeId, when a simple, linear network, can be used as a scale step value starting from one.

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)
        >>> net.realizePitch(pitch.Pitch('G3'))
        [G3, A3, B3, C4, D4, E4, F#4, G4]

        >>> net.realizePitch(pitch.Pitch('G3'), 5) # G3 is the fifth (scale) degree
        [C3, D3, E3, F3, G3, A3, B3, C4]

        >>> net.realizePitch(pitch.Pitch('G3'), 7) # G3 is the seventh (scale) degree
        [A-2, B-2, C3, D-3, E-3, F3, G3, A-3]

        >>> net.realizePitch(pitch.Pitch('G3'), 1) # seventh (scale) degree
        [G3, A3, B3, C4, D4, E4, F#4, G4]

        >>> net.realizePitch(pitch.Pitch('f#3'), 1, 'f2', 'f3') 
        [E#2, F#2, G#2, A#2, B2, C#3, D#3, E#3]

        >>> net.realizePitch(pitch.Pitch('a#2'), 7, 'c6', 'c7') 
        [C#6, D#6, E6, F#6, G#6, A#6, B6]
        '''
        return self.realize(pitchReference=pitchReference, nodeId=nodeId, minPitch=minPitch, maxPitch=maxPitch, direction=direction, alteredNodes=alteredNodes)[0]



    def realizePitchByStep(self, pitchReference, nodeId=None, 
        nodeStepTargets=[1],
        minPitch=None, maxPitch=None, direction=DIRECTION_BI, alteredNodes={}):
        '''Realize the native nodes of this network based on a pitch assigned to a valid `nodeId`, where `nodeId` can be specified by integer (starting from 1) or key (a tuple of origin, destination keys). 

        The `targetSteps` specifies the the steps to be included within the specified range. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork()
        >>> net.fillBiDirectedEdges(edgeList)

        >>> net.realizePitchByStep('g', 5, [1,5], 'c2', 'c4') 
        [C2, G2, C3, G3, C4]

        >>> net.realizePitchByStep('g', 5, [1,2,3], 'c1', 'c6') 
        [C1, D1, E1, C2, D2, E2, C3, D3, E3, C4, D4, E4, D5, E5]
        '''
        realizedPitch, realizedNode = self.realize(
            pitchReference=pitchReference, nodeId=nodeId, 
            minPitch=minPitch, maxPitch=maxPitch, 
            direction=direction, alteredNodes=alteredNodes)

        # take modulus of all
        nodeStepTargets = [self._stepModulus(s) for s in nodeStepTargets]

        post = []
        for i, p in enumerate(realizedPitch):
            # get the node
            n = self._nodes[realizedNode[i]]
            if n.step in nodeStepTargets:
                post.append(p)
        return post


    def _getNetworkxGraph(self):
        '''Create a networx graph from the raw Node representation.
        '''
        #g = networkx.DiGraph()
        g = networkx.MultiDiGraph()

        for eId, e in self._edges.items():
            if e.direction == DIRECTION_ASCENDING:
                weight = 0.9
                style = 'solid'
            elif e.direction == DIRECTION_DESCENDING:
                weight = 0.6
                style = 'solid'
            elif e.direction == DIRECTION_BI:
                weight = 1.0
                style = 'solid'
            for src, dst in e._connections:
                g.add_edge(src, dst, weight=weight, style=style)

        # set positions of all nodes based on step, where y value is step
        # and x is count of values at that step
        stepCount = {} # step, count pairs
        # sorting nodes will help, but not insure, proper positioning
        nKeys = self._nodes.keys()
        nKeys.sort()
        for nId in nKeys:
            n = self._nodes[nId]
            if n.step not in stepCount.keys():
                stepCount[n.step] = 0
            g.node[nId]['pos'] = (stepCount[n.step], n.step)
            stepCount[n.step] += 1
        environLocal.printDebug(['got step count', stepCount])
        return g

    def _getNetworkxRealizedGraph(self, pitchObj, nodeId=None, 
        minPitch=None, maxPitch=None):
        '''Create a networx graph from this representation.
        '''
        # this presently assumes that the realized form is in linear order
        realized = self.realizePitch(pitchObj=pitchObj, nodeId=nodeId, 
                   minPitch=minPitch, maxPitch=maxPitch)
        g = networkx.Graph()
        for i, p in enumerate(realized):
            if i > len(realized) - 2: 
                continue # will be last, will continue
            pNext = realized[i+1]
            g.add_edge(p.nameWithOctave, pNext.nameWithOctave, weight=0.6)
        return g


    networkxGraph = property(_getNetworkxRealizedGraph, doc='''
        Return a networks Graph object representing a realized version of this IntervalNetwork
        ''')

    def plot(self, pitchObj=None, nodeId=None, minPitch=None, maxPitch=None, 
            *args, **keywords):
        '''Given a method and keyword configuration arguments, create and display a plot.
        '''
#         >>> from music21 import *
#         >>> s = corpus.parseWork('bach/bwv324.xml') #_DOCS_HIDE
#         >>> s.plot('pianoroll', doneAction=None) #_DOCS_HIDE
#         >>> #_DOCS_SHOW s = corpus.parseWork('bach/bwv57.8')
#         >>> #_DOCS_SHOW s.plot('pianoroll')
    
#         .. image:: images/PlotHorizontalBarPitchSpaceOffset.*
#             :width: 600
        if pitchObj is None:
            pitchObj = pitch.Pitch('C4')

        # import is here to avoid import of matplotlib problems
        from music21 import graph
        # first ordered arg can be method type
        g = graph.GraphNetworxGraph( 
            networkxGraph=self._getNetworkxGraph())

            #networkxGraph=self._getNetworkxRealizedGraph(pitchObj=pitchObj, nodeId=nodeId, minPitch=minPitch, maxPitch=maxPitch))
        g.process()



    def getRelativeNodeId(self, pitchReference, nodeName, pitchTarget, 
        comparisonAttribute='ps', alteredNodes={}):
        '''Given a reference pitch assigned to node id, determine the relative node id of pitchTarget, even if displaced over multiple octaves

        Returns None if no match.

        If `getNeighbor` is True, or direction, the nearest node will be returned. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork(edgeList)
        >>> net.getRelativeNodeId('a', 1, 'a4')
        'terminusLow'
        >>> net.getRelativeNodeId('a', 1, 'b-4') == None
        True
        '''
        if nodeName == None: # assume first
            nodeId = self._getTerminusLowNodes()[0]
        else:
            nodeId = self._nodeNameToNodes(nodeName)[0]

        if common.isStr(pitchTarget):
            pitchTarget = pitch.Pitch(pitchTarget)

        # try an octave spread first
        # if a scale step is larger than an octave this will fail
        minPitch = pitchTarget.transpose(-12, inPlace=False)
        maxPitch = pitchTarget.transpose(12, inPlace=False)

        realizedPitch, realizedNode = self.realize(pitchReference, nodeId, minPitch=minPitch, maxPitch=maxPitch, alteredNodes=alteredNodes)

        for i in range(len(realizedPitch)):
            #environLocal.printDebug(['getRelativeNodeId', 'comparing',  realizedPitch[i], realizedNode[i]])

            # comparison of attributes, not object
            match = False
            if getattr(pitchTarget, comparisonAttribute) == getattr(realizedPitch[i], comparisonAttribute):
                match = True
            if match:
                #environLocal.printDebug(['getRelativeNodeId', 'pitchReference', pitchReference, 'input nodeId', nodeId, 'pitchTarget', pitchTarget, 'matched', realizedNode[i]])
                return realizedNode[i]
        return None

    def getNeighborNodeIds(self, pitchReference, nodeName, pitchTarget,
         alteredNodes={}):
        '''Given a reference pitch assigned to node id, determine the node ids that neighbor this pitch.

        Returns None if an exact match.

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork(edgeList)
        >>> net.getNeighborNodeIds('c4', 1, 'b-')
        (4, 5)
        >>> net.getNeighborNodeIds('c4', 1, 'b')
        (5, 'terminusHigh')
        '''
        if nodeName == None: # assume first
            nodeId = self._getTerminusLowNodes()[0]
        else:
            nodeId = self._nodeNameToNodes(nodeName)[0]

        if common.isStr(pitchTarget):
            pitchTarget = pitch.Pitch(pitchTarget)

        # try an octave spread first
        # if a scale step is larger than an octave this will fail
        minPitch = pitchTarget.transpose(-12, inPlace=False)
        maxPitch = pitchTarget.transpose(12, inPlace=False)

        realizedPitch, realizedNode = self.realize(pitchReference, nodeId, minPitch=minPitch, maxPitch=maxPitch, alteredNodes=alteredNodes)

        lowNeighbor = None
        highNeighbor = None
        for i in range(len(realizedPitch)):
            if pitchTarget.ps < realizedPitch[i].ps:
                highNeighbor = realizedNode[i]
                return lowNeighbor, highNeighbor
            lowNeighbor = realizedNode[i]
        return None


    def getRelativeNodeStep(self, pitchReference, nodeName, pitchTarget, 
        comparisonAttribute='ps', alteredNodes={}):
        '''Given a reference pitch assigned to node id, determine the relative node id of pitchTarget, even if displaced over multiple octaves
        
        Need flags for pitch class and enharmonic comparison. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork(edgeList)
        >>> net.realizePitch(pitch.Pitch('e-2'))
        [E-2, F2, G2, A-2, B-2, C3, D3, E-3]

        >>> net.getRelativeNodeStep('e-2', 1, 'd3') # if e- is tonic, what is d3
        7
        >>> net.getRelativeNodeStep('e3', 1, 'd5') == None
        True
        >>> net.getRelativeNodeStep('e-3', 1, 'b-3')
        5

        >>> net.getRelativeNodeStep('e-3', 1, 'e-5')
        1
        >>> net.getRelativeNodeStep('e-2', 1, 'f3')
        2
        >>> net.getRelativeNodeStep('e-3', 1, 'b6') == None
        True

        >>> net.getRelativeNodeStep('e-3', 1, 'e-2')
        1
        >>> net.getRelativeNodeStep('e-3', 1, 'd3')
        7
        >>> net.getRelativeNodeStep('e-3', 1, 'e-3')
        1
        >>> net.getRelativeNodeStep('e-3', 1, 'b-1')
        5


        >>> from music21 import *
        >>> edgeList = ['p4', 'p4', 'p4'] # a non octave-repeating scale
        >>> net = IntervalNetwork(edgeList)
        >>> net.realizePitch('f2')
        [F2, B-2, E-3, A-3]
        >>> net.realizePitch('f2', 1, 'f2', 'f6')
        [F2, B-2, E-3, A-3, D-4, G-4, C-5, F-5, A5, D6]

        >>> net.getRelativeNodeStep('f2', 1, 'a-3') # could be 4 or 1
        1
        >>> net.getRelativeNodeStep('f2', 1, 'd-4') # 2 is correct
        2
        >>> net.getRelativeNodeStep('f2', 1, 'g-4') # 3 is correct
        3
        >>> net.getRelativeNodeStep('f2', 1, 'c-5') # could be 4 or 1
        1
        >>> net.getRelativeNodeStep('f2', 1, 'e--6') # could be 4 or 1
        1


        >>> net.realizePitch('f6', 1, 'f2', 'f6')
        [G#2, C#3, F#3, B3, E4, A4, D5, G5, C6, F6]

        >>> net.getRelativeNodeStep('f6', 1, 'd5') 
        1
        >>> net.getRelativeNodeStep('f6', 1, 'g5') 
        2
        >>> net.getRelativeNodeStep('f6', 1, 'a4') 
        3
        >>> net.getRelativeNodeStep('f6', 1, 'e4') 
        2
        >>> net.getRelativeNodeStep('f6', 1, 'b3') 
        1

        '''
        # TODO: needs to use cached results if possible
        nId = self.getRelativeNodeId(pitchReference=pitchReference, 
            nodeName=nodeName, pitchTarget=pitchTarget, 
            comparisonAttribute=comparisonAttribute, alteredNodes=alteredNodes)
        if nId == None:
            return None
        else:
            return self._nodeIdToNodeStep(nId)


    def getPitchFromNodeStep(self, pitchReference, nodeName, nodeStepTarget, 
        direction=DIRECTION_BI, minPitch=None, 
        maxPitch=None, alteredNodes={}):
        '''Given a reference pitch assigned to node id, determine the pitch for the the target node step. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = IntervalNetwork(edgeList)
        >>> net.realizePitch(pitch.Pitch('e-2'))
        [E-2, F2, G2, A-2, B-2, C3, D3, E-3]
        >>> net.getPitchFromNodeStep('e4', 1, 1)
        E4
        >>> net.getPitchFromNodeStep('e4', 1, 7) # seventh scale degree
        D#5
        >>> net.getPitchFromNodeStep('e4', 1, 8) 
        E4
        >>> net.getPitchFromNodeStep('e4', 1, 9) 
        F#4
        >>> net.getPitchFromNodeStep('e4', 1, 3, minPitch='c2', maxPitch='c3') 
        G#2
        >>> # will always get the lowest
        >>> net.getPitchFromNodeStep('e4', 1, 3, minPitch='c2', maxPitch='c10') 
        G#2

        '''
        # this is the reference node
        nodeId = self._nodeNameToNodes(nodeName)[0] # get the first
        #environLocal.printDebug(['getPitchFromNodeStep()', 'node reference', nodeId, 'node step', nodeId.step, 'pitchReference', pitchReference, 'alteredNodes', alteredNodes])

        nodeTargetId = self._nodeNameToNodes(nodeStepTarget, 
                        permitStepModuli=True)[0] # get the first

        #environLocal.printDebug(['getPitchFromNodeStep()', 'nodeTargetId', nodeTargetId])

        # pass direction as well when getting realization
        realizedPitch, realizedNode = self.realize(
            pitchReference=pitchReference, 
            nodeId=nodeId, 
            minPitch=minPitch, 
            maxPitch=maxPitch, 
            direction=direction,
            alteredNodes=alteredNodes)

        #environLocal.printDebug(['getPitchFromNodeStep()', 'realizedPitch', realizedPitch])


        # get the pitch when we have a node id match
        for i, nId in enumerate(realizedNode):
            #environLocal.printDebug(['comparing', nId, 'nodeTargetId', nodeTargetId])
            if nId == nodeTargetId.id:
                return realizedPitch[i]



        
    def _filterPitchList(self, pitchTarget):
        '''Given a list or one pitch, check if all are pitch objects; convert if necessary.

        >>> from music21 import *
        >>> net = intervalNetwork.IntervalNetwork()
        >>> net._filterPitchList('c#')
        ([C#], C#, C#)

        >>> net._filterPitchList(['c#4', 'f5', 'd3'])
        ([C#4, F5, D3], D3, F5)
        '''
        if not common.isListLike(pitchTarget):
            if common.isStr(pitchTarget):
                pitchTarget = pitch.Pitch(pitchTarget)
            pitchTarget = [pitchTarget]
        else:
            # convert a list of string into pitch objects
            temp = []
            for p in pitchTarget:
                if common.isStr(p):
                    temp.append(pitch.Pitch(p))
            if len(temp) == len(pitchTarget):
                pitchTarget = temp

        # automatically derive a min and max from the supplied pitch
        sortList = [(pitchTarget[i].ps, i) for i in range(len(pitchTarget))]
        sortList.sort()
        minPitch = pitchTarget[sortList[0][1]] # first index
        maxPitch = pitchTarget[sortList[-1][1]] # last index

        return pitchTarget, minPitch, maxPitch


    def match(self, pitchReference, nodeId, pitchTarget, 
        comparisonAttribute='pitchClass', alteredNodes={}):
        '''Given one or more pitches in `pitchTarget`, return a list of matched pitches, and unmatched pitches. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = intervalNetwork.IntervalNetwork(edgeList)
        >>> net.realizePitch('e-2')
        [E-2, F2, G2, A-2, B-2, C3, D3, E-3]

        >>> net.match('e-2', 1, 'c3') # if e- is tonic, is 'c3' in the scale?
        ([C3], [])

        >>> net.match('e-2', 1, 'd3')
        ([D3], [])

        >>> net.match('e-2', 1, 'd#3')
        ([D#3], [])

        >>> net.match('e-2', 1, 'e3')
        ([], [E3])

        >>> pitchTarget = [pitch.Pitch('b-2'), pitch.Pitch('b2'), pitch.Pitch('c3')]
        >>> net.match('e-2', 1, pitchTarget)
        ([B-2, C3], [B2])

        >>> pitchTarget = ['b-2', 'b2', 'c3', 'e-3', 'e#3', 'f2', 'e--2']
        >>> net.match('e-2', 1, pitchTarget)
        ([B-2, C3, E-3, E#3, F2, E--2], [B2])

        '''
        # these return a Node, not a nodeId
        if nodeId == None: # assume first
            nodeId = self._getTerminusLowNodes()[0]
        else:
            nodeId = self._nodeNameToNodes(nodeId)[0]

        pitchTarget, minPitch, maxPitch = self._filterPitchList(pitchTarget)

        # TODO: need to do both directions
        nodesRealized = self.realizePitch(pitchReference, nodeId, 
                        minPitch, maxPitch, alteredNodes=alteredNodes)

        matched = []
        noMatch = []
        notFound = []

        for target in pitchTarget:
            found = False
            for p in nodesRealized:
                # enharmonic switch here
                match = False
                if getattr(p, comparisonAttribute) == getattr(target, comparisonAttribute):
                    match = True

                if match:
                    matched.append(target)
                    found = True
                    break
            if not found:
                noMatch.append(target)            
        return matched, noMatch
                

    def findMissing(self, pitchReference, nodeId, 
            pitchTarget, comparisonAttribute='pitchClass', 
            minPitch=None, maxPitch=None, 
            direction=DIRECTION_BI, alteredNodes={}):
        '''Find all pitches in the realized scale that are not in the pitch target network based on the comparison attribute. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = intervalNetwork.IntervalNetwork(edgeList)
        >>> net.realizePitch('G3')
        [G3, A3, B3, C4, D4, E4, F#4, G4]
        >>> net.findMissing('g', 1, ['g', 'a', 'b', 'd', 'f#'])
        [C5, E5]
        '''
            
        # these return a Node, not a nodeId
        if nodeId == None: # assume first
            nodeId = self._getTerminusLowNodes()[0]
        else:
            nodeId = self._nodeNameToNodes(nodeId)[0]

        # TODO: need to do both directions
        nodesRealized = self.realizePitch(pitchReference, nodeId, 
                        minPitch=minPitch, maxPitch=maxPitch, alteredNodes=alteredNodes)

        # note: reassigns min and max
        pitchTarget, minPitch, maxPitch = self._filterPitchList(pitchTarget)

        #environLocal.printDebug(['nodesRealzied:', nodesRealized,])
        post = []
        for target in nodesRealized:
            match = False
            for p in pitchTarget:
                # enharmonic switch here
                if getattr(p, comparisonAttribute) == getattr(target, comparisonAttribute):
                    match = True
                    break
            #environLocal.printDebug(['looking at:', target, p, 'match', match])
            if not match:
                post.append(target)
        return post



    def find(self, pitchTarget, resultsReturned=4, 
        comparisonAttribute='pitchClass', alteredNodes={}):
        '''Given a collection of pitches, test all transpositions of a realized version of this network, and return the number of matches in each for each pitch assigned to the first node. 

        >>> from music21 import *
        >>> edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        >>> net = intervalNetwork.IntervalNetwork(edgeList)
        >>> # a network built on G or D as 
        >>> net.find(['g', 'a', 'b', 'd', 'f#'])
        [(5, G), (5, D), (4, A), (4, C)]

        >>> net.find(['g', 'a', 'b', 'c', 'd', 'e', 'f#'])
        [(7, G), (6, D), (6, C), (5, A)]

        '''

        nodeId = self._getTerminusLowNodes()[0]
        sortList = []

        # for now, searching 12 pitches; this may be more than necessary
#         for p in [pitch.Pitch('c'), pitch.Pitch('c#'),
#                   pitch.Pitch('d'), pitch.Pitch('d#'),
#                   pitch.Pitch('e'), pitch.Pitch('f'),
#                   pitch.Pitch('f#'), pitch.Pitch('g'),
#                   pitch.Pitch('g#'), pitch.Pitch('a'),
#                   pitch.Pitch('a#'), pitch.Pitch('b'),
#                 ]:

        for p in [pitch.Pitch('c'), pitch.Pitch('c#'), pitch.Pitch('d-'),
                  pitch.Pitch('d'), pitch.Pitch('d#'), pitch.Pitch('e-'),
                  pitch.Pitch('e'), pitch.Pitch('f'),
                  pitch.Pitch('f#'), pitch.Pitch('g'),
                  pitch.Pitch('g#'), pitch.Pitch('a'), pitch.Pitch('b-'),
                  pitch.Pitch('b'), pitch.Pitch('c-'),
                ]:


            # realize scales from each pitch, and then compare to pitchTarget   
            # pitchTarget may be a list of pitches
            matched, noMatch = self.match(p, nodeId, pitchTarget,
                               comparisonAttribute=comparisonAttribute,
                               alteredNodes=alteredNodes)                
            sortList.append((len(matched), p))

        sortList.sort()
        sortList.reverse() # want most amtches first
        return sortList[:resultsReturned]  







#-------------------------------------------------------------------------------
class Test(unittest.TestCase):

    def runTest(self):
        pass
    

    def testScaleModel(self):

        # define ordered list of intervals
        edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        net = IntervalNetwork(edgeList)
        
        # get this scale for any pitch at any step over any range
        # need a major scale with c# as the third degree
        match = net.realizePitch('c#', 3)        
        self.assertEqual(str(match), '[A3, B3, C#, D4, E4, F#4, G#4, A4]')
        

        # need a major scale with c# as the leading tone in a high octave
        match = net.realizePitch('c#', 7, 'c8', 'c9')        
        self.assertEqual(str(match), '[C#8, D8, E8, F#8, G8, A8, B8]')
        


        # for a given realization, we can find out the scale degree of any pitch
        self.assertEqual(net.getRelativeNodeStep('b', 7, 'c2'), 1)


        # if c# is the leading tone, what is d? 1
        self.assertEqual(net.getRelativeNodeStep('c#', 7, 'd2'), 1)
        # if c# is the mediant, what is d? 4
        self.assertEqual(net.getRelativeNodeStep('c#', 3, 'd2'), 4)
        
        # we can create non-octave repeating scales too
        edgeList = ['P5', 'P5', 'P5']
        net = IntervalNetwork(edgeList)
        match = net.realizePitch('c4', 1)        
        self.assertEqual(str(match), '[C4, G4, D5, A5]')
        match = net.realizePitch('c4', 1, 'c4', 'c11')        
        self.assertEqual(str(match), '[C4, G4, D5, A5, E6, B6, F#7, C#8, G#8, D#9, A#9, E#10, B#10]')
        
        # based on the original interval list, can get information on scale steps, even for non-octave repeating scales
        self.assertEqual(net.getRelativeNodeStep('c4', 1, 'e#10'), 3)
        
        
        # we can also search for realized and possible matches in a network
        edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        net = IntervalNetwork(edgeList)
        
        # if we know a realized version, we can test if pitches match in that version; returns matched, not found, and no match lists
        # f i s found in a scale where e- is the tonic
        matched, noMatch = net.match('e-', 1, 'f')
        self.assertEqual(str(matched), '[F]')
        
        # can search a list of pitches, isolating non-scale tones
        # if e- is the tonic, which pitches are part of the scale
        matched, noMatch = net.match('e-', 1, ['b-', 'd-', 'f'])
        self.assertEqual(str(matched), '[B-, F]')
        self.assertEqual(str(noMatch), '[D-]')
        
        # finally, can search the unrealized network; all possible realizations
        # are tested, and the matched score is returned
        # the first top 4 results are returned by default
        
        # in this case, the nearest major keys are G and D
        results = net.find(['g', 'a', 'b', 'd', 'f#'])
        self.assertEqual(str(results), '[(5, G), (5, D), (4, A), (4, C)]')
        
        # with an f#, D is the most-matched first node pitch
        results = net.find(['g', 'a', 'b', 'c#', 'd', 'f#'])
        self.assertEqual(str(results), '[(6, D), (5, A), (5, G), (4, E)]')


    def testHarmonyModel(self):

        # can define a chord type as a sequence of intervals
        # to assure octave redundancy, must provide top-most interval to octave
        # this could be managed in specialized subclass
        
        edgeList = ['M3', 'm3', 'P4']
        net = IntervalNetwork(edgeList)
        
        # if g# is the root, or first node
        match = net.realizePitch('g#', 1)        
        self.assertEqual(str(match), '[G#, B#4, D#5, G#5]')
        
        # if g# is the fifth, or third node
        # a specialzied subclass can handle this mapping
        match = net.realizePitch('g#', 3)        
        self.assertEqual(str(match), '[C#4, E#4, G#, C#5]')
        
        # if g# is the third, or second node, across a wide range
        match = net.realizePitch('g#', 2, 'c2', 'c5')        
        self.assertEqual(str(match), '[E2, G#2, B2, E3, G#3, B3, E4, G#, B4]')
        
        # can match pitches to a realization of this chord
        # given a chord built form node 2 as g#, are e2 and b6 in this network
        matched, noMatch = net.match('g#', 2, ['e2', 'b6'])
        self.assertEqual(str(matched), '[E2, B6]')
        
        # can find a first node (root) that match any provided pitches
        # this is independent of any realization
        results = net.find(['c', 'e', 'g'])
        self.assertEqual(str(results), '[(3, C), (1, A), (1, G#), (1, G)]')
        
        # in this case, most likely an e triad
        results = net.find(['e', 'g#'])
        self.assertEqual(str(results), '[(2, E), (1, A), (1, G#), (1, D-)]')
        
        
        # we can do the same with larger or more complicated chords
        # again, we must provide the interval to the octave
        edgeList = ['M3', 'm3', 'M3', 'm3', 'm7']
        net = IntervalNetwork(edgeList)
        match = net.realizePitch('c4', 1)        
        self.assertEqual(str(match), '[C4, E4, G4, B4, D5, C6]')
        
        # if we want the same chord where c4 is the 5th node, or the ninth
        match = net.realizePitch('c4', 5)        
        self.assertEqual(str(match), '[B-2, D3, F3, A3, C4, B-4]')
        
        # we can of course provide any group of pitches and find the value
        # of the lowest node that provides the best fit
        results = net.find(['e', 'g#', 'b', 'd#'])
        self.assertEqual(str(results), '[(3, E), (2, C), (1, B), (1, G#)]')


    def testScaleAndHarmony(self):

        # start with a major scale
        edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        netScale = IntervalNetwork(edgeList)
        
        # take a half diminished seventh chord
        edgeList = ['m3', 'm3', 'M3', 'M2']
        netHarmony = IntervalNetwork(edgeList)
        match = netHarmony.realizePitch('b4', 1)        
        self.assertEqual(str(match), '[B4, D5, F5, A5, B5]')
        
        
        # given a half dim seventh chord built on c#, what scale contains
        # these pitches?
        results = netScale.find(netHarmony.realizePitch('c#', 1))
        # most likely, a  D
        self.assertEqual(str(results), '[(5, D), (4, B), (4, A), (4, E)]')
        # what scale degree is c# in this scale? the seventh
        self.assertEqual(netScale.getRelativeNodeStep('d', 1, 'c#'), 7)


    def testGraphedOutput(self):
        # note this relies on networkx
        edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        netScale = IntervalNetwork(edgeList)
        #netScale.plot(pitchObj='F#', nodeId=3, minPitch='c2', maxPitch='c5')


    def testBasicA(self):
        edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        net = IntervalNetwork()
        net.fillBiDirectedEdges(edgeList)

        self.assertEqual(net._edges.keys(), [0, 1, 2, 3, 4, 5, 6])
        self.assertEqual(sorted(net._nodes.keys()), [0, 1, 2, 3, 4, 5, 'terminusHigh', 'terminusLow'])

        self.assertEqual(repr(net._nodes[0]), "<music21.intervalNetwork.Node id=0>")
        self.assertEqual(repr(net._nodes['terminusLow']), "<music21.intervalNetwork.Node id='terminusLow'>")

        self.assertEqual(repr(net._edges[0]), "<music21.intervalNetwork.Edge bi M2 [('terminusLow',0),(0,'terminusLow')]>")

        self.assertEqual(repr(net._edges[3]), "<music21.intervalNetwork.Edge bi M2 [(2,3),(3,2)]>")

        self.assertEqual(repr(net._edges[6]), "<music21.intervalNetwork.Edge bi m2 [(5,'terminusHigh'),('terminusHigh',5)]>")


        # getting connections: can filter by direction
        self.assertEqual(repr(net._edges[6].getConnections(
            DIRECTION_ASCENDING)), "[(5, 'terminusHigh')]")
        self.assertEqual(repr(net._edges[6].getConnections(
            DIRECTION_DESCENDING)), "[('terminusHigh', 5)]")
        self.assertEqual(repr(net._edges[6].getConnections(
            DIRECTION_BI)), "[(5, 'terminusHigh'), ('terminusHigh', 5)]")

        # in calling get next, get a lost of edges and a lost of nodes that all
        # describe possible pathways
        self.assertEqual(net._getNext(net._nodes['terminusLow'], 'ascending'), ( [net._edges[0]], [net._nodes[0]]))

        self.assertEqual(net._getNext(net._nodes['terminusLow'], 'descending'), ( [net._edges[6]], [net._nodes[5]]))


        self.assertEqual(str(net.realizePitch('c4', 1)), '[C4, D4, E4, F4, G4, A4, B4, C5]')

        self.assertEqual(str(net.realizePitch('c4', 1, maxPitch='c6')), '[C4, D4, E4, F4, G4, A4, B4, C5, D5, E5, F5, G5, A5, B5, C6]')

        self.assertEqual(str(net.realizePitch('c4', 1, minPitch='c3')), '[C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4, C5]')

        self.assertEqual(str(net.realizePitch('c4', 1, minPitch='c3', maxPitch='c6')), '[C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4, C5, D5, E5, F5, G5, A5, B5, C6]')

        self.assertEqual(str(net.realizePitch('f4', 1, minPitch='c3', maxPitch='c6')), '[C3, D3, E3, F3, G3, A3, B-3, C4, D4, E4, F4, G4, A4, B-4, C5, D5, E5, F5, G5, A5, B-5, C6]')


        self.assertEqual(str(net.realizePitch('C#', 7)), '[D3, E3, F#3, G3, A3, B3, C#, D4]')

        self.assertEqual(str(net.realizePitch('C#4', 7, 'c8', 'c9')), '[C#8, D8, E8, F#8, G8, A8, B8]')

        self.assertEqual(str(net.realize('c4', 1)), "([C4, D4, E4, F4, G4, A4, B4, C5], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh'])")


        self.assertEqual(str(net.realize('c#4', 7)), "([D3, E3, F#3, G3, A3, B3, C#4, D4], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh'])")


    def testDirectedA(self):

        # test creating a harmonic minor scale by using two complete        
        # ascending and descending scales

        ascendingEdgeList = ['M2', 'm2', 'M2', 'M2', 'M2', 'M2', 'm2']
        # these are given in ascending order
        descendingEdgeList = ['M2', 'm2', 'M2', 'M2', 'm2', 'M2', 'M2']

        net = IntervalNetwork()
        net.fillDirectedEdges(ascendingEdgeList, descendingEdgeList)

        self.assertEqual(repr(net._edges), "{0: <music21.intervalNetwork.Edge ascending M2 [('terminusLow',0)]>, 1: <music21.intervalNetwork.Edge ascending m2 [(0,1)]>, 2: <music21.intervalNetwork.Edge ascending M2 [(1,2)]>, 3: <music21.intervalNetwork.Edge ascending M2 [(2,3)]>, 4: <music21.intervalNetwork.Edge ascending M2 [(3,4)]>, 5: <music21.intervalNetwork.Edge ascending M2 [(4,5)]>, 6: <music21.intervalNetwork.Edge ascending m2 [(5,'terminusHigh')]>, 7: <music21.intervalNetwork.Edge descending M2 [(6,'terminusLow')]>, 8: <music21.intervalNetwork.Edge descending m2 [(7,6)]>, 9: <music21.intervalNetwork.Edge descending M2 [(8,7)]>, 10: <music21.intervalNetwork.Edge descending M2 [(9,8)]>, 11: <music21.intervalNetwork.Edge descending m2 [(10,9)]>, 12: <music21.intervalNetwork.Edge descending M2 [(11,10)]>, 13: <music21.intervalNetwork.Edge descending M2 [('terminusHigh',11)]>}")

        # returns a list of edges and notes
        self.assertEqual(repr(net._getNext(net._nodes[TERMINUS_LOW], 'ascending')), "([<music21.intervalNetwork.Edge ascending M2 [('terminusLow',0)]>], [<music21.intervalNetwork.Node id=0>])")

        self.assertEqual(repr(net._getNext(net._nodes[TERMINUS_LOW], 'descending')), "([<music21.intervalNetwork.Edge descending M2 [('terminusHigh',11)]>], [<music21.intervalNetwork.Node id=11>])")

        # high terminus gets the same result, as this is the wrapping point
        self.assertEqual(repr(net._getNext(net._nodes[TERMINUS_HIGH], 'ascending')), "([<music21.intervalNetwork.Edge ascending M2 [('terminusLow',0)]>], [<music21.intervalNetwork.Node id=0>])")

        self.assertEqual(repr(net._getNext(net._nodes[TERMINUS_LOW], 'descending')), "([<music21.intervalNetwork.Edge descending M2 [('terminusHigh',11)]>], [<music21.intervalNetwork.Node id=11>])")


        # this is ascending from a4 to a5, then descending from a4 to a3
        # this seems like the right thing to do
        self.assertEqual(str(net.realize('a4', 1, 'a3', 'a5')), "([A3, B3, C4, D4, E4, F4, G4, A4, B4, C5, D5, E5, F#5, G#5, A5], ['terminusLow', 6, 7, 8, 9, 10, 11, 'terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh'])")


        # can get a descending form by setting reference pitch to top of range
        self.assertEqual(str(net.realizePitch('a5', 1, 'a4', 'a5')), 
        "[A4, B4, C5, D5, E5, F5, G5, A5]")

        # can get a descending form by setting reference pitch to top of range
        self.assertEqual(str(net.realizePitch('a4', 1, 'a4', 'a5')), 
        "[A4, B4, C5, D5, E5, F#5, G#5, A5]")
    
        # if we try to get a node by a name that is a step, we will get
        # two results, as one is the ascending and one is the descending
        # form
        self.assertEqual(str(net._nodeNameToNodes(3)), 
        "[<music21.intervalNetwork.Node id=1>, <music21.intervalNetwork.Node id=7>]")
        self.assertEqual(str(net._nodeNameToNodes(7)), 
        "[<music21.intervalNetwork.Node id=5>, <music21.intervalNetwork.Node id=11>]")
        #net.plot()


    def testScaleArbitrary(self):

        from music21 import scale

        
        sc1 = scale.MajorScale('g')
        self.assertEqual(str(sorted(sc1.abstract._net._nodes.keys())), "[0, 1, 2, 3, 4, 5, 'terminusHigh', 'terminusLow']")
        self.assertEqual(str(sorted(sc1.abstract._net._edges.keys())), "[0, 1, 2, 3, 4, 5, 6]")

        nodes = ({'id':'terminusLow', 'step':1},
                 {'id':0, 'step':2},
                 {'id':'terminusHigh', 'step':3},
                )

        edges = ({'interval':'m2', 'connections':(
                        ['terminusLow', 0, 'bi'],
                    )},
                {'interval':'M3', 'connections':(
                        [0, 'terminusHigh', 'bi'],
                    )},
                )

        net = IntervalNetwork()
        net.fillArbitrary(nodes, edges)

        self.assertEqual(str(net._edges), "{0: <music21.intervalNetwork.Edge bi m2 [('terminusLow',0),(0,'terminusLow')]>, 1: <music21.intervalNetwork.Edge bi M3 [(0,'terminusHigh'),('terminusHigh',0)]>}")

        
        self.assertEqual(net.stepMax, 3)
        self.assertEqual(net.stepMaxUnique, 2)

        self.assertEqual(str(net.realizePitch('c4', 1)), '[C4, D-4, F4]')



    def testRealizeDescending(self):
        edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        net = IntervalNetwork()
        net.fillBiDirectedEdges(edgeList)

        self.assertEqual(str(net._realizeDescending('c3', 1, 'c2')), 
        "([C2, D2, E2, F2, G2, A2, B2], ['terminusLow', 0, 1, 2, 3, 4, 5])")


        self.assertEqual(str(net._realizeDescending('c3', 'high', minPitch='c2')), 
        "([C2, D2, E2, F2, G2, A2, B2], ['terminusLow', 0, 1, 2, 3, 4, 5])")

        # this only gets one pitch as this is descending and includes reference 
        # pitch
        self.assertEqual(str(net._realizeDescending('c3', 1, includeReference=True)), 
        "([C3], ['terminusLow'])")

        self.assertEqual(str(net._realizeDescending('g3', 1, 'g0', includeReference=True)), 
        "([G0, A0, B0, C1, D1, E1, F#1, G1, A1, B1, C2, D2, E2, F#2, G2, A2, B2, C3, D3, E3, F#3, G3], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusLow', 0, 1, 2, 3, 4, 5, 'terminusLow', 0, 1, 2, 3, 4, 5, 'terminusLow'])")


        self.assertEqual(str(net._realizeDescending('d6', 5, 'd4', includeReference=True)), 
        "([D4, E4, F#4, G4, A4, B4, C5, D5, E5, F#5, G5, A5, B5, C6, D6], [3, 4, 5, 'terminusLow', 0, 1, 2, 3, 4, 5, 'terminusLow', 0, 1, 2, 3])"
        )


        self.assertEqual(str(net._realizeAscending('c3', 1)), "([C3, D3, E3, F3, G3, A3, B3, C4], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh'])"), 

        self.assertEqual(str(net._realizeAscending('g#2', 3)), "([G#2, A2, B2, C#3, D#3, E3], [1, 2, 3, 4, 5, 'terminusHigh'])"), 

        self.assertEqual(str(net._realizeAscending('g#2', 3, maxPitch='e4')), "([G#2, A2, B2, C#3, D#3, E3, F#3, G#3, A3, B3, C#4, D#4, E4], [1, 2, 3, 4, 5, 'terminusHigh', 0, 1, 2, 3, 4, 5, 'terminusHigh'])"), 



    def testBasicB(self):
        
        edgeList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        net = IntervalNetwork()
        net.fillBiDirectedEdges(edgeList)

        self.assertEqual(str(net.realize('g4')), "([G4, A4, B4, C5, D5, E5, F#5, G5], ['terminusLow', 0, 1, 2, 3, 4, 5, 'terminusHigh'])")
        #self.assertEqual(str(net.realizePitch('g4')), '[G4, A4, B4, C5, D5, E5, F#5, G5]')

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1: # normal conditions
        music21.mainTest(Test)
    elif len(sys.argv) > 1:
        t = Test()
        #t.testGraphedOutput()
        t.testBasicA()
        #t.testScaleModel()
        #t.testHarmonyModel()
        #t.testDirectedA()
        #t.testScaleArbitrary()
        #t.testRealizeDescending()
        t.testBasicB()


# melodic/harmonic minor
# abstracted in scale class
# non uni-directional scale

#------------------------------------------------------------------------------
# eof


