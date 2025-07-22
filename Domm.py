import random
import pygame
import math

# Configurações da tela
WIDTH, HEIGHT = 800, 600
HALF_HEIGHT = HEIGHT // 2
FPS = 60

# Configurações do mapa
MAP = [
    '########',
    '#      #',
    '#  ##  #',
    '#      #',
    '#      #',
    '#      #',
    '#      #',
    '#  ##  #',
    '#      #',
    '#   #  #',
    '#      #',
    '########',
]

TILE_SIZE = 100

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Inicializa o pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Carrega sprites dos inimigos (coloque as imagens na pasta do projeto)
enemy_sprites = [
    pygame.image.load("images.jfif").convert_alpha(),
    pygame.image.load("images (1).jfif").convert_alpha(),
    pygame.image.load("download.jfif").convert_alpha(),
]

# Player
player_x = TILE_SIZE + TILE_SIZE // 2
player_y = TILE_SIZE + TILE_SIZE // 2
player_angle = 0
player_speed = 3
player_max_health = 100
player_health = player_max_health
PLAYER_DAMAGE = 10

# FOV e Raycasting
FOV = math.pi / 3  # 60 graus
NUM_RAYS = 120
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(FOV / 2))
PROJ_COEFF = 3 * DIST * TILE_SIZE
SCALE = WIDTH // NUM_RAYS

# Mob
SPAWN_INTERVAL = 5000
ENEMY_DAMAGE = 15
ENEMY_VELOCITY = 3
ENEMY_MIN_AGRO_DISTANCE = 10

empty_tiles = []
for row_index, row in enumerate(MAP):
    for col_index, cell in enumerate(row):
        if cell == ' ':
            empty_tiles.append((col_index, row_index))

last_spawn_time = pygame.time.get_ticks()

# Enemies com sprites
enemies = []

# Efeito do tiro
shot_effect_time = 0
shot_effect_pos = None

# Variáveis para recoil da arma
weapon_recoil = 0
weapon_recoil_speed = 1  # velocidade da arma voltar à posição normal

def mapping(x, y):
    return int(x // TILE_SIZE), int(y // TILE_SIZE)

def is_wall(x, y):
    map_x, map_y = mapping(x, y)
    if 0 <= map_x < len(MAP[0]) and 0 <= map_y < len(MAP):
        return MAP[map_y][map_x] == '#'
    return True

def ray_casting(sc, px, py, pa):
    start_angle = pa - FOV / 2
    for ray in range(NUM_RAYS):
        angle = start_angle + ray * DELTA_ANGLE
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        for depth in range(MAX_DEPTH):
            x = px + depth * cos_a
            y = py + depth * sin_a

            map_x, map_y = mapping(x, y)
            if 0 <= map_x < len(MAP[0]) and 0 <= map_y < len(MAP):
                if MAP[map_y][map_x] == '#':
                    depth *= math.cos(pa - angle)
                    proj_height = PROJ_COEFF / (depth + 0.0001)
                    color_intensity = 255 / (1 + depth * depth * 0.0001)
                    color = (color_intensity, color_intensity, color_intensity)
                    pygame.draw.rect(sc, color,
                                     (ray * SCALE, HALF_HEIGHT - proj_height // 2, SCALE, proj_height))
                    break

def draw_weapon(sc):
    global weapon_recoil
    x = WIDTH // 2 - 60
    y = HEIGHT - 60 - weapon_recoil  # deslocamento vertical pela recuo

    # Corpo da arma
    gun_body = pygame.Rect(x + 20, y + 20, 80, 20)
    pygame.draw.rect(sc, (20, 20, 20), gun_body)
    pygame.draw.rect(sc, (100, 100, 100), gun_body, 3)

    # Cano da arma
    barrel = pygame.Rect(x + 95, y + 25, 20, 10)
    pygame.draw.rect(sc, (50, 50, 50), barrel)
    pygame.draw.rect(sc, (150, 150, 150), barrel, 2)

    # Empunhadura
    grip = pygame.Rect(x + 40, y + 40, 15, 25)
    pygame.draw.rect(sc, (40, 40, 40), grip)
    pygame.draw.rect(sc, (110, 110, 110), grip, 2)

    # Detalhe extra (tipo mira)
    pygame.draw.circle(sc, (150, 0, 0), (x + 115, y + 30), 5)

def shoot(px, py, pa):
    sin_a = math.sin(pa)
    cos_a = math.cos(pa)

    for depth in range(MAX_DEPTH):
        x = px + depth * cos_a
        y = py + depth * sin_a

        if is_wall(x, y):
            return (x, y), None

        for enemy in enemies:
            if enemy['alive']:
                dist = math.hypot(enemy['x'] - x, enemy['y'] - y)
                if dist < 20:
                    return (x, y), enemy

    return None, None

def is_visible(px, py, ex, ey):
    dx = ex - px
    dy = ey - py
    distance = math.hypot(dx, dy)
    steps = int(distance)
    sin_a = dy / distance
    cos_a = dx / distance

    for step in range(0, steps, 5):
        x = px + cos_a * step
        y = py + sin_a * step
        if is_wall(x, y):
            return False
    return True

def move_enemies():
    for enemy in enemies:
        if enemy['alive']:
            dx = player_x - enemy['x']
            dy = player_y - enemy['y']
            dist = math.hypot(dx, dy)
            if dist > ENEMY_MIN_AGRO_DISTANCE:  # Se estiver muito perto, não se move mais
                dx /= dist
                dy /= dist
                new_x = enemy['x'] + dx * ENEMY_VELOCITY # Velocidade do inimigo
                new_y = enemy['y'] + dy * ENEMY_VELOCITY

                # Verifica se pode andar para a nova posição (sem atravessar parede)
                if not is_wall(new_x, enemy['y']):
                    enemy['x'] = new_x
                if not is_wall(enemy['x'], new_y):
                    enemy['y'] = new_y


def draw_enemies(sc, px, py, pa):
    for enemy in enemies:
        if enemy['alive']:
            if not is_visible(px, py, enemy['x'], enemy['y']):
                continue

            dx = enemy['x'] - px
            dy = enemy['y'] - py
            distance = math.hypot(dx, dy)
            angle = math.atan2(dy, dx) - pa

            if angle > math.pi:
                angle -= 2 * math.pi
            if angle < -math.pi:
                angle += 2 * math.pi

            if -FOV / 2 < angle < FOV / 2 and distance > 0.5:
                proj_height = PROJ_COEFF / distance
                sprite = enemy['sprite']
                sprite = pygame.transform.scale(sprite, (int(proj_height), int(proj_height)))
                screen_x = WIDTH // 2 + (angle) * (WIDTH / FOV) - proj_height // 2
                screen_y = HALF_HEIGHT - proj_height // 2
                sc.blit(sprite, (int(screen_x), int(screen_y)))

                # Barra de vida do inimigo
                bar_width = int(proj_height)
                health_ratio = enemy['health'] / enemy['max_health']
                health_bar_width = int(bar_width * health_ratio)
                bar_x = int(screen_x)
                bar_y = int(screen_y - 10)

                pygame.draw.rect(sc, RED, (bar_x, bar_y, bar_width, 5))
                pygame.draw.rect(sc, GREEN, (bar_x, bar_y, health_bar_width, 5))


def draw_crosshair(sc):
    center_x = WIDTH // 2
    center_y = HALF_HEIGHT
    size = 6
    color = WHITE
    thickness = 2
    pygame.draw.line(sc, color, (center_x - size, center_y), (center_x + size, center_y), thickness)
    pygame.draw.line(sc, color, (center_x, center_y - size), (center_x, center_y + size), thickness)

def draw_player_health(sc):
    bar_width = 200
    bar_height = 20
    x = 20
    y = 20
    health_ratio = player_health / player_max_health
    pygame.draw.rect(sc, RED, (x, y, bar_width, bar_height))
    pygame.draw.rect(sc, GREEN, (x, y, bar_width * health_ratio, bar_height))


def spawn_mob():
    if not empty_tiles:
        return  # Nenhum lugar para spawnar

    col, row = random.choice(empty_tiles)
    x = (col + 0.5) * TILE_SIZE
    y = (row + 0.5) * TILE_SIZE

    enemies.append({
        'x': x,
        'y': y,
        'alive': True,
        'sprite': random.choice(enemy_sprites),  # ou sortear sprite
        'health': 50,
        'max_health': 50,
    })

# Loop principal
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                impact_pos, hit_enemy = shoot(player_x, player_y, player_angle)
                if impact_pos:
                    shot_effect_time = pygame.time.get_ticks()
                    shot_effect_pos = impact_pos
                    weapon_recoil = 15  # Define recoil ao atirar
                if hit_enemy:
                    new_enemy_health = hit_enemy["health"] - PLAYER_DAMAGE
                    if new_enemy_health <= 0:
                        hit_enemy["health"] = 0
                        hit_enemy['alive'] = False
                    else:
                        hit_enemy["health"] = new_enemy_health

    keys = pygame.key.get_pressed()
    dx = dy = 0
    speed = player_speed
    if keys[pygame.K_w]:
        dx += speed * math.cos(player_angle)
        dy += speed * math.sin(player_angle)
    if keys[pygame.K_s]:
        dx -= speed * math.cos(player_angle)
        dy -= speed * math.sin(player_angle)

    new_x = player_x + dx
    if not is_wall(new_x, player_y):
        player_x = new_x

    new_y = player_y + dy
    if not is_wall(player_x, new_y):
        player_y = new_y

    if keys[pygame.K_a]:
        player_angle -= 0.04
    if keys[pygame.K_d]:
        player_angle += 0.04

    screen.fill(BLACK)

    ray_casting(screen, player_x, player_y, player_angle)
    draw_enemies(screen, player_x, player_y, player_angle)

    # enemy attack
    for enemy in enemies:
        if enemy['alive']:
            dist = math.hypot(enemy['x'] - player_x, enemy['y'] - player_y)
            if dist < 50:  # distância de ataque
                if pygame.time.get_ticks() % 60 == 0:  # ataque periódico
                    player_health -= ENEMY_DAMAGE

    if shot_effect_pos:
        elapsed = pygame.time.get_ticks() - shot_effect_time
        if elapsed < 200:
            pygame.draw.circle(screen, RED, (WIDTH // 2, HALF_HEIGHT), 10)
        else:
            shot_effect_pos = None

    current_time = pygame.time.get_ticks()
    alive_mobs = sum(1 for mob in enemies if mob['alive'])
    if current_time - last_spawn_time > SPAWN_INTERVAL and alive_mobs < 2:
        spawn_mob()
        last_spawn_time = current_time

    # Atualiza recoil para a arma voltar à posição normal
    if weapon_recoil > 0:
        weapon_recoil -= weapon_recoil_speed
        if weapon_recoil < 0:
            weapon_recoil = 0

    if player_health <= 0:
        print("Você morreu!")
        running = False

    move_enemies()

    draw_weapon(screen)
    draw_crosshair(screen)
    draw_player_health(screen)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
