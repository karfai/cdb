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

from schema import *
import re, sys

st = create_store()

def search_intersection(parts):
    a = unicode('%' + parts[0].upper() + '%')
    b = unicode('%' + parts[1].upper() + '%')
    return Or(Like(Stop.name, '%s/%s' % (a, b)),
              Like(Stop.name, '%s/%s' % (b, a)))

def search_number(parts):
    return Stop.number == int(parts[0])

def search_label(parts):
    return Stop.label == unicode(parts[0].upper())

def search_all(parts):
    return Stop.name.like(unicode('%' + parts[0].upper() + '%'))

patterns = [
    ('(\w+) and (\w+)',       search_intersection),
    ('(\w+)\s*/\s*(\w+)',     search_intersection),
    ('([0-9]{4})',            search_number),
    ('([a-zA-Z]{2}[0-9]{3})', search_label),
    ('(\w+)',                 search_all),
]

srch = None
for p in patterns:
    mt = re.match(p[0], sys.argv[1])
    if mt:
        srch = p[1](mt.groups())

    if srch:
        break

n = secs_elapsed_today()
for r in st.find(Stop, srch):
    print '%s (%i): %s' % (r.label, r.number, r.name)
    for pu in r.upcoming_pickups(int(sys.argv[2])):
        m = (pu.arrival - n) / 60
        print "%s %s in %um (%s)" % (pu.trip.route.name, pu.trip.headsign, m, pu.arrival_s())
