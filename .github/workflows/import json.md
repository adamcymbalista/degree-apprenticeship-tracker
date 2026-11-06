import json

import os

import sys

import heapq

import random

import time



import numpy as np

import pygame





BASE\_DIR = os.path.dirname(os.path.abspath(\_\_file\_\_))

ASSETS\_DIR = os.path.join(BASE\_DIR, 'assets')

SFX\_DIR = os.path.join(ASSETS\_DIR, 'sfx')

MUSIC\_DIR = os.path.join(ASSETS\_DIR, 'music')

SETTINGS\_FILE = os.path.join(BASE\_DIR, 'settings.json')

DEFAULT\_WINDOW\_WIDTH = 1200

DEFAULT\_WINDOW\_HEIGHT = 700

MIN\_WINDOW\_WIDTH = 700

MIN\_WINDOW\_HEIGHT = 450

FPS = 60

MAZE\_MARGIN = 30

PANEL\_GAP = 20

HUD\_HEIGHT = 60

DEFAULT\_MAZE\_COLS = 17

DEFAULT\_MAZE\_ROWS = 13

DEFAULT\_INITIAL\_REPEAT\_DELAY = 0.28

DEFAULT\_START\_REPEAT\_INTERVAL = 0.18

DEFAULT\_MIN\_REPEAT\_INTERVAL = 0.045

DEFAULT\_ACCEL\_TIME = 1.4

MAX\_PATH\_POINTS = 700

MAX\_TIME\_POINTS = 300

ASSUMED\_SECONDS\_PER\_CELL = 0.35

MAX\_ROUND\_SECONDS = 180

COLOR\_BG = (18, 18, 26)

COLOR\_WALL = (235, 235, 245)

COLOR\_PANEL\_BG = (28, 28, 40)

COLOR\_TEXT = (240, 240, 245)

COLOR\_MUTED = (150, 150, 165)

COLOR\_ACCENT = (90, 200, 255)

COLOR\_P1 = (90, 220, 130)

COLOR\_P1\_TRAIL = (40, 110, 70)

COLOR\_P2 = (90, 160, 255)

COLOR\_P2\_TRAIL = (45, 80, 130)

COLOR\_START = (255, 210, 90)

COLOR\_END = (255, 90, 110)

COLOR\_OPTIMAL\_PATH = (255, 255, 255)

DEFAULT\_SETTINGS = {'music\_volume': 0.5, 'sfx\_volume': 0.7, 'movement\_speed': 1.0, 'rounds': 3, 'fullscreen': False}





def load\_settings():

&#x20;   settings = DEFAULT\_SETTINGS.copy()

&#x20;   if os.path.exists(SETTINGS\_FILE):

&#x20;       try:

&#x20;           with open(SETTINGS\_FILE, 'r') as f:

&#x20;               saved = json.load(f)

&#x20;           for key in DEFAULT\_SETTINGS:

&#x20;               if key in saved:

&#x20;                   settings\[key] = saved\[key]

&#x20;       except (json.JSONDecodeError, OSError):

&#x20;           pass

&#x20;   return settings





def save\_settings(settings):

&#x20;   try:

&#x20;       with open(SETTINGS\_FILE, 'w') as f:

&#x20;           json.dump(settings, f, indent=2)

&#x20;   except OSError:

&#x20;       pass





DIRECTIONS = {'N': (0, -1, 'S'), 'S': (0, 1, 'N'), 'E': (1, 0, 'W'), 'W': (-1, 0, 'E')}





class Cell:

&#x20;   \_\_slots\_\_ = ('x', 'y', 'walls', 'visited')



&#x20;   def \_\_init\_\_(self, x, y):

&#x20;       self.x = x

&#x20;       self.y = y

&#x20;       self.walls = {'N': True, 'S': True, 'E': True, 'W': True}

&#x20;       self.visited = False





class Maze:



&#x20;   def \_\_init\_\_(self, cols, rows, seed=None):

&#x20;       self.cols = cols

&#x20;       self.rows = rows

&#x20;       self.rng = random.Random(seed)

&#x20;       self.grid = \[\[Cell(x, y) for y in range(rows)] for x in range(cols)]

&#x20;       self.start = (0, 0)

&#x20;       self.end = (cols - 1, rows - 1)

&#x20;       self.\_generate()

&#x20;       self.optimal\_path = self.solve\_astar(self.start, self.end)



&#x20;   def \_in\_bounds(self, x, y):

&#x20;       return 0 <= x < self.cols and 0 <= y < self.rows



&#x20;   def \_generate(self):

&#x20;       stack = \[]

&#x20;       start\_cell = self.grid\[0]\[0]

&#x20;       start\_cell.visited = True

&#x20;       stack.append(start\_cell)

&#x20;       while stack:

&#x20;           current = stack\[-1]

&#x20;           neighbors = \[]

&#x20;           for direction, (dx, dy, opposite) in DIRECTIONS.items():

&#x20;               nx, ny = (current.x + dx, current.y + dy)

&#x20;               if self.\_in\_bounds(nx, ny):

&#x20;                   neighbor = self.grid\[nx]\[ny]

&#x20;                   if not neighbor.visited:

&#x20;                       neighbors.append((direction, opposite, neighbor))

&#x20;           if neighbors:

&#x20;               direction, opposite, neighbor = self.rng.choice(neighbors)

&#x20;               current.walls\[direction] = False

&#x20;               neighbor.walls\[opposite] = False

&#x20;               neighbor.visited = True

&#x20;               stack.append(neighbor)

&#x20;           else:

&#x20;               stack.pop()

&#x20;       extra\_links = max(1, self.cols \* self.rows // 25)

&#x20;       for \_ in range(extra\_links):

&#x20;           x = self.rng.randrange(self.cols)

&#x20;           y = self.rng.randrange(self.rows)

&#x20;           cell = self.grid\[x]\[y]

&#x20;           direction, (dx, dy, opposite) = self.rng.choice(list(DIRECTIONS.items()))

&#x20;           nx, ny = (x + dx, y + dy)

&#x20;           if self.\_in\_bounds(nx, ny):

&#x20;               neighbor = self.grid\[nx]\[ny]

&#x20;               cell.walls\[direction] = False

&#x20;               neighbor.walls\[opposite] = False



&#x20;   def neighbors(self, x, y):

&#x20;       cell = self.grid\[x]\[y]

&#x20;       for direction, (dx, dy, opposite) in DIRECTIONS.items():

&#x20;           if not cell.walls\[direction]:

&#x20;               nx, ny = (x + dx, y + dy)

&#x20;               if self.\_in\_bounds(nx, ny):

&#x20;                   yield (nx, ny)



&#x20;   def can\_move(self, x, y, direction):

&#x20;       if direction not in DIRECTIONS:

&#x20;           return False

&#x20;       cell = self.grid\[x]\[y]

&#x20;       if cell.walls\[direction]:

&#x20;           return False

&#x20;       dx, dy, \_ = DIRECTIONS\[direction]

&#x20;       return self.\_in\_bounds(x + dx, y + dy)



&#x20;   @staticmethod

&#x20;   def \_heuristic(a, b):

&#x20;       return abs(a\[0] - b\[0]) + abs(a\[1] - b\[1])



&#x20;   def solve\_astar(self, start, goal):

&#x20;       open\_heap = \[(self.\_heuristic(start, goal), 0, start)]

&#x20;       came\_from = {}

&#x20;       g\_score = {start: 0}

&#x20;       visited = set()

&#x20;       while open\_heap:

&#x20;           \_, cost, current = heapq.heappop(open\_heap)

&#x20;           if current in visited:

&#x20;               continue

&#x20;           visited.add(current)

&#x20;           if current == goal:

&#x20;               return self.\_reconstruct(came\_from, current)

&#x20;           for nxt in self.neighbors(\*current):

&#x20;               tentative\_g = cost + 1

&#x20;               if tentative\_g < g\_score.get(nxt, float('inf')):

&#x20;                   g\_score\[nxt] = tentative\_g

&#x20;                   came\_from\[nxt] = current

&#x20;                   priority = tentative\_g + self.\_heuristic(nxt, goal)

&#x20;                   heapq.heappush(open\_heap, (priority, tentative\_g, nxt))

&#x20;       return \[]



&#x20;   @staticmethod

&#x20;   def \_reconstruct(came\_from, current):

&#x20;       path = \[current]

&#x20;       while current in came\_from:

&#x20;           current = came\_from\[current]

&#x20;           path.append(current)

&#x20;       path.reverse()

&#x20;       return path



&#x20;   @property

&#x20;   def optimal\_length(self):

&#x20;       return len(self.optimal\_path)





class HeldKeyState:



&#x20;   def \_\_init\_\_(self):

&#x20;       self.held = False

&#x20;       self.press\_time = 0.0

&#x20;       self.next\_repeat\_time = 0.0





class Player:



&#x20;   def \_\_init\_\_(self, name, maze, color, trail\_color, key\_map, movement\_cfg):

&#x20;       self.name = name

&#x20;       self.maze = maze

&#x20;       self.color = color

&#x20;       self.trail\_color = trail\_color

&#x20;       self.key\_map = key\_map

&#x20;       self.cfg = movement\_cfg

&#x20;       self.cell = list(maze.start)

&#x20;       self.path\_cells = \[tuple(self.cell)]

&#x20;       self.move\_count = 0

&#x20;       self.finished = False

&#x20;       self.finish\_time = None

&#x20;       self.start\_time = None

&#x20;       self.held = {d: HeldKeyState() for d in ('N', 'S', 'E', 'W')}

&#x20;       self.active\_direction = None

&#x20;       self.last\_move\_time = 0.0

&#x20;       self.bump\_flag = False



&#x20;   def start\_timer(self):

&#x20;       self.start\_time = time.time()



&#x20;   def key\_down(self, key, now):

&#x20;       direction = self.key\_map.get(key)

&#x20;       if direction is None:

&#x20;           return

&#x20;       state = self.held\[direction]

&#x20;       state.held = True

&#x20;       state.press\_time = now

&#x20;       state.next\_repeat\_time = now + self.cfg\['initial\_delay']

&#x20;       self.active\_direction = direction

&#x20;       self.\_attempt\_move(direction, now)



&#x20;   def key\_up(self, key):

&#x20;       direction = self.key\_map.get(key)

&#x20;       if direction is None:

&#x20;           return

&#x20;       self.held\[direction].held = False

&#x20;       if self.active\_direction == direction:

&#x20;           still\_held = \[d for d, s in self.held.items() if s.held]

&#x20;           self.active\_direction = still\_held\[-1] if still\_held else None



&#x20;   def \_attempt\_move(self, direction, now):

&#x20;       self.bump\_flag = False

&#x20;       if self.finished:

&#x20;           return False

&#x20;       x, y = self.cell

&#x20;       if self.maze.can\_move(x, y, direction):

&#x20;           dx, dy, \_ = \_DELTA\[direction]

&#x20;           self.cell = \[x + dx, y + dy]

&#x20;           self.path\_cells.append(tuple(self.cell))

&#x20;           self.move\_count += 1

&#x20;           self.last\_move\_time = now

&#x20;           if tuple(self.cell) == self.maze.end:

&#x20;               self.finished = True

&#x20;               self.finish\_time = now

&#x20;           return True

&#x20;       else:

&#x20;           self.bump\_flag = True

&#x20;           return False



&#x20;   def update(self, now):

&#x20;       self.bump\_flag = False

&#x20;       if self.finished or self.active\_direction is None:

&#x20;           return

&#x20;       direction = self.active\_direction

&#x20;       state = self.held\[direction]

&#x20;       if not state.held:

&#x20;           return

&#x20;       if now >= state.next\_repeat\_time:

&#x20;           self.\_attempt\_move(direction, now)

&#x20;           held\_duration = now - state.press\_time

&#x20;           progress = min(1.0, held\_duration / max(0.001, self.cfg\['accel\_time']))

&#x20;           interval = self.cfg\['start\_interval'] + progress \* (self.cfg\['min\_interval'] - self.cfg\['start\_interval'])

&#x20;           state.next\_repeat\_time = now + max(self.cfg\['min\_interval'], interval)



&#x20;   @property

&#x20;   def elapsed\_time(self):

&#x20;       if self.start\_time is None:

&#x20;           return 0.0

&#x20;       end = self.finish\_time if self.finished else time.time()

&#x20;       return end - self.start\_time



&#x20;   def reset\_for\_maze(self, maze):

&#x20;       self.maze = maze

&#x20;       self.cell = list(maze.start)

&#x20;       self.path\_cells = \[tuple(self.cell)]

&#x20;       self.move\_count = 0

&#x20;       self.finished = False

&#x20;       self.finish\_time = None

&#x20;       self.start\_time = None

&#x20;       self.active\_direction = None

&#x20;       for s in self.held.values():

&#x20;           s.held = False

\_DELTA = {'N': (0, -1, 'S'), 'S': (0, 1, 'N'), 'E': (1, 0, 'W'), 'W': (-1, 0, 'E')}





def compute\_round\_score(optimal\_length, move\_count, elapsed\_seconds):

&#x20;   optimal\_length = max(1, optimal\_length)

&#x20;   move\_count = max(1, move\_count)

&#x20;   efficiency\_ratio = min(1.0, optimal\_length / move\_count)

&#x20;   path\_score = round(efficiency\_ratio \* MAX\_PATH\_POINTS)

&#x20;   par\_time = optimal\_length \* ASSUMED\_SECONDS\_PER\_CELL

&#x20;   if elapsed\_seconds and elapsed\_seconds > 0:

&#x20;       time\_ratio = min(1.0, par\_time / elapsed\_seconds)

&#x20;   else:

&#x20;       time\_ratio = 0.0

&#x20;   time\_score = round(time\_ratio \* MAX\_TIME\_POINTS)

&#x20;   total = path\_score + time\_score

&#x20;   return (total, path\_score, time\_score, efficiency\_ratio)





SAMPLE\_RATE = 44100





def \_envelope(n\_samples, attack=0.01, release=0.15):

&#x20;   env = np.ones(n\_samples)

&#x20;   a = max(1, int(attack \* SAMPLE\_RATE))

&#x20;   r = max(1, int(release \* SAMPLE\_RATE))

&#x20;   a = min(a, n\_samples // 2) if n\_samples > 1 else 0

&#x20;   r = min(r, n\_samples // 2) if n\_samples > 1 else 0

&#x20;   if a > 0:

&#x20;       env\[:a] \*= np.linspace(0, 1, a)

&#x20;   if r > 0:

&#x20;       env\[-r:] \*= np.linspace(1, 0, r)

&#x20;   return env





def \_tone(freq, duration, volume=0.5, wave='sine', attack=0.005, release=0.1):

&#x20;   n = int(SAMPLE\_RATE \* duration)

&#x20;   t = np.linspace(0, duration, n, endpoint=False)

&#x20;   if wave == 'sine':

&#x20;       raw = np.sin(2 \* np.pi \* freq \* t)

&#x20;   elif wave == 'square':

&#x20;       raw = np.sign(np.sin(2 \* np.pi \* freq \* t))

&#x20;   elif wave == 'triangle':

&#x20;       raw = 2 \* np.abs(2 \* (t \* freq - np.floor(t \* freq + 0.5))) - 1

&#x20;   elif wave == 'saw':

&#x20;       raw = 2 \* (t \* freq - np.floor(t \* freq + 0.5))

&#x20;   else:

&#x20;       raw = np.sin(2 \* np.pi \* freq \* t)

&#x20;   raw \*= \_envelope(n, attack, release)

&#x20;   return raw \* volume





def \_to\_pygame\_sound(mono\_wave):

&#x20;   mono\_wave = np.clip(mono\_wave, -1.0, 1.0)

&#x20;   stereo = np.repeat(mono\_wave.reshape(-1, 1), 2, axis=1)

&#x20;   audio = (stereo \* 32767).astype(np.int16)

&#x20;   audio = np.ascontiguousarray(audio)

&#x20;   return pygame.sndarray.make\_sound(audio)





def \_chord(freqs, duration, volume=0.4, wave='sine'):

&#x20;   total = np.zeros(int(SAMPLE\_RATE \* duration))

&#x20;   for f in freqs:

&#x20;       total += \_tone(f, duration, volume=volume / len(freqs), wave=wave, release=duration \* 0.6)

&#x20;   return total





def \_sequence(notes, wave='square', volume=0.5):

&#x20;   chunks = \[]

&#x20;   for freq, dur in notes:

&#x20;       if freq is None:

&#x20;           chunks.append(np.zeros(int(SAMPLE\_RATE \* dur)))

&#x20;       else:

&#x20;           chunks.append(\_tone(freq, dur, volume=volume, wave=wave, release=dur \* 0.5))

&#x20;   return np.concatenate(chunks) if chunks else np.zeros(1)





def \_generate\_music\_loop(duration=16.0, volume=0.18):

&#x20;   progression = \[\[261.63, 329.63, 392.0], \[220.0, 261.63, 329.63], \[174.61, 220.0, 261.63], \[196.0, 246.94, 293.66]]

&#x20;   beat = duration / (len(progression) \* 4)

&#x20;   out = np.zeros(int(SAMPLE\_RATE \* duration))

&#x20;   pos = 0

&#x20;   for chord in progression:

&#x20;       for i in range(4):

&#x20;           freq = chord\[i % len(chord)]

&#x20;           n = int(SAMPLE\_RATE \* beat)

&#x20;           note = \_tone(freq \* (1 if i % 2 == 0 else 2), beat, volume=volume, wave='triangle', attack=0.02, release=beat \* 0.8)

&#x20;           end = min(len(out), pos + len(note))

&#x20;           out\[pos:end] += note\[:end - pos]

&#x20;           pos += n

&#x20;   pad = np.zeros(int(SAMPLE\_RATE \* duration))

&#x20;   seg = duration / len(progression)

&#x20;   pos = 0

&#x20;   for chord in progression:

&#x20;       n = int(SAMPLE\_RATE \* seg)

&#x20;       note = \_tone(chord\[0] / 2, seg, volume=volume \* 0.5, wave='sine', attack=0.05, release=seg \* 0.9)

&#x20;       end = min(len(pad), pos + len(note))

&#x20;       pad\[pos:end] += note\[:end - pos]

&#x20;       pos += n

&#x20;   mix = out + pad

&#x20;   fade = int(SAMPLE\_RATE \* 0.5)

&#x20;   mix\[:fade] \*= np.linspace(0, 1, fade)

&#x20;   mix\[-fade:] \*= np.linspace(1, 0, fade)

&#x20;   return mix





class AudioManager:



&#x20;   def \_\_init\_\_(self, settings):

&#x20;       self.settings = settings

&#x20;       self.enabled = True

&#x20;       try:

&#x20;           pygame.mixer.init(frequency=SAMPLE\_RATE, size=-16, channels=2)

&#x20;           self.\_build\_sounds()

&#x20;           self.enabled = True

&#x20;       except pygame.error:

&#x20;           self.enabled = False

&#x20;           self.sounds = {}

&#x20;           self.music\_channel = None

&#x20;           return

&#x20;       self.\_music\_channel = pygame.mixer.Channel(7)

&#x20;       self.apply\_volumes()



&#x20;   def \_build\_sounds(self):

&#x20;       self.sounds = {

&#x20;           'step': \_to\_pygame\_sound(\_tone(520, 0.05, volume=0.35, wave='square', release=0.03)),

&#x20;           'step\_alt': \_to\_pygame\_sound(\_tone(600, 0.045, volume=0.3, wave='square', release=0.03)),

&#x20;           'countdown\_beep': \_to\_pygame\_sound(\_tone(440, 0.15, volume=0.5, wave='sine')),

&#x20;           'countdown\_go': \_to\_pygame\_sound(\_chord(\[523.25, 659.25, 783.99], 0.35, volume=0.55)),

&#x20;           'finish': \_to\_pygame\_sound(\_sequence(

&#x20;               \[(523.25, 0.1), (659.25, 0.1), (783.99, 0.1), (1046.5, 0.25)],

&#x20;               wave='triangle', volume=0.5)),

&#x20;           'wall\_bump': \_to\_pygame\_sound(\_tone(120, 0.06, volume=0.3, wave='saw', release=0.05)),

&#x20;           'menu\_select': \_to\_pygame\_sound(\_tone(700, 0.05, volume=0.35, wave='square')),

&#x20;           'menu\_confirm': \_to\_pygame\_sound(\_sequence(

&#x20;               \[(660, 0.06), (880, 0.09)], wave='square', volume=0.4)),

&#x20;           'round\_end': \_to\_pygame\_sound(\_chord(\[392.0, 493.88, 587.33], 0.5, volume=0.5)),

&#x20;           'victory': \_to\_pygame\_sound(\_sequence(

&#x20;               \[(523.25, 0.12), (659.25, 0.12), (783.99, 0.12), (1046.5, 0.4)],

&#x20;               wave='triangle', volume=0.55)),

&#x20;       }

&#x20;       self.\_music\_wave = \_generate\_music\_loop()

&#x20;       self.music\_sound = \_to\_pygame\_sound(self.\_music\_wave)



&#x20;   def apply\_volumes(self):

&#x20;       if not self.enabled:

&#x20;           return

&#x20;       sfx\_vol = self.settings.get('sfx\_volume', 0.7)

&#x20;       for snd in self.sounds.values():

&#x20;           snd.set\_volume(sfx\_vol)

&#x20;       self.music\_sound.set\_volume(self.settings.get('music\_volume', 0.5))



&#x20;   def play(self, name):

&#x20;       if not self.enabled:

&#x20;           return

&#x20;       snd = self.sounds.get(name)

&#x20;       if snd:

&#x20;           snd.play()



&#x20;   def start\_music(self):

&#x20;       if not self.enabled:

&#x20;           return

&#x20;       if not self.\_music\_channel.get\_busy():

&#x20;           self.\_music\_channel.play(self.music\_sound, loops=-1)



&#x20;   def stop\_music(self):

&#x20;       if not self.enabled:

&#x20;           return

&#x20;       self.\_music\_channel.stop()



&#x20;   def set\_music\_volume(self, value):

&#x20;       self.settings\['music\_volume'] = value

&#x20;       if self.enabled:

&#x20;           self.music\_sound.set\_volume(value)



&#x20;   def set\_sfx\_volume(self, value):

&#x20;       self.settings\['sfx\_volume'] = value

&#x20;       if self.enabled:

&#x20;           for snd in self.sounds.values():

&#x20;               snd.set\_volume(value)





\_font\_cache = {}





def get\_font(size, bold=False):

&#x20;   key = (size, bold)

&#x20;   if key not in \_font\_cache:

&#x20;       f = pygame.font.SysFont('arial', size, bold=bold)

&#x20;       \_font\_cache\[key] = f

&#x20;   return \_font\_cache\[key]





def draw\_text(surface, text, pos, size=28, color=COLOR\_TEXT, bold=False, center=False, align\_right=False):

&#x20;   font = get\_font(size, bold)

&#x20;   rendered = font.render(text, True, color)

&#x20;   rect = rendered.get\_rect()

&#x20;   if center:

&#x20;       rect.center = pos

&#x20;   elif align\_right:

&#x20;       rect.topright = pos

&#x20;   else:

&#x20;       rect.topleft = pos

&#x20;   surface.blit(rendered, rect)

&#x20;   return rect





class Button:



&#x20;   def \_\_init\_\_(self, rect, label, on\_click=None, font\_size=26):

&#x20;       self.rect = pygame.Rect(rect)

&#x20;       self.label = label

&#x20;       self.on\_click = on\_click

&#x20;       self.font\_size = font\_size

&#x20;       self.hovered = False



&#x20;   def handle\_event(self, event):

&#x20;       if event.type == pygame.MOUSEMOTION:

&#x20;           self.hovered = self.rect.collidepoint(event.pos)

&#x20;       elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

&#x20;           if self.rect.collidepoint(event.pos):

&#x20;               if self.on\_click:

&#x20;                   self.on\_click()

&#x20;               return True

&#x20;       return False



&#x20;   def draw(self, surface):

&#x20;       bg = COLOR\_ACCENT if self.hovered else (45, 45, 62)

&#x20;       text\_color = (10, 10, 15) if self.hovered else COLOR\_TEXT

&#x20;       pygame.draw.rect(surface, bg, self.rect, border\_radius=10)

&#x20;       pygame.draw.rect(surface, COLOR\_ACCENT, self.rect, width=2, border\_radius=10)

&#x20;       draw\_text(surface, self.label, self.rect.center, size=self.font\_size, color=text\_color, center=True)





class Slider:



&#x20;   def \_\_init\_\_(self, rect, value, on\_change=None, label=''):

&#x20;       self.rect = pygame.Rect(rect)

&#x20;       self.value = value

&#x20;       self.on\_change = on\_change

&#x20;       self.label = label

&#x20;       self.dragging = False



&#x20;   def \_set\_from\_x(self, x):

&#x20;       ratio = (x - self.rect.x) / self.rect.width

&#x20;       self.value = max(0.0, min(1.0, ratio))

&#x20;       if self.on\_change:

&#x20;           self.on\_change(self.value)



&#x20;   def handle\_event(self, event):

&#x20;       if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

&#x20;           handle\_x = self.rect.x + self.value \* self.rect.width

&#x20;           handle\_rect = pygame.Rect(handle\_x - 10, self.rect.y - 8, 20, self.rect.height + 16)

&#x20;           if handle\_rect.collidepoint(event.pos) or self.rect.collidepoint(event.pos):

&#x20;               self.dragging = True

&#x20;               self.\_set\_from\_x(event.pos\[0])

&#x20;       elif event.type == pygame.MOUSEBUTTONUP:

&#x20;           self.dragging = False

&#x20;       elif event.type == pygame.MOUSEMOTION and self.dragging:

&#x20;           self.\_set\_from\_x(event.pos\[0])



&#x20;   def draw(self, surface):

&#x20;       draw\_text(surface, f'{self.label}', (self.rect.x, self.rect.y - 28), size=20, color=COLOR\_MUTED)

&#x20;       pygame.draw.rect(surface, (50, 50, 68), self.rect, border\_radius=6)

&#x20;       fill\_width = int(self.rect.width \* self.value)

&#x20;       fill\_rect = pygame.Rect(self.rect.x, self.rect.y, fill\_width, self.rect.height)

&#x20;       pygame.draw.rect(surface, COLOR\_ACCENT, fill\_rect, border\_radius=6)

&#x20;       handle\_x = self.rect.x + fill\_width

&#x20;       pygame.draw.circle(surface, COLOR\_TEXT, (handle\_x, self.rect.centery), 11)

&#x20;       pct = int(self.value \* 100)

&#x20;       draw\_text(surface, f'{pct}%', (self.rect.right + 15, self.rect.centery), size=18, color=COLOR\_MUTED, center=False)





class Stepper:



&#x20;   def \_\_init\_\_(self, rect, value, lo, hi, on\_change=None, label=''):

&#x20;       self.rect = pygame.Rect(rect)

&#x20;       self.value = value

&#x20;       self.lo = lo

&#x20;       self.hi = hi

&#x20;       self.on\_change = on\_change

&#x20;       self.label = label

&#x20;       btn\_w = 40

&#x20;       self.left\_rect = pygame.Rect(rect\[0], rect\[1], btn\_w, rect\[3])

&#x20;       self.right\_rect = pygame.Rect(rect\[0] + rect\[2] - btn\_w, rect\[1], btn\_w, rect\[3])



&#x20;   def handle\_event(self, event):

&#x20;       if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

&#x20;           if self.left\_rect.collidepoint(event.pos):

&#x20;               self.value = max(self.lo, self.value - 1)

&#x20;               if self.on\_change:

&#x20;                   self.on\_change(self.value)

&#x20;           elif self.right\_rect.collidepoint(event.pos):

&#x20;               self.value = min(self.hi, self.value + 1)

&#x20;               if self.on\_change:

&#x20;                   self.on\_change(self.value)



&#x20;   def draw(self, surface):

&#x20;       draw\_text(surface, self.label, (self.rect.x, self.rect.y - 28), size=20, color=COLOR\_MUTED)

&#x20;       pygame.draw.rect(surface, (45, 45, 62), self.left\_rect, border\_radius=8)

&#x20;       pygame.draw.rect(surface, (45, 45, 62), self.right\_rect, border\_radius=8)

&#x20;       draw\_text(surface, '-', self.left\_rect.center, size=28, center=True)

&#x20;       draw\_text(surface, '+', self.right\_rect.center, size=28, center=True)

&#x20;       draw\_text(surface, str(self.value), self.rect.center, size=30, center=True, bold=True)





class MazePanel:



&#x20;   def \_\_init\_\_(self, maze, rect):

&#x20;       self.maze = maze

&#x20;       self.rect = pygame.Rect(rect)

&#x20;       self.board\_rect = pygame.Rect(rect\[0], rect\[1] + HUD\_HEIGHT, rect\[2], rect\[3] - HUD\_HEIGHT)

&#x20;       self.cell\_w = self.board\_rect.width / maze.cols

&#x20;       self.cell\_h = self.board\_rect.height / maze.rows

&#x20;       self.cell\_size = min(self.cell\_w, self.cell\_h)

&#x20;       used\_w = self.cell\_size \* maze.cols

&#x20;       used\_h = self.cell\_size \* maze.rows

&#x20;       self.offset\_x = self.board\_rect.x + (self.board\_rect.width - used\_w) / 2

&#x20;       self.offset\_y = self.board\_rect.y + (self.board\_rect.height - used\_h) / 2



&#x20;   def cell\_center(self, x, y):

&#x20;       px = self.offset\_x + (x + 0.5) \* self.cell\_size

&#x20;       py = self.offset\_y + (y + 0.5) \* self.cell\_size

&#x20;       return (px, py)



&#x20;   def cell\_rect(self, x, y):

&#x20;       left = round(self.offset\_x + x \* self.cell\_size)

&#x20;       top = round(self.offset\_y + y \* self.cell\_size)

&#x20;       right = round(self.offset\_x + (x + 1) \* self.cell\_size)

&#x20;       bottom = round(self.offset\_y + (y + 1) \* self.cell\_size)

&#x20;       return pygame.Rect(left, top, right - left, bottom - top)



&#x20;   def draw\_board\_bg(self, surface):

&#x20;       pygame.draw.rect(surface, COLOR\_PANEL\_BG, self.board\_rect, border\_radius=6)



&#x20;   def draw\_walls(self, surface):

&#x20;       line\_w = max(2, int(self.cell\_size \* 0.08))

&#x20;       maze = self.maze

&#x20;       for x in range(maze.cols):

&#x20;           for y in range(maze.rows):

&#x20;               cell = maze.grid\[x]\[y]

&#x20;               r = self.cell\_rect(x, y)

&#x20;               if cell.walls\['N']:

&#x20;                   pygame.draw.line(surface, COLOR\_WALL, r.topleft, r.topright, line\_w)

&#x20;               if cell.walls\['W']:

&#x20;                   pygame.draw.line(surface, COLOR\_WALL, r.topleft, r.bottomleft, line\_w)

&#x20;               if cell.walls\['S']:

&#x20;                   pygame.draw.line(surface, COLOR\_WALL, r.bottomleft, r.bottomright, line\_w)

&#x20;               if cell.walls\['E']:

&#x20;                   pygame.draw.line(surface, COLOR\_WALL, r.topright, r.bottomright, line\_w)

&#x20;       pygame.draw.rect(surface, COLOR\_WALL, self.board\_rect, width=line\_w, border\_radius=4)



&#x20;   def draw\_start\_end(self, surface):

&#x20;       sx, sy = self.maze.start

&#x20;       ex, ey = self.maze.end

&#x20;       s\_rect = self.cell\_rect(sx, sy).inflate(-self.cell\_size \* 0.3, -self.cell\_size \* 0.3)

&#x20;       e\_rect = self.cell\_rect(ex, ey).inflate(-self.cell\_size \* 0.3, -self.cell\_size \* 0.3)

&#x20;       pygame.draw.rect(surface, COLOR\_START, s\_rect, border\_radius=4)

&#x20;       pygame.draw.rect(surface, COLOR\_END, e\_rect, border\_radius=4)



&#x20;   def draw\_trail(self, surface, player):

&#x20;       if len(player.path\_cells) < 2:

&#x20;           return

&#x20;       points = \[self.cell\_center(x, y) for x, y in player.path\_cells]

&#x20;       pygame.draw.lines(surface, player.trail\_color, False, points, width=max(2, int(self.cell\_size \* 0.15)))



&#x20;   def draw\_player(self, surface, player):

&#x20;       cx, cy = self.cell\_center(\*player.cell)

&#x20;       radius = int(self.cell\_size \* 0.32)

&#x20;       pygame.draw.circle(surface, player.color, (int(cx), int(cy)), radius)

&#x20;       pygame.draw.circle(surface, (255, 255, 255), (int(cx), int(cy)), radius, width=2)



&#x20;   def draw\_hud(self, surface, player, score, label, key\_hint):

&#x20;       hud\_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, HUD\_HEIGHT)

&#x20;       pygame.draw.rect(surface, COLOR\_PANEL\_BG, hud\_rect, border\_radius=6)

&#x20;       draw\_text(surface, label, (hud\_rect.x + 14, hud\_rect.y + 8), size=20, color=player.color, bold=True)

&#x20;       draw\_text(surface, key\_hint, (hud\_rect.x + 14, hud\_rect.y + 32), size=14, color=COLOR\_MUTED)

&#x20;       draw\_text(surface, f'Score: {score}', (hud\_rect.right - 14, hud\_rect.y + 8), size=20, color=COLOR\_TEXT, align\_right=True)

&#x20;       t = player.elapsed\_time

&#x20;       status = 'FINISHED' if player.finished else f'{t:0.1f}s'

&#x20;       draw\_text(surface, status, (hud\_rect.right - 14, hud\_rect.y + 32), size=16, color=COLOR\_MUTED, align\_right=True)



&#x20;   def draw(self, surface, player, score, label, key\_hint):

&#x20;       self.draw\_board\_bg(surface)

&#x20;       self.draw\_start\_end(surface)

&#x20;       self.draw\_trail(surface, player)

&#x20;       self.draw\_walls(surface)

&#x20;       self.draw\_player(surface, player)

&#x20;       self.draw\_hud(surface, player, score, label, key\_hint)





class MenuScene:



&#x20;   def \_\_init\_\_(self, app):

&#x20;       self.app = app

&#x20;       self.\_layout(app.width, app.height)



&#x20;   def resize(self, width, height):

&#x20;       self.\_layout(width, height)



&#x20;   def \_layout(self, width, height):

&#x20;       self.width, self.height = (width, height)

&#x20;       cx = width // 2

&#x20;       top = max(260, int(height \* 0.42))

&#x20;       self.rounds\_stepper = Stepper((cx - 90, top, 180, 50), self.app.settings\['rounds'], 1, 15, on\_change=self.\_on\_rounds\_change, label='Rounds to play')

&#x20;       self.play\_button = Button((cx - 110, top + 100, 220, 60), 'Play', self.\_start\_game, font\_size=30)

&#x20;       self.settings\_button = Button((cx - 110, top + 180, 220, 50), 'Settings', self.\_open\_settings)

&#x20;       self.quit\_button = Button((cx - 110, top + 250, 220, 50), 'Quit', self.\_quit)

&#x20;       self.widgets = \[self.rounds\_stepper, self.play\_button, self.settings\_button, self.quit\_button]



&#x20;   def \_on\_rounds\_change(self, value):

&#x20;       self.app.settings\['rounds'] = value

&#x20;       self.app.save\_settings()

&#x20;       self.app.audio.play('menu\_select')



&#x20;   def \_start\_game(self):

&#x20;       self.app.audio.play('menu\_confirm')

&#x20;       self.app.start\_new\_match(self.rounds\_stepper.value)



&#x20;   def \_open\_settings(self):

&#x20;       self.app.audio.play('menu\_select')

&#x20;       self.app.go\_to('settings')



&#x20;   def \_quit(self):

&#x20;       self.app.quit()



&#x20;   def handle\_event(self, event):

&#x20;       for w in self.widgets:

&#x20;           w.handle\_event(event)



&#x20;   def update(self, dt):

&#x20;       pass



&#x20;   def draw(self, surface):

&#x20;       surface.fill((18, 18, 26))

&#x20;       cx = self.width // 2

&#x20;       title\_y = max(90, int(self.height \* 0.16))

&#x20;       draw\_text(surface, 'MAZE RACE', (cx, title\_y), size=min(64, self.width // 14), color=COLOR\_ACCENT, bold=True, center=True)

&#x20;       draw\_text(surface, 'Two racers. Two identical mazes. One optimal path.', (cx, title\_y + 55), size=20, color=COLOR\_MUTED, center=True)

&#x20;       draw\_text(surface, 'Player 1: W A S D    |    Player 2: Arrow Keys', (cx, title\_y + 100), size=18, color=COLOR\_TEXT, center=True)

&#x20;       draw\_text(surface, 'Tap to step one cell - hold to accelerate', (cx, title\_y + 128), size=16, color=COLOR\_MUTED, center=True)

&#x20;       for w in self.widgets:

&#x20;           w.draw(surface)

&#x20;       draw\_text(surface, 'F11: toggle fullscreen', (10, self.height - 24), size=14, color=COLOR\_MUTED)





class SettingsScene:



&#x20;   def \_\_init\_\_(self, app):

&#x20;       self.app = app

&#x20;       self.\_layout(app.width, app.height)



&#x20;   def resize(self, width, height):

&#x20;       self.\_layout(width, height)



&#x20;   def \_layout(self, width, height):

&#x20;       self.width, self.height = (width, height)

&#x20;       cx = width // 2

&#x20;       slider\_x = cx - 150

&#x20;       slider\_w = 300

&#x20;       top = max(220, int(height \* 0.3))

&#x20;       gap = 90

&#x20;       self.music\_slider = Slider((slider\_x, top, slider\_w, 14), self.app.settings\['music\_volume'], on\_change=self.\_set\_music\_volume, label='Music Volume')

&#x20;       self.sfx\_slider = Slider((slider\_x, top + gap, slider\_w, 14), self.app.settings\['sfx\_volume'], on\_change=self.\_set\_sfx\_volume, label='SFX Volume')

&#x20;       self.movement\_slider = Slider((slider\_x, top + gap \* 2, slider\_w, 14), self.\_speed\_to\_slider(self.app.settings\['movement\_speed']), on\_change=self.\_set\_movement\_speed, label='Movement Acceleration')

&#x20;       self.fullscreen\_button = Button((cx - 110, top + gap \* 3 + 10, 220, 50), 'Fullscreen: ON' if self.app.fullscreen else 'Fullscreen: OFF', self.\_toggle\_fullscreen)

&#x20;       self.back\_button = Button((cx - 100, top + gap \* 3 + 80, 200, 50), 'Back', self.\_back)

&#x20;       self.widgets = \[self.music\_slider, self.sfx\_slider, self.movement\_slider, self.fullscreen\_button, self.back\_button]



&#x20;   @staticmethod

&#x20;   def \_speed\_to\_slider(speed):

&#x20;       return (speed - 0.5) / 1.5



&#x20;   @staticmethod

&#x20;   def \_slider\_to\_speed(value):

&#x20;       return 0.5 + value \* 1.5



&#x20;   def \_set\_music\_volume(self, value):

&#x20;       self.app.audio.set\_music\_volume(value)

&#x20;       self.app.settings\['music\_volume'] = value

&#x20;       self.app.save\_settings()



&#x20;   def \_set\_sfx\_volume(self, value):

&#x20;       self.app.audio.set\_sfx\_volume(value)

&#x20;       self.app.settings\['sfx\_volume'] = value

&#x20;       self.app.save\_settings()

&#x20;       self.app.audio.play('menu\_select')



&#x20;   def \_set\_movement\_speed(self, value):

&#x20;       speed = self.\_slider\_to\_speed(value)

&#x20;       self.app.settings\['movement\_speed'] = speed

&#x20;       self.app.save\_settings()



&#x20;   def \_toggle\_fullscreen(self):

&#x20;       self.app.audio.play('menu\_select')

&#x20;       self.app.toggle\_fullscreen()



&#x20;   def \_back(self):

&#x20;       self.app.audio.play('menu\_select')

&#x20;       self.app.go\_to('menu')



&#x20;   def handle\_event(self, event):

&#x20;       for w in self.widgets:

&#x20;           w.handle\_event(event)



&#x20;   def update(self, dt):

&#x20;       pass



&#x20;   def draw(self, surface):

&#x20;       surface.fill((18, 18, 26))

&#x20;       cx = self.width // 2

&#x20;       draw\_text(surface, 'SETTINGS', (cx, max(80, int(self.height \* 0.12))), size=48, color=COLOR\_ACCENT, bold=True, center=True)

&#x20;       for w in self.widgets:

&#x20;           w.draw(surface)

&#x20;       draw\_text(surface, 'Movement acceleration controls how quickly held keys speed up. F11 also toggles fullscreen.', (cx, self.height - 30), size=15, color=COLOR\_MUTED, center=True)





P1\_KEYS = {pygame.K\_w: 'N', pygame.K\_s: 'S', pygame.K\_a: 'W', pygame.K\_d: 'E'}

P2\_KEYS = {pygame.K\_UP: 'N', pygame.K\_DOWN: 'S', pygame.K\_LEFT: 'W', pygame.K\_RIGHT: 'E'}





def \_movement\_cfg(settings):

&#x20;   speed = settings.get('movement\_speed', 1.0)

&#x20;   return {'initial\_delay': DEFAULT\_INITIAL\_REPEAT\_DELAY / speed, 'start\_interval': DEFAULT\_START\_REPEAT\_INTERVAL / speed, 'min\_interval': DEFAULT\_MIN\_REPEAT\_INTERVAL / speed, 'accel\_time': DEFAULT\_ACCEL\_TIME}





class GameScene:

&#x20;   STATE\_COUNTDOWN = 'countdown'

&#x20;   STATE\_PLAYING = 'playing'

&#x20;   STATE\_ROUND\_SUMMARY = 'round\_summary'



&#x20;   def \_\_init\_\_(self, app, total\_rounds):

&#x20;       self.app = app

&#x20;       self.total\_rounds = total\_rounds

&#x20;       self.round\_number = 0

&#x20;       self.total\_scores = {'p1': 0, 'p2': 0}

&#x20;       self.last\_round\_result = None

&#x20;       self.maze = None

&#x20;       self.\_layout(app.width, app.height)

&#x20;       self.\_start\_round()



&#x20;   def resize(self, width, height):

&#x20;       self.\_layout(width, height)

&#x20;       if self.maze is not None:

&#x20;           self.left\_panel = MazePanel(self.maze, self.left\_rect)

&#x20;           self.right\_panel = MazePanel(self.maze, self.right\_rect)



&#x20;   def \_layout(self, width, height):

&#x20;       self.width, self.height = (width, height)

&#x20;       margin = MAZE\_MARGIN if width >= 900 else max(10, MAZE\_MARGIN // 2)

&#x20;       gap = PANEL\_GAP if width >= 900 else max(8, PANEL\_GAP // 2)

&#x20;       panel\_w = (width - 2 \* margin - gap) // 2

&#x20;       panel\_h = height - 2 \* margin

&#x20;       self.left\_rect = (margin, margin, panel\_w, panel\_h)

&#x20;       self.right\_rect = (margin + panel\_w + gap, margin, panel\_w, panel\_h)

&#x20;       self.continue\_button = Button((width // 2 - 110, height - 110, 220, 55), 'Continue', self.\_advance\_from\_summary, font\_size=26)



&#x20;   def \_start\_round(self):

&#x20;       self.round\_number += 1

&#x20;       seed = random.randint(0, 2 \*\* 31)

&#x20;       maze = Maze(DEFAULT\_MAZE\_COLS, DEFAULT\_MAZE\_ROWS, seed=seed)

&#x20;       self.maze = maze

&#x20;       cfg = \_movement\_cfg(self.app.settings)

&#x20;       self.p1 = Player('Player 1', maze, COLOR\_P1, COLOR\_P1\_TRAIL, P1\_KEYS, cfg)

&#x20;       self.p2 = Player('Player 2', maze, COLOR\_P2, COLOR\_P2\_TRAIL, P2\_KEYS, cfg)

&#x20;       self.left\_panel = MazePanel(maze, self.left\_rect)

&#x20;       self.right\_panel = MazePanel(maze, self.right\_rect)

&#x20;       self.state = self.STATE\_COUNTDOWN

&#x20;       self.countdown\_start = time.time()

&#x20;       self.countdown\_last\_tick = None

&#x20;       self.round\_start\_time = None



&#x20;   def \_advance\_from\_summary(self):

&#x20;       self.app.audio.play('menu\_select')

&#x20;       if self.round\_number >= self.total\_rounds:

&#x20;           self.app.finish\_match(self.total\_scores)

&#x20;       else:

&#x20;           self.\_start\_round()



&#x20;   def handle\_event(self, event):

&#x20;       if self.state == self.STATE\_PLAYING:

&#x20;           if event.type == pygame.KEYDOWN:

&#x20;               prev1, prev2 = (self.p1.move\_count, self.p2.move\_count)

&#x20;               self.p1.key\_down(event.key, time.time())

&#x20;               self.p2.key\_down(event.key, time.time())

&#x20;               self.\_feedback(self.p1, prev1)

&#x20;               self.\_feedback(self.p2, prev2)

&#x20;           elif event.type == pygame.KEYUP:

&#x20;               self.p1.key\_up(event.key)

&#x20;               self.p2.key\_up(event.key)

&#x20;       elif self.state == self.STATE\_ROUND\_SUMMARY:

&#x20;           self.continue\_button.handle\_event(event)

&#x20;       if event.type == pygame.KEYDOWN and event.key == pygame.K\_ESCAPE:

&#x20;           self.app.go\_to('menu')



&#x20;   def \_feedback(self, player, prev\_move\_count):

&#x20;       if player.move\_count > prev\_move\_count:

&#x20;           self.app.audio.play('step' if player.move\_count % 2 == 0 else 'step\_alt')

&#x20;       elif player.bump\_flag:

&#x20;           self.app.audio.play('wall\_bump')



&#x20;   def update(self, dt):

&#x20;       now = time.time()

&#x20;       if self.state == self.STATE\_COUNTDOWN:

&#x20;           elapsed = now - self.countdown\_start

&#x20;           remaining = 3 - int(elapsed)

&#x20;           if remaining != self.countdown\_last\_tick:

&#x20;               self.countdown\_last\_tick = remaining

&#x20;               if remaining > 0:

&#x20;                   self.app.audio.play('countdown\_beep')

&#x20;               elif remaining == 0:

&#x20;                   self.app.audio.play('countdown\_go')

&#x20;           if elapsed >= 3.0:

&#x20;               self.state = self.STATE\_PLAYING

&#x20;               self.round\_start\_time = now

&#x20;               self.p1.start\_timer()

&#x20;               self.p2.start\_timer()

&#x20;       elif self.state == self.STATE\_PLAYING:

&#x20;           prev1, prev2 = (self.p1.move\_count, self.p2.move\_count)

&#x20;           self.p1.update(now)

&#x20;           self.p2.update(now)

&#x20;           self.\_feedback(self.p1, prev1)

&#x20;           self.\_feedback(self.p2, prev2)

&#x20;           for p in (self.p1, self.p2):

&#x20;               if p.finished and (not getattr(p, '\_finish\_sound\_played', False)):

&#x20;                   self.app.audio.play('finish')

&#x20;                   p.\_finish\_sound\_played = True

&#x20;           round\_elapsed = now - self.round\_start\_time

&#x20;           timeout = round\_elapsed >= MAX\_ROUND\_SECONDS

&#x20;           if self.p1.finished and self.p2.finished or timeout:

&#x20;               if timeout:

&#x20;                   for p in (self.p1, self.p2):

&#x20;                       if not p.finished:

&#x20;                           p.finished = True

&#x20;                           p.finish\_time = now

&#x20;               self.\_finish\_round()



&#x20;   def \_finish\_round(self):

&#x20;       optimal\_len = self.maze.optimal\_length

&#x20;       s1, path1, time1, eff1 = compute\_round\_score(optimal\_len, self.p1.move\_count, self.p1.elapsed\_time)

&#x20;       s2, path2, time2, eff2 = compute\_round\_score(optimal\_len, self.p2.move\_count, self.p2.elapsed\_time)

&#x20;       self.total\_scores\['p1'] += s1

&#x20;       self.total\_scores\['p2'] += s2

&#x20;       self.last\_round\_result = {'p1': {'score': s1, 'path': path1, 'time': time1, 'eff': eff1, 'moves': self.p1.move\_count, 'seconds': self.p1.elapsed\_time}, 'p2': {'score': s2, 'path': path2, 'time': time2, 'eff': eff2, 'moves': self.p2.move\_count, 'seconds': self.p2.elapsed\_time}, 'optimal\_len': optimal\_len}

&#x20;       self.state = self.STATE\_ROUND\_SUMMARY

&#x20;       self.app.audio.play('round\_end')



&#x20;   def draw(self, surface):

&#x20;       surface.fill((18, 18, 26))

&#x20;       self.left\_panel.draw(surface, self.p1, self.total\_scores\['p1'], 'PLAYER 1', 'W A S D')

&#x20;       self.right\_panel.draw(surface, self.p2, self.total\_scores\['p2'], 'PLAYER 2', 'ARROW KEYS')

&#x20;       draw\_text(surface, f'Round {self.round\_number} / {self.total\_rounds}', (self.width // 2, 20), size=22, color=COLOR\_TEXT, center=True)

&#x20;       if self.state == self.STATE\_COUNTDOWN:

&#x20;           self.\_draw\_countdown\_overlay(surface)

&#x20;       elif self.state == self.STATE\_ROUND\_SUMMARY:

&#x20;           self.\_draw\_round\_summary(surface)



&#x20;   def \_draw\_countdown\_overlay(self, surface):

&#x20;       overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

&#x20;       overlay.fill((10, 10, 15, 160))

&#x20;       surface.blit(overlay, (0, 0))

&#x20;       elapsed = time.time() - self.countdown\_start

&#x20;       remaining = 3 - int(elapsed)

&#x20;       label = 'GO!' if remaining <= 0 else str(remaining)

&#x20;       draw\_text(surface, label, (self.width // 2, self.height // 2), size=110, color=COLOR\_ACCENT, bold=True, center=True)



&#x20;   def \_draw\_round\_summary(self, surface):

&#x20;       overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

&#x20;       overlay.fill((10, 10, 15, 200))

&#x20;       surface.blit(overlay, (0, 0))

&#x20;       cx = self.width // 2

&#x20;       r = self.last\_round\_result

&#x20;       draw\_text(surface, f'Round {self.round\_number} Complete', (cx, 130), size=42, color=COLOR\_ACCENT, bold=True, center=True)

&#x20;       draw\_text(surface, f"Optimal path length: {r\['optimal\_len']} cells", (cx, 175), size=18, color=COLOR\_MUTED, center=True)

&#x20;       col\_gap = min(220, self.width // 5)

&#x20;       self.\_draw\_result\_column(surface, cx - col\_gap, 'PLAYER 1', COLOR\_P1, r\['p1'])

&#x20;       self.\_draw\_result\_column(surface, cx + col\_gap, 'PLAYER 2', COLOR\_P2, r\['p2'])

&#x20;       draw\_text(surface, f"Total  -  P1: {self.total\_scores\['p1']}    P2: {self.total\_scores\['p2']}", (cx, 470), size=26, color=COLOR\_TEXT, center=True, bold=True)

&#x20;       self.continue\_button.label = 'Final Results' if self.round\_number >= self.total\_rounds else 'Next Round'

&#x20;       self.continue\_button.draw(surface)



&#x20;   def \_draw\_result\_column(self, surface, cx, label, color, result):

&#x20;       y = 230

&#x20;       draw\_text(surface, label, (cx, y), size=24, color=color, bold=True, center=True)

&#x20;       draw\_text(surface, f"Moves: {result\['moves']}  (efficiency {result\['eff'] \* 100:0.0f}%)", (cx, y + 40), size=18, color=COLOR\_TEXT, center=True)

&#x20;       draw\_text(surface, f"Time: {result\['seconds']:0.1f}s", (cx, y + 65), size=18, color=COLOR\_TEXT, center=True)

&#x20;       draw\_text(surface, f"Path pts: {result\['path']}   Time pts: {result\['time']}", (cx, y + 90), size=18, color=COLOR\_MUTED, center=True)

&#x20;       draw\_text(surface, f"Round score: {result\['score']}", (cx, y + 120), size=22, color=COLOR\_ACCENT, bold=True, center=True)





class ResultsScene:



&#x20;   def \_\_init\_\_(self, app, total\_scores):

&#x20;       self.app = app

&#x20;       self.total\_scores = total\_scores

&#x20;       self.played\_sound = False

&#x20;       self.\_layout(app.width, app.height)



&#x20;   def resize(self, width, height):

&#x20;       self.\_layout(width, height)



&#x20;   def \_layout(self, width, height):

&#x20;       self.width, self.height = (width, height)

&#x20;       cx = width // 2

&#x20;       button\_y = max(400, int(height \* 0.68))

&#x20;       self.rematch\_button = Button((cx - 240, button\_y, 220, 55), 'Rematch', self.\_rematch, font\_size=26)

&#x20;       self.menu\_button = Button((cx + 20, button\_y, 220, 55), 'Main Menu', self.\_to\_menu, font\_size=26)

&#x20;       self.widgets = \[self.rematch\_button, self.menu\_button]



&#x20;   def \_rematch(self):

&#x20;       self.app.audio.play('menu\_confirm')

&#x20;       self.app.start\_new\_match(self.app.settings\['rounds'])



&#x20;   def \_to\_menu(self):

&#x20;       self.app.audio.play('menu\_select')

&#x20;       self.app.go\_to('menu')



&#x20;   def handle\_event(self, event):

&#x20;       for w in self.widgets:

&#x20;           w.handle\_event(event)



&#x20;   def update(self, dt):

&#x20;       if not self.played\_sound:

&#x20;           self.app.audio.play('victory')

&#x20;           self.played\_sound = True



&#x20;   def draw(self, surface):

&#x20;       surface.fill((18, 18, 26))

&#x20;       cx = self.width // 2

&#x20;       p1, p2 = (self.total\_scores\['p1'], self.total\_scores\['p2'])

&#x20;       if p1 > p2:

&#x20;           winner\_text, winner\_color = ('PLAYER 1 WINS!', COLOR\_P1)

&#x20;       elif p2 > p1:

&#x20;           winner\_text, winner\_color = ('PLAYER 2 WINS!', COLOR\_P2)

&#x20;       else:

&#x20;           winner\_text, winner\_color = ("IT'S A TIE!", COLOR\_ACCENT)

&#x20;       title\_y = max(120, int(self.height \* 0.2))

&#x20;       draw\_text(surface, winner\_text, (cx, title\_y), size=min(64, self.width // 14), color=winner\_color, bold=True, center=True)

&#x20;       draw\_text(surface, 'Final Scores', (cx, title\_y + 80), size=22, color=COLOR\_MUTED, center=True)

&#x20;       draw\_text(surface, f'Player 1: {p1}', (cx - 180, title\_y + 140), size=34, color=COLOR\_P1, bold=True, center=True)

&#x20;       draw\_text(surface, f'Player 2: {p2}', (cx + 180, title\_y + 140), size=34, color=COLOR\_P2, bold=True, center=True)

&#x20;       for w in self.widgets:

&#x20;           w.draw(surface)





class App:



&#x20;   def \_\_init\_\_(self):

&#x20;       pygame.init()

&#x20;       self.settings = load\_settings()

&#x20;       self.fullscreen = bool(self.settings.get('fullscreen', False))

&#x20;       try:

&#x20;           info = pygame.display.Info()

&#x20;           desktop\_w, desktop\_h = (info.current\_w, info.current\_h)

&#x20;       except pygame.error:

&#x20;           desktop\_w, desktop\_h = (DEFAULT\_WINDOW\_WIDTH, DEFAULT\_WINDOW\_HEIGHT)

&#x20;       start\_w = min(DEFAULT\_WINDOW\_WIDTH, int(desktop\_w \* 0.9))

&#x20;       start\_h = min(DEFAULT\_WINDOW\_HEIGHT, int(desktop\_h \* 0.85))

&#x20;       start\_w = max(start\_w, MIN\_WINDOW\_WIDTH)

&#x20;       start\_h = max(start\_h, MIN\_WINDOW\_HEIGHT)

&#x20;       self.windowed\_size = (start\_w, start\_h)

&#x20;       if self.fullscreen:

&#x20;           self.screen = pygame.display.set\_mode((desktop\_w, desktop\_h), pygame.FULLSCREEN)

&#x20;       else:

&#x20;           self.screen = pygame.display.set\_mode(self.windowed\_size, pygame.RESIZABLE)

&#x20;       pygame.display.set\_caption('Maze Race')

&#x20;       self.width, self.height = self.screen.get\_size()

&#x20;       self.clock = pygame.time.Clock()

&#x20;       self.audio = AudioManager(self.settings)

&#x20;       self.audio.start\_music()

&#x20;       self.running = True

&#x20;       self.scene = MenuScene(self)



&#x20;   def save\_settings(self):

&#x20;       save\_settings(self.settings)



&#x20;   def go\_to(self, name):

&#x20;       if name == 'menu':

&#x20;           self.scene = MenuScene(self)

&#x20;       elif name == 'settings':

&#x20;           self.scene = SettingsScene(self)



&#x20;   def start\_new\_match(self, rounds):

&#x20;       self.scene = GameScene(self, rounds)



&#x20;   def finish\_match(self, total\_scores):

&#x20;       self.scene = ResultsScene(self, total\_scores)



&#x20;   def quit(self):

&#x20;       self.running = False



&#x20;   def toggle\_fullscreen(self):

&#x20;       self.fullscreen = not self.fullscreen

&#x20;       if self.fullscreen:

&#x20;           self.windowed\_size = (self.width, self.height)

&#x20;           info = pygame.display.Info()

&#x20;           self.screen = pygame.display.set\_mode((info.current\_w, info.current\_h), pygame.FULLSCREEN)

&#x20;       else:

&#x20;           self.screen = pygame.display.set\_mode(self.windowed\_size, pygame.RESIZABLE)

&#x20;       self.width, self.height = self.screen.get\_size()

&#x20;       self.settings\['fullscreen'] = self.fullscreen

&#x20;       self.save\_settings()

&#x20;       self.\_notify\_resize()



&#x20;   def \_handle\_resize(self, w, h):

&#x20;       w = max(w, MIN\_WINDOW\_WIDTH)

&#x20;       h = max(h, MIN\_WINDOW\_HEIGHT)

&#x20;       if not self.fullscreen:

&#x20;           self.screen = pygame.display.set\_mode((w, h), pygame.RESIZABLE)

&#x20;           self.windowed\_size = (w, h)

&#x20;       self.width, self.height = self.screen.get\_size()

&#x20;       self.\_notify\_resize()



&#x20;   def \_notify\_resize(self):

&#x20;       if hasattr(self.scene, 'resize'):

&#x20;           self.scene.resize(self.width, self.height)



&#x20;   def run(self):

&#x20;       while self.running:

&#x20;           dt = self.clock.tick(FPS) / 1000.0

&#x20;           for event in pygame.event.get():

&#x20;               if event.type == pygame.QUIT:

&#x20;                   self.running = False

&#x20;               elif event.type == pygame.VIDEORESIZE:

&#x20;                   self.\_handle\_resize(event.w, event.h)

&#x20;               elif event.type == pygame.KEYDOWN and event.key == pygame.K\_F11:

&#x20;                   self.toggle\_fullscreen()

&#x20;               else:

&#x20;                   self.scene.handle\_event(event)

&#x20;           self.scene.update(dt)

&#x20;           self.scene.draw(self.screen)

&#x20;           pygame.display.flip()

&#x20;       self.save\_settings()

&#x20;       pygame.quit()





def main():

&#x20;   app = App()

&#x20;   try:

&#x20;       app.run()

&#x20;   except KeyboardInterrupt:

&#x20;       pass

&#x20;   finally:

&#x20;       pygame.quit()

&#x20;   sys.exit(0)

if \_\_name\_\_ == '\_\_main\_\_':

&#x20;   main()

