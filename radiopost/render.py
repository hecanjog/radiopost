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
    renderstart = time.time()
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
    TLEN = dsp.rand(60, 60 * 30)
    clen = 0
    while clen < TLEN:
        c = options.pop(dsp.randint(0, len(options)-1))
        choices += [ c ]
        clen += FLAC(c)['length']

    segments.divide(choices, name, seed)
    synth.makeparticles(TLEN, name, seed)
    waves.makewaves(name, seed)
    waves.mixwaves(TLEN, name, seed)
    waves.basswaves(name, seed)
    waves.combinewaves(name, seed)

    final = Path('renders/%s/%s-combined.wav' % (name, seed))
    catalognumber = 'phafg-%s' % hashit(final)
    dest = Path('/srv/radio/phonography/generated/hcj01/%s.flac' % catalognumber)

    r = subprocess.run(['sox', final, dest])
    if r.returncode != 0:
        raise Exception('Could not convert to flac: %s' % dest)

    flac = FLAC(dest)

    credits = []
    for c in choices:
        credits += FLAC(c)['title']

    flac['title'] = 'Processed from: ' + ', '.join(credits)
    flac['catalognumber'] = catalognumber
    flac.save()

    cover = Path('/srv/www/phonography.radio.af/covers/default.jpg')
    dcover = Path('/srv/www/phonography.radio.af/covers/%s.jpg' % catalognumber)

    shutil.copy(cover, dcover)

    renderend = time.time()

    rendertime = renderend - renderstart
    renderminutes = rendertime // 60
    renderseconds = rendertime - (renderminutes * 60)

    tminutes = TLEN//60
    tseconds = TLEN - (tminutes * 60)

    print('New phonography.radio.af procedural render')
    print(flac.info.pprint())
    print('Target Length: %s minutes %s seconds (%s total seconds)' % (tminutes, tseconds, TLEN))
    print('Credits:', flac['title'][0])
    print('Catalog Number:', flac['catalognumber'][0])
    print('Cover:', dcover)
    print('FLAC:', dest)
    print('Rendered in %s minutes %s seconds' % (renderminutes, renderseconds))

