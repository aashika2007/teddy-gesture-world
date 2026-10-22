
import cv2
import pygame
import mediapipe as mp
import sys
from pathlib import Path

# ==================================================
# GAME SETUP
# ==================================================
pygame.init()

WIDTH, HEIGHT = 1100, 680
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Teddy's Gesture World")

clock = pygame.time.Clock()
ASSET_DIR = Path(__file__).parent / "assets" / "teddy"

BACKGROUND = (245, 240, 255)
DARK = (55, 48, 75)
PANEL = (255, 255, 255)
CARD = (245, 243, 252)
ACCENT = (150, 190, 160)

font = pygame.font.SysFont("Arial", 30, bold=True)
small_font = pygame.font.SysFont("Arial", 20)
label_font = pygame.font.SysFont("Arial", 17, bold=True)
action_font = pygame.font.SysFont("Arial", 17)

# ==================================================
# LOAD TEDDY ASSETS
# ==================================================
def load_teddy(filename):
    path = ASSET_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing teddy asset: {path}"
        )

    image = pygame.image.load(str(path)).convert_alpha()

    max_width, max_height = 260, 320
    scale = min(
        max_width / image.get_width(),
        max_height / image.get_height()
    )

    size = (
        max(1, int(image.get_width() * scale)),
        max(1, int(image.get_height() * scale))
    )

    return pygame.transform.smoothscale(image, size)


poses = {
    "STAND": load_teddy("stand.png"),
    "SIT": load_teddy("sit.png"),
}

wave_frames = [
    load_teddy(f"wave_{i}.png")
    for i in range(1, 4)
]

walk_right_frames = [
    load_teddy(f"walk_right_{i}.png")
    for i in range(1, 5)
]

walk_left_frames = [
    load_teddy(f"walk_left_{i}.png")
    for i in range(1, 5)
]

# ==================================================
# HAND TRACKING
# ==================================================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Could not open camera. Check camera permissions.")
    hands.close()
    pygame.quit()
    sys.exit()

# ==================================================
# GESTURE RECOGNITION
# ==================================================
def recognize_gesture(landmarks):
    tips = [8, 12, 16, 20]
    joints = [6, 10, 14, 18]

    fingers_up = [
        landmarks[tip].y < landmarks[joint].y
        for tip, joint in zip(tips, joints)
    ]

    count = sum(fingers_up)

    if count == 4:
        return "WAVE"

    if count == 0:
        return "SIT"

    if fingers_up == [True, False, False, False]:
        return "STAND"

    if fingers_up == [True, True, False, False]:
        return "RIGHT"

    if fingers_up == [True, True, True, False]:
        return "LEFT"

    return "OTHER"

# ==================================================
# CHARACTER STATE
# ==================================================
base_pose = "STAND"
animation = None
gesture = "SHOW YOUR HAND"

# Fixed teddy position: walking does not move this point.
teddy_x = 280
teddy_y = 340

# Walking animation
WALK_FRAME_DELAY = 110
walk_index = 0
last_walk_frame_time = 0

# Waving animation
FRAME_DELAY = 180
animation_index = 0
last_frame_time = 0

# Gesture stabilization
STABLE_FRAMES = 3
LOST_HAND_DELAY = 350

candidate_gesture = None
candidate_count = 0
stable_gesture = None
last_hand_seen = pygame.time.get_ticks()

# ==================================================
# MAIN GAME LOOP
# ==================================================
running = True

while running:
    now = pygame.time.get_ticks()
    clock.tick(30)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # ----------------------------------------------
    # READ CAMERA
    # ----------------------------------------------
    success, frame = cap.read()
    detected = None

    if success:
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        if result.multi_hand_landmarks:
            hand = result.multi_hand_landmarks[0]

            mp_draw.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            detected = recognize_gesture(hand.landmark)
            last_hand_seen = now

    # ----------------------------------------------
    # STABILIZE GESTURE
    # ----------------------------------------------
    if detected is not None:
        if detected == candidate_gesture:
            candidate_count += 1
        else:
            candidate_gesture = detected
            candidate_count = 1

        if candidate_count >= STABLE_FRAMES:
            stable_gesture = candidate_gesture

    if now - last_hand_seen > LOST_HAND_DELAY:
        stable_gesture = None
        candidate_gesture = None
        candidate_count = 0

    if not success:
        gesture = "CAMERA UNAVAILABLE"
    elif stable_gesture is None:
        gesture = "SHOW YOUR HAND"
    else:
        gesture = stable_gesture

    # ----------------------------------------------
    # APPLY GESTURE ACTIONS
    # ----------------------------------------------
    if stable_gesture == "WAVE":
        if animation != "WAVE":
            animation = "WAVE"
            animation_index = 0
            last_frame_time = now

    elif stable_gesture == "SIT":
        base_pose = "SIT"
        animation = None

    elif stable_gesture == "STAND":
        base_pose = "STAND"
        animation = None

    elif stable_gesture == "RIGHT":
        animation = "WALK_RIGHT"
        base_pose = "STAND"

    elif stable_gesture == "LEFT":
        animation = "WALK_LEFT"
        base_pose = "STAND"

    elif stable_gesture == "OTHER":
        animation = None

    elif stable_gesture is None:
        animation = None

    # ----------------------------------------------
    # ADVANCE WALKING FRAMES
    # Teddy remains in the same position.
    # ----------------------------------------------
    if animation in ("WALK_RIGHT", "WALK_LEFT"):
        if now - last_walk_frame_time >= WALK_FRAME_DELAY:
            walk_index = (walk_index + 1) % 4
            last_walk_frame_time = now

        if animation == "WALK_RIGHT":
            teddy = walk_right_frames[walk_index]
        else:
            teddy = walk_left_frames[walk_index]

    # ----------------------------------------------
    # ADVANCE WAVING FRAMES
    # ----------------------------------------------
    elif animation == "WAVE":
        if now - last_frame_time >= FRAME_DELAY:
            animation_index = (
                animation_index + 1
            ) % len(wave_frames)

            last_frame_time = now

        teddy = wave_frames[animation_index]

    # ----------------------------------------------
    # NORMAL POSES
    # ----------------------------------------------
    else:
        teddy = poses[base_pose]

    # ==================================================
    # DRAW GAME WORLD
    # ==================================================
    screen.fill(BACKGROUND)

    title = font.render(
        "TEDDY'S GESTURE WORLD", True, DARK
    )
    screen.blit(
        title,
        title.get_rect(center=(WIDTH // 2, 38))
    )

    # Panels
    teddy_panel = pygame.Rect(35, 85, 490, 510)
    camera_panel = pygame.Rect(555, 85, 510, 335)

    pygame.draw.rect(
        screen, PANEL, teddy_panel, border_radius=24
    )
    pygame.draw.rect(
        screen, PANEL, camera_panel, border_radius=24
    )

    # Panel titles
    screen.blit(
        small_font.render("YOUR TEDDY", True, DARK),
        (60, 105)
    )
    screen.blit(
        small_font.render("LIVE CAMERA", True, DARK),
        (580, 105)
    )

    # Teddy stays fixed while its animation frames change
    teddy_rect = teddy.get_rect(
        center=(teddy_x, teddy_y)
    )
    screen.blit(teddy, teddy_rect)

    # Live camera preview
    if success:
        camera_rgb = cv2.cvtColor(
            frame, cv2.COLOR_BGR2RGB
        )

        camera_surface = pygame.surfarray.make_surface(
            camera_rgb.swapaxes(0, 1)
        )

        camera_rect = pygame.Rect(580, 145, 460, 250)

        camera_surface = pygame.transform.smoothscale(
            camera_surface,
            (camera_rect.width, camera_rect.height)
        )

        screen.blit(camera_surface, camera_rect)

    else:
        camera_error = small_font.render(
            "Camera unavailable", True, DARK
        )
        screen.blit(camera_error, (700, 250))

    # ----------------------------------------------
    # FORMATTED GESTURE GUIDE
    # ----------------------------------------------
    guide_x = 580
    guide_y = 410
    guide_width = 460
    card_height = 35
    card_gap = 5

    guide_title = small_font.render(
        "HOW TO CONTROL TEDDY", True, DARK
    )
    screen.blit(guide_title, (guide_x, guide_y))

    instructions = [
        ("OPEN PALM", "Wave"),
        ("CLOSED FIST", "Sit"),
        ("INDEX FINGER", "Stand"),
        ("TWO FINGERS", "Walk right in place"),
        ("THREE FINGERS", "Walk left in place"),
    ]

    for i, (gesture_name, action_name) in enumerate(instructions):
        y = guide_y + 30 + i * (card_height + card_gap)

        card = pygame.Rect(
            guide_x, y, guide_width, card_height
        )

        pygame.draw.rect(
            screen, CARD, card, border_radius=9
        )

        gesture_text = label_font.render(
            gesture_name, True, DARK
        )
        action_text = action_font.render(
            action_name, True, DARK
        )

        screen.blit(
            gesture_text,
            (guide_x + 12, y + 9)
        )
        screen.blit(
            action_text,
            (guide_x + 230, y + 9)
        )

    # ----------------------------------------------
    # BOTTOM STATUS BAR
    # ----------------------------------------------
    status_bar = pygame.Rect(35, 610, 1030, 42)

    pygame.draw.rect(
        screen, PANEL, status_bar, border_radius=12
    )

    action_name = animation if animation else base_pose

    status = small_font.render(
        f"Detected: {gesture}     |     Teddy: {action_name}",
        True, DARK
    )

    screen.blit(status, (52, 620))

    pygame.display.flip()

# ==================================================
# CLEANUP
# ==================================================
cap.release()
hands.close()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()
