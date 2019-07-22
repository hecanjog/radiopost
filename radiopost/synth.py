import json
import sys
import sqlite3

from pippi import dsp, fx, shapes
from . import TLEN

SR = 44100

def getsnd(seg):
    return dsp.read(seg['source'], start=seg['start']/SR, length=seg['length']/SR)

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

    length = TLEN * 0.6

    db = sqlite3.connect('%s-info.db' % seed)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    q = 'SELECT * FROM segments WHERE flatness < 0.01'
    c.execute(q)

    segments = c.fetchall()

    out = dsp.buffer(length=length)

    for _ in range(3):
        layer = dsp.buffer(length=length)
        pan = shapes.win('sine', length=0.2)

        #rhythmcurve = makecurve(dsp.choice(segments)).skewed(0.9)
        stablecurve = shapes.win('sine')
        rhythmcurve = shapes.win('sine', length=20, stability=stablecurve)
        rhythmcurve.graph('%s-rhythmcurve.png' % seed)

        lengthcurve = shapes.win('sine', length=10)
        lengthcurve.graph('%s-lengthcurve.png' % seed)
        lengthcurve = dsp.win(lengthcurve, dsp.MS*1, 0.2)

        elapsed = 0

        maxlength = dsp.MS*100
        minlength = dsp.MS*0.1

        onsets = []
        while elapsed < length:
            pos = elapsed / length
            o = abs(rhythmcurve.interp(pos)) * (maxlength-minlength) + minlength
            onsets += [ o + elapsed ]
            elapsed += o


        acurve = shapes.win('hann', length=10)
        acurve.graph('%s-ampcurve.png' % seed)

        fwidth = shapes.win('hann', length=4, stability=shapes.win('sine'))
        fwidth.graph('%s-freqwidth.png' % seed)
        fwidth = dsp.win(fwidth, 0.001, 0.5)

        fmin = shapes.win('hann', length=4, stability=shapes.win('sine'))
        fmin.graph('%s-freqmin.png' % seed)
        fmin = dsp.win(fmin, 0.5, 1)

        p = None
        for i, onset in enumerate(onsets):
            pos = i / len(onsets)

            if p is None or dsp.rand() > 0.6:
                segment = segments[int(acurve.interp(pos) * (len(segments)-1))]
                p = getsnd(segment)

            l = min(lengthcurve.interp(pos), p.dur)
            p = p.rcut(l).taper(dsp.MS*10).env('rsaw')
            fm = fmin.interp(pos)
            fw = fwidth.interp(pos)
            p = p.vspeed(dsp.win(shapes.win('sine'), fm, fm+fw))
            #f = dsp.win(makecurve(dsp.choice(segments)), 100, 20000)
            layer.dub(p, onset)

        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 200, 20000)
        layer = fx.lpf(layer, f)

        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 2, 10000)
        layer = fx.hpf(layer, f)

        out.dub(layer)

    out = fx.norm(out, 1)

    out.write('%s-particles.wav' % seed)


if __name__ == '__main__':
    seed = 12345
    if len(sys.argv) > 2:
        seed = int(sys.argv[2])

    if sys.argv[1] == 'make':
        makeparticles(seed)

