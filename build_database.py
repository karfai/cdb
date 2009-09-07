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

from schema import *
from datetime import *

def add_stop(cur, cache, parts):
    cur.execute(
        'INSERT INTO stops (label,number,name,lat,lon) VALUES (?,?,?,?,?)',
        [parts[0], 0, parts[1], float(parts[3]), float(parts[4]),]
        )
    cache['stops'][parts[0]] = cur.lastrowid

def add_route(cur, cache, parts):
    cur.execute(
        'INSERT INTO routes (name,route_type) VALUES (?,?)',
        [parts[1], int(parts[4]),]
        )
    
    cache['routes'][parts[0]] = cur.lastrowid

def add_trip(cur, cache, parts):
    route_id = cache['routes'][parts[0]]
    service_period_id = cache['service_periods'][parts[1]]
    block = 0
    if not 0 == len(parts[4]):
        block = int(parts[4])
    cur.execute(
        'INSERT INTO trips (headsign,block,service_period_id,route_id) VALUES (?,?,?,?)',
        [parts[3], block, service_period_id, route_id]
        )
    
    cache['trips'][parts[2]] = cur.lastrowid

def add_pickup(cur, cache, parts):
    trip_id = cache['trips'][parts[0]]
    stop_id = cache['stops'][parts[3]]
    
    cur.execute(
        'INSERT INTO pickups (arrival, departure, trip_id, stop_id) VALUES (?,?,?,?)',
        [time_to_secs(parts[1]), time_to_secs(parts[2]), trip_id, stop_id]
        )

def add_service_period(cur, cache, parts):
    p = 0
    days = 0
    for i in parts[1:8]:
        days |= (int(i) << p)
        p += 1
    st = datetime.strptime(parts[8], '%Y%m%d').toordinal()
    fin = datetime.strptime(parts[9], '%Y%m%d').toordinal()
    cur.execute(
        'INSERT INTO service_periods (days, start, finish) VALUES (?,?,?)',
        [days, st, fin]
        )
    cache['service_periods'][parts[0]] = cur.lastrowid
    
    
def build(conn, cache, fuel):
    (t, fn) = fuel
    print t
    with open('feed/%s.txt' % (t)) as f:
        skip_one = True
        lines = f.readlines()
        steps = {}
        for i in range(1, 10):
            steps[int(len(lines) * (float(i)/10.0))] = '%i%%' % (i * 10)

        lc = 0
        for ln in lines:
            if lc in steps:
                print steps[lc]

            if not skip_one:
                parts = [p.replace('"', '').strip() for p in unicode(ln.rstrip(), 'utf_8').split(',')]
                cur = conn.cursor()
                fn(cur, cache, parts)
                cur.close()
            else:
                skip_one = False
            lc += 1
    conn.commit()

conn = make()
cache = {
    'stops'  : {},
    'service_periods'  : {},
    'routes' : {},
    'trips'  : {}
}

builders = [
    ['calendar',   add_service_period],
    ['stops',      add_stop],
    ['routes',     add_route],
    ['trips',      add_trip],
    ['stop_times', add_pickup],
]

[build(conn, cache, fuel) for fuel in builders]
