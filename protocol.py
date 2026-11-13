"""
protocol.py - Core data protocol for QR Code File Transfer
Handles compression, chunking, framing, validation, and reconstruction.
"""

import base64
import hashlib
import json
import math
import os
import time
import zlib
from typing import Dict, List, Optional, Tuple


class TransferProtocol:
    """
    Encapsulates packaging files into QR-ready chunks and reassembling received chunks.
    """

    MAGIC_PREFIX = "QRFT1:"  # QR File Transfer Version 1 prefix

    @staticmethod
    def prepare_file(filepath: str, chunk_size: int = 350) -> Tuple[List[str], dict]:
        """
        Reads a file, compresses it with zlib, chunks it, and generates payload strings.
        
        Args:
            filepath: Path to the file to transmit.
            chunk_size: Size in bytes of each raw compressed chunk (default 350).
            
        Returns:
            Tuple of (list_of_payload_strings, metadata_dict)
        """
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            raw_data = f.read()

        orig_size = len(raw_data)
        file_sha256 = hashlib.sha256(raw_data).hexdigest()

        # Compress data with zlib
        comp_data = zlib.compress(raw_data, level=9)
        comp_size = len(comp_data)

        # Generate unique file ID based on hash and timestamp
        file_id = hashlib.md5(f"{file_sha256}:{time.time()}".encode()).hexdigest()[:8]

        # Calculate chunk count
        total_chunks = max(1, math.ceil(comp_size / chunk_size))
        
        chunks = []
        for idx in range(total_chunks):
            start = idx * chunk_size
            end = min(start + chunk_size, comp_size)
            chunk_bytes = comp_data[start:end]
            
            chunk_crc = zlib.crc32(chunk_bytes)
            chunk_b64 = base64.b64encode(chunk_bytes).decode("ascii")

            packet = {
                "id": file_id,
                "n": filename,
                "i": idx,
                "t": total_chunks,
                "s": orig_size,
                "cs": comp_size,
                "c": chunk_crc,
                "h": file_sha256,
                "d": chunk_b64
            }
            
            # Format as JSON string with prefix
            payload_str = TransferProtocol.MAGIC_PREFIX + json.dumps(packet, separators=(',', ':'))
            chunks.append(payload_str)

        metadata = {
            "file_id": file_id,
            "filename": filename,
            "orig_size": orig_size,
            "comp_size": comp_size,
            "compression_ratio": (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0,
            "total_chunks": total_chunks,
            "sha256": file_sha256,
            "chunk_size": chunk_size
        }

        return chunks, metadata

    @staticmethod
    def parse_payload(payload_str: str) -> Optional[dict]:
        """
        Parses a received payload string from a QR code.
        
        Returns parsed packet dict if valid, or None if invalid.
        """
        if not payload_str or not payload_str.startswith(TransferProtocol.MAGIC_PREFIX):
            return None

        json_str = payload_str[len(TransferProtocol.MAGIC_PREFIX):]
        try:
            packet = json.loads(json_str)
            # Validate required keys
            required_keys = ("id", "n", "i", "t", "s", "cs", "c", "h", "d")
            if not all(k in packet for k in required_keys):
                return None

            # Verify chunk data CRC32
            chunk_bytes = base64.b64decode(packet["d"].encode("ascii"))
            calc_crc = zlib.crc32(chunk_bytes)
            if calc_crc != packet["c"]:
                return None  # Corrupted chunk

            packet["_raw_bytes"] = chunk_bytes
            return packet
        except Exception:
            return None


class ReceiverSession:
    """
    Manages state for receiving a file transmission over QR codes.
    """

    def __init__(self, output_dir: str = "received_files"):
        self.output_dir = output_dir
        self.file_id: Optional[str] = None
        self.filename: str = ""
        self.total_chunks: int = 0
        self.orig_size: int = 0
        self.comp_size: int = 0
        self.file_sha256: str = ""
        
        self.received_chunks: Dict[int, bytes] = {}
        self.start_time: Optional[float] = None
        self.last_chunk_time: Optional[float] = None
        self.is_completed: bool = False
        self.saved_filepath: Optional[str] = None
        self.error_message: Optional[str] = None

    def reset(self, file_id: str, filename: str, total_chunks: int, orig_size: int, comp_size: int, file_sha256: str):
        """Initializes state for a new file transfer."""
        self.file_id = file_id
        self.filename = filename
        self.total_chunks = total_chunks
        self.orig_size = orig_size
        self.comp_size = comp_size
        self.file_sha256 = file_sha256
        self.received_chunks = {}
        self.start_time = time.time()
        self.last_chunk_time = time.time()
        self.is_completed = False
        self.saved_filepath = None
        self.error_message = None

    def add_chunk(self, packet: dict) -> Tuple[bool, bool]:
        """
        Adds a parsed packet into the session.
        
        Returns:
            (is_new_chunk, is_now_completed)
        """
        pkt_id = packet["id"]
        
        # If it's a new file or we don't have an active session
        if self.file_id != pkt_id:
            self.reset(
                file_id=pkt_id,
                filename=packet["n"],
                total_chunks=packet["t"],
                orig_size=packet["s"],
                comp_size=packet["cs"],
                file_sha256=packet["h"]
            )

        idx = packet["i"]
        is_new = idx not in self.received_chunks

        if is_new:
            self.received_chunks[idx] = packet["_raw_bytes"]
            self.last_chunk_time = time.time()

        # Check for completion
        if len(self.received_chunks) == self.total_chunks and not self.is_completed:
            success = self._finalize_and_save()
            return is_new, success

        return is_new, self.is_completed

    def get_progress(self) -> float:
        """Returns progress percentage (0.0 to 100.0)."""
        if self.total_chunks == 0:
            return 0.0
        return (len(self.received_chunks) / self.total_chunks) * 100.0

    def get_missing_chunks(self) -> List[int]:
        """Returns sorted list of missing chunk indices."""
        if self.total_chunks == 0:
            return []
        all_indices = set(range(self.total_chunks))
        missing = sorted(list(all_indices - set(self.received_chunks.keys())))
        return missing

    def _finalize_and_save(self) -> bool:
        """Reconstructs, decompresses, verifies, and saves the file."""
        try:
            # Assemble compressed stream in order
            comp_stream = b"".join(self.received_chunks[i] for i in range(self.total_chunks))
            
            # Decompress
            raw_data = zlib.decompress(comp_stream)
            
            # Verify SHA-256
            calc_sha256 = hashlib.sha256(raw_data).hexdigest()
            if calc_sha256.lower() != self.file_sha256.lower():
                self.error_message = f"SHA256 checksum mismatch! Expected: {self.file_sha256[:8]}, Got: {calc_sha256[:8]}"
                return False

            # Create output directory
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Avoid overwriting existing files with same name
            base, ext = os.path.splitext(self.filename)
            target_path = os.path.join(self.output_dir, self.filename)
            counter = 1
            while os.path.exists(target_path):
                target_path = os.path.join(self.output_dir, f"{base}_{counter}{ext}")
                counter += 1

            with open(target_path, "wb") as f:
                f.write(raw_data)

            self.saved_filepath = target_path
            self.is_completed = True
            return True
        except Exception as e:
            self.error_message = f"Reconstruction error: {str(e)}"
            return False
