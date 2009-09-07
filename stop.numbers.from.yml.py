from __future__ import with_statement
import sys
import yaml
import schema

tbl = {}
st = schema.create_store()

stops = yaml.load(file(sys.argv[1], 'rb'))
for stop in stops:
    n = unicode(stop[':name'])
    if n not in tbl:
        tbl[n] = []
    tbl[n].append(int(stop[':number']))
    # if len(matches) > 1:
    #     print 'collision: %s' % (n)

print len(tbl)
print len([n for n in tbl if len(tbl[n]) > 1])

for n in tbl:
    matches = [s for s in st.find(schema.Stop, schema.Stop.name == n)]
    i = 0
    if len(tbl[n]) != len(matches):
        print '%s: %s' % (n, (len(tbl[n]), len(matches)))
    for stop in matches:
        if i < len(tbl[n]):
            stop.number = tbl[n][i]
        i += 1
st.commit()
