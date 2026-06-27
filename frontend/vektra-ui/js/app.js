// ── Screen navigation ──
function goTo(screen) {
  document.querySelectorAll('#app > div').forEach(s => s.style.display = 'none');
  const target = document.getElementById(screen);
  if (target) target.style.display = 'flex';
}

window.addEventListener('load', () => {
  setTimeout(() => {
    const splash = document.getElementById('splash');
    splash.style.opacity = '0';
    setTimeout(async () => {
      splash.style.display = 'none';

      // ── Check for saved token ──
      const savedToken = localStorage.getItem('vektra_token');
console.log('Saved token:', savedToken); // ADD THIS
if (savedToken) {
  authToken = savedToken;
  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    console.log('Auto-login status:', res.status); // ADD THIS
    if (res.ok) {
            currentUser = await res.json();
            // Token still valid — go straight to dashboard
            goTo('dashboard');
            loadDashboard();
            return;
          } else {
            // Token expired — clear it
            localStorage.removeItem('vektra_token');
            authToken = null;
          }
        } catch(e) {
          localStorage.removeItem('vektra_token');
          authToken = null;
        }
      }

      window.addEventListener('load', () => {
  const splash = document.getElementById('splash');
  
  setTimeout(() => {
    splash.style.opacity = '0';
    
    setTimeout(async () => {
      splash.style.display = 'none';

      const savedToken = localStorage.getItem('vektra_token');
      
      if (savedToken) {
        authToken = savedToken;
        try {
          const res = await fetch(`${API}/api/v1/users/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          });
          
          if (res.ok) {
            currentUser = await res.json();
            goTo('dashboard');
            loadDashboard();
            return; // stops here — welcome never shows
          }
        } catch(e) {}
        
        // Token invalid — clear it
        localStorage.removeItem('vektra_token');
        authToken = null;
      }

      // No valid session — show welcome
      goTo('welcome');

    }, 600);
  }, 2000);
});

    }, 600);
  }, 2000);
});

// ── API base URL ──
const API = 'http://127.0.0.1:8000';

// ── Token storage ──
let authToken = null;
let currentUser = null;

// ── Register ──
async function register() {
  const name     = document.getElementById('reg-name').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const errEl    = document.getElementById('reg-error');

  errEl.style.display = 'none';

  if (!username || !email || !password) {
    errEl.textContent = 'Please fill in all required fields.';
    errEl.style.display = 'block';
    return;
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
  errEl.textContent = 'Please enter a valid email address.';
  errEl.style.display = 'block';
  return;
 }

  if (password.length < 8) {
    errEl.textContent = 'Password must be at least 8 characters.';
    errEl.style.display = 'block';
    return;
  }

  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
  errEl.textContent = 'Password must contain at least one symbol (e.g. !, @, #)';
  errEl.style.display = 'block';
  return;
}

  try {
    const res = await fetch(`${API}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      errEl.textContent = data.detail || 'Registration failed. Try again.';
      errEl.style.display = 'block';
      return;
    }

    // Registration success — auto login
    await loginWithCredentials(username, password);

  } catch (err) {
    errEl.textContent = 'Could not connect to server. Is the backend running?';
    errEl.style.display = 'block';
  }
}

// ── Login with credentials ──
async function loginWithCredentials(username, password) {
  const body = new URLSearchParams({ username, password });

  const res = await fetch(`${API}/api/v1/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body
  });

  const data = await res.json();

  if (res.ok) {
    authToken = data.access_token;
    // Fetch current user details
const userRes = await fetch(`${API}/api/v1/users/me`, {
  headers: { 'Authorization': `Bearer ${authToken}` }
});
if (userRes.ok) {
  currentUser = await userRes.json();
}
    localStorage.setItem('vektra_token', authToken);
    // New users go through onboarding, returning users go to dashboard
if (!currentUser.north_star) {
  goTo('onboard-1');
} else {
  goTo('dashboard');
  loadDashboard();
}
  }
}

// ── Login ──
async function login() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');

  errEl.style.display = 'none';

  if (!username || !password) {
    errEl.textContent = 'Please enter your username and password.';
    errEl.style.display = 'block';
    return;
  }

  try {
    await loginWithCredentials(username, password);
    if (!authToken) {
      errEl.textContent = 'Incorrect username or password.';
      errEl.style.display = 'block';
    }
  } catch (err) {
    errEl.textContent = 'Could not connect to server.';
    errEl.style.display = 'block';
  }
}

// ── Calculate streak ──
function calculateStreak(snapshots) {
  if (!snapshots || snapshots.length === 0) return 0;
  let streak = 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const loggedDates = snapshots.map(s => {
    const d = new Date(s.timestamp);
    d.setHours(0, 0, 0, 0);
    return d.getTime();
  });
  const uniqueDates = [...new Set(loggedDates)].sort((a, b) => b - a);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (uniqueDates[0] !== today.getTime() && uniqueDates[0] !== yesterday.getTime()) return 0;
  let checkDate = uniqueDates[0];
  for (let i = 0; i < uniqueDates.length; i++) {
    if (uniqueDates[i] === checkDate) { streak++; checkDate -= 86400000; }
    else break;
  }
  return streak;
}

// ── Load dashboard ──
async function loadDashboard() {
  if (!currentUser) return;

  document.getElementById('dash-username').textContent = currentUser.username || 'User';
  document.getElementById('dash-northstar').textContent = currentUser.north_star || 'Not set yet — update in profile';

  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      const snapshots = await res.json();
      if (snapshots.length > 0) {
        const latest = snapshots[0];

        const streak = calculateStreak(snapshots);
        document.getElementById('dash-streak').textContent =
          streak > 0 ? `🔥 ${streak} day${streak > 1 ? 's' : ''}` : '— Start your streak';

        const score = latest.vektra_score;
        document.getElementById('dash-score').textContent = score ? score.toFixed(0) : '—';
        document.getElementById('dash-runway').textContent = latest.survival_runway ? latest.survival_runway + ' days' : '— days';
        document.getElementById('dash-networth').textContent = latest.current_net_worth ?
          currentUser.currency + ' ' + latest.current_net_worth.toLocaleString() : '—';
        document.getElementById('dash-trajectory').textContent =
          score >= 70 ? '🔥 Rising trajectory' :
          score >= 50 ? '→ Steady — push harder' : '⚠ Trajectory dropping';
      }
    }
  } catch(e) {
    console.log('Could not load snapshots', e);
  }
}

async function generateReport() {
  loadReport();
}

// ── Daily log helpers ──
let goalHit = null;

function updateSlider(name) {
  const input = document.getElementById(`inp-${name}`);
  const val = document.getElementById(`val-${name}`);
  if (input && val) val.textContent = input.value;
  updateProgress();
}

function setGoalHit(hit) {
  goalHit = hit;
  document.getElementById('btn-hit-yes').style.background = hit ? 'var(--success)' : 'transparent';
  document.getElementById('btn-hit-yes').style.color = hit ? '#fff' : 'var(--text-secondary)';
  document.getElementById('btn-hit-no').style.background = !hit ? 'var(--danger)' : 'transparent';
  document.getElementById('btn-hit-no').style.color = !hit ? '#fff' : 'var(--text-secondary)';
}

function updateProgress() {
  const fields = ['inp-mood','inp-energy','inp-focus','inp-income','inp-tomorrow','inp-sleep','inp-skills'];
  const filled = fields.filter(id => {
    const el = document.getElementById(id);
    return el && el.value && el.value !== '5' && el.value !== '7' && el.value !== '0';
  }).length;
  const pct = Math.round(filled / fields.length * 100);
  document.getElementById('log-progress').style.width = pct + '%';
}

function openDailyLog() {
  // Set today's date
  const today = new Date().toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric'});
  document.getElementById('log-date').textContent = today;
  goTo('daily-log');
}

// ── Submit daily log ──
async function submitLog() {
  if (!currentUser || !authToken) return;

  const errEl = document.getElementById('log-error');
  errEl.style.display = 'none';

  const payload = {
    mood_score:           parseInt(document.getElementById('inp-mood').value),
    energy_level:         parseInt(document.getElementById('inp-energy').value),
    focus_level:          parseInt(document.getElementById('inp-focus').value),
    social_battery:       parseInt(document.getElementById('inp-social').value),
    health_battery:       parseInt(document.getElementById('inp-health').value),
    uncomfortable_moments: document.getElementById('inp-uncomfortable').value || null,
    daily_income:         parseFloat(document.getElementById('inp-income').value) || null,
    expenses:             parseFloat(document.getElementById('inp-expenses').value) || null,
    savings_investments:  parseFloat(document.getElementById('inp-savings').value) || null,
    any_emergency:        document.getElementById('inp-emergency').value || null,
    tomorrow_goal:        document.getElementById('inp-tomorrow').value || null,
    target_hit_bool:      goalHit,
    best_decision:        document.getElementById('inp-best').value || null,
    worst_decision:       document.getElementById('inp-worst').value || null,
    what_i_avoided:       document.getElementById('inp-avoided').value || null,
    sleep_hours:          parseFloat(document.getElementById('inp-sleep').value),
    screen_time:          parseFloat(document.getElementById('inp-screen').value) || null,
    diet_taken:           document.getElementById('inp-diet').value || null,
    skills_learned:       document.getElementById('inp-skills').value || null,
    new_ideas:            document.getElementById('inp-ideas').value || null,
    gratitude_line:       document.getElementById('inp-gratitude').value || null,
    funny_line:           document.getElementById('inp-funny').value || null,
    focus_hours:          parseFloat(document.getElementById('inp-focushours').value) || null,
    environment_rating:   parseInt(document.getElementById('inp-env').value),
    opportunity_cost:     parseFloat(document.getElementById('inp-oppcost').value) || null,
  };

  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const snap = await res.json();
      // Go back to dashboard and refresh score
      goTo('dashboard');
      loadDashboard();
      // Show score update
      setTimeout(() => {
        alert(`🔥 Log submitted!\n\nYour VEKTRA Score: ${snap.vektra_score}/100\nSurvival Runway: ${snap.survival_runway || '—'} days`);
      }, 500);
    } else {
      const data = await res.json();
      errEl.textContent = data.detail || 'Failed to submit. Try again.';
      errEl.style.display = 'block';
    }
  } catch(e) {
    errEl.textContent = 'Could not connect to server.';
    errEl.style.display = 'block';
  }
}

// ── Onboarding ──
let onboardData = {};
let selectedTone = 'Balanced';

function selectTone(tone) {
  selectedTone = tone;
  ['Harsh','Balanced','Gentle'].forEach(t => {
    const el = document.getElementById(`tone-${t.toLowerCase()}`);
    el.style.border = t === tone ? '1px solid var(--accent)' : '1px solid var(--border)';
    el.style.background = t === tone ? 'rgba(108,99,255,0.1)' : 'transparent';
  });
}

function onboardStep1() {
  const goal = document.getElementById('ob-goal').value.trim();
  const deadline = document.getElementById('ob-deadline').value;
  const errEl = document.getElementById('ob1-error');
  errEl.style.display = 'none';

  if (!goal) {
    errEl.textContent = 'Please enter your north star goal.';
    errEl.style.display = 'block';
    return;
  }

  onboardData.primary_goal = goal;
  onboardData.north_star = deadline ? `${goal} — by ${deadline}` : goal;
  onboardData.north_star_deadline = deadline || null;
  goTo('onboard-2');
}

function onboardStep2() {
  const networth = parseFloat(document.getElementById('ob-networth').value) || 0;
  const capital = parseFloat(document.getElementById('ob-capital').value) || 0;

  onboardData.initial_net_worth = networth;
  onboardData.current_capital = capital;
  goTo('onboard-3');
}

async function onboardStep3() {
  const errEl = document.getElementById('ob3-error');
  errEl.style.display = 'none';
  onboardData.preferred_feedback_tone = selectedTone;

  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        primary_goal: onboardData.primary_goal,
        north_star: onboardData.north_star,
        north_star_deadline: onboardData.north_star_deadline,
        initial_net_worth: onboardData.initial_net_worth,
        preferred_feedback_tone: selectedTone,
      })
    });

    if (res.ok) {
      currentUser = await res.json();
    }
  } catch(e) {
    console.log('Could not save onboarding data', e);
  }

  goTo('dashboard');
  loadDashboard();
}

// ── Load and display report ──
async function loadReport() {
  goTo('reports');
  document.getElementById('report-narrative').textContent = 'Generating your report...';

  if (!currentUser || !authToken) return;

  try {
    // Generate fresh report
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/reports/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    });

    if (!res.ok) return;
    const report = await res.json();
    const content = report.content || {};

    // Score
    document.getElementById('report-score').textContent =
      report.vektra_score ? report.vektra_score.toFixed(0) : '—';

    // Period
    document.getElementById('report-period').textContent =
      `${content.days_logged || 0} days logged`;

    // Quick stats
    document.getElementById('report-days').textContent =
      `${content.days_logged || 0}/7`;
    document.getElementById('report-cashflow').textContent =
      content.net_cash_flow !== undefined ?
      (content.net_cash_flow >= 0 ? '+' : '') + content.net_cash_flow : '—';
    document.getElementById('report-goals').textContent =
      content.goals_set > 0 ?
      `${content.goals_hit}/${content.goals_set}` : '—';

    // Cash flow color
    const cfEl = document.getElementById('report-cashflow');
    cfEl.style.color = content.net_cash_flow >= 0 ?
      'var(--success)' : 'var(--danger)';

    // Narrative
    document.getElementById('report-narrative').textContent =
      report.summary_text || 'No report generated yet.';

    // Engine bars
    renderEngineBar('bar-financial', 'Financial', content.avg_vektra_score || 50, '#22c55e');
    renderEngineBar('bar-mental', 'Mental', content.avg_mood ? content.avg_mood * 10 : 50, '#6c63ff');
    renderEngineBar('bar-execution', 'Execution', content.goal_hit_rate || 0, '#ec4899');
    renderEngineBar('bar-body', 'Body', content.avg_sleep ? Math.min(100, content.avg_sleep / 9 * 100) : 50, '#f59e0b');
    renderEngineBar('bar-growth', 'Growth', content.skills_count ? content.skills_count / 7 * 100 : 0, '#06b6d4');

  } catch(e) {
    document.getElementById('report-narrative').textContent = 'Could not load report. Try again.';
  }
}

function renderEngineBar(id, label, score, color) {
  const el = document.getElementById(id);
  if (!el) return;
  const pct = Math.round(Math.min(100, Math.max(0, score)));
  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-secondary);margin-bottom:4px">
      <span>${label}</span><span style="font-weight:600;color:${color}">${pct}</span>
    </div>
    <div style="background:var(--bg-secondary);border-radius:4px;height:6px;overflow:hidden">
      <div style="width:${pct}%;height:100%;background:${color};border-radius:4px;transition:width .6s"></div>
    </div>
  `;
}

// ── Logout ──
function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('vektra_token');
  goTo('welcome');
}