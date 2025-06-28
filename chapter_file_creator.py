import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import re # For sanitizing filenames
import subprocess
import sys
import time
import json

# Try to import moviepy for video duration
try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# Check for FFprobe availability
def check_ffprobe():
    try:
        # Use subprocess.DEVNULL for stdout/stderr to keep console clean
        subprocess.run(['ffprobe', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return True
    except:
        return False

FFPROBE_AVAILABLE = check_ffprobe()

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
        
        # Add network troubleshooting button
        ttk.Button(folder_frame, text="Test Network Path", command=self.test_network_path).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Button(folder_frame, text="Start Chapter Creation Batch", command=self.start_chapter_creation_batch).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Current Video Info Frame
        video_info_frame = ttk.LabelFrame(self.root, text="Current Video")
        video_info_frame.pack(padx=10, pady=5, fill="x", expand=True)
        video_info_frame.grid_columnconfigure(0, weight=1)
        video_info_frame.grid_columnconfigure(1, weight=0)
        video_info_frame.grid_columnconfigure(2, weight=0)

        self.current_video_label = ttk.Label(video_info_frame, text="No video loaded.", font=("Arial", 12, "bold"))
        self.current_video_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.video_duration_label = ttk.Label(video_info_frame, text="", font=("Arial", 10), foreground="blue")
        self.video_duration_label.grid(row=1, column=0, padx=5, pady=(0,5), sticky="w")
        
        self.copy_filename_button = ttk.Button(video_info_frame, text="Copy Filename", command=self.copy_filename_to_clipboard)
        self.copy_filename_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        self.get_duration_button = ttk.Button(video_info_frame, text="Get Duration", command=self.get_video_duration)
        self.get_duration_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")

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
        action_buttons_frame.grid_columnconfigure(3, weight=1)

        self.save_next_button = ttk.Button(action_buttons_frame, text="Save Chapters & Next Video", command=self.save_chapters_and_next)
        self.save_next_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.skip_button = ttk.Button(action_buttons_frame, text="Skip Video", command=self.skip_video)
        self.skip_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.format_button = ttk.Button(action_buttons_frame, text="Format Chapters", command=self.format_current_chapters)
        self.format_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.finish_button = ttk.Button(action_buttons_frame, text="Finish Batch", command=self.finish_batch)
        self.finish_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Status/Log Frame
        status_frame = ttk.LabelFrame(self.root, text="Status / Log")
        status_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.status_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, width=80, height=8, state='disabled')
        self.status_text.pack(padx=5, pady=5, fill="both", expand=True)

        # Initial state of buttons
        self._set_ui_state(False) # Disable action buttons initially
        
        # Log available duration methods
        methods = []
        if FFPROBE_AVAILABLE:
            methods.append("FFprobe")
        if MOVIEPY_AVAILABLE:
            methods.append("MoviePy")
        
        if methods:
            self.log_message(f"Duration detection available via: {', '.join(methods)}")
        else:
            self.log_message("No duration detection methods available. Install FFmpeg or MoviePy.")

    def _set_ui_state(self, enable):
        """Enables/disables buttons based on batch processing state."""
        self.save_next_button.config(state='normal' if enable else 'disabled')
        self.skip_button.config(state='normal' if enable else 'disabled')
        self.format_button.config(state='normal' if enable else 'disabled')
        self.finish_button.config(state='normal' if enable else 'disabled')
        self.chapter_text_input.config(state='normal' if enable else 'disabled')
        self.copy_filename_button.config(state='normal' if enable else 'disabled')
        self.get_duration_button.config(state='normal' if enable else 'disabled')

    def get_video_duration(self):
        """Gets and displays the duration of the current video file using FFprobe or MoviePy."""
        if self.current_video_index < 0 or self.current_video_index >= len(self.video_files):
            messagebox.showwarning("No Video", "No video file is currently loaded.")
            return
        
        if not FFPROBE_AVAILABLE and not MOVIEPY_AVAILABLE:
            messagebox.showerror("Duration Detection Unavailable", 
                                "Neither FFprobe nor MoviePy is available for duration detection.\n\n"
                                "Install options:\n"
                                "1. FFmpeg (includes FFprobe): https://ffmpeg.org/download.html\n"
                                "2. MoviePy: pip install moviepy")
            return
        
        current_video_name = self.video_files[self.current_video_index]
        video_path = os.path.join(self.folder_path.get(), current_video_name)
        
        def get_duration_thread():
            try:
                self.root.after(0, lambda: self.log_message(f"Getting duration for: {current_video_name}"))
                self.root.after(0, lambda: self.video_duration_label.config(text="Getting duration..."))
                
                duration_seconds = None
                method_used = None
                
                # Try FFprobe first (more reliable and faster)
                if FFPROBE_AVAILABLE:
                    try:
                        cmd = [
                            'ffprobe', '-v', 'quiet', '-print_format', 'json',
                            '-show_format', video_path
                        ]
                        # Use shell=True for network paths on Windows sometimes helps, but can be security risk
                        # Sticking with shell=False for safety and general cross-platform compatibility
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60) # Increased timeout
                        
                        if result.returncode == 0:
                            data = json.loads(result.stdout)
                            duration_seconds = float(data['format']['duration'])
                            method_used = "FFprobe"
                        else:
                            # Log ffprobe's stderr for better debugging
                            raise Exception(f"FFprobe returned error code {result.returncode}. Stderr: {result.stderr}")
                            
                    except Exception as e:
                        self.root.after(0, lambda: self.log_message(f"FFprobe failed: {e}"))
                
                # Fallback to MoviePy if FFprobe failed
                if duration_seconds is None and MOVIEPY_AVAILABLE:
                    try:
                        from moviepy.editor import VideoFileClip
                        # MoviePy can sometimes struggle with network paths directly.
                        # It might need a mapped drive or very stable UNC path.
                        with VideoFileClip(video_path) as clip:
                            duration_seconds = clip.duration
                        method_used = "MoviePy"
                    except Exception as e:
                        self.root.after(0, lambda: self.log_message(f"MoviePy also failed: {e}"))
                
                if duration_seconds is None:
                    raise Exception("All duration detection methods failed")
                
                # Convert to hours:minutes:seconds
                hours = int(duration_seconds // 3600)
                minutes = int((duration_seconds % 3600) // 60)
                seconds = int(duration_seconds % 60)
                
                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                total_seconds_str = f"({int(duration_seconds)} total seconds)"
                
                # Update UI in main thread
                self.root.after(0, lambda: self.video_duration_label.config(
                    text=f"Duration: {duration_str} {total_seconds_str}"))
                self.root.after(0, lambda: self.log_message(
                    f"Duration: {duration_str} {total_seconds_str} (via {method_used})"))
                    
            except Exception as e:
                error_msg = f"Error getting video duration: {e}"
                self.root.after(0, lambda: self.video_duration_label.config(text="Duration: Error"))
                self.root.after(0, lambda: self.log_message(error_msg))
                
                # Show helpful error message
                if not FFPROBE_AVAILABLE and not MOVIEPY_AVAILABLE:
                    help_msg = ("Install FFmpeg or MoviePy for duration detection:\n"
                               "FFmpeg: https://ffmpeg.org/download.html\n"
                               "MoviePy: pip install moviepy")
                elif "ffprobe" in str(e).lower() and not MOVIEPY_AVAILABLE:
                    help_msg = "FFprobe failed. Consider installing MoviePy as backup: pip install moviepy"
                else:
                    help_msg = ("Check if the video file is valid and accessible.\n"
                                "If on network drive, ensure path is stable and authenticated.")
                
                self.root.after(0, lambda: self.log_message(f"Tip: {help_msg}"))
        
        # Run in background thread to avoid UI blocking
        threading.Thread(target=get_duration_thread, daemon=True).start()

    def format_current_chapters(self):
        """Formats the chapters currently in the text input."""
        current_content = self.chapter_text_input.get("1.0", tk.END).strip()
        formatted_content = self.format_chapters(current_content)
        
        # Replace content in text widget
        self.chapter_text_input.delete("1.0", tk.END)
        self.chapter_text_input.insert("1.0", formatted_content)
        
        self.log_message("Formatted chapters - removed empty lines and standardized timecode format")

    def format_seconds_to_timecode(self, seconds):
        """Converts seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def copy_filename_to_clipboard(self):
        """Copies the current video filename to the clipboard."""
        if self.current_video_index >= 0 and self.current_video_index < len(self.video_files):
            filename = self.video_files[self.current_video_index]
            # Remove file extension for cleaner copying
            base_name, _ = os.path.splitext(filename)
            self.root.clipboard_clear()
            self.root.clipboard_append(base_name)
            self.log_message(f"Copied filename to clipboard: {base_name}")
        else:
            messagebox.showwarning("No File", "No video file is currently loaded.")

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

    def test_network_path(self):
        """Tests network connectivity and provides diagnostics."""
        folder = self.folder_path.get().strip()
        if not folder:
            messagebox.showerror("Error", "Please enter or select a folder path first.")
            return
            
        self.log_message(f"Initiating network path test for: {folder}")
        
        folder = os.path.normpath(folder) # Normalize path
        
        if folder.startswith('\\\\') and sys.platform.startswith('win'): # Check for UNC path on Windows
            parts = folder.split('\\')
            if len(parts) >= 3: # Should be at least \\server\share
                server_name = parts[2]
                self.log_message(f"Detected UNC network path. Server: {server_name}")
                
                # Test ping to server
                try:
                    self.log_message(f"Attempting to ping server: {server_name}...")
                    # Using -n 1 for Windows ping, -c 1 for Linux/macOS
                    ping_cmd = ['ping', '-n', '1', server_name] if sys.platform.startswith('win') else ['ping', '-c', '1', server_name]
                    result = subprocess.run(ping_cmd, 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        self.log_message(f"✓ Server '{server_name}' is reachable.")
                    else:
                        self.log_message(f"✗ Server '{server_name}' is not directly reachable (ping failed).")
                        self.log_message(f"   Ping output: {result.stdout.strip()} {result.stderr.strip()}")
                        self.log_message("   Suggestion: Check network connection, VPN, or firewall settings on server.")
                except Exception as e:
                    self.log_message(f"Ping test to '{server_name}' failed unexpectedly: {e}")
                    
                # Test net use command (Windows specific)
                try:
                    self.log_message("Checking 'net use' for mapped drives/connections...")
                    result = subprocess.run(['net', 'use'], capture_output=True, text=True, timeout=10)
                    # Check if the share path (or part of it) is listed
                    if any(folder_part in result.stdout for folder_part in [folder, '\\\\'.join(parts[:3])]):
                        self.log_message("✓ Active network connection or mapped drive found for this path/server.")
                    else:
                        self.log_message("! No active 'net use' connection found for this path.")
                        self.log_message("   Suggestion: You might need to map the drive (e.g., 'net use Z: \\\\server\\share') or authenticate.")
                    self.log_message(f"   'net use' output (first 5 lines): \n{chr(10).join(result.stdout.splitlines()[:5])}")
                except Exception as e:
                    self.log_message(f"'net use' command failed: {e}")
        elif not sys.platform.startswith('win'):
             self.log_message("UNC path testing (\\\\server\\share) is primarily for Windows.")
             self.log_message("On Linux/macOS, ensure the share is mounted correctly (e.g., via SMB/CIFS mount).")


        # Test actual folder access (applies to all OS and path types)
        self.log_message(f"Attempting to access folder directly: {folder}")
        try:
            if os.path.isdir(folder):
                files = os.listdir(folder)
                self.log_message(f"✓ Folder is accessible. Contains {len(files)} items.")
            else:
                self.log_message("✗ Folder path does not exist or is not a directory.")
        except Exception as e:
            self.log_message(f"✗ Folder access failed: {e}")
            self.log_message("   Suggestions for network paths:")
            self.log_message("   1. **Manual Authentication**: Try accessing the path directly in Windows File Explorer (e.g., paste \\\\alp-mac\\Storage into the address bar). This often triggers a credential prompt.")
            self.log_message("   2. **Map Network Drive**: Map \\\\alp-mac\\Storage to a drive letter (e.g., Z:) and then select Z: in this application.")
            self.log_message("   3. **Check Credentials**: Open Windows Credential Manager and ensure stored credentials for 'alp-mac' are correct.")
            self.log_message("   4. **Mac Sharing Settings**: Verify that SMB/File Sharing is enabled on your Mac, and the folder is shared with appropriate permissions.")
            self.log_message("   5. **Firewall**: Temporarily disable firewalls on both machines to test connectivity.")


    def try_access_with_retry(self, folder, max_retries=3):
        """Attempts to access folder with retries and different methods."""
        folder = os.path.normpath(folder) # Normalize path once

        for attempt in range(max_retries):
            self.log_message(f"Access attempt {attempt + 1}/{max_retries} for: {folder}")
            try:
                # On Windows, for UNC paths, sometimes opening in explorer helps trigger auth
                if sys.platform.startswith('win') and folder.startswith('\\\\') and attempt == 0:
                    try:
                        self.log_message("   Attempting to open path in Explorer to trigger potential authentication...")
                        # Use subprocess.Popen to avoid waiting for explorer to close
                        subprocess.Popen(f'explorer "{folder}"', shell=True)
                        time.sleep(1) # Give Explorer a moment to start/authenticate
                    except Exception as e:
                        self.log_message(f"   Could not open Explorer (may not be necessary): {e}")

                # Check if directory exists and is accessible
                if os.path.isdir(folder):
                    files = os.listdir(folder)
                    self.log_message(f"✓ Successfully accessed folder on attempt {attempt + 1}.")
                    return files
                else:
                    raise OSError(f"Path is not a directory or does not exist: {folder}")
                    
            except OSError as e:
                self.log_message(f"✗ Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(2)  # Longer pause between attempts for network
                else:
                    # Final attempt failed
                    raise e
            except Exception as e: # Catch other potential errors
                self.log_message(f"✗ Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise e


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
        if not folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        if self.processing_batch:
            self.log_message("Batch processing is already active.")
            return

        self.clear_log()
        self.log_message(f"Starting batch chapter file creation in: {folder}")
        
        try:
            # Use retry mechanism for network paths
            files = self.try_access_with_retry(folder)
            
            # Find video files (common extensions)
            self.video_files = sorted([
                f for f in files
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.ts')) # Added .ts
            ])

        except Exception as e: # Catch all exceptions during folder access for detailed logging
            error_msg = str(e)
            self.log_message(f"CRITICAL: Error accessing the folder: {error_msg}")
            
            # Provide specific guidance based on common Windows network errors
            suggestion = (
                "Troubleshooting Steps for Network Access Errors:\n\n"
                "1. **Manual Authentication**: Try accessing the path directly in Windows File Explorer (e.g., paste \\\\alp-mac\\Storage into the address bar). This often triggers a credential prompt that can cache credentials for Python.\n\n"
                "2. **Map Network Drive**: Map the network share to a local drive letter (e.g., Z:) and then select the mapped drive in this application. This is often the most reliable method for Windows.\n"
                "   - To map a drive: Open 'This PC' (or 'My Computer'), click 'Map network drive', choose a letter, and enter '\\\\alp-mac\\Storage'.\n"
                "   - Or via Command Prompt (Admin): `net use Z: \"\\\\alp-mac\\Storage\" /persistent:yes` (enter your Mac username/password when prompted).\n\n"
                "3. **Windows Credential Manager**: Ensure correct credentials for 'alp-mac' are saved. Search for 'Credential Manager' in Windows, go to 'Windows Credentials', and add a new generic credential if needed (Internet or network address: `alp-mac`).\n\n"
                "4. **Mac Sharing Settings**: Double-check that SMB/File Sharing is enabled on your Mac (System Settings -> General -> Sharing -> File Sharing -> Options -> Share files and folders using SMB). Ensure the specific folder is shared and the user you're authenticating with has read/write permissions.\n\n"
                "5. **Firewall**: Temporarily disable firewalls on both your Windows machine and your Mac to rule out network blocking.\n\n"
                "6. **VPN**: If you're on a VPN, ensure it's connected and configured to allow local network access."
            )
            
            # Refine error message based on common specific error types
            if "Invalid Signature" in error_msg or "-2146893818" in error_msg or "Access is denied" in error_msg:
                 detailed_error_type = "Network Authentication/Permission Issue"
            elif "not a directory" in error_msg or "The network path was not found" in error_msg:
                 detailed_error_type = "Path Not Found / Share Unavailable"
            else:
                detailed_error_type = "General Folder Access Issue"

            messagebox.showerror(f"Folder Access Error ({detailed_error_type})", suggestion)
            return

        if not self.video_files:
            self.log_message("No video files found in the selected folder. Please check the folder content and selected path.")
            self.processing_batch = False
            self._set_ui_state(False)
            return

        self.log_message(f"Found {len(self.video_files)} video files.")
        self.current_video_index = -1 # Reset index
        self.processing_batch = True
        self._set_ui_state(True) # Enable action buttons
        self.process_next_video()

    def has_intro_chapter(self, content):
        """Checks if the content already has a chapter at 00:00:00."""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('00:00:00') or line.startswith('00:00:00:00'):
                return True
        return False

    def format_chapters(self, content):
        """Formats chapter content to HH:MM:SS:FF and detects left/right timecode.
           Ensures 00:00:00:00 Intro is always present first."""
        
        lines = content.strip().split('\n')
        formatted_lines = []

        timecode_regex = re.compile(r'(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?::(\d{1,2}))?') # Added optional frames
        
        found_intro_chapter = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            matches = list(timecode_regex.finditer(line))
            if not matches:
                # If a line doesn't match timecode pattern, treat it as just text
                # We can't format it, so we'll skip it or add it as a comment later if needed
                self.log_message(f"Warning: Line '{line}' does not appear to be a chapter entry (no valid timecode found). Skipping.")
                continue

            match = matches[0]
            
            # Extract components, default to 0 if not present
            hour = int(match.group(1)) if match.group(1) else 0
            minute = int(match.group(2))
            second = int(match.group(3))
            frame = int(match.group(4)) if match.group(4) else 0 # Use 0 if no frame part

            timecode = f"{hour:02d}:{minute:02d}:{second:02d}:{frame:02d}"

            start, end = match.span()
            before = line[:start].strip()
            after = line[end:].strip()

            # Determine the chapter title
            title = ""
            if after:
                title = after
            elif before: # If 'after' is empty, try 'before'
                title = before
            
            if not title: # Fallback if no text found
                title = f"Chapter {len(formatted_lines) + 1}"

            formatted_entry = f"{timecode} {title}"
            formatted_lines.append(formatted_entry)
            
            if timecode.startswith("00:00:00"): # Check if it's an intro chapter
                found_intro_chapter = True

        # Ensure "00:00:00:00 Intro" is the very first chapter
        if not found_intro_chapter:
            # If no 00:00:00 chapter found at all, add it
            if not any(item.startswith("00:00:00:00 Intro") for item in formatted_lines):
                formatted_lines.insert(0, "00:00:00:00 Intro")
        else:
            # If an intro chapter was found, ensure it's at the very beginning and consistent
            # Filter out existing 00:00:00 chapters to re-insert a standardized one
            filtered_lines = [line for line in formatted_lines if not line.startswith("00:00:00")]
            formatted_lines = ["00:00:00:00 Intro"] + filtered_lines
            
        # Remove duplicates while preserving order
        seen = set()
        deduplicated_lines = []
        for line in formatted_lines:
            if line not in seen:
                deduplicated_lines.append(line)
                seen.add(line)

        return "\n".join(deduplicated_lines)

    def process_next_video(self):
        """Moves to the next video in the batch."""
        self.current_video_index += 1
        
        if self.current_video_index >= len(self.video_files):
            # Batch complete
            self.log_message("Batch processing complete!")
            self.processing_batch = False
            self._set_ui_state(False)
            self.current_video_label.config(text="Batch complete.")
            self.video_duration_label.config(text="")
            messagebox.showinfo("Batch Complete", "All videos in the folder have been processed!")
            return
        
        current_video = self.video_files[self.current_video_index]
        self.current_video_label.config(text=f"Video {self.current_video_index + 1}/{len(self.video_files)}: {current_video}")
        self.video_duration_label.config(text="")
        
        # Clear previous chapter content
        self.chapter_text_input.delete("1.0", tk.END)
        
        # Check if chapter file already exists
        video_name_without_ext = os.path.splitext(current_video)[0]
        chapter_file_path = os.path.join(self.folder_path.get(), f"{video_name_without_ext}.txt")
        
        if os.path.exists(chapter_file_path):
            try:
                with open(chapter_file_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                self.chapter_text_input.insert("1.0", existing_content)
                self.log_message(f"Loaded existing chapter file for: {current_video}")
            except Exception as e:
                self.log_message(f"Error loading existing chapter file: {e}")
                self.chapter_text_input.insert("1.0", "00:00:00:00 Intro") # Default if loading fails
        else:
            # No existing file, start with default intro
            self.chapter_text_input.insert("1.0", "00:00:00:00 Intro")
        
        self.log_message(f"Processing: {current_video}")
        self.get_video_duration() # Automatically attempt to get duration for each video

    def save_chapters_and_next(self):
        """Saves the current chapters and moves to the next video."""
        if self.current_video_index < 0 or not self.processing_batch:
            messagebox.showwarning("No Video", "No video is currently loaded or batch is not active.")
            return
        
        self.save_current_chapters()
        self.process_next_video()

    def skip_video(self):
        """Skips the current video without saving chapters."""
        if self.current_video_index < 0 or not self.processing_batch:
            messagebox.showwarning("No Video", "No video is currently loaded or batch is not active.")
            return
        
        current_video = self.video_files[self.current_video_index]
        self.log_message(f"Skipped: {current_video}")
        self.process_next_video()

    def save_current_chapters(self):
        """Saves the chapters for the current video."""
        if self.current_video_index < 0:
            return
        
        current_video = self.video_files[self.current_video_index]
        video_name_without_ext = os.path.splitext(current_video)[0]
        
        # Get chapter content and format it
        chapter_content = self.chapter_text_input.get("1.0", tk.END).strip()
        
        # Only format if there's actual content beyond just empty lines
        if chapter_content:
            formatted_content = self.format_chapters(chapter_content)
        else:
            formatted_content = "00:00:00:00 Intro" # Default if text box is completely empty
        
        # Save to file
        chapter_file_path = os.path.join(self.folder_path.get(), f"{video_name_without_ext}.txt")
        
        try:
            with open(chapter_file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            self.log_message(f"Saved chapters for: {current_video} to {os.path.basename(chapter_file_path)}")
        except Exception as e:
            self.log_message(f"Error saving chapters for {current_video}: {e}")
            messagebox.showerror("Save Error", f"Could not save chapters for {current_video}:\n{e}")

    def finish_batch(self):
        """Finishes the current batch processing."""
        if self.processing_batch:
            # Save current video if needed
            response = messagebox.askyesnocancel(
                "Finish Batch", 
                "Do you want to save chapters for the current video before finishing?\n\n"
                "Yes: Save current and finish.\n"
                "No: Discard current changes and finish.\n"
                "Cancel: Continue batch processing."
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.save_current_chapters()
        
        self.log_message("Batch processing finished by user.")
        self.processing_batch = False
        self._set_ui_state(False)
        self.current_video_label.config(text="Batch finished.")
        self.video_duration_label.config(text="")
        self.chapter_text_input.delete("1.0", tk.END)

def main():
    root = tk.Tk()
    app = ChapterCreatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()