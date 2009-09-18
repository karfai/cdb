import unittest

from schema import *

class TestingSchema(Schema):
    def __init__(self):
        super(TestingSchema, self).__init__()
        self.ct = None
        
    def current_time(self):
        return self.ct

class TestBase(unittest.TestCase):
    def setUp(self):
        self.sc = TestingSchema()

    def tearDown(self):
        pass

class Find(TestBase):
    def test_find_stop(self):
        expectations = {
            50  : [50,  unicode('AB060'), 7032, unicode('GENEST / MARIER'),    45.441139, -75.669495],
            200 : [200, unicode('AD720'), 7118, unicode('COVENTRY / AD. 360'), 45.421303, -75.649376],
            300 : [300, unicode('AF950'), 0,    unicode('HURDMAN 2B'),         45.411846, -75.665421],
        }
        for stop_id in expectations:
            st = self.sc.find_stop(stop_id)
            self.assertNotEqual(None, st, 'failed to find stop with id=%i' % (stop_id))
            self.assertEqual(expectations[stop_id][0], st.id)
            self.assertEqual(expectations[stop_id][1], st.label)
            self.assertEqual(expectations[stop_id][2], st.number)
            self.assertEqual(expectations[stop_id][3], st.name)
            self.assertEqual(expectations[stop_id][4], st.lat)
            self.assertEqual(expectations[stop_id][5], st.lon)

    def test_find_trip(self):
        expectations = {
            50  : [50,  unicode('Gatineau / Hull'), 1488285,  130,  4],
            200 : [200, unicode('Baseline'),        1488035,  142,  4],
            222 : [222, unicode('South Keys'),      1487942,  142,  4],
        }
        for trip_id in expectations:
            tr = self.sc.find_trip(trip_id)
            self.assertNotEqual(None, tr, 'failed to find trip with id=%i' % (trip_id))
            self.assertEqual(expectations[trip_id][0], tr.id)
            self.assertEqual(expectations[trip_id][1], tr.headsign)
            self.assertEqual(expectations[trip_id][2], tr.block)
            self.assertEqual(expectations[trip_id][3], tr.route_id)
            self.assertEqual(expectations[trip_id][4], tr.service_period_id)

    def test_find_service_exception(self):
        expectations = {
            733657 : [1, 733657, 1, 5],
            733692 : [2, 733692, 1, 5],
        }
        for day in expectations:
            se = self.sc.find_service_exception(day)
            self.assertNotEqual(None, se, 'failed to find service_exception with id=%i' % (day))
            self.assertEqual(expectations[day][0], se.id)
            self.assertEqual(expectations[day][1], se.day)
            self.assertEqual(expectations[day][2], se.exception_type)
            self.assertEqual(expectations[day][3], se.service_period_id)

    def test_current_service_period(self):
        # set the date time arbitrarily that we know will match a single exception
        self.sc.ct = datetime(2009, 9, 17, 20, 4, 33)
        sp = self.sc.current_service_period()
        self.assertNotEqual(None, sp)
        self.assertEqual(6, sp.id)
        self.assertEqual(31, sp.days)
        self.assertEqual(733658, sp.start)
        self.assertEqual(733721, sp.finish)

        # 2009-09-07 was Labour Day, an exception which yields a different period / Sunday service
        self.sc.ct = datetime(2009, 9, 7, 0, 0, 0)
        sp = self.sc.current_service_period()
        self.assertNotEqual(None, sp)
        self.assertEqual(5, sp.id)
        self.assertEqual(64, sp.days)
        self.assertEqual(733656, sp.start)
        self.assertEqual(733719, sp.finish)

def verifyTrip(tc, ex, ac):
    tc.assertNotEqual(None, ac)
    tc.assertEqual(ex.id, ac.id)
    tc.assertEqual(ex.headsign, ac.headsign)
    tc.assertEqual(ex.block, ac.block)
    tc.assertEqual(ex.route_id, ac.route_id)
    tc.assertEqual(ex.service_period_id, ac.service_period_id)
        
def verifyStop(tc, ex, ac):
    tc.assertNotEqual(None, ac)
    tc.assertEqual(ex.id, ac.id)
    tc.assertEqual(ex.label, ac.label)
    tc.assertEqual(ex.number, ac.number)
    tc.assertEqual(ex.name, ac.name)
    tc.assertEqual(ex.lat, ac.lat)
    tc.assertEqual(ex.lon, ac.lon)
        
class PickupRelations(TestBase):
    def test_stop_trips(self):
        # pick a stop we know about
        st = self.sc.find_stop(50)
        tr = st.trips()
        self.assertEqual(274, len(tr))
        # sample a few
        expectations = {
            0  : [449,  unicode('St Laurent'), 1488068, 9, 4],
            1  : [2587, unicode('St Laurent'), 1488037, 9, 4],
            2  : [2744, unicode('St Laurent'), 1488103, 9, 4],
        }

        for i in expectations:
            self.assertEqual(expectations[i][0], tr[i].id)
            self.assertEqual(expectations[i][1], tr[i].headsign)
            self.assertEqual(expectations[i][2], tr[i].block)
            self.assertEqual(expectations[i][3], tr[i].route_id)
            self.assertEqual(expectations[i][4], tr[i].service_period_id)

    def test_trip_stops(self):
        # pick a trip we know about
        tr = self.sc.find_trip(449)
        st = tr.stops()
        self.assertEqual(94, len(st))
        # sample a few
        expectations = {
            0 : [3222, unicode('RA945'), 0, unicode('BILLINGS BRIDGE 4C'), 45.384583, -75.677002],
            1 : [3168, unicode('RA030'), 8298, unicode('BANK / RIVERSIDE'), 45.38776, -75.67569],
            2 : [3166, unicode('RA010'), 4100, unicode('BANK / RIVERSIDE'), 45.388786, -75.67704],
        }
        for i in expectations:
            self.assertEqual(expectations[i][0], st[i].id)
            self.assertEqual(expectations[i][1], st[i].label)
            self.assertEqual(expectations[i][2], st[i].number)
            self.assertEqual(expectations[i][3], st[i].name)
            self.assertEqual(expectations[i][4], st[i].lat)
            self.assertEqual(expectations[i][5], st[i].lon)

    def test_stop_pickups(self):
        # pick a stop we know about
        st = self.sc.find_stop(50)
        pk = st.pickups()
        self.assertEqual(274, len(pk))
        # sample a few
        expectations = {
            0 : [20783, 26520, 26520, 50, 449, 50],
            1 : [136084, 31080, 31080, 48, 2587, 50],
            2 : [141846, 66600, 66600, 48, 2744, 50],

        }
        for i in expectations:
            self.assertEqual(expectations[i][0], pk[i].id)
            self.assertEqual(expectations[i][1], pk[i].arrival)
            self.assertEqual(expectations[i][2], pk[i].departure)
            self.assertEqual(expectations[i][3], pk[i].sequence )
            self.assertEqual(expectations[i][4], pk[i].trip_id)
            self.assertEqual(expectations[i][5], pk[i].stop_id)

            # verify back
            verifyStop(self, st, pk[i].stop())

    def test_trip_pickups(self):
        # pick a trip we know about
        tr = self.sc.find_trip(449)
        pk = tr.pickups()
        self.assertEqual(94, len(pk))
        # sample a few
        expectations = {
            0 : [20734, 24180, 24180, 1, 449, 3222],
            1 : [20735, 24240, 24240, 2, 449, 3168],
            2 : [20736, 24300, 24300, 3, 449, 3166],
        }
        for i in expectations:
            self.assertEqual(expectations[i][0], pk[i].id)
            self.assertEqual(expectations[i][1], pk[i].arrival)
            self.assertEqual(expectations[i][2], pk[i].departure)
            self.assertEqual(expectations[i][3], pk[i].sequence )
            self.assertEqual(expectations[i][4], pk[i].trip_id)
            self.assertEqual(expectations[i][5], pk[i].stop_id)
            # verify back
            verifyTrip(self, tr, pk[i].trip())

class TripRoute(TestBase):
    def test_route(self):
        # pick a trip we know about
        rt = self.sc.find_trip(449).route()
        self.assertNotEqual(None, rt)
        self.assertEqual(9, rt.id)
        self.assertEqual(unicode('5'), rt.name)
        self.assertEqual(3, rt.type)

        self.assertTrue(449 in [tr.id for tr in rt.trips()])
        
class StopSearch(TestBase):
    def test_intersection(self):
        expectations = {
            'GENEst and mariER' : [50, 51],
            'GENEst and mariER' : [50, 51],
            'GENEst / mariER' : [50, 51],
            'GENEst / mariER' : [50, 51],
        }
        for s in expectations:
            r = self.sc.stop_search(s)
            self.assertNotEqual(None, r)
            self.assertEqual(len(expectations[s]), len(r))
            for id in expectations[s]:
                self.assertTrue(id in [st.id for st in r])

    def test_number(self):
        expectations = {
            '2350' : [2932],
            '4817' : [2819],
        }
        for s in expectations:
            r = self.sc.stop_search(s)
            self.assertNotEqual(None, r)
            self.assertEqual(len(expectations[s]), len(r))
            for id in expectations[s]:
                self.assertTrue(id in [st.id for st in r])

    def test_label(self):
        expectations = {
            'nG010' : [2932],
            'Ne020' : [2819],
        }
        for s in expectations:
            r = self.sc.stop_search(s)
            self.assertNotEqual(None, r)
            self.assertEqual(len(expectations[s]), len(r))
            for id in expectations[s]:
                self.assertTrue(id in [st.id for st in r])

    def test_any(self):
        expectations = {
            'GENEst'  : [48, 49, 50, 51],
            'gENEst'  : [48, 49, 50, 51],
            'GENESt'  : [48, 49, 50, 51],
            'coldrey' : [2834, 2858, 2860, 2863],
            'COLdrey' : [2834, 2858, 2860, 2863],
        }
        for s in expectations:
            r = self.sc.stop_search(s)
            self.assertNotEqual(None, r)
            self.assertEqual(len(expectations[s]), len(r))
            for id in expectations[s]:
                self.assertTrue(id in [st.id for st in r])
