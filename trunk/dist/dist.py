#-------------------------------------------------------------------------------
# Name:          dist.py
# Purpose:       Distribution and uploading script
#
# Authors:       Christopher Ariza
#
# Copyright:     (c) 2010-2011 Christopher Ariza
# License:       GPL
#-------------------------------------------------------------------------------

import os, sys, tarfile

from music21 import base
from music21 import common

from music21 import environment
_MOD = 'dist.py'
environLocal = environment.Environment(_MOD)


'''
Build and upload music21 in three formats: egg, exe, and tar.

Simply call from the command line.
'''

PY = 'python2.7'

class Distributor(object):
    def __init__(self):
        self.fpEgg = None
        self.fpWin = None
        self.fpTar = None
        self.version = base.VERSION_STR

        self._initPaths()

    def _initPaths(self):

        # must be in the dist dir
        dir = os.getcwd()
        parentDir = os.path.dirname(dir)
        parentContents = os.listdir(parentDir)
        # make sure we are in the the proper directory
        if (not dir.endswith("dist") or 
            'music21' not in parentContents):
            raise Exception("not in the music21%dist directory: %s" % (os.sep, dir))
    
        self.fpDistDir = dir
        self.fpPackageDir = parentDir # dir with setup.py
        self.fpBuildDir = os.path.join(self.fpPackageDir, 'build')
        self.fpEggInfo = os.path.join(self.fpPackageDir, 'music21.egg-info')

        for fp in [self.fpDistDir, self.fpPackageDir, self.fpBuildDir]:
            environLocal.warn(fp)


    def _updatePaths(self):
        '''Process output of build scripts. Get most recently produced distributions.
        '''
        contents = os.listdir(self.fpDistDir)
        for fn in contents:
            fp = os.path.join(self.fpDistDir, fn)
            if self.version in fn and fn.endswith('.egg'):
                self.fpEgg = fp
            elif self.version in fn and fn.endswith('.exe'):
                fpNew = fp.replace('.macosx-10.6-intel.exe', '.exe')
                os.rename(fp, fpNew)
                self.fpWin = fpNew
            elif self.version in fn and fn.endswith('.tar.gz'):
                self.fpTar = fp

        for fn in [self.fpEgg, self.fpWin, self.fpTar]:
            if fn == None:
                environLocal.warn('missing fn path')
            else:
                environLocal.warn(fn)


    def build(self):
        '''Build all distributions. Update and rename file paths if necessary; remove extract build produts.
        '''
        # call setup.py
        os.system('cd %s; %s setup.py bdist_egg' % (self.fpPackageDir, PY))
        os.system('cd %s; %s setup.py bdist_wininst' % 
                    (self.fpPackageDir, PY))
        os.system('cd %s; %s setup.py sdist' % 
                    (self.fpPackageDir, PY))

        #os.system('cd %s; python setup.py sdist' % self.fpPackageDir)
        self._updatePaths()

        # remove build dir, egg-info dir
        environLocal.warn('removing %s' % self.fpEggInfo)
        os.system('rm -r %s' % self.fpEggInfo)
        environLocal.warn('removing %s' % self.fpBuildDir)
        os.system('rm -r %s' % self.fpBuildDir)




    def _uploadPyPi(self):
        '''Upload source package to PyPI
        '''
        os.system('cd %s; %s setup.py bdist_egg upload' % 
                (self.fpPackageDir, PY))

    def _uploadGoogleCode(self, fp):
        '''Upload distributions to Google code. Requires googlecode_upload.py script from: 
        http://code.google.com/p/support/source/browse/trunk/scripts/googlecode_upload.py
        '''
        import googlecode_upload # placed in site-packages

        summary = self.version
        project = 'music21'
        user = 'christopher.ariza'

        if fp.endswith('.tar.gz'):
            labels = ['OpSys-All', 'Featured', 'Type-Archive']
        elif fp.endswith('.exe'):
            labels = ['OpSys-Windows', 'Featured', 'Type-Installer']
        elif fp.endswith('.egg'):
            labels = ['OpSys-All', 'Featured', 'Type-Archive']
        
        print(['starting GoogleCode upload of:', fp])
        status, reason, url = googlecode_upload.upload_find_auth(fp, 
                        project, summary, labels, user)
        print([status, reason])


    def upload(self):
        '''Perform all uploads.
        '''
        self._uploadPyPi()
        for fp in [self.fpTar, self.fpEgg, self.fpWin]:
            self._uploadGoogleCode(fp)




def removeCorpusTar(fp=None):
    '''Remove the corpus from the tar.gz file.

    NOTE: this function works only with Posix systems. 
    '''
    if fp is None:
        fp = '/Volumes/xdisc/_sync/_x/src/music21/dist/music21-0.6.3.b3.tar.gz'

    TAR = 'TAR'
    EGG = 'EGG'
    if fp.endswith('.tar.gz'):
        mode = TAR
        modeExt = '.tar.gz'
    elif fp.endswith('.egg'):
        mode = EGG
        modeExt = '.egg'
    else:
        raise Exception('incorrect source file path')

    fpDir, fn = os.path.split(fp)

    # this has .tar.gz extension
    fnDst = fn.replace('music21', 'music21-noCorpus')
    fpDst = os.path.join(fpDir, fnDst)
    # remove file extnesions
    fnDstDir = fnDst.replace(modeExt, '')
    fpDstDir = os.path.join(fpDir, fnDstDir)
    
    # get the name of the dir after decompression
    fpSrcDir = os.path.join(fpDir, fn.replace(modeExt, ''))
        
    if mode == TAR:
        tf = tarfile.open(fp, "r:gz")
        # the path here is the dir into which to expand, 
        # not the name of that dir
        tf.extractall(path=fpDir)
    elif mode == EGG:
        pass

    # remove old dir if ti exists
    if os.path.exists(fpDst):
        # can use shutil.rmtree
        os.system('rm -r %s' % fpDst)
    if os.path.exists(fpDstDir):
        # can use shutil.rmtree
        os.system('rm -r %s' % fpDstDir)


    os.system('mv %s %s' % (fpSrcDir, fpDstDir))
    # remove files, updates manifest
    for fn in common.getCorpusContentDirs():
        fp = os.path.join(fpDstDir, 'music21', 'corpus', fn)
        os.system('rm -r %s' % fp)
    # adjust the sources Txt file
    sourcesTxt = os.path.join(fpDstDir, 'music21.egg-info', 'SOURCES.txt')
    # files will look like 'music21/corpus/haydn' in SOURCES.txt
    post = []
    f = open(sourcesTxt, 'r')
    corpusContentDirs = common.getCorpusContentDirs()
    for l in f:
        match = False
        if 'corpus' in l:
            for fn in corpusContentDirs:
                # these are relative paths
                fp = os.path.join('music21', 'corpus', fn)
                if l.startswith(fp):
                    match = True
                    break
        if not match: 
            post.append(l)
    f.close()
    f = open(sourcesTxt, 'w')
    f.writelines(post)
    f.close()


    if mode == TAR:
        # compress dst dir to dst file path name
        # need the -C flag to set relative dir
        # just name of dir
        cmd = 'tar -C %s -czf %s %s/' % (fpDir, fpDst, fnDstDir) 
        os.system(cmd)
    elif mode == EGG:
        # zip and name with egg
        pass

    # remove directory that was compressed
    if os.path.exists(fpDstDir):
        # can use shutil.rmtree
        os.system('rm -r %s' % fpDstDir)


    


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    #d = Distributor()
    #d.build()
    #d.upload()


    #removeCorpusTar()
    




