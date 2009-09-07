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

import pygtk
pygtk.require('2.0')
import gtk

import re
from storm.locals import *

import schema

# model elements
def search_intersection(parts):
    a = unicode('%' + parts[0].upper() + '%')
    b = unicode('%' + parts[1].upper() + '%')
    return Or(Like(schema.Stop.name, '%s/%s' % (a, b)),
              Like(schema.Stop.name, '%s/%s' % (b, a)))

def search_number(parts):
    return schema.Stop.number == int(parts[0])

def search_label(parts):
    return schema.Stop.label == unicode(parts[0].upper())

def search_all(parts):
    return schema.Stop.name.like(unicode('%' + parts[0].upper() + '%'))

srch_pats = [
    ('(\w+) and (\w+)',       search_intersection),
    ('(\w+)\s*/\s*(\w+)',     search_intersection),
    ('([0-9]{4})',            search_number),
    ('([a-zA-Z]{2}[0-9]{3})', search_label),
    ('(\w+)',                 search_all),
]

class Results(object):
    def __init__(self):
        self._real = None

    def set_realization(self, r):
        self._real = r
        
    def show(self, *args):
        if self._real:
            self._real.append(*args)

    def clear(self):
        if self._real:
            self._real.clear()
        
class Model(object):
    def __init__(self):
        self._store = schema.create_store()
        self._results = Results()

    def _build_search(self, s):
        rv = None
        for p in srch_pats:
            mt = re.match(p[0], s)
            if mt:
                rv = p[1](mt.groups())
                
            if rv:
                break
        
        return rv

    # def _prune_stops(self, stops, offset):
    #     n = schema.secs_elapsed_today()
    #     for stop in stops:
    #         for pu in stop.upcoming_pickups(offset):
    #             m = (pu.arrival - n) / 60
    #             print '%s (%i): %s' % (stop.label, stop.number, stop.name)
    #             print "%s %s in %um (%s)" % (pu.trip.route.name, pu.trip.headsign, m, pu.arrival_s())

    def _show_stops(self, stops):
        self._results.clear()
        for stop in stops:
            self._results.show(stop.label, stop.number, stop.name)
            
    def stop_search(self, s):
        srch = self._build_search(s)
        if srch:
            self._show_stops(self._store.find(schema.Stop, srch))

    def results(self):
        return self._results

# GUI (view/control) elements

# there is only ever a Panel which is re-built depending on state
class InfoLabel(gtk.Label):
    def __init__(self, text):
        gtk.Label.__init__(self, None)
        self.set_markup('<span size="x-large">%s</span>' % text)
        self.set_property('xalign', 0.0)
        
class FindButton(gtk.Button):
    def __init__(self, panel):
        gtk.Button.__init__(self, None, 'gtk-find')
        self.connect('clicked', self.act_click, panel)

    def act_click(self, w, panel):
        panel.model().stop_search(panel.get_query_text())

class SelectButton(gtk.Button):
    def __init__(self, panel):
        gtk.Button.__init__(self, None, 'gtk-execute')
        self.connect('clicked', self.act_click, panel)

    def act_click(self, w, panel):
        pass

class LocationEntry(gtk.ComboBoxEntry):
    def __init__(self):
        gtk.ComboBoxEntry.__init__(self)

class ResultsListModel(gtk.ListStore):
    def __init__(self, results):
        gtk.ListStore.__init__(self, str, str, str)
        results.set_realization(self)

    def append(self, *args):
        it = gtk.ListStore.append(self)
        [self.set(it, i, args[i]) for i in range(0, len(args))]
            
class ResultsTreeView(gtk.TreeView):
    def __init__(self, results):
        gtk.TreeView.__init__(self, ResultsListModel(results))
        self.set_headers_visible(False)
        for i in range(0, self.get_model().get_n_columns()):
            self.append_column(gtk.TreeViewColumn('', gtk.CellRendererText(), markup=i))

class Panel(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        self._model = Model()

        self.set_border_width(6)
        self._build_contents()
        self.connect('destroy', self.act_quit)

    def _build_list(self):
        self._list = ResultsTreeView(self._model.results())

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self._list)

        return sw

    def _build_contents(self):
        self._location_entry = LocationEntry()

        vb = gtk.VBox(False, 4)
        vb.pack_start(InfoLabel('Where are you now?'), False, True, 0)

        hb = gtk.HBox(False, 8)
        hb.pack_start(self._location_entry, True, True, 0)

        hb2 = gtk.HBox(False, 2)
        hb2.pack_start(FindButton(self), True, True, 0)
        hb2.pack_start(gtk.Button('GPS'), True, True, 0)

        hb.pack_start(hb2, True, True, 0)

        vb.pack_start(hb, False, True, 0)
        vb.pack_start(self._build_list(), True, True, 0)

        vb.pack_start(SelectButton(self), False, True, 0)

        self.add(vb)

    def act_quit(self, w):
        gtk.main_quit()        

    def get_query_text(self):
        return self._location_entry.get_active_text()

    def model(self):
        return self._model

w = Panel()
w.show_all()
gtk.main()
