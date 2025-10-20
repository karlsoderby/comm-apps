// SPDX-License-Identifier: MPL-2.0

const socket = io({ path: '/socket.io' });
const grid     = document.getElementById('grid');
const clearBt  = document.getElementById('clearBtn');
const fillBt   = document.getElementById('fillBtn');
const statusEl = document.getElementById('status');

const iconName   = document.getElementById('iconName');
const saveIconBt = document.getElementById('saveIconBtn');
const iconsList  = document.getElementById('iconsList');

let W = 13, H = 8;
let frame = new Array(W*H).fill(0);
let icons = []; // [{name, frame}]


function normalizeName(s) {
  return (s || '')
    .normalize?.('NFC')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();
}
function nameExists(rawName) {
  const n = normalizeName(rawName);
  return Array.isArray(icons) && icons.some(i => normalizeName(i.name) === n);
}
// simple inline error UI
let iconErrorEl;
function ensureErrorEl() {
  if (iconErrorEl) return;
  iconErrorEl = document.createElement('div');
  iconErrorEl.id = 'iconError';
  iconErrorEl.style.color = '#b00020';
  iconErrorEl.style.fontSize = '12px';
  iconErrorEl.style.margin = '6px 0 0 0';
 
  const row = iconName.parentElement; // the div containing input+button
  row.insertAdjacentElement('afterend', iconErrorEl);
}
function setIconError(msg) {
  ensureErrorEl();
  iconErrorEl.textContent = msg || '';
  iconName.style.border = msg ? '1px solid #b00020' : '';
}

document.addEventListener('DOMContentLoaded', () => {
  socket.emit('get_initial_state', {});
  socket.emit('get_icons', {});
});

socket.on('connect', () => {
  statusEl.textContent = 'Connected';
  socket.emit('get_initial_state', {});
  socket.emit('get_icons', {});
});

socket.on('disconnect', () => {
  statusEl.textContent = 'Disconnected';
});

socket.on('state_update', (s) => {
  if (typeof s.w === 'number' && typeof s.h === 'number' && (s.w !== W || s.h !== H)) {
    W = s.w; H = s.h; frame = new Array(W*H).fill(0); rebuildGrid();
  }
  if (Array.isArray(s.frame) && s.frame.length === W*H) {
    frame = s.frame.slice();
    paintGrid();
  }
});

socket.on('icons_list', (list) => {
  if (!Array.isArray(list)) return;
  icons = list;
  renderIcons();
  // clear any error if the current input is not colliding anymore
  if (!nameExists(iconName.value)) setIconError('');
});

function rebuildGrid() {
  grid.innerHTML = '';
  grid.style.gridTemplateColumns = `repeat(${W}, 28px)`;
  for (let y=0; y<H; y++) {
    for (let x=0; x<W; x++) {
      const i = y*W + x;
      const c = document.createElement('div');
      c.className = 'cell';
      c.style.width = '28px';
      c.style.height = '28px';
      c.style.border = '1px solid #ccc';
      c.style.borderRadius = '6px';
      c.style.background = '#D9D9D9';
      c.style.cursor = 'pointer';
      c.onclick = () => {
        const newVal = frame[i] ? 0 : 1;
        frame[i] = newVal;
        paintGrid();
        socket.emit('set_xy', { x, y, value: newVal }); // explicit set
      };
      grid.appendChild(c);
    }
  }
  paintGrid();
}

function paintGrid() {
  const cells = grid.children;
  for (let i=0; i<cells.length; i++) {
    cells[i].style.background = frame[i] ? '#4c6aeeff' : '#D9D9D9';
  }
}

clearBt.onclick = () => socket.emit('clear', {});
fillBt.onclick  = () => socket.emit('fill',  {});


saveIconBt.onclick = () => {
  const raw = (iconName.value || '').trim() || 'icon';

  if (nameExists(raw)) {
    setIconError(`An icon named “${raw}” already exists. Choose another name.`);
    iconName.focus();
    iconName.select?.();
    return; // block duplicate save
  }

  setIconError('');
  socket.emit('save_icon', { name: raw, frame });
  iconName.value = raw; // keep as-is; server will refresh icons_list
};
// live-clear error as user types
iconName.addEventListener('input', () => {
  if (!nameExists(iconName.value)) setIconError('');
});


function renderIcons() {
  iconsList.innerHTML = '';
  icons.forEach(({name, frame: fr}) => {
    const item = document.createElement('div');
    item.style.display = 'grid';
    item.style.gridTemplateColumns = '1fr auto';
    item.style.alignItems = 'center';
    item.style.gap = '8px';

    // preview
    const prev = document.createElement('div');
    prev.style.display = 'grid';
    prev.style.gridTemplateColumns = `repeat(${W}, 8px)`;
    prev.style.gap = '2px';
    prev.style.cursor = 'pointer';
    prev.title = name;
    for (let i=0; i<fr.length; i++) {
      const px = document.createElement('div');
      px.style.width = '8px';
      px.style.height = '8px';
      px.style.background = fr[i] ? '#4c6aeeff' : '#D9D9D9';
      px.style.borderRadius = '2px';
      prev.appendChild(px);
    }
    prev.onclick = () => socket.emit('load_icon', { name });

    // right side controls
    const right = document.createElement('div');
    right.style.display = 'flex';
    right.style.gap = '6px';
    const label = document.createElement('span');
    label.textContent = name;
    label.style.fontFamily = 'ui-monospace, monospace';
    label.style.fontSize = '12px';
    label.style.cursor = 'pointer';
    label.onclick = () => socket.emit('load_icon', { name });

    const del = document.createElement('button');
    del.textContent = '🗑';
    del.title = `Delete "${name}"`;
    del.style.padding = '2px 6px';
    del.onclick = () => socket.emit('delete_icon', { name });

    right.appendChild(label);
    right.appendChild(del);

    item.appendChild(prev);
    item.appendChild(right);
    iconsList.appendChild(item);
  });
}

// initial build
rebuildGrid();