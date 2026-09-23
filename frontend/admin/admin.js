// Admin Panel - Separate from user-facing app
const API = 'https://vektra-backend-qic7.onrender.com';
let authToken = null;
let currentUser = null;
let adminUserOffset = 0;
const adminUserLimit = 20;

// Check if already logged in
window.addEventListener('DOMContentLoaded', async () => {
  const savedToken = localStorage.getItem('vektra_admin_token');
  if (savedToken) {
    authToken = savedToken;
    await verifyAdminToken();
  }
});

async function verifyAdminToken() {
  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      currentUser = await res.json();
      if (currentUser.username === 'roophy') {
        showAdminDashboard();
      } else {
        logoutAdmin();
      }
    } else {
      logoutAdmin();
    }
  } catch (e) {
    logoutAdmin();
  }
}

async function adminLogin() {
  const username = document.getElementById('admin-login-username').value;
  const password = document.getElementById('admin-login-password').value;
  const errorEl = document.getElementById('admin-login-error');
  const btn = document.getElementById('admin-login-btn');
  
  if (!username || !password) {
    errorEl.textContent = 'Please enter username and password';
    errorEl.style.display = 'block';
    return;
  }
  
  btn.disabled = true;
  btn.textContent = 'Authenticating...';
  
  try {
    const res = await fetch(`${API}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
    });

    const data = await res.json();
    
    if (res.ok) {
      authToken = data.access_token;
      localStorage.setItem('vektra_admin_token', authToken);
      
      // Verify it's the admin user
      const userRes = await fetch(`${API}/api/v1/users/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      
      if (userRes.ok) {
        currentUser = await userRes.json();
        if (currentUser.username === 'roophy') {
          showAdminDashboard();
        } else {
          errorEl.textContent = 'Admin access required';
          errorEl.style.display = 'block';
          logoutAdmin();
        }
      }
    } else {
      errorEl.textContent = data.detail || 'Login failed';
      errorEl.style.display = 'block';
    }
  } catch (e) {
    errorEl.textContent = 'Connection error';
    errorEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Access Admin Panel';
  }
}

function showAdminDashboard() {
  document.getElementById('admin-login').style.display = 'none';
  document.getElementById('admin-dashboard').style.display = 'flex';
  loadAdminStats();
  loadAdminUsers();
  loadAdminActivity();
  loadLandingClickStats();
}

function adminLogout() {
  localStorage.removeItem('vektra_admin_token');
  authToken = null;
  currentUser = null;
  document.getElementById('admin-login').style.display = 'flex';
  document.getElementById('admin-dashboard').style.display = 'none';
  document.getElementById('admin-login-username').value = '';
  document.getElementById('admin-login-password').value = '';
}

async function loadAdminStats() {
  try {
    const res = await fetch(`${API}/api/v1/admin/stats`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const stats = await res.json();
      document.getElementById('admin-total-users').textContent = stats.total_users;
      document.getElementById('admin-active-users').textContent = stats.active_users_7d;
      document.getElementById('admin-total-snapshots').textContent = stats.total_snapshots;
      document.getElementById('admin-revenue').textContent = `$${stats.total_revenue.toFixed(2)}`;
      
      // Render top performers
      const performersEl = document.getElementById('admin-top-performers');
      performersEl.innerHTML = stats.top_performers.map(p => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px;background:var(--bg-secondary);border-radius:var(--radius-sm)">
          <div style="font-size:13px;color:var(--text-primary)">${p.username}</div>
          <div style="font-size:14px;font-weight:700;color:var(--accent)">${p.avg_score}</div>
        </div>
      `).join('');
    }
  } catch (e) {
    console.error('Failed to load admin stats:', e);
  }
}

function renderBarList(containerId, rows, labelKey, emptyText) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!rows || rows.length === 0) {
    el.innerHTML = `<div style="font-size:12px;color:var(--text-muted)">${emptyText}</div>`;
    return;
  }
  const max = Math.max(...rows.map(r => r.count), 1);
  el.innerHTML = rows.map(row => `
    <div style="margin-bottom:6px">
      <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-secondary);margin-bottom:2px">
        <span>${row[labelKey]}</span><span style="font-weight:700;color:var(--text-primary)">${row.count}</span>
      </div>
      <div style="background:var(--bg-secondary);border-radius:4px;height:6px;overflow:hidden">
        <div style="width:${Math.round(row.count / max * 100)}%;height:100%;background:var(--accent);border-radius:4px"></div>
      </div>
    </div>
  `).join('');
}

async function loadLandingClickStats() {
  try {
    const res = await fetch(`${API}/api/v1/analytics/landing-clicks`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    if (res.ok) {
      const stats = await res.json();
      document.getElementById('admin-landing-clicks-24h').textContent = stats.last_24h;

      const breakdownEl = document.getElementById('admin-landing-clicks-breakdown');
      breakdownEl.innerHTML = stats.by_link_24h.map(row => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px;background:var(--bg-secondary);border-radius:var(--radius-sm)">
          <div style="font-size:13px;color:var(--text-primary)">${row.link}</div>
          <div style="font-size:14px;font-weight:700;color:var(--accent)">${row.count}</div>
        </div>
      `).join('');

      // Daily trend (last 30 days) - rendered as a horizontal bar list since
      // there's no charting library loaded here.
      const dayEl = document.getElementById('admin-clicks-by-day');
      if (dayEl) {
        if (!stats.by_day || stats.by_day.length === 0) {
          dayEl.innerHTML = '<div style="font-size:12px;color:var(--text-muted)">No clicks in the last 30 days.</div>';
        } else {
          const maxDay = Math.max(...stats.by_day.map(d => d.count), 1);
          dayEl.innerHTML = stats.by_day.map(d => `
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
              <div style="font-size:11px;color:var(--text-muted);width:70px;flex-shrink:0">${d.date}</div>
              <div style="flex:1;background:var(--bg-secondary);border-radius:4px;height:14px;overflow:hidden">
                <div style="width:${Math.round(d.count / maxDay * 100)}%;height:100%;background:linear-gradient(90deg,#6c63ff,#ec4899);border-radius:4px"></div>
              </div>
              <div style="font-size:12px;color:var(--text-primary);width:24px;text-align:right;flex-shrink:0">${d.count}</div>
            </div>
          `).join('');
        }
      }

      renderBarList('admin-clicks-by-device', stats.by_device, 'label', 'No device data yet.');
      renderBarList('admin-clicks-by-os', stats.by_os, 'label', 'No OS data yet.');
      renderBarList('admin-clicks-by-browser', stats.by_browser, 'label', 'No browser data yet.');
      renderBarList('admin-clicks-by-country', stats.by_country, 'label', 'No location data yet.');
    }
  } catch (e) {
    console.error('Failed to load landing click stats:', e);
  }
}

async function loadAdminUsers(search = '') {
  try {
    const searchParam = search ? `&search=${encodeURIComponent(search)}` : '';
    const res = await fetch(`${API}/api/v1/admin/users?skip=${adminUserOffset}&limit=${adminUserLimit}${searchParam}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderAdminUsers(data.users);
      
      const loadMoreBtn = document.getElementById('admin-load-more');
      if (data.users.length === adminUserLimit && data.total > adminUserOffset + adminUserLimit) {
        loadMoreBtn.style.display = 'block';
      } else {
        loadMoreBtn.style.display = 'none';
      }
    }
  } catch (e) {
    console.error('Failed to load admin users:', e);
  }
}

function renderAdminUsers(users) {
  const listEl = document.getElementById('admin-users-list');
  listEl.innerHTML = users.map(user => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:12px;background:var(--bg-secondary);border-radius:var(--radius-sm);border:1px solid var(--border)">
      <div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">${user.username}</div>
        <div style="font-size:11px;color:var(--text-muted)">${user.email}</div>
        <div style="font-size:10px;color:var(--text-muted);margin-top:2px">${user.snapshot_count} logs • ${user.report_count} reports</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:end;gap:4px">
        <span style="font-size:11px;padding:2px 8px;background:${user.tier === 'free' ? 'var(--bg-card)' : 'rgba(108,99,255,0.2)'};border-radius:4px;color:${user.tier === 'free' ? 'var(--text-muted)' : 'var(--accent)'}">${user.tier}</span>
        ${user.is_admin ? '<span style="font-size:10px;color:var(--accent)">🛡️</span>' : ''}
      </div>
    </div>
  `).join('');
}

async function loadMoreAdminUsers() {
  adminUserOffset += adminUserLimit;
  const searchValue = document.getElementById('admin-user-search').value;
  loadAdminUsers(searchValue);
}

async function loadAdminActivity() {
  try {
    const res = await fetch(`${API}/api/v1/admin/recent-activity?limit=20`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const activity = await res.json();
      const activityEl = document.getElementById('admin-recent-activity');
      activityEl.innerHTML = activity.map(item => {
        const time = new Date(item.timestamp).toLocaleString();
        const icon = item.type === 'snapshot' ? '📝' : '📊';
        const score = item.vektra_score ? `Score: ${item.vektra_score.toFixed(0)}` : '';
        return `
          <div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--bg-secondary);border-radius:var(--radius-sm)">
            <div style="font-size:16px">${icon}</div>
            <div style="flex:1">
              <div style="font-size:13px;color:var(--text-primary)">${item.username}</div>
              <div style="font-size:11px;color:var(--text-muted)">${item.type === 'snapshot' ? 'Logged snapshot' : 'Generated report'} ${score}</div>
            </div>
            <div style="font-size:10px;color:var(--text-muted)">${time}</div>
          </div>
        `;
      }).join('');
    }
  } catch (e) {
    console.error('Failed to load admin activity:', e);
  }
}

// Add search handler
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('admin-user-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      adminUserOffset = 0;
      loadAdminUsers(e.target.value);
    });
  }
});

// Expose functions globally
window.adminLogin = adminLogin;
window.adminLogout = adminLogout;
window.loadMoreAdminUsers = loadMoreAdminUsers;
