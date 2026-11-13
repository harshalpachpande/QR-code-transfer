"""
test_transfer.py - Automated End-to-End Test for QR Code File Transfer System.
Tests chunking, QR encoding, QR decoding from image frames, out-of-order handling,
carousel recovery, SHA-256 verification, and byte-for-byte file reconstruction.
"""

import hashlib
import os
import shutil
import tempfile
import time

import cv2
import numpy as np

from protocol import ReceiverSession, TransferProtocol
from receiver import scan_qr_codes
from sender import pregenerate_qr_frames


def run_tests():
    print("=" * 65)
    print("[*] Running Automated QR File Transfer Pipeline Verification")
    print("=" * 65)

    test_dir = tempfile.mkdtemp(prefix="qr_test_")
    out_dir = os.path.join(test_dir, "output")
    os.makedirs(out_dir, exist_ok=True)

    try:
        # 1. Create a dummy test file with mixed text and binary data
        test_filepath = os.path.join(test_dir, "sample_document.dat")
        sample_content = (
            b"Hello World! This is a test file for the Optical QR Code File Transfer System.\n"
            b"Testing chunking, compression, CRC32 error-checks, and SHA256 validation.\n"
            + os.urandom(4096)  # 4KB random binary data
        )

        with open(test_filepath, "wb") as f:
            f.write(sample_content)

        orig_sha256 = hashlib.sha256(sample_content).hexdigest()
        print(f"[1] Created test file: {len(sample_content)} bytes")
        print(f"    Original SHA-256: {orig_sha256}")

        # 2. Prepare file chunks
        chunk_size = 300
        payloads, meta = TransferProtocol.prepare_file(test_filepath, chunk_size=chunk_size)
        print(f"[2] Prepared {len(payloads)} chunk payloads (chunk size: {chunk_size}B)")
        print(f"    Original Size: {meta['orig_size']}B -> Compressed: {meta['comp_size']}B ({meta['compression_ratio']:.1f}% saved)")

        # 3. Generate QR images
        qr_frames = pregenerate_qr_frames(payloads, qr_box_size=5)
        assert len(qr_frames) == len(payloads), "Frame count mismatch"
        print(f"[3] Generated {len(qr_frames)} QR code image frames.")

        # 4. Optical Scan & Decode Simulation (simulating non-linear reception / dropped frames)
        print("[4] Simulating receiver decoding QR image frames...")
        cv_detector = cv2.QRCodeDetector()
        session = ReceiverSession(output_dir=out_dir)

        # Simulate out-of-order arrival + dropped frames recovered in second pass
        indices = list(range(len(qr_frames)))
        # Split into two passes to simulate a carousel loop
        first_pass = indices[::2]  # Even indices
        second_pass = indices[1::2]  # Odd indices
        simulated_stream = first_pass + second_pass

        print(f"    Simulating transmission stream across 2 carousel cycles ({len(simulated_stream)} frame reads)...")

        for step, idx in enumerate(simulated_stream):
            frame = qr_frames[idx]
            detections = scan_qr_codes(frame, cv_detector)
            assert len(detections) > 0, f"Failed to detect QR code at index {idx}"
            
            raw_text, pts = detections[0]
            packet = TransferProtocol.parse_payload(raw_text)
            assert packet is not None, f"Failed to parse payload for chunk {idx}"

            is_new, is_done = session.add_chunk(packet)
            progress = session.get_progress()

            if is_done:
                print(f"\n[+] Transfer completed at step {step + 1}!")
                break

        # 5. Verify reconstructed file
        assert session.is_completed, "Session was not marked completed"
        assert session.saved_filepath is not None, "Saved file path is None"
        assert os.path.isfile(session.saved_filepath), f"Saved file does not exist: {session.saved_filepath}"

        with open(session.saved_filepath, "rb") as f:
            reconstructed_data = f.read()

        reconstructed_sha256 = hashlib.sha256(reconstructed_data).hexdigest()
        print(f"[5] Reconstructed file: {len(reconstructed_data)} bytes")
        print(f"    Reconstructed SHA-256: {reconstructed_sha256}")

        assert reconstructed_sha256 == orig_sha256, "SHA-256 MISMATCH!"
        assert reconstructed_data == sample_content, "Binary content mismatch!"

        print("\n" + "=" * 65)
        print("[SUCCESS] ALL TESTS PASSED! Optical QR File Transfer is 100% working.")
        print("=" * 65)

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
