"""
Extract Google Meet Timestamps
By Sreenikethan I
https://github.com/SreenikethanI
21/Oct/2025

This script extracts timestamps from a Google Meet recording by sampling a
cropped, grayscale video stream at a fixed frame rate. If it detects visual
changes between consecutive frames, the frame is saved to a file with the
exact video timestamp mentioned in the filename.

Inputs
------
- Cropbox: Crop the video. Format: width:height:x:y
- Sample rate: The frame rate with which to read the file.
- Comparison threshold: The minimum difference required between two consecutive
    frames to be considered "different". Ranges from 0.0 to 1.0.
"""

import subprocess
import PIL.Image
import os
import os.path

CROPBOX_DEFAULT     = "100:40:71:1310"
SAMPLE_RATE_DEFAULT = 1
PATH_OUT_DEFAULT    = "output/"
THRESHOLD_DEFAULT   = 0.25

# ============================================================================ #

def are_images_equal(frame1: bytes, frame2: bytes, threshold: float=THRESHOLD_DEFAULT) -> bool:
    """Check if the two frames are similar below the given threshold. The colors
    are converted to linear (just squared) before comparison. `threshold` ranges
    from 0 to 1."""

    if len(frame1) != len(frame2):
        raise ValueError("Must be equal length.")

    for b1, b2 in zip(frame1, frame2):
        b1_linear = (b1 / 255) ** 2
        b2_linear = (b2 / 255) ** 2
        if abs(b1_linear - b2_linear) >= threshold:
            return False

    return True

def format_seconds(seconds: float) -> str:
    """Format seconds into hh:mm:ss."""

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"

def start_ffmpeg(input_file: str, sample_rate: float, cropbox: str):
    """Start an instance of FFmpeg with the given parameters. The video is
    output as `rawvideo` format with `gray` (8-bit grayscale) pixel format.

    Arguments:
        input_file: Path to input file.
        sample_rate: The frame rate of the output.
        cropbox: A string of format `width:height:x:y` to crop the video."""
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", input_file.replace('"', "").strip(),
        "-vf", f"fps={sample_rate},crop={cropbox}",
        "-f", "rawvideo",
        "-pix_fmt", "gray",
        "-hide_banner",
        "-"
    ]
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not ffmpeg_proc.stdout or not ffmpeg_proc.stdout.readable():
        raise BrokenPipeError("Unable to open pipe for `stdout`.")
    if not ffmpeg_proc.stderr or not ffmpeg_proc.stderr.readable():
        raise BrokenPipeError("Unable to open pipe for `stderr`.")

    return ffmpeg_proc

# ============================================================================ #

if __name__ == "__main__":
    print(__doc__)
    print()

    input_file = ""
    print("Input video file path:")
    while True:
        input_file = input("==> ").strip()
        if os.path.isfile(input_file): break
        print("    Please enter a valid file.")
    path_out    =       input(f"Output path (default={PATH_OUT_DEFAULT}):\n==> ").replace('"', "").strip() or PATH_OUT_DEFAULT
    cropbox     =       input(f"Cropbox (default={CROPBOX_DEFAULT}):\n==> ").strip() or CROPBOX_DEFAULT
    sample_rate = float(input(f"Sample rate (default={SAMPLE_RATE_DEFAULT}):\n==> ").strip() or SAMPLE_RATE_DEFAULT)
    threshold   = float(input(f"Comparison threshold (default={THRESHOLD_DEFAULT}):\n==> ").strip() or THRESHOLD_DEFAULT)

    # Start FFmpeg
    ffmpeg_proc = start_ffmpeg(input_file, sample_rate, cropbox)
    assert ffmpeg_proc.stdout is not None
    assert ffmpeg_proc.stderr is not None
    os.makedirs(path_out, exist_ok=True)

    w, h = map(int, cropbox.split(":")[:2])
    frame_size = w * h * 1
    frame_index = 0
    previous_frame: bytes | None = None

    while True:
        frame_data = ffmpeg_proc.stdout.read(frame_size)
        if len(frame_data) < frame_size:
            print(f"End of stream, expected {frame_size} bytes, got {len(frame_data)}")
            break

        if previous_frame and not are_images_equal(previous_frame, frame_data, threshold):
            timestamp = frame_index / sample_rate
            filename = f"{path_out}/timestamp {timestamp:06.1f}.jpg"
            try:
                PIL.Image.frombytes("L", (w, h), frame_data).save(filename)
            except Exception as e:
                print("ERROR:", e)
                break
            print(f"Saved - frame {frame_index} - timestamp {format_seconds(timestamp)} - {filename}")

        previous_frame = frame_data
        frame_index += 1

    # Flush any remaining stderr stuff to console
    print()
    print("Remainder stderr output:")
    print("="*32)
    for line in ffmpeg_proc.stderr:
        print(line.decode(errors="ignore"), end="")
    print("="*32)
    ffmpeg_proc.stdout.close()
    ffmpeg_proc.stderr.close()
    ffmpeg_proc.kill()
