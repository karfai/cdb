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
import gtk
import hildon

import re
from datetime import *

import schema

# model elements
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
        self._store = schema.Schema()
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
        return '%s %s' % (self._trip.route().name, self._trip.headsign)

    def set_stop(self, stop_id):
        self._stop = self._store.find_stop(stop_id)
            
    def set_trip(self, trip_id):
        self._trip = self._store.find_trip(trip_id)

    def get_trip_id(self):
        rv = None
        if self._trip:
            rv = self._trip.id
        return rv
            
    def stop_search(self, s):
        self._show_stops(self._store.stop_search(s))

    def _format_arrival(self, pu):
        rv = 'now'
        m = pu.minutes_until_arrival()
        if m < 0:
            rv = 'Expected %s ago' % format_minutes(abs(m))
        elif m > 0:
            rv = 'Arriving in %s' % format_minutes(m)
        return rv

    def upcoming_pickups_at_stop(self, offset):
        b = hildon.hildon_banner_show_animation(w, None, 'Next')
        b.show()
        self._results.clear()
        for pu in self._stop.upcoming_pickups(offset):
            tr = pu.trip()
            self._results.show(tr.id, tr.route().name, tr.headsign, self._format_arrival(pu))
        b.destroy()

    def upcoming_stops_on_trip(self):
        b = hildon.hildon_banner_show_animation(w, None, 'Next')
        b.show()
        self._results.clear()
        if self._trip:
            for pu in self._trip.next_pickups_from_now(5):
                st = pu.stop()
                self._results.show(st.id, st.label, st.number, st.name, self._format_arrival(pu))
        b.destroy()

    def results(self):
        return self._results

# GUI (view/control) elements

# there is only ever a Panel which is re-built depending on state
class InfoLabel(gtk.Label):
    def __init__(self, text):
        gtk.Label.__init__(self, '')
        self.set_property('xalign', 0.0)

    def change_text(self, text):
        self.set_markup('<span size="x-large">%s</span>' % text)
        
class FindButton(gtk.Button):
    def __init__(self, panel, loc):
        gtk.Button.__init__(self, None, 'gtk-find')
        self.connect('clicked', self.act_click, panel, loc)

    def act_click(self, w, panel, loc):
        loc.store_current()
        panel.stop_search()

class NextStateButton(gtk.Button):
    def __init__(self, label, panel, index):
        gtk.Button.__init__(self, label)
        self.connect('clicked', self.act_click, panel, index)

    def act_click(self, w, panel, index):
        panel.next(index)

class LocationEntry(gtk.ComboBoxEntry):
    def __init__(self, panel):
        gtk.ComboBoxEntry.__init__(self)
        self.set_model(gtk.ListStore(str))
        self.set_text_column(0)
        self.entry().connect('activate', self.act_activate, panel)
        self.connect('changed', self.act_changed, panel)
        self._active = self.get_active()
    
    def clear(self):
        self.entry().set_text('')

    def entry(self):
        return self.get_children()[0]

    def store_current(self):
        self.append_text(self.entry().get_text())
        
    def act_changed(self, w, panel):
        if self._active != w.get_active():
            self._active = w.get_active()
            panel.stop_search()

    def act_activate(self, w, panel):
        self.store_current()
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
#        self._timer_id = gtk.timeout_add_seconds(60, self.timeout)
        self._active = True

    def finish(self, index):
        self.update_on_finish(index)
#        glib.source_remove(self._timer_id)
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

    def next(self, index):
        self.finish(index)
        cl = [ex[1] for ex in self.exits()][index]
        rv = cl(self._panel)
        rv.start()
        return rv

    def timeout(self):
        self._t = datetime.now()
        self.panel().change_text()
        self.update_on_timeout()
        return self._active

    def update_on_start(self):
        pass

    def update_on_finish(self, exit_index):
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

    def update_on_finish(self, exit_index):
        r = self.panel().selected_result()
        self.panel().model().set_stop(r[0])

    def get_info_text(self):
        ms = self.minutes() > 0 and ' for %s' % format_minutes(self.minutes()) or ''
        return 'Riding %s%s' % (self.panel().model().format_trip(), ms)

    def get_details_text(self):
        return 'Upcoming stops'

    def exits(self):
        return [('Get off', WaitAtStop)]

class WaitForTrips(State):
    def get_visibility(self):
        return (True, False)

    def get_details_text(self):
        return 'Trips'

    def _refresh_pickups(self):
        self.panel().upcoming_pickups_at_stop(15)
    
    def update_on_start(self):
        self._refresh_pickups()

    def update_on_finish(self, exit_index):
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

    def exits(self):
        return [
            ('Get on', Riding),
            ('Different bus', WaitAtStop),
        ]

class WaitAtStop(WaitForTrips):
    def get_info_text(self):
        ms = self.minutes() > 0 and ' for %s' % format_minutes(self.minutes()) or ''
        return 'Waiting at %s%s' % (self.panel().model().format_stop(), ms)

    def exits(self):
        return [
            ('Wait for this bus', WaitForSelectedTrip),
            ('End the trip', SelectStop),
        ]

class SelectStop(State):
    def get_info_text(self):
        return 'Where are you now?'

    def get_details_text(self):
        return 'Stops'

    def update_on_start(self):
        self.panel().clear_results()

    def update_on_finish(self, exit_index):
        r = self.panel().selected_result()
        self.panel().model().set_stop(r[0])

    def exits(self):
        return [('Wait for buses', WaitAtStop)]

class Panel(hildon.Window):
    def __init__(self):
        hildon.Window.__init__(self)

        self.set_title('voyageur')
        self.set_icon_from_file('icon.png')
        self.set_border_width(6)
        self.connect('destroy', self.act_quit)
        self.connect('key-press-event', self.act_key)
        self.connect('window-state-event', self.act_state)

        self._model = Model()
        self._state = SelectStop(self)

        self._build_contents()
        self._state.start()

    def _build_list(self):
        self._list = ResultsTreeView(self._model.results())
        self._list.get_selection().connect('changed', self.act_selection)
        

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

        self._loc = LocationEntry(self)
        self._search_box.pack_start(self._loc, True, True, 0)

        hb = gtk.HBox(False, 2)
        hb.pack_start(FindButton(self, self._loc), True, True, 0)
        hb.pack_start(gtk.Button('GPS'), True, True, 0)
        self._search_box.pack_start(hb, True, True, 0)

        vb.pack_start(self._search_box, False, True, 0)
        vb.pack_start(self._build_list(), True, True, 0)

        self._exits = gtk.HButtonBox()
        self._exits.set_layout(gtk.BUTTONBOX_SPREAD)
        vb.pack_start(self._exits, False, True, 0)

        self.add(vb)

    def act_quit(self, w):
        gtk.main_quit()        

    def act_selection(self, sel):
        self.enable_exits()

    def act_key(self, w, evt, *args):
        if evt.keyval == gtk.keysyms.F6:
            if self.window_in_fullscreen:
                self.unfullscreen()
            else:
                self.fullscreen()

    def act_state(self, w, evt, *args):
        if evt.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self.window_in_fullscreen = True
        else:
            self.window_in_fullscreen = False

    def get_query_text(self):
        return self._loc.get_active_text()

    def model(self):
        return self._model

    def next(self, index):
        self._state = self._state.next(index)
        self.refresh()

    def enable_exits(self):
        sel = (self._list.get_selection().count_selected_rows() > 0)
        [w.set_sensitive(sel) for w in self._exits.get_children()]

    def change_exits(self):
        [self._exits.remove(w) for w in self._exits.get_children()]
        ex = self._state.exits()
        [self._exits.add(NextStateButton(ex[i][0], self, i)) for i in range(0, len(ex))]
        self._exits.show_all()

    def change_text(self):
        self._info.change_text(self._state.get_info_text())
        self._frame.set_label(self._state.get_details_text())

    def clear_results(self):
        self._loc.clear()
        self._list.get_model().clear()
        
    def refresh(self):
        self.show_all()

        self.change_text()
        self.change_exits()
        self.enable_exits()

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

app = hildon.Program()
w = Panel()
app.add_window(w)
w.refresh()
gtk.main()