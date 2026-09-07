# 🌿 agy-branches

Antigravity skill tạo **mind map tương tác** từ sách, tài liệu, hoặc codebase.

Đầu vào: file text / PDF / JSON index.  
Đầu ra: **HTML standalone** (Markmap) — zoom, tìm kiếm, dark/light mode, KaTeX.

## Skill làm được gì

| Khả năng | Mô tả |
|:---|:---|
| **2 chế độ** | Direct Index (từ `_structure.json` — tức thì) và Autonomous (đọc raw text — sâu hơn) |
| **5 micro-agents** | Scout → Driller → Merger → Verifier → Renderer |
| **Đệ quy tự động** | Driller tự spawn child drillers khi section > 2000 từ |
| **Xác minh 4 cổng** | Section Coverage (40%) + Depth Compliance (30%) + Content Grounding (20%) + Lexicon (10%) |
| **HTML offline** | Standalone, không cần server. D3 + Markmap + KaTeX nhúng sẵn |

## Kiến trúc

```
Input (text / JSON)
  │
  ├─ Mode 1: Direct Index ──────────────────────> Compile ─> HTML
  │  (có _structure.json / registry.json)
  │
  └─ Mode 2: Autonomous Subagent Pipeline
       │
       ├─ Scout ─── quét mục lục, chia routing_table
       ├─ Driller ─ đọc từng chunk, trích cây Markdown (đệ quy)
       ├─ Merger ── gom các fragment theo thứ tự
       ├─ Verifier ─ kiểm 4 cổng, score ≥ 0.95
       └─ Renderer ─ compile Markdown → HTML (Markmap)
```

## Cài đặt

Copy thư mục này vào Antigravity skills:

```bash
# macOS / Linux
cp -r agy-branches ~/.gemini/config/skills/branches

# Windows
xcopy /E /I agy-branches "%USERPROFILE%\.gemini\config\skills\branches"
```

Yêu cầu:
- **Node.js** ≥ 18 (chạy `compile_mindmap.js`)
- **Antigravity** (Google AGY) với subagent support

## Cấu trúc thư mục

```
agy-branches/
├── SKILL.md                          # Hướng dẫn chính cho agent
├── references/
│   ├── branch_orchestrator_prompt.md  # Prompt điều phối 6 phase
│   ├── branch_scout_prompt.md         # Prompt trinh sát mục lục
│   ├── branch_driller_prompt.md       # Prompt khoan đệ quy
│   ├── branch_verifier_prompt.md      # Prompt xác minh 4 cổng
│   ├── mindmap_renderer_prompt.md     # Prompt render HTML
│   └── markmap_template.html          # Template HTML gốc
├── scripts/
│   ├── compile_mindmap.js             # Compiler: Markdown → HTML
│   ├── verify_full_suite.js           # Bộ kiểm tra tự động
│   └── vendor/                        # D3, Markmap, KaTeX (offline)
```

## Ví dụ thực tế

Skill này đã tạo mind map cho bộ sách **Lục Hào Cổ Bốc Thực Đoán Toàn Thư** (5 tập, 63 chương, 7,288 nodes):

👉 **[Xem demo trực tiếp](https://nguyendoanhcmut.github.io/-c-b-c-branches/)**

| Volume | Nodes | Link |
|:---|:---:|:---|
| Toàn Thư (gộp) | 7,288 | [Mở](https://nguyendoanhcmut.github.io/-c-b-c-branches/coboc_toan_thu_branches.html) |
| Tập 1: Nhập Môn | 2,472 | [Mở](https://nguyendoanhcmut.github.io/-c-b-c-branches/vol01_branches.html) |
| Tập 2: Dịch Lý (1) | 1,226 | [Mở](https://nguyendoanhcmut.github.io/-c-b-c-branches/vol02_branches.html) |
| Tập 3: Dịch Lý (2) | 1,077 | [Mở](https://nguyendoanhcmut.github.io/-c-b-c-branches/vol03_branches.html) |
| Tập 4: Tiến Giai | 1,081 | [Mở](https://nguyendoanhcmut.github.io/-c-b-c-branches/vol04_branches.html) |
| Tập 5: Chi Tiết | 1,369 | [Mở](https://nguyendoanhcmut.github.io/-c-b-c-branches/vol05_branches.html) |

## Tính năng HTML output

- 🔍 Tìm kiếm thời gian thực trong cây
- 🔄 Zoom / Pan bằng chuột hoặc cảm ứng
- 📊 Toggle cấp độ L1–L5
- 🌗 Dark / Light mode tự động
- 📐 KaTeX render công thức toán
- 📦 Standalone — mở trực tiếp, không cần server

## License

MIT
