import pygame
import guitarpro as gp
import mido
from mido import Message
import time

TICKS_PER_MEASURE = 120
class Track:
	def __init__(self, gp_track) :
		self.beats = []
		self.current_beat = 0
		self.tuning = [s.value for s in gp_track.strings]
		self.channel = gp_track.channel
		self.track = gp_track
		self.beats_in_mesure = []
		self.set_beats_in_mesure(0)
		self.notes_on = []

	def set_beats_in_mesure(self, m) :
		ticks = 0
		self.beats_in_mesure = []
		#print("mesure : " + str(m))
		for b in self.get_measure(m).voices[0].beats :
			tick_duration = TICKS_PER_MEASURE / b.duration.value
			if b.duration.isDotted:
				 tick_duration += tick_duration / 2
			ticks += tick_duration
			self.beats_in_mesure.append(ticks)
			#print(b.duration)
			#print(b.notes)
		print(self.beats_in_mesure)

	def get_nb_measures(self):
		return len(self.track.measures)

	def get_measure(self, m):
		return self.track.measures[m]

	def get_beats_in_measure(self, m) :
		return self.get_measure(m).voices[0].beats

	def get_next_beat_notes(self, m) :
		next_id = self.current_beat + 1
		if next_id == len (self.get_measure(m).voices[0].beats) :
			if m +1 == self.get_nb_measures() :
				return None
			else :
				return self.note_to_midi(self.get_measure(m+1).voices[0].beats[0].notes)
		else:
			return self.note_to_midi(self.get_measure(m).voices[0].beats[next_id].notes)

	def get_beat(self, m) :
		return self.get_measure(m).voices[0].beats[self.current_beat]

	def note_to_midi(self, notes) :
		return [{'value':(self.tuning[note.string - 1] + note.value), 'type':note.type, 'string': note.string} for note in notes]

	def get_beat_notes(self, m):
		return [{'value':(self.tuning[note.string - 1] + note.value), 'type':note.type, 'string': note.string} for note in self.get_beat(m).notes]


class Guitarician :
	def __init__(self) :
		self.outport = None
		self.tracks = []
		self.time_in_mesure = 0
		self.current_measure = 0
		self.measure_started = False
		self.is_playing = False
		self.ticks_per_ms = 20
		self.tempo = 0
		self.tempo_modifier = 1.0

	def beat_on(self, track, channel) :
		#print(track.get_beat_notes(self.current_measure))
		for n in track.get_beat_notes(self.current_measure) :
			if n['type'] != gp.NoteType.tie :
				self.outport.send(Message('note_on', note=n['value'], channel=channel, velocity=track.channel.volume, time=0))
				track.notes_on.append(n)
			

	def beat_off(self, track, channel) :
		next_notes = track.get_next_beat_notes(self.current_measure)
		notes_off = []
		print(next_notes)
		for n in track.notes_on :
			#print(n)
			if next_notes :
				tie = next((note for note in next_notes if note['string'] == n['string'] and note['type'] == gp.NoteType.tie), None)
			else :
				tie = None
			#print(tie)
			if tie == None :
				self.outport.send(Message('note_off', note=n['value'], channel=channel, velocity=0, time=0))
				notes_off.append(n)
		for n in notes_off :
			track.notes_on.remove(n)
		#print(track.notes_on)

	def play_synchro(self):
		if not self.is_playing :
			return False
		ended = False
		for i, track in enumerate(self.tracks) :
			ticks_in_mesure = int(self.time_in_mesure / self.ticks_per_ms)
			#print(ticks_in_mesure)
			
			if not self.measure_started :
				print('mesure ' + str(self.current_measure))
				self.beat_on(track, i)
			
			if track.beats_in_mesure[track.current_beat] <= ticks_in_mesure :
				self.beat_off(track, i)
				if track.current_beat < len(track.get_beats_in_measure(self.current_measure)) - 1 :
					track.current_beat += 1
					self.beat_on(track, i)

		self.measure_started = True
		if(ticks_in_mesure >= TICKS_PER_MEASURE):	
			self.current_measure += 1
			if self.current_measure == self.tracks[0].get_nb_measures() :
				ended = True
			else :
				for t in self.tracks :
					t.set_beats_in_mesure(self.current_measure)
					t.current_beat = 0
					self.time_in_mesure = 0
					self.measure_started = False
		return ended

	def start(self):
		pygame.init()

		disp = pygame.display.set_mode((800,600))
		pygame.display.set_caption('un test')

		clock = pygame.time.Clock()
		ended = False

		self.outport = mido.open_output()

		# Read file, get all notes, convert to something midi compatible
		song = gp.parse('./songbook/daytripper_riff.gp5')
		self.tempo = song.tempo
		self.ticks_per_ms = 2000 / self.tempo
		for i, t in enumerate(song.tracks):
			track = Track(t)
			self.tracks.append(track)
			self.outport.send(Message('program_change', channel=i, program=track.channel.instrument))

		while not ended:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					ended = True
				if event.type == pygame.KEYDOWN:
					print(event.key)
					if event.key == pygame.K_KP_MINUS :
						print('slow')
						self.tempo_modifier -= 0.1
						self.ticks_per_ms = 2000 / (self.tempo * self.tempo_modifier)
					elif event.key == pygame.K_KP_PLUS :
						print('slow')
						self.tempo_modifier += 0.1
						self.ticks_per_ms = 2000 / (self.tempo * self.tempo_modifier)
					else:
						self.is_playing = True

			if not ended:
				#print(self.is_playing)
				if self.is_playing :
					self.time_in_mesure += clock.get_time()
				#print(clock.get_time())
				#print(self.time_in_mesure)
				ended = self.play_synchro()

			pygame.display.update()
			clock.tick(60)

		self.outport.close()
		pygame.quit()
		quit()

	
s = Guitarician()
s.start()
