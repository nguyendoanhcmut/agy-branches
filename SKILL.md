---
name: branches
description: Generate interactive mind map trees from books and large documents. The skill uses recursive fan-out drilling to extract hierarchical Markdown trees and renders zoomable HTML mind maps via Markmap.
risk: low
source: custom
date_added: "2026-09-06"
---

# branches

The `branches` skill creates interactive HTML mind maps from books, documents, or pre-indexed libraries.
It works in two operating modes:
1. **Direct Index Mode (Instant)**: Directly ingests `_structure.json` or `registry.json` created by `paper-indexer` or `courseware-indexer`. Compiles into a mind map in 0.05 seconds with 100% data fidelity.
2. **Autonomous Subagent Mode**: For raw PDFs, Markdown, or text files, it automatically spawns subagents (`branch_scout` -> parallel `branch_driller` -> `branch_merger` -> `branch_verifier` -> `mindmap_renderer`) to discover, extract, verify, and render the tree.

**In-Place Saving Invariant**: The generated HTML file is always saved in the **exact same folder** as the input file or index directory.

## Triggers

Activate this skill when the user mentions any of these terms:
- `branches`
- `mind map`
- `tree map`
- `branch out`
- `cây kiến thức`
- `sơ đồ nhánh`
- `tạo cây`

## In-Place Output Convention

Wherever the source document or index lives, the output is saved in that **exact same directory**:
- **Single Document**: `path/to/<doc_slug>_branches.html`
- **Indexed Directory**: `path/to/indexes/<library_slug>_mindmap.html`

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
- **Prompt Reference**: [`references/branch_scout_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/branch_scout_prompt.md)

### 2. `branch_orchestrator`
- **Role**: Master coordinator.
- **Description**: Ingests scout manifest, dispatches parallel drillers via lightweight pointer-passing, runs M2 sequential streaming fold, triggers verifier and renderer. Context stays under 8,000 tokens.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=true`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/branch_orchestrator_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/branch_orchestrator_prompt.md)

### 3. `branch_driller`
- **Role**: Recursive section worker.
- **Description**: Parses assigned section slice, extracts nested headings and bullet points, and conditionally spawns child drillers if section > 2000 words.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=true`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/branch_driller_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/branch_driller_prompt.md)

### 4. `branches-verifier`
- **Role**: Adversarial completeness auditor.
- **Description**: Audits the merged Markdown tree across 4 gates against the scout's master skeleton. Enforces completeness score >= 0.95 before rendering.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/branch_verifier_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/branch_verifier_prompt.md)

### 5. `mindmap_renderer`
- **Role**: HTML generator.
- **Description**: Ingests merged Markdown tree and builds an accelerated standalone interactive Markmap HTML page saved in-place via build-time KaTeX transformation.
- **Tool Permissions**: `enable_write_tools=true`, `enable_subagent_tools=false`, `enable_mcp_tools=false`
- **Prompt Reference**: [`references/mindmap_renderer_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/mindmap_renderer_prompt.md)

## Reference Files

- Master Orchestrator Prompt: [`references/branch_orchestrator_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/branch_orchestrator_prompt.md)
- Section Driller Prompt: [`references/branch_driller_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/branch_driller_prompt.md)
- Mindmap Renderer Prompt: [`references/mindmap_renderer_prompt.md`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/mindmap_renderer_prompt.md)
- Interactive HTML Template: [`references/markmap_template.html`](file:///C:/Users/Admin/.gemini/config/skills/branches/references/markmap_template.html)
- Mindmap Compiler Script: [`scripts/compile_mindmap.js`](file:///C:/Users/Admin/.gemini/config/skills/branches/scripts/compile_mindmap.js)

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

## Mode 3: YouTube Channel Mind Map

Execute these 7 steps:
1. `yt_crawler` to get `channel_videos.json`.
2. `topic_clusterer` to get `topic_catalog.json`.
3. User picks a topic.
4. `transcript_fetcher` fetches transcripts (with dynamic batching).
5. `branch_driller` processes transcripts.
6. `branch_merger` merges branches.
7. `branches-verifier` and `mindmap_renderer` verify and render the tree.
