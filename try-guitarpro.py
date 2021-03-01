import guitarpro


demo = guitarpro.parse('./songbook/Johnny Cash - I Walk The Line (ver 5).gp5')
print(demo.artist)
print(demo.tracks)
for t in demo.tracks :
	print(t.name)

g = demo.tracks[1]
for s in g.strings :
	print(s)
print()

m = g.measures[0]
v = m.voices[0]
for b in v.beats :
	print(b.duration)
	for n in b.notes :
		print(n)
		print(n.string)
		print(n.value)
	print()
