// ════════════════════════════════════════
// Sidebar & profile collapse
// ════════════════════════════════════════
function toggleSidebar() {
  const sb  = document.getElementById('sidebar');
  const btn = document.getElementById('btn-menu');
  const ov  = document.getElementById('sb-overlay');
  const open = sb.classList.toggle('open');
  btn.classList.toggle('open', open);
  ov.classList.toggle('visible', open);
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('btn-menu').classList.remove('open');
  document.getElementById('sb-overlay').classList.remove('visible');
}


// ════════════════════════════════════════
// Password reveal toggle
// ════════════════════════════════════════
function togglePassword() {
  const input = document.getElementById('f-password');
  const icon  = document.getElementById('eye-icon');
  const show  = input.type === 'password';
  input.type  = show ? 'text' : 'password';
  // Switch between open-eye and closed-eye icons
  icon.innerHTML = show
    ? `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
       <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
       <line x1="1" y1="1" x2="23" y2="23"/>`
    : `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
       <circle cx="12" cy="12" r="3"/>`;
}

// ════════════════════════════════════════
// Auth state
// ════════════════════════════════════════
let authMode    = 'login';
let currentUser = null;

function switchTab(mode) {
  authMode = mode;
  document.getElementById('tab-login').classList.toggle('active',    mode === 'login');
  document.getElementById('tab-register').classList.toggle('active', mode === 'register');
  document.getElementById('form-title').textContent = mode === 'login' ? 'Welcome back'   : 'Create account';
  document.getElementById('form-sub').textContent   = mode === 'login'
    ? 'Sign in to your Academia account'
    : 'Join Academia to save your searches';
  document.getElementById('btn-submit').textContent = mode === 'login' ? 'Sign In' : 'Create Account';
  setNotice('', '');
}

function setNotice(msg, type) {
  const el = document.getElementById('auth-notice');
  if (!msg) { el.className = ''; el.textContent = ''; return; }
  el.className = `auth-notice ${type}`;
  el.textContent = msg;
}

function googleNotice() {
  setNotice('Google sign-in requires OAuth configuration. Use email/password for now.', 'error');
}

async function submitAuth() {
  const email    = document.getElementById('f-email').value.trim();
  const password = document.getElementById('f-password').value.trim();
  const btn      = document.getElementById('btn-submit');

  setNotice('', '');
  if (!email || !password) { setNotice('Please fill in both fields.', 'error'); return; }

  btn.disabled    = true;
  btn.textContent = authMode === 'login' ? 'Signing in…' : 'Creating account…';

  const url = authMode === 'login' ? '/login' : '/register';
  try {
    const res  = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email, password})
    });
    const data = await res.json();

    if (!res.ok) {
      setNotice(data.error, 'error');
    } else {
      currentUser = data.user;
      transitionToApp();
    }
  } catch {
    setNotice('Connection error. Is Flask running?', 'error');
  }

  btn.disabled    = false;
  btn.textContent = authMode === 'login' ? 'Sign In' : 'Create Account';
}

// Enter key
document.getElementById('f-password').addEventListener('keydown', e => {
  if (e.key === 'Enter') submitAuth();
});
document.getElementById('f-email').addEventListener('keydown', e => {
  if (e.key === 'Enter') submitAuth();
});

// ════════════════════════════════════════
// Screen transition
// ════════════════════════════════════════
function transitionToApp() {
  // Populate profile
  const name  = currentUser.display_name || currentUser.email.split('@')[0];
  const email = currentUser.email;
  const initials = name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();

  document.getElementById('profile-avatar').textContent = initials;
  document.getElementById('topbar-avatar').textContent  = initials;
  document.getElementById('profile-name').textContent   = name;
  document.getElementById('profile-email').textContent  = email;

  // Animate out auth, in app
  document.getElementById('auth-screen').classList.add('hiding');
  document.getElementById('app-screen').classList.add('visible');
  document.body.style.overflow = 'hidden';

  setTimeout(() => {
    document.getElementById('auth-screen').style.display = 'none';
    document.body.style.overflow = '';   // restore scrolling once transition is done
  }, 800);

  loadHistory();
  fetchStats();
  loadBrowse();
}

async function doSignOut() {
  await fetch('/logout', {method: 'POST'});
  window.location.reload();
}

// ════════════════════════════════════════
// Session restore on page load
// ════════════════════════════════════════
async function init() {
  try {
    const res  = await fetch('/me');
    const data = await res.json();
    if (data.logged_in) {
      currentUser = { email: data.email, display_name: data.display_name };
      transitionToApp();
    }
  } catch { /* show auth screen */ }
}

// ════════════════════════════════════════
// History
// ════════════════════════════════════════
async function loadHistory() {
  try {
    const res  = await fetch('/history');
    if (!res.ok) return;
    const data = await res.json();
    renderHistory(data.history);
  } catch {}
}

function renderHistory(items) {
  document.getElementById('h-count').textContent = items.length;
  if (!items.length) {
    document.getElementById('h-list').innerHTML = '<div class="h-empty">No searches yet.</div>';
    return;
  }
  document.getElementById('h-list').innerHTML = items.map(h => `
    <div class="h-item" data-query="${esc(h.query)}">
      <div class="h-query-row">
        <div class="h-query">${esc(h.query)}</div>
        <button class="h-delete" data-query="${esc(h.query)}" aria-label="Delete">✕</button>
      </div>
      <div class="h-meta">
        <span>${h.results_count} results</span>
        <span>${fmtDate(h.searched_at)}</span>
      </div>
    </div>`).join('');
}

function fmtDate(dt) {
  return new Date(dt).toLocaleDateString('en-GB', {day:'numeric', month:'short'});
}

// ════════════════════════════════════════
// Stats
// ════════════════════════════════════════
async function fetchStats() {
  try {
    const res  = await fetch('/stats');
    const data = await res.json();
    document.getElementById('article-count').textContent = data.total_articles.toLocaleString();
  } catch {}
}

// ════════════════════════════════════════
// Browse (homepage topic groups)
// ════════════════════════════════════════
async function loadBrowse() {
  const con = document.getElementById('results-container');
  con.innerHTML = '<div class="loader"><span></span><span></span><span></span></div>';
  try {
    const res  = await fetch('/browse');
    const data = await res.json();
    renderBrowse(data.groups);
  } catch {
    con.innerHTML = '<div class="err">⚠ Could not load articles. Is Flask running?</div>';
  }
}

function renderBrowse(groups) {
  const con = document.getElementById('results-container');
  if (!groups || !groups.length) {
    con.innerHTML = `<div class="state-box">
      <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
      <div class="state-title">No articles yet</div>
      <p>Run <code>python arxiv_fetch.py</code> to populate the database.</p></div>`;
    return;
  }

  const header = `<div class="browse-header">
    <div class="browse-title">Explore by Topic</div>

  </div>`;

  const groupsHtml = groups.map((g, gi) => `
    <div class="topic-group">
      <div class="topic-label">${esc(g.topic)}</div>
      <div class="topic-cards">
        ${g.articles.map(a => `
        <div class="card" data-url="${esc(a.url || '')}">
          <div class="card-top">
            <div class="card-title">${esc(a.title)}</div>
          </div>
          <div class="card-meta">
            <span><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>${esc(a.authors)}</span>
            <span><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/></svg>${esc(a.journal)}</span>
            <span><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${a.year}</span>
          </div>
          <div class="card-abstract">${esc(a.abstract)}</div>
        </div>`).join('')}
      </div>
    </div>`).join('');

  con.innerHTML = header + groupsHtml;
  observeCards();
}

// ════════════════════════════════════════
// Search
// ════════════════════════════════════════
document.getElementById('query-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

function setQ(q) {
  document.getElementById('query-input').value = q;
  doSearch();
}

async function doSearch() {
  const query = document.getElementById('query-input').value.trim();
  if (!query) { document.getElementById('query-input').focus(); return; }

  const btn = document.getElementById('btn-search');
  const con = document.getElementById('results-container');

  btn.disabled = true;
  btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 0.8s linear infinite"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Searching…`;
  con.innerHTML = `<div class="loader"><span></span><span></span><span></span></div>`;

  try {
    const res  = await fetch('/recommend', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query})
    });
    const data = await res.json();
    if (!res.ok) {
      con.innerHTML = `<div class="err">⚠ ${data.error}</div>`;
    } else {
      renderResults(data.results, data.query);
      loadHistory();
    }
  } catch {
    con.innerHTML = `<div class="err">⚠ Could not connect. Is Flask running?</div>`;
  }

  btn.disabled = false;
  btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg> Search`;
}

function queryKeywords(query) {
  const stop = new Set(['a','an','the','of','in','for','on','with','and','or','to','by',
                        'from','using','based','via','towards','approach','study','analysis',
                        'about','into','over','its','this','that','are','was','were','is']);
  return query.toLowerCase()
    .split(/\s+/)
    .map(w => w.replace(/[^a-z0-9]/g, ''))
    .filter(w => w.length > 2 && !stop.has(w));
}

function randomTitleWord(title) {
  const stop = new Set(['a','an','the','of','in','for','on','with','and','or','to','by',
                        'from','using','based','via','towards','approach','study','analysis',
                        'about','into','over','its','this','that','are','was','were','is',
                        'not','but','nor','so','yet','both','either','whether','while',
                        'between','among','across','through','during','without','within']);
  const words = String(title).toLowerCase()
    .split(/\s+/)
    .map(w => w.replace(/[^a-z0-9]/g, ''))
    .filter(w => w.length > 3 && !stop.has(w));
  if (!words.length) return 'article';
  return words[Math.floor(Math.random() * words.length)];
}

function renderResults(results, query) {
  const keywords = queryKeywords(query);
  const hdr = `
    <div class="results-hdr">
      <div class="results-title">Results for <span>"${esc(query)}"</span></div>
      <div class="r-count">${results.length} article${results.length!==1?'s':''}</div>
    </div>`;

  const cards = results.map((r, i) => {
    const kw = randomTitleWord(r.title);
    return `
    <div class="card-divider"><span class="divider-kw">${esc(kw)}</span></div>
    <div class="card" data-url="${esc(r.url || '')}">
      <div class="card-top">
        <div class="card-title">${esc(r.title)}</div>
        <div class="score-badge">⬡ ${r.score}%</div>
      </div>
      <div class="card-meta">
        <span><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>${esc(r.authors)}</span>
        <span><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/></svg>${esc(r.journal)}</span>
        <span><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${r.year}</span>
      </div>
      <div class="card-abstract">${esc(r.abstract)}</div>
    </div>`;
  }).join('');

  document.getElementById('results-container').innerHTML = hdr + cards;
  observeCards();
}

// ════════════════════════════════════════
// Scroll-reveal animation for article cards
// ════════════════════════════════════════
const cardObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in-view');
      cardObserver.unobserve(entry.target);   // animate once per card
    }
  });
}, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

function observeCards() {
  // Stagger reveal slightly for cards that are already in the same batch
  const cards = document.querySelectorAll('.card:not(.in-view)');
  cards.forEach((card, i) => {
    card.style.transitionDelay = `${Math.min(i % 6, 5) * 70}ms`;
    cardObserver.observe(card);
  });
}

function openArticle(url) {
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer');
  } else {
    alert('No external source link is available for this article.');
  }
}

// Event delegation: handle clicks on article cards (data-url) and history items (data-query)
document.addEventListener('click', function(e) {
  const card = e.target.closest('.card[data-url]');
  if (card) {
    openArticle(card.getAttribute('data-url'));
    return;
  }
  const delBtn = e.target.closest('.h-delete');
  if (delBtn) {
    e.stopPropagation();
    deleteSearch(delBtn.getAttribute('data-query'));
    return;
  }
  const hItem = e.target.closest('.h-item[data-query]');
  if (hItem) {
    setQ(hItem.getAttribute('data-query'));
  }
});

async function deleteSearch(query) {
  try {
    await fetch('/history/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query})
    });
    loadHistory();
  } catch {}
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function topKeyword(keywords) {
  if (!keywords) return '';
  // keywords are semicolon-separated e.g. "deep; learning; neural"
  const parts = String(keywords).split(';').map(k => k.trim()).filter(k => k.length > 2);
  return parts[0] || '';
}

init();