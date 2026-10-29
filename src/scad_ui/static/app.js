(function () {
  let projectDoc = null;
  let resolveData = null;

  // --- Menu dropdown ---
  const fileMenu = document.getElementById('menu-file');
  document.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      const isFile = item.dataset.menu === 'file';
      document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
      if (isFile) {
        item.classList.add('active');
        fileMenu.classList.toggle('show');
      } else {
        fileMenu.classList.remove('show');
        item.classList.add('active');
      }
    });
  });
  document.addEventListener('click', () => fileMenu.classList.remove('show'));

  // --- View tabs ---
  document.querySelectorAll('.vtab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.vtab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
    });
  });

  function formatCof(doc) {
    const cof = doc?.project?.datum?.cof_elevation;
    if (cof == null) return '—';
    // tampilkan meter jika besar
    if (Math.abs(cof) >= 100) return (cof / 1000).toFixed(2).replace('.', ',') + ' m';
    return cof + ' mm';
  }

  function renderSidebar(doc, resolved) {
    const sidebar = document.getElementById('sidebar');
    const group = (doc.groups || [])[0];
    if (!group) {
      sidebar.innerHTML = '<div class="h">Pohon</div><div class="tree-muted">Belum ada grup</div>';
      return;
    }
    const piles = (resolved?.groups || []).find(g => g.id === group.id)?.piles || [];
    const pileMap = Object.fromEntries(piles.map(p => [p.id, p]));
    let html = '<div class="h">Pohon</div>';
    html += `<div class="tree-root">${doc.project?.name || doc.project?.id || 'Project'}</div>`;
    const n = (group.instances || []).length;
    html += `<div class="tree-group active" data-group="${group.id}">${group.id} · ${group.type || 'element'} (${n})</div>`;
    (group.instances || []).forEach((inst, idx) => {
      const rp = pileMap[inst.id];
      const ov = rp && rp.overridden && rp.overridden.includes('depth_below_cof');
      const depth = rp ? rp.depth_below_cof : '';
      const mark = ov ? ` <span class="ov">● ${depth}</span>` : '';
      const active = idx === 0 ? ' active' : '';
      html += `<div class="tree-item${active}" data-pile="${inst.id}">${inst.id}${mark}</div>`;
    });
    sidebar.innerHTML = html;

    sidebar.querySelectorAll('.tree-item[data-pile]').forEach(el => {
      el.addEventListener('click', () => {
        sidebar.querySelectorAll('.tree-item').forEach(t => t.classList.remove('active'));
        el.classList.add('active');
        const id = el.dataset.pile;
        const rp = pileMap[id];
        const depth = rp ? rp.depth_below_cof : '?';
        document.getElementById('view-title').textContent =
          `Pile ${id} · kedalaman ${depth} mm`;
        renderProps(doc, group, rp);
      });
    });
  }

  function renderTable(resolved) {
    const group = (resolved?.groups || [])[0];
    const piles = group?.piles || [];
    const tbody = document.querySelector('#bottom table tbody');
    if (!tbody) return;
    tbody.innerHTML = piles.map(p => {
      const z3 = (p.zones || []).find(z => z.id === 'Z3');
      const z3len = z3 ? z3.length : '—';
      const depthCell = (p.overridden || []).includes('depth_below_cof')
        ? `<td class="ov">${p.depth_below_cof} ●</td>`
        : `<td>${p.depth_below_cof} (grup)</td>`;
      return `<tr>
        <td>${p.id}</td>
        <td>${p.x ?? ''}</td>
        <td>${p.y ?? ''}</td>
        ${depthCell}
        <td>${z3len}</td>
        <td>Sesuai</td>
      </tr>`;
    }).join('');
  }

  function renderProps(doc, group, pileResolved) {
    const props = document.getElementById('props');
    const data = (group.definition || {}).data || {};
    const params = data.params || {};
    const mats = data.materials || doc.materials || {};
    const rebars = data.rebars || [];
    const depth = pileResolved ? pileResolved.depth_below_cof : params.depth_below_cof;
    let html = `<div class="h" style="margin-top:0">Grup ${group.id}</div>`;
    html += `<div class="r"><span>Diameter</span><span>${params.diameter ?? '—'} mm</span></div>`;
    html += `<div class="r"><span>Kedalaman</span><span>${depth ?? '—'} mm</span></div>`;
    html += `<div class="r"><span>Selimut</span><span>${params.cover ?? '—'} mm (${params.cover_ref || ''})</span></div>`;
    const beton = mats.concrete?.grade || '—';
    const baja = mats.steel?.grade || '—';
    html += `<div class="r"><span>Beton / Baja</span><span>${beton} / ${baja}</span></div>`;
    html += `<div class="h">Tulangan</div>`;
    rebars.forEach(r => {
      const shape = r.shape?.code || r.shape || '';
      const zones = (r.extent?.zones || []).join(',');
      html += `<div class="r"><span>${r.id} ${shape} D${r.diameter}</span><span>${zones}</span></div>`;
    });
    html += `<button class="btn-accent" onclick="openRebarModal()">+ Tambah tulangan</button>`;
    html += `<div class="h">Pemeriksaan</div>`;
    const nIssues = (resolveData?.issues || []).length;
    html += `<div class="r"><span>Issue resolve</span><span class="${nIssues ? 'status-warn' : 'status-ok'}">${nIssues || 0}</span></div>`;
    props.innerHTML = html;
  }

  function renderCanvas() {
    const svg = `
<svg viewBox="0 0 640 490" width="720" height="490" role="img"
     aria-label="Tampak dan potongan bored pile dengan zona">
  <g stroke="#1d2330" fill="none" stroke-width="1.3">
    <rect x="150" y="30" width="60" height="420"/>
  </g>
  <g fill="#e3ebfa" stroke="#9db6e8">
    <rect x="150" y="30" width="60" height="30"/>
  </g>
  <g stroke="#1f5fd0" stroke-width="1">
    <line x1="150" y1="60" x2="210" y2="60"/>
    <line x1="150" y1="130" x2="210" y2="130"/>
    <line x1="150" y1="260" x2="210" y2="260"/>
  </g>
  <g stroke="#1d2330" stroke-width="1.3">
    <line x1="145" y1="450" x2="215" y2="450"/>
  </g>
  <g font-size="12" fill="#1d2330">
    <text x="225" y="50">Z0 (di atas Cof)</text>
    <text x="225" y="100">Z1 · B1 · B2</text>
    <text x="225" y="200">Z2 · B1 · B3</text>
    <text x="225" y="360">Z3 (fleksibel / rest)</text>
    <text x="225" y="465" fill="#5a6270">ujung pile</text>
    <text x="60" y="64" fill="#1f5fd0">Cof</text>
  </g>
  <g stroke="#1d2330" fill="none" stroke-width="1.3">
    <circle cx="500" cy="170" r="70"/>
  </g>
  <g stroke="#2a7a4b" fill="none">
    <circle cx="500" cy="170" r="62"/>
  </g>
  <g fill="#b3261e">
    <circle cx="500" cy="115" r="4"/>
    <circle cx="539" cy="131" r="4"/>
    <circle cx="555" cy="170" r="4"/>
    <circle cx="539" cy="209" r="4"/>
    <circle cx="500" cy="225" r="4"/>
    <circle cx="461" cy="209" r="4"/>
    <circle cx="445" cy="170" r="4"/>
    <circle cx="461" cy="131" r="4"/>
  </g>
  <text x="440" y="270" font-size="12" fill="#1d2330">Potongan skematik</text>
  <text x="440" y="290" font-size="12" fill="#5a6270">Data dari project v1</text>
</svg>`;
    document.getElementById('canvas-body').innerHTML = svg;
  }

  async function loadProject() {
    try {
      const res = await fetch('/api/project');
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || 'Gagal muat project');
      projectDoc = data.project;
      const rres = await fetch('/api/project/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc: projectDoc }),
      });
      const rd = await rres.json();
      if (!rd.ok) throw new Error(rd.error || 'Gagal resolve');
      resolveData = rd;

      const name = projectDoc.project?.name || projectDoc.project?.id || 'Project';
      document.querySelector('.menu-right').textContent =
        `${name} · Cof ${formatCof(projectDoc)} · mm`;
      const ptab = document.querySelector('#project-tabs .ptab');
      if (ptab) ptab.textContent = name;

      const group = (projectDoc.groups || [])[0];
      renderSidebar(projectDoc, resolveData);
      renderTable(resolveData);
      if (group) {
        const firstPile = resolveData.groups?.[0]?.piles?.[0];
        renderProps(projectDoc, group, firstPile);
        if (firstPile) {
          document.getElementById('view-title').textContent =
            `Pile ${firstPile.id} · kedalaman ${firstPile.depth_below_cof} mm`;
        }
      }
      renderCanvas();
      const n = (resolveData.issues || []).length;
      document.getElementById('cmd-input').placeholder =
        n ? `${n} issue pada resolve` : 'SET P1-2 DEPTH 26000';
    } catch (err) {
      console.error(err);
      document.getElementById('cmd-input').placeholder =
        'Server tidak tersedia — buka lewat python -m pilecap_rebar.ui';
      renderCanvas();
    }
  }

  // --- Modal ---
  window.openRebarModal = function () {
    document.getElementById('rebar-modal').classList.add('show');
  };
  window.closeRebarModal = function () {
    document.getElementById('rebar-modal').classList.remove('show');
  };
  window.addRebar = function () {
    closeRebarModal();
    document.getElementById('cmd-input').placeholder = 'Tambah tulangan: belum disimpan ke model v1';
  };
  document.getElementById('rebar-modal').addEventListener('click', (e) => {
    if (e.target.id === 'rebar-modal') closeRebarModal();
  });
  document.querySelectorAll('.shape-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.shape-item').forEach(s => s.classList.remove('selected'));
      item.classList.add('selected');
    });
  });

  document.getElementById('cmd-input').addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const cmd = e.target.value.trim();
    if (!cmd || !projectDoc) return;
    // Parser minimal: SET <pile> DEPTH <mm>
    const m = cmd.match(/^SET\s+(\S+)\s+DEPTH\s+(\d+(?:\.\d+)?)$/i);
    if (m) {
      const pileId = m[1];
      const depth = Number(m[2]);
      const res = await fetch(`/api/pile/${encodeURIComponent(pileId)}/depth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ depth }),
      });
      const data = await res.json();
      e.target.value = '';
      if (!data.ok) {
        e.target.placeholder = data.error || 'Gagal';
        return;
      }
      e.target.placeholder = `OK ${pileId} depth=${depth}`;
      await loadProject();
      return;
    }
    e.target.placeholder = 'Sintaks: SET <pile> DEPTH <mm>';
    e.target.value = '';
  });

  window.action = function (name) {
    console.log('Action:', name);
    fileMenu.classList.remove('show');
    if (name === 'save-project' && projectDoc) {
      fetch('/api/project/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectDoc),
      }).then(r => r.json()).then(d => {
        document.getElementById('cmd-input').placeholder =
          d.ok ? `Tersimpan: ${d.path}` : (d.error || 'Gagal simpan');
      });
    }
  };

  loadProject();
})();

// Modular API bridge for the active UI. The visual shell above remains framework-free.
window.StructuralCadUI = Object.freeze({
  async request(path, body, method = 'POST') {
    const response = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: method === 'GET' ? undefined : JSON.stringify(body ?? {}),
    });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
  },
  getProject() { return this.request('/api/project', undefined, 'GET'); },
  openProject(path) { return this.request('/api/project/open', { path }); },
  saveProject(doc, path) {
    return this.request('/api/project/save', { doc, ...(path ? { path } : {}) });
  },
  validate(doc) { return this.request('/api/validate', { doc }); },
  run2d(doc, options = {}) { return this.request('/run-2d', { doc, ...options }); },
  run3d(doc, options = {}) { return this.request('/run-3d', { doc, ...options }); },
});
window.dispatchEvent(new CustomEvent('structural-cad-ready', { detail: window.StructuralCadUI }));
