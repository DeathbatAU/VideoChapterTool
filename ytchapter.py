import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import re
import subprocess
import os
import threading
from pathlib import Path
import urllib.parse
import json
import time
import sys
import shutil # Added for shutil.which

class VideoChapterTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Chapter Marker Tool - Batch Enabled")
        self.root.geometry("900x850")
        self.video_path = tk.StringVar()
        self.youtube_url = tk.StringVar()
        self.batch_folder = tk.StringVar()
        self.chapters = []
        self.processing = False
        self.downloading = False
        self.batch_processing = False
        self.batch_results = []
        
        # Initialize paths for executables
        self.ffmpeg_path = None
        self.yt_dlp_path = None

        self.setup_ui()
        self.check_dependencies() # Call dependency check after UI setup

    def setup_ui(self):
        # Main Input Frame
        input_frame = ttk.LabelFrame(self.root, text="Video/Batch Configuration")
        input_frame.pack(padx=10, pady=10, fill="x", expand=True)

        # Configure columns for input_frame to allow consistent sizing
        input_frame.grid_columnconfigure(0, weight=0) # Labels, min width
        input_frame.grid_columnconfigure(1, weight=1) # Entries, expand
        input_frame.grid_columnconfigure(2, weight=0) # Buttons, min width (will hold a frame of buttons)

        # --- Row 0: Video File Path ---
        ttk.Label(input_frame, text="Video File Path (for single video):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(input_frame, textvariable=self.video_path, width=70).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        single_video_buttons_frame = ttk.Frame(input_frame)
        single_video_buttons_frame.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Button(single_video_buttons_frame, text="Browse Video", command=self.browse_video).pack(side=tk.LEFT, fill="x", expand=True)

        # --- Row 1: Batch Folder Path & Start Batch ---
        ttk.Label(input_frame, text="Batch Folder (for multiple videos):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(input_frame, textvariable=self.batch_folder, width=70).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        batch_buttons_frame = ttk.Frame(input_frame)
        batch_buttons_frame.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Button(batch_buttons_frame, text="Browse Folder", command=self.browse_batch_folder).pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 2))
        ttk.Button(batch_buttons_frame, text="Start Batch", command=self.start_batch_processing_thread).pack(side=tk.LEFT, fill="x", expand=True)

        # --- Row 2: YouTube URL and related buttons ---
        ttk.Label(input_frame, text="YouTube URL (Optional):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(input_frame, textvariable=self.youtube_url, width=70).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        youtube_buttons_frame = ttk.Frame(input_frame)
        youtube_buttons_frame.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        ttk.Button(youtube_buttons_frame, text="Download Video", command=self.start_youtube_download_thread).pack(side=tk.LEFT, fill="x", expand=True)
        # Removed the "Extract Chapters" button from here

        # --- Chapter Input and Display ---
        chapter_frame = ttk.LabelFrame(self.root, text="Chapters Input/Editor")
        chapter_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.chapter_text = scrolledtext.ScrolledText(chapter_frame, wrap=tk.WORD, width=80, height=15)
        self.chapter_text.pack(padx=5, pady=5, fill="both", expand=True)

        parse_button = ttk.Button(chapter_frame, text="Parse Chapters from Text", command=self.parse_chapters_from_text_wrapper)
        parse_button.pack(pady=5)

        # --- Actions (Apply Chapters) ---
        action_frame = ttk.LabelFrame(self.root, text="Apply Chapters to Video")
        action_frame.pack(padx=10, pady=5, fill="x")

        ttk.Button(action_frame, text="Burn Chapters into Video (Overwrite)", command=self.start_burn_chapters_thread).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(action_frame, text="Create New Video with Chapters ('_chapters' suffix)", command=self.start_create_new_chapter_video_thread).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(action_frame, text="Clear All Inputs & Log", command=self.clear_all).pack(side=tk.RIGHT, padx=5, pady=5)

        # --- Status and Log ---
        status_frame = ttk.LabelFrame(self.root, text="Status / Log")
        status_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.status_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, width=80, height=8, state='disabled')
        self.status_text.pack(padx=5, pady=5, fill="both", expand=True)

        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(padx=10, pady=5, fill="x")

    def _find_executable_path(self, base_name):
        """
        Finds the full path to an executable, prioritizing the script's directory.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Check for platform-specific names (e.g., .exe on Windows)
        # We check both base_name and base_name.exe on Windows for local files
        local_path = os.path.join(script_dir, base_name)
        local_path_exe = os.path.join(script_dir, base_name + ".exe")

        if sys.platform == "win32" and os.path.exists(local_path_exe) and os.path.isfile(local_path_exe):
            return local_path_exe
        elif os.path.exists(local_path) and os.path.isfile(local_path):
            return local_path
        
        # Fallback to checking PATH using shutil.which
        # shutil.which handles .exe extension and PATHEXT on Windows automatically
        return shutil.which(base_name)

    def check_dependencies(self):
        """Checks if FFmpeg and yt-dlp are installed and on PATH or in the script directory."""
        self.log_message("Checking dependencies: FFmpeg and yt-dlp...")

        # Check FFmpeg
        self.ffmpeg_path = self._find_executable_path('ffmpeg')
        if self.ffmpeg_path:
            self.log_message(f"FFmpeg found at: {self.ffmpeg_path}")
        else:
            self.log_message("WARNING: FFmpeg not found. Please place 'ffmpeg' (or 'ffmpeg.exe') in the script folder or ensure it's on your system's PATH.")

        # Check yt-dlp
        self.yt_dlp_path = self._find_executable_path('yt-dlp')
        if self.yt_dlp_path:
            self.log_message(f"yt-dlp found at: {self.yt_dlp_path}")
        else:
            self.log_message("WARNING: yt-dlp not found. Please place 'yt-dlp' (or 'yt-dlp.exe') in the script folder or ensure it's on your system's PATH.")

        self.log_message("Dependency check complete.")


    def parse_chapters_from_text(self, comment_text):
        """Parse chapters from comment text"""
        chapters = []
        lines = [line.strip() for line in comment_text.split('\n') if line.strip()]

        pattern1 = r'^(\d{1,2}:\d{2})\s*[-:]?\s*(.+?)$'  # Time first
        pattern2 = r'^(.+?)\s*[-:]?\s*(\d{1,2}:\d{2})$'  # Title first

        matches1 = []
        matches2 = []

        for line in lines:
            match1 = re.match(pattern1, line)
            match2 = re.match(pattern2, line)

            if match1:
                matches1.append(match1)
            elif match2:
                matches2.append(match2)

        use_matches = matches1 if len(matches1) >= len(matches2) else matches2

        for match in use_matches:
            if len(match.groups()) == 2:
                time, title = match.groups()
                if len(time.split(':')) == 2:
                    time = '00:' + time
                chapters.append((time, title.strip()))

        return chapters

    def browse_video(self):
        file_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.flv *.webm"), ("All files", "*.*")]
        )
        if file_path:
            self.video_path.set(file_path)
            self.log_message(f"Selected video: {file_path}")

    def start_youtube_download_thread(self):
        if self.yt_dlp_path is None:
            messagebox.showerror("Error", "yt-dlp executable not found. Please place it in the script folder or ensure it's on your system's PATH. Check the log for details.")
            return

        url = self.youtube_url.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL to download.")
            return
        if self.downloading:
            self.log_message("Already downloading a video. Please wait.")
            return

        self.downloading = True
        self.log_message(f"Starting YouTube video download for: {url}")
        threading.Thread(target=self._download_youtube_video, args=(url,)).start()

    def _download_youtube_video(self, url):
        try:
            # First, get video title to use as filename
            info_command = [self.yt_dlp_path, '--get-title', url]
            title_process = subprocess.Popen(info_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            title_output, title_error = title_process.communicate()

            if title_process.returncode != 0:
                self.log_message(f"Error getting video title: {title_error.strip()}")
                return

            video_title = title_output.strip()
            # Sanitize filename
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '', video_title)
            output_template = f"{sanitized_title}.%(ext)s"

            self.log_message(f"Downloading YouTube video '{video_title}' to '{output_template}'...")

            command = [self.yt_dlp_path, '-f', 'bestvideo+bestaudio/best', '--merge-output-format', 'mp4', url, '-o', output_template]
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in iter(process.stdout.readline, ''):
                self.log_message(f"Download: {line.strip()}")
                self.root.update_idletasks()
            
            stderr_output = process.stderr.read()
            if stderr_output:
                self.log_message(f"Download Error: {stderr_output.strip()}")
            
            process.wait()

            if process.returncode == 0:
                # Find the downloaded file based on the sanitized title and common extensions
                downloaded_file = None
                for ext in ['mp4', 'mkv', 'webm', 'flv', 'avi']: # Common extensions
                    potential_path = f"{sanitized_title}.{ext}"
                    if os.path.exists(potential_path):
                        downloaded_file = os.path.abspath(potential_path)
                        break

                if downloaded_file:
                    self.video_path.set(downloaded_file)
                    self.log_message(f"YouTube video downloaded successfully to: {downloaded_file}")
                else:
                    self.log_message("Error: Downloaded video file not found after successful download command (check expected filename).")
            else:
                self.log_message(f"YouTube download failed with exit code {process.returncode}")
                self.log_message(f"stderr: {stderr_output}")

        except Exception as e:
            self.log_message(f"An error occurred during YouTube download: {e}")
        finally:
            self.downloading = False
            self.progress_bar.stop()

    # Removed start_extract_comments_thread and _extract_youtube_comments functions

    def parse_chapters_from_text_wrapper(self):
        comment_text = self.chapter_text.get("1.0", tk.END)
        self.chapters = self.parse_chapters_from_text(comment_text)
        self.log_message(f"Parsed {len(self.chapters)} chapters.")
        self.chapter_text.delete("1.0", tk.END)
        for time, title in self.chapters:
            self.chapter_text.insert(tk.END, f"{time} {title}\n")

    def _generate_ffmpeg_chapters_metadata(self, chapters):
        metadata_content = [
            ";FFMETADATA1",
            "[CHAPTER]",
            "TIMEBASE=1/1000"
        ]
        for start_time_str, title in chapters:
            h, m, s = map(int, start_time_str.split(':'))
            start_ms = (h * 3600 + m * 60 + s) * 1000
            metadata_content.extend([
                "[CHAPTER]",
                f"START={start_ms}",
                f"END={start_ms + 1000}",
                f"title={title}"
            ])
        return "\n".join(metadata_content)

    def start_burn_chapters_thread(self):
        if self.ffmpeg_path is None:
            messagebox.showerror("Error", "FFmpeg executable not found. Please place it in the script folder or ensure it's on your system's PATH. Check the log for details.")
            return

        video_file = self.video_path.get().strip()
        if not video_file or not os.path.exists(video_file):
            messagebox.showerror("Error", "Please select a valid video file.")
            return
        if not self.chapters:
            messagebox.showerror("Error", "No chapters parsed. Please enter or extract chapters first.")
            return
        
        if self.processing:
            self.log_message("Already processing a video. Please wait.")
            return

        self.processing = True
        self.log_message(f"Starting to burn chapters into (overwrite): {video_file}")
        threading.Thread(target=self._burn_chapters_into_video, args=(video_file,)).start()

    def _burn_chapters_into_video(self, video_file):
        try:
            metadata_file = "chapters_metadata.txt"
            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write(self._generate_ffmpeg_chapters_metadata(self.chapters))
            
            output_file = video_file
            temp_output_file = video_file + ".temp"

            command = [
                self.ffmpeg_path,
                '-i', video_file,
                '-i', metadata_file,
                '-map_metadata', '1',
                '-map', '0',
                '-c', 'copy',
                '-movflags', 'use_metadata_tags',
                '-f', os.path.splitext(video_file)[1][1:],
                temp_output_file
            ]
            
            self.log_message(f"FFmpeg command: {' '.join(command)}")

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in iter(process.stderr.readline, ''):
                self.log_message(f"FFmpeg: {line.strip()}")
                self.root.update_idletasks()

            process.wait()

            if process.returncode == 0:
                os.replace(temp_output_file, output_file)
                self.log_message(f"Chapters burned successfully into: {output_file}")
            else:
                self.log_message(f"Burning chapters failed with exit code {process.returncode}")
                stdout_output, stderr_output = process.communicate()
                self.log_message(f"FFmpeg stdout: {stdout_output.strip()}")
                self.log_message(f"FFmpeg stderr: {stderr_output.strip()}")

        except Exception as e:
            self.log_message(f"An error occurred during burning chapters: {e}")
        finally:
            self.processing = False
            self.progress_bar.stop()
            if os.path.exists(metadata_file):
                os.remove(metadata_file)


    def start_create_new_chapter_video_thread(self):
        if self.ffmpeg_path is None:
            messagebox.showerror("Error", "FFmpeg executable not found. Please place it in the script folder or ensure it's on your system's PATH. Check the log for details.")
            return

        video_file = self.video_path.get().strip()
        if not video_file or not os.path.exists(video_file):
            messagebox.showerror("Error", "Please select a valid video file.")
            return
        if not self.chapters:
            messagebox.showerror("Error", "No chapters parsed. Please enter or extract chapters first.")
            return
        
        if self.processing:
            self.log_message("Already processing a video. Please wait.")
            return

        self.processing = True
        self.log_message(f"Starting to create new video with chapters from: {video_file}")
        threading.Thread(target=self._create_new_chapter_video, args=(video_file,)).start()

    def _create_new_chapter_video(self, video_file):
        try:
            base, ext = os.path.splitext(video_file)
            output_file = f"{base}_chapters{ext}"
            metadata_file = "chapters_metadata.txt"

            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write(self._generate_ffmpeg_chapters_metadata(self.chapters))

            command = [
                self.ffmpeg_path,
                '-i', video_file,
                '-i', metadata_file,
                '-map_metadata', '1',
                '-map', '0',
                '-c', 'copy',
                '-movflags', 'use_metadata_tags',
                '-f', ext[1:],
                output_file
            ]
            
            self.log_message(f"FFmpeg command: {' '.join(command)}")

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in iter(process.stderr.readline, ''):
                self.log_message(f"FFmpeg: {line.strip()}")
                self.root.update_idletasks()

            process.wait()

            if process.returncode == 0:
                self.log_message(f"New video with chapters created successfully: {output_file}")
            else:
                self.log_message(f"Creating new video with chapters failed with exit code {process.returncode}")
                stdout_output, stderr_output = process.communicate()
                self.log_message(f"FFmpeg stdout: {stdout_output.strip()}")
                self.log_message(f"FFmpeg stderr: {stderr_output.strip()}")

        except Exception as e:
            self.log_message(f"An error occurred during creating new chapter video: {e}")
        finally:
            self.processing = False
            self.progress_bar.stop()
            if os.path.exists(metadata_file):
                os.remove(metadata_file)

    def clear_all(self):
        self.log_message("Clearing all inputs and log...")
        self.video_path.set("")
        self.youtube_url.set("")
        self.batch_folder.set("")
        self.chapter_text.delete("1.0", tk.END)
        self.chapters = []
        self.clear_log()
        self.progress_bar.stop()
        self.processing = False
        self.downloading = False
        self.batch_processing = False
        self.batch_results = []
        self.log_message("All cleared.")

    def browse_batch_folder(self):
        folder_path = filedialog.askdirectory(title="Select Batch Folder")
        if folder_path:
            self.batch_folder.set(folder_path)
            self.log_message(f"Selected batch folder: {folder_path}")

    def start_batch_processing_thread(self):
        batch_folder = self.batch_folder.get().strip()
        if not batch_folder or not os.path.isdir(batch_folder):
            messagebox.showerror("Error", "Please select a valid batch folder.")
            return
        
        if self.batch_processing:
            self.log_message("Batch processing is already running. Please wait.")
            return

        # Note: Batch processing relies on FFmpeg being present for chapter application.
        # So, we should check FFmpeg here. yt-dlp is not strictly required for batch,
        # unless your batch process involves downloading YouTube videos.
        if self.ffmpeg_path is None:
            messagebox.showerror("Error", "FFmpeg executable not found. FFmpeg is required for batch video processing (applying chapters). Please place it in the script folder or ensure it's on your system's PATH. Check the log for details.")
            return


        self.batch_processing = True
        self.batch_results = []
        self.log_message(f"Starting batch processing in folder: {batch_folder}")
        threading.Thread(target=self._run_batch_processing, args=(batch_folder,)).start()

    def _run_batch_processing(self, folder_path):
        video_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))]
        
        if not video_files:
            self.log_message("No video files found in the selected batch folder.")
            self.batch_processing = False
            self.progress_bar.stop()
            return

        self.log_message(f"Found {len(video_files)} video files in batch folder.")
        
        for i, video_file_name in enumerate(video_files):
            full_video_path = os.path.join(folder_path, video_file_name)
            self.log_message(f"\nProcessing batch video {i+1}/{len(video_files)}: {full_video_path}")
            
            chapter_txt_path = os.path.splitext(full_video_path)[0] + ".txt"
            batch_chapters = []
            if os.path.exists(chapter_txt_path):
                self.log_message(f"Found companion chapter text file: {chapter_txt_path}")
                try:
                    with open(chapter_txt_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                    batch_chapters = self.parse_chapters_from_text(text_content)
                    if batch_chapters:
                        self.log_message(f"Parsed {len(batch_chapters)} chapters from {chapter_txt_path}")
                    else:
                        self.log_message(f"No chapters parsed from {chapter_txt_path}. Skipping.")
                except Exception as e:
                    self.log_message(f"Error reading/parsing {chapter_txt_path}: {e}")
            else:
                self.log_message(f"No companion chapter text file found for {video_file_name}. Skipping chapters for this video.")

            if batch_chapters:
                original_chapters = list(self.chapters) 
                self.chapters = batch_chapters
                self.log_message(f"Applying chapters to {video_file_name} (creating new file)...")
                try:
                    self._create_new_chapter_video(full_video_path)
                    self.batch_results.append((video_file_name, "Success"))
                except Exception as e:
                    self.log_message(f"Failed to process {video_file_name}: {e}")
                    self.batch_results.append((video_file_name, f"Failed: {e}"))
                finally:
                    self.chapters = original_chapters
            else:
                self.batch_results.append((video_file_name, "Skipped (no chapters found)"))
            
            self.root.after(0, lambda: self.progress_bar.set((i + 1) / len(video_files) * 100))


        self.log_message("\nBatch processing complete.")
        for item, status in self.batch_results:
            self.log_message(f"- {item}: {status}")
        self.batch_processing = False
        self.progress_bar.stop()


    def log_message(self, message):
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    def clear_log(self):
        self.status_text.config(state='normal')
        self.status_text.delete("1.0", tk.END)
        self.status_text.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoChapterTool(root)
    root.mainloop()