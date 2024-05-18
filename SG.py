import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pydub import AudioSegment
from TTS.api import TTS
import tempfile
import threading
import os
import traceback
import pygame
import simpleaudio as sa

class LayerControl(ttk.Frame):
    def __init__(self, parent, layer_number, remove_layer_callback):
        super().__init__(parent)
        self.layer_number = layer_number
        self.remove_layer_callback = remove_layer_callback

        ttk.Label(self, text=f"Layer {self.layer_number} Text:").grid(row=0, column=0, sticky="w")
        self.affirmation_text = ttk.Entry(self)
        self.affirmation_text.grid(row=0, column=1)

        ttk.Label(self, text="Volume (dB):").grid(row=1, column=0, sticky="w")
        self.volume = ttk.Entry(self)
        self.volume.grid(row=1, column=1)
        self.volume.insert(0, "0")

        ttk.Label(self, text="Play Rate:").grid(row=2, column=0, sticky="w")
        self.play_rate = ttk.Entry(self)
        self.play_rate.grid(row=2, column=1)
        self.play_rate.insert(0, "1.0")

        self.remove_button = ttk.Button(self, text="Remove Layer", command=self.remove_layer)
        self.remove_button.grid(row=3, column=0, columnspan=2, pady=5)

    def remove_layer(self):
        self.remove_layer_callback(self)

def generate_tts(text, filename):
    try:
        tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
        tts.tts_to_file(text=text, file_path=filename, bitrate="128k")
        print(f"Generated TTS for text '{text}' and saved to '{filename}'")
    except Exception as e:
        print(f"Error generating TTS: {e}")
        traceback.print_exc()

def add_affirmations(layer_controls, progress_var, progress_bar):
    try:
        combined_audio = None
        num_layers = len(layer_controls)
        for idx, control in enumerate(layer_controls):
            affirmation_text = control.affirmation_text.get()
            try:
                volume = int(control.volume.get())
                play_rate = float(control.play_rate.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric values for volume and play rate.")
                return None

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                generate_tts(affirmation_text, fp.name)
                affirmation = AudioSegment.from_wav(fp.name)
                affirmation = affirmation + volume  # Adjust volume
                if play_rate != 1.0:
                    affirmation = affirmation.speedup(playback_speed=play_rate, chunk_size=150, crossfade=25)

            if combined_audio is None:
                combined_audio = affirmation
            else:
                combined_audio = combined_audio.overlay(affirmation)

            os.remove(fp.name)
            progress_var.set((idx + 1) / num_layers * 100)
            progress_bar.update_idletasks()

        return combined_audio
    except Exception as e:
        messagebox.showerror("Error", str(e))
        traceback.print_exc()

def add_automatic_layers(affirmation_text, num_layers, progress_var, progress_bar):
    try:
        base_affirmation = None
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
            generate_tts(affirmation_text, fp.name)
            base_affirmation = AudioSegment.from_wav(fp.name)
            os.remove(fp.name)

        combined_audio = None
        for i in range(num_layers):
            volume = max(-25, -(i * 5))
            play_rate = 10.0 + i * 0.2  # Incrementally increase play rate from 10 to 30
            affirmation = base_affirmation + volume  # Adjust volume
            if play_rate != 1.0:
                affirmation = affirmation.speedup(playback_speed=play_rate, chunk_size=150, crossfade=25)

            if combined_audio is None:
                combined_audio = affirmation
            else:
                combined_audio = combined_audio.overlay(affirmation)

            progress_var.set((i + 1) / num_layers * 100)
            progress_bar.update_idletasks()

        return combined_audio
    except Exception as e:
        messagebox.showerror("Error", str(e))
        traceback.print_exc()

def play_audio(file_path, loop, stop_event):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play(-1 if loop else 0)
    while pygame.mixer.music.get_busy() and not stop_event.is_set():
        pygame.time.Clock().tick(10)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Subliminal Affirmations Generator")
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.configure(bg="#2b2b2b")  # Background color

        self.style = ttk.Style(self)
        self.style.configure("TFrame", background="#2b2b2b")
        self.style.configure("TLabel", background="#2b2b2b", foreground="#00ff00")
        self.style.configure("TButton", background="#2b2b2b", foreground="#00ff00")
        self.style.configure("TScale", background="#2b2b2b", troughcolor="#00ff00")
        self.style.configure("TEntry", fieldbackground="#2b2b2b", foreground="#00ff00")

        self.layer_controls = []

        self.mode_var = tk.StringVar(value="manual")
        self.mode_frame = ttk.Frame(self)
        self.mode_frame.pack(pady=10)

        self.manual_radiobutton = ttk.Radiobutton(self.mode_frame, text="Manual", variable=self.mode_var, value="manual", command=self.update_mode)
        self.manual_radiobutton.grid(row=0, column=0, padx=10)

        self.automatic_radiobutton = ttk.Radiobutton(self.mode_frame, text="Automatic", variable=self.mode_var, value="automatic", command=self.update_mode)
        self.automatic_radiobutton.grid(row=0, column=1, padx=10)

        self.canvas = tk.Canvas(self, bg="#2b2b2b")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.add_layer_button = ttk.Button(self, text="Add Layer", command=self.add_layer)
        self.add_layer_button.pack(pady=10)

        self.clear_manual_button = ttk.Button(self, text="Clear Text (Manual)", command=self.clear_manual_text)
        self.clear_manual_button.pack(pady=5)

        self.copy_manual_button = ttk.Button(self, text="Copy Manual Layers", command=self.copy_manual_layers)
        self.copy_manual_button.pack(pady=5)

        self.automatic_layer_frame = ttk.Frame(self)

        ttk.Label(self.automatic_layer_frame, text="Number of Layers:").grid(row=0, column=0, sticky="w")
        self.num_layers_entry = ttk.Entry(self.automatic_layer_frame)
        self.num_layers_entry.grid(row=0, column=1)
        self.num_layers_entry.insert(0, "1")

        ttk.Label(self.automatic_layer_frame, text="Affirmation Text:").grid(row=1, column=0, sticky="w")
        self.affirmation_text_entry = ttk.Entry(self.automatic_layer_frame)
        self.affirmation_text_entry.grid(row=1, column=1)

        self.clear_automatic_button = ttk.Button(self.automatic_layer_frame, text="Clear Text (Automatic)", command=self.clear_automatic_text)
        self.clear_automatic_button.grid(row=2, column=0, columnspan=2, pady=10)

        self.generate_auto_button = ttk.Button(self.automatic_layer_frame, text="Generate Automatic Layers", command=self.generate_automatic_layers)
        self.generate_auto_button.grid(row=3, column=0, columnspan=2, pady=10)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        self.generate_button = ttk.Button(button_frame, text="Generate", command=self.generate_audio)
        self.generate_button.pack(side="left", padx=5)

        self.save_button = ttk.Button(button_frame, text="Save Audio", command=self.save_audio, state="disabled")
        self.save_button.pack(side="left", padx=5)

        self.play_button = ttk.Button(button_frame, text="Play", command=lambda: self.play_audio(self.loop_var.get()), state="disabled")
        self.play_button.pack(side="left", padx=5)

        self.pause_button = ttk.Button(button_frame, text="Pause", command=self.pause_audio, state="disabled")
        self.pause_button.pack(side="left", padx=5)

        self.loop_var = tk.BooleanVar(value=False)
        self.loop_button = ttk.Checkbutton(button_frame, text="Loop", variable=self.loop_var)
        self.loop_button.pack(side="left", padx=5)

        self.toggle_fullscreen_button = ttk.Button(button_frame, text="Toggle Fullscreen", command=self.toggle_fullscreen)
        self.toggle_fullscreen_button.pack(side="left", padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", padx=10, pady=10)

        self.audio_thread = None
        self.playing = False
        self.stop_event = threading.Event()
        self.fullscreen = False
        self.combined_audio = None

        self.after(10, self.maximize_window)  # Maximize window after it has been created

        self.update_mode()  # Initialize the correct mode

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.attributes("-fullscreen", self.fullscreen)

    def update_mode(self):
        mode = self.mode_var.get()
        if mode == "manual":
            self.automatic_layer_frame.pack_forget()
            self.add_layer_button.pack(pady=10)
            self.scrollable_frame.pack()
        else:
            self.add_layer_button.pack_forget()
            self.scrollable_frame.pack_forget()
            self.automatic_layer_frame.pack(pady=10)

    def add_layer(self):
        layer_number = len(self.layer_controls) + 1
        layer_control = LayerControl(self.scrollable_frame, layer_number, self.remove_layer)
        layer_control.pack(fill="x", pady=5)
        self.layer_controls.append(layer_control)

    def remove_layer(self, layer_control):
        layer_control.pack_forget()
        self.layer_controls.remove(layer_control)
        self.update_layer_numbers()

    def update_layer_numbers(self):
        for idx, layer_control in enumerate(self.layer_controls, start=1):
            layer_control.children[f'!label'].config(text=f"Layer {idx} Text:")

    def clear_manual_text(self):
        for control in self.layer_controls:
            control.affirmation_text.delete(0, tk.END)
            control.volume.delete(0, tk.END)
            control.play_rate.delete(0, tk.END)
            control.volume.insert(0, "0")
            control.play_rate.insert(0, "1.0")

    def copy_manual_layers(self):
        num_layers = len(self.layer_controls)
        for _ in range(num_layers):
            self.add_layer()
        for i in range(num_layers):
            self.layer_controls[num_layers + i].affirmation_text.insert(0, self.layer_controls[i].affirmation_text.get())
            self.layer_controls[num_layers + i].volume.insert(0, self.layer_controls[i].volume.get())
            self.layer_controls[num_layers + i].play_rate.insert(0, self.layer_controls[i].play_rate.get())

    def clear_automatic_text(self):
        self.affirmation_text_entry.delete(0, tk.END)
        self.num_layers_entry.delete(0, tk.END)
        self.num_layers_entry.insert(0, "1")

    def generate_audio(self):
        try:
            if self.layer_controls:
                self.progress_var.set(0)
                self.progress_bar.update_idletasks()
                self.combined_audio = add_affirmations(self.layer_controls, self.progress_var, self.progress_bar)
                if self.combined_audio is not None:
                    messagebox.showinfo("Success", "Audio generated successfully.")
                    self.save_button["state"] = "normal"
                    self.play_button["state"] = "normal"
            else:
                messagebox.showwarning("Warning", "No layers to generate audio.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values.")

    def generate_automatic_layers(self):
        try:
            num_layers = int(self.num_layers_entry.get())
            affirmation_text = self.affirmation_text_entry.get()
            if num_layers < 1:
                messagebox.showerror("Invalid Input", "Number of layers must be at least 1.")
                return
            self.progress_var.set(0)
            self.progress_bar.update_idletasks()
            self.combined_audio = add_automatic_layers(affirmation_text, num_layers, self.progress_var, self.progress_bar)
            if self.combined_audio is not None:
                messagebox.showinfo("Success", "Audio generated successfully.")
                self.save_button["state"] = "normal"
                self.play_button["state"] = "normal"
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number of layers.")

    def save_audio(self):
        if self.combined_audio:
            file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
            if file_path:
                try:
                    self.combined_audio.export(file_path, format="wav")
                    messagebox.showinfo("Success", f"Audio saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
                    traceback.print_exc()
        else:
            messagebox.showwarning("Warning", "No audio generated to save.")

    def play_audio(self, loop=False):
        if self.combined_audio:
            if not self.playing:
                self.playing = True
                self.pause_button["state"] = "normal"
                self.stop_event.clear()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    self.combined_audio.export(fp.name, format="wav")
                    self.audio_thread = threading.Thread(target=play_audio, args=(fp.name, loop, self.stop_event))
                    self.audio_thread.start()
            else:
                messagebox.showwarning("Warning", "Audio is already playing.")
        else:
            messagebox.showwarning("Warning", "No audio generated to play.")

    def pause_audio(self):
        if self.playing:
            self.playing = False
            self.pause_button["state"] = "disabled"
            self.stop_event.set()
            self.audio_thread.join()

    def maximize_window(self):
        self.state("normal")
        self.attributes("-fullscreen", False)
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Error", str(e))
        traceback.print_exc()

