import contextlib
from collections import defaultdict
import json
import os
from pathlib import Path
import random
import sys
import sqlite3

import aubio
import librosa
import numpy as np
from mutagen.flac import FLAC
from pippi import dsp, fx

from . import waves
from . import synth
from . import TLEN

WINSIZE = 4096
HOPSIZE = WINSIZE//2
SR = 44100


class Segment:
    source = ''
    start = 0
    length = 0
    freq = 0
    centroid = 0
    contrast = 0
    peak = 0
    bandwidth = 0
    flatness = 0
    rolloff = 0

    def __init__(self, source, start):
        self.source = str(source)
        self.start = start
        
def flatten(snd):
    return np.asarray(snd.remix(1).frames, dtype='f').flatten()

def getpitch(snd, tolerance=0.8):
    o = aubio.pitch('yin', WINSIZE, HOPSIZE, SR)
    o.set_tolerance(tolerance)

    pitches = []

    pos = 0
    while True:
        chunk = snd[pos:pos+HOPSIZE]
        if len(chunk) < HOPSIZE:
            break

        est = o(chunk)[0]
        con = o.get_confidence()

        pos += HOPSIZE
        if con < tolerance:
            continue

        pitches += [ est ]

    if len(pitches) == 0:
        return None

    return sum(pitches) / len(pitches)

def divide(recs, seed=12345):
    segments = []

    for rec in recs:
        print('Segmenting', rec)
        o = aubio.onset('specflux', WINSIZE, HOPSIZE, SR)

        snd = dsp.read(rec)
        snd = fx.hpf(snd, 200)
        snd = fx.lpf(snd, 12000)

        read_pos = 0
        total_length = len(snd)
        last_grain = None

        while read_pos < total_length - HOPSIZE:
            frames = flatten(snd[read_pos:read_pos+HOPSIZE])

            if o(frames):
                pos = o.get_last()
                grain = Segment(rec, pos)

                if last_grain is not None:
                    last_grain.length = pos - last_grain.start
                    chunk = snd[last_grain.start:last_grain.start+last_grain.length]
                    last_frames = np.asarray(chunk.remix(1).frames, dtype='f').flatten()

                    last_grain.bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=last_frames, sr=SR, n_fft=WINSIZE)))
                    last_grain.flatness = float(np.mean(librosa.feature.spectral_flatness(y=last_frames, n_fft=WINSIZE)))
                    last_grain.rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=last_frames, sr=SR, n_fft=WINSIZE)))
                    last_grain.centroid = float(np.mean(librosa.feature.spectral_centroid(y=last_frames, sr=SR, n_fft=WINSIZE)))
                    last_grain.contrast = float(np.mean(librosa.feature.spectral_contrast(y=last_frames, sr=SR, n_fft=WINSIZE)))
                    last_grain.peak = float(np.max(np.abs(last_frames)))
                    last_grain.freq = getpitch(last_frames) or 0

                segments += [ grain ]
                last_grain = grain

            read_pos += HOPSIZE

    dbpath = '%s-info.db' % seed

    with contextlib.suppress(FileNotFoundError):
        os.remove(dbpath)

    db = sqlite3.connect(dbpath)
    c = db.cursor()

    fields = []
    for k,v in Segment.__dict__.items():
        if "__" not in k and k != 'source':
            fields += [ str(k) ]

    qt = "CREATE TABLE segments (source text, %s)" % ', '.join([ '%s numeric' % f for f in fields])
    qv = "INSERT INTO segments VALUES (:source, %s)" % ', '.join([ ':%s' % f for f in fields])
    c.execute(qt)

    rows = []
    for seg in segments:
        vals = defaultdict(lambda: None, seg.__dict__)
        rows += [ vals ]

    c.executemany(qv, rows)

    db.commit()
    db.close()

    return segments

def choose(path, seed=12345):
    dsp.seed(seed)

    longrecs = []
    shortrecs = []

    for r in Path(path).glob('*.flac'):
        f = FLAC(r)
        if f.info.length <= 60 * 5:
            shortrecs += [ r ]
        else:
            longrecs += [ r ]
    
    shortchoices = []
    longchoices = []

    if len(shortrecs) < 4:
        shortchoices = shortrecs

    else:
        while len(shortchoices) < 4:
            choice = dsp.choice(shortrecs)
            if choice not in shortchoices:
                shortchoices += [ choice ]

    while len(longchoices) < 2:
        choice = dsp.choice(longrecs)
        if choice not in longchoices:
            longchoices += [ choice ]

    return shortchoices + longchoices


if __name__ == '__main__':
    try:
        flacs = sys.argv[1]
        seed = int(sys.argv[2])

        #choices = choose(flacs, seed)
        choices = [ str(p) for p in Path(sys.argv[1]).glob('*.flac') ]
        print('Choices:', choices)

        segments = divide(choices, seed)
    except IndexError:
        print('Usage: python -m radiopost.segments <path-to-flacs> <seed>')

    print('makeparticles')
    synth.makeparticles(seed)
    print('makewaves')
    waves.makewaves(seed)
    print('mixwaves')
    waves.mixwaves(seed)
    print('basswaves')
    waves.basswaves(seed)
    print('combine')
    waves.combinewaves(seed)
    print('DONE!')

