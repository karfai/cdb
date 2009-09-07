# Copyright 2009 Don Kelly <karfai@gmail.com>

# This file is part of voyageur.

# voyageur is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# voyageur is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with voyageur.  If not, see <http://www.gnu.org/licenses/>.

import pygtk
pygtk.require('2.0')
import glib, gtk

import re
from datetime import *
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

def format_minutes(m):
    rv = '%i minute%s' % (m, (m > 1) and 's' or '')
    return (m > 60) and '%i:%02i' % (m / 60, m % 60) or rv

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
        self._stop = None
        self._trip = None

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
            self._results.show(stop.id, stop.label, stop.number, stop.name)

    def format_stop(self):
        return '%s (%s/%i)' % (self._stop.name, self._stop.label, self._stop.number)

    def format_trip(self):
        return '%s %s' % (self._trip.route.name, self._trip.headsign)

    def set_stop(self, stop_id):
        self._stop = self._store.find(schema.Stop, schema.Stop.id == stop_id).one()
            
    def set_trip(self, trip_id):
        self._trip = self._store.find(schema.Trip, schema.Trip.id == trip_id).one()

    def get_trip_id(self):
        rv = None
        if self._trip:
            rv = self._trip.id
        return rv
            
    def stop_search(self, s):
        srch = self._build_search(s)
        if srch:
            self._show_stops(self._store.find(schema.Stop, srch))

    def _format_arrival(self, pu):
        rv = 'now'
        m = pu.minutes_until_arrival()
        if m < 0:
            rv = 'Expected %s ago' % format_minutes(abs(m))
        elif m > 0:
            rv = 'Arriving in %s' % format_minutes(m)
        return rv

    def upcoming_pickups_at_stop(self, offset):
        self._results.clear()
        for pu in self._stop.upcoming_pickups(offset):
            self._results.show(pu.trip.id, pu.trip.route.name, pu.trip.headsign, self._format_arrival(pu))

    def upcoming_stops_on_trip(self):
        self._results.clear()
        if self._trip:
            for pu in self._trip.next_pickups_from_now(5):
                self._results.show(pu.stop.id, pu.stop.label, pu.stop.number, pu.stop.name, self._format_arrival(pu))

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
        panel.stop_search()

class NextStateButton(gtk.Button):
    def __init__(self, panel):
        gtk.Button.__init__(self, None, 'gtk-execute')
        self.connect('clicked', self.act_click, panel)

    def act_click(self, w, panel):
        panel.next()

class LocationEntry(gtk.ComboBoxEntry):
    def __init__(self, panel):
        gtk.ComboBoxEntry.__init__(self)
        self.entry().connect('activate', self.act_activate, panel)

    def entry(self):
        return self.get_children()[0]

    def act_activate(self, w, panel):
        panel.stop_search()

class ResultsListModel(gtk.ListStore):
    def __init__(self, results):
        gtk.ListStore.__init__(self, int, str, str, str, str)
        results.set_realization(self)

    def append(self, *args):
        it = gtk.ListStore.append(self)
        [self.set(it, i, args[i]) for i in range(0, len(args))]
            
class MatchId(object):
    def __init__(self, id):
        self.id = id
        self.it = None

    def check(self, m, p, it):
        if self.id == m.get_value(it, 0):
            self.it = it
        return self.it is not None

class ResultsTreeView(gtk.TreeView):
    def __init__(self, results):
        gtk.TreeView.__init__(self, ResultsListModel(results))
        self.set_headers_visible(False)
        for i in range(1, self.get_model().get_n_columns()):
            self.append_column(gtk.TreeViewColumn('', gtk.CellRendererText(), markup=i))

    def find(self, id):
        rv = None
        if id:
            idm = MatchId(id)
            self.get_model().foreach(idm.check)
            rv = idm.it
        return rv

    def select_first(self):
        self.get_selection().select_path(0)

    def select_id(self, active_id):
        it = self.find(active_id)
        if it:
            self.get_selection().select_iter(it)
        else:
            self.select_first()

class State(object):
    def __init__(self, panel):
        self._panel = panel
        self._active = False

    def start(self):
        self._start_t = datetime.now()
        self._t = self._start_t
        self.update_on_start()
        self._timer_id = glib.timeout_add_seconds(60, self.timeout)
        self._active = True

    def finish(self):
        self.update_on_finish()
        glib.source_remove(self._timer_id)
        self._active = False

    def get_visibility(self):
        return (True, True)

    def get_info_text(self):
        return ''

    def get_details_text(self):
        return ''

    def get_active_id(self):
        return None

    def model(self):
        return self._panel.model()

    def minutes(self):
        td = self._t - self._start_t
        return (td.days * 1440) + (td.seconds / 60)

    def panel(self):
        return self._panel

    def next(self):
        self.finish()
        rv = self.next_class()(self._panel)
        rv.start()
        return rv

    def timeout(self):
        self._t = datetime.now()
        self.panel().change_text()
        self.update_on_timeout()
        return self._active

    def update_on_start(self):
        pass

    def update_on_finish(self):
        pass

    def update_on_timeout(self):
        pass

class Riding(State):
    def get_visibility(self):
        return (True, False)

    def _refresh_pickups(self):
        self.panel().upcoming_stops_on_trip()

    def update_on_start(self):
        self._refresh_pickups()

    def update_on_timeout(self):
        self._refresh_pickups()

    def update_on_finish(self):
        r = self.panel().selected_result()
        self.panel().model().set_stop(r[0])

    def get_info_text(self):
        ms = self.minutes() > 0 and ' for %s' % format_minutes(self.minutes()) or ''
        return 'Riding %s%s' % (self.panel().model().format_trip(), ms)

    def get_details_text(self):
        return 'Upcoming stops'

    def next_class(self):
        return WaitAtStop

class WaitForTrips(State):
    def get_visibility(self):
        return (True, False)

    def get_details_text(self):
        return 'Trips'

    def _refresh_pickups(self):
        self.panel().upcoming_pickups_at_stop(15)
    
    def update_on_start(self):
        self._refresh_pickups()

    def update_on_finish(self):
        r = self.panel().selected_result()
        self.panel().model().set_trip(r[0])

    def update_on_timeout(self):
        self._refresh_pickups()

class WaitForSelectedTrip(WaitForTrips):
    def get_info_text(self):
        ms = self.minutes() > 0 and ' for %s' % format_minutes(self.minutes()) or ''
        return 'Waiting for %s%s' % (self.panel().model().format_trip(), ms)

    def get_active_id(self):
        return self.panel().model().get_trip_id()

    def update_on_start(self):
        pass

    def next_class(self):
        return Riding

class WaitAtStop(WaitForTrips):
    def get_info_text(self):
        ms = self.minutes() > 0 and ' for %s' % format_minutes(self.minutes()) or ''
        return 'Waiting at %s%s' % (self.panel().model().format_stop(), ms)

    def next_class(self):
        return WaitForSelectedTrip

class SelectStop(State):
    def get_info_text(self):
        return 'Where are you now?'

    def get_details_text(self):
        return 'Stops'

    def update_on_finish(self):
        r = self.panel().selected_result()
        self.panel().model().set_stop(r[0])

    def next_class(self):
        return WaitAtStop

class Panel(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        self.set_title('voyageur')
        self.set_icon_from_file('icon.png')
        self.set_border_width(6)
        self.connect('destroy', self.act_quit)

        self._model = Model()
        self._state = SelectStop(self)
        self._state.start()

        self._build_contents()

    def _build_list(self):
        self._list = ResultsTreeView(self._model.results())

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self._list)

        al = gtk.Alignment(0.5, 0.5, 1.0, 1.0)
        al.set_padding(0, 6, 4, 4)
        al.add(sw)

        self._frame = gtk.Frame('')
        self._frame.add(al)

        return self._frame

    def _build_contents(self):
        vb = gtk.VBox(False, 4)

        self._info = InfoLabel('')
        vb.pack_start(self._info, False, True, 0)

        self._search_box = gtk.HBox(False, 8)

        self._location_entry = LocationEntry(self)
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

    def change_text(self):
        self._info.change_text(self._state.get_info_text())
        self._frame.set_label(self._state.get_details_text())
        
    def refresh(self):
        self.show_all()

        self.change_text()

        vis = self._state.get_visibility()
        if vis[0]:
            self._info.show_all()
        else:
            self._info.hide_all()
        if vis[1]:
            self._search_box.show_all()
        else:
            self._search_box.hide_all()

        self.select_active()

    def select_active(self):
        self._list.select_id(self._state.get_active_id())

    def selected_result(self):
        sel = self._list.get_selection()
        rv = None
        if sel:
            (m, it) = sel.get_selected()
            if it:
                rv = [m.get_value(it, i) for i in range(0, m.get_n_columns())]
        return rv

    def stop_search(self):
        self._model.stop_search(self.get_query_text())        
        self._list.select_first()

    def upcoming_pickups_at_stop(self, offset):
        self._model.upcoming_pickups_at_stop(offset)
        self.select_active()

    def upcoming_stops_on_trip(self):
        self._model.upcoming_stops_on_trip()
        self.select_active()

w = Panel()
w.refresh()
gtk.main()
