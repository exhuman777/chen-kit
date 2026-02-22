#!/usr/bin/env python3
"""
CHEN-KIT Ingest Core
Shared logic for CLI and dashboard ingest
"""
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPE_AVAILABLE = True
except ImportError:
    SCRAPE_AVAILABLE = False
    BeautifulSoup = None  # type: ignore


class Blueprint:
    """Parse and apply .blueprint.md templates"""

    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem.replace('.blueprint', '')
        self.target_folder = ""
        self.keywords: List[str] = []
        self.embedding_weight = 0.7
        self.required_fields: Dict[str, str] = {}
        self.optional_fields: Dict[str, str] = {}
        self.required_sections: Dict[str, dict] = {}
        self.optional_sections: List[str] = []
        self.validation_rules: List[str] = []
        self.example = ""
        self._parse()

    def _parse(self):
        """Parse blueprint markdown into structured config"""
        content = self.path.read_text(encoding='utf-8')
        lines = content.split('\n')

        current_section = None
        current_subsection = None

        for line in lines:
            line_stripped = line.strip()

            # Header metadata
            if line_stripped.startswith('target_folder:'):
                self.target_folder = line_stripped.split(':', 1)[1].strip()
            elif line_stripped.startswith('classification_keywords:'):
                kw_str = line_stripped.split(':', 1)[1].strip()
                kw_str = kw_str.strip('[]')
                self.keywords = [k.strip() for k in kw_str.split(',')]
            elif line_stripped.startswith('embedding_weight:'):
                self.embedding_weight = float(line_stripped.split(':', 1)[1].strip())

            # Section headers
            elif line_stripped.startswith('## Required Fields'):
                current_section = 'required_fields'
            elif line_stripped.startswith('## Optional Fields'):
                current_section = 'optional_fields'
            elif line_stripped.startswith('## Required Sections'):
                current_section = 'required_sections'
            elif line_stripped.startswith('## Optional Sections'):
                current_section = 'optional_sections'
            elif line_stripped.startswith('## Validation'):
                current_section = 'validation'
            elif line_stripped.startswith('## Example'):
                current_section = 'example'

            # Subsection (### Name)
            elif line_stripped.startswith('### ') and current_section == 'required_sections':
                current_subsection = line_stripped[4:].strip()
                self.required_sections[current_subsection] = {}

            # Content parsing
            elif current_section == 'required_fields' and line_stripped.startswith('- '):
                parts = line_stripped[2:].split(':', 1)
                if len(parts) == 2:
                    self.required_fields[parts[0].strip()] = parts[1].strip().strip('"')

            elif current_section == 'optional_fields' and line_stripped.startswith('- '):
                parts = line_stripped[2:].split(':', 1)
                if len(parts) == 2:
                    self.optional_fields[parts[0].strip()] = parts[1].strip().strip('"')

            elif current_section == 'required_sections' and current_subsection:
                if line_stripped.startswith('format:'):
                    self.required_sections[current_subsection]['format'] = line_stripped.split(':', 1)[1].strip().strip('"')
                elif line_stripped.startswith('min_items:'):
                    self.required_sections[current_subsection]['min_items'] = int(line_stripped.split(':', 1)[1].strip())

            elif current_section == 'optional_sections' and line_stripped.startswith('- '):
                self.optional_sections.append(line_stripped[2:].strip())

            elif current_section == 'validation' and line_stripped.startswith('- '):
                self.validation_rules.append(line_stripped[2:].strip())

            elif current_section == 'example':
                self.example += line + '\n'

    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """Check if content conforms to blueprint. Returns (valid, errors)"""
        errors = []

        # Check required fields
        for field, pattern in self.required_fields.items():
            if field == 'title':
                if not re.search(r'^#\s+.+', content, re.MULTILINE):
                    errors.append(f"Missing title (expected: {pattern})")
            elif not re.search(f'^{field}:', content, re.MULTILINE | re.IGNORECASE):
                errors.append(f"Missing field: {field}")

        # Check required sections
        for section, rules in self.required_sections.items():
            section_pattern = rf'^##\s+{re.escape(section)}'
            if not re.search(section_pattern, content, re.MULTILINE | re.IGNORECASE):
                errors.append(f"Missing section: {section}")
            else:
                # Check min_items
                min_items = rules.get('min_items', 0)
                if min_items > 0:
                    # Count items after section header
                    match = re.search(section_pattern + r'(.+?)(?=^##|\Z)', content, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                    if match:
                        section_content = match.group(1)
                        item_count = len(re.findall(r'^-\s*\[', section_content, re.MULTILINE))
                        if item_count < min_items:
                            errors.append(f"Section '{section}' needs at least {min_items} items, found {item_count}")

        return len(errors) == 0, errors

    def get_prompt_context(self) -> str:
        """Generate LLM prompt context from blueprint"""
        ctx = f"TARGET: {self.target_folder}/\n\n"

        ctx += "REQUIRED FIELDS:\n"
        for field, pattern in self.required_fields.items():
            ctx += f"  - {field}: {pattern}\n"

        if self.optional_fields:
            ctx += "\nOPTIONAL FIELDS:\n"
            for field, pattern in self.optional_fields.items():
                ctx += f"  - {field}: {pattern}\n"

        ctx += "\nREQUIRED SECTIONS:\n"
        for section, rules in self.required_sections.items():
            fmt = rules.get('format', 'free text')
            ctx += f"  ## {section}\n    format: {fmt}\n"

        if self.example:
            ctx += f"\nEXAMPLE:\n{self.example}"

        return ctx


class BlueprintManager:
    """Load and match blueprints to content"""

    def __init__(self, blueprints_dir: Path):
        self.blueprints: Dict[str, Blueprint] = {}
        self.model = None
        self.blueprint_embeddings = {}
        self._load_all(blueprints_dir)

    def _load_all(self, blueprints_dir: Path):
        """Load all blueprint files"""
        if not blueprints_dir.exists():
            return

        for bp_file in blueprints_dir.glob('*.blueprint.md'):
            bp = Blueprint(bp_file)
            self.blueprints[bp.name] = bp

        # Pre-compute embeddings for keywords
        if SEMANTIC_AVAILABLE and self.blueprints:
            try:
                self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
                for name, bp in self.blueprints.items():
                    kw_text = ' '.join(bp.keywords)
                    self.blueprint_embeddings[name] = self.model.encode(kw_text)
            except Exception:
                self.model = None

    def classify(self, text: str) -> Tuple[str, float]:
        """
        Classify text to best-matching blueprint.
        Returns (blueprint_name, confidence_score)
        """
        if not self.blueprints:
            return ('transcripts', 0.5)

        text_lower = text.lower()
        scores = {}

        # Keyword matching
        for name, bp in self.blueprints.items():
            keyword_hits = sum(1 for kw in bp.keywords if kw.lower() in text_lower)
            keyword_score = keyword_hits / max(len(bp.keywords), 1)
            scores[name] = keyword_score * (1 - bp.embedding_weight)

        # Semantic matching
        if self.model and self.blueprint_embeddings:
            text_embed = self.model.encode(text[:1000])  # First 1000 chars
            for name, bp_embed in self.blueprint_embeddings.items():
                similarity = float(np.dot(text_embed, bp_embed) / (np.linalg.norm(text_embed) * np.linalg.norm(bp_embed)))
                bp = self.blueprints[name]
                scores[name] = scores.get(name, 0) + similarity * bp.embedding_weight

        # Find best match
        if scores:
            best = max(scores, key=scores.get)
            return (best, scores[best])

        return ('transcripts', 0.5)

    def get_blueprint(self, name: str) -> Optional[Blueprint]:
        return self.blueprints.get(name)


class Transcriber:
    """Audio transcription via whisper-cli"""

    WHISPER_PATH = "/opt/homebrew/bin/whisper-cli"
    FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"
    MODEL_PATH = Path.home() / "whisper-models/ggml-medium.bin"

    @classmethod
    def transcribe(cls, audio_path: Path, language: str = "pl") -> str:
        """Transcribe audio file to text"""
        if not cls.is_available():
            raise RuntimeError("Whisper not available")

        audio_path = Path(audio_path)

        # Convert to wav if needed
        if audio_path.suffix.lower() != '.wav':
            wav_path = Path(tempfile.gettempdir()) / f"{audio_path.stem}.wav"
            subprocess.run([
                cls.FFMPEG_PATH, '-y', '-i', str(audio_path),
                '-ar', '16000', '-ac', '1', str(wav_path)
            ], capture_output=True, check=True)
        else:
            wav_path = audio_path

        # Run whisper
        result = subprocess.run([
            cls.WHISPER_PATH,
            '-m', str(cls.MODEL_PATH),
            '-l', language,
            '-f', str(wav_path)
        ], capture_output=True, text=True, timeout=300)

        # Clean up temp wav
        if wav_path != audio_path and wav_path.exists():
            wav_path.unlink()

        return result.stdout.strip()

    @classmethod
    def is_available(cls) -> bool:
        return Path(cls.WHISPER_PATH).exists() and cls.MODEL_PATH.exists()


class URLScraper:
    """Fetch and extract content from URLs"""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    @classmethod
    def scrape(cls, url: str) -> Tuple[str, dict]:
        """Scrape URL, return (text_content, metadata)"""
        if not SCRAPE_AVAILABLE:
            raise RuntimeError("Install: pip install requests beautifulsoup4")

        from urllib.parse import urlparse
        resp = requests.get(url, headers=cls.HEADERS, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        domain = urlparse(url).netloc

        if 'substack.com' in domain:
            return cls._scrape_substack(soup, url)
        elif 'medium.com' in domain:
            return cls._scrape_medium(soup, url)
        else:
            return cls._scrape_generic(soup, url)

    @classmethod
    def _scrape_substack(cls, soup: BeautifulSoup, url: str) -> Tuple[str, dict]:
        """Extract Substack article content"""
        title = soup.select_one('h1.post-title')
        title_text = title.get_text(strip=True) if title else ""

        author = soup.select_one('.author-name')
        author_text = author.get_text(strip=True) if author else ""

        date = soup.select_one('time')
        date_text = date.get('datetime', '') if date else ""

        body = soup.select_one('.body.markup') or soup.select_one('article')

        paragraphs = []
        if body:
            for elem in body.find_all(['p', 'h2', 'h3', 'li']):
                text = elem.get_text(strip=True)
                if elem.name.startswith('h'):
                    paragraphs.append(f"\n## {text}\n")
                elif elem.name == 'li':
                    paragraphs.append(f"- {text}")
                else:
                    paragraphs.append(text)

        content = '\n\n'.join(paragraphs)

        return content, {
            'title': title_text,
            'author': author_text,
            'date': date_text,
            'source_url': url,
            'domain': 'substack'
        }

    @classmethod
    def _scrape_medium(cls, soup: BeautifulSoup, url: str) -> Tuple[str, dict]:
        """Extract Medium article content"""
        title = soup.select_one('h1')
        title_text = title.get_text(strip=True) if title else ""

        article = soup.select_one('article')
        paragraphs = []
        if article:
            for elem in article.find_all(['p', 'h1', 'h2', 'h3', 'li']):
                text = elem.get_text(strip=True)
                if elem.name.startswith('h') and elem.name != 'h1':
                    paragraphs.append(f"\n## {text}\n")
                elif elem.name == 'li':
                    paragraphs.append(f"- {text}")
                elif text:
                    paragraphs.append(text)

        content = '\n\n'.join(paragraphs)

        return content, {
            'title': title_text,
            'source_url': url,
            'domain': 'medium'
        }

    @classmethod
    def _scrape_generic(cls, soup: BeautifulSoup, url: str) -> Tuple[str, dict]:
        """Generic article extraction"""
        from urllib.parse import urlparse

        for tag in soup(['nav', 'footer', 'aside', 'script', 'style', 'header']):
            tag.decompose()

        article = (
            soup.select_one('article') or
            soup.select_one('.post-content') or
            soup.select_one('.entry-content') or
            soup.select_one('main') or
            soup.select_one('.content')
        )

        if article:
            content = article.get_text(separator='\n\n', strip=True)
        else:
            content = soup.get_text(separator='\n\n', strip=True)

        title = soup.select_one('h1')
        title_text = title.get_text(strip=True) if title else ""

        return content, {
            'title': title_text,
            'source_url': url,
            'domain': urlparse(url).netloc
        }

    @classmethod
    def is_available(cls) -> bool:
        return SCRAPE_AVAILABLE


class IngestProcessor:
    """Main processing pipeline"""

    def __init__(self, kitchen_root: Path):
        self.root = Path(kitchen_root)
        self.blueprints = BlueprintManager(self.root / "blueprints")
        self.inbox = self.root / "inbox"

    def process_audio(self, path: Path) -> Dict:
        """Audio -> transcribe -> classify -> transform"""
        transcript = Transcriber.transcribe(path)
        result = self.process_text(transcript, source_file=str(path.name), source_type='audio')
        return result

    def process_url(self, url: str) -> Dict:
        """URL -> scrape -> classify -> transform"""
        content, meta = URLScraper.scrape(url)
        result = self.process_text(content, source_url=url, source_type='url')
        result['meta'].update(meta)
        return result

    def process_text(self, text: str, **meta) -> Dict:
        """
        Text -> classify -> transform -> validate
        Returns processing result dict
        """
        # 1. Classify
        blueprint_name, confidence = self.blueprints.classify(text)
        blueprint = self.blueprints.get_blueprint(blueprint_name)

        if not blueprint:
            # Fallback: just wrap in basic markdown
            formatted = f"# Notes\ndate: {datetime.now().strftime('%Y-%m-%d')}\n\n{text}"
            return {
                'blueprint': 'unknown',
                'confidence': 0.0,
                'raw_text': text,
                'formatted': formatted,
                'valid': True,
                'errors': [],
                'suggested_filename': self._suggest_filename(formatted),
                'target_folder': 'transcripts',
                'meta': meta
            }

        # 2. Transform via LLM (if available) or simple formatting
        formatted = self._transform(text, blueprint)

        # 3. Validate
        valid, errors = blueprint.validate(formatted)

        # 4. Generate filename
        filename = self._suggest_filename(formatted)

        return {
            'blueprint': blueprint_name,
            'confidence': confidence,
            'raw_text': text,
            'formatted': formatted,
            'valid': valid,
            'errors': errors,
            'suggested_filename': filename,
            'target_folder': blueprint.target_folder,
            'meta': meta
        }

    def _transform(self, text: str, blueprint: Blueprint) -> str:
        """Transform raw text to blueprint format"""
        # Try Claude CLI first
        try:
            prompt = f"""Transform this raw text into structured markdown following this blueprint exactly.
Output ONLY the formatted markdown, no explanations.

BLUEPRINT:
{blueprint.get_prompt_context()}

RAW INPUT:
{text[:3000]}

OUTPUT:"""

            result = subprocess.run(
                ['claude', '-p', prompt],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Fallback: simple formatting
        return self._simple_format(text, blueprint)

    def _simple_format(self, text: str, blueprint: Blueprint) -> str:
        """Simple rule-based formatting when LLM unavailable"""
        lines = []

        # Title
        title_match = re.search(r'^(.+?)[\n\.]', text)
        title = title_match.group(1)[:50] if title_match else "Untitled"
        title = re.sub(r'[^\w\s-]', '', title).strip()

        if blueprint.name == 'recipes':
            lines.append(f"# Recipe: {title}")
            lines.append(f"tags: other")
            lines.append(f"time: 30 min")
            lines.append("")
            lines.append("## Ingredients")
            lines.append("- [ ] (extract from content)")
            lines.append("")
            lines.append("## Steps")
            lines.append("1. (extract from content)")
            lines.append("")
            lines.append("## Notes")
            lines.append(text[:500])
        elif blueprint.name == 'rules':
            lines.append(f"# {title}")
            lines.append(f"category: knowledge/general")
            lines.append("")
            lines.append("## Zasady")
            lines.append("- [ ] (extract from content)")
            lines.append("")
            lines.append("## Notes")
            lines.append(text[:500])
        elif blueprint.name == 'inventory':
            lines.append(f"# Inventory: {title}")
            lines.append(f"updated: {datetime.now().strftime('%Y-%m-%d')}")
            lines.append("")
            lines.append("## Items")
            for item in re.findall(r'\b[\w]+\b', text)[:20]:
                lines.append(f"- [ ] {item}")
        else:
            lines.append(f"# {title}")
            lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
            lines.append("")
            lines.append(text)

        return '\n'.join(lines)

    def _suggest_filename(self, content: str) -> str:
        """Generate filename from content"""
        # Extract title
        title_match = re.search(r'^#\s*(?:Recipe:\s*)?(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = "untitled"

        # Slugify
        slug = title.lower()
        slug = re.sub(r'[ąàáâã]', 'a', slug)
        slug = re.sub(r'[ćčç]', 'c', slug)
        slug = re.sub(r'[ęèéêë]', 'e', slug)
        slug = re.sub(r'[łľ]', 'l', slug)
        slug = re.sub(r'[ńñň]', 'n', slug)
        slug = re.sub(r'[óòôõö]', 'o', slug)
        slug = re.sub(r'[śšş]', 's', slug)
        slug = re.sub(r'[úùûü]', 'u', slug)
        slug = re.sub(r'[ýÿ]', 'y', slug)
        slug = re.sub(r'[źżž]', 'z', slug)
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = slug.strip('-')[:50]

        return slug or 'untitled'

    def save(self, result: Dict, filename: str = None) -> Path:
        """Save processed result to target folder"""
        filename = filename or result['suggested_filename']
        if not filename.endswith('.md'):
            filename += '.md'

        target_dir = self.root / result['target_folder']
        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / filename
        target.write_text(result['formatted'], encoding='utf-8')
        return target

    def process_inbox(self, auto_save: bool = False) -> List[Dict]:
        """Process all items in inbox/"""
        results = []

        # Audio files
        audio_dir = self.inbox / "audio"
        if audio_dir.exists():
            for f in audio_dir.glob("*"):
                if f.suffix.lower() in {'.mp3', '.wav', '.m4a', '.ogg'}:
                    try:
                        results.append(self.process_audio(f))
                    except Exception as e:
                        results.append({'error': str(e), 'file': str(f)})

        # Text files
        text_dir = self.inbox / "text"
        if text_dir.exists():
            for f in text_dir.glob("*.txt"):
                try:
                    text = f.read_text(encoding='utf-8')
                    result = self.process_text(text, source_file=f.name)
                    results.append(result)
                except Exception as e:
                    results.append({'error': str(e), 'file': str(f)})

        # URL queue
        url_queue = self.inbox / "urls" / "queue.txt"
        if url_queue.exists():
            urls = url_queue.read_text().strip().split('\n')
            for url in urls:
                url = url.strip()
                if url and url.startswith('http'):
                    try:
                        results.append(self.process_url(url))
                    except Exception as e:
                        results.append({'error': str(e), 'url': url})

        # Auto-save valid results
        if auto_save:
            for r in results:
                if r.get('valid') and 'error' not in r:
                    self.save(r)

        return results

    def list_inbox(self) -> Dict[str, List[str]]:
        """List all items in inbox"""
        items = {'audio': [], 'text': [], 'urls': []}

        audio_dir = self.inbox / "audio"
        if audio_dir.exists():
            items['audio'] = [f.name for f in audio_dir.glob("*") if f.is_file()]

        text_dir = self.inbox / "text"
        if text_dir.exists():
            items['text'] = [f.name for f in text_dir.glob("*.txt")]

        url_queue = self.inbox / "urls" / "queue.txt"
        if url_queue.exists():
            items['urls'] = [u.strip() for u in url_queue.read_text().split('\n') if u.strip()]

        return items


def is_available() -> bool:
    """Check if ingest dependencies are available"""
    return True  # Core always available, features degrade gracefully
