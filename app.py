"""
app.py - Unified Graphical Launcher for Optical QR Code File Transfer System.
Allows users to easily launch Sender or Receiver with customized settings.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class QRTransferApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Optical QR Code File Transfer")
        self.geometry("620x540")
        self.minsize(580, 480)

        # Base style configuration
        self.configure(bg="#1E1E2E")
        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Configure notebook tabs
        style.configure("TNotebook", background="#1E1E2E", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2A2B3D", foreground="#CDD6F4", padding=[18, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#89B4FA")], foreground=[("selected", "#11111B")])

        # Frames & Labels
        style.configure("TFrame", background="#1E1E2E")
        style.configure("Card.TFrame", background="#252538", relief="ridge", borderwidth=1)
        style.configure("TLabel", background="#1E1E2E", foreground="#CDD6F4", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#252538", foreground="#CDD6F4", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#1E1E2E", foreground="#89B4FA", font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background="#1E1E2E", foreground="#A6ADC8", font=("Segoe UI", 9))
        style.configure("Header.TLabel", background="#25382D", foreground="#F9E2AF", font=("Segoe UI", 11, "bold"))

        # Buttons
        style.configure("Primary.TButton", background="#89B4FA", foreground="#11111B", font=("Segoe UI", 11, "bold"), borderwidth=0, padding=[12, 8])
        style.map("Primary.TButton", background=[("active", "#B4BEFE")])

        style.configure("Secondary.TButton", background="#45475A", foreground="#CDD6F4", font=("Segoe UI", 9, "bold"), borderwidth=0, padding=[8, 5])
        style.map("Secondary.TButton", background=[("active", "#585B70")])

        style.configure("Success.TButton", background="#A6E3A1", foreground="#11111B", font=("Segoe UI", 11, "bold"), borderwidth=0, padding=[12, 8])
        style.map("Success.TButton", background=[("active", "#94E2D5")])

    def create_widgets(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title = ttk.Label(header_frame, text="⚡ QR Flash File Transfer", style="Title.TLabel")
        title.pack(anchor="w")
        subtitle = ttk.Label(header_frame, text="High-speed optical data transmission over animated QR code streams", style="Subtitle.TLabel")
        subtitle.pack(anchor="w", pady=(2, 0))

        # Notebook tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        # 1. Send Tab
        send_tab = ttk.Frame(notebook)
        notebook.add(send_tab, text="  📤 Send File (Transmitter)  ")
        self.build_send_tab(send_tab)

        # 2. Receive Tab
        recv_tab = ttk.Frame(notebook)
        notebook.add(recv_tab, text="  📥 Receive File (Scanner)  ")
        self.build_receive_tab(recv_tab)

        # 3. Help & Tips Tab
        help_tab = ttk.Frame(notebook)
        notebook.add(help_tab, text="  💡 Tips & Info  ")
        self.build_help_tab(help_tab)

    def build_send_tab(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(card, text="File Selection", style="Header.TLabel").pack(anchor="w", pady=(0, 5))
        
        # File selector row
        file_frame = ttk.Frame(card, style="Card.TFrame")
        file_frame.pack(fill="x", pady=(0, 15))

        self.send_file_var = tk.StringVar(value="")
        file_entry = ttk.Entry(file_frame, textvariable=self.send_file_var, font=("Segoe UI", 9))
        file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)

        browse_btn = ttk.Button(file_frame, text="Browse...", style="Secondary.TButton", command=self.browse_send_file)
        browse_btn.pack(side="right")

        # Transmission settings
        ttk.Label(card, text="Transmission Settings", style="Header.TLabel").pack(anchor="w", pady=(5, 5))

        # Milliseconds delay slider
        delay_frame = ttk.Frame(card, style="Card.TFrame")
        delay_frame.pack(fill="x", pady=4)
        
        self.delay_var = tk.IntVar(value=100)
        self.delay_label = ttk.Label(delay_frame, text="Speed / Delay: 100 ms (~10.0 FPS)", style="Card.TLabel")
        self.delay_label.pack(anchor="w")

        delay_scale = ttk.Scale(
            delay_frame,
            from_=30,
            to=400,
            variable=self.delay_var,
            command=self.update_delay_label
        )
        delay_scale.pack(fill="x", pady=2)

        # Chunk size slider
        chunk_frame = ttk.Frame(card, style="Card.TFrame")
        chunk_frame.pack(fill="x", pady=6)

        self.chunk_var = tk.IntVar(value=350)
        self.chunk_label = ttk.Label(chunk_frame, text="Chunk Size: 350 bytes per QR code", style="Card.TLabel")
        self.chunk_label.pack(anchor="w")

        chunk_scale = ttk.Scale(
            chunk_frame,
            from_=150,
            to=700,
            variable=self.chunk_var,
            command=self.update_chunk_label
        )
        chunk_scale.pack(fill="x", pady=2)

        # Start Button
        start_send_btn = ttk.Button(
            card,
            text="🚀 Start Flashing Transmission",
            style="Primary.TButton",
            command=self.launch_sender
        )
        start_send_btn.pack(fill="x", pady=(18, 5))

    def build_receive_tab(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(card, text="Camera & Storage", style="Header.TLabel").pack(anchor="w", pady=(0, 5))

        # Camera selection row
        cam_frame = ttk.Frame(card, style="Card.TFrame")
        cam_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(cam_frame, text="Camera Device Index:", style="Card.TLabel").pack(side="left", padx=(0, 10))
        self.cam_idx_var = tk.IntVar(value=0)
        cam_spin = ttk.Spinbox(cam_frame, from_=0, to=5, textvariable=self.cam_idx_var, width=5)
        cam_spin.pack(side="left")

        # Output folder row
        ttk.Label(card, text="Save Received Files In:", style="Card.TLabel").pack(anchor="w", pady=(5, 2))
        out_frame = ttk.Frame(card, style="Card.TFrame")
        out_frame.pack(fill="x", pady=(0, 10))

        default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "received_files"))
        self.output_dir_var = tk.StringVar(value=default_dir)
        out_entry = ttk.Entry(out_frame, textvariable=self.output_dir_var, font=("Segoe UI", 9))
        out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)

        out_browse = ttk.Button(out_frame, text="Change...", style="Secondary.TButton", command=self.browse_output_dir)
        out_browse.pack(side="right")

        # Open folder button
        open_folder_btn = ttk.Button(
            card,
            text="📁 Open Received Files Folder",
            style="Secondary.TButton",
            command=self.open_output_folder
        )
        open_folder_btn.pack(anchor="w", pady=(0, 15))

        # Launch Receiver Button
        start_recv_btn = ttk.Button(
            card,
            text="📷 Launch Webcam Scanner",
            style="Success.TButton",
            command=self.launch_receiver
        )
        start_recv_btn.pack(fill="x", pady=(10, 5))

    def build_help_tab(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        tips_text = (
            "✨ Tips for High-Speed Optical File Transfer:\n\n"
            "1. Distance & Focus: Position camera ~20-50 cm away from the sender screen "
            "so the QR code fills roughly 40-70% of the camera view.\n\n"
            "2. Speed Optimization: Start at 100ms (~10 FPS). You can press '+' in the "
            "sender window to speed up to 50ms (~20 FPS) if your camera is 30/60 FPS.\n\n"
            "3. Automatic Catch-up: The sender streams in a continuous loop. If a frame "
            "is dropped or blurry, the receiver will automatically catch it on the next cycle!\n\n"
            "4. Integrity Verification: Every chunk is CRC32 checked and the completed file is "
            "verified against its master SHA-256 hash before saving.\n\n"
            "5. Hotkeys on Sender: '+' / '-' adjust speed, 'Space' pauses, 'R' resets to chunk 1, 'Q' exits."
        )
        msg_label = ttk.Label(card, text=tips_text, style="Card.TLabel", justify="left", wraplength=480)
        msg_label.pack(anchor="w", fill="both", expand=True)

    def update_delay_label(self, val):
        delay = int(float(val))
        fps = 1000.0 / delay if delay > 0 else 0
        self.delay_label.config(text=f"Speed / Delay: {delay} ms (~{fps:.1f} FPS)")

    def update_chunk_label(self, val):
        chunk = int(float(val))
        self.chunk_label.config(text=f"Chunk Size: {chunk} bytes per QR code")

    def browse_send_file(self):
        filename = filedialog.askopenfilename(title="Select File to Send")
        if filename:
            self.send_file_var.set(filename)

    def browse_output_dir(self):
        dirpath = filedialog.askdirectory(title="Select Output Folder")
        if dirpath:
            self.output_dir_var.set(dirpath)

    def open_output_folder(self):
        target = self.output_dir_var.get()
        os.makedirs(target, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])

    def launch_sender(self):
        target_file = self.send_file_var.get().strip()
        if not target_file:
            messagebox.showwarning("File Required", "Please select a file to transfer first.")
            return
        if not os.path.isfile(target_file):
            messagebox.showerror("File Error", f"Cannot find file:\n{target_file}")
            return

        delay = int(self.delay_var.get())
        chunk_size = int(self.chunk_var.get())

        sender_script = os.path.join(os.path.dirname(__file__), "sender.py")
        cmd = [
            sys.executable,
            sender_script,
            "--file", target_file,
            "--delay", str(delay),
            "--chunk-size", str(chunk_size)
        ]

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to launch sender:\n{e}")

    def launch_receiver(self):
        cam_idx = self.cam_idx_var.get()
        output_dir = self.output_dir_var.get().strip()

        receiver_script = os.path.join(os.path.dirname(__file__), "receiver.py")
        cmd = [
            sys.executable,
            receiver_script,
            "--camera", str(cam_idx),
            "--output", output_dir
        ]

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to launch receiver:\n{e}")


def main():
    app = QRTransferApp()
    app.mainloop()


if __name__ == "__main__":
    main()
