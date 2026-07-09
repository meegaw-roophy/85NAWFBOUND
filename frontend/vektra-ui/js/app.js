// ── API base URL ──
const API = 'http://127.0.0.1:8000';

// ── Token storage ──
let authToken = null;
let currentUser = null;

// ── Toast notifications ──
function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
  toast.onclick = () => removeToast(toast);
  
  container.appendChild(toast);
  
  setTimeout(() => removeToast(toast), duration);
}

function removeToast(toast) {
  toast.classList.add('hiding');
  setTimeout(() => toast.remove(), 300);
}

// ── Loading spinner ──
function showLoader(text = 'Loading...') {
  document.getElementById('loader-text').textContent = text;
  document.getElementById('global-loader').classList.add('active');
}

function hideLoader() {
  document.getElementById('global-loader').classList.remove('active');
}

// ── Screen navigation ──
function goTo(screen) {
  document.querySelectorAll('#app > div').forEach(s => s.style.display = 'none');
  const target = document.getElementById(screen);
  if (target) target.style.display = 'flex';
}

// ── Auto-login on page load ──
window.addEventListener('load', () => {
  const splash = document.getElementById('splash');
  setTimeout(() => {
    splash.style.opacity = '0';
    setTimeout(async () => {
      splash.style.display = 'none';
      const savedToken = localStorage.getItem('vektra_token');
console.log('Saved token:', savedToken);

if (savedToken) {
  authToken = savedToken;

  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    console.log('Auto-login status:', res.status);

    if (res.ok) {
  currentUser = await res.json();
  console.log('Auto-login user:', currentUser);

  console.log('Going to dashboard...');
  goTo('dashboard');

  try {
    console.log('Before loadDashboard');
    await loadDashboard();
    console.log('After loadDashboard');
  } catch (e) {
    console.error('Dashboard crashed:', e);
  }

  return;
}
  } catch (e) {
    console.log('Auto-login error:', e);
  }
        localStorage.removeItem('vektra_token');
        authToken = null;
      }
      goTo('welcome');
    }, 600);
  }, 2000);
});

// ── Register service worker ──
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then(() => console.log('VEKTRA SW registered'))
      .catch(e => console.log('SW error', e));
  });
}

// ── Register ──
async function register() {
  const name     = document.getElementById('reg-name').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const errEl    = document.getElementById('reg-error');
  const btnEl    = document.getElementById('reg-btn');

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

  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Creating account...';
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
    await loginWithCredentials(username, password);
  } catch (err) {
    errEl.textContent = 'Could not connect to server. Is the backend running?';
    errEl.style.display = 'block';
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = 'Sign Up';
    }
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
    const userRes = await fetch(`${API}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (userRes.ok) {
      currentUser = await userRes.json();
    }
    localStorage.setItem('vektra_token', authToken);
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
  const btnEl    = document.getElementById('login-btn');
  errEl.style.display = 'none';
  if (!username || !password) {
    errEl.textContent = 'Please enter your username and password.';
    errEl.style.display = 'block';
    return;
  }
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Signing in...';
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
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = 'Sign In';
    }
  }
}

// ── Logout ──
function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('vektra_token');
  goTo('welcome');
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

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

// ── Load dashboard ──
async function loadDashboard() {
  console.log('loadDashboard started');

  if (!currentUser) {
    console.log('No currentUser');
    return;
  }
  
  console.log('currentUser =', currentUser);

  document.getElementById('dash-greeting').textContent = getGreeting();
  document.getElementById('dash-username').textContent =
    currentUser.username || 'User';

  document.getElementById('dash-northstar').textContent =
    currentUser.north_star || 'Not set yet — update in profile';

  try {
    const res = await fetch(
      `${API}/api/v1/users/${currentUser.id}/snapshots`,
      {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      }
    );

    console.log('Snapshots status:', res.status);

    if (!res.ok) {
      console.error('Failed to load snapshots:', res.status);
      showToast('Could not load your data. Please refresh.', 'error');
      return;
    }

    const snapshots = await res.json();
    console.log('snapshots =', snapshots);

    if (!snapshots || snapshots.length === 0) {
      document.getElementById('dash-score').textContent = '—';
      document.getElementById('dash-streak').textContent = 'Log your first day 🚀';
      document.getElementById('dash-trajectory').textContent = 'Start logging to see your trajectory';
      document.getElementById('dash-lastlog').textContent = 'No logs yet';
      document.getElementById('dash-status').textContent = 'Start logging to build momentum';
      document.getElementById('dash-week-summary').textContent = '0 logs • 0 unique days';
      document.getElementById('dash-week-status').textContent = 'Keep logging to unlock richer weekly insights';
      document.getElementById('first-log-prompt').style.display = 'block';
      return;
    }

    document.getElementById('first-log-prompt').style.display = 'none';

    if (snapshots.length > 0) {
      const latest = snapshots[0];
      console.log('latest =', latest);

      const streak = calculateStreak(snapshots);

      document.getElementById('dash-streak').textContent =
        streak > 0
          ? `🔥 ${streak} day${streak > 1 ? 's' : ''}`
          : '— Start your streak';

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - 6);
        const weekSnapshots = snapshots.filter(snapshot => {
          const snapshotDate = new Date(snapshot.timestamp || snapshot.log_date || today);
          snapshotDate.setHours(0, 0, 0, 0);
          return snapshotDate >= weekStart && snapshotDate <= today;
        });
        const uniqueWeekDays = new Set(weekSnapshots.map(snapshot => {
          const snapshotDate = new Date(snapshot.timestamp || snapshot.log_date || today);
          snapshotDate.setHours(0, 0, 0, 0);
          return snapshotDate.toDateString();
        })).size;
        document.getElementById('dash-week-summary').textContent = `${weekSnapshots.length} log${weekSnapshots.length === 1 ? '' : 's'} • ${uniqueWeekDays} unique day${uniqueWeekDays === 1 ? '' : 's'}`;
        document.getElementById('dash-week-status').textContent = weekSnapshots.length >= 3
          ? 'Enough data for a meaningful weekly readout'
          : 'Keep logging to unlock richer weekly insights';

        const latestDate = latest.timestamp ? new Date(latest.timestamp) : null;
        const latestDay = latestDate ? new Date(latestDate) : null;
        if (latestDay) {
          latestDay.setHours(0, 0, 0, 0);
        }
        const loggedToday = latestDay && latestDay.getTime() === today.getTime();

        document.getElementById('dash-lastlog').textContent = latestDate
          ? `Last log: ${latestDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
          : 'No logs yet';
        document.getElementById('dash-status').textContent = loggedToday
          ? 'Today’s log is already in place'
          : 'A log is still needed today';

        const score = latest.vektra_score;

        if (score) animateScore(score);
          else document.getElementById('dash-score').textContent = '—';

        document.getElementById('dash-runway').textContent =
          latest.survival_runway
            ? latest.survival_runway + ' days'
            : '— days';

        document.getElementById('dash-networth').textContent =
          latest.current_net_worth
            ? (currentUser.currency || '') +
              ' ' +
              latest.current_net_worth.toLocaleString()
            : '—';

        document.getElementById('dash-trajectory').textContent =
          score >= 70
            ? '🔥 Rising trajectory'
            : score >= 50
            ? '→ Steady — push harder'
            : '⚠ Trajectory dropping';

        // Generate smart insight
        const smartInsight = generateSmartInsight(snapshots, latest);
        document.getElementById('smart-insight').textContent = smartInsight;

        console.log('Dashboard updated successfully');
      } else {
        console.log('No snapshots yet.');
      }
  } catch (e) {
    console.error('Could not load snapshots:', e);
    showToast('Could not load your data. Please refresh.', 'error');
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

let dailyLogLocked = false;

function updateProgress() {
  const fields = ['inp-mood','inp-energy','inp-focus','inp-income','inp-tomorrow','inp-sleep','inp-skills'];
  const filled = fields.filter(id => {
    const el = document.getElementById(id);
    return el && el.value && el.value !== '5' && el.value !== '7' && el.value !== '0';
  }).length;
  const pct = Math.round(filled / fields.length * 100);
  document.getElementById('log-progress').style.width = pct + '%';
}

function setDailyLogReadOnly(readonly, message = '') {
  const statusEl = document.getElementById('daily-log-status');
  const controls = document.querySelectorAll('#daily-log input, #daily-log textarea, #daily-log button');
  controls.forEach(control => {
    control.disabled = readonly;
  });
  dailyLogLocked = readonly;
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.style.display = message ? 'block' : 'none';
  }
}

async function checkTodayLogStatus() {
  if (!currentUser || !authToken) return;
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots/today`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();
    if (data.logged) {
      setDailyLogReadOnly(true, 'A log for today is already saved. You can review your dashboard or come back tomorrow.');
    } else {
      setDailyLogReadOnly(false, '');
    }
  } catch (e) {
    setDailyLogReadOnly(false, '');
  }
}

function openDailyLog() {
  const today = new Date().toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric'});
  document.getElementById('log-date').textContent = today;
  goTo('daily-log');
  restoreDraft();
  checkTodayLogStatus();
  // Auto-save every 30 seconds when on daily log screen
  setInterval(() => {
    if (document.getElementById('daily-log').style.display !== 'none') {
      saveDraft();
    }
  }, 30000);
}

// ── Submit daily log ──
async function submitLog() {
  if (!currentUser || !authToken) return;
  if (dailyLogLocked) {
    showToast('Today’s log is already saved. Nothing new was submitted.', 'info', 3000);
    return;
  }
  const errEl = document.getElementById('log-error');
  const submitBtn = document.querySelector('.btn-primary[onclick="submitLog()"]');
  errEl.style.display = 'none';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';
  }
  const moodVal = document.getElementById('inp-mood').value;
  const sleepVal = document.getElementById('inp-sleep').value;
  const incomeVal = document.getElementById('inp-income').value;
  const expenseVal = document.getElementById('inp-expenses').value;
  
  if (!moodVal || moodVal === '5') {
    showToast('Please select your mood', 'warning');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Today's Log 🔥";
    }
    return;
  }
  if (!sleepVal || sleepVal === '7') {
    showToast('Please enter your sleep hours', 'warning');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Today's Log 🔥";
    }
    return;
  }
  
  const sleepHours = parseFloat(sleepVal);
  if (isNaN(sleepHours) || sleepHours < 0 || sleepHours > 24) {
    showToast('Sleep hours must be between 0 and 24', 'warning');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Today's Log 🔥";
    }
    return;
  }

  if (incomeVal && (isNaN(parseFloat(incomeVal)) || parseFloat(incomeVal) < 0)) {
    showToast('Income must be a positive number', 'warning');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Today's Log 🔥";
    }
    return;
  }

  if (expenseVal && (isNaN(parseFloat(expenseVal)) || parseFloat(expenseVal) < 0)) {
    showToast('Expenses must be a positive number', 'warning');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Today's Log 🔥";
    }
    return;
  }

  const payload = {
    mood_score:            parseInt(moodVal),
    energy_level:          parseInt(document.getElementById('inp-energy').value) || null,
    focus_level:           parseInt(document.getElementById('inp-focus').value) || null,
    social_battery:        parseInt(document.getElementById('inp-social').value) || null,
    health_battery:        parseInt(document.getElementById('inp-health').value) || null,
    uncomfortable_moments: document.getElementById('inp-uncomfortable').value || null,
    daily_income:          parseFloat(document.getElementById('inp-income').value) || null,
    expenses:              parseFloat(document.getElementById('inp-expenses').value) || null,
    savings_investments:   parseFloat(document.getElementById('inp-savings').value) || null,
    any_emergency:         document.getElementById('inp-emergency').value || null,
    tomorrow_goal:         document.getElementById('inp-tomorrow').value || null,
    target_hit_bool:       goalHit,
    best_decision:         document.getElementById('inp-best').value || null,
    worst_decision:        document.getElementById('inp-worst').value || null,
    what_i_avoided:        document.getElementById('inp-avoided').value || null,
    sleep_hours:           sleepHours,
    screen_time:           parseFloat(document.getElementById('inp-screen').value) || null,
    diet_taken:            document.getElementById('inp-diet').value || null,
    skills_learned:        document.getElementById('inp-skills').value || null,
    new_ideas:             document.getElementById('inp-ideas').value || null,
    gratitude_line:        document.getElementById('inp-gratitude').value || null,
    funny_line:            document.getElementById('inp-funny').value || null,
    focus_hours:           parseFloat(document.getElementById('inp-focushours').value) || null,
    environment_rating:    parseInt(document.getElementById('inp-env').value) || null,
    opportunity_cost:      parseFloat(document.getElementById('inp-oppcost').value) || null,
  };
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const snap = await res.json();
      showScoreReveal(snap);
      clearDraft();
    } else {
      const data = await res.json();
      errEl.textContent = data.detail || 'Failed to submit. Try again.';
      errEl.style.display = 'block';
    }
  } catch(e) {
    errEl.textContent = 'Could not connect to server.';
    errEl.style.display = 'block';
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Today's Log 🔥";
    }
  }
  clearDraft();
}

// ── Onboarding ──
let onboardData = {};
let selectedTone = 'Balanced';

function selectTone(tone) {
  selectedTone = tone;
  ['Harsh','Balanced','Gentle'].forEach(t => {
    const el = document.getElementById(`tone-${t.toLowerCase()}`);
    if (el) {
      el.style.border = t === tone ? '1px solid var(--accent)' : '1px solid var(--border)';
      el.style.background = t === tone ? 'rgba(108,99,255,0.1)' : 'transparent';
    }
  });
}

function onboardStep1() {
  const goal = document.getElementById('ob-goal').value.trim();
  const deadline = document.getElementById('ob-deadline').value;
  const errEl = document.getElementById('ob1-error');
  const btnEl = document.getElementById('ob1-btn');
  errEl.style.display = 'none';
  if (!goal) {
    errEl.textContent = 'Please enter your north star goal.';
    errEl.style.display = 'block';
    return;
  }
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Saving...';
  }
  onboardData.primary_goal = goal;
  onboardData.north_star = deadline ? `${goal} — by ${deadline}` : goal;
  onboardData.north_star_deadline = deadline || null;
  setTimeout(() => {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = 'Set My North Star →';
    }
    goTo('onboard-2');
  }, 300);
}

function onboardStep2() {
  const btnEl = document.getElementById('ob2-btn');
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Saving...';
  }
  onboardData.initial_net_worth = parseFloat(document.getElementById('ob-networth').value) || 0;
  onboardData.current_capital = parseFloat(document.getElementById('ob-capital').value) || 0;
  setTimeout(() => {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = 'Continue →';
    }
    goTo('onboard-3');
  }, 300);
}

async function onboardStep3() {
  const errEl = document.getElementById('ob3-error');
  const btnEl = document.getElementById('ob3-btn');
  errEl.style.display = 'none';
  onboardData.preferred_feedback_tone = selectedTone;
  
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Launching...';
  }
  
  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        primary_goal: onboardData.primary_goal,
        north_star: onboardData.north_star,
        north_star_deadline: onboardData.north_star_deadline,
        initial_net_worth: onboardData.initial_net_worth,
        preferred_feedback_tone: selectedTone,
      })
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      errEl.textContent = data.detail || 'Could not save your preferences.';
      errEl.style.display = 'block';
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.textContent = 'Launch VEKTRA 🚀';
      }
      return;
    }

    // Force fresh user fetch ──
    const userRes = await fetch(`${API}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (userRes.ok) currentUser = await userRes.json();

  } catch(e) {
    console.log('Could not save onboarding data', e);
    errEl.textContent = 'Could not connect to server. Please try again.';
    errEl.style.display = 'block';
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = 'Launch VEKTRA 🚀';
    }
    return;
  }

  goTo('dashboard');
  loadDashboard();
}

// ── Load and display report ──
async function loadReport() {
  goTo('reports');
  showLoader('Generating your report...');
  document.getElementById('report-narrative').textContent = 'Generating...';
  
  if (!currentUser || !authToken) { 
    hideLoader();
    showToast('Please log in to view your report', 'error');
    return;
  }
  
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/reports/generate`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    
    if (!res.ok) {
      hideLoader();
      const data = await res.json().catch(() => ({}));
      showToast(data.detail || 'Could not generate report. Try again.', 'error');
      document.getElementById('report-narrative').textContent = 'Could not load report. Try again.';
      return;
    }
    
    const report = await res.json();
    const content = report.content || {};
    const uniqueDays = content.unique_days_logged ?? content.days_logged ?? 0;
    const reportCountdown = content.report_countdown ?? Math.max(0, 7 - uniqueDays);
    const signalScores = content.signal_scores || {};
    const reportReady = content.report_ready ?? uniqueDays >= 3;
    const readinessMessage = content.report_readiness_message || (reportReady ? 'Your weekly report is ready.' : 'Log a few more days to unlock a richer weekly report.');

    document.getElementById('report-score').textContent =
      report.vektra_score ? report.vektra_score.toFixed(0) : '—';
    document.getElementById('report-period').textContent =
      uniqueDays > 0 ? `${uniqueDays} unique day${uniqueDays === 1 ? '' : 's'} logged` : 'No week data yet';
    document.getElementById('report-days').textContent =
      `${uniqueDays}/7`;
    document.getElementById('report-timer').textContent =
      `${reportCountdown}/7`;
    document.getElementById('report-cashflow').textContent =
      content.net_cash_flow !== undefined ?
      (content.net_cash_flow >= 0 ? '+' : '') + content.net_cash_flow : '—';
    document.getElementById('report-goals').textContent =
      content.goals_set > 0 ? `${content.goals_hit}/${content.goals_set}` : '—';

    const cfEl = document.getElementById('report-cashflow');
    cfEl.style.color = content.net_cash_flow >= 0 ? 'var(--success)' : 'var(--danger)';

    const readinessEl = document.getElementById('report-readiness');
    if (readinessEl) {
      readinessEl.textContent = readinessMessage;
      readinessEl.style.display = 'block';
      readinessEl.style.borderColor = reportReady ? 'rgba(34,197,94,0.3)' : 'rgba(236,72,153,0.3)';
      readinessEl.style.background = reportReady ? 'rgba(34,197,94,0.08)' : 'rgba(236,72,153,0.08)';
    }

    // Show/hide empty state based on report readiness
    const emptyEl = document.getElementById('report-empty');
    const narrativeEl = document.getElementById('report-narrative');
    if (emptyEl && narrativeEl) {
      if (!reportReady) {
        emptyEl.style.display = 'block';
        narrativeEl.style.display = 'none';
      } else {
        emptyEl.style.display = 'none';
        narrativeEl.style.display = 'block';
      }
    }

    // Format narrative
    const raw = report.summary_text || 'No report generated yet.';
    const formatted = raw
      .replace(/={3,}/g, '')
      .replace(/VEKTRA WEEKLY REPORT/g, '')
      .replace(/\[Note:.*?\]/g, '')
      .replace(/TRAJECTORY STATUS:/g, '\n🎯 TRAJECTORY STATUS:')
      .replace(/YOUR WINS THIS WEEK:/g, '\n\n🏆 YOUR WINS THIS WEEK:')
      .replace(/SILENT KILLERS:/g, '\n\n⚠️ SILENT KILLERS:')
      .replace(/THE NUMBERS DON'T LIE:/g, '\n\n📊 THE NUMBERS DON\'T LIE:')
      .replace(/NEXT WEEK DIRECTIVE:/g, '\n\n🔥 NEXT WEEK DIRECTIVE:')
      .trim();
    document.getElementById('report-narrative').innerHTML = formatted.replace(/\n/g, '<br>');

    renderEngineBar('bar-financial', 'Financial', signalScores.Financial ?? 0, '#22c55e', 100);
    renderEngineBar('bar-mental', 'Mental', signalScores.Mental ?? 0, '#6c63ff', 100);
    renderEngineBar('bar-execution', 'Execution', signalScores.Execution ?? 0, '#ec4899', 100);
    renderEngineBar('bar-body', 'Body', signalScores.Body ?? 0, '#f59e0b', 100);
    renderEngineBar('bar-growth', 'Growth', signalScores.Growth ?? 0, '#06b6d4', 100);
    
    // Load weekly comparison
    loadWeeklyComparison();
    
    hideLoader();

  } catch(e) {
    hideLoader();
    console.error('Report generation error:', e);
    showToast('Could not load report. Please try again.', 'error');
    document.getElementById('report-narrative').textContent = 'Could not load report. Try again.';
  }
}

async function generateReport() {
  loadReport();
}

// ── Render engine bar ──
function renderEngineBar(id, label, score, color, maxScore = 100) {
  const el = document.getElementById(id);
  if (!el) return;
  const pct = Math.round(Math.min(100, Math.max(0, (score / maxScore) * 100)));
  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-secondary);margin-bottom:4px">
      <span>${label}</span><span style="font-weight:600;color:${color}">${Number(score).toFixed(1)}</span>
    </div>
    <div style="background:var(--bg-secondary);border-radius:4px;height:6px;overflow:hidden">
      <div style="width:${pct}%;height:100%;background:${color};border-radius:4px;transition:width .6s"></div>
    </div>
  `;
}

// ── Profile ──
let profileTone = 'Balanced';

function setProfileTone(tone) {
  profileTone = tone;
  ['Harsh','Balanced','Gentle'].forEach(t => {
    const el = document.getElementById(`ptone-${t.toLowerCase()}`);
    if (el) {
      el.style.background = t === tone ? 'rgba(108,99,255,0.2)' : 'transparent';
      el.style.borderColor = t === tone ? 'var(--accent)' : 'var(--border)';
      el.style.color = t === tone ? 'var(--text-primary)' : 'var(--text-secondary)';
    }
  });
}

async function openProfile() {
  goTo('profile');
  if (!currentUser) return;
  document.getElementById('profile-username').textContent = currentUser.username || '—';
  document.getElementById('profile-tier').textContent = currentUser.tier || 'Free';
  document.getElementById('profile-northstar').value = currentUser.north_star || '';
  profileTone = currentUser.preferred_feedback_tone || 'Balanced';
  setProfileTone(profileTone);
  const code = currentUser.username?.toUpperCase() || '—';
  document.getElementById('referral-code').textContent = code;
  document.getElementById('vek-credits').textContent = '0';
  document.getElementById('referral-count').textContent = '0';
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      const snapshots = await res.json();
      const streak = calculateStreak(snapshots);
      const latest = snapshots[0];
      document.getElementById('profile-streak').textContent = streak > 0 ? `🔥 ${streak}` : '0';
      document.getElementById('profile-score').textContent = latest?.vektra_score ? latest.vektra_score.toFixed(0) : '—';
      document.getElementById('profile-logs').textContent = snapshots.length;
    } else {
      console.error('Failed to load profile data:', res.status);
    }
  } catch(e) {
    console.error('Profile data load error:', e);
  }
  
  // Load goal progress
  loadGoalProgress();
  
  // Load goal prediction
  loadGoalPrediction();
}

async function saveProfile() {
  if (!currentUser || !authToken) return;
  const northStar = document.getElementById('profile-northstar').value.trim();
  const successEl = document.getElementById('profile-success');
  const errorEl = document.getElementById('profile-error');
  const saveBtn = document.getElementById('profile-save-btn');
  successEl.style.display = 'none';
  errorEl.style.display = 'none';
  if (!northStar) {
    errorEl.textContent = 'Please add a north star before saving.';
    errorEl.style.display = 'block';
    return;
  }
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
  }
  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ north_star: northStar, preferred_feedback_tone: profileTone })
    });
    if (res.ok) {
      currentUser = await res.json();
      document.getElementById('dash-northstar').textContent = currentUser.north_star || 'Not set yet — update in profile';
      successEl.textContent = '✓ Profile updated';
      successEl.style.display = 'block';
      showToast('Profile updated', 'success', 2500);
      setTimeout(() => successEl.style.display = 'none', 3000);
    } else {
      const data = await res.json().catch(() => ({}));
      errorEl.textContent = data.detail || 'Could not save your profile.';
      errorEl.style.display = 'block';
    }
  } catch(e) {
    errorEl.textContent = 'Could not connect to server.';
    errorEl.style.display = 'block';
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save Changes';
    }
  }
}

// ── Referral system ──
function copyReferral() {
  const code = document.getElementById('referral-code').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = event.target;
    btn.textContent = 'Copied!';
    btn.style.background = 'rgba(34,197,94,0.2)';
    btn.style.borderColor = 'var(--success)';
    btn.style.color = 'var(--success)';
    setTimeout(() => {
      btn.textContent = 'Copy';
      btn.style.background = 'rgba(108,99,255,0.2)';
      btn.style.borderColor = 'var(--accent)';
      btn.style.color = 'var(--accent)';
    }, 2000);
  });
}

function shareReferral() {
  const code = currentUser?.username?.toUpperCase() || 'VEKTRA';
  const message = `I've been tracking my trajectory with VEKTRA — the AI-powered self-tracking app that gives you harsh truths about your progress.\n\nUse my code ${code} to get started:\nhttps://vektra.app\n\nVector = Magnitude × Direction 🔥`;
  
  // Always use clipboard on desktop, share sheet on mobile
  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  
  if (isMobile && navigator.share) {
    navigator.share({ title: 'Join me on VEKTRA', text: message });
  } else {
    navigator.clipboard.writeText(message).then(() => {
      const btn = event.target;
      const original = btn.textContent;
      btn.textContent = '✓ Copied to clipboard!';
      btn.style.background = 'var(--success)';
      setTimeout(() => {
        btn.textContent = original;
        btn.style.background = 'linear-gradient(135deg,#6c63ff,#ec4899)';
      }, 2500);
    });
  }
}

// ── Auto-save draft ──
function saveDraft() {
  const draft = {
    mood: document.getElementById('inp-mood')?.value,
    energy: document.getElementById('inp-energy')?.value,
    focus: document.getElementById('inp-focus')?.value,
    social: document.getElementById('inp-social')?.value,
    health: document.getElementById('inp-health')?.value,
    income: document.getElementById('inp-income')?.value,
    expenses: document.getElementById('inp-expenses')?.value,
    savings: document.getElementById('inp-savings')?.value,
    emergency: document.getElementById('inp-emergency')?.value,
    tomorrow: document.getElementById('inp-tomorrow')?.value,
    best: document.getElementById('inp-best')?.value,
    worst: document.getElementById('inp-worst')?.value,
    avoided: document.getElementById('inp-avoided')?.value,
    sleep: document.getElementById('inp-sleep')?.value,
    screen: document.getElementById('inp-screen')?.value,
    diet: document.getElementById('inp-diet')?.value,
    skills: document.getElementById('inp-skills')?.value,
    ideas: document.getElementById('inp-ideas')?.value,
    gratitude: document.getElementById('inp-gratitude')?.value,
    funny: document.getElementById('inp-funny')?.value,
    focushours: document.getElementById('inp-focushours')?.value,
    env: document.getElementById('inp-env')?.value,
    oppcost: document.getElementById('inp-oppcost')?.value,
    goalHit: goalHit,
    savedAt: new Date().toISOString()
  };
  localStorage.setItem('vektra_draft', JSON.stringify(draft));
}

function restoreDraft() {
  const saved = localStorage.getItem('vektra_draft');
  if (!saved) return;
  
  const draft = JSON.parse(saved);
  
  // Only restore if draft is from today
  const savedDate = new Date(draft.savedAt).toDateString();
  const today = new Date().toDateString();
  if (savedDate !== today) {
    localStorage.removeItem('vektra_draft');
    return;
  }

  // Restore all fields
  const fields = ['mood','energy','focus','social','health','sleep','focushours','env'];
  fields.forEach(f => {
    const el = document.getElementById(`inp-${f}`);
    if (el && draft[f]) {
      el.value = draft[f];
      updateSlider(f);
    }
  });

  const textFields = ['income','expenses','savings','emergency','tomorrow','best','worst','avoided','screen','diet','skills','ideas','gratitude','funny','oppcost'];
  textFields.forEach(f => {
    const el = document.getElementById(`inp-${f}`);
    if (el && draft[f]) el.value = draft[f];
  });

  if (draft.goalHit !== null && draft.goalHit !== undefined) {
    setGoalHit(draft.goalHit);
  }

  showToast('Draft restored from earlier today 📝', 'info');
}

function clearDraft() {
  localStorage.removeItem('vektra_draft');
}

// ── Animate score counter ──
function animateScore(targetScore) {
  const el = document.getElementById('dash-score');
  if (!el || !targetScore) return;
  
  const duration = 1500;
  const start = performance.now();
  const startVal = 0;
  
  function update(currentTime) {
    const elapsed = currentTime - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(startVal + (targetScore - startVal) * eased);
    el.textContent = current;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// ── GOALS / MILESTONES ──
async function loadGoals() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/goals`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const goals = await res.json();
      renderGoals(goals);
    } else {
      console.error('Failed to load goals');
    }
  } catch (e) {
    console.error('Error loading goals:', e);
  }
}

async function loadGoalProgress() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/goals/progress`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const progress = await res.json();
      updateGoalProgressUI(progress);
    }
  } catch (e) {
    console.error('Error loading goal progress:', e);
  }
}

function updateGoalProgressUI(progress) {
  const pctEl = document.getElementById('goal-progress-pct');
  const barEl = document.getElementById('goal-progress-bar');
  const nextEl = document.getElementById('next-milestone');
  const completedEl = document.getElementById('goals-completed');
  const goalsBarEl = document.getElementById('goals-progress-bar');
  
  if (pctEl) pctEl.textContent = `${Math.round(progress.progress_pct)}%`;
  if (barEl) barEl.style.width = `${progress.progress_pct}%`;
  if (completedEl) completedEl.textContent = `${progress.completed_goals}/${progress.total_goals}`;
  if (goalsBarEl) goalsBarEl.style.width = `${progress.progress_pct}%`;
  if (nextEl) {
    if (progress.next_milestone) {
      nextEl.textContent = `Next: ${progress.next_milestone}`;
    } else if (progress.total_goals === 0) {
      nextEl.textContent = 'No milestones set yet';
    } else {
      nextEl.textContent = 'All milestones completed! 🎉';
    }
  }
}

function renderGoals(goals) {
  const listEl = document.getElementById('goals-list');
  const emptyEl = document.getElementById('goals-empty');
  
  if (!listEl) return;
  
  if (!goals || goals.length === 0) {
    listEl.style.display = 'none';
    if (emptyEl) emptyEl.style.display = 'block';
    return;
  }
  
  listEl.style.display = 'flex';
  if (emptyEl) emptyEl.style.display = 'none';
  
  listEl.innerHTML = goals.map(goal => `
    <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:1rem;${goal.completed ? 'opacity:0.6' : ''}">
      <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px">
        <div style="flex:1">
          <div style="font-weight:600;font-size:14px;margin-bottom:4px ${goal.completed ? 'text-decoration:line-through;color:var(--text-muted)' : ''}">${goal.title}</div>
          ${goal.deadline ? `<div style="font-size:12px;color:var(--text-muted)">Due: ${new Date(goal.deadline).toLocaleDateString()}</div>` : ''}
        </div>
        <div style="display:flex;gap:8px">
          <button onclick="toggleGoalComplete(${goal.id}, ${!goal.completed})" style="padding:6px 10px;border-radius:var(--radius-sm);border:1px solid ${goal.completed ? 'var(--success)' : 'var(--border)'};background:${goal.completed ? 'rgba(34,197,94,0.1)' : 'transparent'};color:${goal.completed ? 'var(--success)' : 'var(--text-secondary)'};cursor:pointer;font-size:12px;font-family:var(--font)">
            ${goal.completed ? '✓' : '○'}
          </button>
          <button onclick="deleteGoal(${goal.id})" style="padding:6px 10px;border-radius:var(--radius-sm);border:1px solid var(--border);background:transparent;color:var(--text-muted);cursor:pointer;font-size:12px;font-family:var(--font)">✕</button>
        </div>
      </div>
      ${goal.intensity || goal.effort ? `
        <div style="display:flex;gap:12px;margin-top:8px">
          ${goal.intensity ? `<div style="font-size:11px;color:var(--text-muted)">Intensity: ${goal.intensity}/10</div>` : ''}
          ${goal.effort ? `<div style="font-size:11px;color:var(--text-muted)">Effort: ${goal.effort}/10</div>` : ''}
        </div>
      ` : ''}
      <div style="margin-top:8px;height:4px;background:var(--bg-secondary);border-radius:2px;overflow:hidden">
        <div style="height:100%;background:linear-gradient(90deg,#6c63ff,#ec4899);width:${goal.progress_pct}%"></div>
      </div>
    </div>
  `).join('');
}

async function addGoal() {
  if (!currentUser || !authToken) return;
  
  const title = document.getElementById('goal-title').value.trim();
  const intensity = parseInt(document.getElementById('goal-intensity').value) || null;
  const effort = parseInt(document.getElementById('goal-effort').value) || null;
  const deadline = document.getElementById('goal-deadline').value || null;
  const errEl = document.getElementById('goal-error');
  const btnEl = document.getElementById('goal-add-btn');
  
  errEl.style.display = 'none';
  
  if (!title) {
    errEl.textContent = 'Please enter a milestone title';
    errEl.style.display = 'block';
    return;
  }
  
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Adding...';
  }
  
  try {
    const res = await fetch(`${API}/api/v1/goals`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, intensity, effort, deadline: deadline ? new Date(deadline).toISOString().split('T')[0] : null })
    });
    
    if (res.ok) {
      showToast('Milestone added! 🎯', 'success');
      document.getElementById('goal-title').value = '';
      document.getElementById('goal-intensity').value = '';
      document.getElementById('goal-effort').value = '';
      document.getElementById('goal-deadline').value = '';
      loadGoals();
      loadGoalProgress();
    } else {
      const data = await res.json().catch(() => ({}));
      errEl.textContent = data.detail || 'Failed to add milestone';
      errEl.style.display = 'block';
    }
  } catch (e) {
    errEl.textContent = 'Could not connect to server';
    errEl.style.display = 'block';
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = 'Add Milestone';
    }
  }
}

async function toggleGoalComplete(goalId, completed) {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/goals/${goalId}`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ completed })
    });
    
    if (res.ok) {
      showToast(completed ? 'Milestone completed! 🎉' : 'Milestone reopened', 'success');
      loadGoals();
      loadGoalProgress();
    } else {
      showToast('Failed to update milestone', 'error');
    }
  } catch (e) {
    showToast('Could not connect to server', 'error');
  }
}

async function deleteGoal(goalId) {
  if (!confirm('Delete this milestone?')) return;
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/goals/${goalId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      showToast('Milestone deleted', 'success');
      loadGoals();
      loadGoalProgress();
    } else {
      showToast('Failed to delete milestone', 'error');
    }
  } catch (e) {
    showToast('Could not connect to server', 'error');
  }
}

// ── ANALYTICS DASHBOARD ──
let currentAnalyticsPeriod = '7d';

async function loadAnalytics(period) {
  if (!currentUser || !authToken) return;
  
  currentAnalyticsPeriod = period;
  
  // Update period button styles
  document.querySelectorAll('.period-btn').forEach(btn => {
    btn.style.borderColor = 'var(--border)';
    btn.style.background = 'transparent';
    btn.style.color = 'var(--text-secondary)';
  });
  const activeBtn = document.getElementById(`period-${period}`);
  if (activeBtn) {
    activeBtn.style.borderColor = 'var(--accent)';
    activeBtn.style.background = 'rgba(108,99,255,0.2)';
    activeBtn.style.color = 'var(--accent)';
  }
  
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots/analytics?period=${period}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderAnalyticsCharts(data.data);
    } else {
      console.error('Failed to load analytics');
      showAnalyticsError();
    }
  } catch (e) {
    console.error('Error loading analytics:', e);
    showAnalyticsError();
  }
}

function showAnalyticsError() {
  const charts = ['chart-vektra', 'chart-networth', 'chart-sleep', 'chart-mood', 'chart-focus'];
  charts.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:13px">Could not load data</div>';
    }
  });
}

function renderAnalyticsCharts(data) {
  if (!data || data.length === 0) {
    showNoDataMessage();
    return;
  }
  
  renderSimpleChart('chart-vektra', data, 'vektra_score', 0, 100, '#6c63ff');
  renderSimpleChart('chart-networth', data, 'current_net_worth', null, null, '#22c55e');
  renderSimpleChart('chart-sleep', data, 'sleep_hours', 0, 12, '#f59e0b');
  renderSimpleChart('chart-mood', data, 'mood_score', 1, 10, '#ec4899');
  renderSimpleChart('chart-focus', data, 'focus_hours', 0, 12, '#06b6d4');
}

function showNoDataMessage() {
  const charts = ['chart-vektra', 'chart-networth', 'chart-sleep', 'chart-mood', 'chart-focus'];
  charts.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:13px">No data for this period</div>';
    }
  });
}

function renderSimpleChart(containerId, data, valueKey, minVal, maxVal, color) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  const values = data.map(d => d[valueKey]).filter(v => v !== null && v !== undefined);
  
  if (values.length === 0) {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:13px">No data</div>';
    return;
  }
  
  const actualMin = minVal !== null ? minVal : Math.min(...values);
  const actualMax = maxVal !== null ? maxVal : Math.max(...values);
  const range = actualMax - actualMin || 1;
  
  // Create simple bar chart
  const barsHtml = values.map((val, i) => {
    const normalized = (val - actualMin) / range;
    const height = Math.max(5, normalized * 100);
    const displayVal = val !== null && val !== undefined ? val.toFixed(1) : '—';
    return `
      <div style="flex:1;display:flex;align-items:end;justify-content:center;position:relative">
        <div style="width:80%;height:${height}%;background:${color};border-radius:4px 4px 0 0;min-height:4px;transition:height 0.3s ease"></div>
        <div style="position:absolute;top:-20px;font-size:10px;color:var(--text-muted)">${displayVal}</div>
      </div>
    `;
  }).join('');
  
  // Date labels (show first, middle, last)
  const dateLabels = data.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
  const labelHtml = `
    <div style="display:flex;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
      <span style="font-size:10px;color:var(--text-muted)">${dateLabels[0]}</span>
      ${dateLabels.length > 2 ? `<span style="font-size:10px;color:var(--text-muted)">${dateLabels[Math.floor(dateLabels.length / 2)]}</span>` : ''}
      <span style="font-size:10px;color:var(--text-muted)">${dateLabels[dateLabels.length - 1]}</span>
    </div>
  `;
  
  container.innerHTML = `
    <div style="display:flex;gap:4px;height:100%;align-items:end;padding-bottom:24px">
      ${barsHtml}
    </div>
    ${labelHtml}
  `;
}

// ── DAILY REMINDER ENGINE ──
let notificationsEnabled = false;
let reminderTime = '20:00';

async function toggleNotifications() {
  const toggleBtn = document.getElementById('notification-toggle');
  const timeContainer = document.getElementById('reminder-time-container');
  const statusEl = document.getElementById('notification-status');
  
  if (!('Notification' in window)) {
    statusEl.textContent = 'Notifications not supported in this browser';
    statusEl.style.color = 'var(--danger)';
    return;
  }
  
  if (notificationsEnabled) {
    // Disable notifications
    notificationsEnabled = false;
    toggleBtn.textContent = 'Enable';
    toggleBtn.style.borderColor = 'var(--border)';
    toggleBtn.style.background = 'transparent';
    toggleBtn.style.color = 'var(--text-secondary)';
    timeContainer.style.display = 'none';
    statusEl.textContent = 'Notifications disabled';
    statusEl.style.color = 'var(--text-muted)';
    
    // Clear any scheduled alarms
    if (navigator.alarms) {
      navigator.alarms.clear('vektra-daily-log');
    }
  } else {
    // Request permission
    const permission = await Notification.requestPermission();
    
    if (permission === 'granted') {
      notificationsEnabled = true;
      toggleBtn.textContent = 'Disable';
      toggleBtn.style.borderColor = 'var(--success)';
      toggleBtn.style.background = 'rgba(34,197,94,0.1)';
      toggleBtn.style.color = 'var(--success)';
      timeContainer.style.display = 'block';
      statusEl.textContent = 'Notifications enabled';
      statusEl.style.color = 'var(--success)';
      
      // Schedule the reminder
      scheduleReminder();
    } else {
      statusEl.textContent = 'Notification permission denied';
      statusEl.style.color = 'var(--danger)';
    }
  }
}

function scheduleReminder() {
  if (!notificationsEnabled) return;
  
  const timeInput = document.getElementById('reminder-time');
  if (timeInput) {
    reminderTime = timeInput.value;
  }
  
  // Parse the reminder time
  const [hours, minutes] = reminderTime.split(':').map(Number);
  
  // Calculate when to trigger
  const now = new Date();
  const triggerTime = new Date();
  triggerTime.setHours(hours, minutes, 0, 0);
  
  // If the time has already passed today, schedule for tomorrow
  if (triggerTime <= now) {
    triggerTime.setDate(triggerTime.getDate() + 1);
  }
  
  const delayMs = triggerTime - now;
  
  // Set timeout for the reminder
  setTimeout(() => {
    sendDailyReminder();
    // Reschedule for next day
    scheduleReminder();
  }, delayMs);
  
  // Also try to use the Alarm API if available (better for background)
  if (navigator.alarms && navigator.alarms.create) {
    try {
      navigator.alarms.create('vektra-daily-log', {
        when: triggerTime.getTime(),
        periodInMinutes: 24 * 60 // Daily
      });
    } catch (e) {
      console.log('Alarm API not available, using setTimeout fallback');
    }
  }
}

function sendDailyReminder() {
  const messages = [
    "Time to log your daily VEKTRA snapshot! 📝",
    "Don't break your streak - log today's progress! 🔥",
    "Your trajectory awaits - log your daily snapshot! 🎯",
    "Keep the momentum going - log today! ⚡",
    "Daily logging = better insights. Log now! 📊"
  ];
  
  const randomMessage = messages[Math.floor(Math.random() * messages.length)];
  
  if (Notification.permission === 'granted') {
    new Notification('VEKTRA Daily Reminder', {
      body: randomMessage,
      icon: '/favicon.ico',
      tag: 'vektra-daily-log'
    });
  }
}

// Listen for reminder time changes
document.addEventListener('DOMContentLoaded', () => {
  const timeInput = document.getElementById('reminder-time');
  if (timeInput) {
    timeInput.addEventListener('change', () => {
      reminderTime = timeInput.value;
      if (notificationsEnabled) {
        scheduleReminder();
        showToast('Reminder time updated', 'success');
      }
    });
  }
  
  // Check for existing notification permission
  if ('Notification' in window && Notification.permission === 'granted') {
    const toggleBtn = document.getElementById('notification-toggle');
    const timeContainer = document.getElementById('reminder-time-container');
    const statusEl = document.getElementById('notification-status');
    
    if (toggleBtn) {
      toggleBtn.textContent = 'Disable';
      toggleBtn.style.borderColor = 'var(--success)';
      toggleBtn.style.background = 'rgba(34,197,94,0.1)';
      toggleBtn.style.color = 'var(--success)';
    }
    if (timeContainer) timeContainer.style.display = 'block';
    if (statusEl) {
      statusEl.textContent = 'Notifications enabled';
      statusEl.style.color = 'var(--success)';
    }
    notificationsEnabled = true;
    scheduleReminder();
  }
});

// ── TRAJECTORY HISTORY ──
let currentHistoryFilter = 'all';
let allReports = [];

async function loadHistory() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/reports`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      allReports = await res.json();
      filterHistory(currentHistoryFilter);
    } else {
      console.error('Failed to load reports');
    }
  } catch (e) {
    console.error('Error loading reports:', e);
  }
}

function filterHistory(filter) {
  currentHistoryFilter = filter;
  
  // Update filter button styles
  document.querySelectorAll('.hist-filter-btn').forEach(btn => {
    btn.style.borderColor = 'var(--border)';
    btn.style.background = 'transparent';
    btn.style.color = 'var(--text-secondary)';
  });
  const activeBtn = document.getElementById(`hist-filter-${filter}`);
  if (activeBtn) {
    activeBtn.style.borderColor = 'var(--accent)';
    activeBtn.style.background = 'rgba(108,99,255,0.2)';
    activeBtn.style.color = 'var(--accent)';
  }
  
  // Filter reports
  let filtered = allReports;
  if (filter === 'weekly') {
    filtered = allReports.filter(r => r.report_type === 'weekly');
  } else if (filter === 'monthly') {
    filtered = allReports.filter(r => r.report_type === 'monthly');
  }
  
  renderHistory(filtered);
}

function renderHistory(reports) {
  const listEl = document.getElementById('history-list');
  const emptyEl = document.getElementById('history-empty');
  
  if (!listEl) return;
  
  if (!reports || reports.length === 0) {
    listEl.style.display = 'none';
    if (emptyEl) emptyEl.style.display = 'block';
    return;
  }
  
  listEl.style.display = 'flex';
  if (emptyEl) emptyEl.style.display = 'none';
  
  listEl.innerHTML = reports.map(report => {
    const date = new Date(report.generated_at);
    const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    const score = report.vektra_score ? Math.round(report.vektra_score) : '—';
    const typeLabel = report.report_type === 'weekly' ? 'Weekly' : report.report_type === 'monthly' ? 'Monthly' : report.report_type;
    
    // Determine trajectory status from summary
    let trajectoryStatus = 'Neutral';
    let trajectoryColor = 'var(--text-muted)';
    if (report.summary_text) {
      const summary = report.summary_text.toLowerCase();
      if (summary.includes('improving') || summary.includes('positive') || summary.includes('upward')) {
        trajectoryStatus = 'Improving';
        trajectoryColor = 'var(--success)';
      } else if (summary.includes('declining') || summary.includes('negative') || summary.includes('downward')) {
        trajectoryStatus = 'Declining';
        trajectoryColor = 'var(--danger)';
      } else if (summary.includes('stable') || summary.includes('steady')) {
        trajectoryStatus = 'Stable';
        trajectoryColor = 'var(--accent)';
      }
    }
    
    return `
      <div onclick="viewReport(${report.id})" style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:1rem;cursor:pointer;transition:border-color 0.2s ease" onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--border)'">
        <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px">
          <div>
            <div style="font-weight:600;font-size:14px;margin-bottom:4px">${typeLabel} Report</div>
            <div style="font-size:12px;color:var(--text-muted)">${formattedDate}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:20px;font-weight:700;color:var(--accent)">${score}</div>
            <div style="font-size:10px;color:var(--text-muted)">Score</div>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
          <div style="font-size:12px;color:${trajectoryColor};font-weight:600">${trajectoryStatus}</div>
          <div style="font-size:11px;color:var(--text-muted)">Tap to view →</div>
        </div>
      </div>
    `;
  }).join('');
}

async function viewReport(reportId) {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/reports/${reportId}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const report = await res.json();
      // Load the report into the current report view
      currentReport = report;
      goTo('reports');
      loadReport();
    } else {
      showToast('Failed to load report', 'error');
    }
  } catch (e) {
    showToast('Could not connect to server', 'error');
  }
}

// ── WEEKLY COMPARISON ENGINE ──
async function loadWeeklyComparison() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots/comparison`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderWeeklyComparison(data);
    } else {
      console.error('Failed to load comparison');
      document.getElementById('comparison-metrics').innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:40px;color:var(--text-muted);font-size:13px">Comparison unavailable</div>';
    }
  } catch (e) {
    console.error('Error loading comparison:', e);
    document.getElementById('comparison-metrics').innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:40px;color:var(--text-muted);font-size:13px">Could not load comparison</div>';
  }
}

function renderWeeklyComparison(data) {
  const container = document.getElementById('comparison-metrics');
  if (!container) return;
  
  const metrics = [
    { key: 'vektra_score', label: 'VEKTRA Score', format: (v) => v ? v.toFixed(1) : '—' },
    { key: 'mood_score', label: 'Mood', format: (v) => v ? v.toFixed(1) : '—' },
    { key: 'sleep_hours', label: 'Sleep', format: (v) => v ? v.toFixed(1) + 'h' : '—' },
    { key: 'focus_hours', label: 'Focus', format: (v) => v ? v.toFixed(1) + 'h' : '—' },
    { key: 'net_cash_flow', label: 'Cash Flow', format: (v) => v ? (v >= 0 ? '+' : '') + v.toFixed(0) : '—' }
  ];
  
  const html = metrics.map(metric => {
    const current = data.current_week[metric.key];
    const previous = data.previous_week[metric.key];
    const change = data.changes[metric.key];
    
    if (change === null || current === null || previous === null) {
      return `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0">
          <span style="font-size:13px;color:var(--text-secondary)">${metric.label}</span>
          <span style="font-size:13px;color:var(--text-muted)">No data</span>
        </div>
      `;
    }
    
    const isPositive = change >= 0;
    const arrow = isPositive ? '↑' : '↓';
    const color = isPositive ? 'var(--success)' : 'var(--danger)';
    const sign = isPositive ? '+' : '';
    
    return `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0">
        <span style="font-size:13px;color:var(--text-secondary)">${metric.label}</span>
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-size:13px;color:var(--text-primary)">${metric.format(current)}</span>
          <span style="font-size:12px;color:${color};font-weight:600">${arrow} ${sign}${change.toFixed(1)}%</span>
        </div>
      </div>
    `;
  }).join('');
  
  container.innerHTML = html;
}

// ── SMART DASHBOARD ──
function generateSmartInsight(snapshots, latest) {
  if (!snapshots || snapshots.length === 0) {
    return "Log your first snapshot to unlock personalized insights";
  }
  
  const insights = [];
  
  // Check for streak warning
  const streak = calculateStreak(snapshots);
  if (streak === 0 && snapshots.length > 0) {
    insights.push("🔥 Your streak has reset. Log today to start building momentum!");
  } else if (streak >= 7) {
    insights.push(`🔥 Amazing! You're on a ${streak}-day streak. Keep it going!`);
  } else if (streak >= 3) {
    insights.push(`🔥 Great progress! ${streak}-day streak and counting.`);
  }
  
  // Check score trend
  if (latest && latest.vektra_score) {
    if (latest.vektra_score >= 80) {
      insights.push("🚀 Your trajectory is excellent! You're performing at a high level.");
    } else if (latest.vektra_score >= 60) {
      insights.push("📈 Good momentum. Focus on consistency to reach the next level.");
    } else if (latest.vektra_score < 40) {
      insights.push("⚠️ Your score needs attention. Review your habits and make small improvements.");
    }
  }
  
  // Check sleep patterns
  if (latest && latest.sleep_hours) {
    if (latest.sleep_hours < 6) {
      insights.push("😴 Low sleep detected. Prioritize rest for better performance.");
    } else if (latest.sleep_hours >= 7 && latest.sleep_hours <= 9) {
      insights.push("💤 Great sleep! You're well-rested for peak performance.");
    }
  }
  
  // Check financial health
  if (latest && latest.survival_runway) {
    if (latest.survival_runway < 30) {
      insights.push("💰 Low runway warning. Focus on increasing income or reducing expenses.");
    } else if (latest.survival_runway >= 180) {
      insights.push("💰 Strong financial position. You have excellent runway.");
    }
  }
  
  // Check goal progress
  if (latest && latest.target_hit_bool === false) {
    insights.push("🎯 You missed yesterday's goal. Reflect and adjust your approach.");
  } else if (latest && latest.target_hit_bool === true) {
    insights.push("🎯 Goal hit! Keep the momentum going.");
  }
  
  // Check focus
  if (latest && latest.focus_hours) {
    if (latest.focus_hours >= 6) {
      insights.push("⚡ Excellent focus hours today. Deep work pays off!");
    } else if (latest.focus_hours < 2) {
      insights.push("⚡ Low focus time. Try to block time for deep work tomorrow.");
    }
  }
  
  // Return a random insight if multiple exist
  if (insights.length > 0) {
    return insights[Math.floor(Math.random() * insights.length)];
  }
  
  return "Keep logging daily to unlock more personalized insights!";
}

// ── Score reveal after log submission ──
function showScoreReveal(snap) {
  const score = snap.vektra_score || 0;
  
  // Set message based on score
  const message = score >= 80 ? "You're locked in. Keep this energy going." :
                  score >= 70 ? "Strong trajectory. One more push." :
                  score >= 60 ? "Moving forward. The gap is closing." :
                  score >= 50 ? "Steady. Identify your weakest engine." :
                  "The data doesn't lie. Tomorrow is a new vector.";

  document.getElementById('reveal-message').textContent = message;

  // Show metrics
  const metrics = [];
  if (snap.survival_runway) metrics.push({label:'Runway', val: snap.survival_runway + ' days'});
  if (snap.burn_rate) metrics.push({label:'Burn Rate', val: snap.burn_rate});
  if (snap.leverage_score) metrics.push({label:'Leverage', val: snap.leverage_score.toFixed(2)});

  document.getElementById('reveal-metrics').innerHTML = metrics.map(m => `
    <div style="text-align:center">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">${m.label}</div>
      <div style="font-size:18px;font-weight:700">${m.val}</div>
    </div>
  `).join('');

  goTo('score-reveal');

  // Animate score counting up
  const el = document.getElementById('reveal-score');
  const duration = 1800;
  const start = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(score * eased);
    el.textContent = current;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);

  // Auto-go to dashboard after 5 seconds
  setTimeout(() => {
    goTo('dashboard');
    loadDashboard();
  }, 5000);
}