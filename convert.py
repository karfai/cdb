# Copyright 2009 Don Kelly <karfai@gmail.com>

# This file is part of transit.

# transit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# transit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with transit.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement
import glob
import re
import sqlite3
import sys
import yaml

def lookup_type(cn):
    cols = {
        'date' : 'DATE',
        'exception_type' : 'INT',
        'monday' : 'INT',
        'tuesday' : 'INT',
        'wednesday' : 'INT', 
        'thursday' : 'INT',
        'friday' : 'INT',
        'saturday' : 'INT',
        'sunday' : 'INT',
        'start_date' : 'DATE',
        'end_date' : 'DATE',
        'route_type' : 'INT',
        'stop_lat' : 'FLOAT',
        'stop_lon' : 'FLOAT',
        'stop_sequence': 'INT',
        'pickup_type' : 'INT',
        'drop_off_type' : 'INT',
        'block_id' : 'INT',
    }
    t = 'TEXT'
    if cn in cols:
        t = cols[cn]
    return t

def parse(fn):
    cols = None
    data = []
    with open(fn) as f:
        for ln in f:
            vals = unicode(ln.rstrip(), 'utf_8').split(',')
            # don't replace(), trim the ends in case there are embedded "'s
            vals = [(len(v) > 0 and v[0] == '"') and v[1:-1] or v for v in vals]
            if cols is None:
                cols = vals
            else:
                data.append(vals)
    return (cols, data)

def add_table(conn, fn):
    mt = re.match('.+/(\w+)\.txt', fn)
    tbl = mt.group(1)
    (cols, data) = parse(fn)
    if cols is not None:
        print "adding %s (%s)" % (tbl, fn)
        cr = 'CREATE TABLE %s (%s)' % (tbl, ','.join(['%s %s' % (cn, lookup_type(cn)) for cn in cols]))
        ins = 'INSERT INTO %s (%s) VALUES (%s)' % (tbl, ','.join(cols), ','.join(['?' for i in range(0, len(cols))]))
        cur = conn.cursor()
        cur.execute(cr)
        [cur.execute(ins, d,) for d in data]
        conn.commit()
        cur.close()

conn = sqlite3.connect('octranspo.db')
#for fn in glob.glob('%s/*.txt' % sys.argv[1]):
#    add_table(conn, fn)

#stops = yaml.load(file('stops.yml', 'rb'))
#for stop in stops:
#    n = stop[':name']
#    if not unicode == n.__class__:
#        n = unicode(n)

# print len(stops)

            
