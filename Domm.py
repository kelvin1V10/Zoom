import random
import pygame
import math

from time import time

# Configurações da tela
WIDTH, HEIGHT = 800, 600
HALF_HEIGHT = HEIGHT // 2
FPS = 60

SHOOTING_HAND_PROPS = {
    "pistol": {
        "size": (200, 200),
        "image_path": "pistol_hand.png",
        "offset": (40, 4),
    },
    "rifle": {
        "size": (200, 200),
        "image_path": "rifle_hand.png",
        "offset": (-40, 0),
    },
    "shotgun": {
        "size": (200, 200),
        "image_path": "shotgun_hand.png",
        "offset": (-5, 4),
    },
}

def load_image(weapon: str):
    props = SHOOTING_HAND_PROPS[weapon]

    img = pygame.image.load(props["image_path"])
    img = pygame.transform.scale(img, props["size"])

    SHOOTING_HAND_PROPS[weapon]["image"] = img

# images
try:
    load_image("pistol")
    load_image("rifle")
    load_image("shotgun")
except pygame.error as e:
    print(f"Error loading image: {e}")
    pygame.quit()
    exit()

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
GRAY = (50, 50, 50)
LIGHT_GRAY = (170, 170, 170)

# Inicializa o pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FPS com munição e recarga")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 24)
big_font = pygame.font.SysFont("Arial", 36, bold=True)

# Carrega sprites dos inimigos
enemy_sprites = [
    pygame.image.load("Macaquinho.jfif").convert_alpha(),
    pygame.image.load("Sherek.jfif").convert_alpha(),
    pygame.image.load("TeleTUBs.jfif").convert_alpha(),
]

# Sprites das armas
pistol_sprite = pygame.image.load("pistol.png").convert_alpha()
rifle_sprite = pygame.image.load("rifle.png").convert_alpha()
shotgun_sprite = pygame.image.load("shotgun.png").convert_alpha()

# Posições das armas no mapa (coletáveis)
rifle_pos = ((5 + 0.5) * TILE_SIZE, (5 + 0.5) * TILE_SIZE)
shotgun_pos = ((2 + 0.5) * TILE_SIZE, (8 + 0.5) * TILE_SIZE)

rifle_collected = False
shotgun_collected = False

# Player
player_x = TILE_SIZE + TILE_SIZE // 2
player_y = TILE_SIZE + TILE_SIZE // 2
player_angle = 0
player_speed = 3
player_max_health = 100
player_health = player_max_health
player_last_shoot_timestamp = 0

# Armas e munição
WEAPONS = {
    "pistol": {"damage": 9, "max_range": 200, "mag_size": 12, "shoot_cooldown": 700},
    "rifle": {"damage": 15, "max_range": 600, "mag_size": 30, "shoot_cooldown": 30},
    "shotgun": {"damage": 30, "max_range": 400, "mag_size": 1, "shoot_cooldown": 2000}
}
current_weapon = "pistol"

AMMO = {
    "pistol": {"current": 12, "reserve": 36},
    "rifle": {"current": 30, "reserve": 90},
    "shotgun": {"current": 8, "reserve": 24}
}

reloading = False
reload_start_time = 0
RELOAD_TIME = 1500  # milissegundos para recarregar

# FOV e Raycasting
FOV = math.pi / 3
NUM_RAYS = 120
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(FOV / 2))
PROJ_COEFF = 3 * DIST * TILE_SIZE
SCALE = WIDTH // NUM_RAYS

# Inimigos
SPAWN_INTERVAL = 5000
ENEMY_DAMAGE = 8
ENEMY_VELOCITY = 2
ENEMY_MIN_AGRO_DISTANCE = 20
ENEMY_ATTACK_RANGE = 100
ENEMY_ATTACK_COOLDOWN = 1000

empty_tiles = [(col_index, row_index) for row_index, row in enumerate(MAP) for col_index, cell in enumerate(row) if cell == ' ']
last_spawn_time = pygame.time.get_ticks()
enemies = []
last_attack_times = {}

shot_effect_time = 0
shot_effect_pos = None
weapon_recoil = 0
weapon_recoil_speed = 1

score = 0

def mapping(x, y): 
    return int(x // TILE_SIZE), int(y // TILE_SIZE)

def is_wall(x, y):
    map_x, map_y = mapping(x, y)
    return 0 > map_x or map_x >= len(MAP[0]) or 0 > map_y or map_y >= len(MAP) or MAP[map_y][map_x] == '#'

def ray_casting(sc, px, py, pa):
    start_angle = pa - FOV / 2
    for ray in range(NUM_RAYS):
        angle = start_angle + ray * DELTA_ANGLE
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        for depth in range(MAX_DEPTH):
            x, y = px + depth * cos_a, py + depth * sin_a
            map_x, map_y = mapping(x, y)
            if 0 <= map_x < len(MAP[0]) and 0 <= map_y < len(MAP) and MAP[map_y][map_x] == '#':
                depth *= math.cos(pa - angle)
                proj_height = PROJ_COEFF / (depth + 0.0001)
                base = min(100 + 155 / (1 + depth * depth * 0.0001), 255)
                color = (base * 0.8, base * 0.9, base)
                pygame.draw.rect(sc, color, (ray * SCALE, HALF_HEIGHT - proj_height // 2, SCALE, proj_height))
                break

def draw_weapon(sc):
    global weapon_recoil
    x = WIDTH // 2 - 60
    y = HEIGHT - 60 - weapon_recoil

    if current_weapon == "pistol":
        weapon_img = pistol_sprite
    elif current_weapon == "rifle":
        weapon_img = rifle_sprite
    elif current_weapon == "shotgun":
        weapon_img = shotgun_sprite
    else:
        return

    weapon_img_scaled = pygame.transform.scale(weapon_img, (120, 60))
    sc.blit(weapon_img_scaled, (x, y))

def shoot(px, py, pa):
    global AMMO
    if reloading:
        return None, None
    if AMMO[current_weapon]["current"] <= 0:
        return None, None

    AMMO[current_weapon]["current"] -= 1

    sin_a, cos_a = math.sin(pa), math.cos(pa)
    weapon = WEAPONS[current_weapon]
    max_range = weapon["max_range"]
    for depth in range(int(max_range)):
        x, y = px + depth * cos_a, py + depth * sin_a
        if is_wall(x, y):
            return (x, y), None
        for enemy in enemies:
            if enemy['alive']:
                dist = math.hypot(enemy['x'] - x, enemy['y'] - y)
                if dist < 20:
                    damage = weapon["damage"] * (1 - depth / weapon["max_range"])
                    return (x, y), (enemy, max(1, int(damage)))
    return None, None

def is_visible(px, py, ex, ey):
    dx, dy = ex - px, ey - py
    distance = math.hypot(dx, dy)
    sin_a, cos_a = dy / distance, dx / distance
    for step in range(0, int(distance), 5):
        x, y = px + cos_a * step, py + sin_a * step
        if is_wall(x, y):
            return False
    return True

def move_enemies():
    for enemy in enemies:
        if enemy['alive']:
            dx, dy = player_x - enemy['x'], player_y - enemy['y']
            dist = math.hypot(dx, dy)
            if ENEMY_MIN_AGRO_DISTANCE < dist > ENEMY_ATTACK_RANGE:
                dx, dy = dx / dist, dy / dist
                new_x = enemy['x'] + dx * ENEMY_VELOCITY
                new_y = enemy['y'] + dy * ENEMY_VELOCITY
                if not is_wall(new_x, enemy['y']):
                    enemy['x'] = new_x
                if not is_wall(enemy['x'], new_y):
                    enemy['y'] = new_y

def draw_enemies(sc, px, py, pa):
    for enemy in enemies:
        if enemy['alive'] and is_visible(px, py, enemy['x'], enemy['y']):
            dx, dy = enemy['x'] - px, enemy['y'] - py
            distance = math.hypot(dx, dy)
            angle = math.atan2(dy, dx) - pa
            angle = (angle + math.pi) % (2 * math.pi) - math.pi
            if -FOV / 2 < angle < FOV / 2 and distance > 0.5:
                proj_height = PROJ_COEFF / distance
                sprite = pygame.transform.scale(enemy['sprite'], (int(proj_height), int(proj_height)))
                screen_x = WIDTH // 2 + (angle) * (WIDTH / FOV) - proj_height // 2
                screen_y = HALF_HEIGHT - proj_height // 2
                sc.blit(sprite, (int(screen_x), int(screen_y)))
                bar_width = int(proj_height)
                health_ratio = enemy['health'] / enemy['max_health']
                pygame.draw.rect(sc, RED, (int(screen_x), int(screen_y - 10), bar_width, 5))
                pygame.draw.rect(sc, GREEN, (int(screen_x), int(screen_y - 10), int(bar_width * health_ratio), 5))

def spawn_mob():
    if empty_tiles:
        col, row = random.choice(empty_tiles)
        x, y = (col + 0.5) * TILE_SIZE, (row + 0.5) * TILE_SIZE
        enemies.append({'x': x, 'y': y, 'alive': True, 'sprite': random.choice(enemy_sprites), 'health': 50, 'max_health': 50})

def draw_collectable_weapon(sc, px, py, pa, weapon_pos, weapon_sprite):
    dx, dy = weapon_pos[0] - px, weapon_pos[1] - py
    distance = math.hypot(dx, dy)
    if distance < 0.5 or distance >= 300:
        return
    angle = math.atan2(dy, dx) - pa
    angle = (angle + math.pi) % (2 * math.pi) - math.pi
    if -FOV / 2 < angle < FOV / 2:
        if not is_visible(px, py, weapon_pos[0], weapon_pos[1]):
            return
    
        size = 300 - distance
        sprite = pygame.transform.scale(weapon_sprite, (size, size))
        screen_x = WIDTH // 2 + (angle) * (WIDTH / FOV) - size // 2
        screen_y = HALF_HEIGHT - size // 2 + 20  # um pouco abaixo do meio (no "chão")
        sc.blit(sprite, (int(screen_x), int(screen_y)))

def draw_pause_menu(sc, selected_option):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 80))  # Alpha 80 para escurecer o fundo
    sc.blit(overlay, (0, 0))

    def draw_text_with_shadow(text, x, y, font, color, shadow_color):
        shadow_offset = 2
        shadow = font.render(text, True, shadow_color)
        sc.blit(shadow, (x + shadow_offset, y + shadow_offset))
        text_render = font.render(text, True, color)
        sc.blit(text_render, (x, y))

    title = "Jogo Pausado"
    title_font = pygame.font.SysFont(None, 60)
    option_font = pygame.font.SysFont(None, 40)

    title_x = WIDTH // 2
    title_y = 100

    title_surface = title_font.render(title, True, WHITE)
    title_rect = title_surface.get_rect(center=(title_x, title_y))
    draw_text_with_shadow(title, title_rect.x, title_rect.y, title_font, WHITE, (50, 50, 50))

    options = ["Continuar", "Sair do Jogo"]
    for i, option in enumerate(options):
        color = WHITE if i == selected_option else (200, 200, 200)
        option_surface = option_font.render(option, True, color)
        option_rect = option_surface.get_rect(center=(title_x, 250 + i * 50))
        draw_text_with_shadow(option, option_rect.x, option_rect.y, option_font, color, (30, 30, 30))

def draw_hand(sc):
    props = SHOOTING_HAND_PROPS[current_weapon]
    offset = props["offset"]
    hand_size = props["size"]

    sc.blit(props["image"], ((WIDTH // 2) - (hand_size[0] // 2) + offset[0], HEIGHT - hand_size[1] + offset[1]))

# Controle do menu de pausa
paused = False
pause_selected = 0  # índice da opção selecionada

# Controle do mouse e movimento
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)

mouse_sensitivity = 0.003

running = True
while running:
    dt = clock.tick(FPS)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if not paused:
                if event.key == pygame.K_ESCAPE:
                    paused = True
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)

                elif event.key == pygame.K_1:
                    current_weapon = "pistol"

                elif event.key == pygame.K_2 and rifle_collected:
                    current_weapon = "rifle"

                elif event.key == pygame.K_3 and shotgun_collected:
                    current_weapon = "shotgun"

                elif event.key == pygame.K_r and not reloading:
                    # Recarregar
                    if AMMO[current_weapon]["current"] < WEAPONS[current_weapon]["mag_size"] and AMMO[current_weapon]["reserve"] > 0:
                        reloading = True
                        reload_start_time = pygame.time.get_ticks()

            else:
                # Menu pausa
                if event.key == pygame.K_ESCAPE:
                    paused = False
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                elif event.key == pygame.K_UP:
                    pause_selected = (pause_selected - 1) % 2
                elif event.key == pygame.K_DOWN:
                    pause_selected = (pause_selected + 1) % 2
                elif event.key == pygame.K_RETURN:
                    if pause_selected == 0:
                        paused = False
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif pause_selected == 1:
                        running = False

    if not paused:
        is_mouse1_down = pygame.mouse.get_pressed(3)[0]
        now = (time() * 1000)

        if is_mouse1_down and not reloading and now - player_last_shoot_timestamp >= 100:
            player_last_shoot_timestamp = now

            impact_pos, hit_data = shoot(player_x, player_y, player_angle)
            if impact_pos:
                shot_effect_time = pygame.time.get_ticks()
                shot_effect_pos = impact_pos
                weapon_recoil = 15
            if hit_data:
                hit_enemy, damage = hit_data
                hit_enemy['health'] -= damage
                if hit_enemy['health'] <= 0:
                    hit_enemy['alive'] = False
                    score += 10

        # Atualiza recarga
        if reloading:
            now = pygame.time.get_ticks()
            if now - reload_start_time >= RELOAD_TIME:
                reloading = False
                needed = WEAPONS[current_weapon]["mag_size"] - AMMO[current_weapon]["current"]
                available = AMMO[current_weapon]["reserve"]
                to_load = min(needed, available)
                AMMO[current_weapon]["current"] += to_load
                AMMO[current_weapon]["reserve"] -= to_load

        # Controle da câmera pelo mouse
        mx, my = pygame.mouse.get_rel()
        player_angle += mx * mouse_sensitivity
        player_angle %= 2 * math.pi

        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w]:
            dx += player_speed * math.cos(player_angle)
            dy += player_speed * math.sin(player_angle)
        if keys[pygame.K_s]:
            dx -= player_speed * math.cos(player_angle)
            dy -= player_speed * math.sin(player_angle)
        if keys[pygame.K_a]:
            dx += player_speed * math.cos(player_angle - math.pi/2)
            dy += player_speed * math.sin(player_angle - math.pi/2)
        if keys[pygame.K_d]:
            dx += player_speed * math.cos(player_angle + math.pi/2)
            dy += player_speed * math.sin(player_angle + math.pi/2)

        if not is_wall(player_x + dx, player_y):
            player_x += dx
        if not is_wall(player_x, player_y + dy):
            player_y += dy

        screen.fill(BLACK)
        ray_casting(screen, player_x, player_y, player_angle)
        draw_enemies(screen, player_x, player_y, player_angle)

        current_time = pygame.time.get_ticks()
        for i, enemy in enumerate(enemies):
            if enemy['alive'] and math.hypot(enemy['x'] - player_x, enemy['y'] - player_y) <= ENEMY_ATTACK_RANGE:
                if current_time - last_attack_times.get(i, 0) >= ENEMY_ATTACK_COOLDOWN:
                    player_health -= ENEMY_DAMAGE
                    last_attack_times[i] = current_time

        if shot_effect_pos and pygame.time.get_ticks() - shot_effect_time < 200:
            pygame.draw.circle(screen, RED, (WIDTH // 2, HALF_HEIGHT), 10)
        else:
            shot_effect_pos = None

        if current_time - last_spawn_time > SPAWN_INTERVAL and sum(e['alive'] for e in enemies) < 2:
            spawn_mob()
            last_spawn_time = current_time

        if weapon_recoil > 0:
            weapon_recoil -= weapon_recoil_speed
            if weapon_recoil < 0:
                weapon_recoil = 0

        if player_health <= 0:
            print("Você morreu!")
            running = False

        move_enemies()
        draw_hand(screen)
        draw_weapon(screen)

        # Desenha armas para coletar
        if not rifle_collected:
            draw_collectable_weapon(screen, player_x, player_y, player_angle, rifle_pos, rifle_sprite)
            dist = math.hypot(rifle_pos[0] - player_x, rifle_pos[1] - player_y)
            if dist < 40:
                rifle_collected = True
                current_weapon = "rifle"
                print("Rifle coletado!")

        if not shotgun_collected:
            draw_collectable_weapon(screen, player_x, player_y, player_angle, shotgun_pos, shotgun_sprite)
            dist = math.hypot(shotgun_pos[0] - player_x, shotgun_pos[1] - player_y)
            if dist < 40:
                shotgun_collected = True
                current_weapon = "shotgun"
                print("Shotgun coletada!")

        # Desenha a mira central
        pygame.draw.line(screen, WHITE, (WIDTH//2 - 10, HALF_HEIGHT), (WIDTH//2 + 10, HALF_HEIGHT), 2)
        pygame.draw.line(screen, WHITE, (WIDTH//2, HALF_HEIGHT - 10), (WIDTH//2, HALF_HEIGHT + 10), 2)

        # Barra de vida verde do player no canto superior esquerdo
        health_bar_width = 200
        health_bar_height = 25
        health_ratio = player_health / player_max_health
        pygame.draw.rect(screen, RED, (20, 20, health_bar_width, health_bar_height))
        pygame.draw.rect(screen, GREEN, (20, 20, int(health_bar_width * health_ratio), health_bar_height))
        health_text = font.render(f"Vida: {player_health} / {player_max_health}", True, WHITE)
        screen.blit(health_text, (20, 50))

        # Munição e recarga
        weapon_props = AMMO[current_weapon]
        ammo_text = font.render(f"{current_weapon.capitalize()} Ammo: {weapon_props['current']} / {WEAPONS[current_weapon]['mag_size']}  ({weapon_props['reserve']})", True, WHITE)
        screen.blit(ammo_text, (20, 80))
        if reloading:
            reload_text = font.render("Recarregando...", True, RED)
            screen.blit(reload_text, (20, 110))

        # Pontuação
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (WIDTH - 150, 20))

    else:
        draw_pause_menu(screen, pause_selected)

    pygame.display.flip()

pygame.quit()
