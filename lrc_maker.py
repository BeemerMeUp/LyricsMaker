#!/usr/bin/env python3
"""LRC Maker - Synchronize lyrics to audio and export .lrc files."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import time
from pathlib import Path

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


SUPPORTED_FORMATS = (
    ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".opus", ".mp4"
)

C = {
    "bg":           "#1e1e2e",
    "surface":      "#2a2a3e",
    "surface2":     "#313244",
    "accent":       "#7c6af5",
    "text":         "#cdd6f4",
    "dim":          "#6c7086",
    "green":        "#a6e3a1",
    "yellow":       "#f9e2af",
    "red":          "#f38ba8",
    "stamp_idle":   "#45475a",
    "stamp_hot":    "#f38ba8",
}


def fmt_display(seconds: float) -> str:
    """mm:ss.xx for display."""
    if seconds < 0:
        seconds = 0.0
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


def fmt_lrc(seconds: float) -> str:
    """[mm:ss.xx] for LRC file output."""
    if seconds < 0:
        seconds = 0.0
    m = int(seconds // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{m:02d}:{s:02d}.{cs:02d}"


class LRCMaker:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LRC Maker")
        self.root.geometry("960x740")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)

        # Audio state
        self.audio_file: str | None = None
        self.audio_length: float = 0.0
        self.is_playing = False
        self.is_paused = False
        self.play_start_pos: float = 0.0    # position where current play() started
        self.play_start_wall: float = 0.0   # wall clock when play() was called
        self.current_pos: float = 0.0       # last known paused/stopped position
        self._was_playing_before_seek = False
        self._seeking = False

        # Lyrics state
        self.lyrics_lines: list[str] = []
        self.current_idx: int = 0
        self.timed: list[tuple[float, float, str]] = []  # (start_s, end_s, text)

        # Stamp state
        self._stamp_down = False
        self._stamp_start: float = 0.0

        if PYGAME_AVAILABLE:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        else:
            messagebox.showerror(
                "Missing dependency",
                "pygame is not installed.\nRun: pip install pygame\n\nAudio playback will be unavailable.",
            )

        self._build_ui()
        self._tick()

    # ------------------------------------------------------------------ UI build

    def _btn(self, parent, text, cmd, bg=None, fg=None, **kw):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=bg or C["surface2"], fg=fg or C["text"],
            activebackground=C["accent"], activeforeground="white",
            relief="flat", bd=0, padx=10, pady=5,
            font=("Segoe UI", 9), cursor="hand2", **kw,
        )

    def _build_ui(self):
        wrap = tk.Frame(self.root, bg=C["bg"])
        wrap.pack(fill="both", expand=True, padx=12, pady=10)

        self._build_toolbar(wrap)
        self._build_player(wrap)
        self._build_main(wrap)
        self._build_status(wrap)

        # Global space-bar stamp (avoid firing when a widget has focus)
        self.root.bind("<KeyPress-space>",   self._on_space_press)
        self.root.bind("<KeyRelease-space>", self._on_space_release)

    def _build_toolbar(self, p):
        f = tk.Frame(p, bg=C["bg"])
        f.pack(fill="x", pady=(0, 8))

        self._btn(f, "Load Audio",         self._load_audio).pack(side="left", padx=(0, 4))
        self._btn(f, "Load Lyrics (.txt)", self._load_lyrics).pack(side="left", padx=(0, 4))
        self._btn(f, "Save .lrc",          self._save_lrc,
                  bg=C["accent"], fg="white").pack(side="left", padx=(0, 4))

        self._btn(f, "Clear Stamps", self._clear_stamps,
                  bg=C["stamp_idle"]).pack(side="right")

        self.audio_lbl = tk.Label(f, text="No audio loaded",
                                   bg=C["bg"], fg=C["dim"], font=("Segoe UI", 9))
        self.audio_lbl.pack(side="left", padx=10)

    def _build_player(self, p):
        f = tk.Frame(p, bg=C["surface"], padx=12, pady=10)
        f.pack(fill="x", pady=(0, 8))
        self._frame_border(f)

        # Seek row
        seek_row = tk.Frame(f, bg=C["surface"])
        seek_row.pack(fill="x", pady=(0, 8))

        self.time_lbl = tk.Label(seek_row, text="00:00.00",
                                  bg=C["surface"], fg=C["accent"],
                                  font=("Consolas", 13, "bold"), width=8)
        self.time_lbl.pack(side="left")

        self.seek_var = tk.DoubleVar(value=0)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("custom.Horizontal.TScale",
                         background=C["surface"], troughcolor=C["surface2"],
                         sliderlength=14, sliderrelief="flat")
        self.seek_bar = ttk.Scale(seek_row, from_=0, to=100,
                                   orient="horizontal", variable=self.seek_var,
                                   style="custom.Horizontal.TScale")
        self.seek_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.seek_bar.bind("<ButtonPress-1>",   self._seek_press)
        self.seek_bar.bind("<ButtonRelease-1>", self._seek_release)

        self.dur_lbl = tk.Label(seek_row, text="00:00.00",
                                 bg=C["surface"], fg=C["dim"],
                                 font=("Consolas", 11), width=8)
        self.dur_lbl.pack(side="left")

        # Control row
        ctrl = tk.Frame(f, bg=C["surface"])
        ctrl.pack()

        self._btn(ctrl, "⏮",      self._restart).pack(side="left", padx=3)
        self._btn(ctrl, "◀◀ 5s",  lambda: self._skip(-5)).pack(side="left", padx=3)
        self.play_btn = self._btn(ctrl, "▶  Play", self._toggle_play,
                                   bg=C["accent"], fg="white", width=10)
        self.play_btn.pack(side="left", padx=3)
        self._btn(ctrl, "5s ▶▶",  lambda: self._skip(5)).pack(side="left", padx=3)
        self._btn(ctrl, "⏹ Stop", self._stop).pack(side="left", padx=3)

        # Volume
        vol_f = tk.Frame(f, bg=C["surface"])
        vol_f.pack(side="right")
        tk.Label(vol_f, text="Vol:", bg=C["surface"], fg=C["dim"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.vol_var = tk.IntVar(value=80)
        ttk.Scale(vol_f, from_=0, to=100, orient="horizontal",
                  variable=self.vol_var, length=90,
                  style="custom.Horizontal.TScale",
                  command=lambda _: (pygame.mixer.music.set_volume(self.vol_var.get() / 100)
                                      if PYGAME_AVAILABLE else None)
                  ).pack(side="left")

    def _build_main(self, p):
        row = tk.Frame(p, bg=C["bg"])
        row.pack(fill="both", expand=True, pady=(0, 8))

        # Left panel
        left = tk.Frame(row, bg=C["surface"], padx=12, pady=12, width=340)
        left.pack(side="left", fill="both", padx=(0, 6))
        left.pack_propagate(False)
        self._frame_border(left)
        self._build_left_panel(left)

        # Right panel
        right = tk.Frame(row, bg=C["surface"], padx=10, pady=10)
        right.pack(side="left", fill="both", expand=True)
        self._frame_border(right)
        self._build_right_panel(right)

    def _build_left_panel(self, p):
        hdr = tk.Frame(p, bg=C["surface"])
        hdr.pack(fill="x", pady=(0, 4))
        tk.Label(hdr, text="LYRICS", bg=C["surface"],
                 fg=C["dim"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.counter_lbl = tk.Label(hdr, text="0 / 0", bg=C["surface"],
                                     fg=C["dim"], font=("Segoe UI", 8))
        self.counter_lbl.pack(side="right")

        list_f = tk.Frame(p, bg=C["surface"])
        list_f.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(list_f, orient="vertical")
        sb.pack(side="right", fill="y")

        self.lyrics_lb = tk.Listbox(
            list_f, yscrollcommand=sb.set,
            bg="#1a1a2e", fg=C["text"],
            selectbackground=C["accent"], selectforeground="white",
            font=("Segoe UI", 10), relief="flat", bd=0,
            activestyle="none", highlightthickness=0,
        )
        self.lyrics_lb.pack(side="left", fill="both", expand=True)
        sb.config(command=self.lyrics_lb.yview)
        self.lyrics_lb.bind("<<ListboxSelect>>", self._on_lyrics_click)

        # Stamp button
        self.stamp_btn = tk.Button(
            p, text="HOLD TO STAMP\nPress = start  •  Release = end + next line",
            bg=C["stamp_idle"], fg="white",
            activebackground=C["stamp_hot"],
            relief="flat", bd=0, padx=10, pady=18,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        )
        self.stamp_btn.pack(fill="x", pady=(10, 2))
        self.stamp_btn.bind("<ButtonPress-1>",   self._stamp_press)
        self.stamp_btn.bind("<ButtonRelease-1>", self._stamp_release)

        tk.Label(p, text="Keyboard shortcut: Space",
                 bg=C["surface"], fg=C["dim"], font=("Segoe UI", 8)).pack()

        nav = tk.Frame(p, bg=C["surface"])
        nav.pack(pady=(10, 0))
        self._btn(nav, "◀ Prev", self._prev_line).pack(side="left", padx=4)
        self._btn(nav, "Next ▶", self._next_line).pack(side="left", padx=4)
        self._btn(nav, "Undo Last", self._undo_last,
                  bg=C["stamp_idle"]).pack(side="left", padx=4)

    def _build_right_panel(self, p):
        hdr = tk.Frame(p, bg=C["surface"])
        hdr.pack(fill="x", pady=(0, 6))
        tk.Label(hdr, text="TIMED LYRICS", bg=C["surface"],
                 fg=C["dim"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self._btn(hdr, "Remove Selected", self._remove_selected,
                  bg=C["stamp_idle"]).pack(side="right")

        list_f = tk.Frame(p, bg=C["surface"])
        list_f.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(list_f, orient="vertical")
        sb.pack(side="right", fill="y")

        self.timed_lb = tk.Listbox(
            list_f, yscrollcommand=sb.set,
            bg="#1a1a2e", fg=C["text"],
            selectbackground=C["accent"],
            font=("Consolas", 9), relief="flat", bd=0,
            activestyle="none",
        )
        self.timed_lb.pack(side="left", fill="both", expand=True)
        sb.config(command=self.timed_lb.yview)

    def _build_status(self, p):
        self.status_lbl = tk.Label(
            p, text="Ready — load an audio file and a lyrics .txt file to start.",
            bg=C["surface2"], fg=C["dim"],
            font=("Segoe UI", 9), anchor="w", padx=8,
        )
        self.status_lbl.pack(fill="x", ipady=4)

    def _frame_border(self, w):
        w.configure(highlightbackground=C["surface2"], highlightthickness=1)

    # ------------------------------------------------------------------ Audio

    def _load_audio(self):
        if not PYGAME_AVAILABLE:
            messagebox.showerror("Error", "pygame is not installed.")
            return
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        path = filedialog.askopenfilename(
            title="Open Audio File",
            filetypes=[("Audio files", exts), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.vol_var.get() / 100)
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load audio:\n{e}")
            return

        self.audio_file = path
        self.is_playing = False
        self.is_paused = False
        self.current_pos = 0.0
        self.play_start_pos = 0.0
        self.seek_var.set(0)
        self.play_btn.config(text="▶  Play")

        self.audio_length = self._detect_length(path)
        self.dur_lbl.config(text=fmt_display(self.audio_length))

        name = Path(path).name
        self.audio_lbl.config(text=name, fg=C["green"])
        self._status(f"Audio loaded: {name}")

    def _detect_length(self, path: str) -> float:
        if MUTAGEN_AVAILABLE:
            try:
                af = MutagenFile(path)
                if af and hasattr(af, "info") and hasattr(af.info, "length"):
                    return float(af.info.length)
            except Exception:
                pass
        return 0.0

    def _toggle_play(self):
        if not self.audio_file:
            messagebox.showwarning("No audio", "Please load an audio file first.")
            return
        if not PYGAME_AVAILABLE:
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.current_pos = self._pos()
            self.is_playing = False
            self.is_paused = True
            self.play_btn.config(text="▶  Play")
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self.play_start_wall = time.monotonic()
            self.play_start_pos = self.current_pos
            self.is_playing = True
            self.is_paused = False
            self.play_btn.config(text="⏸  Pause")
        else:
            self._play_from(self.current_pos)

    def _play_from(self, pos: float):
        if not PYGAME_AVAILABLE or not self.audio_file:
            return
        pygame.mixer.music.play(start=pos)
        self.play_start_pos = pos
        self.play_start_wall = time.monotonic()
        self.is_playing = True
        self.is_paused = False
        self.play_btn.config(text="⏸  Pause")

    def _stop(self):
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        self.current_pos = self._pos()
        self.is_playing = False
        self.is_paused = False
        self.play_btn.config(text="▶  Play")

    def _restart(self):
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_pos = 0.0
        self.seek_var.set(0)
        self.play_btn.config(text="▶  Play")

    def _skip(self, delta: float):
        target = max(0.0, self._pos() + delta)
        if self.audio_length > 0:
            target = min(target, self.audio_length)
        was = self.is_playing
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        self.current_pos = target
        self.is_playing = False
        self.is_paused = False
        if was:
            self._play_from(target)

    def _seek_press(self, _event):
        self._seeking = True
        self._was_playing_before_seek = self.is_playing
        if self.is_playing and PYGAME_AVAILABLE:
            pygame.mixer.music.pause()
            self.current_pos = self._pos()
            self.is_playing = False
            self.is_paused = True

    def _seek_release(self, _event):
        self._seeking = False
        frac = self.seek_var.get() / 100.0
        pos = frac * self.audio_length if self.audio_length > 0 else 0.0
        self.current_pos = pos
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        if self._was_playing_before_seek:
            self._play_from(pos)

    def _pos(self) -> float:
        """Current playback position in seconds."""
        if self.is_playing and PYGAME_AVAILABLE:
            raw = pygame.mixer.music.get_pos()  # ms since last play(), -1 if not playing
            if raw >= 0:
                return self.play_start_pos + raw / 1000.0
        return self.current_pos

    # ------------------------------------------------------------------ Stamp

    def _stamp_press(self, _event=None):
        if not self.lyrics_lines or self.current_idx >= len(self.lyrics_lines):
            return
        if self._stamp_down:
            return
        self._stamp_down = True
        self._stamp_start = self._pos()
        self.stamp_btn.config(bg=C["stamp_hot"],
                               text="STAMPING…\nRelease to mark end + advance to next line")

    def _stamp_release(self, _event=None):
        if not self._stamp_down:
            return
        self._stamp_down = False
        end = self._pos()
        start = self._stamp_start

        if self.current_idx < len(self.lyrics_lines):
            text = self.lyrics_lines[self.current_idx]
            self.timed.append((start, end, text))
            self._refresh_list()
            self.current_idx += 1
            self._refresh_lines()

        self.stamp_btn.config(bg=C["stamp_idle"],
                               text="HOLD TO STAMP\nPress = start  •  Release = end + next line")

    def _on_space_press(self, event):
        # Skip if a text-entry widget has focus
        if isinstance(self.root.focus_get(), (tk.Entry, tk.Text)):
            return
        self._stamp_press()

    def _on_space_release(self, event):
        if isinstance(self.root.focus_get(), (tk.Entry, tk.Text)):
            return
        self._stamp_release()

    # ------------------------------------------------------------------ Lyrics nav

    def _load_lyrics(self):
        path = filedialog.askopenfilename(
            title="Open Lyrics File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = [ln.rstrip("\n") for ln in fh]
            while lines and not lines[-1].strip():
                lines.pop()
            self.lyrics_lines = lines
            self.current_idx = 0
            self._refresh_lyrics_list()
            self._status(f"Loaded {len(lines)} lines from {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not read file:\n{e}")

    def _prev_line(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._refresh_lines()

    def _next_line(self):
        if self.current_idx < len(self.lyrics_lines):
            self.current_idx += 1
            self._refresh_lines()

    def _undo_last(self):
        if not self.timed:
            return
        self.timed.pop()
        if self.current_idx > 0:
            self.current_idx -= 1
        self._refresh_list()
        self._refresh_lines()

    def _refresh_lyrics_list(self):
        """Repopulate the listbox (call once after loading new lyrics)."""
        self.lyrics_lb.delete(0, "end")
        for line in self.lyrics_lines:
            self.lyrics_lb.insert("end", f"  {line}")
        self._refresh_lines()

    def _on_lyrics_click(self, *_):
        sel = self.lyrics_lb.curselection()
        if sel:
            self.current_idx = sel[0]
            self._refresh_lines()

    def _refresh_lines(self):
        total = len(self.lyrics_lines)
        idx = self.current_idx

        if total == 0:
            self.counter_lbl.config(text="0 / 0")
            return

        # Colour each row: dimmed = stamped, highlighted = current, normal = upcoming
        for i in range(total):
            if i < idx:
                self.lyrics_lb.itemconfig(i, fg=C["dim"],    bg="#1a1a2e")
            elif i == idx:
                self.lyrics_lb.itemconfig(i, fg="white",     bg=C["accent"])
            else:
                self.lyrics_lb.itemconfig(i, fg=C["text"],   bg="#1a1a2e")

        # Keep current line visible, centred in the viewport when possible
        visible_idx = min(idx, total - 1)
        self.lyrics_lb.see(visible_idx)

        shown = min(idx + 1, total)
        self.counter_lbl.config(text=f"{shown} / {total}")

    # ------------------------------------------------------------------ Timed list

    def _refresh_list(self):
        self.timed_lb.delete(0, "end")
        for start, end, text in self.timed:
            self.timed_lb.insert("end", f"[{fmt_lrc(start)}]  {text}")
        if self.timed:
            self.timed_lb.see("end")

    def _remove_selected(self):
        sel = self.timed_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.timed[idx]
        if self.current_idx > 0:
            self.current_idx -= 1
        self._refresh_list()
        self._refresh_lines()

    def _clear_stamps(self):
        if not self.timed:
            return
        if messagebox.askyesno("Clear stamps", "Remove all timed entries?"):
            self.timed.clear()
            self.current_idx = 0
            self._refresh_list()
            self._refresh_lines()

    # ------------------------------------------------------------------ Save

    def _save_lrc(self):
        if not self.timed:
            messagebox.showwarning("Nothing to save", "No timed lines to export yet.")
            return

        initial = ""
        if self.audio_file:
            initial = Path(self.audio_file).stem

        path = filedialog.asksaveasfilename(
            title="Save LRC file",
            initialfile=initial,
            defaultextension=".lrc",
            filetypes=[("LRC files", "*.lrc"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            lines = []
            if self.audio_file:
                lines.append(f"[ti:{Path(self.audio_file).stem}]")
            lines.append("[by:LRC Maker]")
            lines.append("")
            for start, _end, text in sorted(self.timed, key=lambda x: x[0]):
                lines.append(f"[{fmt_lrc(start)}]{text}")

            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))

            self._status(f"Saved: {Path(path).name}  ({len(self.timed)} lines)")
            messagebox.showinfo("Saved", f"Saved {len(self.timed)} lines to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save file:\n{e}")

    # ------------------------------------------------------------------ Loop

    def _tick(self):
        if self.is_playing and PYGAME_AVAILABLE:
            # Detect natural end
            if not pygame.mixer.music.get_busy() and not self._stamp_down:
                self.current_pos = self._pos()
                self.is_playing = False
                self.is_paused = False
                self.play_btn.config(text="▶  Play")
            else:
                self.current_pos = self._pos()

        pos = self.current_pos
        self.time_lbl.config(text=fmt_display(pos))

        if not self._seeking and self.audio_length > 0:
            self.seek_var.set(min((pos / self.audio_length) * 100, 100))

        self.root.after(50, self._tick)

    # ------------------------------------------------------------------ Helpers

    def _status(self, msg: str):
        self.status_lbl.config(text=msg)


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = LRCMaker(root)
    root.mainloop()
    if PYGAME_AVAILABLE:
        pygame.mixer.quit()


if __name__ == "__main__":
    main()
