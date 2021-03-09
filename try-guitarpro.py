import guitarpro


demo = guitarpro.parse('./songbook/daytripper_riff.gp5')
print(demo.artist)
print(demo.tracks)
print(demo.tempo)
#for mh in demo.measureHeaders:
#	print(mh.timeSignature)
for t in demo.tracks :
	print(t.name)
	print(t.channel)
	print(t.isPercussionTrack)

'''
g = demo.tracks[0]
for s in g.strings :
	print(s)
	print(s.number)
	print(s.value)
print()
print(g)
m = g.measures[2]
print(m.header.timeSignature)
print(m)
v = m.voices[0]
for b in v.beats :
	print(b.duration)
	print(b.notes)
	print()
'''