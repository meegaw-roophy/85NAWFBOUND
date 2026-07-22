// Admin Panel - Separate from user-facing app
const API = 'http://127.0.0.1:8000';
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
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
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
