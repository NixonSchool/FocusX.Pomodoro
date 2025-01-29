import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import os
import random
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class PomodoroBlocker:
    def __init__(self):
        # Create the main window
        self.root = tk.Tk()
        self.root.title("Focus Time")
        
        # Window positioning
        window_width = 400
        window_height = 300  # Reduced height since we simplified the interface
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        self.root.attributes('-topmost', True)
        
        # Simple color scheme
        self.colors = {
            'bg': '#ffffff',
            'primary': '#1a73e8',
            'warning': '#ea4335',
            'text': '#202124'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Timer settings
        self.work_duration = 40 * 60  # 40 minutes
        self.rest_duration = 15 * 60  # 15 minutes
        self.is_running = False
        self.is_work_session = True
        
        # Break messages
        self.break_activities = [
            "Take time to read and reflect",
            "Step away from the screen and rest your eyes",
            "Go for a short walk",
            "Do some light stretching",
            "Practice deep breathing",
            "Hydrate yourself",
            "Tidy up your workspace"
        ]
        
        self.overlay = None
        self.setup_ui()
        
        self.blocking = False
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # Audio control
        self.audio = None
        self.init_audio_control()

    def init_audio_control(self):
        """Initialize audio control capabilities"""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.audio = cast(interface, POINTER(IAudioEndpointVolume))
        except:
            print("Could not initialize audio control")

    def mute_audio(self):
        """Mute system audio"""
        if self.audio:
            try:
                self.audio.SetMute(1, None)
            except:
                print("Could not mute audio")

    def unmute_audio(self):
        """Unmute system audio"""
        if self.audio:
            try:
                self.audio.SetMute(0, None)
            except:
                print("Could not unmute audio")

    def setup_ui(self):
        """Set up the simplified UI"""
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Timer display
        self.time_var = tk.StringVar(value="40:00")
        self.time_label = tk.Label(main_frame,
                                 textvariable=self.time_var,
                                 font=('Helvetica', 48, 'bold'),
                                 fg=self.colors['text'],
                                 bg=self.colors['bg'])
        self.time_label.pack(pady=20)
        
        # Status display
        self.status_var = tk.StringVar(value="Ready to focus")
        self.status_label = tk.Label(main_frame,
                                   textvariable=self.status_var,
                                   font=('Helvetica', 14),
                                   fg=self.colors['primary'],
                                   bg=self.colors['bg'])
        self.status_label.pack(pady=10)
        
        # Start button
        self.start_button = tk.Button(main_frame,
                                    text="Start",
                                    command=self.start_timer,
                                    bg=self.colors['primary'],
                                    fg='white',
                                    width=10)
        self.start_button.pack(pady=5)
        
        # Emergency stop button
        self.stop_button = tk.Button(main_frame,
                                   text="Emergency Stop",
                                   command=self.stop_timer,
                                   bg=self.colors['warning'],
                                   fg='white',
                                   width=20)
        self.stop_button.pack(pady=5)

    def create_overlay(self):
        """Create a simple black overlay with periodic message display"""
        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes('-fullscreen', True, '-topmost', True)
        self.overlay.configure(bg='black')
        
        message_label = tk.Label(self.overlay,
                               text=random.choice(self.break_activities),
                               font=('Arial', 24),
                               fg='white',
                               bg='black',
                               wraplength=800)
        message_label.pack(expand=True)
        
        timer_label = tk.Label(self.overlay,
                             font=('Arial', 18),
                             fg='white',
                             bg='black')
        timer_label.pack(pady=20)
        
        def update_display():
            if self.overlay:
                # Update timer
                remaining = int(self.time_var.get().split(':')[0]) * 60 + int(self.time_var.get().split(':')[1])
                mins, secs = divmod(remaining, 60)
                timer_label.config(text=f"Break time remaining: {mins:02d}:{secs:02d}")
                
                # Update message every 5 seconds
                if remaining % 5 == 0:
                    message_label.config(text=random.choice(self.break_activities))
                
                self.overlay.after(1000, update_display)
        
        update_display()

    def start_timer(self):
        """Start the timer cycles"""
        self.is_running = True
        self.is_work_session = True
        threading.Thread(target=self._run_timer, daemon=True).start()

    def stop_timer(self):
        """Emergency stop"""
        self.is_running = False
        self.cleanup()

    def _run_timer(self):
        """Main timer loop"""
        while self.is_running:
            if self.is_work_session:
                self.status_var.set("Work Session")
                self.unblock_input()
                self.unmute_audio()
                if self.overlay:
                    self.overlay.destroy()
                self.countdown(self.work_duration)
            else:
                self.status_var.set("Break Time")
                self.create_overlay()
                self.block_input()
                self.mute_audio()
                self.countdown(self.rest_duration)
            
            if self.is_running:
                self.is_work_session = not self.is_work_session

    def countdown(self, duration):
        """Timer countdown"""
        while duration > 0 and self.is_running:
            minutes, seconds = divmod(duration, 60)
            self.time_var.set(f"{minutes:02d}:{seconds:02d}")
            time.sleep(1)
            duration -= 1

    def cleanup(self):
        """Reset everything"""
        if self.overlay:
            self.overlay.destroy()
        self.unblock_input()
        self.unmute_audio()
        self.time_var.set("40:00")
        self.status_var.set("Ready to focus")
        self.is_work_session = True

    def block_input(self):
        """Block mouse and keyboard"""
        self.blocking = True
        self.mouse_listener = MouseListener(on_move=lambda x, y: False,
                                          on_click=lambda x, y, button, pressed: False)
        self.keyboard_listener = KeyboardListener(on_press=lambda key: False,
                                                on_release=lambda key: False)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def unblock_input(self):
        """Unblock mouse and keyboard"""
        self.blocking = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = PomodoroBlocker()
    app.run()
