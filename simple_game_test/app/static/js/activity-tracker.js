
/**
 * ActivityTracker.js - User activity logging module
 * Tracks user interactions, page navigation, keyboard/mouse events
 * Stores data efficiently in localStorage
 */

// Configuration
const config = {
    maxLogEntries: 10000,
    storageKey: 'activity_log',
    enableLogging: true
  };
  
  // Abbreviations for events (to save storage space)
  const eventAbbr = {
    'click': 'clk', 'mousedown': 'mdn', 'mouseup': 'mup', 'mousemove': 'mmv',
    'keydown': 'kdn', 'keyup': 'kup',
    'touchstart': 'tst', 'touchend': 'ted',
    'input': 'inp', 'change': 'chg',
    'beforeunload': 'bun', 'unload': 'unl', 'pagehide': 'phd', 'pageshow': 'psh',
    'popstate': 'pop', 'hashchange': 'hch', 'load': 'lod',
    'reload': 'rel', 'back_forward': 'bfw', 'fresh_navigation': 'nav',
    'focus': 'foc', 'blur': 'blr', 'visibilitychange': 'vch',
    'error': 'err', 'inactive': 'ina'
  };
  
  // Key mapping to save space
  const keyMap = {
    'ArrowLeft': 'Left', 'ArrowRight': 'Right', 'ArrowUp': 'Up', 'ArrowDown': 'Down',
    'Enter': 'Enter', 'Tab': 'Tab', 'Escape': 'Esc', 'Backspace': 'BckSpc', 'Delete': 'Del',
    'Home': 'Hm', 'End': 'End', 'PageUp': 'PgU', 'PageDown': 'PgD',
    'Control': 'Ctrl', 'Alt': 'Alt', 'Shift': 'Shft', 'Meta': 'Met',
    ' ': 'Spc', 'Space': 'Spc'
  };
  
  // State
  let activityLog = [];
  
  function formatDate(date) {
    const options = { timeZone: 'America/New_York', hour12: false };
    const padZero = (num) => String(num).padStart(2, '0');
    const zonedDate = new Date(date.toLocaleString('en-US', options));
    return `${padZero(zonedDate.getHours())}-${padZero(zonedDate.getMinutes())}-${padZero(zonedDate.getSeconds())}`;
  }
  
  function loadLogs() {
    try {
      const savedLog = localStorage.getItem(config.storageKey);
      if (savedLog) activityLog = JSON.parse(savedLog);
    } catch (e) {
      console.error('Error loading activity log:', e);
      activityLog = [];
    }
  }
  
  function logActivity(eventType, additionalInfo = {}) {
    if (!config.enableLogging) return;
  
    try {
      const abbr = eventAbbr[eventType] || eventType;
      const timestamp = formatDate(new Date());
      const logEntry = { t: timestamp, e: abbr };
  
      if (additionalInfo.key) logEntry.k = keyMap[additionalInfo.key] || additionalInfo.key;
      if (!logEntry.k && additionalInfo.keyCode) logEntry.c = additionalInfo.keyCode;
  
      if (additionalInfo.modifiers) {
        let modifiers = 0;
        if (additionalInfo.modifiers.ctrl) modifiers |= 1;
        if (additionalInfo.modifiers.alt) modifiers |= 2;
        if (additionalInfo.modifiers.shift) modifiers |= 4;
        if (additionalInfo.modifiers.meta) modifiers |= 8;
        logEntry.m = modifiers;
      }
  
      if (additionalInfo.target) logEntry.tg = additionalInfo.target;
  
      if (additionalInfo.url) {
        try {
          const urlObj = new URL(additionalInfo.url);
          let pathname = urlObj.pathname + urlObj.search;
          const basePath = "/flask_closed_loop_teaching";
          if (pathname.startsWith(basePath)) pathname = pathname.slice(basePath.length);
          logEntry.u = pathname;
        } catch (e) {
          let rawPath = additionalInfo.url;
          const basePath = "/flask_closed_loop_teaching";
          if (rawPath.startsWith(basePath)) rawPath = rawPath.slice(basePath.length);
          logEntry.u = rawPath;
        }
      }

      if (additionalInfo.hidden){
        try{
            logEntry.h = additionalInfo.hidden
        }
        catch (e) {
            console.error('Error logging activity:', e);
        }
      }
  
      activityLog.push(logEntry);
      if (activityLog.length > config.maxLogEntries) {
        activityLog = activityLog.slice(-config.maxLogEntries);
      }
  
      localStorage.setItem(config.storageKey, JSON.stringify(activityLog));
      localStorage.setItem("last_activity", abbr);
      localStorage.setItem("last_activity_time", timestamp);
    } catch (e) {
      console.error('Error logging activity:', e);
    }
  }
  
  function setupTracking() {
    window.addEventListener("load", () => {
      try {
        const navEntry = performance.getEntriesByType("navigation")[0];
        if (navEntry) {
          const navType = navEntry.type;
          if (navType === "reload") logActivity("reload", { url: window.location.href });
          else if (navType === "back_forward") logActivity("back_forward", { url: window.location.href });
          else if (navType === "navigate") logActivity("fresh_navigation", { url: window.location.href });
          else logActivity("load", { url: window.location.href, navType: navType });
        } else {
          logActivity("load", { url: window.location.href, note: "nav_timing_unsupported" });
        }
      } catch (e) {
        console.error("Error detecting navigation type:", e);
      }
    });
  
    document.addEventListener('click', e => logActivity('click', { x: e.clientX, y: e.clientY, target: e.target.id || e.target.tagName.toLowerCase() }));
    document.addEventListener('mousedown', e => logActivity('mousedown', { x: e.clientX, y: e.clientY, target: e.target.id || e.target.tagName.toLowerCase() }));
    document.addEventListener('mouseup', e => logActivity('mouseup', { x: e.clientX, y: e.clientY }));
  
    document.addEventListener('keydown', e => logActivity('keydown', {
      key: e.key,
      keyCode: e.keyCode,
      modifiers: { ctrl: e.ctrlKey, alt: e.altKey, shift: e.shiftKey, meta: e.metaKey },
      target: e.target.id || e.target.tagName.toLowerCase()
    }));
  
    document.addEventListener('keyup', e => logActivity('keyup', {
      key: e.key,
      keyCode: e.keyCode,
      modifiers: { ctrl: e.ctrlKey, alt: e.altKey, shift: e.shiftKey, meta: e.metaKey }
    }));
  
    document.addEventListener('touchstart', e => {
      const touch = e.touches[0];
      logActivity('touchstart', { x: touch.clientX, y: touch.clientY, target: e.target.id || e.target.tagName.toLowerCase() });
    });
  
    document.addEventListener('touchend', e => logActivity('touchend', { target: e.target.id || e.target.tagName.toLowerCase() }));
    document.addEventListener('input', e => logActivity('input', { target: e.target.id || e.target.tagName.toLowerCase() }));
    document.addEventListener('change', e => logActivity('change', { target: e.target.id || e.target.tagName.toLowerCase() }));
  
    window.addEventListener('beforeunload', () => logActivity('beforeunload', { url: window.location.href }));
    // window.addEventListener('unload', () => logActivity('unload', { url: window.location.href }));
    window.addEventListener('pagehide', () => logActivity('pagehide', { url: window.location.href }));
    window.addEventListener('pageshow', () => logActivity('pageshow', { url: window.location.href }));
    window.addEventListener('popstate', () => logActivity('popstate', { url: window.location.href }));
  
    const originalPushState = window.history.pushState;
    window.history.pushState = function () {
      originalPushState.apply(this, arguments);
      logActivity('pushState', { url: window.location.href });
    };
  
    const originalReplaceState = window.history.replaceState;
    window.history.replaceState = function () {
      originalReplaceState.apply(this, arguments);
      logActivity('replaceState', { url: window.location.href });
    };
  
    document.addEventListener('visibilitychange', () => logActivity('visibilitychange', { hidden: document.hidden, url: window.location.href }));
    window.addEventListener('hashchange', e => logActivity('hashchange', { oldUrl: e.oldURL, newUrl: e.newURL }));
    window.addEventListener('focus', () => logActivity('focus', { url: window.location.href }));
    window.addEventListener('blur', () => logActivity('blur', { url: window.location.href }));
  
    logActivity('pageInitialized', { url: window.location.href });
  }
  
  window.ActivityTracker = (function () {
    let initialized = false;
    let publicAPI = {};
  
    publicAPI.init = function (options = {}) {
      if (initialized) return publicAPI;
  
      if (options.maxLogEntries) config.maxLogEntries = options.maxLogEntries;
      if (options.storageKey) config.storageKey = options.storageKey;
      if (options.enableLogging !== undefined) config.enableLogging = !!options.enableLogging;
  
      loadLogs();
      setupTracking();
      initialized = true;
  
      return publicAPI;
    };
  
    publicAPI.logActivity = logActivity;
  
    return publicAPI;
  })();
  