# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------------
# Name:         lookup.py
# Purpose:      music21 class which contains lookup tables between print and braille
# Authors:      Jose Cabal-Ugaz
#
# Copyright:    (c) 2011 The music21 Project
# License:      LGPL
#-----------------------------------------------------------------------------------

c = {'128th':   u'\u2819',
     '64th':    u'\u2839',
     '32nd':    u'\u281d',
     '16th':    u'\u283d',
     'eighth':  u'\u2819',
     'quarter': u'\u2839',
     'half':    u'\u281d',
     'whole':   u'\u283d',
     'breve':   u'\u283d\u2818\u2809\u283d'}

d = {'128th':   u'\u2811',
     '64th':    u'\u2831',
     '32nd':    u'\u2815',
     '16th':    u'\u2835',
     'eighth':  u'\u2811',
     'quarter': u'\u2831',
     'half':    u'\u2815',
     'whole':   u'\u2835',
     'breve':   u'\u2835\u2818\u2809\u2835'}

e = {'128th':   u'\u280b',
     '64th':    u'\u282b',
     '32nd':    u'\u280f',
     '16th':    u'\u282f',
     'eighth':  u'\u280b',
     'quarter': u'\u282b',
     'half':    u'\u280f',
     'whole':   u'\u282f',
     'breve':   u'\u282f\u2818\u2809\u282f'}

f = {'128th':   u'\u281b',
     '64th':    u'\u283b',
     '32nd':    u'\u281f',
     '16th':    u'\u283f',
     'eighth':  u'\u281b',
     'quarter': u'\u283b',
     'half':    u'\u281f',
     'whole':   u'\u283f',
     'breve':   u'\u283f\u2818\u2809\u283f'}

g = {'128th':   u'\u2813',
     '64th':    u'\u2833',
     '32nd':    u'\u2817',
     '16th':    u'\u2837',
     'eighth':  u'\u2813',
     'quarter': u'\u2833',
     'half':    u'\u2817',
     'whole':   u'\u2837',
     'breve':   u'\u2837\u2818\u2809\u2837'}

a = {'128th':   u'\u280a',
     '64th':    u'\u282a',
     '32nd':    u'\u280e',
     '16th':    u'\u282e',
     'eighth':  u'\u280a',
     'quarter': u'\u282a',
     'half':    u'\u280e',
     'whole':   u'\u282e',
     'breve':   u'\u282e\u2818\u2809\u282e'}

b = {'128th':   u'\u281a',
     '64th':    u'\u283a',
     '32nd':    u'\u281e',
     '16th':    u'\u283e',
     'eighth':  u'\u281a',
     'quarter': u'\u283a',
     'half':    u'\u281e',
     'whole':   u'\u283e',
     'breve':   u'\u283e\u2818\u2809\u283e'}

pitchNameToNotes = {'C': c,
                    'D': d,
                    'E': e,
                    'F': f,
                    'G': g,
                    'A': a,
                    'B': b}

octaves = {0: u'\u2808\u2808',
           1: u'\u2808',
           2: u'\u2818',
           3: u'\u2838',
           4: u'\u2810',
           5: u'\u2828',
           6: u'\u2830',
           7: u'\u2820',
           8: u'\u2820\u2820'}

accidentals = {'sharp':          u'\u2829',
               'double-sharp':   u'\u2829\u2829',
               'flat':           u'\u2823',
               'double-flat':    u'\u2823\u2823',
               'natural':        u'\u2821'}

intervals = {2: u'\u280c',
             3: u'\u282c',
             4: u'\u283c',
             5: u'\u2814',
             6: u'\u2834',
             7: u'\u2812',
             8: u'\u2824'}

keySignatures = {-7:    u'\u283c\u281b\u2823',
                 -6:    u'\u283c\u280b\u2823',
                 -5:    u'\u283c\u2811\u2823',
                 -4:    u'\u283c\u2819\u2823',
                 -3:    u'\u2823\u2823\u2823',
                 -2:    u'\u2823\u2823',
                 -1:    u'\u2823',
                 0:     u'',
                 1:     u'\u2829',
                 2:     u'\u2829\u2829',
                 3:     u'\u2829\u2829\u2829',
                 4:     u'\u283c\u2819\u2829',
                 5:     u'\u283c\u2811\u2829',
                 6:     u'\u283c\u280b\u2829',
                 7:     u'\u283c\u281b\u2829'}

naturals = {0: u'',
            1: u'\u2821',
            2: u'\u2821\u2821',
            3: u'\u2821\u2821\u2821',
            4: u'\u283c\u2819\u2821',
            5: u'\u283c\u2811\u2821',
            6: u'\u283c\u280b\u2821',
            7: u'\u283c\u281b\u2821'}

numbers = {0: u'\u281a',
           1: u'\u2801',
           2: u'\u2803',
           3: u'\u2809',
           4: u'\u2819',
           5: u'\u2811',
           6: u'\u280b',
           7: u'\u281b',
           8: u'\u2813',
           9: u'\u280a'}

beatUnits = {2: u'\u2806',
             4: u'\u2832',
             8: u'\u2826'}

rests = {'dummy':   u'\u2804',
         '128th':   u'\u282d',
         '64th':    u'\u2827',
         '32nd':    u'\u2825',
         '16th':    u'\u280d',
         'eighth':  u'\u282d',
         'quarter': u'\u2827',
         'half':    u'\u2825',
         'whole':   u'\u280d',
         'breve':   u'\u280d\u2818\u2809\u280d'}

barlines = {'final': u'\u2823\u2805',
            'double': u'\u2823\u2805\u2804'}

fingerMarks = {'1': u'\u2801',
               '2': u'\u2803',
               '3': u'\u2807',
               '4': u'\u2802',
               '5': u'\u2805'}

clefSigns = {'treble': u'\u281c\u280c\u2807',
             'bass': u'\u281c\u283c\u2807',
             'alto': u'\u281c\u282c\u2807',
             'tenor': u'\u281c\u282c\u2810\u2807'}

bowingSymbols = {}

beforeNoteExpr = {'staccato': u'\u2826',
                  'accent': u'\u2828\u2826',
                  'tenuto': u'\u2838\u2826',
                  'staccatissimo': u'\u2820\u2826'}

textExpressions = {'crescendo': u'\u281c\u2809\u2817\u2804',
                   'cresc.': u'\u281c\u2809\u2817\u2804',
                   'cr.': u'\u281c\u2809\u2817\u2804',
                   'decrescendo': u'\u281c\u2819\u2811\u2809\u2817\u2804',
                   'decresc.': u'\u281c\u2819\u2811\u2809\u2817\u2804',
                   'decr.': u'\u281c\u2819\u2811\u2809\u2817\u2804'}

alphabet = {'a': u'\u2801',
            'b': u'\u2803',
            'c': u'\u2809',
            'd': u'\u2819',
            'e': u'\u2811',
            'f': u'\u280b',
            'g': u'\u281b',
            'h': u'\u2813',
            'i': u'\u280a',
            'j': u'\u281a',
            'k': u'\u2805',
            'l': u'\u2807',
            'm': u'\u280d',
            'n': u'\u281d',
            'o': u'\u2815',
            'p': u'\u280f',
            'q': u'\u281f',
            'r': u'\u2817',
            's': u'\u280e',
            't': u'\u281e',
            'u': u'\u2825',
            'v': u'\u2827',
            'w': u'\u283a',
            'x': u'\u282d',
            'y': u'\u283d',
            'z': u'\u2835',
            '!': u'\u2816',
            '\'': u'\u2804',
            ',': u'\u2802',
            '-': u'\u2834',
            '.': u'\u2832',
            '?': u'\u2826',
            '(': u'\u2836',
            ')': u'\u2836'}

symbols = {'space': u'\u2800',
           'double_space': u'\u2800\u2800',
           'number': u'\u283c',
           'dot': u'\u2804',
           'tie': u'\u2808\u2809',
           'uppercase': u'\u2820',
           'metronome': u'\u2836',
           'common': u'\u2828\u2809',
           'cut': u'\u2838\u2809',
           'music_hyphen': u'\u2810',
           'music_asterisk': u'\u281c\u2822\u2814',
           'rh_keyboard': u'\u2805\u281c',
           'lh_keyboard': u'\u2807\u281c',
           'word': u'\u281c',
           'triplet': u'\u2806',
           'finger_change': u'\u2809',
           'first_set_missing_fingermark': u'\u2820',
           'second_set_missing_fingermark': u'\u2804',
           'opening_single_slur': u'\u2809',
           'opening_double_slur': u'\u2809\u2809',
           'closing_double_slur': u'\u2809',
           'opening_bracket_slur': u'\u2830\u2803',
           'closing_bracket_slur': u'\u2818\u2806',
           'basic_exception': u'\u281c\u2826',
           'full_inaccord': u'\u2823\u281c'}

ascii_chars = {u'\u2800': ' ',
               u'\u2801': 'A',
               u'\u2802': '1',
               u'\u2803': 'B',
               u'\u2804': '\'',
               u'\u2805': 'K',
               u'\u2806': '2',
               u'\u2807': 'L',
               u'\u2808': '@',
               u'\u2809': 'C',
               u'\u280a': 'I',
               u'\u280b': 'F',
               u'\u280c': '/',
               u'\u280d': 'M',
               u'\u280e': 'S',
               u'\u280f': 'P',
               u'\u2810': '"',
               u'\u2811': 'E',
               u'\u2812': '3',
               u'\u2813': 'H',
               u'\u2814': '9',
               u'\u2815': 'O',
               u'\u2816': '6',
               u'\u2817': 'R',
               u'\u2818': '^',
               u'\u2819': 'D',
               u'\u281a': 'J',
               u'\u281b': 'G',
               u'\u281c': '>',
               u'\u281d': 'N',
               u'\u281e': 'T',
               u'\u281f': 'Q',
               u'\u2820': ',',     
               u'\u2821': '*',
               u'\u2822': '5',
               u'\u2823': '<',
               u'\u2824': '-',
               u'\u2825': 'U',
               u'\u2826': '8',
               u'\u2827': 'V',
               u'\u2828': '.',
               u'\u2829': '%',
               u'\u282a': '[',
               u'\u282b': '$',
               u'\u282c': '+',
               u'\u282d': 'X',
               u'\u282e': '!',
               u'\u282f': '&',
               u'\u2830': ';',     
               u'\u2831': ':',
               u'\u2832': '4',
               u'\u2833': '\\',
               u'\u2834': '0',
               u'\u2835': 'Z',
               u'\u2836': '7',
               u'\u2837': '(',
               u'\u2838': '_',
               u'\u2839': '?',
               u'\u283a': 'W',
               u'\u283b': ']',
               u'\u283c': '#',
               u'\u283d': 'Y',
               u'\u283e': ')',
               u'\u283f': '='}

binary_dots = {u'\u2800': ('00','00','00'),
               u'\u2801': ('10','00','00'),
               u'\u2802': ('00','10','00'),
               u'\u2803': ('10','10','00'),
               u'\u2804': ('00','00','10'),
               u'\u2805': ('10','00','10'),
               u'\u2806': ('00','10','10'),
               u'\u2807': ('10','10','10'),
               u'\u2808': ('01','00','00'),
               u'\u2809': ('11','00','00'),
               u'\u280a': ('01','10','00'),
               u'\u280b': ('11','10','00'),
               u'\u280c': ('01','00','10'),
               u'\u280d': ('11','00','10'),
               u'\u280e': ('01','10','10'),
               u'\u280f': ('11','10','10'),
               u'\u2810': ('00','01','00'),
               u'\u2811': ('10','01','00'),
               u'\u2812': ('00','11','00'),
               u'\u2813': ('10','11','00'),
               u'\u2814': ('00','01','10'),
               u'\u2815': ('10','01','10'),
               u'\u2816': ('00','11','10'),
               u'\u2817': ('10','11','10'),
               u'\u2818': ('01','01','00'),
               u'\u2819': ('11','01','00'),
               u'\u281a': ('01','11','00'),
               u'\u281b': ('11','11','00'),
               u'\u281c': ('01','01','10'),
               u'\u281d': ('11','01','10'),
               u'\u281e': ('01','11','10'),
               u'\u281f': ('11','11','10'),
               u'\u2820': ('00','00','01'),    
               u'\u2821': ('10','00','01'),
               u'\u2822': ('00','10','01'),
               u'\u2823': ('10','10','01'),
               u'\u2824': ('00','00','11'),
               u'\u2825': ('10','00','11'),
               u'\u2826': ('00','10','11'),
               u'\u2827': ('10','10','11'),
               u'\u2828': ('01','00','01'),
               u'\u2829': ('11','00','01'),
               u'\u282a': ('01','10','01'),
               u'\u282b': ('11','10','01'),
               u'\u282c': ('01','00','11'),
               u'\u282d': ('11','00','11'),
               u'\u282e': ('01','10','11'),
               u'\u282f': ('11','10','11'),
               u'\u2830': ('00','01','01'),     
               u'\u2831': ('10','01','01'),
               u'\u2832': ('00','11','01'),
               u'\u2833': ('10','11','01'),
               u'\u2834': ('00','01','11'),
               u'\u2835': ('10','01','11'),
               u'\u2836': ('00','11','11'),
               u'\u2837': ('01','11','11'),
               u'\u2838': ('01','01','01'),
               u'\u2839': ('11','01','01'),
               u'\u283a': ('01','11','01'),
               u'\u283b': ('11','11','01'),
               u'\u283c': ('01','01','11'),
               u'\u283d': ('11','01','11'),
               u'\u283e': ('01','11','11'),
               u'\u283f': ('11','11','11')}

#------------------------------------------------------------------------------
# eof