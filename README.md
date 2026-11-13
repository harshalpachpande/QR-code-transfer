# ⚡ Optical QR Code File Transfer System

A high-speed, air-gapped optical file transfer system written in Python. It encodes any file into a stream of rapidly flashing QR codes displayed on screen, and decodes them in real time using a webcam or camera with live progress tracking, CRC32/SHA-256 integrity verification, and automatic carousel re-transmission.

---

## 🌟 Features

- **Any File Type**: Supports images, PDFs, archives, binaries, and text documents.
- **zlib Stream Compression**: Automatically compresses files prior to chunking, reducing the required QR code frames by 30%–70%.
- **Millisecond-Level Speed Control**: Flash QR codes at 30ms to 400ms intervals (10–30 FPS).
- **Carousel Looping Transmission**: Loops the QR stream continuously so the receiver automatically catches any missed or blurry frames on the next cycle.
- **Real-Time Visual Progress Bar**:
  - **Sender HUD**: Displays current chunk index / total chunks, loop cycle count, current delay (ms/FPS), and a visual progress bar.
  - **Receiver HUD**: Live camera overlay with green tracking polygon, progress bar (% complete), chunks received vs. missing count, reception rate (chunks/sec), and verified file save notification.
- **Data Integrity**: Per-chunk CRC32 verification and full-file SHA-256 cryptographic verification before disk write.
- **Unified GUI & CLI**: Launch either via the interactive graphical control center (`app.py`) or standalone command-line scripts.

---

## 📁 Project Structure

```
qr_file_transfer/
├── protocol.py       # Core chunking, compression, CRC32/SHA-256 validation
├── sender.py         # QR code generator, flashing window, and HUD progress bar
├── receiver.py       # Webcam QR scanner, live HUD overlay, and file assembler
├── app.py            # Unified GUI Launcher (Tkinter)
├── test_transfer.py  # Automated end-to-end test suite
└── received_files/   # Default directory where received files are saved
```

---

## 🚀 Quick Start

### 1. Launch the Unified GUI
```bash
python app.py
```
From the GUI you can:
- Select any file to upload and start transmitting.
- Tune the flashing delay (ms) and chunk size.
- Select your webcam and launch the optical scanner.
- Quickly browse and open the received files folder.

---

### 2. Standalone Sender (Transmitter)

```bash
# Upload a file via file picker dialog:
python sender.py

# Or specify the file directly with custom speed:
python sender.py --file "C:\path\to\document.pdf" --delay 100 --chunk-size 350
```

#### Sender On-Screen Hotkeys:
| Key | Action |
|---|---|
| `+` / `Up Arrow` | Increase flashing speed (decrease ms delay) |
| `-` / `Down Arrow` | Decrease flashing speed (increase ms delay) |
| `Spacebar` | Pause / Resume transmission |
| `Left` / `Right Arrow` | Step backward / forward one chunk (when paused) |
| `r` / `R` | Reset stream back to chunk 1 |
| `q` / `ESC` | Stop and close sender |

---

### 3. Standalone Receiver (Scanner)

```bash
# Launch receiver with default webcam:
python receiver.py

# Specify a different camera index or output directory:
python receiver.py --camera 0 --output "received_files"
```

#### Receiver On-Screen HUD:
- **Green Box**: Shows the detected QR code in real-time.
- **Top Bar**: Current file name and size.
- **Bottom Progress Bar**: Live completion % and colored status bar.
- **Stats**: Total chunks, missing chunks, and chunks/sec throughput.
- **Success Banner**: Appears when 100% of chunks are collected and SHA-256 hash is verified.

---

## 🧪 Verification & Testing

Run the automated headless test suite:
```bash
python test_transfer.py
```
This simulates end-to-end QR code generation, optical frame decoding, out-of-order chunk assembly, and byte-for-byte SHA-256 verification.

---

## 💡 Optical Scanning Best Practices

1. **Distance & Focus**: Position the receiving camera 20–50 cm away from the sender screen so the QR code covers roughly 50%–75% of the camera frame.
2. **Screen Brightness**: Ensure the screen has good contrast and avoid direct glare or reflections on the monitor.
3. **Speed Tuning**: Start at `100ms` (~10 FPS). If the camera runs smoothly at 30 or 60 FPS, press `+` on the sender to increase speed down to `50ms` (~20 FPS).
4. **Dropped Frames**: You don't need to restart if a frame is missed; the sender streams in an infinite carousel loop until all chunks are collected!
