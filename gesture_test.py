
import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

cap = cv2.VideoCapture(0)


def recognize_gesture(landmarks):
    # Finger tips and joints for index, middle, ring, pinky
    tips = [8, 12, 16, 20]
    joints = [6, 10, 14, 18]

    # In image coordinates, smaller y means higher on screen
    fingers_up = [
        landmarks[tip].y < landmarks[joint].y
        for tip, joint in zip(tips, joints)
    ]

    if not any(fingers_up):
        return "SIT - FIST"

    if all(fingers_up):
        return "STOP - OPEN PALM"

    if fingers_up == [True, False, False, False]:
        return "STAND - ONE FINGER"

    return "GESTURE NOT RECOGNIZED"


while True:
    success, frame = cap.read()

    if not success:
        print("Could not access camera")
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    label = "Show your hand"

    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame, hand, mp_hands.HAND_CONNECTIONS
            )

            label = recognize_gesture(hand.landmark)

    cv2.rectangle(frame, (10, 10), (frame.shape[1] - 10, 65),
                  (35, 35, 35), -1)

    cv2.putText(
        frame, label, (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
        (0, 255, 0), 2
    )

    cv2.imshow("Gesture Recognition Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
hands.close()
cv2.destroyAllWindows()
