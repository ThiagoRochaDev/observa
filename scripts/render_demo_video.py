from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRAMES = ROOT / "docs" / "demo" / "frames"
DEFAULT_OUTPUT = ROOT / "docs" / "demo" / "observa-complete-walkthrough.mp4"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def render(frames_dir: Path, output: Path, *, fps: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    frames = sorted(frames_dir.glob("*.png"))
    if not frames:
        raise RuntimeError(f"No PNG frames found in {frames_dir}")

    render_dir = output.parent / ".demo-render"
    if render_dir.exists():
        shutil.rmtree(render_dir)
    render_dir.mkdir(parents=True)
    segments: list[Path] = []
    try:
        for index, frame in enumerate(frames):
            segment = render_dir / f"{index:03d}.mp4"
            duration = 4.2 if any(key in frame.name for key in ("title", "automation", "finish")) else 3.2
            zoom_frames = round(duration * fps)
            filter_chain = (
                "scale=1440:900:force_original_aspect_ratio=decrease,"
                "pad=1440:900:(ow-iw)/2:(oh-ih)/2:color=#03070c,"
                f"zoompan=z='min(zoom+0.00016,1.018)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={zoom_frames}:s=1440x900:fps={fps},"
                "format=yuv420p"
            )
            run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(frame),
                    "-vf",
                    filter_chain,
                    "-t",
                    str(duration),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "19",
                    "-movflags",
                    "+faststart",
                    str(segment),
                ]
            )
            segments.append(segment)

        concat_file = render_dir / "segments.txt"
        concat_file.write_text(
            "\n".join(f"file '{segment.as_posix()}'" for segment in segments),
            encoding="utf-8",
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
    finally:
        shutil.rmtree(render_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Observa product demo video")
    parser.add_argument("--frames", type=Path, default=DEFAULT_FRAMES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    render(args.frames.resolve(), args.output.resolve(), fps=args.fps)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
