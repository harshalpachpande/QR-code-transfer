"""
sender.py - Transmits files by flashing QR codes sequentially on screen.
Includes millisecond timing control, real-time HUD, and visual progress bar.
"""

import argparse
import os
import sys
import time
import tkinter as tk
from tkinter import filedialog
from typing import List, Optional

import cv2
import numpy as np
import qrcode

from protocol import TransferProtocol


def select_file_dialog() -> Optional[str]:
    """Opens a native file picker dialog to select a file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    filepath = filedialog.askopenfilename(
        title="Select File to Transfer via QR Codes",
        filetypes=[("All Files", "*.*")]
    )
    root.destroy()
    return filepath if filepath else None


def format_bytes(size: int) -> str:
    """Formats byte counts into human-readable strings."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def pregenerate_qr_frames(payloads: List[str], qr_box_size: int = 8, border: int = 2) -> List[np.ndarray]:
    """
    Pre-generates QR code images as OpenCV BGR numpy arrays.
    Uses QR Error Correction Level L for highest data density and fastest optical reading.
    """
    frames = []
    print(f"[*] Pre-generating {len(payloads)} QR code frame(s)...")
    
    for i, payload in enumerate(payloads):
        qr = qrcode.QRCode(
            version=None,  # Auto-determine smallest version
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=qr_box_size,
            border=border,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        
        # Convert PIL Image to OpenCV BGR
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        frames.append(cv_img)

        # Progress indicator in console
        if (i + 1) % 10 == 0 or (i + 1) == len(payloads):
            pct = ((i + 1) / len(payloads)) * 100
            print(f"\r    Rendered {i + 1}/{len(payloads)} frames ({pct:.0f}%)", end="", flush=True)

    print("\n[+] All frames generated successfully.")
    return frames


def create_sender_canvas(
    qr_img: np.ndarray,
    current_idx: int,
    total_chunks: int,
    cycle_count: int,
    delay_ms: int,
    is_paused: bool,
    meta: dict
) -> np.ndarray:
    """
    Renders the complete display canvas including header, QR code, on-screen progress bar, and HUD.
    """
    qr_h, qr_w = qr_img.shape[:2]
    
    # Canvas dimensions
    margin = 20
    header_h = 75
    footer_h = 100
    canvas_w = max(qr_w + margin * 2, 540)
    canvas_h = qr_h + header_h + footer_h + margin * 2

    # Create dark modern canvas background (Dark Slate #1E222A)
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[:] = (30, 24, 20)  # BGR

    # 1. Place QR Code centered
    qr_x = (canvas_w - qr_w) // 2
    qr_y = header_h + margin
    canvas[qr_y:qr_y + qr_h, qr_x:qr_x + qr_w] = qr_img

    # 2. Header: File details
    cv2.rectangle(canvas, (0, 0), (canvas_w, header_h), (45, 38, 32), -1)
    cv2.line(canvas, (0, header_h), (canvas_w, header_h), (70, 60, 50), 1)

    filename_text = f"File: {meta['filename']}"
    if len(filename_text) > 42:
        filename_text = filename_text[:39] + "..."
    cv2.putText(canvas, filename_text, (margin, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

    size_info = f"Size: {format_bytes(meta['orig_size'])} -> {format_bytes(meta['comp_size'])} ({meta['compression_ratio']:.1f}% saved)"
    cv2.putText(canvas, size_info, (margin, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1, cv2.LINE_AA)

    # 3. Footer: Progress Bar
    pb_y = qr_y + qr_h + 15
    pb_h = 16
    pb_w = canvas_w - (margin * 2)
    
    # Progress bar background
    cv2.rectangle(canvas, (margin, pb_y), (margin + pb_w, pb_y + pb_h), (50, 40, 35), -1)
    cv2.rectangle(canvas, (margin, pb_y), (margin + pb_w, pb_y + pb_h), (90, 80, 70), 1)
    
    # Progress bar fill (Green to Cyan gradient look)
    progress_ratio = (current_idx + 1) / total_chunks
    fill_w = int(pb_w * progress_ratio)
    if fill_w > 0:
        cv2.rectangle(canvas, (margin, pb_y), (margin + fill_w, pb_y + pb_h), (80, 200, 50), -1)

    # 4. Status and Chunk Info
    info_y1 = pb_y + pb_h + 25
    chunk_text = f"Chunk: {current_idx + 1} / {total_chunks}   |   Loop Cycle: #{cycle_count}"
    cv2.putText(canvas, chunk_text, (margin, info_y1), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1, cv2.LINE_AA)

    # Speed & Status Badges
    fps = 1000.0 / delay_ms if delay_ms > 0 else 0
    status_str = "[PAUSED]" if is_paused else "[TRANSMITTING]"
    status_color = (0, 165, 255) if is_paused else (80, 230, 80)
    
    info_y2 = info_y1 + 22
    speed_text = f"Speed: {delay_ms} ms/frame (~{fps:.1f} FPS)   {status_str}"
    cv2.putText(canvas, speed_text, (margin, info_y2), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1, cv2.LINE_AA)

    # Controls hint
    info_y3 = info_y2 + 20
    hint_text = "[+/-] Speed  [Space] Pause  [<- / ->] Step  [R] Reset  [Q] Exit"
    cv2.putText(canvas, hint_text, (margin, info_y3), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1, cv2.LINE_AA)

    return canvas


def run_sender(filepath: str, delay_ms: int = 100, chunk_size: int = 350, qr_box_size: int = 7):
    """
    Main loop for transmitting the selected file as flashing QR codes.
    
    Args:
        filepath: Target file path.
        delay_ms: Milliseconds per frame (default 100ms = 10 FPS).
        chunk_size: Bytes per chunk (default 350).
        qr_box_size: Pixel scaling factor per QR module.
    """
    print(f"[*] Preparing file: {filepath}")
    try:
        payloads, meta = TransferProtocol.prepare_file(filepath, chunk_size=chunk_size)
    except Exception as e:
        print(f"[!] Error preparing file: {e}")
        return

    print(f"[+] File ready: {meta['filename']}")
    print(f"    Original: {format_bytes(meta['orig_size'])}, Compressed: {format_bytes(meta['comp_size'])}")
    print(f"    Total chunks: {meta['total_chunks']}")
    print(f"    Initial speed: {delay_ms} ms per frame (~{1000/delay_ms:.1f} FPS)")

    # Pre-render QR code images for glitch-free optical transmission
    frames = pregenerate_qr_frames(payloads, qr_box_size=qr_box_size)

    window_name = "QR Transmitter - Flashing Sender"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    idx = 0
    cycle_count = 1
    total_chunks = len(frames)
    is_paused = False

    print("\n[+] Starting broadcast. Point the receiver camera at the screen.")
    print("    Controls:")
    print("      '+' or Up Arrow   : Increase Speed (faster flashing)")
    print("      '-' or Down Arrow : Decrease Speed (slower flashing)")
    print("      Spacebar          : Pause / Resume")
    print("      Left / Right      : Step frame (when paused)")
    print("      'r'               : Reset to first chunk")
    print("      'q' or ESC        : Stop & Close\n")

    while True:
        # Create framed canvas with HUD and progress bar
        canvas = create_sender_canvas(
            qr_img=frames[idx],
            current_idx=idx,
            total_chunks=total_chunks,
            cycle_count=cycle_count,
            delay_ms=delay_ms,
            is_paused=is_paused,
            meta=meta
        )

        cv2.imshow(window_name, canvas)

        # Wait key handles both frame pacing and user input
        wait_time = 30 if is_paused else max(10, delay_ms)
        key = cv2.waitKeyEx(wait_time)

        if key in (ord('q'), ord('Q'), 27):  # 'q' or ESC
            print("\n[*] Sender closed by user.")
            break
        elif key in (ord('+'), ord('='), 2490368):  # '+' or Up Arrow (Windows key code)
            delay_ms = max(20, delay_ms - 15)
            print(f"[*] Speed changed: {delay_ms} ms/frame ({1000/delay_ms:.1f} FPS)")
        elif key in (ord('-'), ord('_'), 2621440):  # '-' or Down Arrow (Windows key code)
            delay_ms = min(2000, delay_ms + 15)
            print(f"[*] Speed changed: {delay_ms} ms/frame ({1000/delay_ms:.1f} FPS)")
        elif key == ord(' '):  # Spacebar
            is_paused = not is_paused
            print(f"[*] {'Paused' if is_paused else 'Resumed'}")
        elif key in (ord('r'), ord('R')):
            idx = 0
            cycle_count = 1
            print("[*] Rewound to chunk 1.")
        elif is_paused:
            if key in (ord('a'), 2424832):  # Left Arrow
                idx = (idx - 1) % total_chunks
            elif key in (ord('d'), 2555904):  # Right Arrow
                idx = (idx + 1) % total_chunks

        # Advance to next frame if not paused
        if not is_paused:
            idx += 1
            if idx >= total_chunks:
                idx = 0
                cycle_count += 1

    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flashing QR Code File Sender")
    parser.add_argument("-f", "--file", type=str, help="Path to file to transmit (opens dialog if omitted)")
    parser.add_argument("-d", "--delay", type=int, default=100, help="Delay in milliseconds per frame (default: 100ms)")
    parser.add_argument("-c", "--chunk-size", type=int, default=350, help="Raw chunk size in bytes (default: 350)")
    parser.add_argument("-s", "--scale", type=int, default=7, help="QR code module size scale (default: 7)")

    args = parser.parse_args()

    target_file = args.file
    if not target_file:
        print("[*] No file specified. Opening file selection dialog...")
        target_file = select_file_dialog()
        if not target_file:
            print("[!] No file selected. Exiting.")
            sys.exit(0)

    run_sender(
        filepath=target_file,
        delay_ms=args.delay,
        chunk_size=args.chunk_size,
        qr_box_size=args.scale
    )
