"""Play with Tab"""
import json
import pygame
import guitarpro as gp
import mido
from mido import Message
from MenuItem import MenuItem


TICKS_PER_MEASURE = 120

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BACKGROUND_COLOR = (29, 104, 135)

NB_EMPTY_MEASURE = 2


class Track:
    """A track to play (midi) and/or to play with"""
    def __init__(self, gp_track):
        self.tuning = [s.value for s in gp_track.strings]
        self.midi = gp_track.channel
        self.volume = gp_track.channel.volume
        self.channel = gp_track.channel.channel
        self.name = gp_track.name

        self.notes_on = []
        self.measures = []
        for i in range(NB_EMPTY_MEASURE):
            self.measures.append({'num': 0, 'notes': []})
        for i, m in enumerate(gp_track.measures):
            mn = i + NB_EMPTY_MEASURE
            self.measures.append({'num': mn, 'notes': []})
            ticks = 0
            for b in m.voices[0].beats:
                tick_top = ticks
                tick_duration = TICKS_PER_MEASURE / b.duration.value
                if b.duration.isDotted:
                    tick_duration += tick_duration / 2
                tick_end = tick_top + tick_duration
                for n in b.notes:
                    if n.type == gp.NoteType.tie:
                        p_note = self.get_previous_note(mn, n.string)
                        p_note['tick_stop'] = tick_end + (mn) * TICKS_PER_MEASURE
                    note = self.note_to_midi(n)
                    note['measure'] = mn
                    note['tick_start'] = tick_top + mn * TICKS_PER_MEASURE
                    note['tick_stop'] = tick_end + mn * TICKS_PER_MEASURE
                    self.measures[mn]['notes'].append(note)
                ticks = tick_end

    def get_previous_note(self, measure, string):
        for nm in range(measure, -1, -1):
            notes = reversed(self.measures[nm]['notes'])
            note = next((note for note in notes if note['string'] == string), None)
            if note is not None:
                return note
        return None

    def note_to_midi(self, note):
        return {'value': (self.tuning[note.string - 1] + note.value),
                'type': note.type,
                'string': note.string,
                'fret': note.value,
                'on': False}


class Guitarician:
    def __init__(self):
        self.font = None
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

        self.menus = []

        with open('params.json') as json_file:
            self.params = json.load(json_file)

    def play_track(self, track):
        # notes off de la mesure
        notes_off = [note
                     for note
                     in track.measures[self.current_measure]['notes']
                     if not note['on'] and note['type'] != gp.NoteType.tie]

        ticks = self.ticks_in_mesure + self.current_measure * TICKS_PER_MEASURE
        for note in notes_off:
            if note['tick_start'] <= ticks <= note['tick_stop']:
                self.note_on(track, note)
                note['on'] = True
                track.notes_on.append(note)
                if note['value'] == 40:
                    print(self.ticks_in_mesure)
        notes_down = []
        for n in track.notes_on:
            if ticks > n['tick_stop']:
                self.note_off(track, n)
                n['on'] = False
                notes_down.append(n)
        for n in notes_down:
            track.notes_on.remove(n)

    def accelerate_tempo(self, value=None):
        """ Accelere le tempo

        De 10% de la valeur initiale, sauf si une valeur spécifique est donnée
        """
        # TODO : Prendre en compte value pour setter tempo à une valeur donnée
        self.tempo_modifier += 0.1
        self.ticks_per_ms = 2000 / (self.tempo * self.tempo_modifier)

    def slowdown_tempo(self, value=None):
        """ Ralenti le tempo

        De 10% de la valeur initiale, sauf si une valeur spécifique est donnée
        """
        # TODO : Prendre en compte value pour setter tempo à une valeur donnée
        self.tempo_modifier -= 0.1
        self.ticks_per_ms = 2000 / (self.tempo * self.tempo_modifier)

    def toogle_playing(self):
        """Start or pause the play"""
        if self.is_playing:
            self.pause_play()
        else:
            self.start_play()

    def pause_play(self):
        """Pause the game"""
        self.is_playing = False
        # Stop every notes playing
        for track in self.tracks:
            for note in track.notes_on:
                self.note_off(track, note)
        self.get_menu_item('play').is_visible = True
        self.get_menu_item('pause').is_visible = False

    def start_play(self):
        """Start or restart the game"""
        self.is_playing = True
        # If it was a pause, there is notes playing that we have to 'restart'
        for track in self.tracks:
            for note in track.notes_on:
                self.note_on(track, note)
        self.get_menu_item('play').is_visible = False
        self.get_menu_item('pause').is_visible = True


    def note_on(self, track, note):
        """Start a midi note"""
        on_msg = Message('note_on',
                         note=note['value'],
                         channel=track.channel,
                         velocity=track.volume,
                         time=0)
        self.outport.send(on_msg)

    def note_off(self, track, note):
        """Stop a midi note"""
        off_msg = Message('note_off',
                          note=note['value'],
                          channel=track.channel,
                          velocity=track.volume,
                          time=0)
        self.outport.send(off_msg)

    def play_synchro(self):
        ended = False
        if not self.is_playing:
            return False
        for track in self.tracks:
            self.play_track(track)

        if self.ticks_in_mesure >= TICKS_PER_MEASURE:
            self.current_measure += 1
            self.time_in_mesure = 0
            self.ticks_in_mesure = 0
            if self.current_measure == len(self.tracks[0].measures):
                ended = True
            else:
                for track in self.tracks:
                    self.play_track(track)
        return ended

    def track_choose(self):
        choosed = None
        menu_surf = pygame.Surface((SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
        for i, t in enumerate(self.tracks):
            tmenu = self.font.render(t.name, True, (255, 255, 255))
            menu_surf.blit(tmenu, (0, i*20))
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

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('un test')

        clock = pygame.time.Clock()
        ended = False

        self.font = pygame.font.SysFont(None, 24)
        self.outport = mido.open_output()

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

        # INIT MENUS
        self.init_menus()

        # MAIN LOOP
        while not ended:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    ended = True
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click_menu(event.pos)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_KP_MINUS:
                        self.slowdown_tempo()
                    elif event.key == pygame.K_KP_PLUS:
                        self.accelerate_tempo()
                    elif event.key == pygame.K_SPACE:
                        self.toogle_playing()

            if not ended:
                # print(self.is_playing)
                if self.is_playing:
                    self.time_in_mesure += clock.get_time()
                    self.ticks_in_mesure = int(self.time_in_mesure / self.ticks_per_ms)

            self.screen.fill(BACKGROUND_COLOR)
            board_height = SCREEN_HEIGHT / 2.2
            board = pygame.Surface((SCREEN_WIDTH, board_height))
            board.fill((73, 70, 71))
            # MEASURES
            measure_width = SCREEN_WIDTH / 2.5
            tick_width = measure_width / TICKS_PER_MEASURE
            first_measure = - tick_width * self.ticks_in_mesure
            # print(first_measure)
            # print(first_measure)
            for nm in range(-1, 4):
                measure_pos = 100 + first_measure + nm * measure_width
                img = self.font.render(str(self.current_measure + nm + 1), True, (255, 255, 255))
                self.screen.blit(img, (measure_pos, SCREEN_HEIGHT / 2.5 - 20))
                pygame.draw.line(board, (29, 104, 135), (measure_pos, 0), (measure_pos, board_height), 3)
                for nt in range(3):
                    temp_pos = measure_pos + ((nt + 1) * measure_width / 4)
                    pygame.draw.line(board, (20, 20, 20), (temp_pos, 0), (temp_pos, board_height), 1)
            # STRINGS
            first_string = board_height / 12
            space_string = board_height / 6
            for ns in range(6):
                height_pos = first_string + ns * space_string
                if ns < 3:
                    string_color = (255, 255, 255)
                else:
                    string_color = (174, 154, 122)
                pygame.draw.line(board, string_color, (0, height_pos), (SCREEN_WIDTH, height_pos), 3)

            # NOTES
            for nm in range(-1, 4):
                if (self.current_measure + nm) < 0 or (self.current_measure + nm) > len(self.main_track.measures) - 1:
                    continue
                measure = self.main_track.measures[self.current_measure + nm]
                for n in measure['notes']:
                    if n['type'] == gp.NoteType.tie:
                        continue
                    note_width = int((n['tick_stop'] - n['tick_start']) * tick_width)
                    note_heigt = int(space_string)
                    note_x = 100 + first_measure + nm * measure_width + (n['tick_start'] - (self.current_measure + nm) * TICKS_PER_MEASURE) * tick_width
                    note_y = (n['string'] - 1) * space_string
                    note_color = (120, 70, 200)
                    if n['on']:
                        note_color = (70, 120, 200)
                    pygame.draw.ellipse(board, note_color, (note_x, note_y, note_width, note_heigt))
                    img = self.font.render(str(n['fret']), True, (255, 255, 255))
                    board.blit(img, (note_x + note_width / 2 - img.get_rect().width / 2, note_y + note_heigt / 3))

            self.screen.blit(board, (0, SCREEN_HEIGHT / 2.5))
            pygame.draw.line(self.screen, (255, 170, 100), (100, SCREEN_HEIGHT / 2.5 - 20), (100, SCREEN_HEIGHT / 2.5 + board_height + 20), width=2)

            # CONTROLS
            self.draw_menu_controls()

            pygame.display.flip()
            if not ended:
                ended = self.play_synchro()

            clock.tick(60)

        self.outport.close()
        pygame.quit()
        quit()

    def init_menus(self):
        # Bouton play :
        play_surf = pygame.Surface((50, 50))
        play_x = 2 * SCREEN_WIDTH / 5
        play_y = SCREEN_HEIGHT / 2.5 + SCREEN_HEIGHT / 2.2 + 20
        play_surf.fill(BACKGROUND_COLOR)
        pygame.draw.polygon(play_surf, (255, 255, 255), [(5, 10), (5, 40), (30, 25)])
        menu_item = MenuItem('play', play_surf, (play_x, play_y))
        menu_item.callback = self.start_play
        self.menus.append(menu_item)
        # Bouton pause :
        pause_surf = pygame.Surface((50, 50))
        pause_x = 2 * SCREEN_WIDTH / 5
        pause_y = SCREEN_HEIGHT / 2.5 + SCREEN_HEIGHT / 2.2 + 20
        pause_surf.fill(BACKGROUND_COLOR)
        pygame.draw.rect(pause_surf, (255, 255, 255), ((5, 10), (11, 30)))
        pygame.draw.rect(pause_surf, (255, 255, 255), ((20, 10), (11, 30)))
        menu_item = MenuItem('pause', pause_surf, (pause_x, pause_y))
        menu_item.callback = self.pause_play
        menu_item.is_visible = False
        self.menus.append(menu_item)

    def draw_menu_controls(self):
        """Draw all the visible menu item""""
        for menu_item in self.menus:
            menu_item.draw_on(self.screen)

    def handle_click_menu(self, point):
        """Find the clicked menu item and send the callback of this item"""
        clicked = next(menu_item for menu_item in self.menus
                       if menu_item.is_clicked(point))
        if clicked is not None:
            clicked.callback()

    def get_menu_item(self, name):
        """Find the menu item by its name"""
        for menu_item in self.menus:
            if menu_item.name == name:
                return menu_item
        return None


if __name__ == '__main__':
    s = Guitarician()
    s.start()
