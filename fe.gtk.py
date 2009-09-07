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
        self._current_stop = None

    def _build_search(self, s):
        rv = None
        for p in srch_pats:
            mt = re.match(p[0], s)
            if mt:
                rv = p[1](mt.groups())
                
            if rv:
                break
        
        return rv

    def _show_stops(self, stops):
        self._results.clear()
        for stop in stops:
            self._results.show(stop.label, stop.number, stop.name)

    def format_current_stop(self):
        return '%s (%s/%i)' % (self._current_stop.name, self._current_stop.label, self._current_stop.number)

    def set_current_stop(self, code):
        self._current_stop = self._store.find(schema.Stop, schema.Stop.label == unicode(code)).one()
            
    def stop_search(self, s):
        srch = self._build_search(s)
        if srch:
            self._show_stops(self._store.find(schema.Stop, srch))

    def _format_arrival(self, m):
        fmt = (m < 0) and 'Should have arrived %s ago' or 'Arriving in %s'
        ms = (m > 60) and '%i:%02i' % (m / 60, m % 60) or '%i minutes' % m
        return fmt % ms

    def upcoming_pickups_at_current(self, offset):
        n = schema.secs_elapsed_today()
        self._results.clear()
        for pu in self._current_stop.upcoming_pickups(offset):
            m = (pu.arrival - n) / 60
            s = 'now'
            if m < 0:
                s = self._format_arrival(m)
            elif m > 0:
                s = self._format_arrival(m)
            self._results.show(pu.trip.route.name, pu.trip.headsign, s)

    def results(self):
        return self._results

# GUI (view/control) elements

# there is only ever a Panel which is re-built depending on state
class InfoLabel(gtk.Label):
    def __init__(self, text):
        gtk.Label.__init__(self, None)
        self.set_property('xalign', 0.0)

    def change_text(self, text):
        self.set_markup('<span size="x-large">%s</span>' % text)
        
class FindButton(gtk.Button):
    def __init__(self, panel):
        gtk.Button.__init__(self, None, 'gtk-find')
        self.connect('clicked', self.act_click, panel)

    def act_click(self, w, panel):
        panel.model().stop_search(panel.get_query_text())

class NextStateButton(gtk.Button):
    def __init__(self, panel):
        gtk.Button.__init__(self, None, 'gtk-execute')
        self.connect('clicked', self.act_click, panel)

    def act_click(self, w, panel):
        panel.next()

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

class State(object):
    def __init__(self, panel):
        self._panel = panel

    def start(self):
        pass

    def finish(self):
        pass

    def get_visibility(self):
        return (True, True)

    def get_info_text(self):
        return ''

    def model(self):
        return self._panel.model()

    def panel(self):
        return self._panel

    def next(self):
        self.finish()
        rv = self.next_class()(self._panel)
        rv.start()
        return rv

class Wait(State):
    def get_visibility(self):
        return (True, False)

    def start(self):
        self.panel().model().upcoming_pickups_at_current(300)

    def get_info_text(self):
        return 'Waiting at %s' % self.panel().model().format_current_stop()

class SelectStop(State):
    def get_info_text(self):
        return 'Where are you now?'

    def finish(self):
        r = self.panel().selected_result()
        self.panel().model().set_current_stop(r[0])

    def next_class(self):
        return Wait

class Panel(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        self.set_border_width(6)
        self.connect('destroy', self.act_quit)

        self._model = Model()
        self._state = SelectStop(self)

        self._build_contents()

    def _build_list(self):
        self._list = ResultsTreeView(self._model.results())

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self._list)

        return sw

    def _build_contents(self):
        vb = gtk.VBox(False, 4)

        self._info = InfoLabel('')
        vb.pack_start(self._info, False, True, 0)

        self._search_box = gtk.HBox(False, 8)

        self._location_entry = LocationEntry()
        self._search_box.pack_start(self._location_entry, True, True, 0)

        hb = gtk.HBox(False, 2)
        hb.pack_start(FindButton(self), True, True, 0)
        hb.pack_start(gtk.Button('GPS'), True, True, 0)
        self._search_box.pack_start(hb, True, True, 0)

        vb.pack_start(self._search_box, False, True, 0)
        vb.pack_start(self._build_list(), True, True, 0)

        vb.pack_start(NextStateButton(self), False, True, 0)

        self.add(vb)

    def act_quit(self, w):
        gtk.main_quit()        

    def get_query_text(self):
        return self._location_entry.get_active_text()

    def model(self):
        return self._model

    def next(self):
        self._state = self._state.next()
        self.refresh()

    def refresh(self):
        self.show_all()

        self._info.change_text(self._state.get_info_text())

        vis = self._state.get_visibility()
        if vis[0]:
            self._info.show_all()
        else:
            self._info.hide_all()
        if vis[1]:
            self._search_box.show_all()
        else:
            self._search_box.hide_all()

    def selected_result(self):
        sel = self._list.get_selection()
        rv = None
        if sel:
            (m, it) = sel.get_selected()
            if it:
                rv = [m.get_value(it, i) for i in range(0, m.get_n_columns())]
        return rv


w = Panel()
w.refresh()
gtk.main()
