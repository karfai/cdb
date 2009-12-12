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

import re, threading, Queue
from datetime import *

import schema

# model elements
def format_minutes(m):
    rv = '%i minute%s' % (m, (m > 1) and 's' or '')
    return (m > 60) and '%i:%02i' % (m / 60, m % 60) or rv

def format_arrival(pu):
    rv = 'now'
    m = pu.minutes_until_arrival()
    if m < 0:
        rv = 'Expected %s ago' % format_minutes(abs(m))
    elif m > 0:
        rv = 'Arriving in %s' % format_minutes(m)
    return rv

def format_stop(stop):
    return '%s %s' % (str(stop.number).zfill(4), stop.name)

def format_trip(trip):
    return '%s %s' % (trip.route().name, trip.headsign)

class SchemaThread(threading.Thread):
    def __init__(self, q, e):
        threading.Thread.__init__(self)
        self._q = q
        self._e = e
        
    def run(self):
        self._store = schema.Schema()
        while not self._e.is_set():
            try:
                m = self._q.get(False, 1)
                if m is None:
                    break
                
                m.execute(self._store)
            except Queue.Empty:
                pass

class StoreRequest(object):
    def __init__(self, bridge, repeats=True):
        self._bridge = bridge
        self._repeats = repeats

    def _show(self, l, fn):
        self._bridge.show_start()
        [self._bridge.show(*fn(e)) for e in l]
        self._bridge.show_finish()

    def _show_info(self, o):
        self._bridge.show_info(o)

    def repeats(self):
        return self._repeats

class StopSearch(StoreRequest):
    def __init__(self, bridge, srch):
        super(StopSearch, self).__init__(bridge, False)
        self._srch = srch

    def execute(self, st):
        self._show(st.stop_search(self._srch),
                   lambda stop: [stop.id, str(stop.number).zfill(4), stop.name])

class UpcomingPickups(StoreRequest):
    def __init__(self, bridge, stop_id, offset):
        super(UpcomingPickups, self).__init__(bridge)
        self._stop_id = stop_id
        self._offset = offset

    def execute(self, st):
        stop = st.find_stop(self._stop_id)
        self._show_info(stop)
#        print "stop_id=%s; stop=%s" % (str(self._stop_id), str(stop))
        self._show([(pu, pu.trip()) for pu in stop.upcoming_pickups(self._offset)],
                   lambda (pu, tr): [tr.id, tr.route().name, tr.headsign, format_arrival(pu)])

class ShowTrip(StoreRequest):
    def __init__(self, bridge, trip_id):
        super(ShowTrip, self).__init__(bridge)
        self._trip_id = trip_id

    def execute(self, st):
        trip = st.find_trip(self._trip_id)
        self._show_info(trip)

class ShowStop(StoreRequest):
    def __init__(self, bridge, stop_id):
        super(ShowStop, self).__init__(bridge)
        self._stop_id = stop_id

    def execute(self, st):
        stop = st.find_stop(self._stop_id)
        self._show_info(stop)

class UpcomingStops(StoreRequest):
    def __init__(self, bridge, trip_id):
        super(UpcomingStops, self).__init__(bridge)
        self._trip_id = trip_id

    def execute(self, st):
        trip = st.find_trip(self._trip_id)
        self._show_info(trip)
        self._show([(pu, pu.stop()) for pu in trip.next_pickups_from_now(5)],
                   lambda (pu, st): [st.id, st.number, st.name, format_arrival(pu)])
            
class Bridge(object):
    def __init__(self, panel, tv):
        self._tv = tv
        self._panel = panel
        self._info_q = Queue.Queue(0)
        self._results_q = Queue.Queue(0)
        self._results_ready = threading.Event()

    def show_info(self, o):
#        print "info < %s" % str(o)
        self._info_q.put_nowait(o)

    def show_start(self):
        self._results_ready.clear()

    def show_finish(self):
        self._results_ready.set()
        self.enable()
        
    def show(self, *args):
        self._results_q.put_nowait(args)
        
    def clear(self):
        self._tv.get_model().clear()

    def disable(self):
        self._panel.disable()

    def enable(self):
        self._panel.enable()

    def poll_results(self):
        self._results_ready.wait()
        empty = False
        while not empty:
            try:
                args = self._results_q.get(False, 1)
                if args is None:
                    break
                
#                print "result"
                tm = self._tv.get_model()
                it = tm.append()
                [tm.set(it, i, args[i]) for i in range(0, len(args))]
            except Queue.Empty:
#                print "empty"
                empty = True

    def poll_info(self):
        try:
            o = self._info_q.get(False, 1)
#            print "info > %s" % str(o)
            self._panel.show_info(o)
        except Queue.Empty:
            pass
#            print "empty"
        
class Model(object):
    def __init__(self):
        self._q = Queue.Queue(0)
        self._e = threading.Event()
        self._th = SchemaThread(self._q, self._e)
        self._th.start()
        self._timer = None

    def _reschedule(self, t, a, expect_results=True):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(t, lambda : self._schedule(a, expect_results))
        self._timer.start()
        
    def _schedule(self, a, expect_results=True):
        if expect_results:
            self._bridge.clear()
            self._bridge.disable()

        self._q.put(a)
        if a.repeats():
            self._reschedule(60.0, a, expect_results)

    def kill_current_timer(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def set_bridge(self, br):
        self._bridge = br

    def set_stop(self, stop_id):
        self._stop_id = stop_id
            
    def set_trip(self, trip_id):
        self._trip_id = trip_id

    def get_trip_id(self):
        return self._trip_id

    def poll(self):
        self._bridge.poll_info()
        self._bridge.poll_results()
            
    def stop_search(self, s):
        self._schedule(StopSearch(self._bridge, s))

    def stop(self):
        self._e.set()
        self._th.join()
        if self._timer:
            self._timer.cancel()

    def upcoming_pickups_at_stop(self, offset):
        self._schedule(UpcomingPickups(self._bridge, self._stop_id, offset))

    def upcoming_stops_on_trip(self):
        self._schedule(UpcomingStops(self._bridge, self._trip_id))

    def show_current_stop(self):
        self._schedule(ShowStop(self._bridge, self._stop_id), False)

    def show_current_trip(self):
        self._schedule(ShowTrip(self._bridge, self._trip_id), False)

    def bridge(self):
        return self._bridge

# GUI (view/control) elements

# there is only ever a Panel which is re-built depending on state
class InfoLabel(gtk.Label):
    def __init__(self, text):
        gtk.Label.__init__(self, None)
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

class State(object):
    def __init__(self, panel):
        self._panel = panel
        self._active = False

    def start(self):
        self._start_t = datetime.now()
        self._t = self._start_t
        self.update_on_start()
        self._active = True

    def active(self):
        pass

    def finish(self, index):
        self._panel.model().kill_current_timer()
        self.update_on_finish(index)
        self._active = False

    def get_visibility(self):
        return (True, True)

    def get_details_text(self):
        return ''

    def get_active_id(self):
        return None

    def model(self):
        return self._panel.model()

    def minutes(self):
        td = datetime.now() - self._start_t
        return (td.days * 1440) + (td.seconds / 60)

    def panel(self):
        return self._panel

    def next(self, index):
        self.finish(index)
        cl = [ex[1] for ex in self.exits()][index]
        rv = cl(self._panel)
        rv.start()
        return rv

    def update_on_start(self):
        pass

    def update_on_finish(self, exit_index):
        pass

class Riding(State):
    def get_visibility(self):
        return (True, False)

    def _refresh_pickups(self):
        self.panel().upcoming_stops_on_trip()

    def update_on_start(self):
        self._refresh_pickups()

    def update_on_finish(self, exit_index):
        r = self.panel().selected_result()
        self.panel().model().set_stop(r[0])

    def get_info_text(self, tr):
        ms = self.minutes() > 0 and ' for %s' % format_minutes(self.minutes()) or ''
        return '%s%s' % (format_trip(tr), ms)

    def get_details_text(self):
        return 'Upcoming stops'

    def exits(self):
        return [('Get off', WaitAtStop)]

class WaitAtStop(State):
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
        if exit_index == 0:
            self.panel().model().set_trip(r[0])

    def get_info_text(self, stop):
        ms = self.minutes() > 0 and ' for %s' % format_minutes(self.minutes()) or ''
        return '%s%s' % (format_stop(stop), ms)

    def exits(self):
        return [
            ('Get on this bus', Riding),
            ('End the trip', SelectStop),
        ]

class SelectStop(State):
    def get_info_text(self, o):
        return 'Where are you now?'

    def get_details_text(self):
        return 'Stops'

    def active(self):
        super(SelectStop, self).active()
        self.panel().show_info()


    def update_on_start(self):
        self.panel().clear_results()

    def update_on_finish(self, exit_index):
        r = self.panel().selected_result()
        self.panel().model().set_stop(r[0])

    def exits(self):
        return [('Wait for buses', WaitAtStop)]

class ResultsListModel(gtk.ListStore):
    def __init__(self):
        gtk.ListStore.__init__(self, int, str, str, str, str)
            
class MatchId(object):
    def __init__(self, id):
        self.id = id
        self.it = None

    def check(self, m, p, it):
        if self.id == m.get_value(it, 0):
            self.it = it
        return self.it is not None

class ResultsTreeView(gtk.TreeView):
    def __init__(self, panel):
        gtk.TreeView.__init__(self, ResultsListModel())
        self._panel = panel
        self.set_headers_visible(False)
        for i in range(1, self.get_model().get_n_columns()):
            self.append_column(gtk.TreeViewColumn('', gtk.CellRendererText(), markup=i))

        self.connect("notify::sensitive", self.act_notify)

    def find(self, id):
        rv = None
        if id:
            idm = MatchId(id)
            self.get_model().foreach(idm.check)
            rv = idm.it
        return rv

    def select_first(self):
        self.get_selection().select_path(0)

    def select(self, it):
        self.get_selection().select_iter(it)

    def select_id(self, active_id):
        it = self.find(active_id)
        if it:
            self.select(it)
        else:
            self.select_first()

    def act_notify(self, w, spec):
        if w.get_property('sensitive'):
            self._panel.poll()

class Panel(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        self.set_title('voyageur')
        self.set_icon_from_file('icon.png')
        self.set_border_width(6)
        self.connect('destroy', self.act_quit)

        self._model = Model()
        self._state = SelectStop(self)

        self._build_contents()
        self._model.set_bridge(Bridge(self, self._list))
        self._state.start()
        self.show_info()

    def _build_list(self):
        self._list = ResultsTreeView(self)
        self._list.get_selection().connect('changed', self.act_selection)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self._list)

        self._details = gtk.Label('More details....')

        vbox = gtk.VBox(False, 2)
        vbox.pack_start(sw, True, True, 0)
#        vbox.pack_end(self._details, False, True, 0)

        al = gtk.Alignment(0.5, 0.5, 1.0, 1.0)
        al.set_padding(0, 6, 4, 4)
        al.add(vbox)

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
        self._model.stop()
        gtk.main_quit()        

    def act_selection(self, sel):
        self.enable_exits()

    def get_query_text(self):
        return self._loc.get_active_text()

    def model(self):
        return self._model

    def next(self, index):
#        print "next"
        self._state = self._state.next(index)
        self._state.active()
#        print "refresh"
        self.refresh()
#        print "refreshed"

    def disable(self):
        self._list.set_sensitive(False)
        self._info.set_sensitive(False)

    def enable(self):
        self._list.set_sensitive(True)
        self._info.set_sensitive(True)

    def enable_exits(self):
        sel = (self._list.get_selection().count_selected_rows() > 0)
        [w.set_sensitive(sel) for w in self._exits.get_children()]

    def change_exits(self):
        [self._exits.remove(w) for w in self._exits.get_children()]
        ex = self._state.exits()
        [self._exits.add(NextStateButton(ex[i][0], self, i)) for i in range(0, len(ex))]
        self._exits.show_all()

    def show_info(self, o=None):
        self._info.change_text(self._state.get_info_text(o))
        self._frame.set_label(self._state.get_details_text())

    def clear_results(self):
        self._loc.clear()
        self._list.get_model().clear()

    def poll(self):
        self.model().poll()
        self.select_active()
        
    def refresh(self):
        self.show_all()

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

    def upcoming_pickups_at_stop(self, offset):
        self._model.upcoming_pickups_at_stop(offset)

    def upcoming_stops_on_trip(self):
        self._model.upcoming_stops_on_trip()

gtk.gdk.threads_init()
w = Panel()
w.refresh()
gtk.main()
