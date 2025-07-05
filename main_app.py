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

        # Frame for buttons below the text area
        chapter_buttons_frame = ttk.Frame(chapter_frame)
        chapter_buttons_frame.pack(pady=5, fill='x', padx=5)

        # Make the columns in the frame expand equally
        chapter_buttons_frame.grid_columnconfigure(0, weight=1)
        chapter_buttons_frame.grid_columnconfigure(1, weight=1)

        parse_button = ttk.Button(chapter_buttons_frame, text="Parse Chapters from Text", command=self.parse_chapters_from_text_wrapper)
        parse_button.grid(row=0, column=0, padx=(0, 2), sticky='ew')

        launch_creator_button = ttk.Button(chapter_buttons_frame, text="Launch Batch Chapter File Creator", command=self.launch_chapter_creator)
        launch_creator_button.grid(row=0, column=1, padx=(2, 0), sticky='ew')

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
        Finds the full path to an executable, prioritizing PyInstaller's temp path,
        then the script's directory, then system PATH.
        """
        # 1. Check PyInstaller's temporary extraction path (when bundled)
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            temp_path = os.path.join(sys._MEIPASS, base_name)
            temp_path_exe = os.path.join(sys._MEIPASS, base_name + ".exe") # For Windows
            if sys.platform == "win32" and os.path.exists(temp_path_exe):
                return temp_path_exe
            elif os.path.exists(temp_path):
                return temp_path

        # 2. Check the script's original directory (for non-bundled runs or if user places it there)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(script_dir, base_name)
        local_path_exe = os.path.join(script_dir, base_name + ".exe")

        if sys.platform == "win32" and os.path.exists(local_path_exe) and os.path.isfile(local_path_exe):
            return local_path_exe
        elif os.path.exists(local_path) and os.path.isfile(local_path):
            return local_path
        
        # 3. Fallback to system PATH using shutil.which
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

        # Changed regex to explicitly capture H:M:S for better parsing
        # It handles optional hours.
        pattern1 = re.compile(r'^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*[-:]?\s*(.+?)$')  # HH:MM:SS or MM:SS followed by title
        pattern2 = re.compile(r'^(.+?)\s*[-:]?\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})$')  # Title followed by HH:MM:SS or MM:SS

        for line in lines:
            match = pattern1.match(line)
            if match:
                # If group 1 (hours) exists, use it, otherwise 0
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = int(match.group(2))
                seconds = int(match.group(3))
                title = match.group(4).strip()
                
                # Convert to HH:MM:SS format consistently for storage
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                chapters.append((time_str, title))
                continue

            match = pattern2.match(line)
            if match:
                title = match.group(1).strip()
                hours = int(match.group(2)) if match.group(2) else 0
                minutes = int(match.group(3))
                seconds = int(match.group(4))
                
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                chapters.append((time_str, title))
                continue
            
            self.log_message(f"Warning: Could not parse chapter from line: '{line}'")


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

    def parse_chapters_from_text_wrapper(self):
        comment_text = self.chapter_text.get("1.0", tk.END)
        self.chapters = self.parse_chapters_from_text(comment_text)
        self.log_message(f"Parsed {len(self.chapters)} chapters.")
        self.chapter_text.delete("1.0", tk.END)
        for time_str, title in self.chapters: # Using time_str for consistency with parsing logic
            self.chapter_text.insert(tk.END, f"{time_str} {title}\n")

    def _generate_ffmpeg_chapters_metadata(self, chapters):
        metadata_content = [
            ";FFMETADATA1",
            "; This section can be used for global metadata, like video title."
            # "title=My Video Title"
        ]

        # Process chapters to include START and calculated END times
        processed_chapters = []
        for i, (start_time_str, title) in enumerate(chapters):
            h, m, s = map(int, start_time_str.split(':'))
            start_ms = (h * 3600 + m * 60 + s) * 1000
            
            processed_chapters.append({
                'start_ms': start_ms,
                'title': title,
            })
            
        # Calculate END times based on the next chapter's start time
        for i in range(len(processed_chapters)):
            # If not the last chapter, end_ms is the start_ms of the next chapter
            if i < len(processed_chapters) - 1:
                processed_chapters[i]['end_ms'] = processed_chapters[i+1]['start_ms']
            else:
                # For the last chapter, set a reasonable default end time
                # A common practice is start_ms + 1000 (1 second), or total video duration
                # For now, let's use a small duration to just mark the point.
                processed_chapters[i]['end_ms'] = processed_chapters[i]['start_ms'] + 1000 # 1 second after start
        
        for chapter_data in processed_chapters:
            metadata_content.extend([
                "[CHAPTER]",
                "TIMEBASE=1/1000", # Define TIMEBASE explicitly for each chapter block
                f"START={chapter_data['start_ms']}",
                f"END={chapter_data['end_ms']}",
                f"title={chapter_data['title']}"
            ])
        return "\n".join(metadata_content)
    
    def _clean_existing_chapter_files(self, video_path):
        """
        Deletes existing companion .txt chapter files for a given video name.
        Looks for:
        - {video_name_without_ext}.txt
        - {video_name_without_ext}_chapters.txt (if a new file was created previously)
        """
        video_dir, video_filename = os.path.split(video_path)
        base_name, _ = os.path.splitext(video_filename)

        potential_chapter_files = [
            os.path.join(video_dir, f"{base_name}.txt"),
            os.path.join(video_dir, f"{base_name}_chapters.txt")
        ]

        cleaned_count = 0
        for chapter_file in potential_chapter_files:
            if os.path.exists(chapter_file):
                try:
                    os.remove(chapter_file)
                    self.log_message(f"Cleaned old companion chapter text file: {os.path.basename(chapter_file)}")
                    cleaned_count += 1
                except Exception as e:
                    self.log_message(f"Warning: Could not delete old companion chapter file {os.path.basename(chapter_file)}: {e}")
        return cleaned_count

    def _strip_all_metadata_from_video(self, input_video_path, output_video_path):
        """
        Strips all metadata (including chapters) from a video file and saves it to a new path.
        Returns True on success, False on failure.
        """
        self.log_message(f"Stripping all metadata from: {os.path.basename(input_video_path)}...")
        
        command = [
            self.ffmpeg_path,
            '-i', input_video_path,
            '-map_chapters', '-1', # Tells ffmpeg to not map any chapters from input
            '-map_metadata', '-1', # Tells ffmpeg to not map any metadata from input
            '-c', 'copy',
            output_video_path
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # It's generally good practice to read stdout/stderr even if not logging every line
        stdout_output, stderr_output = process.communicate()
        
        if process.returncode == 0:
            self.log_message(f"Metadata stripped successfully. Output to: {os.path.basename(output_video_path)}")
            return True
        else:
            self.log_message(f"Failed to strip metadata from {os.path.basename(input_video_path)} with exit code {process.returncode}")
            self.log_message(f"FFmpeg stdout (strip): {stdout_output.strip()}")
            self.log_message(f"FFmpeg stderr (strip): {stderr_output.strip()}")
            return False

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
        
        # Determine temporary files for stripping metadata
        base, ext = os.path.splitext(video_file)
        temp_stripped_video = f"{base}_stripped{ext}" # Video with all metadata stripped
        final_temp_output = f"{base}.temp{ext}"       # Final temporary output with new chapters

        try:
            # Step 1: Strip all existing metadata from the input video
            # (This will create temp_stripped_video)
            if not self._strip_all_metadata_from_video(video_file, temp_stripped_video):
                self.log_message("Aborting chapter burning due to metadata stripping failure.")
                return

            # Step 2: Create the temporary FFmpeg metadata file
            metadata_file = "chapters_metadata.txt"
            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write(self._generate_ffmpeg_chapters_metadata(self.chapters))
            
            # Step 3: Burn new chapters into the stripped video
            command = [
                self.ffmpeg_path,
                '-i', temp_stripped_video, # Use the stripped video as input
                '-i', metadata_file,
                '-map_metadata', '1', # Map metadata from the .txt file
                '-map', '0',          # Map all streams from the first input (the stripped video)
                '-c', 'copy',         # Copy streams without re-encoding
                '-movflags', 'use_metadata_tags', # Ensures metadata is properly written to mov/mp4
                final_temp_output     # Output to the final temporary file
            ]
            
            self.log_message(f"FFmpeg command (burn chapters): {' '.join(command)}")

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # It's generally good practice to read stdout/stderr even if not logging every line
            stdout_output, stderr_output = process.communicate() # Changed to communicate to get all output at once
            
            if process.returncode == 0:
                os.replace(final_temp_output, video_file) # Overwrite original with the new final temp
                self.log_message(f"Chapters burned successfully into: {video_file}")
            else:
                self.log_message(f"Burning chapters failed with exit code {process.returncode}")
                self.log_message(f"FFmpeg stdout (burn): {stdout_output.strip()}")
                self.log_message(f"FFmpeg stderr (burn): {stderr_output.strip()}")

        except Exception as e:
            self.log_message(f"An error occurred during burning chapters: {e}")
        finally:
            self.processing = False
            self.progress_bar.stop()
            # Clean up all temporary files created in this process
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            if os.path.exists(temp_stripped_video):
                os.remove(temp_stripped_video)
            if os.path.exists(final_temp_output): # Clean this up only if it still exists (e.g., if os.replace failed)
                os.remove(final_temp_output)


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
        
        # Determine temporary file for stripping metadata and final output name
        base, ext = os.path.splitext(video_file)
        temp_stripped_video = f"{base}_stripped{ext}" # Video with all metadata stripped
        output_file = f"{base}_chapters{ext}"       # Final new output file with new chapters

        try:
            # Step 1: Strip all existing metadata from the input video
            # (This will create temp_stripped_video)
            if not self._strip_all_metadata_from_video(video_file, temp_stripped_video):
                self.log_message("Aborting new chapter video creation due to metadata stripping failure.")
                return

            # Step 2: Create the temporary FFmpeg metadata file
            metadata_file = "chapters_metadata.txt"
            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write(self._generate_ffmpeg_chapters_metadata(self.chapters))

            # Step 3: Burn new chapters into the stripped video to the final output file
            command = [
                self.ffmpeg_path,
                '-i', temp_stripped_video, # Use the stripped video as input
                '-i', metadata_file,
                '-map_metadata', '1', # Map metadata from the .txt file
                '-map', '0',          # Map all streams from the first input (the stripped video)
                '-c', 'copy',         # Copy streams without re-encoding
                '-movflags', 'use_metadata_tags', # Ensures metadata is properly written to mov/mp4
                output_file           # Direct output to the new suffixed file
            ]
            
            self.log_message(f"FFmpeg command (create new with chapters): {' '.join(command)}")

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # It's generally good practice to read stdout/stderr even if not logging every line
            stdout_output, stderr_output = process.communicate() # Changed to communicate to get all output at once

            if process.returncode == 0:
                self.log_message(f"New video with chapters created successfully: {output_file}")
            else:
                self.log_message(f"Creating new video with chapters failed with exit code {process.returncode}")
                self.log_message(f"FFmpeg stdout (create): {stdout_output.strip()}")
                self.log_message(f"FFmpeg stderr (create): {stderr_output.strip()}")

        except Exception as e:
            self.log_message(f"An error occurred during creating new chapter video: {e}")
        finally:
            self.processing = False
            self.progress_bar.stop()
            # Clean up temporary metadata file and stripped video
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            if os.path.exists(temp_stripped_video):
                os.remove(temp_stripped_video)


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
                
                # In batch mode, we always create a new file with chapters
                # So we strip metadata from the original video, then add chapters to a NEW output file.
                base_name_for_new_file, ext_for_new_file = os.path.splitext(full_video_path)
                batch_stripped_video = f"{base_name_for_new_file}_stripped_batch{ext_for_new_file}"
                final_output_file_batch = f"{base_name_for_new_file}_chapters{ext_for_new_file}"

                self.log_message(f"Applying chapters to {video_file_name} (creating new file '{os.path.basename(final_output_file_batch)}')")
                try:
                    # Step 1: Strip metadata from the *original* video to a temporary stripped copy
                    if not self._strip_all_metadata_from_video(full_video_path, batch_stripped_video):
                        self.log_message(f"Aborting processing for {video_file_name} due to metadata stripping failure.")
                        self.batch_results.append((video_file_name, "Failed (metadata strip)"))
                        continue # Move to next video in batch

                    # Step 2: Create the temporary FFmpeg metadata file (for this video in batch)
                    batch_metadata_file = f"chapters_metadata_batch_{i}.txt" # Unique name for batch files
                    with open(batch_metadata_file, "w", encoding="utf-8") as f:
                        f.write(self._generate_ffmpeg_chapters_metadata(self.chapters))

                    # Step 3: Burn new chapters into the stripped video to the final output file
                    command = [
                        self.ffmpeg_path,
                        '-i', batch_stripped_video, # Use the stripped video as input
                        '-i', batch_metadata_file,
                        '-map_metadata', '1',
                        '-map', '0',
                        '-c', 'copy',
                        '-movflags', 'use_metadata_tags',
                        final_output_file_batch
                    ]
                    
                    self.log_message(f"FFmpeg command (batch new chapter video): {' '.join(command)}")

                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    # Reading stderr directly instead of iter() for simpler batch error handling
                    stdout_output, stderr_output = process.communicate() 

                    if process.returncode == 0:
                        self.log_message(f"Batch new video with chapters created successfully: {os.path.basename(final_output_file_batch)}")
                        self.batch_results.append((video_file_name, "Success"))
                    else:
                        self.log_message(f"Creating new batch video with chapters failed for {video_file_name} with exit code {process.returncode}")
                        self.log_message(f"FFmpeg stdout (batch new): {stdout_output.strip()}")
                        self.log_message(f"FFmpeg stderr (batch new): {stderr_output.strip()}")
                        self.batch_results.append((video_file_name, f"Failed: {stderr_output.strip()[:100]}...")) # Log a snippet
                        
                except Exception as e:
                    self.log_message(f"An unexpected error occurred during batch processing for {video_file_name}: {e}")
                    self.batch_results.append((video_file_name, f"Failed: {e}"))
                finally:
                    self.chapters = original_chapters
                    # Clean up temporary files for this specific video in batch
                    if os.path.exists(batch_metadata_file):
                        os.remove(batch_metadata_file)
                    if os.path.exists(batch_stripped_video):
                        os.remove(batch_stripped_video)
            else:
                self.batch_results.append((video_file_name, "Skipped (no chapters found)"))
            
            self.root.after(0, lambda: self.progress_bar.set((i + 1) / len(video_files) * 100))


        self.log_message("\nBatch processing complete.")
        for item, status in self.batch_results:
            self.log_message(f"- {item}: {status}")
        self.batch_processing = False
        self.progress_bar.stop()

    def launch_chapter_creator(self):
        """Launches the chapter_file_creator.py script in a new process."""
        script_name = "chapter_file_creator.py"
        
        # Determine if running as a PyInstaller bundled executable
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running from PyInstaller bundle
            bundled_script_path = os.path.join(sys._MEIPASS, script_name)
            
            self.log_message(f"Launching bundled {script_name} from {bundled_script_path}...")
            try:
                # Launch a new process using the *current* executable (the bundled .exe)
                # and pass the bundled script path as an argument.
                subprocess.Popen([sys.executable, bundled_script_path])
            except Exception as e:
                self.log_message(f"Failed to launch bundled {script_name}: {e}")
                messagebox.showerror("Error", f"An error occurred while trying to launch the bundled script: {e}")
        else:
            # Running as a standard Python script
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)

            if not os.path.exists(script_path):
                self.log_message(f"ERROR: Could not find {script_name}. Make sure it's in the same folder as this script.")
                messagebox.showerror("Error", f"Could not find {script_name}. Make sure it's in the same folder.")
                return

            try:
                self.log_message(f"Launching {script_name}...")
                subprocess.Popen([sys.executable, script_path])
            except Exception as e:
                self.log_message(f"Failed to launch {script_name}: {e}")
                messagebox.showerror("Error", f"An error occurred while trying to launch the script: {e}")

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