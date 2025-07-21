import pygame
import math
import random

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
    '########',
]

TILE_SIZE = 100
MAP_WIDTH = len(MAP[0]) * TILE_SIZE
MAP_HEIGHT = len(MAP) * TILE_SIZE

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)

# Inicializa o pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Player
player_x = TILE_SIZE + TILE_SIZE // 2
player_y = TILE_SIZE + TILE_SIZE // 2
player_angle = 0
player_speed = 3

FOV = math.pi / 3  # 60 graus
NUM_RAYS = 120
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(FOV / 2))
PROJ_COEFF = 3 * DIST * TILE_SIZE
SCALE = WIDTH // NUM_RAYS

# Mob
SPAWN_INTERVAL = 5_000
spawn_positions = [
    (3.5 * TILE_SIZE, 1.5 * TILE_SIZE),
    (5.5 * TILE_SIZE, 1.5 * TILE_SIZE),
    (2.5 * TILE_SIZE, 2.5 * TILE_SIZE),
    (5.5 * TILE_SIZE, 3.5 * TILE_SIZE),
]
last_spawn_time = pygame.time.get_ticks()

# Inimigos: lista de dicionários com x,y no mapa
enemies = [
    {'x': 4.5 * TILE_SIZE, 'y': 2.5 * TILE_SIZE, 'alive': True},
    {'x': 6.5 * TILE_SIZE, 'y': 3.5 * TILE_SIZE, 'alive': True},
]


# Variável para efeito do tiro
shot_effect_time = 0
shot_effect_pos = None

def mapping(x, y):
    return int(x // TILE_SIZE), int(y // TILE_SIZE)

def is_wall(x, y):
    map_x, map_y = mapping(x, y)
    if 0 <= map_x < len(MAP[0]) and 0 <= map_y < len(MAP):
        return MAP[map_y][map_x] == '#'
    return True  # Fora do mapa é parede

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
                    depth *= math.cos(pa - angle)  # corrigir efeito "fish-eye"
                    proj_height = PROJ_COEFF / (depth + 0.0001)
                    color_intensity = 255 / (1 + depth * depth * 0.0001)
                    color = (color_intensity, color_intensity, color_intensity)
                    pygame.draw.rect(sc, color,
                                     (ray * SCALE, HALF_HEIGHT - proj_height // 2, SCALE, proj_height))
                    break

def draw_weapon(sc):
    """Desenha uma arma simples na parte inferior central da tela"""
    weapon_width = 120
    weapon_height = 60
    x = WIDTH // 2 - weapon_width // 2
    y = HEIGHT - weapon_height - 10
    # Corpo da arma
    pygame.draw.rect(sc, GRAY, (x, y, weapon_width, weapon_height))
    # Cano
    pygame.draw.rect(sc, BLACK, (x + weapon_width - 20, y + 20, 40, 20))
    # Detalhes
    pygame.draw.rect(sc, YELLOW, (x + 10, y + 10, 30, 40))

def shoot(px, py, pa):
    """Simula o tiro, retorna ponto do impacto e inimigo atingido (se houver)"""
    sin_a = math.sin(pa)
    cos_a = math.cos(pa)

    for depth in range(MAX_DEPTH):
        x = px + depth * cos_a
        y = py + depth * sin_a

        if is_wall(x, y):
            return (x, y), None  # atingiu parede, sem inimigo

        # Checar colisão com inimigos (simples distância menor que raio)
        for enemy in enemies:
            if enemy['alive']:
                dist = math.hypot(enemy['x'] - x, enemy['y'] - y)
                if dist < 20:  # raio de acerto
                    return (x, y), enemy

    return None, None

def is_visible(px, py, ex, ey):
    """Verifica se há linha de visão livre do player (px,py) até o inimigo (ex,ey)"""
    dx = ex - px
    dy = ey - py
    distance = math.hypot(dx, dy)
    steps = int(distance)

    sin_a = dy / distance
    cos_a = dx / distance

    for step in range(0, steps, 5):  # pula de 5 em 5 pixels para otimizar
        x = px + cos_a * step
        y = py + sin_a * step
        if is_wall(x, y):
            return False  # parede no caminho
    return True  # caminho livre


def draw_enemies(sc, px, py, pa):
    for enemy in enemies:
        if enemy['alive']:
            if not is_visible(px, py, enemy['x'], enemy['y']):
                continue  # inimigo está atrás da parede, não desenha

            # restante do código para projetar e desenhar o inimigo
            dx = enemy['x'] - px
            dy = enemy['y'] - py

            distance = math.hypot(dx, dy)
            angle = math.atan2(dy, dx) - pa

            # Ajusta o ângulo para ficar entre -pi e pi
            if angle > math.pi:
                angle -= 2 * math.pi
            if angle < -math.pi:
                angle += 2 * math.pi

            if -FOV / 2 < angle < FOV / 2 and distance > 0.5:
                proj_height = PROJ_COEFF / distance
                sprite_width = sprite_height = proj_height
                screen_x = WIDTH // 2 + (angle) * (WIDTH / FOV) - sprite_width // 2
                screen_y = HALF_HEIGHT - proj_height // 2
                pygame.draw.rect(sc, GREEN, (int(screen_x), int(screen_y), int(sprite_width), int(sprite_height)))


def draw_crosshair(sc):
    center_x = WIDTH // 2
    center_y = HALF_HEIGHT
    size = 6
    color = WHITE
    thickness = 2

    # Linha horizontal
    pygame.draw.line(sc, color, (center_x - size, center_y), (center_x + size, center_y), thickness)
    # Linha vertical
    pygame.draw.line(sc, color, (center_x, center_y - size), (center_x, center_y + size), thickness)

def spawn_mob():
    # Spawn no primeiro local disponível (sem mob vivo perto)
    for pos in spawn_positions:
        x, y = posdwadw
        # Verifica se já existe mob próximo (pra evitar spawn duplicado)
        too_close = False
        for mob in enemies:
            if mob['alive'] and math.hypot(mob['x'] - x, mob['y'] - y) < TILE_SIZE:
                too_close = True
                break
        if not too_close:
            enemies.append({'x': x, 'y': y, 'alive': True})
            print(f'Mob spawnado em ({x}, {y})')
            break

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                impact_pos, hit_enemy = shoot(player_x, player_y, player_angle)
                if impact_pos:
                    shot_effect_time = pygame.time.get_ticks()
                    shot_effect_pos = impact_pos
                if hit_enemy:
                    hit_enemy['alive'] = False  # Mata o inimigo

    # Movimentação com colisão
    keys = pygame.key.get_pressed()
    dx = dy = 0
    speed = player_speed
    if keys[pygame.K_w]:
        dx += speed * math.cos(player_angle)
        dy += speed * math.sin(player_angle)
    if keys[pygame.K_s]:
        dx -= speed * math.cos(player_angle)
        dy -= speed * math.sin(player_angle)

    # Testa colisão no eixo X
    new_x = player_x + dx
    if not is_wall(new_x, player_y):
        player_x = new_x

    # Testa colisão no eixo Y
    new_y = player_y + dy
    if not is_wall(player_x, new_y):
        player_y = new_y

    if keys[pygame.K_a]:
        player_angle -= 0.04
    if keys[pygame.K_d]:
        player_angle += 0.04

    screen.fill(BLACK)

    # Raycasting
    ray_casting(screen, player_x, player_y, player_angle)

    # Desenha inimigos
    draw_enemies(screen, player_x, player_y, player_angle)

    # Efeito do tiro (aparece por 200 ms)
    if shot_effect_pos:
        elapsed = pygame.time.get_ticks() - shot_effect_time
        if elapsed < 200:
            # Desenha um círculo vermelho no centro da tela para mostrar o tiro
            pygame.draw.circle(screen, RED, (WIDTH // 2, HALF_HEIGHT), 10)
        else:
            shot_effect_pos = None

    current_time = pygame.time.get_ticks()
    alive_mobs = sum(1 for mob in enemies if mob['alive'])
    if current_time - last_spawn_time > SPAWN_INTERVAL and alive_mobs < 2:
        spawn_mob()
        last_spawn_time = current_time

    # Desenha a arma na tela
    draw_weapon(screen)
    draw_crosshair(screen)

    pygame.display.flip()
    clock.tick(FPS)
