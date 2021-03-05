import pygame
import guitarpro as gp
import mido
from mido import Message
import time

TICKS_PER_MEASURE = 120

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
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
		self.measures = []
		self.notes = []
		for i, m in enumerate(gp_track.measures) :
			self.measures.append({'num': i, 'notes':[]})
			ticks = 0
			for b in m.voices[0].beats:
				tick_top = ticks
				tick_duration = TICKS_PER_MEASURE / b.duration.value
				if b.duration.isDotted:
					tick_duration += tick_duration / 2
				tick_end = tick_top + tick_duration
				for n in b.notes : 
					if n.type == gp.NoteType.tie :
						p_note = self.get_previous_note(i, n.string)
						p_note['tick_stop'] = tick_end + i * TICKS_PER_MEASURE
					note = self.note_to_midi(n)
					note['tick_start'] = tick_top + i * TICKS_PER_MEASURE
					note['tick_stop'] = tick_end + i * TICKS_PER_MEASURE
					self.measures[i]['notes'].append(note)
				ticks = tick_end
		# repassage pour lier les notes 'tie'
		#for i,m in enumerate(self.measures) :

	def get_previous_note(self, measure, string):
		for nm in range(measure, -1, -1) :
			notes = reversed(self.measures[nm]['notes'])
			note = next((note for note in notes if note['string'] ==string), None)
			if note != None :
				return note
		return None


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
		#print(self.beats_in_mesure)

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
				return self.notes_to_midi(self.get_measure(m+1).voices[0].beats[0].notes)
		else:
			return self.notes_to_midi(self.get_measure(m).voices[0].beats[next_id].notes)

	def get_measures_notes(self, m_start, m_end) :
		notes = []
		for m in range(m_start, m_end) :
			if m < 0 or m > len(self.track.measures) -1 :
				continue
			
	def get_beat(self, m) :
		return self.get_measure(m).voices[0].beats[self.current_beat]

	def notes_to_midi(self, notes) :
		return [{'value':(self.tuning[note.string - 1] + note.value), 'type':note.type, 'string': note.string} for note in notes]

	def note_to_midi(self, note) :
		return {'value':(self.tuning[note.string - 1] + note.value), 'type':note.type, 'string': note.string, 'fret':note.value}

	def get_beat_notes(self, m):
		return [{'value':(self.tuning[note.string - 1] + note.value), 'type':note.type, 'string': note.string} for note in self.get_beat(m).notes]


class Guitarician :
	def __init__(self) :
		self.outport = None
		self.tracks = []
		self.time_in_mesure = 0
		self.time_in_song = 0
		self.current_measure = 0
		self.measure_started = False
		self.is_playing = False
		self.ticks_per_ms = 20
		self.tempo = 0
		self.tempo_modifier = 1.0
		self.main_track = None

	def beat_on(self, track, channel) :
		#print(track.get_beat_notes(self.current_measure))
		for n in track.get_beat_notes(self.current_measure) :
			if n['type'] != gp.NoteType.tie :
				self.outport.send(Message('note_on', note=n['value'], channel=channel, velocity=track.channel.volume, time=0))
				track.notes_on.append(n)
			

	def beat_off(self, track, channel) :
		next_notes = track.get_next_beat_notes(self.current_measure)
		notes_off = []
		#print(next_notes)
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
				for n in self.main_track.measures[self.current_measure]['notes'] : 
					print(n)
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

		screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
		pygame.display.set_caption('un test')

		clock = pygame.time.Clock()
		ended = False

		self.outport = mido.open_output()
		self.font = pygame.font.SysFont(None, 24)
		# Read file, get all notes, convert to something midi compatible
		song = gp.parse('./songbook/daytripper_riff.gp5')
		self.tempo = song.tempo
		self.ticks_per_ms = 2000 / self.tempo
		for i, t in enumerate(song.tracks):
			track = Track(t)
			self.tracks.append(track)
			self.outport.send(Message('program_change', channel=i, program=track.channel.instrument))

		self.main_track = self.tracks[0]
		print(self.main_track.measures[0]['notes'])
		while not ended:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					ended = True
				if event.type == pygame.KEYDOWN:
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
			ticks_in_song = 0
			ticks_in_mesure = 0
			if not ended:
				#print(self.is_playing)
				if self.is_playing :
					self.time_in_mesure += clock.get_time()
					self.time_in_song += clock.get_time()
					ticks_in_mesure = int(self.time_in_mesure / self.ticks_per_ms)


			screen.fill((29, 104, 135))
			board_height = SCREEN_HEIGHT / 2.2
			board = pygame.Surface((SCREEN_WIDTH, board_height))
			board.fill((73,70,71))
			#MEASURES
			measure_width = SCREEN_WIDTH / 2.5
			tick_width = measure_width / TICKS_PER_MEASURE
			first_measure = - tick_width * ticks_in_mesure
			#print(first_measure)
			#print(first_measure)
			for nm in range(-1, 4) :
				measure_pos = 40 + first_measure + nm * measure_width
				img = self.font.render(str(self.current_measure + nm + 1), True, (255,255,255))
				screen.blit(img, (measure_pos , SCREEN_HEIGHT / 2.5 -20))
				pygame.draw.line(board, (29,104,135), (measure_pos,0), (measure_pos,board_height), 3)
				for nt in range(3) :
					temp_pos = measure_pos + ((nt + 1) * measure_width / 4)
					pygame.draw.line(board, (20,20,20), (temp_pos,0), (temp_pos,board_height), 1)
			# STRINGS
			first_string = board_height / 12
			space_string = board_height / 6
			for ns in range(6) :
				height_pos = first_string + ns * space_string
				if ns < 3 :
					string_color = (255,255,255)
				else :
					string_color = (174, 154, 122)
				pygame.draw.line(board, string_color, (0,height_pos), (SCREEN_WIDTH,height_pos), 3)
			
			# NOTES
			for nm in range(-1, 4) :
				if (self.current_measure + nm) < 0 or (self.current_measure + nm) > len(self.main_track.measures) - 1 :
					continue
				measure = self.main_track.measures[self.current_measure + nm]
				for n in measure['notes']:
					if n['type'] == gp.NoteType.tie :
						continue
					note_width = int((n['tick_stop'] - n['tick_start']) * tick_width)
					note_heigt = int(space_string)
					note_x = 40 + first_measure + nm * measure_width + (n['tick_start'] - (self.current_measure + nm) * TICKS_PER_MEASURE) * tick_width
					note_y = (n['string'] - 1) * space_string
					pygame.draw.ellipse(board, (120,70,200), (note_x, note_y, note_width, note_heigt))
					img = self.font.render(str(n['fret']), True, (255,255,255))
					board.blit(img, (note_x + note_width / 2 - img.get_rect().width / 2, note_y + note_heigt / 3))
			
			screen.blit(board, (0,SCREEN_HEIGHT / 2.5))
			pygame.draw.line(screen, (255,170,100), (40, SCREEN_HEIGHT / 2.5 - 20), (40, SCREEN_HEIGHT / 2.5 + board_height + 20), width=2)
			pygame.display.flip()
			if not ended :
				ended = self.play_synchro()	
				

			
			clock.tick(60)

		self.outport.close()
		pygame.quit()
		quit()

	
s = Guitarician()
s.start()
