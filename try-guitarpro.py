import guitarpro


demo = guitarpro.parse('./songbook/Johnny Cash - I Walk The Line (ver 5).gp5')
print(demo.artist)
print(demo.tracks)
for t in demo.tracks :
	print(t.name)

g = demo.tracks[2]
for s in g.strings :
	print(s)
print()

m = g.measures[6]
for v in m.voices :
	for b in v.beats :
		print(b.notes)
		print(b.duration)
		print(b.status)
	print()
