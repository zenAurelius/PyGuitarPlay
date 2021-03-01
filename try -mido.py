import mido
from mido import Message, MidiFile, MidiTrack
import time
 
mid = MidiFile(type=1)
trackP = MidiTrack()
trackS = MidiTrack()
mid.tracks.append(trackP)
mid.tracks.append(trackS)

'''mid1 = MidiFile('./songbook/chiquita.mid')
for i, track in enumerate(mid1.tracks):
    print('Track {}: {}'.format(i, track.name))
    for msg in track:
        print(msg)'''
 
n = 24  # initialisation variable n avec note 24 = Do1
p = 0   # initialisation variable p avec program 0 = Grand Piano

while n < 36:  # boucle notes à jouer dans la gamme Chromatique 24 à 96 / Do1 à Do7
	print("Note", n)
	trackP.append(Message('program_change', channel=0, program=0, time=0))
	trackP.append(Message('note_on', note=n, channel=0, velocity=100, time=32))
	trackP.append(Message('note_off', note=n, channel=0, velocity=67, time=128))
	n = n +1  # incrémentation i (note)

n=24
while n < 36:  # boucle notes à jouer dans la gamme Chromatique 24 à 96 / Do1 à Do7
	print("Note", n)
	trackS.append(Message('program_change', channel=0, program=68, time=0))
	trackS.append(Message('note_on', note=n+12, channel=0, velocity=100, time=0))
	trackS.append(Message('note_off', note=n+12, channel=0, velocity=67, time=600))
	n = n +1  # incrémentation i (note)

outport = mido.open_output()
for track in mid.tracks:
	print(track)

for m in mid:
	print(m)

for m in mid.play():
	outport.send(m)


outport.close()