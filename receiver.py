"""
receiver.py - Scans flashing QR codes using a webcam, displays live progress HUD,
verifies data integrity, and reconstructs the received file.
"""

import argparse
import os
import sys
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

# Try importing pyzbar for high-speed scanning; fallback to cv2.QRCodeDetector
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False

from protocol import ReceiverSession, TransferProtocol


def format_bytes(size: int) -> str:
    """Formats byte counts into human-readable strings."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def scan_qr_codes(frame: np.ndarray, cv_detector: Optional[cv2.QRCodeDetector] = None) -> List[Tuple[str, Optional[np.ndarray]]]:
    """
    Decodes QR codes from an image frame.
    
    Returns:
        List of tuples: (decoded_text, polygon_points)
    """
    results = []
    
    if HAS_PYZBAR:
        # Convert to grayscale for faster processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        decoded_objs = pyzbar_decode(gray)
        for obj in decoded_objs:
            try:
                text = obj.data.decode("utf-8")
                pts = np.array(obj.polygon, np.int32).reshape((-1, 1, 2))
                results.append((text, pts))
            except Exception:
                continue

    # Fallback to OpenCV QRCodeDetector if pyzbar didn't find anything
    if not results and cv_detector is not None:
        try:
            retval, decoded_info, points, _ = cv_detector.detectAndDecodeMulti(frame)
            if retval:
                for text, pts in zip(decoded_info, points):
                    if text:
                        pts_int = np.array(pts, np.int32).reshape((-1, 1, 2))
                        results.append((text, pts_int))
        except Exception:
            pass

    return results


def draw_hud(
    frame: np.ndarray,
    session: ReceiverSession,
    fps: float,
    last_scanned_idx: Optional[int] = None
) -> np.ndarray:
    """
    Renders an overlay HUD on top of the webcam frame with a progress bar and transfer statistics.
    """
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # 1. Header Banner (Dark gradient overlay)
    header_h = 70
    cv2.rectangle(overlay, (0, 0), (w, header_h), (25, 20, 18), -1)
    
    # 2. Footer HUD Banner
    footer_h = 105
    cv2.rectangle(overlay, (0, h - footer_h), (w, h), (25, 20, 18), -1)

    # Blend overlay with transparency
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

    # Header Content
    if session.file_id:
        fname = session.filename
        if len(fname) > 30:
            fname = fname[:27] + "..."
        title_text = f"Receiving: {fname}"
        size_text = f"Size: {format_bytes(session.orig_size)} (Compressed: {format_bytes(session.comp_size)})"
    else:
        title_text = "QR File Receiver - Ready"
        size_text = "Point camera at the flashing QR code on the sender screen"

    cv2.putText(frame, title_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, size_text, (15, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (190, 190, 190), 1, cv2.LINE_AA)
    
    # Camera FPS & Scanner Badge
    scanner_type = "pyzbar" if HAS_PYZBAR else "opencv"
    engine_text = f"Cam: {fps:.1f} FPS [{scanner_type}]"
    cv2.putText(frame, engine_text, (w - 185, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 220, 255), 1, cv2.LINE_AA)

    # Footer Progress Bar
    margin_x = 20
    pb_y = h - footer_h + 15
    pb_h = 22
    pb_w = w - (margin_x * 2)

    progress_pct = session.get_progress()
    
    # Progress bar border & track
    cv2.rectangle(frame, (margin_x, pb_y), (margin_x + pb_w, pb_y + pb_h), (50, 42, 38), -1)
    cv2.rectangle(frame, (margin_x, pb_y), (margin_x + pb_w, pb_y + pb_h), (95, 80, 70), 1)

    # Progress fill
    fill_w = int(pb_w * (progress_pct / 100.0))
    if fill_w > 0:
        bar_color = (60, 210, 75) if session.is_completed else (0, 180, 255)
        cv2.rectangle(frame, (margin_x, pb_y), (margin_x + fill_w, pb_y + pb_h), bar_color, -1)

    # Progress percentage text centered on the bar
    pct_text = f"{progress_pct:.1f}%"
    text_size = cv2.getTextSize(pct_text, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 2)[0]
    tx = margin_x + (pb_w - text_size[0]) // 2
    ty = pb_y + (pb_h + text_size[1]) // 2
    cv2.putText(frame, pct_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(frame, pct_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)

    # Footer Statistics
    received_count = len(session.received_chunks)
    total_count = session.total_chunks
    missing_count = len(session.get_missing_chunks())

    elapsed = time.time() - session.start_time if session.start_time else 0.0
    rate = (received_count / elapsed) if elapsed > 0 else 0.0

    stat_y1 = pb_y + pb_h + 24
    if session.is_completed:
        stat_text = f"[SUCCESS] 100% Complete! Received all {total_count} chunks in {elapsed:.1f}s"
        cv2.putText(frame, stat_text, (margin_x, stat_y1), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 235, 75), 2, cv2.LINE_AA)
        
        stat_y2 = stat_y1 + 22
        save_text = f"Saved to: {session.saved_filepath}"
        if len(save_text) > 65:
            save_text = save_text[:62] + "..."
        cv2.putText(frame, save_text, (margin_x, stat_y2), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    elif session.error_message:
        err_text = f"[ERROR] {session.error_message}"
        cv2.putText(frame, err_text, (margin_x, stat_y1), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 50, 240), 2, cv2.LINE_AA)
    else:
        stat_text = f"Chunks: {received_count} / {total_count}  |  Missing: {missing_count}  |  Speed: {rate:.1f} chunks/s"
        cv2.putText(frame, stat_text, (margin_x, stat_y1), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 230, 230), 1, cv2.LINE_AA)
        
        stat_y2 = stat_y1 + 20
        last_str = f"Last chunk received: #{last_scanned_idx + 1}" if last_scanned_idx is not None else "Waiting for initial chunk..."
        hint_str = "Press [Q] or [ESC] to quit"
        cv2.putText(frame, f"{last_str}   |   {hint_str}", (margin_x, stat_y2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 150, 150), 1, cv2.LINE_AA)

    # Highlight completion with top banner if done
    if session.is_completed:
        banner_h = 45
        cv2.rectangle(frame, (0, 0), (w, banner_h), (35, 160, 45), -1)
        cv2.putText(frame, "FILE RECEIVED & VERIFIED SUCCESSFULLY!", (w // 2 - 210, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

    return frame


def run_receiver(camera_idx: int = 0, output_dir: str = "received_files"):
    """
    Main loop for capturing video, detecting QR codes, and reconstructing files.
    """
    print(f"[*] Initializing camera index {camera_idx}...")
    cap = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
    
    if not cap.isOpened():
        print(f"[!] Unable to open camera {camera_idx}. Trying default backend...")
        cap = cv2.VideoCapture(camera_idx)
        if not cap.isOpened():
            print(f"[!] Fatal Error: Could not open camera {camera_idx}.")
            return

    # Request high resolution and FPS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    cv_detector = cv2.QRCodeDetector() if not HAS_PYZBAR else None
    session = ReceiverSession(output_dir=output_dir)

    window_name = "QR Receiver - Optical Scanner"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 600)

    print("\n[+] Receiver listening. Aim camera at the transmitter screen.")
    print("    Press 'q' or ESC in the window to stop.")

    last_scanned_idx = None
    frame_count = 0
    fps_start_time = time.time()
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("[!] Failed to grab frame from camera.")
            time.sleep(0.05)
            continue

        frame_count += 1
        now = time.time()
        if now - fps_start_time >= 1.0:
            fps = frame_count / (now - fps_start_time)
            frame_count = 0
            fps_start_time = now

        # Only decode QR codes if not already completed
        if not session.is_completed:
            qr_detections = scan_qr_codes(frame, cv_detector)
            for raw_text, pts in qr_detections:
                # Draw polygon around detected QR code
                if pts is not None:
                    cv2.polylines(frame, [pts], True, (0, 255, 0), 3)

                packet = TransferProtocol.parse_payload(raw_text)
                if packet:
                    is_new, is_done = session.add_chunk(packet)
                    last_scanned_idx = packet["i"]
                    
                    if is_new:
                        pct = session.get_progress()
                        print(f"\r[+] Received chunk {packet['i'] + 1}/{packet['t']} ({pct:.1f}%)", end="", flush=True)

                    if is_done:
                        print(f"\n\n{'='*60}")
                        print(f"[+] Transfer Complete! File verified with SHA-256.")
                        print(f"    Saved: {session.saved_filepath}")
                        print(f"    Size: {format_bytes(session.orig_size)}")
                        print(f"{'='*60}\n")

        # Draw real-time HUD with progress bar
        frame = draw_hud(frame, session, fps, last_scanned_idx)

        cv2.imshow(window_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            print("\n[*] Receiver stopped by user.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flashing QR Code File Receiver")
    parser.add_argument("-c", "--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("-o", "--output", type=str, default="received_files", help="Output directory (default: received_files)")

    args = parser.parse_args()
    run_receiver(camera_idx=args.camera, output_dir=args.output)
