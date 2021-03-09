import pygame
import guitarpro as gp
import mido
from mido import Message
import time
import json

TICKS_PER_MEASURE = 120

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

NB_EMPTY_MEASURE = 2
class Track:
	def __init__(self, gp_track) :
		self.tuning = [s.value for s in gp_track.strings]
		self.midi = gp_track.channel
		self.volume = gp_track.channel.volume
		self.channel = gp_track.channel.channel
		self.name = gp_track.name

		self.notes_on = []
		self.measures = []
		for i in range(NB_EMPTY_MEASURE) :
			self.measures.append({'num': 0, 'notes':[]})
		for i, m in enumerate(gp_track.measures) :
			mn = i + NB_EMPTY_MEASURE
			self.measures.append({'num': mn, 'notes':[]})
			ticks = 0
			for b in m.voices[0].beats:
				tick_top = ticks
				tick_duration = TICKS_PER_MEASURE / b.duration.value
				if b.duration.isDotted:
					tick_duration += tick_duration / 2
				tick_end = tick_top + tick_duration
				for n in b.notes : 
					if n.type == gp.NoteType.tie :
						p_note = self.get_previous_note(mn, n.string)
						p_note['tick_stop'] = tick_end + (mn) * TICKS_PER_MEASURE
					note = self.note_to_midi(n)
					note['measure'] = mn
					note['tick_start'] = tick_top + mn * TICKS_PER_MEASURE
					note['tick_stop'] = tick_end + mn * TICKS_PER_MEASURE
					self.measures[mn]['notes'].append(note)
				ticks = tick_end
		

	def get_previous_note(self, measure, string):
		for nm in range(measure, -1, -1) :
			notes = reversed(self.measures[nm]['notes'])
			note = next((note for note in notes if note['string'] ==string), None)
			if note != None :
				return note
		return None


	def note_to_midi(self, note) :
		return {'value':(self.tuning[note.string - 1] + note.value), 'type':note.type, 'string': note.string, 'fret':note.value, 'on': False}



class Guitarician :
	def __init__(self) :
		self.outport = None
		self.screen = None

		self.tracks = []

		self.time_in_mesure = 0
		self.ticks_in_mesure = 0
		self.ticks_per_ms = 20

		self.current_measure = 0
		self.measure_started = False
		self.is_playing = False
		
		self.tempo = 0
		self.tempo_modifier = 1.0
		self.main_track = None

		with open('params.json') as json_file:
			self.params = json.load(json_file)

	def play_track(self, track) :
		# notes off / on de la mesure
		notes_off = [note for note in track.measures[self.current_measure]['notes'] if not note['on'] and note['type'] != gp.NoteType.tie]
		#
		ticks = self.ticks_in_mesure + self.current_measure * TICKS_PER_MEASURE
		for n in notes_off :
			if ticks >= n['tick_start'] and ticks <= n['tick_stop'] :
				self.outport.send(Message('note_on', note=n['value'], channel=track.channel, velocity=track.volume, time=0))
				n['on'] = True
				track.notes_on.append(n)
				if n['value'] == 40 :
					print(self.ticks_in_mesure)
		notes_down = []
		for n in track.notes_on :
			if ticks > n['tick_stop'] :
				self.outport.send(Message('note_off', note=n['value'], channel=track.channel, velocity=track.volume, time=0))
				n['on'] = False
				notes_down.append(n)
		for n in notes_down :
			track.notes_on.remove(n)


	def play_synchro(self):
		ended = False
		if not self.is_playing :
			return False
		for track in self.tracks :
			self.play_track(track)

		if(self.ticks_in_mesure >= TICKS_PER_MEASURE):	
				self.current_measure += 1
				self.time_in_mesure = 0
				self.ticks_in_mesure = 0
				if self.current_measure == len(self.tracks[0].measures) :
					ended = True
				else :
					for track in self.tracks :
						self.play_track(track)
		return ended

	def track_choose(self):
		choosed = None
		menu_surf = pygame.Surface((SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
		for i,t in enumerate(self.tracks):
			tmenu = self.font.render(t.name, True, (255,255,255))
			menu_surf.blit(tmenu, (0 , i*20))
		self.screen.blit(menu_surf, (SCREEN_WIDTH/4, SCREEN_HEIGHT/4))
		pygame.display.update()
		while choosed is None:
			for event in pygame.event.get():
				if event.type == pygame.MOUSEBUTTONUP:
					pos = pygame.mouse.get_pos()
					rel_pos = (pos[0] - SCREEN_WIDTH/4, pos[1] - SCREEN_HEIGHT/4)
					choosed_id = int(rel_pos[1] / 20)
					print(choosed_id)
					choosed = self.tracks[choosed_id]
		return choosed

	def start(self):
		pygame.init()

		self.screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
		pygame.display.set_caption('un test')

		clock = pygame.time.Clock()
		ended = False

		self.outport = mido.open_output()
		self.font = pygame.font.SysFont(None, 24)
		# Read file, get all notes, convert to something midi compatible
		song = gp.parse('./songbook/' + self.params['file'])
		self.tempo = song.tempo
		self.ticks_per_ms = 2000 / self.tempo
		for t in song.tracks:
			track = Track(t)
			track.volume = 100
			self.tracks.append(track)
			self.outport.send(Message('program_change', channel=track.channel, program=track.midi.instrument))
			
		
		self.main_track = self.track_choose()
		self.main_track.volume = 100
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

			self.ticks_in_mesure = 0
			if not ended:
				#print(self.is_playing)
				if self.is_playing :
					self.time_in_mesure += clock.get_time()
					self.ticks_in_mesure = int(self.time_in_mesure / self.ticks_per_ms)

			self.screen.fill((29, 104, 135))
			board_height = SCREEN_HEIGHT / 2.2
			board = pygame.Surface((SCREEN_WIDTH, board_height))
			board.fill((73,70,71))
			#MEASURES
			measure_width = SCREEN_WIDTH / 2.5
			tick_width = measure_width / TICKS_PER_MEASURE
			first_measure = - tick_width * self.ticks_in_mesure
			#print(first_measure)
			#print(first_measure)
			for nm in range(-1, 4) :
				measure_pos = 100 + first_measure + nm * measure_width
				img = self.font.render(str(self.current_measure + nm + 1), True, (255,255,255))
				self.screen.blit(img, (measure_pos , SCREEN_HEIGHT / 2.5 -20))
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
					note_x = 100 + first_measure + nm * measure_width + (n['tick_start'] - (self.current_measure + nm) * TICKS_PER_MEASURE) * tick_width
					note_y = (n['string'] - 1) * space_string
					pygame.draw.ellipse(board, (120,70,200), (note_x, note_y, note_width, note_heigt))
					img = self.font.render(str(n['fret']), True, (255,255,255))
					board.blit(img, (note_x + note_width / 2 - img.get_rect().width / 2, note_y + note_heigt / 3))
			
			self.screen.blit(board, (0,SCREEN_HEIGHT / 2.5))
			pygame.draw.line(self.screen, (255,170,100), (100, SCREEN_HEIGHT / 2.5 - 20), (100, SCREEN_HEIGHT / 2.5 + board_height + 20), width=2)
			pygame.display.flip()

			if not ended :
				ended = self.play_synchro()	
				

			
			clock.tick(60)

		self.outport.close()
		pygame.quit()
		quit()

if __name__ == '__main__':	
	s = Guitarician()
	s.start()
