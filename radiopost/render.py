from pathlib import Path
import sys

if __name__ == '__main__':
    from . import synth, segments, waves

    try:
        flacs = sys.argv[1]
        seed = int(sys.argv[2])
    except IndexError:
        print('Usage: python -m radiopost <path-to-flacs> <seed>')

    choices = [ str(p) for p in Path(sys.argv[1]).glob('*.flac') ]
    print('Choices:', choices)

    print('divide')
    segments.divide(choices, seed)

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

