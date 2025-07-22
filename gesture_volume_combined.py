import cv2
import mediapipe as mp
from math import hypot
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import numpy as np
import threading
import tkinter as tk
import screen_brightness_control as sbc

# Global control flag
running = False

def start_detection():
    global running
    running = True
    cap = cv2.VideoCapture(0)
    mpHands = mp.solutions.hands
    hands = mpHands.Hands(max_num_hands=2)
    mpDraw = mp.solutions.drawing_utils

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volMin, volMax = volume.GetVolumeRange()[:2]

    last_vol = volume.GetMasterVolumeLevel()
    last_volbar = 400
    last_volper = 0

    while running:
        success, img = cap.read()
        if not success:
            break
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_idx, hand_handedness in enumerate(results.multi_handedness):
                label = hand_handedness.classification[0].label  # 'Left' or 'Right'
                hand_landmarks = results.multi_hand_landmarks[hand_idx]
                lmList = []

                for id, lm in enumerate(hand_landmarks.landmark):
                    h, w, _ = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lmList.append([id, cx, cy])
                mpDraw.draw_landmarks(img, hand_landmarks, mpHands.HAND_CONNECTIONS)

                if label == "Left" and len(lmList) > 8:
                    # Volume Control - Left Hand (Thumb & Index)
                    x1, y1 = lmList[4][1], lmList[4][2]
                    x2, y2 = lmList[8][1], lmList[8][2]
                    cv2.circle(img, (x1, y1), 13, (255, 0, 0), cv2.FILLED)
                    cv2.circle(img, (x2, y2), 13, (255, 0, 0), cv2.FILLED)
                    cv2.line(img, (x1, y1), (x2, y2), (255, 0, 0), 3)
                    length = hypot(x2 - x1, y2 - y1)

                    vol = np.interp(length, [30, 200], [volMin, volMax])
                    volbar = np.interp(length, [30, 200], [400, 150])
                    volper = np.interp(length, [30, 200], [0, 100])

                    volume.SetMasterVolumeLevel(vol, None)
                    last_vol = vol
                    last_volbar = volbar
                    last_volper = volper

                elif label == "Right" and len(lmList) > 20:
                    # Brightness Control - Right Hand (Thumb & Pinky)
                    x3, y3 = lmList[4][1], lmList[4][2]    # Thumb tip
                    x4, y4 = lmList[20][1], lmList[20][2]  # Pinky tip

                    cv2.circle(img, (x3, y3), 10, (0, 255, 0), cv2.FILLED)
                    cv2.circle(img, (x4, y4), 10, (0, 255, 0), cv2.FILLED)
                    cv2.line(img, (x3, y3), (x4, y4), (0, 255, 0), 2)
                    brightness_len = hypot(x4 - x3, y4 - y3)
                    brightness_per = np.interp(brightness_len, [30, 200], [0, 100])

                    try:
                        sbc.set_brightness(int(brightness_per))
                    except Exception as e:
                        print(f"Brightness Error: {e}")

                    cv2.putText(img, f"Brightness: {int(brightness_per)}%", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        else:
            # No hand detected
            cv2.putText(img, "No hand detected", (10, 70), cv2.FONT_ITALIC, 1, (0, 0, 255), 2)

        # Volume bar using last known values
        cv2.rectangle(img, (50, 150), (85, 400), (0, 0, 255), 4)
        cv2.rectangle(img, (50, int(last_volbar)), (85, 400), (0, 0, 255), cv2.FILLED)
        cv2.putText(img, f"{int(last_volper)}%", (10, 40), cv2.FONT_ITALIC, 1, (0, 255, 98), 3)

        # -------- VISUAL GESTURE TIPS --------
        cv2.putText(img, "Left Hand: Volume (Thumb + Index)", (10, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 255), 2)
        cv2.putText(img, "Right Hand: Brightness (Thumb + Pinky)", (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)

        # Volume visual
        cv2.circle(img, (370, 420), 10, (255, 0, 0), cv2.FILLED)  # Thumb
        cv2.circle(img, (390, 410), 10, (255, 0, 0), cv2.FILLED)  # Index
        cv2.line(img, (370, 420), (390, 410), (255, 0, 0), 2)
        cv2.putText(img, "Volume", (360, 440), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)

        # Brightness visual
        cv2.circle(img, (370, 460), 10, (0, 255, 0), cv2.FILLED)  # Thumb
        cv2.circle(img, (400, 460), 10, (0, 255, 0), cv2.FILLED)  # Pinky
        cv2.line(img, (370, 460), (400, 460), (0, 255, 0), 2)
        cv2.putText(img, "Brightness", (355, 480), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)

        # Show the image
        cv2.imshow('Gesture Volume and Brightness Control', img)
        if cv2.waitKey(1) & 0xFF == ord(' '):
            break

    cap.release()
    cv2.destroyAllWindows()

def stop_detection():
    global running
    running = False

# UI Part
def start_gesture_control():
    global running_thread
    if not running_thread or not running_thread.is_alive():
        running_thread = threading.Thread(target=start_detection, daemon=True)
        running_thread.start()
        status_label.config(text="Gesture Control: RUNNING", fg="green")

def stop_gesture_control():
    stop_detection()
    status_label.config(text="Gesture Control: STOPPED", fg="red")

# Tkinter App
running_thread = None
root = tk.Tk()
root.title("Gesture Volume & Brightness Control")
root.geometry("400x300")
root.resizable(False, False)

title_label = tk.Label(root, text="Gesture Volume & Brightness", font=("Arial", 18, "bold"))
title_label.pack(pady=20)

start_button = tk.Button(root, text="Start", font=("Arial", 14), bg="green", fg="white", width=20, command=start_gesture_control)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="Stop", font=("Arial", 14), bg="red", fg="white", width=20, command=stop_gesture_control)
stop_button.pack(pady=10)

status_label = tk.Label(root, text="Gesture Control: STOPPED", font=("Arial", 12), fg="red")
status_label.pack(pady=20)

exit_button = tk.Button(root, text="Exit", font=("Arial", 12), command=root.destroy)
exit_button.pack(pady=10)

root.mainloop()
