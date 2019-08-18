import json
import sys
import sqlite3

from pippi import dsp, fx, shapes
from . import TLEN, SR, DB, getsnd, stretch

def save_long_sounds():
    out = dsp.buffer()
    with open('segments.json', 'r') as j:
        segments = json.loads(j.read())

        pos = 0
        for segment in segments:
            if segment['length'] is None or segment['length'] < (2*SR):
                continue

            print('%s - %s - Contrast: %s, Freq: %s' % (segment['source'], pos, segment['contrast'], segment['freq']))
            snd = getsnd(segment)
            out.dub(snd, pos)
            pos += snd.dur + 1

    out.write('long_sounds.flac')

def save_low_contrast_sounds():
    out = dsp.buffer()
    with open('segments.json', 'r') as j:
        segments = json.loads(j.read())

        pos = 0
        for segment in segments:
            if segment['contrast'] is None or segment['contrast'] > 16:
                continue

            print('%s - %s - Contrast: %s, Freq: %s' % (segment['source'], pos, segment['contrast'], segment['freq']))
            snd = getsnd(segment)
            out.dub(snd, pos)
            pos += snd.dur + 1

    out.write('low_contrast_sounds.flac')

def save_low_flatness_sounds():
    out = dsp.buffer()
    with open('segments.json', 'r') as j:
        segments = json.loads(j.read())

        pos = 0
        for segment in segments:
            if segment['flatness'] is None or segment['flatness'] > 0.01 or segment['freq'] is None:
                continue

            print('%s - %s - Flatness: %s, Freq: %s' % (segment['source'], pos, segment['flatness'], segment['freq']))
            snd = getsnd(segment)
            out.dub(snd, pos)
            pos += snd.dur + 1

    out.write('low_flatness_sounds.flac')

def makecurve(segment):
    snd = getsnd(segment)
    return snd.toenv()

def makeparticles(seed=12345):
    dsp.seed(seed)

    #length = TLEN * 0.6
    #TLEN = 60

    #db = sqlite3.connect('%s-info.db' % seed)
    #db.row_factory = sqlite3.Row
    #c = db.cursor()

    #q = 'SELECT * FROM segments WHERE flatness < 0.01'
    #c.execute(q)

    #segments = c.fetchall()

    out = dsp.buffer(length=TLEN)

    numphrases = dsp.randint(1, max(2, int(TLEN * 0.05)))
    maxphrase = TLEN / numphrases
    minphrase = maxphrase / 4

    phrases = []
    for _ in range(numphrases):
        phrases += [ dsp.rand(minphrase, maxphrase) ]

    lenphrases = sum(phrases)
    lensilences = TLEN - lenphrases

    phraseidxs = []
    while len(phraseidxs) < numphrases:
        idx = dsp.randint(0, numphrases-1)
        if idx not in phraseidxs:
            phraseidxs += [ idx ]

    pos = 0
    unusedsilence = lensilences

    print('PHRASES', lenphrases, 'SILENCES', lensilences)

    params = []
    for li in phraseidxs:
        length = phrases[li]
        params += [ (seed, li, length, pos) ]

        if unusedsilence > 0:
            s = dsp.rand(0, min(unusedsilence, maxphrase))
            unusedsilence -= s
            pos += s

        pos += length

    outputs = dsp.pool(makephrase, params=params, processes=8)
    for pos, phrase in outputs:
        print('DUB', pos, phrase.dur)
        out.dub(phrase, pos)

    out *= 2
    out = fx.compressor(out, -5, 5)
    out = fx.norm(out, 1)

    out.write('%s-particles.wav' % seed)


def makephrase(seed, li, length, dpos):
    db = DB(seed)
    segments = db.noisy()

    dsp.seed(seed+li)

    print('MAKEPHRASE', length, seed, li, dpos)
    out = dsp.buffer(length=length)

    rcurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))
    lcurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))
    acurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))
    fwcurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))
    fmcurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))

    for _ in range(3):
        layer = dsp.buffer(length=length)
        pan = shapes.win('sine', length=0.2)

        #rhythmcurve = makecurve(dsp.choice(segments)).skewed(0.9)
        stablecurve = shapes.win('sine')
        rhythmcurve = shapes.win('sine', length=20, stability=stablecurve) * rcurvemod
        rhythmcurve.graph('%s-rhythmcurve.png' % seed)

        lengthcurve = shapes.win('sine', length=10) * lcurvemod
        lengthcurve.graph('%s-lengthcurve.png' % seed)
        lengthcurve = dsp.win(lengthcurve, dsp.MS*1, dsp.rand(0.02, length/2))

        elapsed = 0
        pos = 0

        maxlength = dsp.rand(dsp.MS*10, length/dsp.randint(2, 10))
        minlength = dsp.MS*0.1

        onsets = []
        while elapsed < length:
            pos = elapsed / length
            o = abs(rhythmcurve.interp(pos)) * (maxlength-minlength) + minlength
            onsets += [ o + elapsed ]
            elapsed += o

        acurve = shapes.win('hann', length=10) * acurvemod
        acurve.graph('%s-ampcurve.png' % seed)

        fwidth = shapes.win('hann', length=4, stability=shapes.win('sine')) * fwcurvemod
        fwidth.graph('%s-freqwidth.png' % seed)
        fwidth = dsp.win(fwidth, 0.001, 0.5)

        fmin = shapes.win('hann', length=4, stability=shapes.win('sine')) * fmcurvemod
        fmin.graph('%s-freqmin.png' % seed)
        fmin = dsp.win(fmin, 0.5, 1)

        p = None
        for i, onset in enumerate(onsets):
            pos = i / len(onsets)

            if p is None or dsp.rand() > 0.96:
                segment = segments[int(acurve.interp(pos) * (len(segments)-1))]
                p = getsnd(segment)

            l = lengthcurve.interp(pos)
            p = p.rcut(min(l, p.dur))

            if dsp.rand() > 0.5:
                p = p.env(shapes.win('sine', length=dsp.rand(0.01, 2)))

            p = p.taper(dsp.MS*10).env('rsaw')

            if p.dur < l:
                p = stretch(p, l)

            if dsp.rand() > 0.5:
                fm = fmin.interp(pos)
                fw = fwidth.interp(pos)
                p = p.vspeed(dsp.win(shapes.win('sine'), fm, fm+fw))

            layer.dub(p, onset)

        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 200, 20000)
        layer = fx.lpf(layer, f)

        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 2, 10000)
        layer = fx.hpf(layer, f)

        out.dub(layer)

    out = fx.norm(out, 1)

    return dpos, out


if __name__ == '__main__':
    seed = 12345
    if len(sys.argv) > 2:
        seed = int(sys.argv[2])

    if sys.argv[1] == 'make':
        makeparticles(seed)

