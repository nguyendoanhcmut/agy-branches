const fs = require('fs');
const path = require('path');
const vm = require('vm');
const zlib = require('zlib');

class MockNode {
  setAttribute() {}
  append() {}
}

const doc = {
  compatMode: 'CSS1Compat',
  head: { append: () => {} },
  body: { prepend: () => {}, append: () => {} },
  createElement: () => new MockNode(),
  createElementNS: () => new MockNode(),
  createTextNode: () => new MockNode(),
  createDocumentFragment: () => new MockNode()
};

const context = {
  console: { log: () => {}, error: console.error, warn: () => {} },
  setTimeout,
  clearTimeout,
  document: doc,
  Node: MockNode,
  window: {}
};
context.window = context;
context.globalThis = context;

const vendorDir = path.join(__dirname, 'vendor');
vm.runInNewContext(fs.readFileSync(path.join(vendorDir, 'd3.min.js'), 'utf8'), context);
vm.runInNewContext(fs.readFileSync(path.join(vendorDir, 'katex.min.js'), 'utf8'), context);
vm.runInNewContext(fs.readFileSync(path.join(vendorDir, 'markmap-lib.iife.js'), 'utf8'), context);
vm.runInNewContext(fs.readFileSync(path.join(vendorDir, 'markmap-view.iife.js'), 'utf8'), context);

const { Transformer } = context.markmap;
const transformer = new Transformer();

function compileMindmap(inputMdPath, outputHtmlPath, docTitle) {
  const t0 = performance.now();
  let md = fs.readFileSync(inputMdPath, 'utf8');

  if (!docTitle) {
    const titleMatch = md.match(/^#\s+(.+)$/m);
    docTitle = titleMatch ? titleMatch[1].trim() : path.basename(inputMdPath, path.extname(inputMdPath));
  }

  if (!md.startsWith('---')) {
    md = `---\nmarkmap:\n  initialExpandLevel: 2\n  maxWidth: 420\n---\n${md}`;
  }

  const tTransform0 = performance.now();
  const res = transformer.transform(md);
  const tTransform1 = performance.now();

  let nodeCount = 0;
  let katexCount = 0;
  function walk(n) {
    nodeCount++;
    if (n.content && n.content.includes('class="katex"')) katexCount++;
    if (n.payload) {
      if (n.payload.fold !== undefined) {
        n.payload = { fold: n.payload.fold };
      } else {
        delete n.payload;
      }
    }
    if (n.children) n.children.forEach(walk);
  }
  walk(res.root);

  const jsonStr = JSON.stringify(res.root);
  const gzBuffer = zlib.gzipSync(Buffer.from(jsonStr, 'utf8'), { level: 9 });
  const b64Data = gzBuffer.toString('base64');

  const templatePath = path.join(__dirname, '..', 'references', 'markmap_template.html');
  let html = fs.readFileSync(templatePath, 'utf8');

  html = html.replace(/\{DOCUMENT_TITLE\}/g, docTitle);
  html = html.replace(/\{MINDMAP_DATA\}/g, b64Data);

  fs.writeFileSync(outputHtmlPath, html, 'utf8');
  const tTotal = performance.now() - t0;

  const outSizeMb = (fs.statSync(outputHtmlPath).size / 1024 / 1024).toFixed(2);
  console.log(`[compile_mindmap] Built "${docTitle}" -> ${outputHtmlPath}`);
  console.log(`  - Total nodes: ${nodeCount} | KaTeX math nodes: ${katexCount}`);
  console.log(`  - Transform time: ${(tTransform1 - tTransform0).toFixed(1)}ms | Total compile time: ${tTotal.toFixed(1)}ms`);
  console.log(`  - Output size: ${outSizeMb} MB (raw JSON: ${(jsonStr.length / 1024 / 1024).toFixed(2)} MB, compressed: ${(gzBuffer.length / 1024 / 1024).toFixed(2)} MB)`);

  return { nodeCount, katexCount, tTotal, outputHtmlPath };
}

function findMarkdownFiles(dir, fileList = []) {
  if (!fs.existsSync(dir)) {
    console.warn(`[compile_mindmap] Directory does not exist: ${dir}`);
    return fileList;
  }
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== 'node_modules' && entry.name !== '.git') {
        findMarkdownFiles(fullPath, fileList);
      }
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      fileList.push(fullPath);
    }
  }
  return fileList;
}

function compileAllMindmaps(targetDir = '.') {
  console.log(`[compile_mindmap] Scanning directory for Markdown files: ${targetDir}`);
  const mdFiles = findMarkdownFiles(targetDir);
  console.log(`[compile_mindmap] Found ${mdFiles.length} Markdown file(s)`);
  const results = [];
  for (const mdPath of mdFiles) {
    const outHtmlPath = mdPath.replace(/\.md$/i, '.html');
    try {
      results.push(compileMindmap(mdPath, outHtmlPath));
    } catch (err) {
      console.error(`[compile_mindmap] Failed to compile ${mdPath}:`, err.message);
    }
  }
  return results;
}

module.exports = { compileMindmap, compileAllMindmaps };

if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.includes('--all')) {
    const dirIdx = args.indexOf('--dir');
    const targetDir = dirIdx !== -1 && args[dirIdx + 1] ? args[dirIdx + 1] : '.';
    compileAllMindmaps(targetDir);
  } else if (args.length < 2) {
    console.error('Usage: node compile_mindmap.js <input.md> <output.html> [doc_title]');
    console.error('       node compile_mindmap.js --all [--dir <directory>]');
    process.exit(1);
  } else {
    compileMindmap(args[0], args[1], args[2]);
  }
}

