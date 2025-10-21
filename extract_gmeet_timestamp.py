import subprocess
import PIL.Image

CROPBOX_DEFAULT = "100:40:71:1310"
SAMPLE_RATE_DEFAULT = 1
PATH_OUT = "output/"



def are_images_equal(frame1: bytes, frame2: bytes, threshold: float=0.25) -> bool:
    if len(frame1) != len(frame2):
        raise ValueError("Must be equal length.")

    for b1, b2 in zip(frame1, frame2):
        b1_linear = (b1 / 255) ** 2
        b2_linear = (b2 / 255) ** 2
        if abs(b1_linear - b2_linear) >= threshold:
            return False

    return True

def format_seconds(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"

# Inputs
cropbox = input(f"Cropbox (default={CROPBOX_DEFAULT}): ").strip() or CROPBOX_DEFAULT
sample_rate = float(input(f"Sample rate (default={SAMPLE_RATE_DEFAULT}): ").strip() or SAMPLE_RATE_DEFAULT)
input_file = input("Input video file path: ").strip()

# Invoke FFmpeg
w, h = map(int, cropbox.split(":")[:2])
ffmpeg_cmd = [
    "ffmpeg",
    "-i", input_file,
    "-vf", f"fps={sample_rate},crop={cropbox}",
    "-f", "rawvideo",
    # "-pix_fmt", "rgb24",
    "-pix_fmt", "gray",
    "-hide_banner",
    "-"
]
ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if not ffmpeg_proc.stdout or not ffmpeg_proc.stderr:
    raise ValueError()

frame_size = w * h * 1
frame_index = 0
previous_frame: bytes | None = None

while True:
    frame_data = ffmpeg_proc.stdout.read(frame_size)
    if len(frame_data) < frame_size:
        print(f"End of stream, expected {frame_size} bytes, got {len(frame_data)}")
        break

    if previous_frame and not are_images_equal(previous_frame, frame_data):
        timestamp = frame_index / sample_rate
        filename = f"{PATH_OUT}/timestamp {timestamp:06.1f}.jpg"
        try:
            PIL.Image.frombytes("L", (w, h), frame_data).save(filename)
        except Exception as e:
            print("ERROR:", e)
            break
        print(f"Saved - frame {frame_index} - timestamp {format_seconds(timestamp)} - {filename}")

    previous_frame = frame_data
    frame_index += 1

# Flush any remaining stderr output to console
for line in ffmpeg_proc.stderr:
    print(line.decode(errors="ignore"), end="")

ffmpeg_proc.stdout.close()
ffmpeg_proc.stderr.close()
ffmpeg_proc.kill()
