import json
import sys

import matplotlib.pyplot as plt

SR = 44100

def plotlengths(path):
    with open(path, 'r') as j:
        segments = json.loads(j.read())

        lengths = []

        for segment in segments:
            if segment['length'] is None or segment['length'] > (5*SR):
                continue
            l = segment['length'] / float(SR) 
            lengths += [ l ]

        plt.hist(lengths, bins='auto')
        plt.title('Lengths < 5 seconds')
        plt.savefig('%s-seglengths.pdf' % path.replace('.json', ''))

def plotcontrasts(path):
    with open(path, 'r') as j:
        segments = json.loads(j.read())

        contrasts = []

        for segment in segments:
            if segment['contrast'] is None:
                continue

            contrasts += [ segment['contrast'] ]

        plt.hist(contrasts, bins='auto')
        plt.title('Contrasts')
        plt.savefig('segcontrasts.pdf')

def plotflatness(path):
    with open(path, 'r') as j:
        segments = json.loads(j.read())

        flatness = []

        for segment in segments:
            if segment['flatness'] is None:
                continue

            flatness += [ segment['flatness'] ]

        plt.hist(flatness, bins='auto')
        plt.title('Flatness')
        plt.savefig('segflatness.pdf')


if __name__ == '__main__':
    try:
        plotlengths(sys.argv[1])
        #plotcontrasts(sys.argv[1])
        #plotflatness(sys.argv[1])
    except IndexError:
        print('Usage: python -m radiopost.graph <path-to-segments.json>')


