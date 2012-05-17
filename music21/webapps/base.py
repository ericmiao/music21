# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         webapps.base.py
# Purpose:      music21 functions for implementing web interfaces
#
# Authors:      Lars Johnson
#
# Copyright:    (c) 2012 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------
'''
Webapps is a module designed for using music21 with a webserver.

This file includes the classes and functions used to parse and process requests to music21 running on a server.

For information about how to set up a server to use music21, look at the files in webapps.server
For examples of application-specific commands and templates, see webapps.apps
For details about various output template options available, see webapps.templates

**Overview of Processing a Request**

1.  The GET and POST data from the request are combined into an agenda object
    The POST data can in the formats 'application/json', 'multipart/form-data' or 'application/x-www-form-urlencoded'
    For more information, see the documentation for Agenda and makeAgendaFromRequest

2.  If an appName is specified, additional data and commands are added to the agenda
    For more information, see the applicationInitializers in apps.py

3.  A CommandProcessor is created for the agenda

4.  The processor parses its dataDict into primitives or music21 objects and saves them to a parsedDataDict
    For more information, see commandProcessor._parseData()

5.  The processor executes its commandList, modifying its internal parsedDataDict
    For more information, see commandProcessor.executeCommands()

6.  If outputTemplate is specified, the processor uses a template to generate and output.
    For more information, see commandProcessor.getOutput() and the templates in templates.py

7.  Otherwise, the data will be returned as JSON, where the variables in the agenda's returnList specify which
    variables to include in the returned JSON.
    
9.  If an error occurs, an error message will be returned to the user 

**Full JSON Example:**

Below is an example of a complete JSON request:
{
    "dataDict": {
        "myNum": {
            "fmt": "int", 
            "data": "23"
        }
    }, 
    "returnDict": {
        "myNum": "int", 
        "ho": "int"
    }, 
    "commandList": [
        {
            "function": "corpus.parse", 
            "argList": [
                "'bwv7.7'"
            ], 
            "resultVariable": "sc"
        }, 
        {
            "function": "transpose", 
            "argList": [
                "'p5'"
            ], 
            "caller": "sc", 
            "resultVariable": "sc"
        }, 
        {
            "attribute": "flat", 
            "caller": "sc", 
            "resultVariable": "scFlat"
        }, 
        {
            "attribute": "highestOffset", 
            "caller": "scFlat", 
            "resultVariable": "ho"
        }
    ]
}
'''

import unittest
import doctest

# music21 imports
import music21
from music21 import common
from music21 import converter
from music21 import stream
from music21 import corpus
from music21 import note
from music21 import features
from music21 import harmony
from music21 import clef
from music21 import tempo
from music21.demos.theoryAnalysis import theoryAnalyzer

# webapps imports
import commands
import templates
import apps

# python library imports
import json
import zipfile
import cgi
import urlparse
import re
import sys
import traceback

import StringIO

#-------------------------------------------------------------------------------

# Valid format types for data input to the server
availableDataFormats = ['xml',
                        'musicxml',
                        'abc',
                        'str',
                        'string',
                        'bool',
                        'boolean'
                        'int',
                        'reprtext',
                        'list',
                        'int',
                        'float']

# Commands of type function (no caller) must be in this list
availableFunctions = ['', # A blank string symbolizes no operation, the commandElement will be ignored rather than failing.
                      'checkLeadSheetPitches',
                      'colorAllChords',
                      'colorAllNotes',
                      'colorResults',
                      'commands.reduction',
                      'commands.runPerceivedDissonanceAnalysis',
                      'commands.generateIntervals',
                      'converter.parse',
                      'corpus.parse',
                      'createMensuralCanon',
                      'getResultsString',
                      'generateChords',
                      'reduction',
                      'stream.transpose',
                      'tempo.MetronomeMark',
                      'theoryAnalyzer.identifyHiddenFifths',
                      'theoryAnalyzer.identifyHiddenOctaves',
                      'theoryAnalyzer.identifyParallelFifths',
                      'theoryAnalyzer.identifyParallelOctaves',
                      'writeMIDIFileToServer',
                      
                      '__getitem__',
                      'augmentOrDiminish',
                      'insert',
                      'measures',
                      'transpose'
                      ] 

# Commands of type method (have a caller) must be in this list
availableMethods = ['__getitem__',
                    'augmentOrDiminish',
                    'insert',
                    'measures'
                    'transpose',
                    ]

# Commands of type attribute must be in this list
availableAttribtues = ['highestOffset',
                       'flat',
                       '_theoryScore',
                       'musicxml']

# Commands of type attribute must be in this list
availableOutputTemplates = ['templates.noteflightEmbed',
                            'templates.musicxmlText',
                            'templates.musicxmlFile',
                            'templates.vexflow',
                            'templates.braille']

#-------------------------------------------------------------------------------

def ModWSGIApplication(environ, start_response):
    '''
    Application function in proper format for a mod_wsgi Application:
    Reads the contents of a post request, and passes the data string to
    webapps.processDataString for further processing. 
        
    For an example of how to install this application on a server see webapps.server.wsgiapp.py
    
    The request to the application should have the following structures:

    >>> environ = {}              # environ is usually created by the server. Manually constructing dictionary for demonstrated
    >>> wsgiInput = StringIO.StringIO()    # wsgi.input is usually a buffer containing the contents of a POST request. Using StringIO to demonstrate
    >>> wsgiInput.write('{"dataDict":{"a":{"data":3}},"returnDict":{"a":"int"}}')
    >>> wsgiInput.seek(0)
    >>> environ['wsgi.input'] = wsgiInput
    >>> environ['QUERY_STRING'] = ""
    >>> environ['DOCUMENT_ROOT'] = "/Library/WebServer/Documents"
    >>> environ['HTTP_HOST'] = "ciconia.mit.edu"
    >>> environ['SCRIPT_NAME'] = "/music21/unifiedinterface"
    >>> environ['CONTENT_TYPE'] = "application/json"
    >>> start_response = lambda status, headers: None         # usually called by mod_wsgi server. Used to initiate response
    >>> ModWSGIApplication(environ, start_response)
    ['{"status": "success", "dataDict": {"a": {"fmt": "int", "data": "3"}}, "errorList": []}']
    '''
    # This additional environment information is needed primarily in the context of writing files to a
    # to a file on the server or including links back to the server in returned HTML templates    
    documentRoot = environ['DOCUMENT_ROOT']     # Path to ducment root     e.g. /Library/WebServer/Documents
    hostName = environ['HTTP_HOST']             # Host name                e.g. ciconia.mit.edu
    scriptName = environ['SCRIPT_NAME']         # Mount point on server    e.g. /music21/unifiedinterface
    serverConfigInfo = {"DOCUMENT_ROOT":documentRoot,
                        "HTTP_HOST":hostName,
                        "SCRIPT_NAME":scriptName}
    
    requestFormat = str(environ.get("CONTENT_TYPE")).split(';')[0]

    # Get content of request: is in a file-like object that will need to be .read() to get content
    requestInput = environ['wsgi.input']
    try:        
        agenda = makeAgendaFromRequest(requestInput,environ,requestFormat)
        processor = CommandProcessor(agenda)
        processor.executeCommands()
        (responseData, responseContentType) = processor.getOutput()
        #(responseData, responseContentType) = (str(debug), 'text/plain')
        
    # Handle any unexpected exceptions
    # TODO: Change output based on environment variables...
    except Exception as e:
        errorData = 'music21_server_error:\n'
        errorData += traceback.format_exc()
        sys.stderr.write(errorData)
        (responseData, responseContentType) = (errorData, 'text/plain')

    start_response('200 OK', [('Content-type', responseContentType),
                              ('Content-Length', str(len(responseData)))])

    return [responseData]

#-------------------------------------------------------------------------------

def makeAgendaFromRequest(requestInput, environ, requestFormat = None):
    '''
    Takes in a file-like requestInput (has .read()) containing form/multipart data
    and a dictionary-like serverConfigInfo, containing at a minimum keys QUERY
    Combines information from form fields and server info into an agenda object
    that can be used with the CommandProcessor.
    
    Note that variables specified via query string will always be returned as a list,
    regardless of how many times the variable is specified.
    
    >>> requestInput = StringIO.StringIO() # requestInput should be buffer from the server application. Using StringIO for demonstration
    >>> requestInput.write('{"dataDict":{"a":{"data":3}}}')
    >>> requestInput.seek(0)
    
    >>> environ = {"QUERY_STRING":"b=3", "DOCUMENT_ROOT": "/Library/WebServer/Documents", "HTTP_HOST": "ciconia.mit.edu", "SCRIPT_NAME": "/music21/unifiedinterface"}
    >>> agenda = makeAgendaFromRequest(requestInput, environ, 'application/json')
    >>> agenda
    {'dataDict': {u'a': {u'data': 3}, 'b': {'data': '3'}}, 'returnDict': {}, 'commandList': []}
   
    >>> environ2 = {"QUERY_STRING":"a=2&b=3&b=4","DOCUMENT_ROOT": "/Library/WebServer/Documents", "HTTP_HOST": "ciconia.mit.edu", "SCRIPT_NAME": "/music21/unifiedinterface"}
    >>> agenda2 = makeAgendaFromRequest(requestInput, environ2, 'multipart/form-data')
    >>> agenda2
    {'dataDict': {'a': {'data': '2'}, 'b': {'data': ['3', '4']}}, 'returnDict': {}, 'commandList': []}

    '''
    agenda = Agenda()
    
    combinedFormFields = {}
    
    # Determine the correct format of the input. Combine the post and get data into combinedFormFields dictionary.
    if requestFormat == 'application/json':
        agenda.loadJson(requestInput.read())
    elif requestFormat == 'multipart/form-data':
        postFormFields = cgi.FieldStorage(requestInput, environ = environ)  
        for key in postFormFields:
            value = postFormFields.getlist(key)
            if len(value) == 1:
                value = value[0]
            combinedFormFields[key] = value
        
    # Add GET fields:
    getFormFields = urlparse.parse_qs(environ['QUERY_STRING']) # Parse GET request in URL to dict
    for (key,value) in getFormFields.iteritems():
        if len(value) == 1:
            value = value[0]
        combinedFormFields[key] = value
           
    # Load json as first priority if it is set
    if 'json' in combinedFormFields:
        agenda.loadJson(combinedFormFields['json'])
    
    # These keys will not go into dataDataDict
    reservedKeys = ['json','appName','dataDict','commandList','returnDict','appName','outputTemplate','outputArgList','uploadedFile']

    # Add remaining form fields as variables in dataDict. Will replace duplicates with new value
    for k in combinedFormFields:
        if k not in reservedKeys:
            agenda['dataDict'][k] = {"data": combinedFormFields[k]}

    # Process uploaded file
    if 'uploadedFile' in combinedFormFields:
        result = processFileUpload(combinedFormFields['uploadedFile'])
        if result is not None:
            agenda['uploadedFile'] = result
 
    # For other reserved keys, load the value into the topmost level of the agenda
    if 'appName' in combinedFormFields:
        agenda['appName'] = combinedFormFields['appName']     
    if 'outputTemplate' in combinedFormFields:
        agenda['outputTemplate'] = combinedFormFields['outputTemplate']  
    if 'outputArgList' in combinedFormFields:
        agenda['outputArgList'] = combinedFormFields['outputArgList']
    
    # Allows the appName to direct final processing
    if 'appName' in agenda:
        setupApplication(agenda)
    
    return agenda

def processFileUpload(fileData):
    '''
    Converts the file upload Data from a multipart/form-data into a StringIO
    object that will behave like a file (has .read() etc.)
    '''
    fileObject = StringIO.StringIO(fileData)
    return fileObject

def setupApplication(agenda, appName = None):
    if appName == None:
        if 'appName' in agenda:
            appName = agenda['appName']
        else:
            raise Exception("appName is None and no appName key in agenda.")
    
    if appName not in apps.applicationInitializers.keys():
        raise Exception ("Unknown appName: " + appName)
    
    # Run initializer on agenda - edits it in place.
    apps.applicationInitializers[appName](agenda)

#-------------------------------------------------------------------------------

class Agenda(dict):
    '''
    Subclass of dictionary that represents data and commands to be processed by a CommandProcessor.
    
    The Agenda contains the following keys:
    
    **'dataDict'** whose value is a dictionary specifying data to be inputted to the processor of the form:
        "dataDict" : {"<VARIABLE_1_NAME>": {"data": "<VARIABLE_1_DATA>",
                                            "fmt":  "<VARIABLE_1_FMT>"},
                      "<VARIABLE_2_NAME>": {"data": "<VARIABLE_2_DATA>",
                                            "fmt":  "<VARIABLE_2_FMT>"},
                      etc.
                      }
        where the variable formats are elements of availableDataFormats ("str","int","musicxml", etc.)
    
    **'commandList'**  whose value is a list specifying commands to be executed by the processor of the form::
        "commandList" : [{"type":       "<CMD_1_TYPE>",
                          "resultVar":  "<CMD_1_RESULT_VARIABLE>",
                          "caller":     "<CMD_1_CALLER>",
                          "command":    "<CMD_1_COMMAND_NAME>",
                          "argList":    ['<CMD_1_ARG_1>','<CMD_1_ARG_2>'...]},
                          
                          {"type":      "<CMD_2_TYPE>",
                          "resultVar":  "<CMD_2_RESULT_VARIABLE>",
                          "caller":     "<CMD_2_CALLER>",
                          "command":    "<CMD_2_COMMAND_NAME>",
                          "argList":    ['<CMD_2_ARG_1>','<CMD_2_ARG_2>'...]},
                          etc.
                          ]
        Calling .executeCommands() iterates through the commandList sequentially, calling the equivalent of:
        <CMD_n_RESULT_VARAIBLE> = <CMD_n_CALLER>.<CMD_n_COMMAND_NAME>(<CMD_n_ARG_1>,<CMD_n_ARG_2>...)
        
        where the command TYPE is "function", "method", or "attribute"
    
    **'returnList'** whose value is a list specifying the variables to be returned from the server.
        "returnList" : ["<VARIABLE_1_NAME>","<VARIABLE_2_NAME>", etc.]
        
        returnList is used to limit JSON output to only the relevant variables. If returnList is not specified,
        the entire set of variables in the processor's environment will be returned in string format.
        
    **'outputTemplate'**  which specifies the return template to be used
    **'outputArgList'**   which specifies what arguments to pass the return template
    
    '''
    def __init__(self):
        '''
        Initializes core key values 'dataDict', 'commandList', 'returnDict'
        >>> agenda = Agenda()
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': []}
        '''
        self['dataDict'] = dict()
        self['commandList'] = list()
        self['returnDict'] = dict()
        dict.__init__(self)
        
    def __setitem__(self, key, value):
        '''
        Raises an error if one attempts to set 'dataDict', 'returnDict', or 'commandList'
        to values that are not of the corresponding dict/list type.
        >>> agenda = Agenda()
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': []}
        >>> agenda['dataDict'] = {"a":{"data":2}}
        >>> agenda
        {'dataDict': {'a': {'data': 2}}, 'returnDict': {}, 'commandList': []}
        
        '''
        if key in ['dataDict','returnDict'] and type(value) is not dict:
            raise Exception('value for key: '+ str(key) + ' must be dict')
            return
        
        elif key in ['commandList'] and type(value) is not list:
            raise Exception('value for key: '+ str(key) + ' must be list')
            return
        
        dict.__setitem__(self,key,value)
    
    def addData(self, variableName, data, fmt = None):
        '''
        Given a variable name, data, and optionally format, constructs the proper dataDictElement structure,
        and adds it to the dataDict of the agenda.
        
        >>> agenda = Agenda()
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': []}
        >>> agenda.addData('a', 2)
        >>> agenda
        {'dataDict': {'a': {'data': 2}}, 'returnDict': {}, 'commandList': []}
        >>> agenda.addData(variableName='b', data=[1,2,3], fmt='list')
        >>> agenda
        {'dataDict': {'a': {'data': 2}, 'b': {'fmt': 'list', 'data': [1, 2, 3]}}, 'returnDict': {}, 'commandList': []}
        
        '''
        dataDictElement = {}
        dataDictElement['data'] = data
        if fmt != None:
            dataDictElement['fmt'] = fmt
        self['dataDict'][variableName] = dataDictElement
        
    def getData(self, variableName):
        '''
        Given a variable name, returns the data stored in the agenda for that variable name. If no data is stored,
        returns the value None.        
        >>> agenda = Agenda()
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': []}
        >>> agenda.getData('a') == None
        True
        >>> agenda.addData('a', 2)
        >>> agenda.getData('a')
        2
        '''
        if variableName in self['dataDict'].keys():
            return self['dataDict'][variableName]['data']
        else:
            return None
        
    def addCommand(self, type, resultVar, caller, command, argList = None):
        '''
        Adds the specified command to the commandList of the agenda. type is either "function" or "attribute". 
        resultVar, caller, and command are strings that will result in the form shown below. Set an argument as 
        none to 
        argList should be a list of data encoded in an appropriate format (see parseStringToPrimitive for more information)
        
        <resultVar> = <caller>.<command>(<argList>)
        
        >>> agenda = Agenda()
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': []}
        >>> agenda.addCommand('function','sc','sc','transpose',['p5'])
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': [{'function': 'transpose', 'argList': ['p5'], 'caller': 'sc', 'resultVariable': 'sc'}]}
        >>> agenda.addCommand('attribute','scFlat','sc','flat')
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': [{'function': 'transpose', 'argList': ['p5'], 'caller': 'sc', 'resultVariable': 'sc'}, {'attribute': 'flat', 'caller': 'sc', 'resultVariable': 'scFlat'}]}
        
        '''
        commandListElement = {}
        commandListElement[type] = command
        if resultVar != None:
            commandListElement['resultVariable'] = resultVar
        if caller != None:
            commandListElement['caller'] = caller
        if argList != None:
            commandListElement['argList'] = argList
            
        self['commandList'].append(commandListElement)
        
    def setOutputTemplate(self, outputTemplate, outputArgList):
        '''
        Specifies the output template that will be used for the agenda.
        
        >>> agenda = Agenda()
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': []}
        >>> agenda.setOutputTemplate('templates.noteflightEmbed',['sc'])
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'outputArgList': ['sc'], 'commandList': [], 'outputTemplate': 'templates.noteflightEmbed'}
        '''
        self['outputTemplate'] = outputTemplate
        self['outputArgList'] = outputArgList
    
    def loadJson(self, jsonRequestStr):
        '''
        Runs json.loads on jsonRequestStr and loads the resulting structure into the agenda object.
        
        >>> agenda = Agenda()
        >>> agenda
        {'dataDict': {}, 'returnDict': {}, 'commandList': []}
        >>> agenda.loadJson(sampleJsonStringSimple)
        >>> agenda
        {'dataDict': {u'myNum': {u'fmt': u'int', u'data': u'23'}}, 'returnDict': {u'myNum': u'int'}, 'commandList': []}

        '''
        tempDict = json.loads(jsonRequestStr)
        for (key, value) in tempDict.iteritems():
            if isinstance(key, unicode):
                key = str(key)
            if isinstance(value, unicode):
                value = str(value)
            self[key] = value

        
#-------------------------------------------------------------------------------

class CommandProcessor(object):
    '''
    Processes server request for music21.
    
    Takes an Agenda (dict) as input, containing the keys:
    'dataDict'
    'commandList'
    'returnDict'
    'outputTemplate'
    'outputArgList'

    '''
    def __init__(self,agenda):
        '''
        Given an agenda 
        '''
        self.agenda = agenda
        self.rawDataDict = {}
        self.parsedDataDict = {}
        self.commandList = []
        self.errorList = []
        self.returnDict = {}
        self.outputTemplate = ""
        self.outputArgList = []
        
        if "dataDict" in agenda.keys():
            self.rawDataDict = agenda['dataDict']
            self._parseData()
        
        if "commandList" in agenda.keys():
            self.commandList = agenda['commandList']
        
        if "returnDict" in agenda.keys():
            self.returnDict = agenda['returnDict']

        if "outputTemplate" in agenda.keys():
            self.outputTemplate = agenda['outputTemplate']

        if "outputArgList" in agenda.keys():
            self.outputArgList = agenda['outputArgList']
      
    def recordError(self, errorString, exceptionObj = None):
        '''
        Adds an error to the internal errorList array and prints the whole error to stderr
        so both the user and the administrator know. Error string represents a brief, human-readable
        message decribing the error.
        
        Errors are appended to the errorList as a tuple (errorString,errorTraceback) where errorTraceback
        is the traceback of the exception if exceptionObj is specified, otherwise errorTraceback is the empty string
        '''
        errorTraceback = ''    
        if exceptionObj is not None:
            errorTraceback += traceback.format_exc()
        
        sys.stderr.write(errorString)
        sys.stderr.write(errorTraceback)
        self.errorList.append(('music21_server_error: '+errorString,errorTraceback))


    def _parseData(self):
        '''
        Parses data specified as strings in self.dataDict into objects in self.parsedDataDict
        '''
        for (name,dataDictElement) in self.rawDataDict.iteritems():
            if 'data' not in dataDictElement.keys():
                self.recordError("no data specified for data element "+unicode(dataDictElement))
                continue

            dataStr = dataDictElement['data']

            if 'fmt' in dataDictElement.keys():
                fmt = dataDictElement['fmt']
                
                if name in self.parsedDataDict.keys():
                    self.recordError("duplicate definition for data named "+str(name)+" "+str(dataDictElement))
                    continue
                if fmt not in availableDataFormats:
                    self.recordError("invalid data format for data element "+str(dataDictElement))
                    continue
                
                if fmt == 'string' or fmt == 'str':
                    if dataStr.count("'") == 2: # Single Quoted String
                        data = dataStr.replace("'","") # remove excess quotes
                    elif dataStr.count("\"") == 2: # Double Quoted String
                        data = dataStr.replace("\"","") # remove excess quotes
                    else:
                        self.recordError("invalid string (not in quotes...) for data element "+str(dataDictElement))
                        continue
                elif fmt == 'int':
                    try:
                        data = int(dataStr)
                    except:
                        self.recordError("invalid integer for data element "+str(dataDictElement))
                        continue
                elif fmt in ['bool','boolean']:
                    if dataStr in ['true','True']:
                        data = True
                    elif dataStr in ['false','False']:
                        data = False
                    else:
                        self.recordError("invalid boolean for data element "+str(dataDictElement))
                        continue
                elif fmt == 'list':
                    # in this case dataStr should actually be an list object.
                    if not common.isListLike(dataStr):
                        self.recordError("list format must actually be a list structure "+str(dataDictElement))
                        continue
                    data = []
                    for elementStr in dataStr:
                        if common.isStr(elementStr):
                            dataElement = self.parseStringToPrimitive(elementStr)
                        else:
                            dataElement = elementStr
                        data.append(dataElement)
                else:
                    if fmt in ['xml','musicxml']:                
                        if dataStr.find("<!DOCTYPE") == -1:
                            dataStr = """<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 1.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">""" + dataStr
                        if dataStr.find("<?xml") == -1:
                            dataStr = """<?xml version="1.0" encoding="UTF-8"?>""" + dataStr
                    try:
                        data = converter.parseData(dataStr)
                    except converter.ConverterException as e:
                        #self.recordError("Error parsing data variable "+name+": "+str(e)+"\n\n"+dataStr)
                        self.recordError("Error parsing data variable "+name+": "+unicode(e)+"\n\n"+dataStr,e)
                        continue
            else: # No format specified
                dataStr = str(dataStr)
                data = self.parseStringToPrimitive(dataStr)
                
                
            self.parsedDataDict[name] = data
                
            
    def executeCommands(self):
        '''
        Parses JSON Commands specified in the self.commandList
        
        In the JSON, commands are described by::

            {"commandList:"[
                {"function":"corpus.parse",
                 "argList":["'bwv7.7'"],
                 "resultVariable":"sc"},
                 
                {"function":"transpose",
                 "caller":"sc",
                 "argList":["'p5'"],
                 "resultVariable":"sc"},
                 
                
                {"attribute":"flat",
                 "caller":"sc",
                 "resultVariable":"scFlat"},
                 
                {"attribute":"higestOffset",
                 "caller":"scFlat",
                 "resultVariable":"ho"}
                 ]
            }

        '''
        
        for commandElement in self.commandList:
            if 'function' in commandElement.keys() and 'attribute'  in commandElement.keys():
                self.recordError("cannot specify both function and attribute for:  "+str(commandElement))
                continue
            
            if 'function' in commandElement.keys():
                functionName = commandElement['function']
                
                if functionName in self.parsedDataDict.keys():
                    functionName = self.parsedDataDict[functionName]
                if functionName == '':
                    if 'caller' in commandElement.keys() and  'resultVariable' in commandElement.keys():
                        callerName = commandElement['caller']
                        resultVarName = commandElement['resultVariable']
                        self.parsedDataDict[resultVarName]
                    continue
                elif functionName not in availableFunctions:
                    self.recordError("unknown function "+str(functionName)+" :"+str(commandElement))
                    continue
                
                if 'argList' not in commandElement.keys():
                    argList = []
                else:
                    argList = commandElement['argList']
                    for (i,arg) in enumerate(argList):
                        parsedArg = self.parseStringToPrimitive(arg)
                        argList[i] = parsedArg

                if 'caller' in commandElement.keys(): # Caller Specified
                    callerName = commandElement['caller']
                    if callerName not in self.parsedDataDict.keys():
                        self.recordError(callerName+" not defined "+str(commandElement))
                        continue
                    try:
                        result = eval("self.parsedDataDict[callerName]."+functionName+"(*argList)")
                    except Exception as e:
                        self.recordError("Error: "+str(e)+" executing function "+str(functionName)+" :"+str(commandElement))
                        continue
                    
                    
                else: # No caller specified
                    result = eval(functionName)(*argList)
                
                if 'resultVariable' in commandElement.keys():
                    resultVarName = commandElement['resultVariable']
                    self.parsedDataDict[resultVarName] = result
                    
            elif 'attribute' in commandElement.keys():
                attribtueName = commandElement['attribute']
                
                if attribtueName not in availableAttribtues:
                    self.recordError("unknown attribute "+str(attribtueName)+" :"+str(commandElement))
                    continue
                
                if 'args'  in commandElement.keys():
                    self.recordError("No args should be specified with attribute :"+str(commandElement))
                    continue
                
                if 'caller' in commandElement.keys(): # Caller Specified
                    callerName = commandElement['caller']
                    if callerName not in self.parsedDataDict.keys():
                        self.recordError(callerName+" not defined "+str(commandElement))
                        continue
                    result = eval("self.parsedDataDict[callerName]."+attribtueName)
                    
                else: # No caller specified
                    self.recordError("Caller must be specified with attribute :"+str(commandElement))
                    continue

                if 'resultVariable' in commandElement.keys():
                    resultVarName = commandElement['resultVariable']
                    self.parsedDataDict[resultVarName] = result
                    
            else:
                self.recordError("must specify function or attribute for:  "+str(commandElement))
                continue
            
    def getResultObject(self):
        '''
        Returns a new object ready for json parsing with the string values of the objects
        specified in self.returnDict in the formats specified in self.returnDict::
        
            "returnDict":{
                "myNum" : "int",
                "ho"    : "int"
            }
        '''
        return_obj = {};
        return_obj['status'] = "success"
        return_obj['dataDict'] = {}
        return_obj['errorList'] = []
        
        if len(self.errorList) > 0:
            return_obj['status'] = "error"
            return_obj['errorList'] = self.errorList
            return return_obj
        
        for (dataName,fmt) in self.returnDict.iteritems():
            if dataName not in self.parsedDataDict.keys():
                self.recordError("Data element "+dataName+" not defined at time of return");
                continue
            if fmt not in availableDataFormats:
                self.recordError("Format "+fmt+" not available");
                continue
            
            data = self.parsedDataDict[dataName]
            
            if fmt == 'string' or fmt == 'str':
                dataStr = str(data)
            elif fmt == 'musicxml':
                dataStr = data.musicxml
            elif fmt == 'reprtext':
                dataStr = data._reprText()
            else:
                dataStr = str(data)
                
            return_obj['dataDict'][dataName] = {"fmt":fmt, "data":dataStr}
            
        
        if len(self.errorList) > 0:
            return_obj['status'] = "error"
            return_obj['errorList'] = self.errorList
            return return_obj
        
        return return_obj
    
    def getErrorStr(self):
        '''
        Converts self.errorList into a string
        '''
        errorStr = ""
        for e in self.errorList:
            errorStr += e + "\n"
        return errorStr
    
    def parseStringToPrimitive(self, strVal):
        '''
        Determines what format a given string is in and returns a value in that format..
        First checks if it is the name of a variable defined in the parsedDataDict or the
        name of an allowable function. In either of these cases, it will return the actual value
        of the data or the actual function.
        
        Next, it will check if the string is an int, float, boolean, or none, returning the appropriate value.
        If it is a quoted string then it will remove the quotes on the ends and return it as a string.
        If no type can be determined, raises an exception
        
        >>> agenda = Agenda()
        >>> agenda.addData("a",2)
        >>> agenda.addData("b",[1,2,3],"list")
        >>> processor = CommandProcessor(agenda)
        >>> processor.parseStringToPrimitive("a")
        2
        >>> processor.parseStringToPrimitive("b")
        [1, 2, 3]
        >>> processor.parseStringToPrimitive("1.0")
        1.0
        >>> processor.parseStringToPrimitive("2")
        2
        >>> processor.parseStringToPrimitive("True")
        True
        >>> processor.parseStringToPrimitive("False")
        False
        >>> processor.parseStringToPrimitive("None") == None
        True
        >>> processor.parseStringToPrimitive("'hi'")
        'hi'
        >>> processor.parseStringToPrimitive("'Madam I\'m Adam'")
        "Madam I'm Adam"
        '''
        returnVal = None
        
        strVal = strVal.strip() # removes whitespace on ends
        
        if strVal in self.parsedDataDict.keys(): # Used to specify data via variable name
            returnVal = self.parsedDataDict[strVal]
        elif strVal in availableFunctions: # Used to specify function via variable name
            returnVal = strVal
        else:
            try:
                returnVal = int(strVal)
            except:
                try:
                    returnVal = float(strVal)
                except:
                    if strVal == "True":
                        returnVal = True
                        
                    elif strVal == "None":
                        returnVal = None
                        
                    elif strVal == "False":
                        returnVal = False
                        
                    elif strVal[0] == '"' and strVal[-1] == '"': # Double Quoted String
                        returnVal = strVal[1:-1] # remove quotes
                        
                    elif strVal[0] == "'" and strVal[-1] == "'": # Single Quoted String
                        returnVal = strVal[1:-1] # remove quotes
                        
                    else: 
                        returnVal = cgi.escape(str(strVal))
        return returnVal
    
    def getOutput(self):
        '''
        Generates the output of the processor. Uses the attributes outputTemplate and outputArgList from the agenda
        to determine which format the output should be in. If an outputTemplate is unspecified or known,
        will return json by default.
        
        Return is of the tyle (output, outputType) where outputType is a content-type ready for returning to the server:
        "text/plain", "application/json", "text/html", etc.
        '''
        if self.outputTemplate == "":
            output =  json.dumps(self.getResultObject())
            outputType = 'text/plain'
            
        elif self.outputTemplate not in availableOutputTemplates:
            self.recordError("Unknown output template "+str(self.outputTemplate))
            output =  json.dumps(self.getResultObject(),indent=4)
            outputType = 'text/plain'
            
        else:
            argList = self.outputArgList
            for (i,arg) in enumerate(argList):
                parsedArg = self.parseStringToPrimitive(arg)
                argList[i] = parsedArg             
            (output, outputType) = eval(self.outputTemplate)(*argList)
        return (output, outputType)
#-------------------------------------------------------------------------------
# Tests 
#-------------------------------------------------------------------------------


sampleFormDataSimple = '------WebKitFormBoundarytO99C5T6SZEHKAIb\r\nContent-Disposition: form-data; name="a"\r\n\r\n7\r\n------WebKitFormBoundarytO99C5T6SZEHKAIb\r\nContent-Disposition: form-data; name="b"\r\n\r\n8\r\n------WebKitFormBoundarytO99C5T6SZEHKAIb\r\nContent-Disposition: form-data; name="json"\r\n\r\n{"dataDict":{"c":{"data":7}},\r\n        "returnDict":{"a":"int"}\r\n        }\r\n------WebKitFormBoundarytO99C5T6SZEHKAIb--\r\n'

sampleJsonStringSimple = r'''
    {
    "dataDict": {
        "myNum":
            {"fmt" : "int",
             "data" : "23"}
             },
    "returnDict":{
        "myNum" : "int"}
    }'''

        
sampleJsonString = r'''
        {
    "dataDict": {
        "myNum":
            {"fmt" : "int",
             "data" : "23"}
    },
    "commandList":[
        {"function":"corpus.parse",
         "argList":["'bwv7.7'"],
         "resultVariable":"sc"},
         
        {"function":"transpose",
         "caller":"sc",
         "argList":["'p5'"],
         "resultVariable":"sc"},
         
    
        {"attribute":"flat",
         "caller":"sc",
         "resultVariable":"scFlat"},
         
        {"attribute":"highestOffset",
         "caller":"scFlat",
         "resultVariable":"ho"}
    ],
    "returnDict":{
        "myNum" : "int",
        "ho"    : "int"
        }
    }'''

class Test(unittest.TestCase):
    
    def runTest(self):
        pass
    
    def testAgenda(self):
        jsonString = r'''
        {
    "dataDict": {
        "myNum":
            {"fmt" : "int",
             "data" : "23"}
    },
    "commandList":[
        {"function":"corpus.parse",
         "argList":["'bwv7.7'"],
         "resultVariable":"sc"},
         
        {"function":"transpose",
         "caller":"sc",
         "argList":["'p5'"],
         "resultVariable":"sc"},
         
    
        {"attribute":"flat",
         "caller":"sc",
         "resultVariable":"scFlat"},
         
        {"attribute":"highestOffset",
         "caller":"scFlat",
         "resultVariable":"ho"}
    ],
    "returnDict":{
        "myNum" : "int",
        "ho"    : "int"
        }
    }
    '''
        ad = Agenda()
        ad.loadJson(jsonString)
        self.assertEqual(ad['dataDict']['myNum']['data'], "23")

if __name__ == '__main__':
    music21.mainTest(Test)
        