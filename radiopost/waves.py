from collections import Counter
import json
from pathlib import Path
import sys
import sqlite3
import time

from pippi import dsp, fx, shapes
from . import SR, DEFAULT_SEED, DB, getsnd, stretch
from . import recipes as RS

def makewaves(name, seed=12345):
    dsp.seed(seed)

    waves = []
    rocks = []

    db = sqlite3.connect('renders/%s/%s-info.db' % (name, seed))
    db.row_factory = sqlite3.Row
    c = db.cursor()

    q = 'SELECT * FROM segments WHERE flatness < 0.01'
    c.execute(q)

    segments = c.fetchall()

    for segment in segments:
        segment = dict(segment)
        if segment['flatness'] == 0 or segment['freq'] == 0:
            continue

        segment['speed'] = 1
        while segment['freq'] * segment['speed'] > 1000:
            segment['speed'] /= 2

        waves += [ segment ]

    for segment in segments:
        if segment['length'] == 0 or segment['freq'] > 0 or segment['length'] < (5*SR):
            continue

        rocks += [ segment ]

    if len(rocks) == 0:
        rocks = [ dict(s) for s in segments ]

    waves_used = Counter()
    usable_waves = []

    while len(usable_waves) < 50:
        usable_waves += [ dsp.choice(waves) ]

    with open('renders/%s/%s-waves.log' % (name, seed), 'w') as iw:
        count = 0
        for w in usable_waves:
            snd = getsnd(w).speed(w['speed'])
            snd = fx.hpf(snd, 60)

            length = dsp.rand(snd.dur, snd.dur * 10)

            snd = stretch(snd, length)

            snd = fx.norm(snd, 1)
            filename = 'renders/%s/waves/sources-%s-%s.wav' % (name, seed, count)
            snd.write(filename)

            r = dsp.choice(rocks)
            rock = getsnd(r)
            rock = fx.hpf(rock, 60)

            rock = stretch(rock, length)

            rock = fx.norm(rock, 1)
            filename = 'renders/%s/waves/rocks-%s-%s.wav' % (name, seed, count)
            rock.write(filename)

            filename = 'renders/%s/waves/waves-%s-%s.wav' % (name, seed, count)
            info = '%s, %s, %s, %s, %s, %s' % (filename, length, w['freq'], w['speed'], w['source'], r['source'])

            snd = snd.convolve(rock)

            snd.write(filename)
            iw.write(info+'\n')

            count += 1

def basswaves(name, seed=12345):
    dsp.seed(seed)
    waves = dsp.read('renders/%s/stems/%s-mixedwaves.wav' % (name, seed))
    length = waves.dur
    out = dsp.buffer(length=length)

    octaves = [1] + [ 2**dsp.randint(1,6) for _ in range(4) ]

    for i, octave in enumerate(octaves):
        env = dsp.win('hannout').skewed(0.01) 
        env = env * env * dsp.win('hannout')
        env.graph('renders/%s/graphs/%s-%s-bassenv.png' % (name, seed, i))

        grid = dsp.win(shapes.win('hann', length=3), 0.1, 15)
        grid.graph('renders/%s/graphs/%s-%s-bassgrid.png' % (name, seed, i))

        amps = dsp.win(shapes.win('hann', length=8), 0, 1)
        amps.graph('renders/%s/graphs/%s-%s-bassamps.png' % (name, seed, i))

        lens = dsp.win(shapes.win('hann', length=10), 0.1, 15)
        lens.graph('renders/%s/graphs/%s-%s-basslens.png' % (name, seed, i))

        pan = shapes.win('sine', length=0.2)
        pan.graph('renders/%s/graphs/%s-%s-basspan.png' % (name, seed, i))

        pos = 0
        while pos < length:
            if dsp.rand() > 0.8:
                pos += grid.interp(pos/length)
                continue

            lowf = dsp.rand(500, 1000)
            higf = lowf + dsp.rand(50, 80)

            nlength = lens.interp(pos/length)
            chunk = waves.rcut(nlength).env(env).taper(dsp.MS*8)
            chunk = fx.hpf(chunk, lowf)
            chunk = fx.lpf(chunk, higf)
            speed = dsp.choice([0.5, 0.25])
            chunk = chunk.speed(speed)
            chunk = fx.lpf(chunk, lowf * speed)
            if dsp.rand() > 0.75:
                chunk = chunk.speed(1.5)

            chunk *= amps.interp(pos/length)

            out.dub(chunk.speed(octave).pan(pan.interp(pos/length)), pos)
            #pos += dsp.rand(chunk.dur/4, chunk.dur)
            #print('bass', i, 'of', len(octaves), octave, length, pos)
            pos += grid.interp(pos/length)

    out = fx.norm(out, 1)

    out.write('renders/%s/stems/%s-basswaves.wav' % (name, seed))

def mixwaves(TLEN, name, seed=12345):
    """ Filter and stack a number of waves, staggered over time
    """
    # pick frequency bands
    dsp.seed(seed)
    out = dsp.buffer()

    waves = [ dsp.read(p) for p in Path('renders/%s/waves' % name).glob('waves-%s-*.wav' % seed) ]

    #for octave in octaves:
    pos = 0
    while pos < TLEN:
        for _ in range(dsp.randint(2, 4)):
            lowband = dsp.rand(50, 200)
            midband = (dsp.rand(200, 800), dsp.rand(1000, 5000))
            higband = dsp.rand(5000, 10000)

            lowwave = dsp.choice(waves)
            lowwave = fx.lpf(lowwave, lowband).pad(dsp.rand(0, 20))
            if dsp.rand() > 0.5:
                lowwave = lowwave * dsp.win(shapes.win('sine', length=dsp.rand(0.1, 0.5)), dsp.rand(0, 0.5), 1)

            midwave = dsp.choice(waves)
            midwave = fx.lpf(midwave, midband[0])
            midwave = fx.hpf(midwave, midband[1]).pad(dsp.rand(0, 20))
            if dsp.rand() > 0.5:
                midwave = midwave * dsp.win(shapes.win('sine', length=dsp.rand(0.1, 0.5)), dsp.rand(0, 0.5), 1)

            higwave = dsp.choice(waves)
            higwave = fx.hpf(higwave, higband).pad(dsp.rand(0, 20))
            if dsp.rand() > 0.5:
                higwave = higwave * dsp.win(shapes.win('sine', length=dsp.rand(0.1, 0.5)), dsp.rand(0, 0.5), 1)

            out.dub(lowwave, pos)
            out.dub(midwave, pos)
            out.dub(higwave, pos)

        pos += dsp.rand(0, 20)

    out = fx.norm(out, 1)

    out.write('renders/%s/stems/%s-mixedwaves.wav' % (name, seed))

def combinewaves(name, seed=12345):
    db = DB(name, seed)
    bits = dsp.read('renders/%s/stems/%s-particles.wav' % (name, seed))
    tone = dsp.read('renders/%s/stems/%s-mixedwaves.wav' % (name, seed))
    bass = dsp.read('renders/%s/stems/%s-basswaves.wav' % (name, seed))

    swell = tone.cut(0, bits.dur).env(bits.toenv())
    out = dsp.mix([swell, bits])

    tonefull = tone * shapes.win(dsp.win('hann').skewed(0.1), length=dsp.rand(0.5, 3))
    out.dub(tonefull)

    bassfull = bass * shapes.win(dsp.win('hann').skewed(0.1), length=dsp.rand(1, 3))
    out.dub(bassfull)

    inserts = ([RS.sparkgauze]*5) + [RS.stutterinsert] + ([RS.altinsert] * 4)
    #numinserts = dsp.randint(20, 500)
    numinserts = dsp.randint(10, 15)

    for _ in range(numinserts):
        insert = dsp.choice(inserts)(bits, tone, bass, db)
        pos = dsp.rand(0, out.dur-insert.dur)
        out.dub(insert, pos)

    replacements = ([RS.sparkreplace] *5) + [RS.stutterreplace, RS.altreplace]
    #numreplacements = dsp.randint(2, 150)
    numreplacements = dsp.randint(5, 15)

    for _ in range(numreplacements):
        out = dsp.choice(replacements)(out, bits, tone, bass, db)

    out *= 10
    out = fx.compressor(out, -10, 10)
    out = fx.norm(out, 1)
    out.write('renders/%s/%s-combined.wav' % (name, seed))

if __name__ == '__main__':
    seed = DEFAULT_SEED
    if len(sys.argv) > 2:
        seed = int(sys.argv[2])

    if sys.argv[1] == 'make':
        makewaves(seed)
    elif sys.argv[1] == 'mix':
        mixwaves(seed)
    elif sys.argv[1] == 'bass':
        basswaves(seed)
    elif sys.argv[1] == 'combine':
        combinewaves(seed)

