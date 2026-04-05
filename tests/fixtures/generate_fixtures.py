"""Generate test audio fixtures using ffmpeg."""
import subprocess
import os

FIXTURES_DIR = os.path.dirname(__file__)


def generate_silence(output_path: str, duration: float):
    """Generate a silent audio file."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=16000:cl=mono",
            "-t", str(duration),
            "-c:a", "pcm_s16le",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


def generate_speech(output_path: str, duration: float):
    """Generate a speech-like audio file (sine wave as placeholder)."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration}:sample_rate=16000",
            "-c:a", "pcm_s16le",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


if __name__ == "__main__":
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    print("Generating 5s silence...")
    generate_silence(os.path.join(FIXTURES_DIR, "5s_silence.wav"), 5)

    print("Generating 5s speech-like audio...")
    generate_speech(os.path.join(FIXTURES_DIR, "5s_speech.wav"), 5)

    print("Generating 120s speech-like audio...")
    generate_speech(os.path.join(FIXTURES_DIR, "120s_speech.wav"), 120)

    print("Done!")