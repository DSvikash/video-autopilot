import json
import click
from pathlib import Path
from src.pipeline import VideoAutopilotPipeline
from src.queue.topic_queue import TopicQueue
from src.studio.scriptwriter import DocumentaryScriptwriter
from src.studio.studio_composer import StudioComposer

@click.group()
def cli():
    """Video Autopilot: High-Value Long-Form Tech Documentaries & YouTube Automation"""
    pass

@cli.command("documentary")
@click.option("--topic", "-t", required=True, help="Topic for the in-depth tech documentary")
@click.option("--upload/--no-upload", default=True, show_default=True, help="Whether to upload to YouTube")
def documentary(topic: str, upload: bool):
    """
    Produce a serious, high-production 1080p tech documentary
    modeled on top tech creators (Vaibhav Sisinty / Matt Wolfe).
    Features: Multi-chapter breakdowns, sleek dark-mode slide decks,
    expert narration, verified benchmarks, and automatic YouTube timestamps.
    """
    click.echo(f"🎬 Initializing Studio Documentary Production for: '{topic}'")
    writer = DocumentaryScriptwriter()
    script = writer.write_script(topic)
    
    click.echo(f"📋 Script Prepared: '{script.title}' ({len(script.chapters)} Chapters)")
    composer = StudioComposer()
    result = composer.produce_documentary(script, upload_to_youtube=upload)
    
    click.echo("\n" + "=" * 60)
    click.echo("✅ High-Production Documentary Production Complete!")
    click.echo(f"📁 Video Path: {result['video_path']}")
    click.echo(f"⏱️ Duration: {result['duration']:.1f}s")
    click.echo(f"🎬 Title: {result['title']}")
    click.echo("\n📌 YouTube Timestamps:")
    for ch in result["chapters"]:
        click.echo(f"  {ch['timestamp_str']} - {ch['title']}")
        
    if result.get("upload"):
        up = result["upload"]
        click.echo(f"\n📡 YouTube Status: {up.get('status')}")
        if up.get("url"):
            click.echo(f"🔗 YouTube URL: {up.get('url')}")
    click.echo("=" * 60)

@cli.command()
@click.option("--topic", "-t", required=True, help="Topic for the video")
@click.option(
    "--genre", "-g",
    type=click.Choice(["explainer", "action", "drama", "thriller", "motivational", "mystery", "comedy", "Let the director decide"]),
    default="explainer",
    show_default=True,
    help="Narrative genre"
)
@click.option(
    "--format", "-f",
    "format_type",
    type=click.Choice(["short", "long"]),
    default="short",
    show_default=True,
    help="Video format: short (9:16) or long (16:9)"
)
@click.option(
    "--upload/--no-upload",
    default=True,
    show_default=True,
    help="Whether to upload to YouTube automatically"
)
def generate(topic: str, genre: str, format_type: str, upload: bool):
    """Generate a single video autonomously with Director scripting & Ken Burns motion."""
    click.echo(f"🚀 Starting Video Pipeline for: '{topic}' [Genre: {genre}, Format: {format_type.upper()}]")
    pipeline = VideoAutopilotPipeline()
    result = pipeline.run(topic=topic, format_type=format_type, genre=genre, upload_to_youtube=upload)
    click.echo("✅ Production Complete!")
    click.echo(f"📁 Video Path: {result['video_path']}")
    click.echo(f"🎬 Title: {result['title']}")
    if result.get("upload"):
        up = result["upload"]
        click.echo(f"📡 YouTube Status: {up.get('status')}")
        if up.get("url"):
            click.echo(f"🔗 YouTube URL: {up.get('url')}")

@cli.command()
@click.option("--topic", "-t", required=True, help="Topic to enqueue")
@click.option(
    "--genre", "-g",
    type=click.Choice(["explainer", "action", "drama", "thriller", "motivational", "mystery", "comedy", "Let the director decide"]),
    default="explainer"
)
def enqueue(topic: str, genre: str):
    """Add a new topic to the processing queue."""
    tq = TopicQueue()
    row_id = tq.enqueue(topic=topic, genre=genre, source="cli")
    click.echo(f"📥 Enqueued topic #{row_id}: '{topic}' [{genre}]")

@cli.command("list-queue")
def list_queue():
    """List all topics in the queue with their current status."""
    tq = TopicQueue()
    items = tq.list_queue()
    if not items:
        click.echo("Queue is empty.")
        return
    click.echo(f"\n{'ID':<5} {'STATUS':<18} {'GENRE':<12} {'TOPIC':<35} {'YOUTUBE ID'}")
    click.echo("-" * 80)
    for it in items:
        click.echo(f"{it['id']:<5} {it['status']:<18} {it['genre']:<12} {it['topic'][:32]:<35} {it.get('youtube_video_id', '')}")

@cli.command("process-queue")
@click.option("--max-items", "-m", default=1, type=int, help="Maximum number of queued topics to process")
def process_queue(max_items: int):
    """Process pending topics from the queue sequentially."""
    tq = TopicQueue()
    pipeline = VideoAutopilotPipeline()
    processed = 0

    while processed < max_items:
        job = tq.get_next_queued()
        if not job:
            click.echo("🏁 No more queued topics to process.")
            break

        row_id = job["id"]
        topic = job["topic"]
        genre = job.get("genre", "explainer")
        click.echo(f"\n▶️ Processing Job #{row_id}: '{topic}' [{genre}]...")

        tq.mark_processing(row_id)
        try:
            res = pipeline.run(topic=topic, format_type="short", genre=genre, upload_to_youtube=True)
            video_id = res.get("upload", {}).get("video_id", "")
            tq.mark_uploaded(row_id, res["title"], video_id, res["video_path"])
            click.echo(f"✅ Job #{row_id} uploaded successfully! YouTube ID: {video_id}")
            processed += 1
        except Exception as e:
            tq.mark_failed(row_id, str(e))
            click.echo(f"❌ Job #{row_id} failed: {e}")

if __name__ == "__main__":
    cli()
