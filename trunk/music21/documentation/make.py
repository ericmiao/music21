#! /usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         documentation/make.py
# Purpose:      music21 documentation script, v. 2.0
#
# Authors:      Josiah Wolf Oberholtzer
#
# Copyright:    Copyright © 2013 Michael Scott Cuthbert and the music21 Project
# License:      LGPL, see license.txt
#-------------------------------------------------------------------------------


import os
import shutil
import sys
import webbrowser

try:
    import sphinx
except ImportError:
    raise ImportError("Sphinx is required to build documentation; download from http://sphinx-doc.org")


def _print_usage():
    usage = '''\
m21 Documentation build script:

    documentation$ python ./make.py [TARGET]

Currently supported targets include:

    html:     build HTML documentation
    latex:    build LaTeX sources
    pdflatex: build PDF from LaTeX source
    clean:    remove autogenerated files
    help:     print this message
'''

    print usage 


def _main(target):
    from music21 import documentation # @UnresolvedImport
    from music21 import common
    documentationDirectoryPath = documentation.__path__[0]
    sourceDirectoryPath = os.path.join(
        documentationDirectoryPath,
        'source',
        )
    buildDirectoryPath = os.path.join(
        documentationDirectoryPath,
        'build',
        )
    doctreesDirectoryPath = os.path.join(
        buildDirectoryPath,
        'doctrees',
        )
    buildDirectories = {
        'html': os.path.join(
            buildDirectoryPath,
            'html',
            ),
        'latex': os.path.join(
            buildDirectoryPath,
            'latex',
            ),
        'latexpdf': os.path.join(
            buildDirectoryPath,
            'latex',
            ),
    }
    if target in buildDirectories:
        print 'WRITING DOCUMENTATION FILES'
        documentation.ModuleReferenceReSTWriter()()
        documentation.CorpusReferenceReSTWriter()()
        documentation.IPythonNotebookReSTWriter()()
        sphinxOptions = ['sphinx']
        sphinxOptions.extend(('-b', target))
        sphinxOptions.extend(('-d', doctreesDirectoryPath))
        sphinxOptions.append(sourceDirectoryPath)
        sphinxOptions.append(buildDirectories[target])
        # sphinx.main() returns 0 on success, 1 on failure.
        # If the docs fail to build, we should not try to open a web browser.
        if sphinx.main(sphinxOptions):
            return
        if target == 'html':
            launchPath = os.path.join(
                buildDirectories[target],
                'index.html',
                )
            # TODO: Test launching web browsers under Windows.
            if launchPath.startswith('/'):
                launchPath = 'file://' + launchPath
            webbrowser.open(launchPath)
    elif target == 'clean':
        print 'CLEANING AUTOGENERATED DOCUMENTATION'
        documentation.CorpusReferenceCleaner()()
        documentation.ModuleReferenceCleaner()()
        documentation.IPythonNotebookCleaner()()
        for name in os.listdir(buildDirectoryPath):
            if name.startswith('.'):
                continue
            path = os.path.join(
                buildDirectoryPath,
                name,
                )
            shutil.rmtree(path)
            print '\tCLEANED {0}'.format(common.relativepath(path))
    elif target == 'help':
        _print_usage()
    else:
        print 'Unsupported documentation target {!r}'.format(target)
        print
        _print_usage()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1]   # to rebuild everything run "make.py clean"
    else:
        target = 'html'
    _main(target)
