(function(){
  const wrap = document.getElementById('odontograma-wrap');
  if(!wrap) return;

  const svg = document.getElementById('odontograma-svg');
  const menu = document.getElementById('odonto-menu');
  const tip  = document.getElementById('odonto-tip');
  const sel  = document.getElementById('odonto-status');
  const note = document.getElementById('odonto-note');
  const btnSave = document.getElementById('odonto-save');
  const btnCancel = document.getElementById('odonto-cancel');

  const saveURL = wrap.dataset.saveUrl;
  const state = (window.ODONTO_STATE || {});

  const color = {
    saudavel:  '#16a34a',
    carie:     '#ef4444',
    restauracao:'#f59e0b',
    canal:     '#3b82f6',
    fratura:   '#eab308',
    ausente:   '#94a3b8',
    implante:  '#22d3ee',
    protese:   '#a855f7',
    mobilidade:'#fb7185',
    placa:     '#f97316'
  };

function updateRegistroTable(tooth, status, note){
  const tbody = document.getElementById('odontograma-tbody');
  if(!tbody) return;

  // Remove "Sem registros." row if present
  const empty = tbody.querySelector('tr[data-empty="1"]');
  if(empty) empty.remove();

  // Try to find existing row by tooth
  let row = Array.from(tbody.querySelectorAll('tr[data-tooth]')).find(tr => tr.getAttribute('data-tooth') === String(tooth));
  const now = new Date();
  const pad = n => String(n).padStart(2,'0');
  const stamp = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  if(!row){
    row = document.createElement('tr');
    row.setAttribute('data-tooth', String(tooth));
    row.innerHTML = `<td></td><td></td><td></td><td></td>`;
    if(tbody.firstChild) tbody.insertBefore(row, tbody.firstChild);
    else tbody.appendChild(row);
  }
  const tds = row.querySelectorAll('td');
  if(tds[0]) tds[0].textContent = tooth;
  if(tds[1]) tds[1].textContent = status;
  if(tds[2]) tds[2].textContent = note || '';
  if(tds[3]) tds[3].textContent = stamp;

  row.setAttribute('data-tooth', String(tooth));
}



  function paintTooth(g, status){
    const r = g.querySelector('rect');
    if(!r) return;
    const c = color[status];
    r.setAttribute('fill', c || '#ffffff');
    r.setAttribute('stroke', c || '#c7d1bb');
    g.querySelectorAll('text').forEach(text => text.setAttribute('fill', c ? '#ffffff' : '#5b6b50'));
    g.setAttribute('aria-label', 'Dente ' + g.dataset.tooth + ': ' + (status || 'sem status'));
  }

  Array.from(svg.querySelectorAll('g.tooth')).forEach(g=>{
    const t = g.dataset.tooth;
    if(state[t]) paintTooth(g, state[t]);
  });

  function showTip(txt, evt){
    if(!txt){ tip.style.display='none'; return; }
    tip.textContent = txt;
    const bounds = wrap.getBoundingClientRect();
    tip.style.left = Math.max(0, Math.min(evt.clientX - bounds.left + 12, wrap.clientWidth - 180)) + 'px';
    tip.style.top = (evt.clientY - bounds.top + 12) + 'px';
    tip.style.display = 'block';
  }

  svg.addEventListener('mousemove', (e)=>{
    const g = e.target.closest('g.tooth');
    if(!g){ tip.style.display='none'; return; }
    const tooth = g.dataset.tooth;
    const s = state[tooth];
    showTip(`Dente ${tooth}: ${s ? s : '(sem status)'}`, e);
  });
  svg.addEventListener('mouseleave', ()=> tip.style.display='none');

  let currentTooth = null;
  function openMenu(g, evt){
    currentTooth = g.dataset.tooth;
    sel.value = state[currentTooth] || 'saudavel';
    note.value = '';
    const rect = wrap.getBoundingClientRect();
    const targetBounds = g.getBoundingClientRect();
    const x = (evt.clientX || targetBounds.left) - rect.left + 6;
    const y = (evt.clientY || targetBounds.bottom) - rect.top + 6;
    menu.style.display = 'block';
    menu.style.left = Math.max(0, Math.min(x, wrap.clientWidth - menu.offsetWidth)) + 'px';
    menu.style.top = Math.max(0, y) + 'px';
    svg.querySelectorAll('g.tooth').forEach(t=>t.classList.remove('selected'));
    g.classList.add('selected');
  }
  function closeMenu(){
    menu.style.display = 'none';
    svg.querySelectorAll('g.tooth').forEach(t=>t.classList.remove('selected'));
    currentTooth = null;
  }

  svg.addEventListener('click', (e)=>{
    const g = e.target.closest('g.tooth');
    if(!g) return;
    openMenu(g, e);
  });
  svg.addEventListener('keydown', (e) => {
    const tooth = e.target.closest('g.tooth');
    if (tooth && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      openMenu(tooth, e);
      sel.focus();
    }
  });
  menu.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const selected = svg.querySelector('g.tooth.selected');
      closeMenu();
      selected?.focus();
    }
  });
  document.getElementById('odonto-cancel').addEventListener('click', (e)=>{ e.preventDefault(); closeMenu(); });

  document.getElementById('odonto-save').addEventListener('click', async (e)=>{
    e.preventDefault();
    if(!currentTooth) return;
    const payload = { tooth: String(currentTooth), status: sel.value, note: note.value || '' };
    try{
      const res = await fetch(saveURL, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      const j = await res.json();
      if(j && j.ok){
        state[currentTooth] = payload.status;
        const g = svg.querySelector(`g.tooth[data-tooth="${currentTooth}"]`);
        if(g) paintTooth(g, payload.status);
        try{ updateRegistroTable(payload.tooth, payload.status, payload.note); }catch(e){}
        closeMenu();
      }else{
        alert('Falha ao salvar: ' + (j && j.error ? j.error : 'desconhecido'));
      }
    }catch(err){
      alert('Erro de rede ao salvar: ' + err.message);
    }
  });
})();
