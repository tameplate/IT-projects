"""Audio Sorter and Renamer Script v5.8.

This script scans the user's desktop for .mp3 and .wav files, then opens a
custom Tkinter GUI for each file sequentially. It allows the user to listen to
the audio, dynamic-adjust volume, skip through the timeline, rename the file,
and move it to target folders (Music/Soundboard) or delete it.
Supports RU, EN, and HE localization on the fly.
"""

import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk
import numpy as np
import sounddevice as sd
import soundfile as sf

# ==================== CONSTANTS & CONFIGURATION ====================
DOWNLOADS_DIR = "C:/Users/yourname/Desktop"
MUSIC_DIR = "C:/Users/yourname/Desktop/yourmusicfolder"
SOUNDBOARD_DIR = "C:/Users/yourname/Desktop/yoursoundsfolder"

# Localized text database for the user interface
LOCALIZATION = {
    "RU": {
        "title": "Разгребатель балагана v5.8",
        "remaining": "Осталось разгрести файлов: ",
        "rename_label": "Переименовать и отправить файл:",
        "vol_label": "🔊 Громкость: ",
        "play_fallback": "▶ Послушать звук",
        "btn_music": "🎵 В Музыку",
        "btn_soundboard": "🔊 В Саундборд",
        "btn_delete": "❌ Удалить",
        "btn_exit": "🛑 Выключить скрипт",
        "finished_title": "🎉 УРА!",
        "finished_msg": "Весь балаган успешно разгребен! На столе чистота.",
    },
    "EN": {
        "title": "File Sorter v5.8",
        "remaining": "Files remaining: ",
        "rename_label": "Rename and send file:",
        "vol_label": "🔊 Volume: ",
        "play_fallback": "▶ Play Sound",
        "btn_music": "🎵 To Music",
        "btn_soundboard": "🔊 To Soundboard",
        "btn_delete": "❌ Delete",
        "btn_exit": "🛑 Exit Script",
        "finished_title": "🎉 SUCCESS!",
        "finished_msg": "All files sorted successfully! Desktop is clean.",
    },
    "HE": {
        "title": "ממיין קבצים v5.8",
        "remaining": "קבצים שנשארו: ",
        "rename_label": ":שנה שם ושלח קובץ",
        "vol_label": "🔊 עוצמת שמע: ",
        "play_fallback": "▶ השמע צлиל",
        "btn_music": "🎵 למוזיקה",
        "btn_soundboard": "🔊 לסאונדבורד",
        "btn_delete": "❌ מחק",
        "btn_exit": "🛑 סגור תוכנה",
        "finished_title": "🎉 כל הכבוד!",
        "finished_msg": "כל הקבצים מוינו בהצלחה! שולחן העבודה נקי.",
    },
}

# ==================== GLOBAL STATES ====================
files_to_process = []
current_lang = "RU"

# Audio engine states
audio_stream = None
audio_data = None
samplerate = None
current_frame = 0
is_playing = False

# UI widget references
volume_scale = None
lbl_vol_pct = None
track_scale = None
lbl_time = None
btn_play = None
total_seconds = 0
current_window = None
is_dragging_track = False

# Image assets cache
img_play_bg = None
img_pause_bg = None
img_music_bg = None
img_soundboard_bg = None
img_delete_bg = None

# Window position memory
last_window_x = None
last_window_y = None


# ─────────────────────────────────────────────────────────────
#  AUDIO CALLBACK (runs on a background thread)
# ─────────────────────────────────────────────────────────────
def audio_callback(outdata, frames, time_info, status):
    global current_frame, is_playing, audio_data, volume_scale

    if not is_playing or audio_data is None:
        outdata.fill(0)
        return

    vol = 1.0
    try:
        if volume_scale is not None and volume_scale.winfo_exists():
            vol = volume_scale.get()
    except Exception:
        pass  # Tkinter might be shutting down

    chunk = audio_data[current_frame : current_frame + frames]

    if len(chunk) < frames:
        outdata[: len(chunk)] = chunk * vol
        outdata[len(chunk) :].fill(0)
        is_playing = False
        current_frame = 0
        if current_window:
            try:
                current_window.after(0, reset_play_button)
            except Exception:
                pass
    else:
        outdata[:] = chunk * vol
        current_frame += frames


def reset_play_button():
    """Swap the button icon back to Play after the track finishes."""
    global btn_play, img_play_bg
    if btn_play and btn_play.winfo_exists() and img_play_bg:
        btn_play.config(image=img_play_bg)


# ─────────────────────────────────────────────────────────────
#  PLAYBACK CONTROLS
# ─────────────────────────────────────────────────────────────
def toggle_play_pause():
    global audio_stream, is_playing, audio_data, samplerate
    global btn_play, img_play_bg, img_pause_bg

    if audio_data is None:
        return

    if is_playing:
        is_playing = False
        if btn_play and img_play_bg:
            btn_play.config(image=img_play_bg)
    else:
        is_playing = True
        if btn_play and img_pause_bg:
            btn_play.config(image=img_pause_bg)

        if audio_stream is None:
            try:
                audio_stream = sd.OutputStream(
                    samplerate=samplerate,
                    channels=audio_data.shape[1],
                    callback=audio_callback,
                )
                audio_stream.start()
            except Exception as e:
                print(f"[Audio error]: {e}")


def stop_audio():
    """Stop playback and reset position safely."""
    global audio_stream, is_playing, current_frame
    is_playing = False
    current_frame = 0
    if audio_stream is not None:
        try:
            audio_stream.stop()
            audio_stream.close()
        except Exception:
            pass
        audio_stream = None


# ─────────────────────────────────────────────────────────────
#  TIMELINE + VOLUME (polled every 100 ms)
# ─────────────────────────────────────────────────────────────
def update_timeline():
    global current_frame, samplerate, total_seconds
    global lbl_time, track_scale, current_window, is_dragging_track

    if audio_data is None or current_window is None:
        return

    try:
        if not current_window.winfo_exists():
            return

        elapsed = current_frame / samplerate if samplerate else 0

        if lbl_time and lbl_time.winfo_exists():
            lbl_time.config(text=f"{int(elapsed)}s / {int(total_seconds)}s")

        if track_scale and track_scale.winfo_exists() and not is_dragging_track:
            track_scale.set(elapsed)

        if (
            volume_scale
            and volume_scale.winfo_exists()
            and lbl_vol_pct
            and lbl_vol_pct.winfo_exists()
        ):
            lbl_vol_pct.config(text=f"{int(volume_scale.get() * 100)}%")

        current_window.after(100, update_timeline)
    except Exception:
        return


def on_track_scroll_start(event):
    global is_dragging_track
    is_dragging_track = True


def on_track_scroll_end(event):
    global is_dragging_track, current_frame, samplerate
    if track_scale:
        try:
            current_frame = int(track_scale.get() * samplerate)
        except Exception:
            pass
    is_dragging_track = False


# ─────────────────────────────────────────────────────────────
#  FILE QUEUE MANAGEMENT
# ─────────────────────────────────────────────────────────────
def start_sorting():
    global files_to_process

    try:
        entries = os.listdir(DOWNLOADS_DIR)
    except Exception as e:
        print(f"[Error] Couldn't read the Desktop folder: {e}")
        return

    for filename in entries:
        full_path = os.path.join(DOWNLOADS_DIR, filename)
        if os.path.isfile(full_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in (".mp3", ".wav"):
                files_to_process.append(full_path)

    print(f"Found {len(files_to_process)} audio file(s) to sort.")
    process_next_file()


def process_next_file():
    global files_to_process, current_lang

    if not files_to_process:
        print("\n" + "=" * 50)
        title = LOCALIZATION[current_lang]["finished_title"]
        msg = LOCALIZATION[current_lang]["finished_msg"]
        print(f"{title} {msg}")
        print("=" * 50)
        return

    next_file = files_to_process.pop(0)
    if not os.path.exists(next_file):
        process_next_file()
        return

    create_popup(next_file)


# ─────────────────────────────────────────────────────────────
#  MAIN WINDOW GRAPHICS (GUI)
# ─────────────────────────────────────────────────────────────
def create_popup(file_path):
    global audio_data, samplerate, total_seconds
    global volume_scale, lbl_vol_pct, track_scale, lbl_time
    global btn_play, current_window
    global last_window_x, last_window_y
    global img_play_bg, img_pause_bg, img_music_bg, img_soundboard_bg, img_delete_bg
    global current_lang

    old_filename = os.path.basename(file_path)
    name_without_ext, ext = os.path.splitext(old_filename)

    stop_audio()

    try:
        audio_data, samplerate = sf.read(file_path)
        if audio_data.ndim == 1:
            audio_data = audio_data[:, np.newaxis]
        total_seconds = len(audio_data) / samplerate
    except Exception as e:
        print(f"[Error] Couldn't read audio file: {e}")
        audio_data = None
        total_seconds = 0

    root = tk.Tk()
    root.withdraw()

    window = tk.Toplevel()
    current_window = window
    window.title(LOCALIZATION[current_lang]["title"])

    WIN_W, WIN_H = 460, 380

    if last_window_x is None or last_window_y is None:
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        x = (sw - WIN_W) // 2
        y = (sh - WIN_H) // 2
    else:
        x, y = last_window_x, last_window_y

    window.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")
    window.attributes("-topmost", True)
    window.configure(bg="#0d0d0d")
    window.resizable(False, False)

    try:
        window.img_play = tk.PhotoImage(file="btn_play_bg.png")
        window.img_pause = tk.PhotoImage(file="btn_pause_bg.png")
        window.img_music = tk.PhotoImage(file="btn_music_bg.png")
        window.img_soundboard = tk.PhotoImage(file="btn_soundboard_bg.png")
        window.img_delete = tk.PhotoImage(file="btn_delete_bg.png")

        img_play_bg = window.img_play
        img_pause_bg = window.img_pause
        img_music_bg = window.img_music
        img_soundboard_bg = window.img_soundboard
        img_delete_bg = window.img_delete
    except Exception as e:
        print(f"[Warning] Using text fallbacks for controls: {e}")

    # ── LANGUAGE SELECTOR PANEL ──────────────────────────────
    lang_frame = tk.Frame(window, bg="#0d0d0d")
    lang_frame.pack(anchor="ne", padx=10, pady=2)

    def change_language(lang_code):
        """Switch language states and force redraw current window context."""
        global current_lang, last_window_x, last_window_y
        current_lang = lang_code
        if window.winfo_exists():
            last_window_x = window.winfo_x()
            last_window_y = window.winfo_y()
        files_to_process.insert(0, file_path)
        stop_audio()
        window.destroy()
        root.quit()
        process_next_file()

    for lang in ["RU", "EN", "HE"]:
        btn_bg = "#222222" if lang == current_lang else "#0d0d0d"
        btn_fg = "#ffcc00" if lang == current_lang else "#888888"
        l_btn = tk.Button(
            lang_frame,
            text=lang,
            command=lambda l=lang: change_language(l),
            bg=btn_bg,
            fg=btn_fg,
            bd=0,
            font=("Arial", 8, "bold"),
            padx=5,
            cursor="hand2",
        )
        l_btn.pack(side=tk.LEFT, padx=2)

    # ── UI TEXT LAYOUTS ──────────────────────────────────────
    lbl_style = {"bg": "#0d0d0d", "fg": "#ffffff", "font": ("Arial", 10, "bold")}

    remaining = len(files_to_process) + 1
    tk.Label(
        window,
        text=f"{LOCALIZATION[current_lang]['remaining']}{remaining}",
        bg="#0d0d0d",
        fg="#ffcc00",
        font=("Arial", 9, "italic"),
    ).pack(pady=(2, 0))

    tk.Label(window, text=LOCALIZATION[current_lang]["rename_label"], **lbl_style).pack(pady=(5, 0))

    entry_justify = tk.RIGHT if current_lang == "HE" else tk.LEFT
    entry_var = tk.StringVar(value=name_without_ext)
    entry = tk.Entry(
        window,
        textvariable=entry_var,
        font=("Arial", 11),
        width=42,
        bg="#222222",
        fg="white",
        insertbackground="white",
        justify=entry_justify,
    )
    entry.pack(pady=8, padx=20)
    entry.focus_set()

    def close_window():
        global last_window_x, last_window_y
        stop_audio()
        if window.winfo_exists():
            last_window_x = window.winfo_x()
            last_window_y = window.winfo_y()
            window.destroy()
        root.quit()

    def emergency_exit():
        """Forcibly stop script loop execution process tasks."""
        stop_audio()
        if window.winfo_exists():
            window.destroy()
        root.destroy()
        sys.exit(0)

    def move_file(destination_dir):
        new_name = entry_var.get().strip() or name_without_ext
        dest_path = os.path.join(destination_dir, f"{new_name}{ext}")
        try:
            shutil.move(file_path, dest_path)
            print(f"[Moved] {new_name}{ext}")
        except Exception as e:
            print(f"[Error] Couldn't move file: {e}")
        close_window()
        process_next_file()

    def delete_file():
        try:
            os.remove(file_path)
            print(f"[Deleted] {old_filename}")
        except Exception as e:
            print(f"[Error] Couldn't delete file: {e}")
        close_window()
        process_next_file()

    # Slider configuration styles
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Horizontal.TScale", background="#0d0d0d", troughcolor="#222222")

    # ── TIMELINE TRACKBAR ────────────────────────────────────
    track_frame = tk.Frame(window, bg="#0d0d0d")
    track_frame.pack(pady=5, fill=tk.X, padx=35)

    track_scale = ttk.Scale(
        track_frame,
        from_=0,
        to=total_seconds,
        orient=tk.HORIZONTAL,
        style="Horizontal.TScale",
    )
    track_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
    track_scale.bind("<ButtonPress-1>", on_track_scroll_start)
    track_scale.bind("<ButtonRelease-1>", on_track_scroll_end)

    lbl_time = tk.Label(
        track_frame,
        text=f"0s / {int(total_seconds)}s",
        bg="#0d0d0d",
        fg="white",
        font=("Arial", 9),
        width=10,
    )
    lbl_time.pack(side=tk.RIGHT, padx=(5, 0))

    # ── VOLUME TRACKBAR ──────────────────────────────────────
    vol_frame = tk.Frame(window, bg="#0d0d0d")
    vol_frame.pack(pady=5, fill=tk.X, padx=35)

    tk.Label(
        vol_frame,
        text=LOCALIZATION[current_lang]["vol_label"],
        bg="#0d0d0d",
        fg="white",
        font=("Arial", 9),
    ).pack(side=tk.LEFT)

    volume_scale = ttk.Scale(
        vol_frame, from_=0.0, to=2.0, orient=tk.HORIZONTAL, style="Horizontal.TScale"
    )
    volume_scale.set(1.0)
    volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    lbl_vol_pct = tk.Label(
        vol_frame,
        text="100%",
        bg="#0d0d0d",
        fg="#ffcc00",
        font=("Arial", 9, "bold"),
        width=6,
    )
    lbl_vol_pct.pack(side=tk.RIGHT)

    # ── AUDIO PLAYER ACTION TRIGGER ──────────────────────────
    player_frame = tk.Frame(window, bg="#0d0d0d")
    player_frame.pack(pady=10)

    btn_kwargs = dict(
        command=toggle_play_pause,
        bg="#0d0d0d",
        activebackground="#0d0d0d",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
    )
    if img_play_bg:
        btn_play = tk.Button(player_frame, image=img_play_bg, **btn_kwargs)
    else:
        btn_play = tk.Button(
            player_frame,
            text=LOCALIZATION[current_lang]["play_fallback"],
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            width=20,
            command=toggle_play_pause,
        )
    btn_play.pack()

    # ── FILE MANAGEMENT ACTIONS ROW ──────────────────────────
    action_frame = tk.Frame(window, bg="#0d0d0d")
    action_frame.pack(pady=(10, 0))

    icon_btn = dict(bg="#0d0d0d", activebackground="#0d0d0d", bd=0, highlightthickness=0, cursor="hand2")

    if current_lang == "RU" and img_music_bg:
        tk.Button(action_frame, image=img_music_bg, command=lambda: move_file(MUSIC_DIR), **icon_btn).pack(
            side=tk.LEFT, padx=6
        )
    else:
        tk.Button(
            action_frame,
            text=LOCALIZATION[current_lang]["btn_music"],
            width=12,
            command=lambda: move_file(MUSIC_DIR),
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT, padx=6)

    if current_lang == "RU" and img_soundboard_bg:
        tk.Button(action_frame, image=img_soundboard_bg, command=lambda: move_file(SOUNDBOARD_DIR), **icon_btn).pack(
            side=tk.LEFT, padx=6
        )
    else:
        tk.Button(
            action_frame,
            text=LOCALIZATION[current_lang]["btn_soundboard"],
            width=14,
            command=lambda: move_file(SOUNDBOARD_DIR),
            bg="#9C27B0",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT, padx=6)

    if current_lang == "RU" and img_delete_bg:
        tk.Button(action_frame, image=img_delete_bg, command=delete_file, **icon_btn).pack(side=tk.LEFT, padx=6)
    else:
        tk.Button(
            action_frame,
            text=LOCALIZATION[current_lang]["btn_delete"],
            width=10,
            command=delete_file,
            bg="#555555",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT, padx=6)

    # ── EMERGENCY SCRIPT EXIT BUTTON ─────────────────────────
    exit_frame = tk.Frame(window, bg="#0d0d0d")
    exit_frame.pack(pady=(15, 0))

    btn_exit = tk.Button(
        exit_frame,
        text=LOCALIZATION[current_lang]["btn_exit"],
        command=emergency_exit,
        bg="#1a1a1a",
        fg="#ff4444",
        activebackground="#ff4444",
        activeforeground="white",
        font=("Arial", 9, "bold"),
        bd=1,
        relief=tk.SOLID,
        padx=10,
        pady=2,
        cursor="hand2",
    )
    btn_exit.pack()

    update_timeline()

    window.protocol("WM_DELETE_WINDOW", close_window)
    root.mainloop()


# ─────────────────────────────────────────────────────────────
#  SCRIPT SYSTEM ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(MUSIC_DIR, exist_ok=True)
    os.makedirs(SOUNDBOARD_DIR, exist_ok=True)

    print("=" * 50)
    print("Audio File Organizer v5.8 ")
    print("Thread-safe asset routing engine initialized.")
    print("=" * 50)

    start_sorting()