let puppeteer;
try {
  puppeteer = require('puppeteer');
} catch (e) {
  try {
    const fallbackPath = require('path').join(process.env.APPDATA || '', 'npm/node_modules/md-to-pdf/node_modules/puppeteer');
    puppeteer = require(fallbackPath);
  } catch (e2) {
    console.error('Puppeteer not found. Please install puppeteer via npm.');
  }
}
const fs = require('fs');
const path = require('path');

const TARGETS = [
  {
    name: 'Water Treatment Engineering',
    htmlPath: 'C:/antgravity workplace/hcmut-263/kt xu ly nuoc cap/indexes/test_branches_deep/water_treatment_subagent_deep_branches.html',
    expectedRootNodes: 9,
    mathSteps: ['Chương 1', '1.0', '1.0.1', '1.0.1.1', 'Phân bổ']
  },
  {
    name: 'Wastewater Treatment Engineering',
    htmlPath: 'C:/antgravity workplace/hcmut-263/kt xu ly nuoc thai/indexes/test_branches_deep/wastewater_treatment_deep_branches.html',
    expectedRootNodes: 13,
    mathSteps: ['Chương 01', '1.1', '1.1.1', '1.1.1.2', '1.1.1.2.2']
  }
];

async function verifyTarget(browser, target) {
  console.log(`\n===============================================================`);
  console.log(`VERIFYING: ${target.name}`);
  console.log(`File: ${target.htmlPath}`);
  console.log(`===============================================================`);

  // Gate 1: Static Code Invariants
  console.log('\n[Gate 1: Static Code Invariants]');
  const htmlContent = fs.readFileSync(target.htmlPath, 'utf8');
  const sizeMb = (fs.statSync(target.htmlPath).size / 1024 / 1024).toFixed(2);
  console.log(`  - File Size: ${sizeMb} MB`);

  const checks = [
    { desc: 'Contains katex.min.css', pass: htmlContent.includes('katex.min.css') },
    { desc: 'Contains d3.min.js', pass: htmlContent.includes('d3') && htmlContent.includes('.min.js') },
    { desc: 'Contains markmap-view', pass: htmlContent.includes('markmap-view') },
    { desc: 'Contains katex.min.js', pass: htmlContent.includes('katex.min.js') },
    { desc: 'markmap-autoloader ELIMINATED', pass: !htmlContent.includes('markmap-autoloader') },
    { desc: 'Contains initialExpandLevel: 2', pass: htmlContent.includes('initialExpandLevel: 2') },
    { desc: 'Contains maxWidth: 420', pass: htmlContent.includes('maxWidth: 420') },
    { desc: 'Contains #theme-toggle button', pass: htmlContent.includes('id="theme-toggle"') },
    { desc: 'Contains .icon-sun and .icon-moon SVGs', pass: htmlContent.includes('icon-sun') && htmlContent.includes('icon-moon') },
    { desc: 'Contains localStorage theme persistence', pass: htmlContent.includes("localStorage.getItem('markmap-theme')") },
    { desc: 'Contains clean ES6 Map colorCache', pass: htmlContent.includes('colorCache = new Map()') }
  ];

  let gate1Pass = true;
  for (const c of checks) {
    console.log(`  ${c.pass ? '✓' : '✗'} ${c.desc}`);
    if (!c.pass) gate1Pass = false;
  }

  // Gate 2: Load Time Performance Benchmark
  console.log('\n[Gate 2: Load Time Performance Benchmark]');
  const fileUrl = 'file:///' + path.resolve(target.htmlPath).replace(/\\/g, '/');

  // Warm CDN cache
  const pWarm = await browser.newPage();
  await pWarm.setCacheEnabled(true);
  await pWarm.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 90000 });
  await pWarm.close();

  const loadTimes = [];
  for (let r = 1; r <= 3; r++) {
    const page = await browser.newPage();
    await page.setCacheEnabled(true);
    const t0 = performance.now();
    await page.goto(fileUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
    const dcl = performance.now() - t0;
    await page.waitForFunction(() => window.mm && document.querySelector('.markmap svg g'), { timeout: 90000 });
    const total = performance.now() - t0;
    loadTimes.push({ total, dcl });
    console.log(`  - Run ${r}: Total = ${total.toFixed(1)} ms | DCL = ${dcl.toFixed(1)} ms`);
    await page.close();
  }

  const avgTotal = loadTimes.reduce((a, b) => a + b.total, 0) / loadTimes.length;
  console.log(`  -> Average Warm Load-to-Interactive: ${avgTotal.toFixed(1)} ms`);

  // Gate 3: Interactive Rendering & Hierarchy Integrity
  console.log('\n[Gate 3: Interactive Rendering & Tree Hierarchy]');
  const testPage = await browser.newPage();
  await testPage.setCacheEnabled(true);
  await testPage.goto(fileUrl, { waitUntil: 'domcontentloaded' });
  await testPage.waitForFunction(() => window.mm && document.querySelector('.markmap svg g'));

  const initialStats = await testPage.evaluate(() => {
    return {
      nodes: document.querySelectorAll('.markmap svg g.markmap-node').length,
      links: document.querySelectorAll('.markmap svg path.markmap-link').length,
      circles: document.querySelectorAll('.markmap svg circle').length
    };
  });
  console.log(`  - Initial Visible Level 2 Nodes: ${initialStats.nodes}`);
  console.log(`  - Initial Links: ${initialStats.links} | Circles: ${initialStats.circles}`);

  const expandStats = await testPage.evaluate(async () => {
    const circles = document.querySelectorAll('.markmap svg circle');
    if (circles[0]) {
      circles[0].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    }
    await new Promise(r => setTimeout(r, 400));
    return {
      nodesAfterClick: document.querySelectorAll('.markmap svg g.markmap-node').length,
      hasLayoutCollapse: document.querySelectorAll('.markmap svg g.markmap-node').length === 0,
      hasInfiniteLoop: document.querySelectorAll('.markmap svg g.markmap-node').length > 50000
    };
  });
  console.log(`  - Nodes after Chapter 1 Expand: ${expandStats.nodesAfterClick}`);
  console.log(`  - Layout collapse check: ${!expandStats.hasLayoutCollapse ? 'PASS' : 'FAIL'}`);
  console.log(`  - Infinite expansion check: ${!expandStats.hasInfiniteLoop ? 'PASS' : 'FAIL'}`);

  // Gate 4: Theme Toggle & Persistence
  console.log('\n[Gate 4: Theme Toggle & Persistence]');
  const themeStats = await testPage.evaluate(async () => {
    const docEl = document.documentElement;
    const initialTheme = docEl.getAttribute('data-theme') || 'light';
    const expectedToggled = initialTheme === 'dark' ? 'light' : 'dark';

    const btn = document.getElementById('theme-toggle');
    btn.click();
    await new Promise(r => setTimeout(r, 200));
    const toggledTheme = docEl.getAttribute('data-theme');
    const storedTheme = localStorage.getItem('markmap-theme');
    const toggleSuccess = (toggledTheme === expectedToggled && storedTheme === expectedToggled);

    // Revert
    btn.click();
    await new Promise(r => setTimeout(r, 200));
    const revertedTheme = docEl.getAttribute('data-theme');
    const revertSuccess = (revertedTheme === initialTheme);

    return {
      initialTheme,
      toggledTheme,
      storedTheme,
      toggleSuccess,
      revertedTheme,
      revertSuccess
    };
  });
  console.log(`  - Initial Theme: ${themeStats.initialTheme}`);
  console.log(`  - Toggle Result: ${themeStats.toggledTheme} (Stored: ${themeStats.storedTheme}) - ${themeStats.toggleSuccess ? 'PASS' : 'FAIL'}`);
  console.log(`  - Revert Result: ${themeStats.revertedTheme} - ${themeStats.revertSuccess ? 'PASS' : 'FAIL'}`);

  // Gate 5: Toolbar Controls
  console.log('\n[Gate 5: Toolbar Controls (Fit, Zoom In, Zoom Out)]');
  const toolbarPass = await testPage.evaluate(() => {
    try {
      const buttons = document.querySelectorAll('.toolbar button');
      buttons[0].click();
      buttons[1].click();
      buttons[2].click();
      return true;
    } catch (e) {
      return false;
    }
  });
  console.log(`  - Toolbar Zoom/Fit handlers: ${toolbarPass ? 'PASS' : 'FAIL'}`);
  await testPage.close();

  // Gate 6: KaTeX Math Rendering Fidelity on Fresh Page
  console.log('\n[Gate 6: KaTeX Math Rendering Fidelity]');
  const mathPage = await browser.newPage();
  await mathPage.setCacheEnabled(true);
  await mathPage.goto(fileUrl, { waitUntil: 'domcontentloaded' });
  await mathPage.waitForFunction(() => window.mm && document.querySelector('.markmap svg g'));

  const katexStats = await mathPage.evaluate(async (steps) => {
    async function clickNodeWithText(snippet) {
      const nodes = Array.from(document.querySelectorAll('.markmap svg g.markmap-node'));
      for (const n of nodes) {
        if (n.textContent.includes(snippet)) {
          const circle = n.querySelector('circle');
          if (circle) {
            circle.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
            await new Promise(r => setTimeout(r, 350));
            return true;
          }
        }
      }
      return false;
    }

    for (const step of steps) {
      await clickNodeWithText(step);
    }

    const katexNodes = document.querySelectorAll('.markmap svg .katex');
    const mathml = document.querySelectorAll('.markmap svg math');

    return {
      katexCount: katexNodes.length,
      mathmlCount: mathml.length,
      sampleText: katexNodes.length > 0 ? katexNodes[0].innerText.replace(/\s+/g, ' ').trim() : null,
      sampleHtml: katexNodes.length > 0 ? katexNodes[0].outerHTML.slice(0, 160) : null
    };
  }, target.mathSteps);

  console.log(`  - Rendered KaTeX DOM elements: ${katexStats.katexCount}`);
  console.log(`  - MathML elements: ${katexStats.mathmlCount}`);
  console.log(`  - Sample KaTeX text: "${katexStats.sampleText}"`);
  console.log(`  - Sample KaTeX HTML: ${katexStats.sampleHtml}`);
  await mathPage.close();

  return {
    name: target.name,
    gate1Pass,
    avgTotal: avgTotal.toFixed(1) + ' ms',
    initialNodes: initialStats.nodes,
    expandNodes: expandStats.nodesAfterClick,
    katexRendered: katexStats.katexCount,
    themeWorking: themeStats.toggleSuccess && themeStats.revertSuccess,
    toolbarPass
  };
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const summary = [];
  for (const t of TARGETS) {
    const res = await verifyTarget(browser, t);
    summary.push(res);
  }

  await browser.close();

  console.log('\n===============================================================');
  console.log('                 FINAL VERIFICATION SUMMARY MATRIX             ');
  console.log('===============================================================');
  console.table(summary);
})();
