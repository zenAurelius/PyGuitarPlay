import pygame
import guitarpro as gp
import mido
from mido import Message
import time


class Track:
	def __init__(self) :
		self.beats = []
		self.current_beat = 0
		self.from_last_beat = 0
		self.beats = []

class Guitarician :
	def __init__(self) :
		self.standard = [76,71,67,62,57,52]
		self.outport = None
		self.tracks = []

	def note_to_midi(self, note) :
		return self.standard[note.string - 1] + note.value

	def beat_on(self, beat, channel) :
		notes = [self.note_to_midi(n) for n in beat.notes]
		for n in notes:
			self.outport.send(Message('note_on', note=n, channel=channel, velocity=100, time=0))

	def beat_off(self, beat, channel) :
		notes = [self.note_to_midi(n) for n in beat.notes]
		for n in notes:
			self.outport.send(Message('note_off', note=n, channel=channel, velocity=100, time=0))

	def play_synchro(self, tick):
		ended = False
		for i, track in enumerate(self.tracks[2:3]) :
			# si on est on début => on démarre
			if track.current_beat == 0 :
				self.beat_on(track.beats[0], i)
			track.from_last_beat += tick
			if track.from_last_beat >= 2300 / int(track.beats[track.current_beat].duration.value) :
				self.beat_off(track.beats[track.current_beat], i)
				if track.current_beat < len(track.beats) - 1 :
					track.current_beat += 1
					track.from_last_beat = 0
					self.beat_on(track.beats[track.current_beat], i)
				else:
					ended = True
		return ended

	def start(self):
		pygame.init()

		disp = pygame.display.set_mode((800,600))
		pygame.display.set_caption('un test')

		clock = pygame.time.Clock()
		ended = False

		# Read file, get all notes, convert to something midi compatible
		song = gp.parse('./songbook/Johnny Cash - I Walk The Line (ver 5).gp5')
		for t in song.tracks:
			track = Track()
			for m in t.measures[0:6] :
				v = m.voices[0]
				for b in v.beats :
					track.beats.append(b)
			self.tracks.append(track)

		for b in self.tracks[1].beats :
			print(b.duration)
			print(b.notes)

		self.outport = mido.open_output()

		while not ended:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					ended = True

			if not ended:
				ended = self.play_synchro(clock.get_time())

			pygame.display.update()
			clock.tick(60)

		self.outport.close()
		pygame.quit()
		quit()

	
s = Guitarician()
s.start()
