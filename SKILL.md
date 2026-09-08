---
name: branches
description: Generate interactive mind map trees from books and large documents. The skill uses recursive fan-out drilling to extract hierarchical Markdown trees and renders zoomable HTML mind maps via Markmap.
risk: low
source: custom
date_added: "2026-09-06"
---

# branches

The `branches` skill creates interactive HTML mind maps from books, documents, pre-indexed libraries, or YouTube channels and video playlists.
It works in three operating modes:
1. **Direct Index Mode (Instant)**: Directly ingests `_structure.json` or `registry.json` created by `paper-indexer` or `courseware-indexer`. Compiles into a mind map in 0.05 seconds with 100% data fidelity.
2. **Autonomous Subagent Mode (Documents)**: For raw PDFs, Markdown, or text files, it automatically spawns subagents (`branch_scout` -> parallel `branch_driller` -> `branch_merger` -> `branch_verifier` -> `mindmap_renderer`) to discover, extract, verify, and render the tree.
3. **YouTube Channel & Series Mode**: For YouTube channels, playlists, or lecture series, it automatically crawls metadata (`yt_crawler`), clusters videos into thematic curricula (`topic_clusterer`), presents an interactive topic selection menu to the user, fetches transcripts via adaptive duration bin-packing (`transcript_fetcher`), and drills/synthesizes branches with timestamp deep links (`branch_driller` -> `branch_merger` -> `branches-verifier` -> `mindmap_renderer`).

**In-Place Saving Invariant**: The generated HTML file is always saved in the **exact same folder** as the input file, index directory, or target channel directory.

## Triggers

Activate this skill when the user mentions any of these terms:
- `branches`
- `mind map`
- `tree map`
- `branch out`
- `cây kiến thức`
- `sơ đồ nhánh`
- `tạo cây`
- `youtube mind map`
- `kênh youtube`
- `video mind map`
- `playlist mind map`
- `tạo cây youtube`

## In-Place Output Convention

Wherever the source document, index, or channel workspace lives, the output is saved in that **exact same directory**:
- **Single Document**: `path/to/<doc_slug>_branches.html`
- **Indexed Directory**: `path/to/indexes/<library_slug>_mindmap.html`
- **YouTube Channel/Topic**: `path/to/<channel_slug>/<topic_slug>_branches.html` (alongside `channel_videos.json`, `topic_catalog.json`, and `transcripts/`)

The system uses five specialized micro-agents:

```
[Raw Document: PDF / MD / TXT]
              │
              ▼
    ┌──────────────────┐
    │  branches-scout  │  (Scans TOC, boundaries, generates global context pack)
    └─────────┬────────┘
              │ writes scout_manifest.json
              ▼
    ┌──────────────────────┐
    │ branch_orchestrator  │  (Master Agent: coordinates workers via pointer-passing)
    └──────────┬───────────┘
               │
      ┌────────┴────────┬────────────────┐
      │ Parallel Spawns │                │
      ▼                 ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│branch_driller│ │branch_driller│ │branch_driller│  (Worker Agents: L3-L6)
└──────┬───────┘ └──────────────┘ └──────────────┘
       │ (if section > 2000 words)
       ▼
┌──────────────┐
│branch_driller│ (Child Driller)
└──────────────┘
       │
       ▼
┌──────────────────────┐
│ Sequential Fold (M2) │  (Merges chapters linearly, resolves cross-links & equations)
└──────────┬───────────┘
           │ writes <doc_slug>_branches.md
           ▼
┌───────────────────┐
│ branches-verifier │  (Audits 4 gates against Scout skeleton; threshold >= 0.95)
└─────────┬─────────┘
          │
          ▼
┌──────────────────┐
│ mindmap_renderer │  (HTML Generator)
└─────────┬────────┘
          │
          ▼
[Interactive Mind Map: <doc_slug>_branches.html]
```

### 1. `branches-scout`
- **Role**: Macro topology & routing generator.
- **Description**: Scans TOC and structural landmarks without reading full body text. Produces `scout_manifest.json` with master skeleton and 1500-token global context pack.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/branch_scout_prompt.md`](references/branch_scout_prompt.md)

### 2. `branch_orchestrator`
- **Role**: Master coordinator.
- **Description**: Ingests scout manifest, dispatches parallel drillers via lightweight pointer-passing, runs M2 sequential streaming fold, triggers verifier and renderer. Context stays under 8,000 tokens.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=true`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/branch_orchestrator_prompt.md`](references/branch_orchestrator_prompt.md)

### 3. `branch_driller`
- **Role**: Recursive section worker.
- **Description**: Parses assigned section slice, extracts nested headings and bullet points, and conditionally spawns child drillers if section > 2000 words.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=true`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/branch_driller_prompt.md`](references/branch_driller_prompt.md)

### 4. `branches-verifier`
- **Role**: Adversarial completeness auditor.
- **Description**: Audits the merged Markdown tree across 4 gates against the scout's master skeleton. Enforces completeness score >= 0.95 before rendering.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/branch_verifier_prompt.md`](references/branch_verifier_prompt.md)

### 5. `mindmap_renderer`
- **Role**: HTML generator.
- **Description**: Ingests merged Markdown tree and builds an accelerated standalone interactive Markmap HTML page saved in-place via build-time KaTeX transformation.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/mindmap_renderer_prompt.md`](references/mindmap_renderer_prompt.md)

## Reference Files

### Mode 1 & 2 (Documents & Pre-Indexed Libraries)
- Master Orchestrator Prompt: [`references/branch_orchestrator_prompt.md`](references/branch_orchestrator_prompt.md)
- Scout Agent Prompt: [`references/branch_scout_prompt.md`](references/branch_scout_prompt.md)
- Section Driller Prompt: [`references/branch_driller_prompt.md`](references/branch_driller_prompt.md)
- Structural Merger Prompt: [`references/branch_merger_prompt.md`](references/branch_merger_prompt.md)
- Adversarial Verifier Prompt: [`references/branch_verifier_prompt.md`](references/branch_verifier_prompt.md)
- Mindmap Renderer Prompt: [`references/mindmap_renderer_prompt.md`](references/mindmap_renderer_prompt.md)
- Interactive HTML Template: [`references/markmap_template.html`](references/markmap_template.html)
- Mindmap Compiler Script: [`scripts/compile_mindmap.js`](scripts/compile_mindmap.js)

### Mode 3 (YouTube Channels & Playlists)
- YouTube Crawler Prompt: [`references/yt_crawler_prompt.md`](references/yt_crawler_prompt.md)
- Topic Clusterer Prompt: [`references/topic_clusterer_prompt.md`](references/topic_clusterer_prompt.md)
- Transcript Fetcher Prompt: [`references/transcript_fetcher_prompt.md`](references/transcript_fetcher_prompt.md)
- YouTube Crawler Script: [`scripts/yt_crawl.py`](scripts/yt_crawl.py)
- YouTube Transcript & Bin-Packing Script: [`scripts/yt_transcript.py`](scripts/yt_transcript.py)

## PDF Text Extraction Script

Use this complete Python script to extract text and outline bookmarks from PDF documents:

```python
import fitz
import json
import sys
import os

def extract_pdf_content(pdf_path: str, output_txt_path: str = None) -> dict:
    """
    Extract text and table of contents bookmarks from a PDF file.
    """
    doc = fitz.open(pdf_path)
    metadata = doc.metadata or {}
    toc = doc.get_toc()
    
    extracted_pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        extracted_pages.append(f"<!-- Page {page_num + 1} -->\n{text}")
        
    full_text = "\n\n".join(extracted_pages)
    
    result = {
        "title": (metadata.get("title") or "").strip(),
        "author": (metadata.get("author") or "").strip(),
        "total_pages": len(doc),
        "toc": toc,
        "full_text": full_text
    }
    
    doc.close()
    
    if output_txt_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_txt_path)), exist_ok=True)
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
            
    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        out_txt = sys.argv[2] if len(sys.argv) > 2 else None
        res = extract_pdf_content(pdf_file, out_txt)
        print(f"Extracted {res['total_pages']} pages. TOC entries: {len(res['toc'])}")
```

## Slug Normalization Rules

Generate document slugs with these rules:
1. Convert all characters to lowercase.
2. Replace spaces and hyphens with underscores (`_`).
3. Remove all punctuation and special characters.
4. Keep at most five words.

Examples:
- `Designing Data-Intensive Applications.pdf` -> `designing_data_intensive_applications`
- `Clean Code: A Handbook.pdf` -> `clean_code`
- `Giao Trinh Triet Hoc.pdf` -> `giao_trinh_triet_hoc`

## Output File Conventions

The skill saves both output files in the directory of the input document:
- `<doc_slug>_branches.md`: Complete merged Markdown tree.
- `<doc_slug>_branches.html`: Standalone interactive mind map.

## Orchestration Workflow

Execute these seven steps to create a mind map:

1. Detect the input document format from its file extension (`.pdf`, `.md`, or `.txt`).
2. If the input is a PDF, run the PyMuPDF extraction script to extract text and outline bookmarks (`toc`). If the input is Markdown or plain text, read the file directly.
3. Register all three subagents with `define_subagent` with their prompt files.
4. Invoke `branch_orchestrator` with `input_text`, `output_dir`, `doc_title`, `doc_slug`, and optional `toc`.
5. Wait for the orchestrator completion message. Do not poll in a loop.
6. Make sure that both `<doc_slug>_branches.md` and `<doc_slug>_branches.html` exist.
7. Report the file paths and tree statistics to the user.

## Advanced Options

- **Depth Control**: The default depth limit is 5 levels. You can set `max_depth` up to 6 levels (`######`).
- **Section Focus**: To map a single chapter, pass that chapter text directly to `branch_driller`.
- **Batch Processing**: To process multiple documents, launch parallel `branch_orchestrator` subagents.

## Mode 3: YouTube Channel & Playlist Mind Map

Mode 3 transforms YouTube channels, video playlists, or lecture series into structured, interactive Markmap knowledge trees. It discovers channel curriculum structures, clusters videos into thematic topics, lets the user select their focus curriculum, downloads transcripts using adaptive duration bin-packing, and synthesizes multi-video knowledge with timestamped deep links.

### Architecture & Pipeline Flow

```
[YouTube Channel / Playlist URL]
              │
              ▼
    ┌──────────────────┐
    │    yt_crawler    │  (Extracts video metadata -> channel_videos.json)
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │ topic_clusterer  │  (2-Stage Hybrid: Macro Taxonomy + Micro Routing -> topic_catalog.json)
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────────────────────────────────────┐
    │ Interactive Topic Catalog Display / Selection UX │  (Presents formatted Markdown table & options)
    └─────────────────┬────────────────────────────────┘
                      │ User selects topic(s)
                      ▼
          ┌───────────────────────┐
          │  transcript_fetcher   │  (Bin-packing batches <= 60 min, dual-tier extraction, rate limits)
          └───────────┬───────────┘
                      │ Writes transcripts to transcripts/
                      ▼
          ┌───────────────────────┐
          │  branch_orchestrator  │  (Coordinates drilling & merging across videos)
          └───────────┬───────────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
    ┌──────────────┐      ┌──────────────┐
    │branch_driller│      │branch_driller│  (Extracts key concepts, preserves timestamp links)
    └──────┬───────┘      └──────┬───────┘
           │                     │
           └──────────┬──────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │     branch_merger     │  (Multi-video synthesis, removes intros/promos, cross-links)
          └───────────┬───────────┘
                      │ writes <topic_slug>_branches.md
                      ▼
          ┌───────────────────────┐
          │   branches-verifier   │  (Audits 4 gates against video coverage & timestamps; score >= 0.95)
          └───────────┬───────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │   mindmap_renderer    │  (Compiles accelerated interactive Markmap HTML page)
          └───────────┬───────────┘
                      │
                      ▼
    [Interactive Mind Map: <topic_slug>_branches.html]
```

### Specialized Micro-Agents for Mode 3

1. **`yt_crawler`**
   - **Role**: Channel metadata harvester.
   - **Description**: Ingests channel URL, handle, or playlist link. Runs `scripts/yt_crawl.py` using `yt-dlp` flat-extraction mode to capture titles, durations, view counts, and URLs without streaming media.
   - **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
   - **Prompt Reference**: [`references/yt_crawler_prompt.md`](references/yt_crawler_prompt.md)

2. **`topic_clusterer`**
   - **Role**: Semantic taxonomy & catalog architect.
   - **Description**: Uses a 2-stage hybrid algorithm (Stage 1: Macro Taxonomy Synthesis, Stage 2: Micro Semantic Routing) to partition videos into 4-7 coherent thematic curricula and outputs `topic_catalog.json`.
   - **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
   - **Prompt Reference**: [`references/topic_clusterer_prompt.md`](references/topic_clusterer_prompt.md)

3. **`transcript_fetcher`**
   - **Role**: Bin-packed transcript harvester.
   - **Description**: Downloads closed captions or auto-generated transcripts with adaptive duration bin-packing (`scripts/yt_transcript.py`), capping batches at `<= 60 minutes` to prevent YouTube HTTP 429 rate limit blocks. Falls back to `yt-dlp` android client if needed.
   - **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
   - **Prompt Reference**: [`references/transcript_fetcher_prompt.md`](references/transcript_fetcher_prompt.md)

4. **`branch_driller`**
   - **Role**: Spoken text recursive extractor.
   - **Description**: Processes individual video transcripts into hierarchical Markdown fragments, extracting concept definitions, technical terms, mathematical formulas, and preserving video timestamps (`[mm:ss]`).
   - **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=true`, `enable_mcp_tools=false`
   - **Prompt Reference**: [`references/branch_driller_prompt.md`](references/branch_driller_prompt.md)

5. **`branch_merger`**
   - **Role**: Multi-video knowledge synthesizer.
   - **Description**: Synthesizes video drill fragments into a unified `<topic_slug>_branches.md` tree. Strips repetitive video intros, sponsorships, and subscribe calls, while integrating cross-video prerequisites and timestamp citations.
   - **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
   - **Prompt Reference**: [`references/branch_merger_prompt.md`](references/branch_merger_prompt.md)

6. **`branches-verifier`**
   - **Role**: Quality & grounding auditor.
   - **Description**: Validates video coverage (40%), depth compliance (30%), timestamp grounding (20%), and deduplication (10%). Requires completeness score `>= 0.95`.
   - **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
   - **Prompt Reference**: [`references/branch_verifier_prompt.md`](references/branch_verifier_prompt.md)

7. **`mindmap_renderer`**
   - **Role**: HTML generator.
   - **Description**: Compiles the unified Markdown tree into an accelerated, standalone Markmap HTML file (`<topic_slug>_branches.html`) with embedded theme toggling and zoomable navigation.
   - **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
   - **Prompt Reference**: [`references/mindmap_renderer_prompt.md`](references/mindmap_renderer_prompt.md)

---

### Data Contracts & Schemas

#### 1. `channel_videos.json`
Generated by `yt_crawler` via `scripts/yt_crawl.py`:
```json
[
  {
    "id": "aircAruvnKk",
    "title": "But what is a neural network? | Chapter 1, Deep Learning",
    "duration": 1152,
    "view_count": 15420100,
    "url": "https://youtu.be/aircAruvnKk",
    "upload_date": "2017-10-05"
  }
]
```

#### 2. `topic_catalog.json`
Generated by `topic_clusterer`:
```json
{
  "catalog_version": "1.0",
  "channel_title": "3Blue1Brown",
  "total_videos": 42,
  "total_duration_seconds": 38400,
  "total_duration_formatted": "10h 40m",
  "topics": [
    {
      "id": 1,
      "name": "Neural Networks & Deep Learning",
      "slug": "neural_networks_deep_learning",
      "description": "Comprehensive visual introduction to neural network architecture, backpropagation, and gradient descent.",
      "video_count": 5,
      "total_duration_seconds": 5820,
      "total_duration_formatted": "1h 37m",
      "keywords": ["neural networks", "gradient descent", "backpropagation", "transformers"],
      "videos": [
        {
          "id": "aircAruvnKk",
          "title": "But what is a neural network? | Chapter 1, Deep Learning",
          "duration": 1152,
          "duration_formatted": "19:12",
          "view_count": 15420100,
          "url": "https://youtu.be/aircAruvnKk"
        }
      ]
    }
  ]
}
```

#### 3. `transcript_manifest.json`
Generated by `transcript_fetcher` via `scripts/yt_transcript.py`:
```json
{
  "total_videos": 5,
  "total_batches": 2,
  "succeeded": 5,
  "failed": 0,
  "batch_duration_cap_minutes": 60,
  "results": [
    {
      "id": "aircAruvnKk",
      "title": "But what is a neural network? | Chapter 1, Deep Learning",
      "duration": 1152,
      "status": "success",
      "method": "api",
      "path": "<output_dir>/transcripts/aircAruvnKk.txt",
      "word_count": 3412
    }
  ]
}
```

---

### Topic Catalog Display & Selection UX

When `topic_clusterer` finishes, the orchestrating agent presents an interactive Markdown catalog menu to the user. This human-in-the-loop gate ensures that users can target the exact curriculum or topic they need before expensive transcript fetching begins.

#### Presentation Format
```markdown
### 📺 YouTube Channel Topic Catalog: {Channel Name}
Found **{total_videos} videos** totaling **{total_duration_formatted}**. Organized into **{N} thematic curricula**:

| # | Topic / Curriculum | Videos | Duration | Core Focus & Representative Videos |
|---|--------------------|:------:|:--------:|-----------------------------------|
| **1** | Neural Networks & Deep Learning | 5 | 1h 37m | Backpropagation, Gradient Descent, Transformers |
| **2** | Essence of Linear Algebra | 16 | 3h 56m | Vectors, Linear Transformations, Eigenvalues |
| **3** | Essence of Calculus | 12 | 2h 45m | Limits, Derivatives, Integrals, Taylor Series |
| **4** | Pure Math & Cryptography | 9 | 2h 22m | Prime Numbers, Riemann Hypothesis, RSA |

---
#### 🎯 Choose Your Topic:
- **Specific Curriculum**: Enter topic number (e.g. `1` or `2`) to drill a deep, complete tree for that topic.
- **Combined Curricula**: Enter comma-separated numbers (e.g. `1, 2`) to synthesize an integrated tree.
- **Full Channel**: Enter `all` to generate an overview master mind map spanning all topics.
- **Custom Filter**: Enter `filter: <keyword>` to only process videos matching a search query.
```

#### Selection Handling Protocol
1. **Single Topic Selected** (`1`): Set target video list to `topics[0].videos`, slug to `topics[0].slug`, and title to `"{channel_name} - {topic_name}"`.
2. **Multiple Topics Selected** (`1, 2`): Combine video lists, set slug to combined slug, and synthesize multi-topic root.
3. **Full Channel Selected** (`all`): Process all topics sequentially; each topic forms a major `##` branch in the final mind map.
4. **User Confirmation Gate**: The orchestrator waits for user response before spawning `transcript_fetcher`.

---

### Step-by-Step Mode 3 Orchestration Workflow

Execute these 7 sequential steps:

#### Step 1: Channel Ingestion & Crawling (`yt_crawler`)
1. User provides a YouTube channel, playlist, or series link.
2. Determine output directory: `<workspace>/<channel_slug>/`.
3. Spawn `yt_crawler` to run `scripts/yt_crawl.py "<channel_url>" "<output_dir>"`.
4. Verify `<output_dir>/channel_videos.json` is populated.

#### Step 2: Semantic Topic Clustering (`topic_clusterer`)
1. Spawn `topic_clusterer` with `channel_videos.json`.
2. Run Stage 1 Macro Taxonomy synthesis to discover 4-7 thematic curricula.
3. Run Stage 2 Micro Semantic routing to map every video and detect chronological sequences.
4. Save `<output_dir>/topic_catalog.json`.

#### Step 3: Interactive Catalog Presentation & User Gate
1. Format `topic_catalog.json` into the Topic Catalog Display UX table.
2. Present the menu to the user and prompt for selection.
3. **Wait for user input** (do not guess or auto-select unless user explicitly requested `all`).

#### Step 4: Adaptive Duration Bin-Packed Transcript Fetching (`transcript_fetcher`)
1. Filter video list based on user selection.
2. Spawn `transcript_fetcher` to execute:
   ```powershell
   python scripts/yt_transcript.py --out "<output_dir>/transcripts" --catalog "<output_dir>/topic_catalog.json" --topic <selected_topic_id> --max-duration 3600 --algorithm ffd
   ```
3. Script bin-packs videos into `<= 60 min` batches and executes dual-tier extraction (API -> yt-dlp fallback).
4. Verify `<output_dir>/transcripts/transcript_manifest.json` shows successful transcript generation.

#### Step 5: Parallel Video Branch Drilling (`branch_driller`)
1. Spawn parallel `branch_driller` workers for each video transcript.
2. Pass video title, YouTube URL, and transcript text.
3. Driller extracts structured concepts, preserving timestamps in format:
   `- [mm:ss] Key insight ([Watch](https://youtu.be/<id>?t=<sec>))`
4. Workers write temporary Markdown fragments to `<output_dir>/temp_<vid>.md`.

#### Step 6: Multi-Video Structural Merge & De-Noising (`branch_merger`)
1. Spawn `branch_merger` (or execute Sequential Streaming Fold M2) over all video fragments.
2. Strip transcript noise (sponsor ads, greetings, subscribe requests, outro plugs).
3. Synthesize overlapping concepts across multiple videos into unified branches.
4. Output unified Markdown tree: `<output_dir>/<topic_slug>_branches.md`.

#### Step 7: Completeness Verification & Standalone HTML Compilation
1. Spawn `branches-verifier` to audit `<topic_slug>_branches.md` across 4 Mode 3 gates:
   - **Video Coverage (0.40)**: All selected videos represented as distinct branches or cited nodes.
   - **Depth Compliance (0.30)**: Hierarchy reaches 3-5 levels of detail.
   - **Timestamp Grounding (0.20)**: Key claims have clickable `[mm:ss]` watch links.
   - **De-noising & Deduplication (0.10)**: Zero sponsor/subscribe boilerplate.
2. If `completeness_score >= 0.95`, spawn `mindmap_renderer` to compile HTML:
   ```powershell
   node scripts/compile_mindmap.js "<output_dir>/<topic_slug>_branches.md" "<output_dir>/<topic_slug>_branches.html" "<Topic Title>"
   ```
3. Report output links, node counts, video counts, and duration statistics to the user.

---

### Video Timestamp Deep-Linking & De-Noising Invariants

1. **Clickable Timestamp Links**:
   Every significant concept node or demonstration must include a clickable link directly to that second in the YouTube video:
   ```markdown
   - [07:45] Backpropagation applies chain rule backwards from loss to weights ([Watch](https://youtu.be/IHZwWFHWa-w?t=465))
   ```
2. **Video Root Nodes**:
   When drilling a specific video, its top-level heading must include the canonical link:
   ```markdown
   ### [Chapter 2: How Neural Networks Learn](https://youtu.be/IHZwWFHWa-w)
   ```
3. **De-Noising Invariant**:
   Never retain channel administrative chatter in the knowledge tree:
   - Exclude: "Thanks to Brilliant.org for sponsoring", "Leave a comment down below", "Smash that subscribe button", "Check out the merch store".
   - Retain: Definitions, proof steps, diagrams explained in speech, code walkthroughs, parameter formulas, and intuitive explanations.
