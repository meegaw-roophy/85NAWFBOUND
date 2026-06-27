// ── Screen navigation ──
function goTo(screen) {
  document.querySelectorAll('#app > div').forEach(s => s.style.display = 'none');
  const target = document.getElementById(screen);
  if (target) target.style.display = 'flex';
}

// ── Splash → Welcome transition ──
window.addEventListener('load', () => {
  setTimeout(() => {
    const splash = document.getElementById('splash');
    splash.style.opacity = '0';
    setTimeout(() => {
      splash.style.display = 'none';
      document.getElementById('welcome').style.display = 'flex';
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

// ── Load dashboard ──
async function loadDashboard() {
  if (!currentUser) return;

  // Set username
  document.getElementById('dash-username').textContent = 
    currentUser.username || 'User';

  // Set north star
  document.getElementById('dash-northstar').textContent = 
    currentUser.north_star || 'Not set yet — update in profile';

  // Pull latest snapshot for score
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      const snapshots = await res.json();
      if (snapshots.length > 0) {
        const latest = snapshots[0];
        const score = latest.vektra_score;
        document.getElementById('dash-score').textContent = 
          score ? score.toFixed(0) : '—';
        document.getElementById('dash-runway').textContent = 
          latest.survival_runway ? latest.survival_runway + ' days' : '— days';
        document.getElementById('dash-networth').textContent = 
          latest.current_net_worth ? 
          currentUser.currency + ' ' + latest.current_net_worth.toLocaleString() : '—';
        document.getElementById('dash-trajectory').textContent = 
          score >= 70 ? '🔥 Rising trajectory' : 
          score >= 50 ? '→ Steady — push harder' : 
          '⚠ Trajectory dropping';
      }
    }
  } catch(e) {
    console.log('Could not load snapshots', e);
  }
}

// ── Generate report ──
async function generateReport() {
  if (!currentUser || !authToken) return;
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/reports/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    });
    if (res.ok) {
      const report = await res.json();
      alert('VEKTRA Report:\n\n' + report.summary_text);
    }
  } catch(e) {
    console.log('Report error', e);
  }
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