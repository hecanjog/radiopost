from pippi import dsp, fx, shapes
from . import getsnd

def sparkreplace(snd, bits, tone, bass, db):
    print('SPARK REPLACE')
    length = dsp.rand(10, 30)
    out = dsp.buffer(length=length)    

    numlayers = dsp.randint(4, 8)
    width = dsp.rand(0.1, 1)
    cpos = dsp.rand(0, tone.dur-length-width)
    t = tone.cut(cpos, length)
    env = dsp.win('hannout').skewed(0.01) * dsp.win('hannout')

    for _ in range(numlayers):
        layer = t.pan(dsp.rand())

        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 200, 20000)
        layer = fx.lpf(layer, f)

        if dsp.rand() > 0.5:
            f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 2, 10000)
            layer = fx.hpf(layer, f)

        layer = layer.vspeed(dsp.win('rsaw', 1, dsp.rand(1.01, 1.1)))
        layer = layer.env(env.skewed(dsp.rand(0.4, 0.6)))

        out.dub(layer)

    if dsp.rand() > 0.7:
        out = fx.crossover(out, dsp.rand(10, 50), 'rnd', 'hann')
        out = fx.lpf(out, dsp.rand(3000, 6000))
        
    out = fx.norm(out, 1)
    pos = dsp.rand(0, snd.dur-out.dur)
    return dsp.join([snd.cut(0, pos), out, snd.cut(pos+out.dur, snd.dur-(pos+out.dur))])

def sparkgauze(bits, tone, bass, db):
    print('SPARK')
    length = dsp.rand(10, 30)
    out = dsp.buffer(length=length)    

    numlayers = dsp.randint(4, 8)
    width = dsp.rand(0.1, 1)
    cpos = dsp.rand(0, tone.dur-length-width)
    t = tone.cut(cpos, length)
    env = dsp.win('hannout').skewed(0.01) * dsp.win('hannout')

    for _ in range(numlayers):
        layer = t.pan(dsp.rand())

        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 200, 20000)
        layer = fx.lpf(layer, f)

        if dsp.rand() > 0.5:
            f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 2, 10000)
            layer = fx.hpf(layer, f)

        layer = layer.vspeed(dsp.win('rsaw', 1, dsp.rand(1.01, 1.1)))
        layer = layer.env(env.skewed(dsp.rand(0.4, 0.6)))

        out.dub(layer)

    if dsp.rand() > 0.7:
        out = fx.crossover(out, dsp.rand(10, 50), 'rnd', 'hann')
        out = fx.lpf(out, dsp.rand(3000, 6000))
        
    out = fx.norm(out, 1)

    out.write('sparkgauze.wav')
    return out

def alternate(a, b):
    print('ALTERNATE')
    length = dsp.rand(1, 15)
    out = dsp.buffer(length=length)    

    aseglength = dsp.rand(dsp.MS*10, 0.4)
    alengths = dsp.win(shapes.win('hann'), aseglength, aseglength * dsp.rand(1.1, 2))

    bseglength = dsp.rand(dsp.MS*10, 0.4)
    blengths = dsp.win(shapes.win('hann'), bseglength, bseglength * dsp.rand(1.1, 2))

    pos = 0
    count = 0
    while pos < length:
        if count % 2 == 0:
            l = alengths.interp(pos/length)
            s = a.cut(0, l)
        else:
            l = blengths.interp(pos/length)
            s = b.cut(0, l)

        out.dub(s, pos)
        pos += s.dur
        count += 1

    if dsp.rand() > 0.5:
        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 200, 20000)
        out = fx.lpf(out, f)

    if dsp.rand() > 0.5:
        f = dsp.win(shapes.win('hann', length=dsp.rand(10, 30)), 2, 10000)
        out = fx.hpf(out, f)

    if dsp.rand() > 0.4:
        out = fx.crush(out, dsp.rand(8, 16), out.samplerate)

    return out

def altinsert(bits, tone, bass, db):
    lng = db.longest(10)
    a = getsnd(dsp.choice(lng))
    b = getsnd(dsp.choice(lng))
    loudest = max(bits.avg, tone.avg, bass.avg) * 4
    print('altinsert loudest', loudest)
    a = fx.norm(a, loudest)
    b = fx.norm(b, loudest)
    return alternate(a, b)

def altreplace(snd, bits, tone, bass, db):
    lng = db.longest(10)
    a = getsnd(dsp.choice(lng))
    b = getsnd(dsp.choice(lng))

    loudest = snd.avg * 4
    print('altreplace loudest', loudest)
    a = fx.norm(a, loudest)
    b = fx.norm(b, loudest)

    s = alternate(a, b)
    pos = dsp.rand(0, snd.dur-s.dur)
    return dsp.join([snd.cut(0, pos), s, snd.cut(pos+s.dur, snd.dur-(pos+s.dur))])


def stutterinsert(bits, tone, bass, db):
    snd = dsp.choice([bits, tone, bass])
    return stutter(snd)

def stutterreplace(snd, bits, tone, bass, db):
    s = stutter(snd)
    pos = dsp.rand(0, snd.dur-s.dur)
    return dsp.join([snd.cut(0, pos), s, snd.cut(pos+s.dur, snd.dur-(pos+s.dur))])

def stutter(snd):
    print('STUTTER')
    length = dsp.rand(1, 15)
    out = dsp.buffer(length=length)    

    seglength = dsp.rand(dsp.MS*10, 0.4)
    lengths = dsp.win(shapes.win('hann'), seglength, seglength * dsp.rand(1.1, 2))
    start = dsp.rand(0, snd.dur-length)

    pos = 0
    while pos < length:
        l = lengths.interp(pos/length)
        b = snd.cut(start, l)
        out.dub(b, pos)
        pos += b.dur

    if dsp.rand() > 0.4:
        out = fx.crush(out, dsp.rand(8, 16), out.samplerate)

    return out

def stutterinsert(bits, tone, bass, db):
    snd = dsp.choice([bits, tone, bass])
    return stutter(snd)

def stutterreplace(snd, bits, tone, bass, db):
    s = stutter(snd)
    pos = dsp.rand(0, snd.dur-s.dur)
    return dsp.join([snd.cut(0, pos), s, snd.cut(pos+s.dur, snd.dur-(pos+s.dur))])


