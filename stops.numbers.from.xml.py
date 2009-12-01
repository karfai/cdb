import lxml.etree
import schema
import chardet

class Update:
    def __init__(self):
        self.m = 0
        self.t = 0

    def update_stop(self, sch, in_id, ph_id, name):
        stop = sch.find_stop_by_label(in_id)
        if not stop:
            print '! not found (%s)' % (in_id)
            self.m += 1
        else:
            print '+ updating %s (%s)' % (stop.name, stop.label)
            stop.number = int(ph_id)
            stop.update()
        self.t += 1

sch = schema.Schema()
tr = lxml.etree.parse('stops.xml')
elems = tr.xpath('/stops/marker')
upd = Update()
[upd.update_stop(sch, e.get('stopid'), e.get('id'), e.get('name')) for e in elems]
print '+ committing'
sch.commit()

print '+ processed (total=%i; missed=%i)' % (upd.t, upd.m)
(una, a) = sch.get_stop_number_stat()
print '+ database (assigned=%i; empty=%i)' % (una, a)
