import contextlib
import os
from pathlib import Path
from pippi import dsp
import sys
import time
from mutagen.flac import FLAC
import subprocess
import hashlib
import shutil

def hashit(f):
    sha1 = hashlib.sha1()
    with open(f, 'rb') as b:
        while True:
            d = b.read(2**16)
            if not d:
                break
            sha1.update(d)
    return str(sha1.hexdigest())


if __name__ == '__main__':
    from . import synth, segments, waves

    FLACPATH = '/srv/radio/phonography/recordings'
    name = 'r'
    seed = int(time.time())

    (Path('renders') / Path(name)).mkdir(exist_ok=True)
    (Path('renders') / Path(name) / Path('waves')).mkdir(exist_ok=True)
    (Path('renders') / Path(name) / Path('stems')).mkdir(exist_ok=True)
    (Path('renders') / Path(name) / Path('graphs')).mkdir(exist_ok=True)

    dsp.seed(seed)

    options = [ str(p) for p in Path(FLACPATH).glob('*.flac') ]

    choices = []
    MLEN = dsp.rand(60 * 3, 60 * 20)
    TLEN = 0
    while TLEN < MLEN:
        o = options.pop(dsp.randint(0, len(options)-1))
        TLEN += dsp.read(o).dur
        choices += [ o ]

    TLEN *= dsp.rand(0.2, 1)

    print('TLEN', TLEN, 'MLEN', MLEN)
    print('Choices:', choices)

    print('divide')
    segments.divide(choices, name, seed)

    print('makeparticles')
    synth.makeparticles(TLEN, name, seed)

    print('makewaves')
    waves.makewaves(name, seed)

    print('mixwaves')
    waves.mixwaves(TLEN, name, seed)

    print('basswaves')
    waves.basswaves(name, seed)

    print('combine')
    waves.combinewaves(name, seed)

    final = Path('renders/%s/%s-combined.wav' % (name, seed))
    catalognumber = 'phafg-%s' % hashit(final)
    dest = Path('/srv/radio/phonography/generated/hcj01/%s.flac' % catalognumber)

    r = subprocess.run(['sox', '-S', final, dest])
    if r.returncode != 0:
        raise Exception('Could not convert to flac: %s' % dest)

    flac = FLAC(dest)

    credits = []
    for c in choices:
        credits += FLAC(c)['title']

    print(credits)

    flac['title'] = ', '.join(credits)
    flac['catalognumber'] = catalognumber
    flac.save()

    cover = Path('/srv/www/phonography.radio.af/covers/default.jpg')
    dcover = Path('/srv/www/phonography.radio.af/covers/%s.jpg' % catalognumber)

    shutil.copy(cover, dcover)

    print('DONE!')

