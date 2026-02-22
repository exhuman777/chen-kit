#!/usr/bin/env python3
"""
CHEN-KIT Ingest CLI
Standalone tool for processing raw content into kitchen structure

Usage:
  ingest.py audio <file>           # Transcribe & process voice memo
  ingest.py text <file>            # Process text file
  ingest.py url <url>              # Scrape & process URL
  ingest.py inbox                  # Process all inbox items
  ingest.py inbox --auto-save      # Auto-save valid items
  ingest.py blueprint --generate   # Interactive blueprint creation
  ingest.py watch                  # Watch inbox folder (background daemon)
  ingest.py status                 # Show inbox status
"""

import argparse
import sys
from pathlib import Path

from ingest_core import IngestProcessor, Transcriber, URLScraper, Blueprint

LOGO = r'''
┌─┐┬ ┬┌─┐┌┐┌   ┬┌─┬┌┬┐
│  ├─┤├┤ │││───├┴┐│ │   INGEST
└─┘┴ ┴└─┘┘└┘   ┴ ┴┴ ┴   raw notes → structured markdown
'''


def print_result(result):
    """Pretty print processing result"""
    if 'error' in result:
        print(f"\n[ERROR] {result.get('file', result.get('url', 'unknown'))}")
        print(f"  {result['error']}")
        return

    status = 'OK' if result['valid'] else 'NEEDS REVIEW'
    conf = f"{result['confidence']:.0%}"

    print(f"\n{'='*60}")
    print(f"Blueprint: {result['blueprint']} (confidence: {conf})")
    print(f"Target: {result['target_folder']}/")
    print(f"Filename: {result['suggested_filename']}.md")
    print(f"Status: {status}")

    if result['errors']:
        print(f"\nValidation issues:")
        for e in result['errors']:
            print(f"  - {e}")

    print(f"\n{'='*60}")
    print("FORMATTED OUTPUT:")
    print(f"{'='*60}")
    print(result['formatted'][:2000])
    if len(result['formatted']) > 2000:
        print(f"\n... ({len(result['formatted'])} chars total)")


def cmd_audio(args):
    """Handle audio transcription + processing"""
    audio_path = Path(args.file)
    if not audio_path.exists():
        print(f"[!] File not found: {args.file}")
        sys.exit(1)

    if not Transcriber.is_available():
        print("[!] Whisper not available")
        print("    Install whisper-cli and download model to ~/whisper-models/")
        sys.exit(1)

    print(f"[*] Transcribing: {audio_path.name}")
    processor = IngestProcessor(Path(__file__).parent)

    try:
        result = processor.process_audio(audio_path)
        print_result(result)

        if args.save:
            filename = args.filename or result['suggested_filename']
            path = processor.save(result, filename)
            print(f"\n[+] Saved: {path}")
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


def cmd_text(args):
    """Handle text file or stdin processing"""
    if args.file == '-':
        text = sys.stdin.read()
    else:
        text_path = Path(args.file)
        if not text_path.exists():
            print(f"[!] File not found: {args.file}")
            sys.exit(1)
        text = text_path.read_text(encoding='utf-8')

    print(f"[*] Processing text ({len(text)} chars)")
    processor = IngestProcessor(Path(__file__).parent)

    result = processor.process_text(text, source_file=args.file)
    print_result(result)

    if args.save:
        filename = args.filename or result['suggested_filename']
        path = processor.save(result, filename)
        print(f"\n[+] Saved: {path}")


def cmd_url(args):
    """Handle URL scraping + processing"""
    if not URLScraper.is_available():
        print("[!] URL scraping not available")
        print("    Install: pip install requests beautifulsoup4")
        sys.exit(1)

    print(f"[*] Scraping: {args.url}")
    processor = IngestProcessor(Path(__file__).parent)

    try:
        result = processor.process_url(args.url)
        print_result(result)

        if args.save:
            filename = args.filename or result['suggested_filename']
            path = processor.save(result, filename)
            print(f"\n[+] Saved: {path}")
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


def cmd_inbox(args):
    """Process all inbox items"""
    processor = IngestProcessor(Path(__file__).parent)

    # Show current inbox status
    items = processor.list_inbox()
    total = sum(len(v) for v in items.values())

    if total == 0:
        print("[*] Inbox is empty")
        print(f"    Add files to: {processor.inbox}/")
        return

    print(f"[*] Processing {total} items from inbox...")

    results = processor.process_inbox(auto_save=args.auto_save)

    # Summary
    valid = sum(1 for r in results if r.get('valid'))
    invalid = sum(1 for r in results if not r.get('valid') and 'error' not in r)
    errors = sum(1 for r in results if 'error' in r)

    print(f"\n{'='*60}")
    print(f"RESULTS: {valid} valid, {invalid} need review, {errors} errors")
    print(f"{'='*60}")

    for r in results:
        if 'error' in r:
            print(f"  [ERROR] {r.get('file', r.get('url', '?'))}: {r['error']}")
        else:
            status = 'OK' if r['valid'] else 'REVIEW'
            print(f"  [{status}] {r['blueprint']}: {r['suggested_filename']}")

    if args.auto_save:
        print(f"\n[+] Auto-saved {valid} valid items")


def cmd_status(args):
    """Show inbox status"""
    processor = IngestProcessor(Path(__file__).parent)
    items = processor.list_inbox()

    print(f"\n{'='*60}")
    print("INBOX STATUS")
    print(f"{'='*60}")

    print(f"\nAudio ({len(items['audio'])} files):")
    for f in items['audio'][:10]:
        print(f"  - {f}")
    if len(items['audio']) > 10:
        print(f"  ... and {len(items['audio']) - 10} more")

    print(f"\nText ({len(items['text'])} files):")
    for f in items['text'][:10]:
        print(f"  - {f}")
    if len(items['text']) > 10:
        print(f"  ... and {len(items['text']) - 10} more")

    print(f"\nURLs ({len(items['urls'])} queued):")
    for u in items['urls'][:10]:
        print(f"  - {u}")
    if len(items['urls']) > 10:
        print(f"  ... and {len(items['urls']) - 10} more")

    total = sum(len(v) for v in items.values())
    print(f"\nTotal: {total} items pending")


def cmd_blueprint(args):
    """Interactive blueprint generation"""
    print("\nBlueprint Generator - Interactive Mode")
    print("-" * 40)

    name = input("Blueprint name (e.g. 'project', 'notes'): ").strip()
    if not name:
        print("[!] Name required")
        return

    folder = input(f"Target folder [{name}s]: ").strip() or f"{name}s"

    print("\nClassification keywords (comma-separated):")
    keywords = input("> ").strip()
    if not keywords:
        keywords = name

    print("\nRequired sections (empty line to finish):")
    sections = []
    while True:
        s = input("  Section name: ").strip()
        if not s:
            break
        sections.append(s)

    if not sections:
        sections = ['Content']

    # Generate blueprint
    kw_list = ', '.join(k.strip() for k in keywords.split(','))
    blueprint_content = f"""# Blueprint: {name.title()}
target_folder: {folder}
classification_keywords: [{kw_list}]
embedding_weight: 0.7

## Required Fields
- title: "# [Title]"

## Required Sections
"""
    for s in sections:
        blueprint_content += f"""### {s}
format: "- [ ] [item]"
min_items: 1

"""

    blueprint_content += """## Example
```markdown
# Example Title

"""
    for s in sections:
        blueprint_content += f"""## {s}
- [ ] Item 1
- [ ] Item 2

"""
    blueprint_content += "```\n"

    # Preview
    print(f"\n{'='*60}")
    print("BLUEPRINT PREVIEW:")
    print(f"{'='*60}")
    print(blueprint_content)

    # Save
    bp_dir = Path(__file__).parent / "blueprints"
    bp_dir.mkdir(exist_ok=True)
    bp_path = bp_dir / f"{name}.blueprint.md"

    if input(f"\nSave to {bp_path}? (y/n): ").lower() == 'y':
        bp_path.write_text(blueprint_content, encoding='utf-8')
        print(f"[+] Saved: {bp_path}")

        # Create target folder
        target_dir = Path(__file__).parent / folder
        target_dir.mkdir(exist_ok=True)
        print(f"[+] Created: {target_dir}/")


def cmd_watch(args):
    """Watch inbox folder for new files"""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("[!] Watchdog not available")
        print("    Install: pip install watchdog")
        sys.exit(1)

    class InboxHandler(FileSystemEventHandler):
        def __init__(self):
            self.processor = IngestProcessor(Path(__file__).parent)

        def on_created(self, event):
            if event.is_directory:
                return

            path = Path(event.src_path)
            print(f"\n[*] New file: {path.name}")

            try:
                if path.suffix.lower() in {'.mp3', '.wav', '.m4a', '.ogg'}:
                    result = self.processor.process_audio(path)
                elif path.suffix.lower() == '.txt':
                    result = self.processor.process_text(path.read_text())
                else:
                    print(f"    Skipped (unsupported type)")
                    return

                status = 'OK' if result['valid'] else 'REVIEW'
                print(f"    [{status}] {result['blueprint']}: {result['suggested_filename']}")

                if args.auto_save and result['valid']:
                    saved = self.processor.save(result)
                    print(f"    [+] Saved: {saved}")

            except Exception as e:
                print(f"    [!] Error: {e}")

    inbox = Path(__file__).parent / "inbox"
    inbox.mkdir(exist_ok=True)

    observer = Observer()
    observer.schedule(InboxHandler(), str(inbox), recursive=True)
    observer.start()

    print(f"[*] Watching: {inbox}")
    print("[*] Press Ctrl+C to stop\n")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
        observer.stop()
    observer.join()


def main():
    print(LOGO)

    parser = argparse.ArgumentParser(
        description="CHEN-KIT Ingest CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ingest.py audio voice_memo.m4a --save
  ingest.py text notes.txt --save --filename "my-recipe"
  ingest.py url https://example.substack.com/p/article
  ingest.py inbox --auto-save
  ingest.py watch --auto-save
"""
    )
    subparsers = parser.add_subparsers(dest="command")

    # audio
    p_audio = subparsers.add_parser("audio", help="Transcribe voice memo")
    p_audio.add_argument("file", help="Audio file path")
    p_audio.add_argument("--save", "-s", action="store_true", help="Save to target folder")
    p_audio.add_argument("--filename", "-f", help="Override filename")

    # text
    p_text = subparsers.add_parser("text", help="Process text file (use - for stdin)")
    p_text.add_argument("file", help="Text file path or - for stdin")
    p_text.add_argument("--save", "-s", action="store_true")
    p_text.add_argument("--filename", "-f")

    # url
    p_url = subparsers.add_parser("url", help="Scrape URL")
    p_url.add_argument("url", help="URL to scrape")
    p_url.add_argument("--save", "-s", action="store_true")
    p_url.add_argument("--filename", "-f")

    # inbox
    p_inbox = subparsers.add_parser("inbox", help="Process all inbox items")
    p_inbox.add_argument("--auto-save", "-a", action="store_true", help="Auto-save valid items")

    # status
    subparsers.add_parser("status", help="Show inbox status")

    # blueprint
    p_bp = subparsers.add_parser("blueprint", help="Create new blueprint interactively")
    p_bp.add_argument("--generate", "-g", action="store_true", help="Generate blueprint")

    # watch
    p_watch = subparsers.add_parser("watch", help="Watch inbox folder")
    p_watch.add_argument("--auto-save", "-a", action="store_true")

    args = parser.parse_args()

    commands = {
        "audio": cmd_audio,
        "text": cmd_text,
        "url": cmd_url,
        "inbox": cmd_inbox,
        "status": cmd_status,
        "blueprint": cmd_blueprint,
        "watch": cmd_watch,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
