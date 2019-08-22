import contextlib
import os
from pathlib import Path
from pippi import dsp
import sys

if __name__ == '__main__':
    from . import synth, segments, waves

    seed = None

    try:
        flacs = sys.argv[1]
        name = sys.argv[2]
        if len(sys.argv) > 3:
            seed = int(sys.argv[3])
    except IndexError:
        print('Usage: python -m radiopost.render <path-to-flacs> <name> <seed>')

    (Path('renders') / Path(name)).mkdir(exist_ok=True)
    (Path('renders') / Path(name) / Path('waves')).mkdir(exist_ok=True)
    (Path('renders') / Path(name) / Path('stems')).mkdir(exist_ok=True)
    (Path('renders') / Path(name) / Path('graphs')).mkdir(exist_ok=True)

    if seed is None:
        seed = sum([ ord(s) for s in str(name) ])

    print('SEED', seed)

    choices = [ str(p) for p in Path(sys.argv[1]).glob('*.flac') ]
    print('Choices:', choices)

    TLEN = 0
    for c in choices:
        TLEN += dsp.read(c).dur

    TLEN = 60 * 3

    print('TLEN', TLEN)

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

    print('DONE!')

