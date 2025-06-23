import pygame
import random
import os

# --------------------------------------------------
# Initialization
# --------------------------------------------------

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

# --------------------------------------------------
# Constants and Configuration
# --------------------------------------------------

BLOCK_SIZE = 30; COLS, ROWS = 10, 20; GRID_WIDTH = COLS * BLOCK_SIZE; PANEL_WIDTH = 250
WIDTH, HEIGHT = GRID_WIDTH + PANEL_WIDTH, ROWS * BLOCK_SIZE; FPS = 60
FALL_SPEED_DEFAULT = 500; FALL_SPEED_SOFT_DROP = 50; FALL_SPEED_SONIC_DROP = 10
INTERPOLATION_SPEED = 0.3; LINE_CLEAR_FLASH_DURATION = 150; LINE_CLEAR_SHATTER_DURATION = 350
SCORE_MAP = {1: 100, 2: 300, 3: 500, 4: 800}

# --------------------------------------------------
# Color Utilities & Definitions
# --------------------------------------------------

def rgb(r, g, b): return (r, g, b)
BG_COLOR = rgb(20, 20, 30); GRID_COLOR = rgb(40, 40, 60); PANEL_COLOR = rgb(30, 30, 50)
PANEL_BOX_COLOR = rgb(25, 25, 40); TEXT_COLOR = rgb(230, 230, 230); GHOST_COLOR = rgb(255, 255, 255)
BUTTON_COLOR = rgb(80, 80, 110); BUTTON_HOVER_COLOR = rgb(110, 110, 140); BUTTON_TEXT_COLOR = rgb(255, 255, 255)
SHAPES = {'I': [[1,1,1,1]], 'O': [[1,1],[1,1]], 'T': [[0,1,0],[1,1,1]], 'S': [[0,1,1],[1,1,0]], 'Z': [[1,1,0],[0,1,1]], 'J': [[1,0,0],[1,1,1]], 'L': [[0,0,1],[1,1,1]],}
COLORS = {'I': rgb(0, 255, 255), 'O': rgb(255, 255, 0), 'T': rgb(128, 0, 128), 'S': rgb(0, 255, 0), 'Z': rgb(255, 0, 0), 'J': rgb(0, 0, 255), 'L': rgb(255, 127, 0),}

class Piece:
    def __init__(self, shape_key):
        self.shape_key = shape_key; self.shape = SHAPES[shape_key]; self.color = COLORS[shape_key]
        self.x = COLS // 2 - len(self.shape[0]) // 2; self.y = 0; self.visual_y = -2 * BLOCK_SIZE # Start off-screen

try: ASSET_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError: ASSET_DIR = os.getcwd()
FONT_PATH = os.path.join(ASSET_DIR, 'PressStart2P-Regular.ttf'); CUSTOM_FONT = os.path.exists(FONT_PATH)

def load_sound(fname):
    path = os.path.join(ASSET_DIR, fname);
    if not os.path.exists(path): return None
    try: return pygame.mixer.Sound(path)
    except pygame.error: return None

LINE_CLEAR_SND = load_sound('line_clear.wav'); ROTATE_SND = load_sound('rotate.wav'); DROP_SND = load_sound('drop.wav')
HARD_DROP_SND = load_sound('drop.wav'); LOCK_SND = load_sound('lock.wav') or DROP_SND

class Particle:
    def __init__(self, x, y, color, vel_x, vel_y, size, lifespan, gravity=0):
        self.x, self.y = x, y; self.color = color; self.vel_x, self.vel_y = vel_x, vel_y
        self.size = size; self.lifespan = lifespan; self.max_lifespan = lifespan; self.gravity = gravity
    def update(self, dt):
        self.lifespan -= dt; self.vel_y += self.gravity * (dt / 16)
        self.x += self.vel_x * (dt / 16); self.y += self.vel_y * (dt / 16)
        self.size = max(0, self.size - 0.1 * (dt / 16))
    def draw(self, surface):
        if self.lifespan > 0:
            int_size = int(self.size)
            if int_size <= 0: return
            alpha = max(0, min(255, int(255 * (self.lifespan / self.max_lifespan))))
            particle_surf = pygame.Surface((int_size, int_size), pygame.SRCALPHA)
            final_color = self.color + (alpha,)
            pygame.draw.rect(particle_surf, final_color, (0, 0, int_size, int_size), border_radius=2)
            surface.blit(particle_surf, (self.x - int_size / 2, self.y - int_size / 2))

def spawn_block_shatter_particles(x, y, color, particles):
    for _ in range(10):
        px, py = (x + 0.5) * BLOCK_SIZE, (y + 0.5) * BLOCK_SIZE
        vel_x = random.uniform(-4, 4); vel_y = random.uniform(-6, 2)
        size = random.uniform(3, 8); particles.append(Particle(px, py, color, vel_x, vel_y, size, 400, gravity=0.4))

def spawn_hard_drop_trace_particles(piece, final_y, particles):
    start_y = int(piece.y)
    for y_step in range(start_y, final_y):
        for block_x_offset, block_y_offset in get_shape_positions(piece, adj_y=y_step - piece.y):
            px = (block_x_offset + 0.5) * BLOCK_SIZE; py = (block_y_offset + 0.5) * BLOCK_SIZE
            particles.append(Particle(px, py, piece.color, 0, 0, BLOCK_SIZE * 0.8, 150, gravity=0))

class Button:
    def __init__(self, x, y, width, height, text=''):
        self.rect = pygame.Rect(x, y, width, height); self.text = text; self.is_hovered = False
    def draw(self, surface):
        color = BUTTON_HOVER_COLOR if self.is_hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=8); pygame.draw.rect(surface, GRID_COLOR, self.rect, 2, border_radius=8)
        if self.text:
            font = pygame.font.Font(FONT_PATH, 16) if CUSTOM_FONT else pygame.font.SysFont('consolas', 18, bold=True)
            text_surf = font.render(self.text, True, BUTTON_TEXT_COLOR); text_rect = text_surf.get_rect(center=self.rect.center); surface.blit(text_surf, text_rect)
    def check_hover(self, mouse_pos): self.is_hovered = self.rect.collidepoint(mouse_pos)
    def is_clicked(self, event): return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered

def draw_text(surface, text, size, x, y, center=False):
    font = pygame.font.Font(FONT_PATH, size) if CUSTOM_FONT else pygame.font.SysFont('consolas', size, bold=True)
    surf = font.render(text, True, TEXT_COLOR); rect = surf.get_rect(center=(x, y)) if center else surf.get_rect(topleft=(x, y)); surface.blit(surf, rect)

def draw_block(surface, color, rect):
    light = tuple(min(c + 50, 255) for c in color); dark  = tuple(max(c - 50, 0) for c in color)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.polygon(surface, light, [rect.topleft, rect.topright, (rect.right-2, rect.top+2), (rect.left+2, rect.top+2)])
    pygame.draw.polygon(surface, light, [rect.topleft, rect.bottomleft, (rect.left+2, rect.bottom-2), (rect.left+2, rect.top+2)])
    pygame.draw.polygon(surface, dark,  [rect.bottomright, rect.topright, (rect.right-2, rect.top+2), (rect.right-2, rect.bottom-2)])
    pygame.draw.polygon(surface, dark,  [rect.bottomright, rect.bottomleft, (rect.left+2, rect.bottom-2), (rect.right-2, rect.bottom-2)])
    pygame.draw.rect(surface, (0, 0, 0), rect, 1)

def desaturate_color(color):
    gray = int(0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]); return (gray, gray, gray)

piece_bag = []
def refill_bag(): global piece_bag; piece_bag = list(SHAPES.keys()); random.shuffle(piece_bag)
def get_next_from_bag():
    if not piece_bag: refill_bag()
    return Piece(piece_bag.pop())

def create_grid(locked_positions):
    grid = [[BG_COLOR for _ in range(COLS)] for _ in range(ROWS)]
    for (x, y), col in locked_positions.items():
        if 0 <= y < ROWS and 0 <= x < COLS: grid[y][x] = col
    return grid

def rotate_shape(shape): return [list(row) for row in zip(*shape[::-1])]

def get_shape_positions(piece, adj_x=0, adj_y=0, shape=None):
    matrix = shape or piece.shape; positions = []
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            if val: positions.append((piece.x + j + adj_x, int(piece.y) + i + adj_y))
    return positions

def is_valid_position(piece, grid, adj_x=0, adj_y=0, shape=None):
    for x, y in get_shape_positions(piece, adj_x, adj_y, shape):
        if not (0 <= x < COLS and 0 <= y < ROWS): return False
        if y >= 0 and grid[y][x] != BG_COLOR: return False
    return True

def check_for_full_rows(grid):
    full_rows = []
    for y, row in enumerate(grid):
        if all(color != BG_COLOR for color in row):
            full_rows.append(y)
    return full_rows

def clear_rows(full_rows, locked):
    if not full_rows: return locked, 0
    new_locked = {};
    for (x, y), col in locked.items():
        if y in full_rows: continue
        shift = sum(1 for cleared_y in full_rows if y < cleared_y)
        new_locked[(x, y + shift)] = col
    return new_locked, len(full_rows)

def reset_game():
    refill_bag()
    return ({}, get_next_from_bag(), get_next_from_bag(), 0, 0, None, False, False, [])

def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT)); pygame.display.set_caption('Tetris By Lucky-Roux')
    clock = pygame.time.Clock()

    # Generated code
    music_loaded = False
    try: pygame.mixer.music.load(os.path.join(ASSET_DIR, 'background.mp3')); pygame.mixer.music.set_volume(0.3); music_loaded = True; pygame.mixer.music.play(-1)
    except pygame.error: pass

    state = reset_game()
    (locked_positions, current_piece, next_piece, score, fall_time,
     line_clear_anim, game_over, is_paused, particles) = state

    is_soft_dropping, is_sonic_dropping = False, False; sonic_drop_score = 0

    buttons = {'replay': Button(GRID_WIDTH//2-125, HEIGHT//2, 120, 50, 'Replay'), 'quit_go': Button(GRID_WIDTH//2+5, HEIGHT//2, 120, 50, 'Quit'),
               'resume': Button(GRID_WIDTH//2-125, HEIGHT//2, 120, 50, 'Resume'), 'quit_p': Button(GRID_WIDTH//2+5, HEIGHT//2, 120, 50, 'Quit')}

    run = True
    while run:
        dt = clock.tick(FPS); grid = create_grid(locked_positions); mouse_pos = pygame.mouse.get_pos(); piece_to_be_locked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT: run = False
            if game_over:
                if buttons['replay'].is_clicked(event): (locked_positions, current_piece, next_piece, score, fall_time, line_clear_anim, game_over, is_paused, particles) = reset_game(); is_soft_dropping, is_sonic_dropping, sonic_drop_score = False, False, 0; pygame.mixer.music.play(-1)
                if buttons['quit_go'].is_clicked(event): run = False
            elif is_paused:
                if buttons['resume'].is_clicked(event): is_paused = False; pygame.mixer.music.unpause()
                if buttons['quit_p'].is_clicked(event): run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and not game_over: is_paused = not is_paused; pygame.mixer.music.pause() if is_paused else pygame.mixer.music.unpause()
                if not game_over and not is_paused and not line_clear_anim:
                    if event.key == pygame.K_LEFT and is_valid_position(current_piece, grid, adj_x=-1): current_piece.x -= 1
                    if event.key == pygame.K_RIGHT and is_valid_position(current_piece, grid, adj_x=1): current_piece.x += 1
                    if event.key == pygame.K_UP:
                        rotated = rotate_shape(current_piece.shape)
                        if is_valid_position(current_piece, grid, shape=rotated): current_piece.shape = rotated; ROTATE_SND.play()
                    if event.key == pygame.K_DOWN: is_soft_dropping = True
                    if event.key == pygame.K_SPACE and not is_sonic_dropping:
                        is_sonic_dropping = True; HARD_DROP_SND.play()
                        ghost_y = current_piece.y
                        while is_valid_position(current_piece, grid, adj_y=(ghost_y - current_piece.y) + 1): ghost_y += 1
                        spawn_hard_drop_trace_particles(current_piece, int(ghost_y), particles)
                        sonic_drop_score = (ghost_y - current_piece.y) * 2
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_DOWN: is_soft_dropping = False

        if not is_paused and not game_over:
            for p in particles: p.update(dt)
            particles = [p for p in particles if p.lifespan > 0]
            target_pixel_y = current_piece.y * BLOCK_SIZE
            current_piece.visual_y += (target_pixel_y - current_piece.visual_y) * INTERPOLATION_SPEED

            if line_clear_anim:
                line_clear_anim['timer'] += dt; total_anim_time = LINE_CLEAR_FLASH_DURATION + LINE_CLEAR_SHATTER_DURATION
                if line_clear_anim['phase'] == 'flashing' and line_clear_anim['timer'] >= LINE_CLEAR_FLASH_DURATION:
                    line_clear_anim['phase'] = 'shattering'; rows_to_clear = line_clear_anim['rows']; new_locked = {}
                    for (x, y), color in locked_positions.items():
                        if y in rows_to_clear: spawn_block_shatter_particles(x, y, color, particles)
                        else: new_locked[(x,y)] = color
                    locked_positions = new_locked
                if line_clear_anim['timer'] >= total_anim_time:
                    rows, cnt = line_clear_anim['rows'], line_clear_anim['count']
                    locked_positions, _ = clear_rows(rows, locked_positions); score += SCORE_MAP.get(cnt, 0)
                    line_clear_anim = None
                    current_piece, next_piece = next_piece, get_next_from_bag()
                    current_piece.visual_y = current_piece.y * BLOCK_SIZE
                    if not is_valid_position(current_piece, create_grid(locked_positions)): game_over = True; pygame.mixer.music.stop()
            elif not piece_to_be_locked:
                fall_speed = FALL_SPEED_DEFAULT
                if is_soft_dropping: fall_speed = FALL_SPEED_SOFT_DROP
                if is_sonic_dropping: fall_speed = FALL_SPEED_SONIC_DROP
                fall_time += dt
                if fall_time >= fall_speed:
                    fall_time = 0
                    if is_valid_position(current_piece, grid, adj_y=1):
                        current_piece.y += 1
                    else:
                        piece_to_be_locked = True

            if piece_to_be_locked and not line_clear_anim:
                was_sonic_dropping = is_sonic_dropping # Remember state for sound logic
                
                # --- FIXED: Play lock sound immediately when piece hits ground ---
                if not was_sonic_dropping and LOCK_SND:
                    LOCK_SND.play()
                
                score += sonic_drop_score
                is_soft_dropping, is_sonic_dropping, sonic_drop_score = False, False, 0
                for pos in get_shape_positions(current_piece): locked_positions[pos] = current_piece.color

                grid_after = create_grid(locked_positions)
                full = check_for_full_rows(grid_after)
                
                if full:
                    # Play line clear sound for a line clear event
                    if LINE_CLEAR_SND:
                        LINE_CLEAR_SND.play()
                    line_clear_anim = {'rows': full, 'timer': 0, 'count': len(full), 'phase': 'flashing'}
                else:
                    # Spawn the next piece
                    current_piece, next_piece = next_piece, get_next_from_bag()
                    current_piece.visual_y = current_piece.y * BLOCK_SIZE
                    if not is_valid_position(current_piece, grid_after): game_over = True; pygame.mixer.music.stop()

        screen.fill(BG_COLOR)
        for i in range(ROWS + 1): pygame.draw.line(screen, GRID_COLOR, (0, i * BLOCK_SIZE), (GRID_WIDTH, i * BLOCK_SIZE))
        for i in range(COLS + 1): pygame.draw.line(screen, GRID_COLOR, (i * BLOCK_SIZE, 0), (i * BLOCK_SIZE, HEIGHT))
        for (x, y), color in locked_positions.items(): draw_block(screen, desaturate_color(color) if game_over else color, pygame.Rect(x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

        if not game_over and not is_paused and not line_clear_anim:
            ghost = Piece(current_piece.shape_key); ghost.shape, ghost.x, ghost.y = current_piece.shape, current_piece.x, current_piece.y
            while is_valid_position(ghost, grid, adj_y=1): ghost.y += 1
            for x, y in get_shape_positions(ghost): pygame.draw.rect(screen, GHOST_COLOR, (x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 2, border_radius=2)
            for x_offset, y_offset in get_shape_positions(current_piece, adj_y=0):
                draw_block(screen, current_piece.color, pygame.Rect(x_offset*BLOCK_SIZE, current_piece.visual_y + (y_offset - int(current_piece.y))*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

        if line_clear_anim and line_clear_anim['phase'] == 'flashing':
            flash_alpha = 255 * (1 - (line_clear_anim['timer'] / LINE_CLEAR_FLASH_DURATION))
            flash_surf = pygame.Surface((GRID_WIDTH, BLOCK_SIZE), pygame.SRCALPHA); flash_surf.fill((255, 255, 255, flash_alpha))
            for row_idx in line_clear_anim['rows']: screen.blit(flash_surf, (0, row_idx * BLOCK_SIZE))

        for p in particles: p.draw(screen)
        pygame.draw.rect(screen, PANEL_COLOR, (GRID_WIDTH, 0, PANEL_WIDTH, HEIGHT))
        score_box_rect = pygame.Rect(GRID_WIDTH + 20, 20, PANEL_WIDTH - 40, 100)
        pygame.draw.rect(screen, PANEL_BOX_COLOR, score_box_rect, border_radius=10); pygame.draw.rect(screen, GRID_COLOR, score_box_rect, 2, border_radius=10)
        draw_text(screen, 'SCORE', 20, score_box_rect.centerx, score_box_rect.y + 25, center=True); draw_text(screen, str(score), 28, score_box_rect.centerx, score_box_rect.y + 65, center=True)
        next_box_rect = pygame.Rect(GRID_WIDTH + 20, 140, PANEL_WIDTH - 40, 140)
        pygame.draw.rect(screen, PANEL_BOX_COLOR, next_box_rect, border_radius=10); pygame.draw.rect(screen, GRID_COLOR, next_box_rect, 2, border_radius=10)
        draw_text(screen, 'NEXT', 20, next_box_rect.centerx, next_box_rect.y + 25, center=True)

        preview_x, preview_y = next_box_rect.centerx, next_box_rect.centery + 15
        shape_w, shape_h = len(next_piece.shape[0]), len(next_piece.shape)
        for i, row in enumerate(next_piece.shape):
            for j, val in enumerate(row):
                if val: p_x = preview_x + (j - shape_w/2)*BLOCK_SIZE; p_y = preview_y + (i - shape_h/2)*BLOCK_SIZE; draw_block(screen, next_piece.color, pygame.Rect(p_x, p_y, BLOCK_SIZE, BLOCK_SIZE))

        if is_paused or game_over:
            overlay = pygame.Surface((GRID_WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0,0))
            if is_paused:
                draw_text(screen, "PAUSED", 32, GRID_WIDTH/2, HEIGHT/2 - 80, center=True)
                buttons['resume'].check_hover(mouse_pos); buttons['resume'].draw(screen); buttons['quit_p'].check_hover(mouse_pos); buttons['quit_p'].draw(screen)
            if game_over:
                draw_text(screen, "GAME OVER", 32, GRID_WIDTH/2, HEIGHT/2 - 80, center=True)
                buttons['replay'].check_hover(mouse_pos); buttons['replay'].draw(screen); buttons['quit_go'].check_hover(mouse_pos); buttons['quit_go'].draw(screen)
        pygame.draw.line(screen, GRID_COLOR, (GRID_WIDTH, 0), (GRID_WIDTH, HEIGHT), 2); pygame.display.update()
    pygame.quit()


if __name__ == '__main__': main()