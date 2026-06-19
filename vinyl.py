# main.py
# Minimal black-theme smartphone music player built with KivyMD
# Features: play / prev / next / loop / shuffle / file+folder picker / Android storage permission
# Monthly wrap (Spotify-style local stats) / audio output device label
# Best used with Buildozer for Android APK

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.core.audio import SoundLoader
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.filemanager import MDFileManager
import os
import random
import sqlite3
from datetime import datetime

KV = '''
MDScreen:
    md_bg_color: 0, 0, 0, 1

    MDBoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20

        MDLabel:
            text: app.current_track if app.current_track else 'No song selected'
            halign: 'center'
            theme_text_color: 'Custom'
            text_color: 1,1,1,1
            font_style: 'H6'

        MDLabel:
            text: 'Output: ' + app.output_device
            halign: 'center'
            theme_text_color: 'Custom'
            text_color: 0.7,0.7,0.7,1

        MDBoxLayout:
            adaptive_height: True
            spacing: 10

            MDRaisedButton:
                text: 'Select File'
                on_release: app.open_file_picker(False)

            MDRaisedButton:
                text: 'Select Folder'
                on_release: app.open_file_picker(True)

            MDRaisedButton:
                text: 'Monthly Wrap'
                on_release: app.show_wrap()

        Widget:

        MDBoxLayout:
            adaptive_height: True
            spacing: 10
            pos_hint: {'center_x': 0.5}

            MDIconButton:
                icon: 'skip-previous'
                theme_icon_color: 'Custom'
                icon_color: 1,1,1,1
                on_release: app.prev_track()

            MDIconButton:
                icon: 'pause' if app.sound and app.sound.state == 'play' and not app.is_paused else 'play'
                theme_icon_color: 'Custom'
                icon_color: 1,1,1,1
                on_release: app.toggle_play_pause()

            MDIconButton:
                icon: 'skip-next'
                theme_icon_color: 'Custom'
                icon_color: 1,1,1,1
                on_release: app.next_track()

            MDIconButton:
                icon: 'repeat'
                theme_icon_color: 'Custom'
                icon_color: 1,1,1,1
                on_release: app.toggle_loop()

            MDIconButton:
                icon: 'shuffle'
                theme_icon_color: 'Custom'
                icon_color: 1,1,1,1
                on_release: app.toggle_shuffle()
'''


class MusicPlayerApp(MDApp):
    current_track = StringProperty('')
    is_paused = BooleanProperty(False)
    output_device = StringProperty('Phone Speaker')
    playlist = ListProperty([])
    current_index = NumericProperty(0)
    loop = BooleanProperty(False)
    shuffle = BooleanProperty(False)

    def build(self):
        self.theme_cls.theme_style = 'Dark'
        self.file_manager = MDFileManager(
            exit_manager=self.close_picker,
            select_path=self.select_path,
        )
        self.sound = None
        self.selecting_folder = False
        self.setup_db()
        self.request_android_permissions()
        Clock.schedule_interval(lambda dt: self.detect_output_device(), 3)
        return Builder.load_string(KV)

    def setup_db(self):
        self.conn = sqlite3.connect('music_stats.db')
        self.cur = self.conn.cursor()
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS plays (
                track TEXT,
                played_at TEXT
            )
        ''')
        self.conn.commit()

    def request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        except Exception:
            # Running on desktop / Windows
            pass

    def open_file_picker(self, folder_mode=False):
        self.selecting_folder = folder_mode
        self.file_manager.show('/')

    def close_picker(self, *args):
        self.file_manager.close()

    def select_path(self, path):
        self.close_picker()
        if self.selecting_folder and os.path.isdir(path):
            self.playlist = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if f.lower().endswith(('.mp3', '.wav', '.ogg'))
            ]
        elif os.path.isfile(path):
            self.playlist = [path]

        self.current_index = 0
        if self.playlist:
            self.load_current()

    def load_current(self):
        if not self.playlist:
            return
        track = self.playlist[self.current_index]
        self.current_track = os.path.basename(track)
        self.sound = SoundLoader.load(track)

    def toggle_play_pause(self):
        if not self.playlist:
            return
        if self.sound is None:
            self.load_current()
        if self.sound:
            if self.sound.state == 'play' and not self.is_paused:
                self.sound.stop()
                self.is_paused = True
            else:
                self.sound.play()
                self.is_paused = False
                self.log_play(self.current_track)

    def play_track(self):
        if not self.playlist:
            return
        if self.sound is None:
            self.load_current()
        if self.sound:
            self.sound.play()
            self.log_play(self.current_track)

    def next_track(self):
        if not self.playlist:
            return
        if self.shuffle:
            self.current_index = random.randint(0, len(self.playlist) - 1)
        else:
            self.current_index = (self.current_index + 1) % len(self.playlist)
        self.load_current()
        self.play_track()

    def prev_track(self):
        if not self.playlist:
            return
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.load_current()
        self.play_track()

    def toggle_loop(self):
        self.loop = not self.loop
        print('Loop:', self.loop)

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        print('Shuffle:', self.shuffle)

    def detect_output_device(self):
        # Placeholder for Android audio routing integration
        # Extend with pyjnius AudioManager for exact route detection
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            activity = PythonActivity.mActivity
            audio = activity.getSystemService(Context.AUDIO_SERVICE)
            if audio.isBluetoothA2dpOn():
                self.output_device = 'Bluetooth / Car / Soundbar'
            elif audio.isWiredHeadsetOn():
                self.output_device = 'Headphones'
            else:
                self.output_device = 'Phone Speaker'
        except Exception:
            self.output_device = 'Desktop Speaker'

    def log_play(self, track):
        self.cur.execute(
            'INSERT INTO plays(track, played_at) VALUES(?, ?)',
            (track, datetime.now().isoformat())
        )
        self.conn.commit()

    def show_wrap(self):
        month = datetime.now().strftime('%Y-%m')
        self.cur.execute(
            "SELECT track, COUNT(*) as c FROM plays WHERE played_at LIKE ? GROUP BY track ORDER BY c DESC LIMIT 5",
            (f'{month}%',)
        )
        top = self.cur.fetchall()
        print('Monthly Wrap Top Songs:')
        for name, count in top:
            print(name, count)


MusicPlayerApp().run()
