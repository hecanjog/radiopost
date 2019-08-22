import contextlib
import os
import sqlite3

from pippi import dsp

DEFAULT_SEED = 12345
TLEN = 60 * 10
WINSIZE = 4096
HOPSIZE = WINSIZE//2
SR = 44100

def getsnd(seg):
    return dsp.read(seg['source'], start=seg['start']/SR, length=seg['length']/SR)

def stretch(snd, length):
    overlap = dsp.rand(dsp.MS*10, dsp.MS*50)
    overlap = min(overlap, snd.dur * 0.25)

    out = dsp.buffer(length=length)

    pos = 0
    while pos < length:
        seglen = dsp.rand(snd.dur/2, snd.dur)
        seg = snd.rcut(seglen).taper(overlap)
        out.dub(seg, pos)
        pos += seglen - overlap

    return out

class DB:
    def __init__(self, name, seed=DEFAULT_SEED, reset=False):
        dbpath = 'renders/%s/%s-info.db' % (name, seed)

        if reset:
            with contextlib.suppress(FileNotFoundError):
                os.remove(dbpath)

        self.db = sqlite3.connect(dbpath)
        self.db.row_factory = sqlite3.Row
        self.c = self.db.cursor()

    def __del__(self):
        self.db.close()

    def longest(self, count=None):
        sql = 'SELECT * FROM segments ORDER BY length DESC'
        if count is not None:
            sql += ' LIMIT ?'
            return self.q(sql, (count,))
        else:
            return self.q(sql)

    def noisy(self, count=None):
        sql = 'SELECT * FROM segments WHERE freq = 0 ORDER BY flatness ASC'
        if count is not None:
            sql += ' LIMIT ?'
            return self.q(sql, (count,))
        else:
            return self.q(sql)

    def pitchy(self, count=None):
        sql = 'SELECT * FROM segments WHERE freq > 0 ORDER BY flatness DESC'
        if count is not None:
            sql += ' LIMIT ?'
            return self.q(sql, (count,))
        else:
            return self.q(sql)

    def a(self, sql):
        try:
            self.c.execute(sql)
            self.db.commit()
        except sqlite3.Error as e:
            print(e)

    def m(self, sql, rows):
        try:
            self.c.executemany(sql, rows)
            self.db.commit()
        except sqlite3.Error as e:
            print(e)

    def q(self, sql, params=None):
        try:
            if params is not None:
                self.c.execute(sql, params)
            else:
                self.c.execute(sql)
            return self.c.fetchall()
        except sqlite3.Error as e:
            print(e)



