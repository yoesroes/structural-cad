// C2: uji perilaku XSS yang menangkap breakout ATRIBUT dan sink yang tidak ter-escape.
// Pemakaian: node tests/ui/xss_attr_harness.js [jalur/app.js]
// Keluar 0 + "ok" bila aman; keluar 1 + pesan bila ada tag/atribut berbahaya.
const fs = require('fs');
const srcPath = process.argv[2] || 'src/scad_ui/static/app.js';
const src = fs.readFileSync(srcPath, 'utf8');

function extractFn(name) {
  const start = src.search(new RegExp('function ' + name + '\\s*\\('));
  if (start < 0) throw new Error('fungsi tidak ditemukan: ' + name);
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error('kurung tidak seimbang: ' + name);
}

function el(id) {
  return { id, innerHTML: '', textContent: '', querySelectorAll() { return []; }, addEventListener() {} };
}
const store = { sidebar: el('sidebar'), tbody: el('tbody'), props: el('props') };
global.document = {
  getElementById(id) { return id === 'sidebar' ? store.sidebar : id === 'props' ? store.props : el(id); },
  querySelector(sel) { return sel.includes('tbody') ? store.tbody : null; },
};

// Semua fungsi yang dipakai renderer diekstrak; fungsi baru di app.js yang dipanggil
// renderer tetapi tidak tercantum di sini akan memunculkan ReferenceError (sengaja).
for (const fn of ['escapeHtml', 'statusForPile', 'renderSidebar', 'renderTable', 'renderProps']) {
  (0, eval)(extractFn(fn).replace(/^function (\w+)/, 'globalThis.$1 = function $1'));
}

// Payload: breakout atribut TANPA '<', serta tag mentah di konteks teks.
// Satu payload gabungan dipakai di SEMUA field: tag mentah ('<'), breakout atribut ('"' dan "'"),
// serta '&' (entity literal), sehingga sink yang kehilangan escape di konteks mana pun terdeteksi.
const ID2 = 'P-2';  // id kedua yang aman agar pileMap tidak saling menimpa
const COMBO = '<b onmouseover=alert(1)>x" onfocus="alert(1)&lt;\'';
const ATTR = COMBO;
const TAG = COMBO;
const doc = {
  project: { name: TAG, id: 'X' },
  materials: { concrete: { grade: ATTR }, steel: { grade: TAG } },
  groups: [{
    id: ATTR, type: TAG,
    definition: { data: {
      params: { diameter: TAG, cover: TAG, cover_ref: ATTR, depth_below_cof: 30000 },
      materials: { concrete: { grade: TAG }, steel: { grade: ATTR } },
      rebars: [
        { id: ATTR, diameter: TAG, shape: { code: ATTR }, extent: { zones: [TAG, ATTR] } },
        { id: TAG, diameter: ATTR, shape: { code: TAG }, extent: { zones: [ATTR] } },
      ],
    } },
    instances: [{ id: ATTR }, { id: ID2 }],
  }],
};
const resolved = {
  groups: [{
    id: ATTR,
    piles: [
      { id: ATTR, x: TAG, y: ATTR, depth_below_cof: TAG, overridden: ['depth_below_cof'], zones: [{ id: 'Z3', length: TAG }] },
      { id: ID2, x: 0, y: 0, depth_below_cof: ATTR, overridden: [], zones: [{ id: 'Z3', length: ATTR }] },
    ],
  }],
  issues: [
    { level: 'error', code: TAG, pile: ATTR, path: '/groups/0/instances/0', message: TAG },
    { level: 'warning', code: ATTR, pile: ID2, path: '/groups/0/instances/1', message: ATTR },
  ],
};
globalThis.resolveData = resolved;

renderSidebar(doc, resolved);
renderTable(resolved);
renderProps(doc, doc.groups[0], resolved.groups[0].piles[0]);

// --- Penguraian tag sederhana yang menghormati tanda kutip ---
const ALLOWED_TAGS = new Set(['div', 'span', 'button', 'tr', 'td']);
const ALLOWED_ATTRS = new Set(['class', 'data-group', 'data-pile', 'onclick', 'disabled', 'title', 'aria-disabled']);
const TAG_RE = /<\/?([a-zA-Z][a-zA-Z0-9-]*)((?:\s+[^\s"'<>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'<>=`]+))?)*)\s*\/?>/g;
const ATTR_RE = /([^\s"'<>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>=`]+)))?/g;
const decode = (s) => s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const fail = (msg, html) => { console.error('GAGAL:', msg, '\n  ...', html.slice(0, 240)); process.exit(1); };

const names = ['sidebar', 'tabel', 'props'];
[store.sidebar.innerHTML, store.tbody.innerHTML, store.props.innerHTML].forEach((html, n) => {
  // 1) Setelah semua tag SAH dibuang, tidak boleh tersisa '<' (tag mentah dari payload).
  const rest = html.replace(TAG_RE, '');
  if (rest.includes('<')) fail(`${names[n]}: sisa '<' mentah setelah tag sah dibuang`, rest);
  // 2) Setiap tag yang muncul harus dari daftar putih, dengan atribut dari daftar putih.
  let m;
  TAG_RE.lastIndex = 0;
  while ((m = TAG_RE.exec(html)) !== null) {
    if (!ALLOWED_TAGS.has(m[1].toLowerCase())) fail(`${names[n]}: tag tak dikenal <${m[1]}>`, html);
    let a;
    ATTR_RE.lastIndex = 0;
    while ((a = ATTR_RE.exec(m[2] || '')) !== null) {
      const name = a[1].toLowerCase();
      if (!ALLOWED_ATTRS.has(name)) fail(`${names[n]}: atribut tak dikenal "${name}" pada <${m[1]}>`, html);
      const val = a[2] ?? a[3] ?? a[4] ?? '';
      if (name === 'onclick' && val !== 'openRebarModal()') fail(`${names[n]}: onclick tak dikenal`, html);
      if ((name === 'data-pile' || name === 'data-group') && ![COMBO, ID2].includes(decode(val))) {
        fail(`${names[n]}: nilai ${name} tidak sama dengan payload asli (escape salah)`, html);
      }
    }
  }
});
// 3) Pastikan data-pile benar-benar membawa payload atribut utuh (bukan terpotong di tanda kutip).
if (!store.sidebar.innerHTML.includes('data-pile="' + '&lt;b onmouseover=alert(1)&gt;x&quot; onfocus=&quot;alert(1)&amp;lt;&#39;' + '"')) {
  fail("sidebar: data-pile tidak membawa payload atribut ter-escape penuh", store.sidebar.innerHTML);
}
console.log('ok');
