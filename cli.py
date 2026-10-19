import json
import click
from pathlib import Path
from src.pipeline import VideoAutopilotPipeline

@click.group()
def cli():
    """Video Autopilot: Autonomous End-to-End AI Video Production & YouTube Publisher"""
    pass

@cli.command()
@click.option("--topic", "-t", required=True, help="Topic for the video")
@click.option(
    "--format", "-f",
    "format_type",
    type=click.Choice(["short", "long"]),
    default="short",
    show_default=True,
    help="Video format: short (9:16 vertical) or long (16:9 horizontal)"
)
@click.option(
    "--upload/--no-upload",
    default=True,
    show_default=True,
    help="Whether to upload to YouTube automatically"
)
def generate(topic: str, format_type: str, upload: bool):
    """Generate a single video autonomously from a topic."""
    click.echo(f"🚀 Starting Video Autopilot for topic: '{topic}' [{format_type.upper()}]")
    pipeline = VideoAutopilotPipeline()
    result = pipeline.run(topic=topic, format_type=format_type, upload_to_youtube=upload)
    click.echo("✅ Video Production Complete!")
    click.echo(f"📁 Video Path: {result['video_path']}")
    click.echo(f"🎬 Title: {result['title']}")
    if result.get("upload"):
        up = result["upload"]
        click.echo(f"📡 YouTube Status: {up.get('status')} | {up.get('message', '')}")
        if up.get("url"):
            click.echo(f"🔗 YouTube URL: {up.get('url')}")

@cli.command()
@click.option("--manifest", "-m", required=True, type=click.Path(exists=True), help="JSON or JSONL file with topics list")
@click.option("--format", "-f", "format_type", type=click.Choice(["short", "long"]), default="short")
def batch(manifest: str, format_type: str):
    """Batch generate multiple videos from a JSON manifest file."""
    path = Path(manifest)
    with open(path, "r", encoding="utf-8") as f:
        if path.suffix == ".jsonl":
            topics = [json.loads(line) for line in f if line.strip()]
        else:
            topics = json.load(f)

    click.echo(f"📋 Starting batch processing for {len(topics)} topics...")
    pipeline = VideoAutopilotPipeline()
    for i, item in enumerate(topics, 1):
        topic = item if isinstance(item, str) else item.get("topic")
        fmt = item.get("format", format_type) if isinstance(item, dict) else format_type
        click.echo(f"\n--- [{i}/{len(topics)}] Processing: '{topic}' [{fmt}] ---")
        try:
            res = pipeline.run(topic=topic, format_type=fmt, upload_to_youtube=True)
            click.echo(f"✅ Success: {res['title']} -> {res['video_path']}")
        except Exception as e:
            click.echo(f"❌ Failed for topic '{topic}': {e}")

if __name__ == "__main__":
    cli()
