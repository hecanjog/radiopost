import json
import sys
import sqlite3

from pippi import dsp, fx, shapes
from . import SR, DB, getsnd, stretch

def makecurve(segment):
    snd = getsnd(segment)
    return snd.toenv()

def makeparticles(TLEN, name, seed=12345):
    dsp.seed(seed)

    out = dsp.buffer(length=TLEN)

    numphrases = dsp.randint(1, max(2, int(TLEN * 0.01)))
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

    params = []
    for li in phraseidxs:
        length = phrases[li]
        params += [ (name, seed, li, length, pos) ]

        if unusedsilence > 0:
            s = dsp.rand(0, min(unusedsilence, maxphrase))
            unusedsilence -= s
            pos += s

        pos += length

    outputs = dsp.pool(makephrase, params=params, processes=8)
    for pos, phrase in outputs:
        out.dub(phrase, pos)

    out *= 2
    out = fx.compressor(out, -5, 5)
    out = fx.norm(out, 1)

    out.write('renders/%s/stems/%s-particles.wav' % (name, seed))


def makephrase(name, seed, li, length, dpos):
    db = DB(name, seed)
    segments = db.noisy()

    dsp.seed(seed+li)

    out = dsp.buffer(length=length)

    rcurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))
    lcurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))
    acurvemod = shapes.win('sine', length=length, stability=shapes.win('sine'))
    fwcurvemod = shapes.win('sine', length=0.5, stability=shapes.win('sine'))
    fmcurvemod = shapes.win('sine', length=1, stability=shapes.win('sine'))

    for _ in range(dsp.randint(1, dsp.randint(2, 10))):
        layer = dsp.buffer(length=length)
        pan = shapes.win('sine', length=0.2)

        stablecurve = shapes.win('sine')
        rhythmcurve = shapes.win('sine', length=20, stability=stablecurve) * rcurvemod
        #rhythmcurve.graph('renders/%s/graphs/%s-rhythmcurve.png' % (name, seed))

        lengthcurve = shapes.win('sine', length=10) * lcurvemod
        #lengthcurve.graph('renders/%s/graphs/%s-lengthcurve.png' % (name, seed))
        lengthcurve = dsp.win(lengthcurve, dsp.MS*1, dsp.rand(0.02, length/2))

        elapsed = 0
        pos = 0

        maxlength = dsp.rand(1, length)
        minlength = dsp.MS*0.1

        onsets = []
        while elapsed < length:
            pos = elapsed / length
            o = abs(rhythmcurve.interp(pos)) * (maxlength-minlength) + minlength
            onsets += [ o + elapsed ]
            elapsed += o

        acurve = shapes.win('hann', length=10) * acurvemod
        #acurve.graph('renders/%s/graphs/%s-ampcurve.png' % (name, seed))

        flens = length/120
        flens = 0.5

        fwidth = shapes.win('hann', length=flens, stability=shapes.win('sine')) * fwcurvemod
        #fwidth.graph('renders/%s/graphs/%s-freqwidth.png' % (name, seed))
        fwidth = dsp.win(fwidth, 0.001, 0.5)

        fmin = shapes.win('hann', length=flens, stability=shapes.win('sine')) * fmcurvemod
        #fmin.graph('renders/%s/graphs/%s-freqmin.png' % (name, seed))
        fmin = dsp.win(fmin, 0.5, 1)

        p = None
        for i, onset in enumerate(onsets):
            pos = i / len(onsets)

            if p is None or dsp.rand() > 0.1:
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

        f = dsp.win(shapes.win('hann', length=0.5) * shapes.win('hann'), 200, 20000)
        layer = fx.lpf(layer, f)

        f = dsp.win(shapes.win('hann') * shapes.win('hann'), 2, 10000)
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

