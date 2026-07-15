"""
4 Pics 1 Word — Main Application
Cross-platform (PC + Android) built with Kivy.

Run on desktop:
    python main.py

Build for Android (requires buildozer on Linux/WSL):
    buildozer android debug deploy run
"""

import os
import random
import string
import threading

# ── Kivy environment tweaks (must come BEFORE kivy imports) ──────────────────
os.environ.setdefault("KIVY_NO_CONSOLELOG", "0")

from kivy.app               import App
from kivy.clock             import Clock
from kivy.factory           import Factory
from kivy.lang              import Builder
from kivy.metrics           import dp, sp
from kivy.properties        import BooleanProperty, StringProperty
from kivy.uix.boxlayout     import BoxLayout
from kivy.uix.button        import Button
from kivy.uix.image         import AsyncImage
from kivy.uix.label         import Label
from kivy.uix.popup         import Popup
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.textinput     import TextInput
from kivy.utils             import platform

from api_handler import ImageAPIHandler
from user_data   import UserData, HINT_COST
from word_list   import WORDS

# Desktop window size (ignored on Android/iOS)
if platform not in ("android", "ios"):
    from kivy.core.window import Window
    Window.size = (400, 720)

# ── KV layout string ─────────────────────────────────────────────────────────

KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

# ── Reusable widget rules ────────────────────────────────────────────────────

<LetterBtn@Button>:
    background_normal: ''
    background_color:  0, 0, 0, 0
    color:             1, 1, 1, 1
    bold:              True
    font_size:         sp(16)
    canvas.before:
        Color:
            rgba: (0.22, 0.52, 0.95, 1) if self.state == 'normal' and not self.disabled \
                  else (0.12, 0.28, 0.55, 0.35)
        RoundedRectangle:
            pos:    self.pos
            size:   self.size
            radius: [dp(8)]

<AnswerBtn@Button>:
    background_normal: ''
    background_color:  0, 0, 0, 0
    bold:              True
    font_size:         sp(20)
    color:             (0.1, 0.1, 0.25, 1) if self.text else (0.5, 0.5, 0.7, 0.6)
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 1, 1
        RoundedRectangle:
            pos:    self.pos
            size:   self.size
            radius: [dp(6)]
        Color:
            rgba: 0.3, 0.3, 0.65, 1
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(6)]
            width: 1.5

# ── Main Menu ────────────────────────────────────────────────────────────────

<MainMenuScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding:     dp(30)
        spacing:     dp(18)
        canvas.before:
            Color:
                rgba: 0.07, 0.07, 0.23, 1
            Rectangle:
                pos:  self.pos
                size: self.size

        Label:
            text:      '4 PICS 1 WORD'
            font_size: sp(34)
            bold:      True
            color:     1, 0.82, 0, 1
            size_hint_y: 0.14

        Label:
            text:      root.welcome_text
            font_size: sp(16)
            color:     0.78, 0.78, 1, 1
            size_hint_y: 0.07

        GridLayout:
            cols:        2
            spacing:     dp(10)
            size_hint_y: 0.22
            BoxLayout:
                orientation: 'vertical'
                padding: dp(10)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0.14, 0.14, 0.38, 1
                    RoundedRectangle:
                        pos:    self.pos
                        size:   self.size
                        radius: [dp(12)]
                Label:
                    text:      root.menu_score
                    font_size: sp(26)
                    bold:      True
                    color:     1, 0.82, 0, 1
                Label:
                    text:      'SCORE'
                    font_size: sp(12)
                    color:     0.68, 0.68, 0.88, 1
            BoxLayout:
                orientation: 'vertical'
                padding: dp(10)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0.14, 0.14, 0.38, 1
                    RoundedRectangle:
                        pos:    self.pos
                        size:   self.size
                        radius: [dp(12)]
                Label:
                    text:      root.menu_level
                    font_size: sp(26)
                    bold:      True
                    color:     0.4, 0.9, 1, 1
                Label:
                    text:      'LEVEL'
                    font_size: sp(12)
                    color:     0.68, 0.68, 0.88, 1

        Widget:
            size_hint_y: 0.04

        Button:
            text:            'PLAY'
            font_size:       sp(22)
            bold:            True
            size_hint_y:     None
            height:          dp(64)
            background_normal: ''
            background_color:  0, 0, 0, 0
            color:           1, 1, 1, 1
            on_press:        root.start_game()
            canvas.before:
                Color:
                    rgba: (0.18, 0.72, 0.32, 1) if self.state == 'normal' \
                          else (0.12, 0.56, 0.24, 1)
                RoundedRectangle:
                    pos:    self.pos
                    size:   self.size
                    radius: [dp(16)]

        Button:
            text:            'PROFILE & SETTINGS'
            font_size:       sp(15)
            size_hint_y:     None
            height:          dp(50)
            background_normal: ''
            background_color:  0, 0, 0, 0
            color:           1, 1, 1, 1
            on_press:        root.go_profile()
            canvas.before:
                Color:
                    rgba: (0.28, 0.28, 0.58, 1) if self.state == 'normal' \
                          else (0.20, 0.20, 0.46, 1)
                RoundedRectangle:
                    pos:    self.pos
                    size:   self.size
                    radius: [dp(12)]

        Widget:
            size_hint_y: 0.1

# ── Game Screen ──────────────────────────────────────────────────────────────

<GameScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding:     [dp(8), dp(6)]
        spacing:     dp(4)
        canvas.before:
            Color:
                rgba: 0.04, 0.04, 0.18, 1
            Rectangle:
                pos:  self.pos
                size: self.size

        # Header bar
        BoxLayout:
            size_hint_y: None
            height:      dp(48)
            spacing:     dp(5)

            Button:
                text:             '<'
                size_hint_x:      None
                width:            dp(44)
                font_size:        sp(22)
                bold:             True
                background_color: 0.20, 0.20, 0.50, 1
                color:            1, 1, 1, 1
                on_press:         root.go_back()

            Label:
                text:      root.score_text
                font_size: sp(15)
                color:     1, 0.85, 0, 1
                bold:      True

            Label:
                text:      root.level_text
                font_size: sp(15)
                color:     0.68, 0.80, 1, 1

            Button:
                text:            root.hints_text
                size_hint_x:     None
                width:           dp(80)
                font_size:       sp(13)
                bold:            True
                background_normal: ''
                background_color:  0, 0, 0, 0
                color:           (1, 0.82, 0.18, 1) if root.can_afford_hint else (0.55, 0.55, 0.65, 1)
                on_press:        root.use_hint()
                canvas.before:
                    Color:
                        rgba: (0.48, 0.36, 0.02, 1) if root.can_afford_hint else (0.22, 0.22, 0.32, 1)
                    RoundedRectangle:
                        pos:    self.pos
                        size:   self.size
                        radius: [dp(8)]

        # 2x2 image grid
        GridLayout:
            id:          img_grid
            cols:        2
            spacing:     dp(4)
            size_hint_y: 0.42

        # Status / loading label
        Label:
            text:        root.status_text
            font_size:   sp(13)
            color:       0.58, 0.68, 0.88, 1
            size_hint_y: None
            height:      dp(22)

        # Answer boxes row
        BoxLayout:
            id:          answer_row
            size_hint_y: None
            height:      dp(54)
            spacing:     dp(4)
            padding:     [dp(8), dp(2)]
            opacity:     1 if root.game_ready else 0
            disabled:    not root.game_ready

        # Feedback label
        Label:
            text:        root.feedback_text
            font_size:   sp(15)
            bold:        True
            color:       (0.28, 1, 0.28, 1) if root.feedback_correct \
                         else (1, 0.38, 0.38, 1)
            size_hint_y: None
            height:      dp(28)
            opacity:     1 if root.game_ready else 0

        # Scrambled letter buttons
        GridLayout:
            id:          letter_grid
            cols:        6
            spacing:     dp(4)
            padding:     [dp(4), dp(2)]
            size_hint_y: None
            height:      dp(110)
            opacity:     1 if root.game_ready else 0
            disabled:    not root.game_ready

        # Bottom controls
        BoxLayout:
            size_hint_y: None
            height:      dp(44)
            spacing:     dp(8)
            padding:     [dp(8), dp(2)]
            opacity:     1 if root.game_ready else 0
            disabled:    not root.game_ready

            Button:
                text:            'SKIP'
                font_size:       sp(13)
                background_normal: ''
                background_color: (0.55, 0.14, 0.14, 1) if self.state == 'normal' \
                                  else (0.42, 0.10, 0.10, 1)
                color:           1, 1, 1, 1
                on_press:        root.skip_word()

            Button:
                text:            'CLEAR'
                font_size:       sp(13)
                background_normal: ''
                background_color: (0.24, 0.24, 0.50, 1) if self.state == 'normal' \
                                  else (0.18, 0.18, 0.40, 1)
                color:           1, 1, 1, 1
                on_press:        root.clear_answer()

# ── Profile / Settings Screen ────────────────────────────────────────────────

<ProfileScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding:     dp(20)
        spacing:     dp(12)
        canvas.before:
            Color:
                rgba: 0.07, 0.07, 0.23, 1
            Rectangle:
                pos:  self.pos
                size: self.size

        # Header
        BoxLayout:
            size_hint_y: None
            height:      dp(50)
            spacing:     dp(10)

            Button:
                text:            '< Back'
                size_hint_x:     None
                width:           dp(82)
                background_color: 0.20, 0.20, 0.50, 1
                color:           1, 1, 1, 1
                font_size:       sp(14)
                on_press:        root.go_back()

            Label:
                text:      'Profile & Settings'
                font_size: sp(22)
                bold:      True
                color:     1, 1, 1, 1

        # Username input
        Label:
            text:        'Username'
            color:       0.68, 0.68, 0.88, 1
            font_size:   sp(13)
            size_hint_y: None
            height:      dp(22)
            halign:      'left'
            text_size:   self.size

        TextInput:
            id:          username_input
            font_size:   sp(17)
            size_hint_y: None
            height:      dp(44)
            multiline:   False
            hint_text:   'Enter your name'
            on_text_validate: root.save_all()

        # Stats grid
        GridLayout:
            cols:        2
            spacing:     dp(10)
            size_hint_y: None
            height:      dp(110)

            BoxLayout:
                orientation: 'vertical'
                padding: dp(10)
                canvas.before:
                    Color:
                        rgba: 0.14, 0.14, 0.38, 1
                    RoundedRectangle:
                        pos:    self.pos
                        size:   self.size
                        radius: [dp(10)]
                Label:
                    text:      root.stat_high_score
                    font_size: sp(24)
                    bold:      True
                    color:     1, 0.82, 0, 1
                Label:
                    text:      'High Score'
                    font_size: sp(12)
                    color:     0.68, 0.68, 0.88, 1

            BoxLayout:
                orientation: 'vertical'
                padding: dp(10)
                canvas.before:
                    Color:
                        rgba: 0.14, 0.14, 0.38, 1
                    RoundedRectangle:
                        pos:    self.pos
                        size:   self.size
                        radius: [dp(10)]
                Label:
                    text:      root.stat_words_done
                    font_size: sp(24)
                    bold:      True
                    color:     0.38, 1, 0.38, 1
                Label:
                    text:      'Words Done'
                    font_size: sp(12)
                    color:     0.68, 0.68, 0.88, 1

        # Cache info + clear button
        BoxLayout:
            size_hint_y: None
            height:      dp(40)
            spacing:     dp(8)

            Label:
                text:      root.cache_info
                font_size: sp(13)
                color:     0.58, 0.58, 0.78, 1

            Button:
                text:            'Clear Cache'
                size_hint_x:     None
                width:           dp(100)
                font_size:       sp(12)
                background_color: 0.40, 0.18, 0.18, 1
                color:           1, 1, 1, 1
                on_press:        root.clear_cache()

        # Reset progress button
        Button:
            text:            'RESET PROGRESS'
            font_size:       sp(14)
            size_hint_y:     None
            height:          dp(42)
            background_normal: ''
            background_color: 0, 0, 0, 0
            color:           1, 0.5, 0.5, 1
            on_press:        root.confirm_reset()
            canvas.before:
                Color:
                    rgba: 0.40, 0.12, 0.12, 1
                RoundedRectangle:
                    pos:    self.pos
                    size:   self.size
                    radius: [dp(10)]

        # Save button
        Button:
            text:            'SAVE SETTINGS'
            font_size:       sp(18)
            bold:            True
            size_hint_y:     None
            height:          dp(55)
            background_normal: ''
            background_color: 0, 0, 0, 0
            color:           1, 1, 1, 1
            on_press:        root.save_all()
            canvas.before:
                Color:
                    rgba: (0.18, 0.58, 0.90, 1) if self.state == 'normal' \
                          else (0.10, 0.44, 0.74, 1)
                RoundedRectangle:
                    pos:    self.pos
                    size:   self.size
                    radius: [dp(12)]

        Widget:
"""


# ── Screen classes ────────────────────────────────────────────────────────────

class MainMenuScreen(Screen):
    welcome_text = StringProperty("Welcome!")
    menu_score   = StringProperty("0")
    menu_level   = StringProperty("1")

    def on_enter(self):
        ud = App.get_running_app().user_data
        self.welcome_text = f"Welcome, {ud.username}!"
        self.menu_score   = str(ud.score)
        self.menu_level   = str(ud.level)

    def start_game(self):
        app = App.get_running_app()
        app.user_data.start_game()
        self.manager.transition = FadeTransition(duration=0.2)
        self.manager.current = "game"

    def go_profile(self):
        self.manager.transition = FadeTransition(duration=0.2)
        self.manager.current = "profile"


class GameScreen(Screen):
    score_text       = StringProperty("Score: 0")
    level_text       = StringProperty("Lvl 1")
    hints_text       = StringProperty(f"Hint ({HINT_COST} pts)")
    status_text      = StringProperty("")
    feedback_text    = StringProperty("")
    feedback_correct = BooleanProperty(False)
    game_ready       = BooleanProperty(False)
    can_afford_hint  = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_word:    str   = ""
        self.current_hint_str: str  = ""
        self.current_letters: list  = []   # 12 uppercase chars
        self.answer_state:    list  = []   # list of [char, src_btn_idx]
        self.letter_btns:     list  = []
        self.answer_btns:     list  = []
        self._loading:        bool  = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self):
        self._refresh_stats()
        self._load_new_word()

    def _refresh_stats(self):
        ud = App.get_running_app().user_data
        self.score_text     = f"Score: {ud.score}"
        self.level_text     = f"Lvl {ud.level}"
        self.hints_text     = f"Hint ({HINT_COST} pts)"
        self.can_afford_hint = ud.score >= HINT_COST

    # ── word loading ──────────────────────────────────────────────────────────

    def _load_new_word(self):
        ud        = App.get_running_app().user_data
        completed = set(ud.data.get("completed_words", []))
        available = [(w, h, d) for w, h, d in WORDS if w.lower() not in completed]

        if not available:
            self._show_all_complete()
            return

        # Fully random — any unseen word can appear
        chosen = random.choice(available)
        self.current_word     = chosen[0].upper()
        self.current_hint_str = chosen[1]

        self.feedback_text = ""
        self._build_answer_row()
        self._build_letter_grid()
        self._show_loading_placeholders()

        # Fetch images on a background thread
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _show_loading_placeholders(self):
        """Single centered animated loader while images are downloading."""
        # Cancel any previous animation
        if hasattr(self, "_loader_event") and self._loader_event:
            self._loader_event.cancel()
            self._loader_event = None

        self.game_ready  = False   # hide answer/letter UI
        self.feedback_text = ""

        grid = self.ids.img_grid
        grid.clear_widgets()
        grid.cols = 1          # Let loader span the full area
        self.status_text = ""  # No text outside the grid during loading

        self._loader_label = Label(
            text="Loading",
            font_size=sp(26),
            bold=True,
            color=(0.55, 0.65, 1, 1),
            halign="center",
            valign="middle",
        )
        self._loader_label.bind(size=self._loader_label.setter("text_size"))
        grid.add_widget(self._loader_label)

        self._loader_tick = 0
        self._loader_event = Clock.schedule_interval(self._tick_loader, 0.38)

    def _tick_loader(self, dt):
        dots = "." * (self._loader_tick % 4)
        self._loader_label.text = f"Loading{dots}"
        self._loader_tick += 1

    def _fetch_thread(self):
        app = App.get_running_app()
        try:
            paths = app.api_handler.get_images_sync(self.current_word.lower())
            Clock.schedule_once(lambda dt: self._on_images(paths), 0)
        except Exception as exc:
            print(f"[ImageFetch] {exc}")
            Clock.schedule_once(lambda dt: self._on_images(None), 0)

    def _on_images(self, paths):
        """Called on the main thread once all 4 images are ready — show them all at once."""
        # Stop loader animation
        if hasattr(self, "_loader_event") and self._loader_event:
            self._loader_event.cancel()
            self._loader_event = None

        grid = self.ids.img_grid
        grid.cols = 2          # Restore 2x2 layout
        grid.clear_widgets()

        if paths and len(paths) >= 4:
            self.status_text = ""
            for p in paths[:4]:
                grid.add_widget(AsyncImage(
                    source=p,
                    allow_stretch=True,
                    keep_ratio=False,
                    nocache=False,
                ))
            self.game_ready = True   # reveal answer/letter UI
        else:
            self.status_text = "Could not load images - check connection."
            self.game_ready  = True  # still reveal so player can skip

    # ── UI builders ───────────────────────────────────────────────────────────

    def _build_answer_row(self):
        row = self.ids.answer_row
        row.clear_widgets()
        n = len(self.current_word)
        self.answer_state = [["", -1] for _ in range(n)]
        self.answer_btns  = []

        for i in range(n):
            btn = Factory.AnswerBtn(text="")
            btn.bind(on_press=lambda b, idx=i: self._remove_letter(idx))
            self.answer_btns.append(btn)
            row.add_widget(btn)

    def _build_letter_grid(self):
        grid = self.ids.letter_grid
        grid.clear_widgets()

        # Guarantee all word letters appear; pad to 12 with randoms
        pool = list(self.current_word)
        while len(pool) < 12:
            pool.append(random.choice(string.ascii_uppercase))
        random.shuffle(pool)
        self.current_letters = pool
        self.letter_btns     = []

        for i, ch in enumerate(pool):
            btn = Factory.LetterBtn(text=ch)
            btn.bind(on_press=lambda b, idx=i: self._place_letter(idx))
            self.letter_btns.append(btn)
            grid.add_widget(btn)

    # ── game logic ────────────────────────────────────────────────────────────

    def _place_letter(self, btn_idx: int):
        if self.letter_btns[btn_idx].disabled:
            return
        # Find the first empty answer slot
        for i, state in enumerate(self.answer_state):
            if state[0] == "":
                state[0] = self.current_letters[btn_idx]
                state[1] = btn_idx
                self.answer_btns[i].text = state[0]
                self.letter_btns[btn_idx].disabled = True
                break
        # Auto-check when all slots are filled
        if all(s[0] != "" for s in self.answer_state):
            Clock.schedule_once(lambda dt: self._check_answer(), 0.1)

    def _remove_letter(self, answer_idx: int):
        state = self.answer_state[answer_idx]
        if state[0] == "":
            return
        src = state[1]
        state[0] = ""
        state[1] = -1
        self.answer_btns[answer_idx].text = ""
        if src >= 0:
            self.letter_btns[src].disabled = False
        self.feedback_text = ""

    def _check_answer(self):
        answer = "".join(s[0] for s in self.answer_state)
        if answer == self.current_word:
            self._on_correct()
        else:
            self._on_wrong()

    def _on_correct(self):
        app = App.get_running_app()
        pts = 100 * app.user_data.level
        app.user_data.add_score(pts)
        app.user_data.complete_word(self.current_word.lower())
        self._refresh_stats()
        self.feedback_correct = True
        self.feedback_text    = f"Correct! +{pts} pts"
        Clock.schedule_once(lambda dt: self._load_new_word(), 2.2)

    def _on_wrong(self):
        self.feedback_correct = False
        self.feedback_text    = "Not quite — try again!"
        Clock.schedule_once(lambda dt: self.clear_answer(), 1.0)

    # ── public button actions ─────────────────────────────────────────────────

    def clear_answer(self, *_):
        self.feedback_text = ""
        for i, state in enumerate(self.answer_state):
            if state[1] >= 0:
                self.letter_btns[state[1]].disabled = False
            state[0] = ""
            state[1] = -1
            self.answer_btns[i].text = ""

    def use_hint(self):
        app = App.get_running_app()
        if not app.user_data.use_hint():
            self.feedback_correct = False
            self.feedback_text    = f"Need {HINT_COST} pts to use a hint!"
            Clock.schedule_once(lambda dt: setattr(self, "feedback_text", ""), 2.0)
            return
        self._refresh_stats()
        # Reveal the first empty answer slot's correct letter
        for i, state in enumerate(self.answer_state):
            if state[0] == "":
                needed = self.current_word[i]
                for j, ch in enumerate(self.current_letters):
                    if ch == needed and not self.letter_btns[j].disabled:
                        self._place_letter(j)
                        return

    def skip_word(self):
        self.feedback_text = ""
        self._load_new_word()

    def go_back(self):
        self.manager.transition = FadeTransition(duration=0.2)
        self.manager.current    = "menu"

    # ── all-complete popup ────────────────────────────────────────────────────

    def _show_all_complete(self):
        app     = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        content.add_widget(Label(
            text="You completed every word!\nIncredible!",
            font_size=sp(20), halign="center", bold=True,
            color=(1, 0.82, 0, 1),
        ))
        content.add_widget(Label(
            text=f"Final Score: {app.user_data.score}",
            font_size=sp(18), halign="center",
        ))
        btn = Button(
            text="Play Again (Reset Progress)",
            size_hint_y=None, height=dp(50),
            background_color=(0.18, 0.52, 0.82, 1),
        )
        content.add_widget(btn)
        popup = Popup(title="All Done!", content=content,
                      size_hint=(0.9, 0.52), auto_dismiss=False)

        def _reset(_):
            popup.dismiss()
            app.user_data.reset_progress()
            self._refresh_stats()
            self._load_new_word()

        btn.bind(on_press=_reset)
        popup.open()


class ProfileScreen(Screen):
    stat_high_score = StringProperty("0")
    stat_words_done = StringProperty("0")
    cache_info      = StringProperty("Cache: 0 MB")

    def on_enter(self):
        app = App.get_running_app()
        ud  = app.user_data
        self.ids.username_input.text = ud.username
        self.stat_high_score = str(ud.high_score)
        self.stat_words_done = str(len(ud.data.get("completed_words", [])))
        mb = app.api_handler.cache_size_mb()
        self.cache_info = f"Image cache: {mb} MB"

    def save_all(self):
        app  = App.get_running_app()
        ud   = app.user_data

        name = self.ids.username_input.text.strip()
        if name:
            ud.data["username"] = name

        ud.save()
        self._toast("Settings saved!")

    def clear_cache(self):
        app = App.get_running_app()
        app.api_handler.clear_cache()
        self.cache_info = "Image cache: 0 MB"
        self._toast("Cache cleared.")

    def confirm_reset(self):
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        content.add_widget(Label(
            text="Reset ALL progress?\n(Score, level, completed words)",
            font_size=sp(15), halign="center",
        ))
        btns = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))

        popup = Popup(title="Reset Progress?", content=content,
                      size_hint=(0.88, 0.4), auto_dismiss=True)

        yes = Button(text="Yes, reset", background_color=(0.6, 0.15, 0.15, 1))
        no  = Button(text="Cancel",     background_color=(0.25, 0.25, 0.50, 1))

        def _do_reset(_):
            App.get_running_app().user_data.reset_progress()
            self.on_enter()
            popup.dismiss()
            self._toast("Progress reset.")

        yes.bind(on_press=_do_reset)
        no.bind(on_press=popup.dismiss)
        btns.add_widget(yes)
        btns.add_widget(no)
        content.add_widget(btns)
        popup.open()

    def go_back(self):
        self.manager.transition = FadeTransition(duration=0.2)
        self.manager.current    = "menu"

    def _toast(self, msg: str):
        p = Popup(title="", content=Label(text=msg, font_size=sp(15)),
                  size_hint=(0.65, 0.22), auto_dismiss=True)
        p.open()
        Clock.schedule_once(lambda dt: p.dismiss(), 1.6)


# ── Application class ─────────────────────────────────────────────────────────

class FourPicsApp(App):
    """Entry point — wires together data, API, and screens."""
    icon = 'icon.png'

    def build(self):
        data_dir  = self.user_data_dir
        cache_dir = os.path.join(data_dir, "image_cache")

        self.user_data   = UserData(data_dir)
        self.api_handler = ImageAPIHandler(cache_dir)

        Builder.load_string(KV)

        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name="menu"))
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(ProfileScreen(name="profile"))
        return sm

    # Android lifecycle hooks
    def on_pause(self):
        self.user_data.save()
        return True   # must return True to allow pause on Android

    def on_resume(self):
        pass

    def on_stop(self):
        self.user_data.save()


if __name__ == "__main__":
    FourPicsApp().run()
