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

import sqlite3
from datetime import *
from storm.locals import *

def time_to_secs(ts):
    (h, m, s) = ts.split(':')
    return int(s) + int(m) * 60 + int(h) * 3600

def secs_to_time(secs):
    h = secs / 3600
    m = (secs % 3600) / 60
    s = (secs % 3600) % 60
    return '%02i:%02i:%02i' % (h, m, s)
    
def secs_elapsed_today():
    n = datetime.now()
    return (n - datetime(n.year, n.month, n.day)).seconds

class ServicePeriod(object):
    __storm_table__ = "service_periods"
    id = Int(primary=True)    
    days = Int()
    start = Int()
    finish = Int()

class ServiceException(object):
    __storm_table__ = "service_exceptions"
    id = Int(primary=True)    
    day = Int()
    exception_type = Int()
    service_period_id = Int()

class Pickup(object):
    __storm_table__ = "pickups"
    __storm_primary__ = "trip_id", "stop_id"
    trip_id = Int()
    stop_id = Int()
    arrival = Int()
    departure = Int()
    sequence = Int()

    def arrival_s(self):
        return secs_to_time(self.arrival)

    def in_service(self, service_period):
        return self.trip.in_service(service_period)

    def arrives_in_range(self, r):
        return self.arrival in r

    def minutes_until_arrival(self):
        n = secs_elapsed_today()
        return (self.arrival - n) / 60


class Stop(object):
    __storm_table__ = "stops"
    id = Int(primary=True)
    label = Unicode()
    number = Int()
    name = Unicode()
    lat = Float()
    lon = Float()

    def upcoming_pickups(self, offset):
        t = secs_elapsed_today()
        r = range(t - 5 * 60, (t + offset * 60) + 1)
        sp = current_service_period(Store.of(self))
        rv = [pu for pu in self.pickups if pu.in_service(sp) and pu.arrives_in_range(r)]
        rv.sort(cmp=lambda a,b: cmp(a.arrival, b.arrival))
        return rv

class Route(object):
    __storm_table__ = "routes"
    id = Int(primary=True)
    name = Unicode()
    route_type = Int()

class Trip(object):
    __storm_table__ = "trips"
    id = Int(primary=True)
    route_id = Int()
    service_period_id = Int()
    headsign = Unicode()
    block = Int()

    def in_service(self, service_period):
        return self.service_period == service_period

    def _pickups_in_sequence(self):
        rv = [pu for pu in self.pickups]
        rv.sort(cmp=lambda a,b: cmp(a.sequence, b.sequence))
        return rv

    def next_pickups_from_now(self, limit):
        n = secs_elapsed_today()
        return [pu for pu in self._pickups_in_sequence() if pu.arrival >= n][0:limit]

    def next_pickups_from_pickup(self, stpu, limit):
        return [pu for pu in self._pickups_in_sequence() if pu.sequence > stpu.sequence][0:limit]

Trip.route = Reference(Trip.route_id, Route.id)
Trip.service_period = Reference(Trip.service_period_id, ServicePeriod.id)
Stop.trips = ReferenceSet(Stop.id, Pickup.stop_id, Pickup.trip_id, Trip.id)
Stop.pickups = ReferenceSet(Stop.id, Pickup.stop_id)
Trip.stops = ReferenceSet(Trip.id, Pickup.trip_id, Pickup.stop_id, Stop.id)
Trip.pickups = ReferenceSet(Trip.id, Pickup.trip_id)
Pickup.stop = Reference(Pickup.stop_id, Stop.id)
Pickup.trip = Reference(Pickup.trip_id, Trip.id)
ServiceException.service_period = Reference(ServiceException.service_period_id, ServicePeriod.id)

def current_service_period(st):
    n = datetime.now()
    fl = (1 << n.weekday())
    day = n.date().toordinal()
    ex = st.find(ServiceException, ServiceException.day == day).one()
    rv = None
    if ex:
        rv = ex.service_period
    else:
        for p in st.find(ServicePeriod):
            if p.days & fl and dt in range(p.start, p.finish + 1):
                rv = p
                break
    return rv

def create_store():
    return Store(create_database('sqlite:test.db'))

def make():
    conn = sqlite3.connect('foo')
    cur = conn.cursor()
    cur.execute('CREATE TABLE stops (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, number INTEGER, name TEXT, lat FLOAT, lon FLOAT)')
    cur.execute('CREATE TABLE routes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, route_type INTEGER)')
    cur.execute('CREATE TABLE trips (id INTEGER PRIMARY KEY AUTOINCREMENT, headsign TEXT, block INTEGER, route_id INTEGER, service_period_id INTEGER)')
    cur.execute('CREATE TABLE pickups (id INTEGER PRIMARY KEY AUTOINCREMENT, arrival INTEGER, departure INTEGER, sequence INTEGER, trip_id INTEGER, stop_id INTEGER)')
    cur.execute('CREATE TABLE service_periods (id INTEGER PRIMARY KEY AUTOINCREMENT, days INTEGER, start INTEGER, finish INTEGER)')
    cur.execute('CREATE TABLE service_exceptions (id INTEGER PRIMARY KEY AUTOINCREMENT, day INTEGER, exception_type INTEGER, service_period_id INTEGER)')
    conn.commit()
    cur.close()
    return conn


