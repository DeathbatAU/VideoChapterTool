import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import re # For sanitizing filenames

class ChapterCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Chapter File Creator")
        self.root.geometry("800x700")

        self.folder_path = tk.StringVar()
        self.video_files = []
        self.current_video_index = -1
        self.processing_batch = False

        self.setup_ui()

    def setup_ui(self):
        # Folder Selection Frame
        folder_frame = ttk.LabelFrame(self.root, text="Select Video Folder")
        folder_frame.pack(padx=10, pady=10, fill="x", expand=True)
        folder_frame.grid_columnconfigure(0, weight=0)
        folder_frame.grid_columnconfigure(1, weight=1)
        folder_frame.grid_columnconfigure(2, weight=0)

        ttk.Label(folder_frame, text="Folder Path:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=70).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(folder_frame, text="Browse Folder", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5, sticky="e")
        ttk.Button(folder_frame, text="Start Chapter Creation Batch", command=self.start_chapter_creation_batch).grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # Current Video Info Frame
        video_info_frame = ttk.LabelFrame(self.root, text="Current Video")
        video_info_frame.pack(padx=10, pady=5, fill="x", expand=True)
        self.current_video_label = ttk.Label(video_info_frame, text="No video loaded.", font=("Arial", 12, "bold"))
        self.current_video_label.pack(padx=5, pady=5, fill="x")

        # Chapters Input Frame
        chapters_frame = ttk.LabelFrame(self.root, text="Chapters Input/Editor (for current video)")
        chapters_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.chapter_text_input = scrolledtext.ScrolledText(chapters_frame, wrap=tk.WORD, width=80, height=15)
        self.chapter_text_input.pack(padx=5, pady=5, fill="both", expand=True)

        # Action Buttons Frame
        action_buttons_frame = ttk.Frame(self.root)
        action_buttons_frame.pack(padx=10, pady=5, fill="x")
        action_buttons_frame.grid_columnconfigure(0, weight=1)
        action_buttons_frame.grid_columnconfigure(1, weight=1)
        action_buttons_frame.grid_columnconfigure(2, weight=1)

        self.save_next_button = ttk.Button(action_buttons_frame, text="Save Chapters & Next Video", command=self.save_chapters_and_next)
        self.save_next_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.skip_button = ttk.Button(action_buttons_frame, text="Skip Video", command=self.skip_video)
        self.skip_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.finish_button = ttk.Button(action_buttons_frame, text="Finish Batch", command=self.finish_batch)
        self.finish_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Status/Log Frame
        status_frame = ttk.LabelFrame(self.root, text="Status / Log")
        status_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.status_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, width=80, height=8, state='disabled')
        self.status_text.pack(padx=5, pady=5, fill="both", expand=True)

        # Initial state of buttons
        self._set_ui_state(False) # Disable action buttons initially

    def _set_ui_state(self, enable):
        """Enables/disables buttons based on batch processing state."""
        self.save_next_button.config(state='normal' if enable else 'disabled')
        self.skip_button.config(state='normal' if enable else 'disabled')
        self.finish_button.config(state='normal' if enable else 'disabled')
        self.chapter_text_input.config(state='normal' if enable else 'disabled')


    def log_message(self, message):
        """Logs messages to the status text area."""
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    def clear_log(self):
        """Clears the status log."""
        self.status_text.config(state='normal')
        self.status_text.delete("1.0", tk.END)
        self.status_text.config(state='disabled')

    def browse_folder(self):
        """Opens a dialog to select a folder."""
        folder_selected = filedialog.askdirectory(title="Select Folder Containing Videos")
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.log_message(f"Selected folder: {folder_selected}")
            self.current_video_label.config(text="Ready to start batch.")
            self._set_ui_state(False) # Disable action buttons until batch starts

    def start_chapter_creation_batch(self):
        """Starts the batch process for creating chapter files."""
        folder = self.folder_path.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder first.")
            return

        if self.processing_batch:
            self.log_message("Batch processing is already active.")
            return

        self.clear_log()
        self.log_message(f"Starting batch chapter file creation in: {folder}")
        
        # Find video files (common extensions)
        self.video_files = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv'))
        ])

        if not self.video_files:
            self.log_message("No video files found in the selected folder.")
            self.processing_batch = False
            self._set_ui_state(False)
            return

        self.log_message(f"Found {len(self.video_files)} video files.")
        self.current_video_index = -1 # Reset index
        self.processing_batch = True
        self._set_ui_state(True) # Enable action buttons
        self.process_next_video()

    def process_next_video(self):
        """Loads the next video file for chapter input."""
        self.current_video_index += 1

        if self.current_video_index < len(self.video_files):
            current_video_name = self.video_files[self.current_video_index]
            self.current_video_label.config(text=f"Processing ({self.current_video_index + 1}/{len(self.video_files)}): {current_video_name}")
            self.chapter_text_input.delete("1.0", tk.END) # Clear previous input

            # Optional: Load existing .txt content if it exists
            base_name, _ = os.path.splitext(current_video_name)
            chapter_txt_path = os.path.join(self.folder_path.get(), f"{base_name}.txt")
            if os.path.exists(chapter_txt_path):
                try:
                    with open(chapter_txt_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    self.chapter_text_input.insert("1.0", existing_content)
                    self.log_message(f"Loaded existing chapters for {current_video_name}")
                except Exception as e:
                    self.log_message(f"Error loading existing chapters for {current_video_name}: {e}")

            self.log_message(f"Ready for chapters for: {current_video_name}")
            self.chapter_text_input.focus_set() # Set focus to the input area
        else:
            self.finish_batch()

    def save_chapters_and_next(self):
        """Saves the current chapter input to a .txt file and moves to the next video."""
        if not self.processing_batch or self.current_video_index == -1:
            return

        current_video_name = self.video_files[self.current_video_index]
        chapter_text = self.chapter_text_input.get("1.0", tk.END).strip()

        if not chapter_text:
            response = messagebox.askyesno("Empty Chapters", "The chapter input is empty. Do you want to save an empty file or skip this video?", icon='warning')
            if not response: # User chose "No" (to not save empty)
                self.log_message(f"Skipping saving chapters for {current_video_name} (empty input).")
                self.process_next_video()
                return
            # If user chose "Yes", proceed to save an empty file (or overwrite with empty)

        base_name, _ = os.path.splitext(current_video_name)
        chapter_txt_path = os.path.join(self.folder_path.get(), f"{base_name}.txt")

        try:
            with open(chapter_txt_path, 'w', encoding='utf-8') as f:
                f.write(chapter_text)
            self.log_message(f"Saved chapters to: {chapter_txt_path}")
        except Exception as e:
            self.log_message(f"Error saving chapters for {current_video_name}: {e}")
            messagebox.showerror("Save Error", f"Could not save chapter file for {current_video_name}: {e}")
        
        self.process_next_video()

    def skip_video(self):
        """Skips the current video without saving chapters and moves to the next."""
        if not self.processing_batch or self.current_video_index == -1:
            return
        
        current_video_name = self.video_files[self.current_video_index]
        self.log_message(f"Skipped: {current_video_name}")
        self.process_next_video()

    def finish_batch(self):
        """Ends the batch processing."""
        self.processing_batch = False
        self.current_video_index = -1
        self.video_files = []
        self.current_video_label.config(text="Batch processing finished.")
        self.chapter_text_input.delete("1.0", tk.END)
        self._set_ui_state(False) # Disable action buttons
        self.log_message("\nBatch chapter file creation complete.")
        messagebox.showinfo("Batch Complete", "All videos processed or skipped.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChapterCreatorApp(root)
    root.mainloop()
