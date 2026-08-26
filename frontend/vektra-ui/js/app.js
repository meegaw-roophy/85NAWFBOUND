// ── VEKTRA Frontend Application ──
console.log('VEKTRA app.js loaded successfully');

// ── API base URL ──
const API = 'https://vektra-backend-qic7.onrender.com';

// ── Token storage ──
let authToken = null; // Ensure this is not declared as a 'const' anywhere!
let currentUser = {};
let currentScreen = 'welcome';
let pendingReferralCode = null;
const quickMoneyOfferRequested = new URLSearchParams(window.location.search).get('offer') === 'quick-money';

// ── Performance Utilities ──

// Debounce function to limit rapid API calls
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Local storage cache with TTL
const Cache = {
  set(key, data, ttlMinutes = 30) {
    try {
      const item = {
        data,
        expiry: Date.now() + (ttlMinutes * 60 * 1000)
      };
      localStorage.setItem(`vektra_${key}`, JSON.stringify(item));
    } catch(e) {
      console.warn('Cache set failed:', e);
    }
  },
  
  get(key) {
    try {
      const itemStr = localStorage.getItem(`vektra_${key}`);
      if (!itemStr) return null;
      
      const item = JSON.parse(itemStr);
      if (Date.now() > item.expiry) {
        localStorage.removeItem(`vektra_${key}`);
        return null;
      }
      return item.data;
    } catch(e) {
      console.warn('Cache get failed:', e);
      return null;
    }
  },
  
  clear() {
    try {
      Object.keys(localStorage)
        .filter(k => k.startsWith('vektra_'))
        .forEach(k => localStorage.removeItem(k));
    } catch(e) {
      console.warn('Cache clear failed:', e);
    }
  }
};

// Request deduplication - prevents duplicate concurrent calls
const pendingRequests = new Map();

async function dedupedFetch(url, options = {}) {
  const cacheKey = `${options.method || 'GET'}_${url}_${JSON.stringify(options.body || '')}`;
  
  if (pendingRequests.has(cacheKey)) {
    return pendingRequests.get(cacheKey);
  }
  
  const promise = fetch(url, options)
    .finally(() => {
      pendingRequests.delete(cacheKey);
    });
  
  pendingRequests.set(cacheKey, promise);
  return promise;
}

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
  const loader = document.getElementById('global-loader');
  const loaderText = document.getElementById('loader-text');
  if (loader && loaderText) {
    loaderText.textContent = text;
    loader.classList.add('active');
  }
}

function hideLoader() {
  const loader = document.getElementById('global-loader');
  if (loader) {
    loader.classList.remove('active');
  }
}

// ── Error handling helper ──
function showError(message, containerId = null) {
  if (containerId) {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `
        <div style="text-align:center;padding:3rem 1.5rem">
          <div style="font-size:48px;margin-bottom:1rem">⚠️</div>
          <div style="font-size:16px;font-weight:600;color:var(--text-primary);margin-bottom:8px">Something went wrong</div>
          <div style="font-size:13px;color:var(--text-muted);margin-bottom:1.5rem">${message}</div>
          <button class="btn-primary" onclick="location.reload()">Try Again</button>
        </div>
      `;
    }
  } else {
    showToast(message, 'error');
  }
}

// ── Empty state helper ──
function showEmptyState(containerId, icon, title, subtitle, actionText = null, actionCallback = null) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  let actionHtml = '';
  if (actionText && actionCallback) {
    actionHtml = `<button class="btn-primary" onclick="${actionCallback}">${actionText}</button>`;
  }
  
  container.innerHTML = `
    <div style="text-align:center;padding:3rem 1.5rem">
      <div style="font-size:48px;margin-bottom:1rem">${icon}</div>
      <div style="font-size:16px;font-weight:600;color:var(--text-primary);margin-bottom:8px">${title}</div>
      <div style="font-size:13px;color:var(--text-muted);margin-bottom:1.5rem">${subtitle}</div>
      ${actionHtml}
    </div>
  `;
}

// ── Screen navigation ──
function goTo(screen) {
  console.log(`Routing Engine Active -> Transitioning to: ${screen}`);
  
  const target = document.getElementById(screen);
  if (!target) {
    console.error(`UI Error: Element with ID '${screen}' not found in DOM layout.`);
    return;
  }
  
  // Safely hide the current active section view container
  const current = document.getElementById(currentScreen);
  if (current) current.style.display = 'none';
  
  // Unveil the new target section view
  target.style.display = 'flex';
  
  // FORCE CRUSH THE SPLASH OVERLAY: If navigating away from splash, rip the mask off!
  const splashOverlay = document.getElementById('splash');
  if (splashOverlay && screen !== 'splash') {
    splashOverlay.style.display = 'none';
  }
  
  currentScreen = screen;
  
  // Initialize offer countdown if navigating to upgrade screen
  if (screen === 'upgrade') {
    initOfferCountdown();
  }
  
  // Load news if navigating to news screen
  if (screen === 'news') {
    loadNews();
  }
  
  // Load goals if navigating to goals screen
  if (screen === 'goals') {
    loadGoals();
    loadGoalProgress();
  }
  
  // Load achievements if navigating to achievements screen
  if (screen === 'achievements') {
    loadAchievements();
    loadStreakCalendar();
  }
  
  // Strip splash out of auth controller array and toggle bottom navigation bar
  const authScreens = ['welcome', 'login', 'register', 'password-reset-request', 'password-reset']; 
  if (authScreens.includes(screen)) {
    hideBottomNav();
  } else {
    showBottomNav();
    updateNavActive(screen);
  }
  
  console.log(`Successfully completed navigation sequence to screen layout: ${screen}`);
}

// ── 2. INSTAGRAM-STYLE NAVIGATION INTERCEPTOR ──
function navTo(screen) {
  console.log(`NavTo intercepting screen token parameter: -> ${screen}`);
  
  // Maps your menu option items directly to your actual HTML section view container IDs
  let realTargetViewId = screen;
  
  if (screen === 'home') {
    realTargetViewId = 'dashboard';
  } else if (screen === 'reports') {
    realTargetViewId = 'reports'; // Adjust to your history or reports view container ID if separate
  } else if (screen === 'analytics') {
    realTargetViewId = 'dashboard'; 
  }

  goTo(realTargetViewId);
  updateNavActive(screen);
}

// ── 3. SAFE BOTTOM NAV DISPLAY UTILITIES (No Null-Property Crashes) ──
function showBottomNav() {
  const nav = document.getElementById('bottom-nav');
  if (nav) {
    nav.style.display = 'block'; 
  } else {
    console.warn("UI Warning: 'bottom-nav' element missing from DOM structure.");
  }
}

function hideBottomNav() {
  const nav = document.getElementById('bottom-nav');
  if (nav) {
    nav.style.display = 'none'; 
  }
}

function updateNavActive(activeScreen) {
  // Clear all previous active icon highlight color classes safely
  const items = document.querySelectorAll('.nav-item');
  items.forEach(item => {
    item.style.color = 'var(--text-muted)';
  });
  
  // Find the icon using the unified structural ID syntax: nav-[screen_name]
  const currentIcon = document.getElementById(`nav-${activeScreen}`);
  if (currentIcon) {
    currentIcon.style.color = 'var(--accent)'; // Highlights active item purple/pink
  }
}

// 🌐 CRITICAL MODULE MOUNT BRIDGE: Force mount functions to global browser scope
window.goTo = goTo;
window.navTo = navTo;
window.showBottomNav = showBottomNav;
window.hideBottomNav = hideBottomNav;
window.updateNavActive = updateNavActive;


// ── Clean Auto-login Engine on Page Load ──
window.addEventListener('DOMContentLoaded', async () => {
  console.log('DOM loaded - starting initialization');

  // 1. Force hide splash screen immediately
  const splash = document.getElementById('splash');
  if (splash) {
    splash.style.display = 'none';
    splash.style.opacity = '0';
    splash.style.visibility = 'hidden';
  }

  // 2. Capture referral code from URL if present
  const params = new URLSearchParams(window.location.search);
  if (params.has('ref')) {
    pendingReferralCode = params.get('ref')?.trim().toUpperCase() || null;
    if (pendingReferralCode) {
      localStorage.setItem('pendingReferralCode', pendingReferralCode);
    }
  } else {
    pendingReferralCode = localStorage.getItem('pendingReferralCode');
  }

  // 3. Fetch locally stored authentication variables
  let savedToken = localStorage.getItem('vektra_token');
  console.log('Token from storage:', savedToken);

  // 4. Simple Route: If no token exists, send them straight to the entry wall
  if (!savedToken || savedToken === "null" || savedToken === "undefined") {
    console.log('No token found - routing to welcome view');
    localStorage.removeItem('vektra_token'); // Clear corrupted states
    goTo('welcome');
    return;
  }

  // 4. Try auto-login if token exists
  authToken = savedToken;
  goTo('welcome'); // Show welcome while checking

  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      currentUser = await res.json();
      console.log('Auto-login successful:', currentUser);
      goTo('dashboard');
      await loadDashboard();
    } else {
      console.log('Token invalid - staying on welcome');
      localStorage.removeItem('vektra_token');
      authToken = null;
    }
  } catch (err) {
    console.log('Server error - staying on welcome:', err);
  }
});

// ── Register service worker ──
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then(() => console.log('VEKTRA SW registered'))
      .catch(e => console.log('SW error', e));
  });
}

async function detectUserLocation() {
  const CACHE_KEY = 'user_location_data';
  const CACHE_TIME_KEY = 'user_location_time';
  const ONE_DAY = 24 * 60 * 60 * 1000;

  // 1. Check valid cache
  try {
    const cachedData = localStorage.getItem(CACHE_KEY);
    const cachedTime = localStorage.getItem(CACHE_TIME_KEY);
    
    if (cachedData && cachedTime && (Date.now() - cachedTime < ONE_DAY)) {
      return JSON.parse(cachedData);
    }
  } catch (e) {
    console.warn('LocalStorage not available:', e);
  }

  // Default fallback data
  const fallback = {
    country_code: 'US',
    currency: 'USD',
    language: 'en',
    timezone: 'UTC',
    city: '',
    country: 'Unknown',
    location_string: 'Unknown'
  };

  // 2. Fetch with a 5-second timeout
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const res = await fetch('https://ipapi.co', { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    
    const data = await res.json();
    if (data.error) throw new Error(data.reason || 'API error');

    const city = data.city || '';
    const country = data.country_name || 'Unknown';
    
    const result = {
      country_code: data.country_code || 'US',
      currency: data.currency || 'USD',
      language: data.languages ? data.languages.split(',')[0] : 'en',
      timezone: data.timezone || 'UTC',
      city: city,
      country: country,
      location_string: city ? `${city}, ${country}` : country
    };

    // 3. Save to cache
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(result));
      localStorage.setItem(CACHE_TIME_KEY, Date.now().toString());
    } catch (e) {
      console.warn('Failed to save to localStorage:', e);
    }

    return result;

  } catch (e) {
    console.log('Location detection failed, using defaults:', e.message);
    return fallback;
  }
}


// ── Email validation helper ──
function validateEmail(email) {
  // Check format
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { valid: false, message: 'Please enter a valid email address.' };
  }
  
  // Check for disposable email domains (common ones)
  const disposableDomains = [
    'tempmail.com', 'guerrillamail.com', 'mailinator.com', '10minutemail.com',
    'yopmail.com', 'trashmail.com', 'sharklasers.com', 'getairmail.com',
    'throwawaymail.com', 'temp-mail.org', 'fakeinbox.com', 'maildrop.cc'
  ];
  
  const domain = email.split('@')[1].toLowerCase();
  if (disposableDomains.includes(domain)) {
    return { valid: false, message: 'Disposable email addresses are not allowed.' };
  }
  
  // Check for common typos in major domains
  const commonTypos = {
    'gmial.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    'gmil.com': 'gmail.com',
    'yahooo.com': 'yahoo.com',
    'yaho.com': 'yahoo.com',
    'hotmial.com': 'hotmail.com',
    'hotmil.com': 'hotmail.com',
    'outlok.com': 'outlook.com',
    'outlookt.com': 'outlook.com'
  };
  
  if (commonTypos[domain]) {
    return { valid: false, message: `Did you mean ${email.split('@')[0]}@${commonTypos[domain]}?` };
  }
  
  return { valid: true };
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
  
  // Use improved email validation
  const emailValidation = validateEmail(email);
  if (!emailValidation.valid) {
    errEl.textContent = emailValidation.message;
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
    // Auto-detect user location
    const locationData = await detectUserLocation();
    const referralInput = document.getElementById('reg-referral')?.value.trim();
    const referralCode = referralInput || pendingReferralCode || undefined;
    
    const bodyPayload = {
      username,
      email,
      password,
      current_location: locationData.location,
      currency: locationData.currency
    };
    if (referralCode) {
      bodyPayload.referral_code = referralCode;
    }
    
    const res = await fetch(`${API}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bodyPayload)
    });
    const data = await res.json();
    if (!res.ok) {
      errEl.textContent = data.detail || 'Registration failed. Try again.';
      errEl.style.display = 'block';
      return;
    }
    // Auto-login after registration (email verification removed)
    localStorage.removeItem('pendingReferralCode');
    pendingReferralCode = null;
    
    // Login automatically
    const loginRes = await fetch(`${API}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
    });
    
    if (loginRes.ok) {
      const loginData = await loginRes.json();
      localStorage.setItem('vektra_token', loginData.access_token);
      authToken = loginData.access_token;
      
      // Get user data
      const userRes = await fetch(`${API}/api/v1/users/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      
      if (userRes.ok) {
        currentUser = await userRes.json();
        goTo('onboard-1');
        showToast('Welcome to VEKTRA! 🚀', 'success', 5000);
      }
    } else {
      showToast('Registration successful. Please log in.', 'success');
      goTo('login');
    }
  } catch (err) {
    errEl.textContent = 'Connecting to server... please try again in 30 seconds.';
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
  try {
    const tokenBody = new URLSearchParams({ username, password });
    const tokenRes = await fetch(`${API}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: tokenBody
    });

    if (!tokenRes.ok) {
        const error = await tokenRes.text();
        console.error("LOGIN FAILED:", tokenRes.status, error);
        return;
    }

    const tokenData = await tokenRes.json();
    authToken = tokenData.access_token;
    localStorage.setItem('vektra_token', authToken);

    // 1. Fetch primary profile records
    const userRes = await fetch(`${API}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (userRes.ok) {
      currentUser = await userRes.json();
    } else {
      currentUser = {}; // Ensure it's never null to prevent layout crashes
    }

    // Clear cache on fresh login
    Cache.clear();

    // 2. Auto-detect and sync location if not set
    if (currentUser && (!currentUser.current_location || !currentUser.currency)) {
      const locationData = await detectUserLocation();
      await fetch(`${API}/api/v1/users/me`, {
        method: 'PATCH',
        headers: { 
          'Authorization': `Bearer ${authToken}`, 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({
          current_location: locationData.location || currentUser.current_location,
          currency: locationData.currency || currentUser.currency
        })
      });
    }

    // 3. Absolute safety fallback to prevent "reading properties of null"
    if (!currentUser) {
      currentUser = { currency: "USD", current_location: "US" };
    }

    // 4. Secure Onboarding Core Pipeline Redirect
    if (!currentUser.north_star) {
      goTo('onboard-1');
    } else {
      goTo('dashboard');
      loadDashboard();
    }

  } catch (error) {
    console.error("Critical login connection error:", error);
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
    errEl.textContent = 'Connecting to server... please try again in 30 seconds.';
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
  Cache.clear();
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

// ── Load dashboard ──
async function loadDashboard() {
  console.log('loadDashboard started');

  if (!currentUser) {
    console.log('No currentUser');
    return;
  }
  
  console.log('currentUser =', currentUser);

  // Dynamic greeting
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' :
                  hour < 17 ? 'Good afternoon' :
                  hour < 21 ? 'Good evening' : 'Still up?';
  const dateStr = new Date().toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric'});
  document.getElementById('dash-greeting').textContent = greeting;
  document.getElementById('dash-date').textContent = dateStr;
  
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
    renderScoreChart(snapshots);
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
      generateInsight(latest);
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

        // Calculate direction angle based on score trend
        const angleEl = document.getElementById('dash-vector-angle');
        if (angleEl && snapshots.length >= 2) {
          const prevScore = snapshots[1].vektra_score || 50;
          const scoreDiff = score - prevScore;
          // Map score difference to angle (-45 to +45 degrees)
          const angle = Math.max(-45, Math.min(45, scoreDiff * 2));
          angleEl.textContent = `${angle.toFixed(1)}° (θ)`;
        }

        // AI verification based on data quality
        const accuracyEl = document.getElementById('dash-vector-accuracy');
        if (accuracyEl) {
          const dataQuality = Math.min(100, (snapshots.length / 7) * 100);
          accuracyEl.textContent = `${Math.round(dataQuality)}% Match`;
        }

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
  checkBirthday();
  checkPaymentReturn();
}

// ── NOTIFICATION SYSTEM ──
let notifications = [];

function addNotification(type, title, message) {
  const notification = {
    id: Date.now(),
    type,
    title,
    message,
    timestamp: new Date().toISOString(),
    read: false
  };
  
  notifications.unshift(notification);
  updateNotificationBell();
  saveNotifications();
}

function updateNotificationBell() {
  const bell = document.getElementById('notification-bell');
  const badge = document.getElementById('notification-badge');
  const unreadCount = notifications.filter(n => !n.read).length;
  
  if (unreadCount > 0) {
    bell.style.display = 'block';
    badge.style.display = 'flex';
    badge.textContent = unreadCount > 9 ? '9+' : unreadCount;
  } else {
    bell.style.display = 'none';
    badge.style.display = 'none';
  }
}

function showNotifications() {
  const panel = document.getElementById('notification-panel');
  const list = document.getElementById('notification-list');
  
  if (panel.style.display === 'block') {
    panel.style.display = 'none';
    return;
  }
  
  panel.style.display = 'block';
  renderNotifications();
  
  // Mark all as read
  notifications.forEach(n => n.read = true);
  updateNotificationBell();
  saveNotifications();
}

function renderNotifications() {
  const list = document.getElementById('notification-list');
  
  if (notifications.length === 0) {
    list.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-muted);font-size:13px">No notifications yet</div>';
    return;
  }
  
  list.innerHTML = notifications.map(n => `
    <div style="background:var(--bg-secondary);border-radius:var(--radius-sm);padding:12px;border-left:3px solid ${getNotificationColor(n.type)}">
      <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:4px">${n.title}</div>
      <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">${n.message}</div>
      <div style="font-size:10px;color:var(--text-muted)">${formatNotificationTime(n.timestamp)}</div>
    </div>
  `).join('');
}

function getNotificationColor(type) {
  switch(type) {
    case 'achievement': return 'var(--success)';
    case 'streak': return 'var(--warning)';
    case 'milestone': return 'var(--accent)';
    default: return 'var(--border)';
  }
}

function formatNotificationTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}

function clearNotifications() {
  notifications = [];
  updateNotificationBell();
  saveNotifications();
  renderNotifications();
}

function saveNotifications() {
  localStorage.setItem('vektra_notifications', JSON.stringify(notifications));
}

function loadNotifications() {
  const saved = localStorage.getItem('vektra_notifications');
  if (saved) {
    notifications = JSON.parse(saved);
    updateNotificationBell();
  }
}

// Load notifications on startup
loadNotifications();

// ── Daily log helpers ──
let goalHit = null;

function updateSlider(name) {
  const input = document.getElementById(`inp-${name}`);
  const val = document.getElementById(`val-${name}`);
  if (input && val) val.textContent = input.value;
  updateProgress();
}

function quickSetMood(value) {
  const input = document.getElementById('inp-mood');
  const val = document.getElementById('val-mood');
  if (input && val) {
    input.value = value;
    val.textContent = value;
    updateProgress();
  }
}

function quickSetSleep(value) {
  const input = document.getElementById('inp-sleep');
  const val = document.getElementById('val-sleep');
  if (input && val) {
    input.value = value;
    val.textContent = value;
    updateProgress();
  }
}

function quickSetFocus(value) {
  const input = document.getElementById('inp-focushours');
  const val = document.getElementById('val-focushours');
  if (input && val) {
    input.value = value;
    val.textContent = value;
    updateProgress();
  }
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
  
  // Hide goal hit question for new users
  fetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
    headers: { 'Authorization': `Bearer ${authToken}` }
  }).then(r => r.json()).then(snapshots => {
    const goalSection = document.getElementById('goal-hit-section');
    if (goalSection) {
      goalSection.style.display = snapshots.length === 0 ? 'none' : 'block';
    }
  }).catch(() => {});
  
  goTo('daily-log');
  restoreDraft();
}

function openWeeklyQuestions() {
  goTo('weekly-questions');
  document.getElementById('weekly-questions-form').style.display = 'flex';
  document.getElementById('monthly-questions-form').style.display = 'none';
  document.querySelector('#weekly-questions > div:first-child > div:first-child > div:first-child').textContent = 'Weekly Check-in';
}

function openMonthlyQuestions() {
  goTo('weekly-questions');
  document.getElementById('weekly-questions-form').style.display = 'none';
  document.getElementById('monthly-questions-form').style.display = 'flex';
  document.querySelector('#weekly-questions > div:first-child > div:first-child > div:first-child').textContent = 'Monthly Goals';
}

async function submitWeeklyQuestions() {
  if (!currentUser || !authToken) return;
  
  const win = document.getElementById('wq-win').value.trim();
  const blocker = document.getElementById('wq-blocker').value.trim();
  const focus = document.getElementById('wq-focus').value.trim();
  const satisfaction = document.getElementById('inp-wq-satisfaction').value;
  
  try {
    const res = await fetch(`${API}/api/v1/questions/users/${currentUser.id}/weekly-questions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        biggest_win: win,
        blockers: blocker,
        next_week_focus: focus,
        satisfaction: parseInt(satisfaction),
        week_number: getWeekNumber(new Date())
      })
    });
    
    if (res.ok) {
      showToast('Weekly check-in saved! 🎯', 'success', 3000);
      goTo('dashboard');
    } else {
      showToast('Failed to save weekly check-in', 'error', 3000);
    }
  } catch (e) {
    console.error('Error submitting weekly questions:', e);
    showToast('Connection error. Try again.', 'error', 3000);
  }
}

async function submitMonthlyQuestions() {
  if (!currentUser || !authToken) return;
  
  const goal = document.getElementById('mq-goal').value.trim();
  const habits = document.getElementById('mq-habits').value.trim();
  const success = document.getElementById('mq-success').value.trim();
  const confidence = document.getElementById('inp-mq-confidence').value;
  
  try {
    const res = await fetch(`${API}/api/v1/questions/users/${currentUser.id}/monthly-questions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        monthly_goal: goal,
        habits_to_build: habits,
        success_definition: success,
        confidence: parseInt(confidence),
        month: new Date().getMonth() + 1,
        year: new Date().getFullYear()
      })
    });
    
    if (res.ok) {
      showToast('Monthly goals saved! 🚀', 'success', 3000);
      goTo('dashboard');
    } else {
      showToast('Failed to save monthly goals', 'error', 3000);
    }
  } catch (e) {
    console.error('Error submitting monthly questions:', e);
    showToast('Connection error. Try again.', 'error', 3000);
  }
}

function getWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
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
  
  if (!moodVal || moodVal === '') {
    showToast('Please select your mood', 'warning');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Today's Log 🔥";
    }
    return;
  }
  if (!sleepVal || sleepVal === '') {
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

  // Helper to safely get values
  const getVal = (id) => document.getElementById(id)?.value || null;
  const getInt = (id) => parseInt(getVal(id)) || null;
  const getFloat = (id) => parseFloat(getVal(id)) || null;

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
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    // 1. Handle success
    if (res.ok) {
      const snap = await res.json();
      checkNewAchievements(snap);
      showScoreReveal(snap);
      clearDraft();
      Cache.set(`snapshots_${currentUser.id}`, null, 0);
      return; // Exit early on success
    }

    // 2. Safely parse JSON for error statuses
    let data = {};
    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await res.json();
    }

    // 3. Handle specific 403 error
    if (res.status === 403 && data.detail === 'free_tier_limit_reached') {
      showToast('7-day free trial complete — upgrade to keep logging 🔥', 'warning', 5000);
      setTimeout(() => {
        goTo('upgrade');
        openUpgrade();
      }, 1500);
      return;
    }

    // 4. Handle all other server errors
    errEl.textContent = data.detail || `Server error: ${res.status}`;
    errEl.style.display = 'block';

  } catch (e) {
    // 5. Handle actual network/connection failures
    console.error(e);
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
  const dob = document.getElementById('ob-dob').value;
  onboardData.dob = document.getElementById('ob-dob').value || null;
  const errEl = document.getElementById('ob1-error');
  const btnEl = document.getElementById('ob1-btn');
  errEl.style.display = 'none';
  
  // DOB is now required for birthday cards
  if (!dob) {
    errEl.textContent = 'Please enter your date of birth.';
    errEl.style.display = 'block';
    return;
  }
  
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
  onboardData.dob = dob;
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
        dob: onboardData.dob || null,
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
  // In onboardStep3() after goTo('dashboard')
  showToast('Welcome to VEKTRA, ' + (currentUser?.username || '') + '! Log your first day to activate your score 🔥', 'success', 6000);
}

// ── Load and display report ──
async function loadReport(reportType = 'weekly') {
  console.log('loadReport called - START');
  
  if (!currentUser || !authToken) { 
    console.log('No user or auth token - ABORTING');
    showToast('Please log in to view your report', 'error');
    return;
  }
  
  const reportsScreen = document.getElementById('reports');
  if (!reportsScreen) {
    console.error('Reports screen not found - ABORTING');
    showToast('Reports screen not available', 'error');
    return;
  }
  
  console.log('Navigating to reports screen');
  goTo('reports');
  console.log('Current screen after goTo:', currentScreen);
  
  showLoader('Generating your report...');
  
  const narrativeEl = document.getElementById('report-narrative');
  if (narrativeEl) narrativeEl.textContent = 'Generating...';
  
  try {
    console.log('Fetching report from API');
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/reports/generate`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_type: reportType })
    });
    
    console.log('Report API response status:', res.status);
    
    if (!res.ok) {
      hideLoader();
      const data = await res.json().catch(() => ({}));
      console.error('Report generation failed:', data);
      showToast(data.detail || 'Could not generate report. Try again.', 'error');
      if (narrativeEl) narrativeEl.textContent = 'Could not load report. Try again.';
      return;
    }
    
    const report = await res.json();
    console.log('Report data received:', report);
    
    // Store current report ID for sharing
    currentReportId = report.id;
    
    // Load existing sharing settings if available
    if (report.share_with_public !== undefined) {
      document.getElementById('share-public').checked = report.share_with_public;
    }
    if (report.share_with_circles !== undefined) {
      document.getElementById('share-circles').checked = report.share_with_circles;
    }
    if (report.share_anonymously !== undefined) {
      document.getElementById('share-anonymous').checked = report.share_anonymously;
    }
    if (report.custom_message) {
      document.getElementById('share-message').value = report.custom_message;
    }
    if (report.share_theme) {
      document.getElementById('share-theme').value = report.share_theme;
    }
    if (report.link_url) {
      document.getElementById('share-link').value = report.link_url;
      document.getElementById('share-link-container').style.display = 'block';
    }
    
    hideLoader();
    
    console.log('Rendering report data...');
    const content = report.content || {};
    const uniqueDays = content.unique_days_logged ?? content.days_logged ?? 0;
    const reportCountdown = content.report_countdown ?? Math.max(0, 7 - uniqueDays);
    const signalScores = content.signal_scores || {};
    const reportReady = content.report_ready ?? uniqueDays >= 3;
    const readinessMessage = content.report_readiness_message || (reportReady ? 'Your weekly report is ready.' : 'Log a few more days to unlock a richer weekly report.');

    const scoreEl = document.getElementById('report-score');
    const periodEl = document.getElementById('report-period');
    const daysEl = document.getElementById('report-days');
    const timerEl = document.getElementById('report-timer');
    const cashflowEl = document.getElementById('report-cashflow');
    const goalsEl = document.getElementById('report-goals');
    
    if (scoreEl) scoreEl.textContent = report.vektra_score ? report.vektra_score.toFixed(0) : '—';
    if (periodEl) {
      if (reportType === 'daily') {
        periodEl.textContent = 'Daily Report';
      } else if (reportType === 'monthly') {
        periodEl.textContent = 'Monthly Report';
      } else if (reportType === 'birthday') {
        periodEl.textContent = 'Birthday Report';
      } else {
        periodEl.textContent = uniqueDays > 0 ? `${uniqueDays} unique day${uniqueDays === 1 ? '' : 's'} logged` : 'No week data yet';
      }
    }
    if (daysEl) daysEl.textContent = `${uniqueDays}/7`;
    if (timerEl) timerEl.textContent = `${reportCountdown}/7`;
    if (cashflowEl) {
      cashflowEl.textContent = content.net_cash_flow !== undefined ? (content.net_cash_flow >= 0 ? '+' : '') + content.net_cash_flow : '—';
      cashflowEl.style.color = content.net_cash_flow >= 0 ? 'var(--success)' : 'var(--danger)';
    }
    if (goalsEl) goalsEl.textContent = content.goals_set > 0 ? `${content.goals_hit}/${content.goals_set}` : '—';

    const readinessEl = document.getElementById('report-readiness');
    if (readinessEl) {
      readinessEl.textContent = readinessMessage;
      readinessEl.style.display = 'block';
      readinessEl.style.borderColor = reportReady ? 'rgba(34,197,94,0.3)' : 'rgba(236,72,153,0.3)';
      readinessEl.style.background = reportReady ? 'rgba(34,197,94,0.08)' : 'rgba(236,72,153,0.08)';
    }

    const emptyEl = document.getElementById('report-empty');
    if (emptyEl && narrativeEl) {
      if (!reportReady) {
        emptyEl.style.display = 'block';
        narrativeEl.style.display = 'none';
      } else {
        emptyEl.style.display = 'none';
        narrativeEl.style.display = 'block';
      }
    }

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
      .replace(/<a[^>]*>/g, '') // Remove opening anchor tags
      .replace(/<\/a>/g, '') // Remove closing anchor tags
      .replace(/<form[^>]*>/g, '') // Remove form tags
      .replace(/<\/form>/g, '')
      .trim();
    if (narrativeEl) narrativeEl.innerHTML = formatted.replace(/\n/g, '<br>');

    renderEngineBar('bar-financial', 'Financial', signalScores.Financial ?? 0, '#22c55e', 100);
    renderEngineBar('bar-mental', 'Mental', signalScores.Mental ?? 0, '#6c63ff', 100);
    renderEngineBar('bar-execution', 'Execution', signalScores.Execution ?? 0, '#ec4899', 100);
    renderEngineBar('bar-body', 'Body', signalScores.Body ?? 0, '#f59e0b', 100);
    renderEngineBar('bar-growth', 'Growth', signalScores.Growth ?? 0, '#06b6d4', 100);
    
    loadWeeklyComparison();
    
    console.log('loadReport completed successfully - END');

  } catch(e) {
    console.error('Report generation error:', e);
    hideLoader();
    showToast('Could not load report. Please try again.', 'error');
    if (narrativeEl) narrativeEl.textContent = 'Could not load report. Try again.';
  }
}

function switchReport(type) {
  // Update button styles for all types
  ['daily', 'weekly', 'monthly'].forEach(t => {
    const btn = document.getElementById(`rpt-btn-${t}`);
    if (!btn) return;
    
    const isActive = t === type;
    btn.style.border = isActive ? '2px solid var(--accent)' : '1px solid var(--border)';
    btn.style.background = isActive ? 'rgba(108,99,255,0.15)' : 'transparent';
    btn.style.color = isActive ? 'var(--text-primary)' : 'var(--text-secondary)';
  });

  // Load the correct report
  if (type === 'daily' && typeof loadDailyReport === 'function') {
    loadDailyReport();
  } else {
    loadReport(type);
  }
}


function calculateDaysUntilBirthday(dob) {
  const today = new Date();
  const currentYear = today.getFullYear();
  const nextBirthday = new Date(currentYear, dob.getMonth(), dob.getDate());
  
  if (nextBirthday < today) {
    nextBirthday.setFullYear(currentYear + 1);
  }
  
  const diffTime = nextBirthday - today;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
}

let currentReportId = null;

async function updateShareSettings() {
  // Just update UI state, actual save happens on button click
  const sharePublic = document.getElementById('share-public').checked;
  const linkContainer = document.getElementById('share-link-container');
  
  if (sharePublic) {
    linkContainer.style.display = 'block';
  } else {
    linkContainer.style.display = 'none';
  }
}

async function saveShareSettings() {
  if (!currentUser || !authToken) {
    showToast('Please log in first', 'error');
    return;
  }
  
  if (!currentReportId) {
    showToast('No report loaded. Generate a report first.', 'error');
    return;
  }
  
  const shareSettings = {
    share_with_public: document.getElementById('share-public').checked,
    share_with_circles: document.getElementById('share-circles').checked,
    share_anonymously: document.getElementById('share-anonymous').checked,
    custom_message: document.getElementById('share-message').value.trim(),
    share_theme: document.getElementById('share-theme').value
  };
  
  try {
    const res = await fetch(`${API}/api/v1/reports/${currentReportId}/share`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(shareSettings)
    });
    
    if (res.ok) {
      const data = await res.json();
      if (data.link_url) {
        document.getElementById('share-link').value = data.link_url;
        document.getElementById('share-link-container').style.display = 'block';
      }
      showToast('Sharing settings saved!', 'success');
    } else {
      showToast('Failed to save sharing settings', 'error');
    }
  } catch (e) {
    console.error('Error saving share settings:', e);
    showToast('Connection error. Try again.', 'error');
  }
}

async function copyShareLink() {
  const linkInput = document.getElementById('share-link');
  if (!linkInput || !linkInput.value) {
    showToast('No share link available', 'error');
    return;
  }
  
  try {
    await navigator.clipboard.writeText(linkInput.value);
    showToast('Link copied to clipboard!', 'success');
  } catch (e) {
    // Fallback for older browsers
    linkInput.select();
    document.execCommand('copy');
    showToast('Link copied to clipboard!', 'success');
  }
}

async function generateReport(e) {
    console.log('generateReport called');
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    try {
        console.log('Calling loadReport...');
        await loadReport();
        console.log('generateReport completed successfully');
    } catch (err) {
        console.error("Report generation error:", err);
        showToast('Could not load report. Please try again.', 'error');
    }
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

async function loadSubscriptionInfo() {
  if (!currentUser || !authToken) return;
  
  // Try cache first
  const cachedSubs = Cache.get(`subscriptions_${currentUser.id}`);
  if (cachedSubs) {
    renderSubscriptionData(cachedSubs);
  }
  
  try {
    // Load subscription info
    const subRes = await dedupedFetch(`${API}/api/v1/subscriptions/current`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (subRes.ok) {
      const subscriptions = await subRes.json();
      // Cache for 10 minutes
      Cache.set(`subscriptions_${currentUser.id}`, subscriptions, 10);
      renderSubscriptionData(subscriptions);
    }
    
    // Try cache for payments
    const cachedPayments = Cache.get(`payments_${currentUser.id}`);
    if (cachedPayments) {
      renderPaymentHistory(cachedPayments);
    }
    
    // Load payment history
    const payRes = await dedupedFetch(`${API}/api/v1/users/${currentUser.id}/payments`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (payRes.ok) {
      const payments = await payRes.json();
      // Cache for 10 minutes
      Cache.set(`payments_${currentUser.id}`, payments, 10);
      renderPaymentHistory(payments);
    }
  } catch(e) {
    console.error('Subscription info load error:', e);
  }
}

function renderSubscriptionData(subscriptions) {
  if (subscriptions && subscriptions.length > 0) {
    const sub = subscriptions[0];
    document.getElementById('sub-plan').textContent = sub.tier || 'Free';
    document.getElementById('sub-status').textContent = sub.status || 'Active';
    
    if (sub.expires_at) {
      const expires = new Date(sub.expires_at);
      document.getElementById('sub-expires').textContent = expires.toLocaleDateString('en-US', {day:'numeric', month:'short', year:'numeric'});
    }
    
    // Auto-renew checkbox
    const autoRenewCheckbox = document.getElementById('auto-renew');
    if (autoRenewCheckbox) {
      autoRenewCheckbox.checked = sub.auto_renew || false;
      autoRenewCheckbox.addEventListener('change', () => toggleAutoRenew(autoRenewCheckbox.checked, sub.id));
    }
  }
}

function renderPaymentHistory(payments) {
  const historyContainer = document.getElementById('payment-history');
  
  if (payments && payments.length > 0) {
    historyContainer.innerHTML = payments.map(payment => {
      const date = new Date(payment.created_at);
      const statusColor = payment.status === 'completed' ? 'var(--success)' : 
                        payment.status === 'pending' ? 'var(--warning)' : 'var(--error)';
      return `
        <div style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px;display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text-primary)">${payment.currency || 'USD'} ${payment.amount?.toLocaleString() || '0'}</div>
            <div style="font-size:11px;color:var(--text-muted)">${date.toLocaleDateString('en-US', {day:'numeric', month:'short', year:'numeric'})}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:12px;font-weight:600;color:${statusColor}">${payment.status || 'Unknown'}</div>
            <div style="font-size:10px;color:var(--text-muted)">${payment.provider || 'Unknown'}</div>
          </div>
        </div>
      `;
    }).join('');
  } else {
    historyContainer.innerHTML = '<div style="font-size:13px;color:var(--text-muted);text-align:center;padding:1rem">No payments yet</div>';
  }
}

async function toggleAutoRenew(enabled) {
  if (!currentUser || !authToken) return;
  
  try {
    // Get current subscription ID from subscription info
    const subPlan = document.getElementById('sub-plan')?.textContent;
    if (!subPlan || subPlan === 'Free') {
      showToast('Auto-renew not available for free plan', 'error');
      return;
    }
    
    // Get subscription ID from cache or fetch it
    const res = await fetch(`${API}/api/v1/subscriptions/current`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (!res.ok) {
      showToast('Failed to get subscription info', 'error');
      return;
    }
    
    const subData = await res.json();
    if (!subData.id || subData.id === 0) {
      showToast('No active subscription found', 'error');
      return;
    }
    
    // Update auto-renew setting
    const updateRes = await fetch(`${API}/api/v1/subscriptions/${subData.id}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ auto_renew: enabled })
    });
    
    if (updateRes.ok) {
      showToast(enabled ? 'Auto-renew enabled' : 'Auto-renew disabled', 'success');
      // Invalidate subscription cache
      Cache.set(`subscriptions_${currentUser.id}`, null, 0);
    } else {
      showToast('Failed to update auto-renew setting', 'error');
      // Revert checkbox
      document.getElementById('auto-renew').checked = !enabled;
    }
  } catch(e) {
    console.error('Auto-renew toggle error:', e);
    showToast('Connection error', 'error');
    document.getElementById('auto-renew').checked = !enabled;
  }
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
  document.getElementById('vek-credits').textContent = currentUser.vek_credit_balance != null ? currentUser.vek_credit_balance : '0';
  document.getElementById('referral-count').textContent = currentUser.referral_count != null ? currentUser.referral_count : '0';
  
  // Populate body metrics
  document.getElementById('profile-weight').value = currentUser.weight || '';
  document.getElementById('profile-height').value = currentUser.height || '';
  document.getElementById('profile-dob').value = currentUser.dob || '';
  document.getElementById('profile-gender').value = currentUser.gender || '';
  
  // Try cache first
  const cachedSnapshots = Cache.get(`snapshots_${currentUser.id}`);
  if (cachedSnapshots) {
    const streak = calculateStreak(cachedSnapshots);
    const latest = cachedSnapshots[0];
    document.getElementById('profile-streak').textContent = streak > 0 ? `🔥 ${streak}` : '0';
    document.getElementById('profile-score').textContent = latest?.vektra_score ? latest.vektra_score.toFixed(0) : '—';
    document.getElementById('profile-logs').textContent = cachedSnapshots.length;
  }
  
  try {
    const res = await dedupedFetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      const snapshots = await res.json();
      // Cache for 5 minutes
      Cache.set(`snapshots_${currentUser.id}`, snapshots, 5);
      
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
  
  // Load personalization settings
  loadPersonalizationSettings();
  
  // Load achievements count
  loadAchievementsCount();
  
  // Load financial health
  loadFinancialHealth();
  
  // Load subscription and payment info
  loadSubscriptionInfo();
  
  // Initialize monthly replay with current month
  const today = new Date();
  document.getElementById('replay-month').value = today.getMonth() + 1;
  
  // Populate year dropdown dynamically
  const yearSelect = document.getElementById('replay-year');
  const currentYear = today.getFullYear();
  yearSelect.innerHTML = '';
  for (let y = currentYear - 2; y <= currentYear + 1; y++) {
    const option = document.createElement('option');
    option.value = y;
    option.textContent = y;
    if (y === currentYear) option.selected = true;
    yearSelect.appendChild(option);
  }
  
  loadMonthlyReplay();
}

async function saveProfile() {
  if (!currentUser || !authToken) return;
  const northStar = document.getElementById('profile-northstar').value.trim();
  const weight = document.getElementById('profile-weight').value;
  const height = document.getElementById('profile-height').value;
  const gender = document.getElementById('profile-gender').value;
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
    const updateData = { 
      north_star: northStar, 
      preferred_feedback_tone: profileTone 
    };
    
    // Add body metrics if provided (DOB is locked, not editable)
    if (weight) updateData.weight = parseFloat(weight);
    if (height) updateData.height = parseFloat(height);
    if (gender) updateData.gender = gender;
    
    const res = await fetch(`${API}/api/v1/users/me`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData)
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
// Pass 'e' (the event object) directly into the function parameter
function copyReferral(e) {
  // Global variable window.event fallback wrapper 
  const currentEvent = e || window.event;
  const code = document.getElementById('referral-code').textContent;
  
  navigator.clipboard.writeText(code).then(() => {
    // Hardened element extraction sequence
    let btn = null;
    if (currentEvent) {
      btn = currentEvent.currentTarget || currentEvent.target;
    }
    
    // Safely execute visual rendering even if event extraction drops
    if (btn) {
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
    }
  });
}

function shareReferral(e) {
  // Global variable window.event fallback wrapper
  const currentEvent = e || window.event;
  const code = currentUser?.username?.toUpperCase() || 'VEXTRA';
  const baseUrl = `${window.location.origin}${window.location.pathname}`;
  const link = `${baseUrl}?ref=${encodeURIComponent(code)}`;
  
  const message = `I've been tracking my trajectory with VEXTRA — the AI-powered self-tracking app that gives you harsh truths about your progress.\n\nUse my referral code: ${code}\n\nVector = Magnitude × Direction 🔥`;
  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  
  let btn = null;
  if (currentEvent) {
    btn = currentEvent.currentTarget || currentEvent.target;
  }
  
  if (isMobile && navigator.share) {
    navigator.share({ 
      title: 'Join me on VEXTRA', 
      text: message,
      url: link 
    }).catch((err) => console.log('Share canceled or failed:', err));
  } else {
    const fullDesktopText = `${message}\nJoin directly here:\n${link}`;
    navigator.clipboard.writeText(fullDesktopText).then(() => {
      if (btn) {
        const original = btn.textContent;
        btn.textContent = '✓ Copied to clipboard!';
        const originalBg = btn.style.background;
        btn.style.background = 'var(--success)';
        
        setTimeout(() => {
          btn.textContent = original;
          btn.style.background = originalBg || 'linear-gradient(135deg,#6c63ff,#ec4899)';
        }, 2500);
      }
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

  // Don't restore if this is clearly a different user's draft
  if (draft.userId && currentUser && draft.userId !== currentUser.id) {
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
      renderAnalyticsStats(data.data);
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

function renderAnalyticsStats(data) {
  if (!data || data.length === 0) {
    document.getElementById('stat-avg-score').textContent = '—';
    document.getElementById('stat-best-day').textContent = '—';
    document.getElementById('stat-total-income').textContent = '—';
    document.getElementById('stat-streak').textContent = '—';
    return;
  }

  // Calculate average VEKTRA score
  const scores = data.map(d => d.vektra_score).filter(v => v !== null && v !== undefined);
  const avgScore = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : '—';
  document.getElementById('stat-avg-score').textContent = avgScore;

  // Find best day
  const bestDay = scores.length > 0 ? Math.max(...scores).toFixed(1) : '—';
  document.getElementById('stat-best-day').textContent = bestDay;

  // Calculate total income
  const income = data.map(d => d.daily_income).filter(v => v !== null && v !== undefined);
  const totalIncome = income.length > 0 ? (income.reduce((a, b) => a + b, 0)).toLocaleString() : '—';
  document.getElementById('stat-total-income').textContent = totalIncome;

  // Current streak (from profile data)
  const streakEl = document.getElementById('profile-streak');
  const streakText = streakEl ? streakEl.textContent : '—';
  const streakNum = streakText.replace(/[^\d]/g, '');
  document.getElementById('stat-streak').textContent = streakNum || '—';
}

function showNoDataMessage() {
  const charts = ['chart-vektra', 'chart-networth', 'chart-sleep', 'chart-mood', 'chart-focus'];
  charts.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:13px">No data for this period</div>';
    }
  });
  
  // Also reset stats
  document.getElementById('stat-avg-score').textContent = '—';
  document.getElementById('stat-best-day').textContent = '—';
  document.getElementById('stat-total-income').textContent = '—';
  document.getElementById('stat-streak').textContent = '—';
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

async function openTrajectoryHistory() {
  goTo('trajectory-history');
  loadHistory();
}

async function loadHistory() {
  if (!currentUser || !authToken) return;
  
  const listEl = document.getElementById('trajectory-history-list');
  if (listEl) {
    listEl.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:14px;padding:3rem 0">Loading reports...</div>';
  }
  
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/reports`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      allReports = await res.json();
      filterHistory(currentHistoryFilter);
    } else {
      console.error('Failed to load reports');
      if (listEl) {
        listEl.innerHTML = '<div style="text-align:center;color:var(--danger);font-size:14px;padding:3rem 0">Failed to load reports.</div>';
      }
    }
  } catch (e) {
    console.error('Error loading reports:', e);
    if (listEl) {
      listEl.innerHTML = '<div style="text-align:center;color:var(--danger);font-size:14px;padding:3rem 0">Could not connect to server.</div>';
    }
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
  const listEl = document.getElementById('trajectory-history-list');
  const emptyEl = document.getElementById('trajectory-history-empty');
  
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
      displayReportData(report);
    } else {
      showToast('Failed to load report', 'error');
    }
  } catch (e) {
    showToast('Could not connect to server', 'error');
  }
}

function displayReportData(report) {
  // Update report UI with the loaded report data
  const narrativeEl = document.getElementById('report-narrative');
  const scoreEl = document.getElementById('report-score');
  const readinessEl = document.getElementById('report-readiness');
  
  if (narrativeEl) narrativeEl.textContent = report.summary_text || 'No narrative available';
  if (scoreEl) scoreEl.textContent = report.vektra_score ? Math.round(report.vektra_score) : '—';
  if (readinessEl) {
    if (report.vektra_score >= 80) {
      readinessEl.textContent = 'Ready for major moves';
      readinessEl.style.color = 'var(--success)';
    } else if (report.vektra_score >= 60) {
      readinessEl.textContent = 'Building momentum';
      readinessEl.style.color = 'var(--accent)';
    } else {
      readinessEl.textContent = 'Focus on fundamentals';
      readinessEl.style.color = 'var(--danger)';
    }
  }
  
  // Update period label
  const periodEl = document.getElementById('report-period');
  if (periodEl) {
    const date = new Date(report.generated_at);
    periodEl.textContent = date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
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

// ── GOAL PREDICTION ENGINE ──
async function loadGoalPrediction() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/goals/prediction`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const prediction = await res.json();
      renderGoalPrediction(prediction);
    } else {
      console.error('Failed to load prediction');
      document.getElementById('prediction-content').textContent = 'Prediction unavailable';
    }
  } catch (e) {
    console.error('Error loading prediction:', e);
    document.getElementById('prediction-content').textContent = 'Could not load prediction';
  }
}

function renderGoalPrediction(prediction) {
  const container = document.getElementById('prediction-content');
  if (!container) return;
  
  if (!prediction.has_prediction) {
    const reason = prediction.reason || 'Insufficient data';
    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:12px; padding: 4px 0;">
        <div style="display:flex; align-items:center; gap:10px;">
          <div class="radar-dot" style="width:10px; height:10px; border-radius:50%; background:var(--accent); animation: pulse 1.5s infinite;"></div>
          <span style="font-size:13px; font-weight:600; color:var(--text-secondary)">Calibrating Goal Trajectory Engine...</span>
        </div>
        <p style="font-size:12px; color:var(--text-muted); margin:0;">${reason}. VEKTRA requires at least 5 consecutive logs to accurately project your completion velocity.</p>
        ${prediction.current_score ? `<div style="font-size:11px; color:var(--text-muted); opacity:0.8;">Current base score: ${prediction.current_score.toFixed(1)}/100</div>` : ''}
      </div>
    `;
    return;
  }
  
  const confidenceColors = {
    'high': 'var(--success)',
    'medium': 'var(--accent)',
    'low': 'var(--text-muted)'
  };
  const confidenceColor = confidenceColors[prediction.confidence] || 'var(--text-muted)';
  
  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:14px;font-weight:600;color:var(--text-primary)">Time to reach target</span>
        <span style="font-size:16px;font-weight:700;color:var(--accent)">${prediction.prediction}</span>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:12px;color:var(--text-secondary)">Current score</span>
        <span style="font-size:12px;color:var(--text-primary)">${prediction.current_score.toFixed(1)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:12px;color:var(--text-secondary)">Weekly improvement</span>
        <span style="font-size:12px;color:var(--success)">+${prediction.weekly_improvement.toFixed(2)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px">
        <span style="font-size:11px;color:var(--text-muted)">Confidence</span>
        <span style="font-size:11px;color:${confidenceColor};font-weight:600">${prediction.confidence.toUpperCase()}</span>
      </div>
    </div>
  `;
}

// ── PERSONALIZATION ENGINE ──
let personalizationSettings = {
  targetScore: 80,
  minSleep: 7,
  targetFocus: 4,
  showScoreCard: true,
  showInsightCard: true,
  showComparisonCard: true
};

function loadPersonalizationSettings() {
  const saved = localStorage.getItem('vektra_personalization');
  if (saved) {
    try {
      personalizationSettings = JSON.parse(saved);
    } catch (e) {
      console.error('Failed to parse personalization settings:', e);
    }
  }
  
  // Apply settings to UI
  const targetScoreEl = document.getElementById('target-score');
  const minSleepEl = document.getElementById('min-sleep');
  const targetFocusEl = document.getElementById('target-focus');
  const showScoreCardEl = document.getElementById('show-score-card');
  const showInsightCardEl = document.getElementById('show-insight-card');
  const showComparisonCardEl = document.getElementById('show-comparison-card');
  
  if (targetScoreEl) targetScoreEl.value = personalizationSettings.targetScore;
  if (minSleepEl) minSleepEl.value = personalizationSettings.minSleep;
  if (targetFocusEl) targetFocusEl.value = personalizationSettings.targetFocus;
  if (showScoreCardEl) showScoreCardEl.checked = personalizationSettings.showScoreCard;
  if (showInsightCardEl) showInsightCardEl.checked = personalizationSettings.showInsightCard;
  if (showComparisonCardEl) showComparisonCardEl.checked = personalizationSettings.showComparisonCard;
  
  // Apply dashboard card visibility
  applyDashboardPreferences();
}

function savePersonalizationSettings() {
  const targetScoreEl = document.getElementById('target-score');
  const minSleepEl = document.getElementById('min-sleep');
  const targetFocusEl = document.getElementById('target-focus');
  const showScoreCardEl = document.getElementById('show-score-card');
  const showInsightCardEl = document.getElementById('show-insight-card');
  const showComparisonCardEl = document.getElementById('show-comparison-card');
  
  personalizationSettings = {
    targetScore: targetScoreEl ? parseInt(targetScoreEl.value) || 80 : 80,
    minSleep: minSleepEl ? parseFloat(minSleepEl.value) || 7 : 7,
    targetFocus: targetFocusEl ? parseFloat(targetFocusEl.value) || 4 : 4,
    showScoreCard: showScoreCardEl ? showScoreCardEl.checked : true,
    showInsightCard: showInsightCardEl ? showInsightCardEl.checked : true,
    showComparisonCard: showComparisonCardEl ? showComparisonCardEl.checked : true
  };
  
  localStorage.setItem('vektra_personalization', JSON.stringify(personalizationSettings));
  applyDashboardPreferences();
  showToast('Personalization settings saved', 'success');
}

function applyDashboardPreferences() {
  const scoreCard = document.getElementById('smart-score-card');
  const insightCard = document.getElementById('smart-insight-card');
  const comparisonCard = document.getElementById('weekly-comparison');
  
  if (scoreCard) scoreCard.style.display = personalizationSettings.showScoreCard ? 'block' : 'none';
  if (insightCard) insightCard.style.display = personalizationSettings.showInsightCard ? 'block' : 'none';
  if (comparisonCard) comparisonCard.style.display = personalizationSettings.showComparisonCard ? 'block' : 'none';
}

// Listen for personalization setting changes
document.addEventListener('DOMContentLoaded', () => {
  const personalizationInputs = ['target-score', 'min-sleep', 'target-focus', 'show-score-card', 'show-insight-card', 'show-comparison-card'];
  personalizationInputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', savePersonalizationSettings);
    }
  });
});

// ── SUBSCRIPTION SYSTEM ──
async function loadSubscriptionPlans() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/subscriptions/plans`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderSubscriptionPlans(data.plans);
    } else {
      console.error('Failed to load plans');
    }
  } catch (e) {
    console.error('Error loading plans:', e);
  }
}

async function loadCurrentSubscription() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/subscriptions/current`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const subscription = await res.json();
      renderCurrentSubscription(subscription);
    } else {
      console.error('Failed to load current subscription');
    }
  } catch (e) {
    console.error('Error loading current subscription:', e);
  }
}

function renderCurrentSubscription(subscription) {
  const nameEl = document.getElementById('current-plan-name');
  const statusEl = document.getElementById('current-plan-status');
  
  if (!nameEl || !statusEl) return;
  
  const planNames = {
    'free': 'Free Plan',
    'tier1': 'Pro Plan',
    'tier2': 'Premium Plan',
    'tier3': 'Enterprise Plan'
  };
  
  nameEl.textContent = planNames[subscription.plan] || subscription.plan;
  
  if (subscription.plan === 'free') {
    statusEl.textContent = 'Upgrade to unlock premium features';
  } else if (subscription.days_remaining !== null) {
    statusEl.textContent = `${subscription.days_remaining} days remaining`;
  } else {
    statusEl.textContent = 'Active';
  }
}

function renderSubscriptionPlans(plans) {
  const container = document.getElementById('plans-container');
  if (!container) return;
  
  container.innerHTML = plans.map(plan => {
    const isCurrentPlan = plan.id === 'free'; // Default to free as current
    
    return `
      <div style="background:var(--bg-card);border:1px solid ${isCurrentPlan ? 'var(--accent)' : 'var(--border)'};border-radius:var(--radius);padding:1.25rem;cursor:pointer;transition:border-color 0.2s ease" onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='${isCurrentPlan ? 'var(--accent)' : 'var(--border)'}'">
        <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
          <div>
            <div style="font-size:16px;font-weight:700;color:var(--text-primary)">${plan.name}</div>
            <div style="font-size:24px;font-weight:800;color:var(--accent)">${plan.price > 0 ? '$' + plan.price.toFixed(2) : 'Free'}</div>
            ${plan.duration_days ? `<div style="font-size:12px;color:var(--text-muted)">per ${plan.duration_days} days</div>` : ''}
          </div>
          ${isCurrentPlan ? '<div style="padding:4px 12px;background:rgba(108,99,255,0.2);border-radius:var(--radius-sm);font-size:11px;color:var(--accent);font-weight:600">CURRENT</div>' : ''}
        </div>
        <div style="display:flex;flex-direction:column;gap:6px">
          ${plan.features.map(feature => `
            <div style="font-size:12px;color:var(--text-secondary);display:flex;align-items:center;gap:6px">
              <span style="color:var(--success)">✓</span>
              ${feature}
            </div>
          `).join('')}
        </div>
        ${!isCurrentPlan ? `
          <button onclick="selectPlan('${plan.id}')" style="margin-top:16px;width:100%;padding:12px;background:linear-gradient(135deg,#6c63ff,#ec4899);border:none;border-radius:var(--radius-sm);color:white;font-size:14px;font-weight:600;cursor:pointer;font-family:var(--font)">Choose ${plan.name}</button>
        ` : ''}
      </div>
    `;
  }).join('');
}

function selectPlan(planId) {
  selectedPlanId = planId;
  
  // Show payment section
  const paymentSection = document.getElementById('payment-section');
  if (paymentSection) {
    paymentSection.style.display = 'block';
  }
  
  showToast(`Selected ${planId} plan. This is a preview of the payment flow.`, 'success');
}

const PAYMENT_PREVIEW_MODE = true;
let selectedPaymentMethod = null;
let selectedPlanId = null;

function selectPaymentMethod(method) {
  selectedPaymentMethod = method;
  
  // Update button styles
  const stripeBtn = document.getElementById('pay-stripe-btn');
  const paystackBtn = document.getElementById('pay-paystack-btn');
  const mpesaBtn = document.getElementById('pay-mpesa-btn');
  const stripeForm = document.getElementById('stripe-form');
  const paystackForm = document.getElementById('paystack-form');
  const mpesaForm = document.getElementById('mpesa-form');
  
  if (method === 'stripe') {
    stripeBtn.style.background = 'rgba(108,99,255,0.2)';
    stripeBtn.style.borderColor = 'var(--accent)';
    paystackBtn.style.background = 'transparent';
    paystackBtn.style.borderColor = 'var(--border)';
    mpesaBtn.style.background = 'transparent';
    mpesaBtn.style.borderColor = 'var(--border)';
    stripeForm.style.display = 'block';
    paystackForm.style.display = 'none';
    mpesaForm.style.display = 'none';
  } else {
    // handle paystack or mpesa selection
    stripeBtn.style.background = 'transparent';
    stripeBtn.style.borderColor = 'var(--border)';
    if (method === 'mpesa') {
      mpesaBtn.style.background = 'rgba(108,99,255,0.2)';
      mpesaBtn.style.borderColor = 'var(--accent)';
      paystackBtn.style.background = 'transparent';
      paystackBtn.style.borderColor = 'var(--border)';
      mpesaForm.style.display = 'block';
      stripeForm.style.display = 'none';
      paystackForm.style.display = 'none';
    } else if (method === 'paystack') {
      paystackBtn.style.background = 'rgba(108,99,255,0.2)';
      paystackBtn.style.borderColor = 'var(--accent)';
      mpesaBtn.style.background = 'transparent';
      mpesaBtn.style.borderColor = 'var(--border)';
      paystackForm.style.display = 'block';
      stripeForm.style.display = 'none';
      mpesaForm.style.display = 'none';
    }
  }
}

async function processPayment() {
  if (!selectedPaymentMethod || !selectedPlanId) {
    showToast('Please select a plan and payment method', 'error');
    return;
  }
  
  const payButton = document.getElementById('pay-button');
  payButton.textContent = 'Processing...';
  payButton.disabled = true;
  
  try {
    if (PAYMENT_PREVIEW_MODE) {
      showToast('Payment preview complete. No live charges are processed in this demo mode.', 'info');
      return;
    }

    if (selectedPaymentMethod === 'stripe') {
      // Stripe payment processing
      const cardNumber = document.getElementById('stripe-card').value;
      const expiry = document.getElementById('stripe-expiry').value;
      const cvc = document.getElementById('stripe-cvc').value;
      
      if (!cardNumber || !expiry || !cvc) {
        throw new Error('Please fill in all card details');
      }
      
      // Call backend Stripe payment endpoint
      const res = await fetch(`${API}/api/v1/users/${currentUser.id}/payments/stripe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          customer_id: null, // Will be created by backend
          price_id: selectedPlanId // Map plan ID to Stripe price ID
        })
      });
      
      if (!res.ok) throw new Error('Payment failed');
      
    } else if (selectedPaymentMethod === 'mpesa') {
      // M-Pesa payment processing
      const phone = document.getElementById('mpesa-phone').value;

      
      if (!phone) {
        throw new Error('Please enter phone number');
      }
      
      // Call backend M-Pesa payment endpoint
      const planPrices = {
        'tier1': 9.99,
        'tier2': 19.99,
        'tier3': 49.99
      };
      const amount = planPrices[selectedPlanId] || 9.99;
      
      const res = await fetch(`${API}/api/v1/users/${currentUser.id}/payments/mpesa`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          phone_number: phone,
          amount: amount
        })
      });
      
      if (!res.ok) throw new Error('Payment failed');
    } else if (selectedPaymentMethod === 'paystack') {
      // Paystack payment processing
      const email = document.getElementById('paystack-email').value;
      if (!email) throw new Error('Please enter an email address for Paystack');

      const planPrices = {
        'tier1': 9.99,
        'tier2': 19.99,
        'tier3': 49.99
      };
      const amount = planPrices[selectedPlanId] || 9.99;

      const res = await fetch(`${API}/api/v1/users/${currentUser.id}/payments/paystack`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: email,
          amount: amount,
          currency: 'KES'
        })
      });

      if (!res.ok) throw new Error('Payment failed');
    }
    
    showToast('Payment successful! Subscription activated.', 'success');
    
    // Create subscription
    await fetch(`${API}/api/v1/subscriptions/create`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        provider: selectedPaymentMethod,
        plan: selectedPlanId,
        duration_days: 30,
        amount_paid: selectedPlanId === 'tier1' ? 9.99 : selectedPlanId === 'tier2' ? 19.99 : 49.99,
        currency: 'USD'
      })
    });
    
    // Reload subscription data
    await loadCurrentSubscription();
    
    // Hide payment section
    document.getElementById('payment-section').style.display = 'none';
    
    // Reset selection
    selectedPaymentMethod = null;
    selectedPlanId = null;
    
  } catch (e) {
    console.error('Payment error:', e);
    showToast(e.message || 'Payment failed. Please try again.', 'error');
  } finally {
    payButton.textContent = PAYMENT_PREVIEW_MODE ? 'Preview payment' : 'Pay Now';
    payButton.disabled = false;
  }
}

// ── ACHIEVEMENT SYSTEM ──
async function loadAchievementsCount() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/achievements`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const achievements = await res.json();
      const countEl = document.getElementById('achievement-count');
      if (countEl) {
        const completedCount = achievements.filter(a => a.completed).length;
        countEl.textContent = `${completedCount}/${achievements.length} Unlocked`;
      }
    }
  } catch (e) {
    console.error('Error loading achievements count:', e);
  }
}

async function loadAchievements() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/achievements/available`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderAchievements(data.achievements);
    } else {
      console.error('Failed to load achievements');
    }
  } catch (e) {
    console.error('Error loading achievements:', e);
  }
  
  // Load streak calendar data
  loadStreakCalendar();
}

async function loadStreakCalendar() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/achievements/streak-calendar?days=366`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderStreakCalendar(data);
    } else {
      console.error('Failed to load streak calendar');
    }
  } catch (e) {
    console.error('Error loading streak calendar:', e);
  }
}

function renderStreakCalendar(data) {
  const container = document.getElementById('streak-calendar');
  const currentStreakEl = document.getElementById('current-streak');
  const longestStreakEl = document.getElementById('longest-streak');
  const totalLoggedEl = document.getElementById('total-logged');
  
  if (!container) return;
  
  // Update stats
  if (currentStreakEl) currentStreakEl.textContent = data.current_streak;
  if (longestStreakEl) longestStreakEl.textContent = data.longest_streak;
  if (totalLoggedEl) totalLoggedEl.textContent = data.total_logged;
  
  // Render calendar grid (GitHub-style)
  const calendarData = data.calendar_data;
  const weeks = [];
  
  // Group by week (7 days)
  for (let i = 0; i < calendarData.length; i += 7) {
    weeks.push(calendarData.slice(i, i + 7));
  }
  
  // Get color based on score
  const getColor = (score) => {
    if (score === 0) return 'var(--bg-secondary)';
    if (score < 50) return '#4ade80';
    if (score < 70) return '#22c55e';
    if (score < 90) return '#16a34a';
    return '#15803d';
  };
  
  container.innerHTML = weeks.map(week => {
    return week.map(day => {
      const color = getColor(day.score);
      const opacity = day.logged ? '1' : '0.3';
      return `<div style="width:10px;height:10px;background:${color};border-radius:2px;opacity:${opacity}" title="${day.date}: ${day.score}"></div>`;
    }).join('');
  }).join('');
}

function renderAchievements(achievements) {
  const container = document.getElementById('achievements-grid');
  const totalEl = document.getElementById('total-achievements');
  const availableEl = document.getElementById('total-available');
  
  if (!container) return;
  
  const completed = achievements.filter(a => a.completed).length;
  
  if (totalEl) totalEl.textContent = completed;
  if (availableEl) availableEl.textContent = achievements.length;
  
  const rarityColors = {
    'common': '#a0aec0',
    'rare': '#6c63ff',
    'epic': '#ec4899',
    'legendary': '#f59e0b'
  };
  
  container.innerHTML = achievements.map(achievement => {
    const rarityColor = rarityColors[achievement.rarity] || '#a0aec0';
    const opacity = achievement.completed ? '1' : '0.4';
    
    return `
      <div style="background:var(--bg-card);border:1px solid ${achievement.completed ? 'var(--accent)' : 'var(--border)'};border-radius:var(--radius);padding:1rem;opacity:${opacity};transition:opacity 0.2s ease">
        <div style="display:flex;align-items:center;gap:12px">
          <div style="font-size:32px">${achievement.icon}</div>
          <div style="flex:1">
            <div style="font-size:14px;font-weight:600;color:var(--text-primary)">${achievement.title}</div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:2px">${achievement.description}</div>
            <div style="font-size:10px;color:${rarityColor};text-transform:uppercase;margin-top:4px;font-weight:600">${achievement.rarity}</div>
          </div>
          ${achievement.completed ? '<div style="font-size:20px">✓</div>' : '<div style="font-size:20px;color:var(--text-muted)">🔒</div>'}
        </div>
      </div>
    `;
  }).join('');
}

async function checkNewAchievements(snapshot) {
  // Trigger achievement check on backend
  try {
    const res = await fetch(`${API}/api/v1/achievements/check`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ snapshot_id: snapshot.id })
    });
    
    if (res.ok) {
      const data = await res.json();
      if (data.new_achievements && data.new_achievements.length > 0) {
        // Show achievement unlock notifications
        data.new_achievements.forEach(achievement => {
          showToast(`🏆 Achievement Unlocked: ${achievement.title}!`, 'success');
        });
        
        // Update achievement count
        loadAchievementsCount();
      }
    }
  } catch (e) {
    console.error('Error checking achievements:', e);
  }
}

async function exportData(format) {
  if (!currentUser || !authToken) {
    showToast('Please log in to export data', 'error');
    return;
  }
  
  try {
    showToast(`Preparing your ${format.toUpperCase()} export...`, 'info');
    
    const res = await fetch(`${API}/api/v1/export/${format}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vektra_export_${currentUser.username}_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast(`Data exported as ${format.toUpperCase()}`, 'success');
    } else {
      showToast('Failed to export data from server', 'error');
    }
  } catch (e) {
    console.error('Error exporting data:', e);
    showToast('Export failed. Please try again.', 'error');
  }
}

async function loadFinancialHealth() {
  if (!currentUser || !authToken) return;
  
  try {
    const res = await fetch(`${API}/api/v1/achievements/financial-health`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderFinancialHealth(data);
    } else {
      console.error('Failed to load financial health');
    }
  } catch (e) {
    console.error('Error loading financial health:', e);
  }
}

function renderFinancialHealth(data) {
  const container = document.getElementById('financial-health-content');
  if (!container) return;
  
  if (!data.has_data) {
    container.innerHTML = `<div style="color:var(--text-muted)">${data.reason}</div>`;
    return;
  }
  
  const healthColor = data.financial_health_score >= 70 ? '#22c55e' : data.financial_health_score >= 50 ? '#f59e0b' : '#ef4444';
  const incomeTrendIcon = data.income_trend > 0 ? '📈' : data.income_trend < 0 ? '📉' : '➡️';
  const expenseTrendIcon = data.expense_trend > 0 ? '📈' : data.expense_trend < 0 ? '📉' : '➡️';
  
  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div>
        <div style="font-size:24px;font-weight:700;color:${healthColor}">${data.financial_health_score}</div>
        <div style="font-size:11px;color:var(--text-muted)">Financial Health Score</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:16px;font-weight:600;color:var(--text-primary)">${data.savings_rate}%</div>
        <div style="font-size:11px;color:var(--text-muted)">Savings Rate</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px">
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Monthly Income</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">$${data.avg_monthly_income.toFixed(2)}</div>
      </div>
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Monthly Expenses</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">$${data.avg_monthly_expenses.toFixed(2)}</div>
      </div>
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Runway</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">${data.runway_months.toFixed(1)} months</div>
      </div>
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Net Worth</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">$${data.current_net_worth.toFixed(2)}</div>
      </div>
    </div>
    <div style="display:flex;gap:12px;margin-top:12px;font-size:12px;color:var(--text-muted)">
      <div>${incomeTrendIcon} Income: ${data.income_trend > 0 ? '+' : ''}${data.income_trend}%</div>
      <div>${expenseTrendIcon} Expenses: ${data.expense_trend > 0 ? '+' : ''}${data.expense_trend}%</div>
    </div>
  `;
}

async function loadMonthlyReplay() {
  if (!currentUser || !authToken) return;
  
  const month = document.getElementById('replay-month').value;
  const year = document.getElementById('replay-year').value;
  
  try {
    const res = await fetch(`${API}/api/v1/achievements/monthly-replay?year=${year}&month=${month}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      renderMonthlyReplay(data);
    } else {
      console.error('Failed to load monthly replay');
    }
  } catch (e) {
    console.error('Error loading monthly replay:', e);
  }
}

function renderMonthlyReplay(data) {
  const container = document.getElementById('monthly-replay-content');
  if (!container) return;
  
  if (!data.has_data) {
    container.innerHTML = `<div style="color:var(--text-muted)">${data.reason}</div>`;
    return;
  }
  
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const monthName = monthNames[data.month - 1];
  
  const improvementColor = data.improvement > 0 ? '#22c55e' : data.improvement < 0 ? '#ef4444' : '#a0aec0';
  const improvementIcon = data.improvement > 0 ? '📈' : data.improvement < 0 ? '📉' : '➡️';
  
  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div>
        <div style="font-size:16px;font-weight:600;color:var(--text-primary)">${monthName} ${data.year}</div>
        <div style="font-size:11px;color:var(--text-muted)">${data.days_logged} days logged</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:24px;font-weight:700;color:var(--accent)">${data.avg_vektra_score}</div>
        <div style="font-size:11px;color:var(--text-muted)">Avg VEKTRA Score</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px">
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Avg Mood</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">${data.avg_mood}/10</div>
      </div>
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Avg Energy</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">${data.avg_energy}/10</div>
      </div>
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Avg Focus</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">${data.avg_focus_hours}h</div>
      </div>
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Improvement</div>
        <div style="font-size:14px;font-weight:600;color:${improvementColor}">${improvementIcon} ${data.improvement > 0 ? '+' : ''}${data.improvement}</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px">
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Total Income</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">$${data.total_income.toFixed(2)}</div>
      </div>
      <div style="background:var(--bg-secondary);padding:8px;border-radius:var(--radius-sm)">
        <div style="font-size:11px;color:var(--text-muted)">Total Expenses</div>
        <div style="font-size:14px;font-weight:600;color:var(--text-primary)">$${data.total_expenses.toFixed(2)}</div>
      </div>
    </div>
    <div style="margin-top:12px;padding:8px;background:var(--bg-secondary);border-radius:var(--radius-sm)">
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px">Best Day</div>
      <div style="font-size:13px;color:var(--text-primary)">${data.best_day.date}: ${data.best_day.vektra_score} (Mood: ${data.best_day.mood_score})</div>
    </div>
    ${(data?.insights || []).length > 0 ? `
    <div style="margin-top:12px">
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px">Key Insights</div>
      ${data.insights.map(insight => `<div style="font-size:13px;color:var(--text-primary);margin-bottom:4px">• ${insight}</div>`).join('')}
    </div>
    ` : ''}
  `;
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

  // Add share button to reveal screen
  const btn = document.querySelector('#score-reveal .btn-primary');
  if (btn) {
    const shareBtn = document.createElement('button');
    shareBtn.className = 'btn-secondary';
    shareBtn.style.cssText = 'margin-top:12px;max-width:280px';
    shareBtn.textContent = `Share my score 🔥`;
    shareBtn.onclick = () => {
      const message = `Just logged my day on VEKTRA and scored ${score}/100! 🔥\n\nKnow your trajectory:\nhttps://vektraapp.online/app/\n\nVector = Magnitude × Direction`;
      if (navigator.share) {
        navigator.share({ title: 'My VEKTRA Score', text: message });
      } else {
        navigator.clipboard.writeText(message).then(() => {
          showToast('Score copied to clipboard! Share it anywhere 🔥', 'success');
        });
      }
    };
    btn.parentNode.insertBefore(shareBtn, btn.nextSibling);
  }

  // Auto-go to dashboard after 5 seconds
  setTimeout(() => {
    goTo('dashboard');
    loadDashboard();
  }, 5000);
}

// ── Settings ──
function openSettings() {
  console.log("Initializing account configuration canvas...");
  
  // 1. Transition the view section wrapper cleanly
  goTo('settings');
  
  // 2. Defensive check to prevent null property selection crashes
  if (currentUser) {
    const emailInput = document.getElementById('settings-email');
    const reminderInput = document.getElementById('settings-reminder');

    if (emailInput) {
      emailInput.value = currentUser.email || '';
    } else {
      console.warn("UI Guardrail: Input field 'settings-email' is missing from the HTML template layout.");
    }

    if (reminderInput) {
      reminderInput.value = currentUser.reminder_time || '20:00';
    }
  }
}

// Ensure the module boundary bridge stays intact
window.openSettings = openSettings;

async function updateEmail() {
  const email = document.getElementById('settings-email').value.trim();
  const successEl = document.getElementById('settings-email-success');
  successEl.style.display = 'none';

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showToast('Please enter a valid email', 'error');
    return;
  }

  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    if (res.ok) {
      currentUser = await res.json();
      successEl.style.display = 'block';
      setTimeout(() => successEl.style.display = 'none', 3000);
      showToast('Email updated successfully', 'success');
    }
  } catch(e) {
    showToast('Could not update email', 'error');
  }
}

async function updatePassword() {
  const current = document.getElementById('settings-current-password').value;
  const newPass = document.getElementById('settings-new-password').value;
  const confirm = document.getElementById('settings-confirm-password').value;
  const errEl = document.getElementById('settings-password-error');
  const successEl = document.getElementById('settings-password-success');

  errEl.style.display = 'none';
  successEl.style.display = 'none';

  if (!current || !newPass || !confirm) {
    errEl.textContent = 'Please fill in all password fields.';
    errEl.style.display = 'block';
    return;
  }
  if (newPass.length < 8) {
    errEl.textContent = 'New password must be at least 8 characters.';
    errEl.style.display = 'block';
    return;
  }
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(newPass)) {
    errEl.textContent = 'New password must contain at least one symbol.';
    errEl.style.display = 'block';
    return;
  }
  if (newPass !== confirm) {
    errEl.textContent = 'New passwords do not match.';
    errEl.style.display = 'block';
    return;
  }

  try {
    const res = await fetch(`${API}/api/v1/users/me/change-password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        current_password: current,
        new_password: newPass
      })
    });

    if (res.ok) {
      successEl.style.display = 'block';
      showToast('Password changed successfully', 'success');
      document.getElementById('settings-current-password').value = '';
      document.getElementById('settings-new-password').value = '';
      document.getElementById('settings-confirm-password').value = '';
      setTimeout(() => successEl.style.display = 'none', 3000);
    } else {
      const data = await res.json();
      errEl.textContent = data.detail || 'Incorrect current password.';
      errEl.style.display = 'block';
    }
  } catch(e) {
    errEl.textContent = 'Could not connect to server.';
    errEl.style.display = 'block';
  }
}

async function updateReminder() {
  const time = document.getElementById('settings-reminder').value;
  const successEl = document.getElementById('settings-reminder-success');
  successEl.style.display = 'none';

  try {
    const res = await fetch(`${API}/api/v1/users/me`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ reminder_time: time })
    });
    if (res.ok) {
      currentUser = await res.json();
      successEl.style.display = 'block';
      setTimeout(() => successEl.style.display = 'none', 3000);
      showToast('Reminder time saved', 'success');
    }
  } catch(e) {
    showToast('Could not save reminder', 'error');
  }
}

function toggleDarkMode() {
  const checkbox = document.getElementById('settings-darkmode');
  const toggle = document.getElementById('darkmode-toggle');
  const isDark = checkbox.checked;
  
  // Update toggle visual
  toggle.style.transform = isDark ? 'translateX(20px)' : 'translateX(0)';
  
  // Save preference
  localStorage.setItem('vektra_darkmode', isDark);
  
  // Apply theme (simplified - in production would update CSS variables)
  if (isDark) {
    document.documentElement.style.setProperty('--bg-primary', '#0a0a0f');
    document.documentElement.style.setProperty('--bg-secondary', '#12121a');
    document.documentElement.style.setProperty('--bg-card', '#1a1a2e');
  } else {
    document.documentElement.style.setProperty('--bg-primary', '#ffffff');
    document.documentElement.style.setProperty('--bg-secondary', '#f5f5f7');
    document.documentElement.style.setProperty('--bg-card', '#ffffff');
  }
  
  showToast(isDark ? 'Dark mode enabled' : 'Light mode enabled', 'success');
}

function clearCache() {
  if (confirm('Clear all cached data? This will make the app load slower until data is cached again.')) {
    Cache.clear();
    localStorage.removeItem('vektra_token');
    localStorage.removeItem('vektra_darkmode');
    showToast('Cache cleared successfully', 'success');
  }
}

function confirmDeleteAccount() {
  if (confirm('Are you absolutely sure? This cannot be undone. All your data will be permanently deleted.')) {
    showToast('Account deletion coming soon. Contact support.', 'warning');
  }
}

window.confirmDeleteAccount = confirmDeleteAccount;
window.toggleDarkMode = toggleDarkMode;
window.clearCache = clearCache;
window.showNotifications = showNotifications;
window.clearNotifications = clearNotifications;
window.showError = showError;
window.showEmptyState = showEmptyState;

// This function handles the actual data fetching and UI updating
async function fetchHarshTruths() {
  showLoader('Consulting the Vector Oracle...');
  
  try {
    const res = await fetch(`${API}/api/v1/harsh-truths`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (!res.ok) throw new Error('Failed to get truths');
    const data = await res.json();
    
    // Fixed: Added quotes around 'truth-output' so JavaScript reads it as a string ID
    const output = document.getElementById('truth-output');
    
    if (output) {
      output.textContent = data.truth;
      output.style.display = 'block';
    } else {
      alert(data.truth);
    }
  } catch(e) {
    showToast('Could not fetch harsh truths. Check your configuration.', 'error');
  } finally {
    hideLoader();
  }
}

function generateAnalysis() {
    alert("AI analysis is temporarily unavailable.");
    generateReport(); // optional
}

window.generateReport = generateReport;
window.generateAnalysis = generateAnalysis; // if you still use it
window.openDailyLog = openDailyLog;
window.openWeeklyQuestions = openWeeklyQuestions;
window.openMonthlyQuestions = openMonthlyQuestions;
window.submitWeeklyQuestions = submitWeeklyQuestions;
window.submitMonthlyQuestions = submitMonthlyQuestions;
window.submitLog = submitLog;
window.logout = logout;
window.openProfile = openProfile;
window.saveProfile = saveProfile;
window.copyReferral = copyReferral;
window.shareReferral = shareReferral;
window.loadSubscriptionInfo = loadSubscriptionInfo;
window.toggleAutoRenew = toggleAutoRenew;
window.showForgotPassword = showForgotPassword;
window.requestPasswordReset = requestPasswordReset;
window.confirmPasswordReset = confirmPasswordReset;
window.resendVerificationEmail = resendVerificationEmail;
window.verifyEmailWithToken = verifyEmailWithToken;
window.switchReport = switchReport;
window.updateShareSettings = updateShareSettings;
window.saveShareSettings = saveShareSettings;
window.copyShareLink = copyShareLink;

// Expose functions to the window so HTML 'onclick' and 'oninput' can find them
window.updateSlider = updateSlider;
window.setGoalHit = setGoalHit;
window.quickSetMood = quickSetMood;
window.quickSetSleep = quickSetSleep;
window.quickSetFocus = quickSetFocus;
async function loadSilentKillers() {
  const container = document.getElementById('silent-killers-container');
  if (!container) return;
  container.innerHTML = '';
  
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/insights/silent-killers`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (!res.ok) return;
    const { insights } = await res.json();
    
    if (insights.length > 0) {
      container.innerHTML = insights.map(i => `
        <div style="font-size:12px;padding:8px;background:rgba(239,68,68,0.1);border-left:3px solid #ef4444;color:#fca5a5;border-radius:4px">
          ${i.text}
        </div>
      `).join('');
    }
  } catch (e) {
    console.error('Failed to load silent killers', e);
  }
}

// ── Log History ──
async function openHistory() {
  goTo('history');
  document.getElementById('history-list').innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:14px;padding:3rem 0">Loading logs...</div>';
  document.getElementById('history-load-more').style.display = 'none';
  historyOffset = 0;

  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots?limit=${historyLimit}&offset=${historyOffset}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (!res.ok) return;
    const snapshots = await res.json();

    if (snapshots.length === 0) {
      document.getElementById('history-list').innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:14px;padding:3rem 0">No logs yet. Start logging daily! 🔥</div>';
      return;
    }

    document.getElementById('history-list').innerHTML = snapshots.map(snap => getSnapshotHTML(snap)).join('');

    if (snapshots.length === historyLimit) {
      document.getElementById('history-load-more').style.display = 'block';
    } else {
      document.getElementById('history-load-more').style.display = 'none';
    }

  } catch(e) {
    document.getElementById('history-list').innerHTML = '<div style="text-align:center;color:var(--danger);font-size:14px;padding:3rem 0">Could not load logs.</div>';
  }
}

function getSnapshotHTML(snap) {
  const date = new Date(snap.timestamp);
  const dateStr = date.toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'});
  const timeStr = date.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
  const score = snap.vektra_score;
  const scoreColor = score >= 70 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';
  const trajectory = score >= 70 ? '🔥' : score >= 50 ? '📈' : '📉';

  return `
    <div onclick="openLogDetail(this)" data-snap='${JSON.stringify(snap).replace(/'/g, "&#39;")}' 
         style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1rem;cursor:pointer;display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-weight:600;font-size:14px">${dateStr}</div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:2px">${timeStr}</div>
        <div style="display:flex;gap:12px;margin-top:6px;font-size:12px;color:var(--text-muted)">
          ${snap.mood_score ? `Mood ${snap.mood_score}/10` : ''}
          ${snap.sleep_hours ? `Sleep ${snap.sleep_hours}h` : ''}
          ${snap.daily_income ? `Income ${snap.daily_income}` : ''}
        </div>
      </div>
      <div style="text-align:right">
        <div style="font-size:28px;font-weight:800;color:${scoreColor}">${score ? score.toFixed(0) : '—'}</div>
        <div style="font-size:11px;color:var(--text-muted)">${trajectory}</div>
      </div>
    </div>
  `;
}

function openLogDetail(el) {
  const snap = JSON.parse(el.getAttribute('data-snap'));
  goTo('log-detail');

  const date = new Date(snap.timestamp);
  document.getElementById('detail-date').textContent = date.toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric', year:'numeric'});
  document.getElementById('detail-score').textContent = snap.vektra_score ? snap.vektra_score.toFixed(0) : '—';

  const sections = [
    {
      title: 'Mental & Emotional',
      color: '#7F77DD',
      fields: [
        {label: 'Mood', val: snap.mood_score ? `${snap.mood_score}/10` : null},
        {label: 'Energy', val: snap.energy_level ? `${snap.energy_level}/10` : null},
        {label: 'Focus Level', val: snap.focus_level ? `${snap.focus_level}/10` : null},
        {label: 'Social Battery', val: snap.social_battery ? `${snap.social_battery}/10` : null},
        {label: 'Health Battery', val: snap.health_battery ? `${snap.health_battery}/10` : null},
        {label: 'Uncomfortable Moments', val: snap.uncomfortable_moments},
      ]
    },
    {
      title: 'Finance',
      color: '#BA7517',
      fields: [
        {label: 'Income', val: snap.daily_income},
        {label: 'Expenses', val: snap.expenses},
        {label: 'Saved/Invested', val: snap.savings_investments},
        {label: 'Emergency', val: snap.any_emergency},
      ]
    },
    {
      title: 'Goals & Decisions',
      color: '#378ADD',
      fields: [
        {label: "Tomorrow's Goal", val: snap.tomorrow_goal},
        {label: 'Hit Yesterday Goal', val: snap.target_hit_bool !== null ? (snap.target_hit_bool ? '✓ Yes' : '✗ No') : null},
        {label: 'Best Decision', val: snap.best_decision},
        {label: 'Worst Decision', val: snap.worst_decision},
        {label: 'What I Avoided', val: snap.what_i_avoided},
      ]
    },
    {
      title: 'Body & Health',
      color: '#1D9E75',
      fields: [
        {label: 'Sleep Hours', val: snap.sleep_hours ? `${snap.sleep_hours} hours` : null},
        {label: 'Screen Time', val: snap.screen_time ? `${snap.screen_time} hours` : null},
        {label: 'Diet', val: snap.diet_taken},
      ]
    },
    {
      title: 'Growth & Learning',
      color: '#D85A30',
      fields: [
        {label: 'Skills Learned', val: snap.skills_learned},
        {label: 'New Ideas', val: snap.new_ideas},
        {label: 'Gratitude', val: snap.gratitude_line},
        {label: 'Funny Line', val: snap.funny_line},
      ]
    },
    {
      title: 'Computed Metrics',
      color: '#639922',
      fields: [
        {label: 'Burn Rate', val: snap.burn_rate},
        {label: 'Survival Runway', val: snap.survival_runway ? `${snap.survival_runway} days` : null},
        {label: 'Leverage Score', val: snap.leverage_score ? snap.leverage_score.toFixed(2) : null},
        {label: 'Procrastination Delta', val: snap.procrastination_delta},
      ]
    },
  ];

  document.getElementById('detail-content').innerHTML = sections.map(section => {
    const visibleFields = section.fields.filter(f => f.val !== null && f.val !== undefined && f.val !== '');
    if (visibleFields.length === 0) return '';

    return `
      <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1rem">
        <div style="font-size:11px;color:${section.color};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:.75rem">${section.title}</div>
        ${visibleFields.map(f => `
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid var(--border);font-size:13px">
            <span style="color:var(--text-secondary)">${f.label}</span>
            <span style="font-weight:500;max-width:60%;text-align:right">${f.val}</span>
          </div>
        `).join('')}
      </div>
    `;
  }).join('');
}

window.openLogDetail = openLogDetail;
window.openHistory = openHistory;

let historyOffset = 0;
const historyLimit = 20;

async function loadMoreHistory() {
    const btn = document.getElementById('history-load-more');
    btn.disabled = true;
    btn.textContent = 'Loading...';
    
    historyOffset += historyLimit;
    try {
        const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots?limit=${historyLimit}&offset=${historyOffset}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (res.ok) {
            const newLogs = await res.json();
            if (newLogs.length > 0) {
                const listEl = document.getElementById('history-list');
                listEl.insertAdjacentHTML('beforeend', newLogs.map(snap => getSnapshotHTML(snap)).join(''));
            }
            
            if (newLogs.length < historyLimit) {
                btn.style.display = 'none';
            } else {
                btn.style.display = 'block';
                btn.disabled = false;
                btn.textContent = 'Load More';
            }
        }
    } catch (e) {
        console.error("Load more failed", e);
        btn.disabled = false;
        btn.textContent = 'Load More';
    }
}
window.loadMoreHistory = loadMoreHistory;

// ── Score trend chart ──
function renderScoreChart(snapshots) {
  console.log("Rendering chart with:");
  console.log("DEBUG: Chart snapshots sample:", snapshots[0]);
  const svg = document.getElementById('score-chart');
  const labelsEl = document.getElementById('chart-labels');
  if (!svg || !snapshots || snapshots.length === 0) return;

  // Get last 7 snapshots with scores
  const scored = snapshots
    .filter(s => s.vektra_score !== null && s.vektra_score !== undefined)
    .slice(0, 7)
    .reverse();

  if (scored.length < 2) {
    svg.innerHTML = `<text x="150" y="45" text-anchor="middle" fill="#444460" font-size="12" font-family="Inter">Log more days to see trend</text>`;
    return;
  }

  const width = 300;
  const height = 80;
  const padding = 10;
  const scores = scored.map(s => s.vektra_score);
  const min = Math.max(0, Math.min(...scores) - 10);
  const max = Math.min(100, Math.max(...scores) + 10);

  const points = scored.map((s, i) => {
    const x = padding + (i / (scored.length - 1)) * (width - padding * 2);
    const y = height - padding - ((s.vektra_score - min) / (max - min)) * (height - padding * 2);
    return `${x},${y}`;
  });

  const pointsArr = points.map(p => p.split(',').map(Number));

  // Gradient area
  const areaPoints = [
    `${pointsArr[0][0]},${height - padding}`,
    ...points,
    `${pointsArr[pointsArr.length-1][0]},${height - padding}`
  ].join(' ');

  svg.innerHTML = `
    <defs>
      <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#6c63ff" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="#6c63ff" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <polygon points="${areaPoints}" fill="url(#chartGrad)"/>
    <polyline points="${points.join(' ')}" fill="none" stroke="#6c63ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    ${pointsArr.map((p, i) => `
      <circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#6c63ff"/>
      <text x="${p[0]}" y="${p[1] - 7}" text-anchor="middle" fill="#f0f0f5" font-size="9" font-family="Inter">${scores[i].toFixed(0)}</text>
    `).join('')}
  `;

  // Labels
  labelsEl.innerHTML = scored.map(s => {
    const d = new Date(s.timestamp);
    return `<span>${d.toLocaleDateString('en-US', {weekday:'short'})}</span>`;
  }).join('');
}


function getLanguageName(code) {
  const languages = {
    'en': 'English', 'sw': 'Swahili', 'fr': 'French',
    'es': 'Spanish', 'pt': 'Portuguese', 'ar': 'Arabic',
    'hi': 'Hindi', 'zh': 'Chinese', 'de': 'German',
    'it': 'Italian', 'ru': 'Russian', 'ja': 'Japanese'
  };
  return languages[code] || 'English';
}

// ── Currency pricing by region ──
function getPricingForCurrency(currency) {
  const pricing = {
    'KES': { tier1: 20, tier2: 50, tier3: 100, symbol: 'KES', name: 'Kenya' },
    'NGN': { tier1: 20, tier2: 50, tier3: 100, symbol: '₦', name: 'Nigeria' },
    'GHS': { tier1: 20, tier2: 50, tier3: 100, symbol: '₵', name: 'Ghana' },
    'ZAR': { tier1: 20, tier2: 50, tier3: 100, symbol: 'R', name: 'South Africa' },
    'UGX': { tier1: 20, tier2: 50, tier3: 100, symbol: 'UGX', name: 'Uganda' },
    'TZS': { tier1: 20, tier2: 50, tier3: 100, symbol: 'TZS', name: 'Tanzania' },
    'USD': { tier1: 20, tier2: 50, tier3: 100, symbol: '$', name: 'US' },
    'BRL': { tier1: 20, tier2: 50, tier3: 100, symbol: 'R$', name: 'Brazil' },
    'MXN': { tier1: 20, tier2: 50, tier3: 100, symbol: '$', name: 'Mexico' },
    'GBP': { tier1: 20, tier2: 50, tier3: 100, symbol: '£', name: 'UK' },
    'EUR': { tier1: 20, tier2: 50, tier3: 100, symbol: '€', name: 'Europe' },
    'INR': { tier1: 20, tier2: 50, tier3: 100, symbol: '₹', name: 'India' },
    'PKR': { tier1: 20, tier2: 50, tier3: 100, symbol: '₨', name: 'Pakistan' },
  };
  return pricing[currency] || pricing['USD'];
}

function getTierPreviewPrice(tier, currency = 'USD') {
  const pricing = getPricingForCurrency(currency);
  const base = pricing[tier] || pricing.tier1 || 20;
  const fxRates = {
    USD: 1, KES: 129.5, NGN: 1520, GHS: 15.2, ZAR: 18.4, UGX: 3720,
    TZS: 2680, GBP: 0.78, EUR: 0.91, CAD: 1.36, AUD: 1.52, INR: 83.5,
    PKR: 278, BRL: 5.1, MXN: 17.2, EGP: 48.5, ZMW: 27, XOF: 600
  };
  const pppRates = {
    USD: 1.0, KES: 0.70, NGN: 0.55, GHS: 0.55, ZAR: 0.65, UGX: 0.40,
    TZS: 0.48, GBP: 1.0, EUR: 1.0, INR: 0.55, PKR: 0.55, BRL: 0.65,
    MXN: 0.65, CAD: 1.0, AUD: 1.0, EGP: 0.55, ZMW: 0.48, XOF: 0.40
  };
  const fx = fxRates[currency] || 1;
  const ppp = pppRates[currency] || 0.70;
  return Math.round(base * ppp * fx);
}

function getTierDisplayPrice(tier, currency = 'USD') {
  const symbol = getPricingForCurrency(currency).symbol || '$';
  const amount = getTierPreviewPrice(tier, currency);
  return `${symbol} ${amount.toLocaleString()}`;
}

function generateInsight(latest) {
  const insightEl = document.getElementById('insight-text') || document.getElementById('smart-insight');
  if (!insightEl) return;
  
  // Logic for the "Truth"
  let message = "Keep logging to calibrate your trajectory.";
  
  if (latest.mood_score < 5) {
    message = "Your mood is in the basement. Stop overthinking and move your body. Progress doesn't care about your feelings.";
  } else if (latest.energy_level > 8 && latest.focus_level < 5) {
    message = "High energy but low focus? You're just spinning wheels. Pick one hard task and kill it.";
  } else if (latest.vektra_score > 75) {
    message = "You're building momentum. Don't get arrogant—that's exactly when you'll slip up.";
  } else if (latest.daily_income === 0) {
    message = "Income is zero. Your trajectory is currently just a hobby. Fix your leverage.";
  }
  // Add this logic to your function to handle the "Best Decision" scenario
  if (latest.best_decision && latest.best_decision.length > 5) {
    message = `You made a good move: "${latest.best_decision}". Keep repeating that logic.`;
  }

  insightEl.textContent = message;
}

// ── Pricing / Upgrade Screen ──
let selectedTierUpgrade = 'tier1';
let currentPriceData = null;
let priceCalculateTimer = null;
let priceLockInterval = null;
let priceLockSeconds = 900; // 15 minutes

async function openUpgrade() {
  goTo('upgrade');
  initOfferCountdown();
  selectedTierUpgrade = 'tier1';
  document.getElementById('days-slider').value = 30;
  const currency = currentUser?.currency || 'USD';
  document.getElementById('amount-input').value = getTierPreviewPrice('tier1', currency);
  document.getElementById('price-content').style.display = 'none';
  document.getElementById('price-loading').style.display = 'block';
  document.getElementById('milestone-badge').style.display = 'none';
  const offerBanner = document.getElementById('quick-money-offer-banner');
  if (offerBanner) offerBanner.style.display = quickMoneyOfferRequested ? 'block' : 'none';
  updateTierButtonLabels();
  updateAmountConstraints();
  await onSliderChange(30);
}

function updateTierButtonLabels() {
  const currency = currentUser?.currency || 'USD';
  ['tier1', 'tier2', 'tier3'].forEach(tier => {
    const el = document.getElementById(`tier-price-${tier}`);
    if (el) el.textContent = `${getTierDisplayPrice(tier, currency)}/mo`;
  });
}

function selectTier(tier) {
  selectedTierUpgrade = tier;
  
  ['tier1','tier2','tier3'].forEach(t => {
    const btn = document.getElementById(`tier-btn-${t}`);
    if (!btn) return; // Skip if element doesn't exist
    
    if (t === tier) {
      btn.style.border = '2px solid var(--accent)';
      btn.style.background = 'rgba(108,99,255,0.15)';
      btn.style.color = 'var(--text-primary)';
    } else {
      btn.style.border = '1px solid var(--border)';
      btn.style.background = 'transparent';
      btn.style.color = 'var(--text-secondary)';
    }
  });

  updateAmountConstraints();
  
  const days = parseInt(document.getElementById('days-slider').value);
  onSliderChange(days);
}

function updateAmountConstraints() {
  const currency = currentUser?.currency || 'USD';
  const monthlyPrice = getTierPreviewPrice(selectedTierUpgrade, currency);
  const m = selectedTierUpgrade === 'tier1' ? 6 : selectedTierUpgrade === 'tier2' ? 5 : 4;
  const minAmount = Math.round(monthlyPrice);
  const maxAmount = Math.round(monthlyPrice * 366 * 2 / 61 * (1 - 1 / m));
  
  const symbol = getPricingForCurrency(currency).symbol || '$';
  document.getElementById('min-amount').textContent = `${symbol} ${minAmount.toLocaleString()}`;
  document.getElementById('max-amount').textContent = `${symbol} ${maxAmount.toLocaleString()}`;
  
  const amountInput = document.getElementById('amount-input');
  amountInput.min = minAmount;
  amountInput.max = maxAmount;
}

function switchTab(tab) {
  const daysTab = document.getElementById('tab-days');
  const amountTab = document.getElementById('tab-amount');
  const daysOption = document.getElementById('option-days');
  const amountOption = document.getElementById('option-amount');
  
  if (tab === 'days') {
    daysTab.style.border = '1px solid var(--accent)';
    daysTab.style.background = 'rgba(108,99,255,0.15)';
    daysTab.style.color = 'var(--text-primary)';
    amountTab.style.border = '1px solid var(--border)';
    amountTab.style.background = 'transparent';
    amountTab.style.color = 'var(--text-secondary)';
    daysOption.style.display = 'block';
    amountOption.style.display = 'none';
  } else {
    amountTab.style.border = '1px solid var(--accent)';
    amountTab.style.background = 'rgba(108,99,255,0.15)';
    amountTab.style.color = 'var(--text-primary)';
    daysTab.style.border = '1px solid var(--border)';
    daysTab.style.background = 'transparent';
    daysTab.style.color = 'var(--text-secondary)';
    amountOption.style.display = 'block';
    daysOption.style.display = 'none';
  }
}

function onSliderChange(value) {
  const days = parseInt(value);
  document.getElementById('days-display').textContent = `${days} days`;

  const currency = currentUser?.currency || 'USD';
  const monthlyPrice = getTierPreviewPrice(selectedTierUpgrade, currency);
  const dailyRate = monthlyPrice / 30;
  const amount = Math.round(dailyRate * days);
  document.getElementById('amount-input').value = amount;

  // Sync amount display
  document.getElementById('days-display-amount').textContent = `${days} days`;

  // Calculate expiry date
  const expiryDate = new Date();
  expiryDate.setDate(expiryDate.getDate() + days);
  document.getElementById('expiry-display').textContent = expiryDate.toLocaleDateString('en-US', { 
    weekday: 'short', 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  });

  // Show milestone badge
  const milestones = [
    {days:366, badge:'👑 Founder — Max savings + 61 FREE bonus days'},
    {days:274, badge:'⭐⭐⭐⭐ 9 Months — +42 bonus days'},
    {days:183, badge:'⭐⭐⭐ Half Year — +25 bonus days'},
    {days:91,  badge:'⭐⭐ Quarter — +10 bonus days'},
    {days:61,  badge:'⭐ 2 Months — +4 bonus days'}
  ];
  const milestone = milestones.find(m => days >= m.days);
  const badgeEl = document.getElementById('milestone-badge');
  if (milestone) {
    badgeEl.textContent = milestone.badge;
    badgeEl.style.display = 'block';
  } else {
    badgeEl.style.display = 'none';
  }

  // Debounced API call
  debouncedCalculatePrice(days);
}

async function onAmountChange(amount) {
  const amountNum = parseFloat(amount);
  const currency = currentUser?.currency || 'USD';
  const monthlyPrice = getTierPreviewPrice(selectedTierUpgrade, currency);
  const m = selectedTierUpgrade === 'tier1' ? 6 : selectedTierUpgrade === 'tier2' ? 5 : 4;
  const minAmount = Math.round(monthlyPrice);
  const maxAmount = Math.round(monthlyPrice * 366 * 2 / 61 * (1 - 1 / m));
  
  if (!amountNum || amountNum < minAmount) {
    document.getElementById('days-display-amount').textContent = '—';
    document.getElementById('expiry-display').textContent = '—';
    return;
  }

  document.getElementById('days-display-amount').textContent = 'Calculating...';
  document.getElementById('days-display').textContent = 'Calculating...';
  document.getElementById('expiry-display').textContent = 'Calculating...';
  debouncedCalculatePrice(30);
}

async function calculatePrice(days) {
  if (!currentUser || !authToken) return;

  document.getElementById('price-loading').style.display = 'block';
  document.getElementById('price-content').style.display = 'none';

  try {
    const amount = parseFloat(document.getElementById('amount-input').value);
    const body = {
      tier: selectedTierUpgrade,
      currency: currentUser.currency || 'USD',
      country_code: currentUser.current_location ? getCountryCode() : 'DEFAULT',
      special_offer: specialOfferActive
    };
    
    // Send amount if user is using amount input, otherwise send days
    if (document.getElementById('option-amount').style.display === 'block') {
      body.amount = amount;
    } else {
      body.days = days;
    }
    body.special_offer = quickMoneyOfferRequested || specialOfferActive;

    const res = await fetch(`${API}/api/v1/pricing/calculate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      console.error('Price calculation error:', res.status);
      document.getElementById('price-loading').style.display = 'none';
      document.getElementById('price-content').style.display = 'none';
      showToast('Price calculation failed. Please try again.', 'error');
      return;
    }
    
    currentPriceData = await res.json();
    renderPriceCard(currentPriceData);

  } catch(e) {
    console.log('Price calculation error:', e);
    document.getElementById('price-loading').style.display = 'none';
    document.getElementById('price-content').style.display = 'none';
    showToast('Price calculation failed. Please try again.', 'error');
  }
}

// Debounced version for amount input events
const debouncedCalculatePrice = debounce((days) => calculatePrice(days), 500);

function getCountryCode() {
  const currencyToCountry = {
    'KES':'KE','NGN':'NG','GHS':'GH','ZAR':'ZA',
    'UGX':'UG','TZS':'TZ','GBP':'GB','EUR':'DE',
    'INR':'IN','BRL':'BR','MXN':'MX','USD':'US'
  };
  return currencyToCountry[currentUser.currency] || 'DEFAULT';
}

function renderPriceCard(data) {
  const amount = data?.total || parseFloat(document.getElementById('amount-input').value) || 0;
  const days = data?.days || parseInt(document.getElementById('days-display').textContent) || 30;
  const currency = data?.currency || currentUser?.currency || 'USD';
  const symbol = data?.symbol || getPricingForCurrency(currency).symbol || '$';
  const savings = data?.you_save || 0;
  const discountPct = data?.discount_rate_pct || 0;
  const bonusDays = data?.bonus_days || 0;

  document.getElementById('amount-input').value = amount;
  document.getElementById('days-display').textContent = `${days} days`;
  document.getElementById('days-display-amount').textContent = `${days} days`;
  document.getElementById('days-slider').value = days;
  const expiryDate = new Date();
  expiryDate.setDate(expiryDate.getDate() + days);
  document.getElementById('expiry-display').textContent = expiryDate.toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
  });

  document.getElementById('price-loading').style.display = 'none';
  document.getElementById('price-content').style.display = 'block';

  document.getElementById('price-total').textContent = `${symbol} ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  document.getElementById('price-monthly-eq').textContent = `${symbol} ${parseFloat(data?.monthly_equivalent || (amount / days * 30)).toLocaleString(undefined, { maximumFractionDigits: 2 })}/month equivalent`;
  document.getElementById('price-final').textContent = `${symbol} ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  document.getElementById('total-days-display').textContent = days;

  const expiryText = document.getElementById('expiry-display').textContent;
  document.getElementById('price-expires').textContent = expiryText !== '—' ? expiryText : '—';

  if (savings > 0) {
    document.getElementById('price-saved').textContent = `${symbol} ${savings.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    const bonusText = bonusDays > 0 ? `Discount ${discountPct.toFixed(1)}% applied — You get ${bonusDays} days free` : `Discount ${discountPct.toFixed(1)}% applied`;
    document.getElementById('price-bonus-days').textContent = bonusText;
    document.getElementById('savings-card').style.display = 'block';
  } else {
    document.getElementById('savings-card').style.display = 'none';
  }

  const btn = document.getElementById('checkout-btn');
  const termsChecked = document.getElementById('terms-checkbox').checked;
  btn.disabled = !termsChecked;
  btn.textContent = termsChecked ? `Pay ${symbol} ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })} →` : 'Accept Terms to Pay';

  // Start price lock countdown
  startPriceLockCountdown();
}

function startPriceLockCountdown() {
  // Safe clear — checks if an interval instance actually exists first
  if (priceLockInterval) {
    clearInterval(priceLockInterval);
  }
  
  // Set to 15 minutes (900 seconds)
  priceLockSeconds = 900; 
  
  // Fetch the element once outside the loop to optimize runtime execution
  const timerElement = document.getElementById('price-lock-timer');
  const sliderElement = document.getElementById('days-slider');
  
  if (!timerElement) {
    console.warn("⚠️ Telemetry Error: 'price-lock-timer' element not found in DOM.");
    return; // Stop execution early if target layout container is missing
  }

  priceLockInterval = setInterval(() => {
    priceLockSeconds--;
    
    // Calculate layout metrics
    const mins = Math.floor(priceLockSeconds / 60);
    const secs = priceLockSeconds % 60;
    
    // Format output with structural padding
    timerElement.textContent = `Price locked for ${mins}:${secs.toString().padStart(2, '0')}`;
    
    // Expiration Logic Hook
    if (priceLockSeconds <= 0) {
      clearInterval(priceLockInterval);
      timerElement.textContent = '⚠ Price lock expired — recalculating...';
      
      if (sliderElement) {
        // Enforce safe mathematical integer parsing (base-10 radix)
        const days = parseInt(sliderElement.value, 10);
        calculatePrice(days);
      } else {
        console.error("⚠️ UI Error: 'days-slider' element not found.");
      }
    }
  }, 1000);
}

async function proceedToCheckout() {
  if (!currentPriceData || !currentUser || !authToken) {
    console.error('Missing required data:', { currentPriceData, currentUser, hasToken: !!authToken });
    showToast('Missing payment information. Please try selecting your plan again.', 'error');
    return;
  }

  const btn = document.getElementById('checkout-btn');
  btn.textContent = 'Connecting to payment...';
  btn.disabled = true;

  try {
    const payload = {
      email: currentUser.email,
      amount: currentPriceData.total,
      currency: currentPriceData.currency || 'KES',
      tier: selectedTierUpgrade,
      special_offer: quickMoneyOfferRequested || specialOfferActive,
      callback_url: window.location.origin + window.location.pathname + '?payment_success=true&tier=' + selectedTierUpgrade
    };
    
    console.log('Sending payment request:', payload);
    console.log('Payment URL:', `${API}/api/v1/users/${currentUser.id}/payments/paystack`);

    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/payments/paystack`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const text = await res.text();
      console.error('Payment error response:', text);
      try {
        const data = JSON.parse(text);
        showToast(data.detail || 'Payment initialization failed', 'error');
      } catch {
        showToast(`Payment failed (${res.status}): ${text.substring(0, 100)}`, 'error');
      }
      btn.textContent = `Pay ${currentPriceData.symbol} ${currentPriceData.total.toLocaleString()} →`;
      btn.disabled = false;
      return;
    }

    const data = await res.json();
    console.log('Payment response:', data);

    // Get Paystack authorization URL
    const authUrl = data?.external_response?.data?.authorization_url;
    
    if (authUrl) {
      // Redirect to Paystack payment page
      window.location.href = authUrl;
    } else {
      console.error('No auth URL in response:', data);
      showToast('Could not initialize payment. Try again.', 'error');
      btn.textContent = `Pay ${currentPriceData.symbol} ${currentPriceData.total.toLocaleString()} →`;
      btn.disabled = false;
    }
  } catch(e) {
    console.error('Payment connection error:', e);
    showToast('Payment connection failed. Try again.', 'error');
    btn.textContent = `Pay ${currentPriceData.symbol} ${currentPriceData.total.toLocaleString()} →`;
    btn.disabled = false;
  }
}

window.generateInsight = generateInsight;
window.login = login;
window.register = register;
window.loginWithCredentials = loginWithCredentials;
window.filterHistory = filterHistory;
window.openTrajectoryHistory = openTrajectoryHistory;
window.viewReport = viewReport;
window.addGoal = addGoal;
window.renderScoreChart = renderScoreChart;
window.loadReport = loadReport;
window.loadAnalytics = loadAnalytics;
window.exportData = exportData;
window.setProfileTone = setProfileTone;
window.loadMonthlyReplay = loadMonthlyReplay;
window.toggleNotifications = toggleNotifications;
window.currentUser = currentUser;
window.navTo = navTo;
window.goTo = goTo;
window.currentScreen = currentScreen;

// Terms checkbox listener
document.addEventListener('DOMContentLoaded', () => {
  const termsCheckbox = document.getElementById('terms-checkbox');
  if (termsCheckbox) {
    termsCheckbox.addEventListener('change', () => {
      if (currentPriceData) {
        renderPriceCard(currentPriceData); // Re-render to update button state
      }
    });
  }
});
window.selectedTierUpgrade = selectedTierUpgrade;
window.currentPriceData = currentPriceData;
window.priceCalculateTimer = priceCalculateTimer;
window.priceLockInterval = priceLockInterval;
window.priceLockSeconds = priceLockSeconds;

window.openUpgrade = openUpgrade;
window.selectTier = selectTier;
window.onSliderChange = onSliderChange;
window.onAmountChange = onAmountChange;
window.switchTab = switchTab;
window.updateAmountConstraints = updateAmountConstraints;
window.calculatePrice = calculatePrice;
window.getCountryCode = getCountryCode;
window.renderPriceCard = renderPriceCard;
window.startPriceLockCountdown = startPriceLockCountdown;
window.proceedToCheckout = proceedToCheckout;
window.onboardStep1 = onboardStep1;
window.onboardStep2 = onboardStep2;
window.onboardStep3 = onboardStep3;
window.selectTone = selectTone;

// ── Keep backend alive (ping every 10 minutes) ──
function keepBackendAlive() {
  fetch(`${API}/api/v1/health`)
    .then(() => console.log('Backend alive'))
    .catch(() => console.log('Backend sleeping - will wake on next request'));
}

// Ping immediately on load, then every 10 minutes
keepBackendAlive();
setInterval(keepBackendAlive, 10 * 60 * 1000);
window.keepBackendAlive = keepBackendAlive;

// ── Forgot Password ──
function showForgotPassword() {
  goTo('password-reset-request');
}

async function requestPasswordReset() {
  const email = document.getElementById('reset-email').value.trim();
  const errEl = document.getElementById('reset-request-error');
  const successEl = document.getElementById('reset-request-success');
  
  errEl.style.display = 'none';
  successEl.style.display = 'none';
  
  if (!email) {
    errEl.textContent = 'Please enter your email address.';
    errEl.style.display = 'block';
    return;
  }
  
  try {
    const res = await fetch(`${API}/api/v1/auth/request-password-reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    
    if (res.ok) {
      successEl.textContent = 'If email exists, reset link sent. Check your inbox.';
      successEl.style.display = 'block';
    } else {
      errEl.textContent = 'Failed to send reset link. Try again.';
      errEl.style.display = 'block';
    }
  } catch (e) {
    errEl.textContent = 'Connection error. Try again.';
    errEl.style.display = 'block';
  }
}

async function confirmPasswordReset() {
  const newPassword = document.getElementById('reset-new-password').value;
  const confirmPassword = document.getElementById('reset-confirm-password').value;
  const errEl = document.getElementById('reset-confirm-error');
  
  errEl.style.display = 'none';
  
  if (!newPassword || !confirmPassword) {
    errEl.textContent = 'Please fill in both password fields.';
    errEl.style.display = 'block';
    return;
  }
  
  if (newPassword !== confirmPassword) {
    errEl.textContent = 'Passwords do not match.';
    errEl.style.display = 'block';
    return;
  }
  
  if (newPassword.length < 8) {
    errEl.textContent = 'Password must be at least 8 characters.';
    errEl.style.display = 'block';
    return;
  }
  
  // Get token from URL query parameter
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  if (!token) {
    errEl.textContent = 'Invalid reset link. Please request a new one.';
    errEl.style.display = 'block';
    return;
  }
  
  try {
    const res = await fetch(`${API}/api/v1/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword })
    });
    
    if (res.ok) {
      showToast('Password reset successfully! Please login.', 'success', 3000);
      goTo('login');
    } else {
      const data = await res.json().catch(() => ({}));
      errEl.textContent = data.detail || 'Failed to reset password. Link may be expired.';
      errEl.style.display = 'block';
    }
  } catch (e) {
    errEl.textContent = 'Connection error. Try again.';
    errEl.style.display = 'block';
  }
}

async function resendVerificationEmail() {
  if (!currentUser || !currentUser.email) {
    showToast('Please login first', 'error', 3000);
    return;
  }
  
  try {
    const res = await fetch(`${API}/api/v1/auth/resend-verification`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: currentUser.email })
    });
    
    if (res.ok) {
      showToast('Verification email sent!', 'success', 3000);
    } else {
      showToast('Failed to send verification email', 'error', 3000);
    }
  } catch (e) {
    showToast('Connection error. Try again.', 'error', 3000);
  }
}

async function verifyEmailWithToken() {
  // Get token from URL query parameter
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  if (!token) {
    document.getElementById('verify-error').textContent = 'No verification token found.';
    document.getElementById('verify-error').style.display = 'block';
    return;
  }
  
  try {
    const res = await fetch(`${API}/api/v1/auth/verify-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    
    if (res.ok) {
      document.getElementById('verify-success').textContent = 'Email verified successfully!';
      document.getElementById('verify-success').style.display = 'block';
      setTimeout(() => {
        if (currentUser) {
          currentUser.is_verified = true;
        }
        goTo('dashboard');
      }, 2000);
    } else {
      const data = await res.json().catch(() => ({}));
      document.getElementById('verify-error').textContent = data.detail || 'Invalid or expired token.';
      document.getElementById('verify-error').style.display = 'block';
    }
  } catch (e) {
    document.getElementById('verify-error').textContent = 'Connection error. Try again.';
    document.getElementById('verify-error').style.display = 'block';
  }
}

async function submitForgotPassword() {
  const username = document.getElementById('forgot-username').value.trim();
  const email = document.getElementById('forgot-email').value.trim();
  const errEl = document.getElementById('forgot-error');
  const successEl = document.getElementById('forgot-success');

  errEl.style.display = 'none';
  successEl.style.display = 'none';

  if (!username || !email) {
    errEl.textContent = 'Please fill in both fields.';
    errEl.style.display = 'block';
    return;
  }

  try {
    const res = await fetch('https://formspree.io/f/xeebwojj', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'PASSWORD_RESET_REQUEST',
        username,
        email,
        date: new Date().toISOString()
      })
    });

    if (res.ok) {
      successEl.style.display = 'block';
      document.getElementById('forgot-username').value = '';
      document.getElementById('forgot-email').value = '';
    } else {
      errEl.textContent = 'Could not send request. Try again.';
      errEl.style.display = 'block';
    }
  } catch(e) {
    errEl.textContent = 'Could not connect. Try again.';
    errEl.style.display = 'block';
  }
}
window.showForgotPassword = showForgotPassword;
window.submitForgotPassword = submitForgotPassword;

// Expose performance utilities
window.debounce = debounce;
window.Cache = Cache;
window.dedupedFetch = dedupedFetch;


async function loadDailyReport() {
  document.getElementById('report-narrative').textContent = 'Loading today\'s summary...';
  document.getElementById('report-period').textContent = 'Today';
  if (!currentUser || !authToken) return;

  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots?limit=1`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (!res.ok) return;
    const snapshots = await res.json();
    if (!snapshots.length) {
      document.getElementById('report-narrative').textContent = 'No log found for today. Submit your daily log first.';
      return;
    }

    const snap = snapshots[0];
    const date = new Date(snap.timestamp);
    const isToday = date.toDateString() === new Date().toDateString();

    document.getElementById('report-period').textContent = 
      isToday ? 'Today' : date.toLocaleDateString('en-US', {weekday:'long', month:'short', day:'numeric'});

    document.getElementById('report-score').textContent = 
      snap.vektra_score ? snap.vektra_score.toFixed(0) : '—';

    // Stats
    document.getElementById('report-days').textContent = isToday ? 'Today' : '1 day';
    document.getElementById('report-cashflow').textContent = 
      snap.daily_income !== null && snap.expenses !== null 
      ? (snap.daily_income - snap.expenses >= 0 ? '+' : '') + (snap.daily_income - snap.expenses)
      : '—';
    document.getElementById('report-goals').textContent = 
      snap.target_hit_bool !== null ? (snap.target_hit_bool ? '✓' : '✗') : '—';

    const cfEl = document.getElementById('report-cashflow');
    if (snap.daily_income !== null && snap.expenses !== null) {
      cfEl.style.color = (snap.daily_income - snap.expenses) >= 0 ? 'var(--success)' : 'var(--danger)';
    }

    // Daily narrative — free tier is data only, no AI
    const tier = currentUser.tier || 'free';
    if (tier === 'free') {
      const summary = buildDailySummaryText(snap);
      document.getElementById('report-narrative').innerHTML = summary;
    } else {
      // Tier 1/2 — AI narrative (needs Claude API)
      document.getElementById('report-narrative').innerHTML = buildDailySummaryText(snap);
    }

    // Engine bars from today's snapshot
    renderEngineBar('bar-financial', 'Financial', snap.vektra_score || 50, '#22c55e');
    renderEngineBar('bar-mental', 'Mental', snap.mood_score ? snap.mood_score * 10 : 50, '#6c63ff');
    renderEngineBar('bar-execution', 'Execution', snap.target_hit_bool ? 100 : 50, '#ec4899');
    renderEngineBar('bar-body', 'Body', snap.sleep_hours ? Math.min(100, snap.sleep_hours / 9 * 100) : 50, '#f59e0b');
    renderEngineBar('bar-growth', 'Growth', snap.skills_learned ? 80 : 30, '#06b6d4');

  } catch(e) {
    document.getElementById('report-narrative').textContent = 'Could not load today\'s summary.';
  }
}

function buildDailySummaryText(snap) {
  const score = snap.vektra_score ? snap.vektra_score.toFixed(0) : '—';
  const mood = snap.mood_score ? `${snap.mood_score}/10` : '—';
  const energy = snap.energy_level ? `${snap.energy_level}/10` : '—';
  const sleep = snap.sleep_hours ? `${snap.sleep_hours}h` : '—';
  const income = snap.daily_income || 0;
  const expenses = snap.expenses || 0;
  const cashflow = income - expenses;
  const goalHit = snap.target_hit_bool !== null ? (snap.target_hit_bool ? '✓ Yes' : '✗ No') : '—';
  const tomorrow = snap.tomorrow_goal || 'Not set';
  const best = snap.best_decision || '—';

  return `
<strong>🎯 TRAJECTORY: ${score}/100</strong><br><br>
<strong>Mental</strong><br>
Mood: ${mood} &nbsp;|&nbsp; Energy: ${energy}<br><br>
<strong>Body</strong><br>
Sleep: ${sleep}<br><br>
<strong>Finance</strong><br>
Cash flow: ${cashflow >= 0 ? '+' : ''}${cashflow}<br><br>
<strong>Execution</strong><br>
Hit yesterday's goal: ${goalHit}<br>
Best decision: ${best}<br><br>
<strong>Tomorrow</strong><br>
${tomorrow}
  `.trim();
}
window.loadDailyReport = loadDailyReport;
window.buildDailySummaryText = buildDailySummaryText;

/**
 * Asynchronously checks profile credentials, fetches stats snapshots,
 * and initializes the visual birthday card experience.
 */
async function loadBirthdayCard() {
  // 1. Route navigation to target screen structure
  goTo('birthday-card');
  if (!currentUser || !authToken) return;

  // 2. Perform baseline profiling validation checks
  if (!currentUser.dob) {
    showToast('Please set your date of birth in profile first', 'error');
    return;
  }

  const today = new Date();
  const dob = new Date(currentUser.dob);
  
  if (isNaN(dob.getTime())) {
    showToast('Invalid date of birth format in profile', 'error');
    return;
  }

  // Check month and day matches today
  const isBirthday = today.getMonth() === dob.getMonth() && today.getDate() === dob.getDate();
  
  if (!isBirthday) {
    if (typeof calculateDaysUntilBirthday === 'function') {
      const daysUntil = calculateDaysUntilBirthday(dob);
      showToast(`Your birthday is in ${daysUntil} days! 🎂`, 'info', 3000);
    }
    return; // Fast exit gate to prevent unnecessary server load
  }

  // 3. Inject descriptive name and target data variables safely
  const name = currentUser.full_name?.split(' ')[0] || currentUser.username || 'Friend';
  const nameEl = document.getElementById('bd-name');
  if (nameEl) nameEl.textContent = name;

  const nsEl = document.getElementById('bd-northstar');
  if (nsEl) nsEl.textContent = currentUser.north_star || 'Not set yet — update in profile';

  // 4. Compute generational milestone age differences
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
    age--;
  }
  
  const ageEl = document.getElementById('bd-age');
  if (ageEl) {
    ageEl.textContent = `Year ${age + 1} begins today 🚀`;
  }

  // Localized fail-safe inner DOM manipulation helper
  const setDOMText = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  // 5. Gather year-to-date telemetry metric snapshots
  try {
    const res = await fetch(`${API}/api/v1/users/${currentUser.id}/snapshots`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (!res.ok) throw new Error(`API Endpoint connection issue: ${res.status}`);
    const snapshots = await res.json();

    // Default zero-state UI fallback boundaries
    if (!snapshots || snapshots.length === 0) {
      setDOMText('bd-score', '—');
      setDOMText('bd-best', '0');
      setDOMText('bd-streak', '🔥 0');
      setDOMText('bd-logs', '0');
      setDOMText('bd-avg', '—');
      setDOMText('bd-trajectory', 'Start logging to build your trajectory');
      
      triggerBirthdayAnimations();
      return;
    }

    // Filter array payload data nodes
    const scores = snapshots.map(s => s.vektra_score).filter(s => s !== null && s !== undefined);
    
    if (scores.length === 0) {
      setDOMText('bd-score', '—');
      setDOMText('bd-best', '—');
      setDOMText('bd-avg', '—');
    } else {
      const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
      const bestScore = Math.max(...scores);
      
      setDOMText('bd-score', avgScore.toFixed(0));
      setDOMText('bd-best', bestScore.toFixed(0));
      setDOMText('bd-avg', avgScore.toFixed(0));
      
      const trajectoryText = avgScore >= 70 ? '🔥 Rising trajectory' :
                             avgScore >= 50 ? '→ Steady vector' : '⚠ Recalibrating';
      setDOMText('bd-trajectory', trajectoryText);
    }

    const streak = typeof calculateStreak === 'function' ? calculateStreak(snapshots) : 0;
    setDOMText('bd-streak', `🔥 ${streak}`);
    setDOMText('bd-logs', snapshots.length);

    // Trigger internal analytics/reporting operations hooks
    if (typeof loadReport === 'function') await loadReport('birthday');

    // Fire graphics/celebration modules
    triggerBirthdayAnimations();

  } catch(e) {
    console.error('Birthday card pipeline exception caught:', e);
    setDOMText('bd-trajectory', 'Could not load your trajectory stats');
    
    // Always trigger presentation tier even when endpoints throw
    triggerBirthdayAnimations();
  }
}

/**
 * Executes CSS animation rendering classes and launches external particle systems.
 */
function triggerBirthdayAnimations() {
  const screen = document.getElementById('birthday-card');
  if (screen) {
    screen.classList.add('animate-ready');
  }

  // Trigger high-density colorful particle spray burst
  if (typeof confetti === 'function') {
    confetti({
      particleCount: 140,
      spread: 75,
      origin: { y: 0.65 },
      colors: ['#6c63ff', '#ec4899', '#ffd200']
    });
  }
}

/**
 * Placeholder share handler action definition
 */
function shareBirthdayCard() {
  if (navigator.share) {
    navigator.share({
      title: 'VEKTRA Birthday Milestones',
      text: `Checked my year progress vector on my birthday!`,
      url: window.location.href
    }).catch(console.error);
  } else {
    // Clipboard copy fallback procedure
    navigator.clipboard.writeText(`My VEKTRA Trajectory score is active today!`)
      .then(() => showToast('Card metrics copied to clipboard!', 'success'))
      .catch(() => showToast('Unable to share card content', 'error'));
  }
}

// Check if today is user's birthday on dashboard load
function checkBirthday() {
  if (!currentUser?.dob) return;
  const dob = new Date(currentUser.dob);
  const today = new Date();
  if (dob.getMonth() === today.getMonth() && dob.getDate() === today.getDate()) {
    setTimeout(() => {
      showToast('🎂 Happy Birthday! Your VEKTRA birthday card is ready!', 'success', 6000);
      setTimeout(() => loadBirthdayCard(), 3000);
    }, 2000);
  }
}
window.loadBirthdayCard = loadBirthdayCard;
window.shareBirthdayCard = shareBirthdayCard;
window.checkBirthday = checkBirthday;
window.triggerBirthdayAnimations = triggerBirthdayAnimations;

// ── Check payment return ──
function checkPaymentReturn() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('payment_success') === 'true') {
    const tier = params.get('tier') || 'tier1';
    const ref = params.get('reference');
    
    showToast('Payment received! Activating your plan... 🔥', 'success', 5000);
    
    // Verify and activate
    if (ref) verifyAndActivate(ref, tier);
    
    // Clean URL
    window.history.replaceState({}, '', window.location.pathname);
  }
}

async function verifyAndActivate(reference, tier) {
  try {
    const res = await fetch(`${API}/api/v1/payments/paystack/verify/${reference}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      // Refresh user data
      const userRes = await fetch(`${API}/api/v1/users/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (userRes.ok) {
        currentUser = await userRes.json();
        showToast(`Welcome to ${tier === 'tier2' ? 'Apex' : 'Vector'}! 🔥`, 'success', 5000);
        goTo('dashboard');
        loadDashboard();
      }
    }
  } catch(e) {
    console.log('Verification error:', e);
  }
}
window.checkPaymentReturn = checkPaymentReturn;
window.verifyAndActivate = verifyAndActivate;

// ── Special Offer Functions ──
let specialOfferActive = false;
const SPECIAL_OFFER_DEADLINE = new Date("2026-09-09T23:59:59+03:00").getTime();
const SPECIAL_OFFER_DAYS = 120; // 4 months (3 paid + 1 free)

function updateOfferCountdown() {
  const countdownEl = document.getElementById('offer-countdown');
  if (!countdownEl) return;
  
  const now = new Date().getTime();
  const difference = SPECIAL_OFFER_DEADLINE - now;
  
  if (difference <= 0) {
    countdownEl.textContent = "Offer ended";
    const banner = document.getElementById('special-offer-banner');
    if (banner) banner.style.display = 'none';
    return;
  }
  
  const days = Math.floor(difference / (1000 * 60 * 60 * 24));
  const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
  
  countdownEl.textContent = `${days}d ${hours}h ${minutes}m remaining`;
}

function activateSpecialOffer() {
  if (!currentUser || !authToken) return;
  
  // Calculate offer price: 3 months × PPP factor
  // We'll call pricing API with days=90 but override display
  specialOfferActive = true;
  
  // Show special offer price card
  document.getElementById('price-loading').style.display = 'none';
  document.getElementById('price-content').style.display = 'block';
  
  // Set expiry to Jan 1st 2027
  const expires = new Date('2027-01-01T23:59:59');
  
  // Calculate 3-month price based on tier and currency
  const currency = currentUser.currency || 'USD';
  const sym = getCurrencySymbol(currency);
  
  // Base monthly prices after PPP (approximated from pricing engine)
  const monthlyPrices = {
    'tier1': { 'KES': 1424.50, 'USD': 26.67, 'NGN': 12000, 'GHS': 160, 'ZAR': 490 },
    'tier2': { 'tier2_KES': 3561.25, 'tier2_USD': 66.67, 'tier2_NGN': 30000, 'tier2_GHS': 400, 'tier2_ZAR': 1225 }
  };
  
  const tierPrices = selectedTierUpgrade === 'tier2' ? 
    { 'KES': 3561.25, 'USD': 66.67, 'NGN': 30000, 'GHS': 400, 'ZAR': 1225, 'DEFAULT': 66.67 } :
    { 'KES': 1424.50, 'USD': 26.67, 'NGN': 12000, 'GHS': 160, 'ZAR': 490, 'DEFAULT': 26.67 };
  
  const monthly = tierPrices[currency] || tierPrices['DEFAULT'];
  const offerTotal = monthly * 3;
  const fullPrice = monthly * 4; // What 4 months would normally cost
  const saved = fullPrice - offerTotal;
  
  // Update price card
  document.getElementById('price-total').textContent = `${sym} ${offerTotal.toLocaleString()}`;
  document.getElementById('price-monthly-eq').textContent = `Access until Jan 1st, 2027`;
  
  document.getElementById('savings-card').style.display = 'block';
  document.getElementById('price-saved').textContent = `${sym} ${saved.toLocaleString()}`;
  document.getElementById('price-bonus-days').textContent = '1 month FREE — Launch offer';
  
  document.getElementById('total-days-display').textContent = '~120 days';
  document.getElementById('price-final').textContent = `${sym} ${offerTotal.toLocaleString()}`;
  document.getElementById('price-expires').textContent = 'January 1st, 2027';
  
  // Store offer price for checkout
  currentPriceData = {
    total: offerTotal,
    currency: currency,
    symbol: sym,
    days: 120,
    is_special_offer: true,
    expires_at: expires.toISOString()
  };
  
  // Update checkout button
  const btn = document.getElementById('checkout-btn');
  btn.disabled = false;
  btn.textContent = `🔥 Claim Offer — ${sym} ${offerTotal.toLocaleString()} →`;
  
  showToast('Launch offer activated! 25% off applied. 🔥', 'success', 3000);
}

function getCurrencySymbol(currency) {
  const symbols = {
    'KES': 'KES', 'USD': '$', 'NGN': '₦', 'GHS': '₵',
    'ZAR': 'R', 'GBP': '£', 'EUR': '€', 'INR': '₹'
  };
  return symbols[currency] || '$';
}

// Initialize countdown when upgrade screen loads
function initOfferCountdown() {
  const deadline = new Date('2026-09-09T23:59:59+03:00');
  const now = new Date();
  
  if (now > deadline) {
    const banner = document.getElementById('special-offer-banner');
    if (banner) banner.style.display = 'none';
    return;
  }
  
  updateOfferCountdown();
  setInterval(updateOfferCountdown, 60000);
}

window.activateSpecialOffer = activateSpecialOffer;
window.initOfferCountdown = initOfferCountdown;

// ── News / Updates Functions ──
async function loadNews() {
  const loadingEl = document.getElementById('news-loading');
  const containerEl = document.getElementById('news-container');
  const emptyEl = document.getElementById('news-empty');
  
  if (!loadingEl || !containerEl || !emptyEl) return;
  
  loadingEl.style.display = 'flex';
  containerEl.style.display = 'none';
  emptyEl.style.display = 'none';
  
  try {
    const res = await fetch(`${API}/api/v1/news/all`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (res.ok) {
      const data = await res.json();
      
      if (data.items && data.items.length > 0) {
        containerEl.innerHTML = data.items.map(item => createNewsCard(item)).join('');
        containerEl.style.display = 'flex';
        loadingEl.style.display = 'none';
      } else {
        emptyEl.style.display = 'block';
        loadingEl.style.display = 'none';
      }
    } else {
      emptyEl.style.display = 'block';
      loadingEl.style.display = 'none';
    }
  } catch (e) {
    console.error('Failed to load news:', e);
    emptyEl.style.display = 'block';
    loadingEl.style.display = 'none';
  }
}

function createNewsCard(item) {
  const typeIcons = {
    'quote': '💭',
    'countdown': '⏰',
    'tip': '💡',
    'announcement': '📢'
  };
  
  const typeColors = {
    'quote': 'rgba(108,99,255,0.15)',
    'countdown': 'rgba(236,72,153,0.15)',
    'tip': 'rgba(34,197,94,0.15)',
    'announcement': 'rgba(250,204,21,0.15)'
  };
  
  const typeBorders = {
    'quote': 'rgba(108,99,255,0.4)',
    'countdown': 'rgba(236,72,153,0.4)',
    'tip': 'rgba(34,197,94,0.4)',
    'announcement': 'rgba(250,204,21,0.4)'
  };
  
  const icon = typeIcons[item.type] || '📰';
  const bgColor = typeColors[item.type] || 'rgba(255,255,255,0.05)';
  const borderColor = typeBorders[item.type] || 'var(--border)';
  
  const date = new Date(item.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
  
  return `
    <div style="background:${bgColor};border:1px solid ${borderColor};border-radius:var(--radius);padding:1.25rem">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:18px">${icon}</span>
        <span style="font-size:11px;color:var(--accent);text-transform:uppercase;letter-spacing:0.05em;font-weight:600">${item.type}</span>
        ${item.priority === 'high' ? '<span style="font-size:10px;background:var(--accent);color:#fff;padding:2px 6px;border-radius:4px;font-weight:600">Important</span>' : ''}
      </div>
      <div style="font-size:15px;font-weight:600;margin-bottom:6px;color:var(--text-primary)">${item.title}</div>
      <div style="font-size:14px;color:var(--text-secondary);line-height:1.5;margin-bottom:8px">${item.content}</div>
      ${item.author ? `<div style="font-size:12px;color:var(--text-muted)">— ${item.author}</div>` : ''}
      <div style="font-size:11px;color:var(--text-muted);margin-top:8px">${date}</div>
    </div>
  `;
}

window.loadNews = loadNews;