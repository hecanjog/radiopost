import contextlib
import os
from pathlib import Path
from pippi import dsp
import sys
import time

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
        seed = int(time.time())
    dsp.seed(int(seed))

    options = [ str(p) for p in Path(sys.argv[1]).glob('*.flac') ]
    options += [ str(p) for p in Path(sys.argv[1]).glob('*.wav') ]

    choices = []
    MLEN = dsp.rand(60 * 3, 60 * 20)
    TLEN = 0
    while TLEN < MLEN:
        o = options.pop(dsp.randint(0, len(options)))
        TLEN += dsp.read(o).dur
        choices += [ o ]

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

    print('DONE!')

