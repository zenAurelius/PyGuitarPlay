import mido
from mido import Message, MidiFile, MidiTrack
import time
 
mid1 = MidiFile('./songbook/test.mid')
for i, track in enumerate(mid1.tracks):
    print('Track {}: {}'.format(i, track.name))
    for msg in track:
        print(msg)