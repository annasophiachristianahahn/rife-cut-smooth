"""GUI interface using tkinter."""

import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import threading
import queue
from pathlib import Path

from .config import Config
from .pipeline import Pipeline


class ProgressWindow:
    """Progress window for processing."""

    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Processing...")
        self.window.geometry("800x600")
        self.window.transient(parent)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_label = tk.Label(self.window, text="Starting...")
        self.progress_label.pack(pady=10)

        self.progress_bar = ttk.Progressbar(
            self.window,
            mode='indeterminate',
            length=700,
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.start(10)

        # Log area
        log_frame = tk.Frame(self.window)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(log_frame, text="Processing Log:").pack(anchor=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=100,
            height=30,
            font=("Courier", 10),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Close button (initially disabled)
        self.close_button = tk.Button(
            self.window,
            text="Close",
            command=self.window.destroy,
            state=tk.DISABLED,
        )
        self.close_button.pack(pady=10)

    def update_status(self, text):
        """Update status label."""
        self.progress_label.config(text=text)

    def append_log(self, text):
        """Append text to log."""
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def set_complete(self, success=True):
        """Mark processing as complete."""
        self.progress_bar.stop()
        if success:
            self.progress_label.config(text="✓ Processing Complete!")
            self.progress_bar.config(mode='determinate')
            self.progress_var.set(100)
        else:
            self.progress_label.config(text="✗ Processing Failed")
        self.close_button.config(state=tk.NORMAL)


class RifeCutSmoothGUI:
    """Main GUI window."""

    def __init__(self, root):
        self.root = root
        self.root.title("RIFE Cut Smooth")
        self.root.geometry("700x650")

        self.input_path = None
        self.output_path = None

        self._create_widgets()

    def _create_widgets(self):
        """Create GUI widgets."""
        # Title
        title = tk.Label(
            self.root,
            text="RIFE Cut Smooth",
            font=("Helvetica", 24, "bold"),
        )
        title.pack(pady=20)

        subtitle = tk.Label(
            self.root,
            text="Smooth hard cuts in videos using optical flow interpolation",
            font=("Helvetica", 12),
        )
        subtitle.pack(pady=5)

        # File selection
        file_frame = tk.LabelFrame(self.root, text="Video File", padx=10, pady=10)
        file_frame.pack(fill=tk.X, padx=20, pady=10)

        self.file_label = tk.Label(file_frame, text="No file selected", fg="gray")
        self.file_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

        choose_button = tk.Button(
            file_frame,
            text="Choose Video...",
            command=self._choose_file,
        )
        choose_button.pack(side=tk.RIGHT)

        # Settings
        settings_frame = tk.LabelFrame(self.root, text="Settings", padx=10, pady=10)
        settings_frame.pack(fill=tk.X, padx=20, pady=10)

        # FPS
        fps_frame = tk.Frame(settings_frame)
        fps_frame.pack(fill=tk.X, pady=5)
        tk.Label(fps_frame, text="Target FPS:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.fps_var = tk.StringVar(value="30")
        tk.Entry(fps_frame, textvariable=self.fps_var, width=10).pack(side=tk.LEFT)
        tk.Label(fps_frame, text="(frames per second)", fg="gray").pack(side=tk.LEFT, padx=5)

        # Threshold
        threshold_frame = tk.Frame(settings_frame)
        threshold_frame.pack(fill=tk.X, pady=5)
        tk.Label(threshold_frame, text="Scene Threshold:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.threshold_var = tk.StringVar(value="0.30")
        tk.Entry(threshold_frame, textvariable=self.threshold_var, width=10).pack(side=tk.LEFT)
        tk.Label(threshold_frame, text="(0.0-1.0, lower=more cuts)", fg="gray").pack(side=tk.LEFT, padx=5)

        # Bridge duration
        bridge_frame = tk.Frame(settings_frame)
        bridge_frame.pack(fill=tk.X, pady=5)
        tk.Label(bridge_frame, text="Bridge Duration:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.bridge_var = tk.StringVar(value="0.5")
        tk.Entry(bridge_frame, textvariable=self.bridge_var, width=10).pack(side=tk.LEFT)
        tk.Label(bridge_frame, text="(seconds)", fg="gray").pack(side=tk.LEFT, padx=5)

        # CRF
        crf_frame = tk.Frame(settings_frame)
        crf_frame.pack(fill=tk.X, pady=5)
        tk.Label(crf_frame, text="Quality (CRF):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.crf_var = tk.StringVar(value="18")
        tk.Entry(crf_frame, textvariable=self.crf_var, width=10).pack(side=tk.LEFT)
        tk.Label(crf_frame, text="(0-51, lower=better)", fg="gray").pack(side=tk.LEFT, padx=5)

        # Preset
        preset_frame = tk.Frame(settings_frame)
        preset_frame.pack(fill=tk.X, pady=5)
        tk.Label(preset_frame, text="Encoding Preset:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value="medium")
        preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            width=15,
            state="readonly",
        )
        preset_combo.pack(side=tk.LEFT)
        tk.Label(preset_frame, text="(slower=smaller file)", fg="gray").pack(side=tk.LEFT, padx=5)

        # Audio mode
        audio_frame = tk.Frame(settings_frame)
        audio_frame.pack(fill=tk.X, pady=5)
        tk.Label(audio_frame, text="Audio Mode:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.audio_var = tk.StringVar(value="keep-original")
        audio_combo = ttk.Combobox(
            audio_frame,
            textvariable=self.audio_var,
            values=["keep-original", "stretch-audio", "no-audio"],
            width=15,
            state="readonly",
        )
        audio_combo.pack(side=tk.LEFT)

        # Info text
        info_frame = tk.LabelFrame(self.root, text="Info", padx=10, pady=10)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        info_text = (
            "This tool detects hard cuts in your video and replaces them with smooth\n"
            "RIFE-interpolated transitions. The output video maintains the same length\n"
            "as the input (length-preserving).\n\n"
            "• keep-original: Keeps original audio (may have tiny desync)\n"
            "• stretch-audio: Time-stretches audio to match (perfect sync)\n"
            "• no-audio: Output video without audio\n\n"
            "Processing may take several minutes depending on video length and cut count."
        )
        tk.Label(info_frame, text=info_text, justify=tk.LEFT, fg="#333").pack()

        # Run button
        self.run_button = tk.Button(
            self.root,
            text="▶ Run Processing",
            command=self._run_processing,
            font=("Helvetica", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10,
            state=tk.DISABLED,
        )
        self.run_button.pack(pady=20)

    def _choose_file(self):
        """Open file chooser dialog."""
        filepath = filedialog.askopenfilename(
            title="Choose Video File",
            filetypes=[
                ("Video Files", "*.mp4 *.mov *.avi *.mkv *.m4v"),
                ("All Files", "*.*"),
            ],
        )

        if filepath:
            self.input_path = filepath
            self.file_label.config(text=Path(filepath).name, fg="black")
            self.run_button.config(state=tk.NORMAL)

            # Generate output path
            input_stem = Path(filepath).stem
            input_dir = Path(filepath).parent
            self.output_path = str(input_dir / f"{input_stem}__rife_smooth.mp4")

    def _run_processing(self):
        """Run the processing pipeline."""
        if not self.input_path:
            return

        # Validate settings
        try:
            fps = float(self.fps_var.get())
            threshold = float(self.threshold_var.get())
            bridge = float(self.bridge_var.get())
            crf = int(self.crf_var.get())

            if not (1 <= fps <= 120):
                raise ValueError("FPS must be between 1 and 120")
            if not (0.0 <= threshold <= 1.0):
                raise ValueError("Threshold must be between 0.0 and 1.0")
            if not (0.1 <= bridge <= 5.0):
                raise ValueError("Bridge duration must be between 0.1 and 5.0 seconds")
            if not (0 <= crf <= 51):
                raise ValueError("CRF must be between 0 and 51")

        except ValueError as e:
            tk.messagebox.showerror("Invalid Settings", str(e))
            return

        # Create config
        config = Config(
            fps=fps,
            scene_threshold=threshold,
            bridge_duration=bridge,
            output_crf=crf,
            preset=self.preset_var.get(),
            audio_mode=self.audio_var.get(),
        )

        # Show progress window
        progress_window = ProgressWindow(self.root)

        # Message queue for thread communication
        msg_queue = queue.Queue()

        def progress_callback(msg):
            """Callback for progress updates."""
            msg_queue.put(("log", msg))

        def run_pipeline_thread():
            """Run pipeline in background thread."""
            try:
                pipeline = Pipeline(config, progress_callback=progress_callback)
                output_path = pipeline.run(self.input_path, self.output_path)
                msg_queue.put(("complete", output_path))
            except Exception as e:
                msg_queue.put(("error", str(e)))

        # Start processing thread
        thread = threading.Thread(target=run_pipeline_thread, daemon=True)
        thread.start()

        # Poll message queue
        def check_queue():
            try:
                while True:
                    msg_type, msg_data = msg_queue.get_nowait()

                    if msg_type == "log":
                        progress_window.append_log(msg_data)
                    elif msg_type == "complete":
                        progress_window.append_log(f"\n{'='*80}")
                        progress_window.append_log(f"SUCCESS! Output saved to:")
                        progress_window.append_log(f"  {msg_data}")
                        progress_window.append_log(f"{'='*80}")
                        progress_window.set_complete(success=True)
                        return
                    elif msg_type == "error":
                        progress_window.append_log(f"\n{'='*80}")
                        progress_window.append_log(f"ERROR: {msg_data}")
                        progress_window.append_log(f"{'='*80}")
                        progress_window.set_complete(success=False)
                        return

            except queue.Empty:
                pass

            # Schedule next check
            self.root.after(100, check_queue)

        # Start queue polling
        check_queue()


def launch_gui():
    """Launch the GUI."""
    root = tk.Tk()
    app = RifeCutSmoothGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
