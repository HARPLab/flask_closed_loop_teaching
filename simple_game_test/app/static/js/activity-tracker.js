/**
 * ActivityTracker.js - User activity logging module
 * Tracks user interactions, page navigation, keyboard/mouse events
 * Stores data efficiently in localStorage
 */

// Self-executing function to avoid polluting global namespace
(function() {
    // Configuration
    const config = {
      maxLogEntries: 500,
      storageKey: 'activity_log',
      enableLogging: true
    };
    
    // Abbreviations for events (to save storage space)
    const eventAbbr = {
      // Mouse events
      'click': 'clk', 'mousedown': 'mdn', 'mouseup': 'mup', 'mousemove': 'mmv',
      // Keyboard events
      'keydown': 'kdn', 'keyup': 'kup',
      // Touch events
      'touchstart': 'tst', 'touchend': 'ted',
      // Form events
      'input': 'inp', 'change': 'chg',
      // Navigation events
      'beforeunload': 'bun', 'unload': 'unl', 'pagehide': 'phd', 'pageshow': 'psh',
      'popstate': 'pop', 'hashchange': 'hch', 'load': 'lod',
      // Navigation types
      'reload': 'rel', 'back_forward': 'bfw', 'fresh_navigation': 'nav',
      // Focus events
      'focus': 'foc', 'blur': 'blr', 'visibilitychange': 'vch',
      // Other
      'error': 'err', 'inactive': 'ina'
    };
    
    // Key mapping to save space
    const keyMap = {
      'ArrowLeft': '←', 'ArrowRight': '→', 'ArrowUp': '↑', 'ArrowDown': '↓',
      'Enter': '⏎', 'Tab': '⇥', 'Escape': 'Esc', 'Backspace': '⌫', 'Delete': 'Del',
      'Home': 'Hm', 'End': 'End', 'PageUp': 'PgU', 'PageDown': 'PgD',
      'Control': 'Ctrl', 'Alt': 'Alt', 'Shift': 'Shft', 'Meta': 'Met',
      ' ': 'Spc', 'Space': 'Spc'
    };
    
    // State variables
    let activityLog = [];
    
    // Format date as YY-MM-DD-HH-MM-SS
    function formatDate(date) {
      const padZero = (num) => String(num).padStart(2, '0');
      const year = date.getFullYear().toString().slice(2);
      const month = padZero(date.getMonth() + 1);
      const day = padZero(date.getDate());
      const hours = padZero(date.getHours());
      const minutes = padZero(date.getMinutes());
      const seconds = padZero(date.getSeconds());
      
      return `${year}-${month}-${day}-${hours}-${minutes}-${seconds}`;
    }
    
    // Load existing logs if available
    function loadLogs() {
      try {
        const savedLog = localStorage.getItem(config.storageKey);
        if (savedLog) {
          activityLog = JSON.parse(savedLog);
        }
      } catch (e) {
        console.error('Error loading activity log:', e);
        activityLog = [];
      }
    }
    
    // Main logging function
    function logActivity(eventType, additionalInfo = {}) {
      if (!config.enableLogging) return;
      
      try {
        const abbr = eventAbbr[eventType] || eventType;
        const timestamp = formatDate(new Date());
        
        // Create compact log entry
        const logEntry = { t: timestamp, e: abbr };
        
        // Add key information for keyboard events
        if (additionalInfo.key) {
          logEntry.k = keyMap[additionalInfo.key] || additionalInfo.key;
        }
        
        // Add keyCode if no key mapping exists
        if (!logEntry.k && additionalInfo.keyCode) {
          logEntry.c = additionalInfo.keyCode;
        }
        
        // Add modifier keys if present
        if (additionalInfo.modifiers) {
          let modifiers = 0;
          if (additionalInfo.modifiers.ctrl) modifiers |= 1;
          if (additionalInfo.modifiers.alt) modifiers |= 2;
          if (additionalInfo.modifiers.shift) modifiers |= 4;
          if (additionalInfo.modifiers.meta) modifiers |= 8;
          logEntry.m = modifiers;
        }
        
        // Add mouse/touch coordinates if available
        if (additionalInfo.x !== undefined && additionalInfo.y !== undefined) {
          logEntry.x = Math.round(additionalInfo.x);
          logEntry.y = Math.round(additionalInfo.y);
        }
        
        // Add target element information if available
        if (additionalInfo.target) {
          logEntry.tg = additionalInfo.target;
        }
        
        // Add URL info for navigation events
        if (additionalInfo.url) {
          try {
            const urlObj = new URL(additionalInfo.url);
            logEntry.u = urlObj.pathname + urlObj.search;
          } catch (e) {
            logEntry.u = additionalInfo.url;
          }
        }
        
        // Add to memory log
        activityLog.push(logEntry);
        
        // Trim log if too large
        if (activityLog.length > config.maxLogEntries) {
          activityLog = activityLog.slice(-config.maxLogEntries);
        }
        
        // Update localStorage
        localStorage.setItem(config.storageKey, JSON.stringify(activityLog));
        
        // Update last activity for inactivity timer
        localStorage.setItem("last_activity", abbr);
        localStorage.setItem("last_activity_time", timestamp);
        

      } catch (e) {
        console.error('Error logging activity:', e);
      }
    }
    
    // Set up event listeners for tracking
    function setupTracking() {
      // Track page navigation using Navigation Timing API
      window.addEventListener("load", () => {
        try {
          const navEntry = performance.getEntriesByType("navigation")[0];
          
          if (navEntry) {
            const navType = navEntry.type;
            
            if (navType === "reload") {
              logActivity("reload", {url: window.location.href});
            } else if (navType === "back_forward") {
              logActivity("back_forward", {url: window.location.href});
            } else if (navType === "navigate") {
              logActivity("fresh_navigation", {url: window.location.href});
            } else {
              logActivity("load", {url: window.location.href, navType: navType});
            }
          } else {
            logActivity("load", {url: window.location.href, note: "nav_timing_unsupported"});
          }
        } catch (e) {
          console.error("Error detecting navigation type:", e);
          logActivity("load", {url: window.location.href, error: e.message});
        }
      });
      
      // Mouse events
      document.addEventListener('click', e => logActivity('click', {
        x: e.clientX, y: e.clientY,
        target: e.target.id || e.target.tagName.toLowerCase()
      }));
      
      document.addEventListener('mousedown', e => logActivity('mousedown', {
        x: e.clientX, y: e.clientY,
        target: e.target.id || e.target.tagName.toLowerCase()
      }));
      
      document.addEventListener('mouseup', e => logActivity('mouseup', {
        x: e.clientX, y: e.clientY
      }));
      
      // Keyboard events
      document.addEventListener('keydown', e => {
        logActivity('keydown', {
          key: e.key,
          keyCode: e.keyCode,
          modifiers: {
            ctrl: e.ctrlKey,
            alt: e.altKey,
            shift: e.shiftKey,
            meta: e.metaKey
          },
          target: e.target.id || e.target.tagName.toLowerCase()
        });
      });
      
      document.addEventListener('keyup', e => logActivity('keyup', {
        key: e.key,
        keyCode: e.keyCode,
        modifiers: {
          ctrl: e.ctrlKey,
          alt: e.altKey,
          shift: e.shiftKey,
          meta: e.metaKey
        }
      }));
      
      // Touch events for mobile
      document.addEventListener('touchstart', e => {
        const touch = e.touches[0];
        logActivity('touchstart', {
          x: touch.clientX, 
          y: touch.clientY,
          target: e.target.id || e.target.tagName.toLowerCase()
        });
      });
      
      document.addEventListener('touchend', e => logActivity('touchend', {
        target: e.target.id || e.target.tagName.toLowerCase()
      }));
      
      // Form events
      document.addEventListener('input', e => logActivity('input', {
        target: e.target.id || e.target.tagName.toLowerCase()
      }));
      
      document.addEventListener('change', e => logActivity('change', {
        target: e.target.id || e.target.tagName.toLowerCase()
      }));
      
      // Browser navigation events
      window.addEventListener('beforeunload', e => {
        logActivity('beforeunload', {url: window.location.href});
        if (localStorage.getItem("movement") === "false") {
          e.preventDefault();
          e.returnValue = "Are you sure you want to leave? The task is incomplete.";
        }
      });
      
      window.addEventListener('unload', () => logActivity('unload', {url: window.location.href}));
      window.addEventListener('pagehide', () => logActivity('pagehide', {url: window.location.href}));
      window.addEventListener('pageshow', () => logActivity('pageshow', {url: window.location.href}));
      
      // Track popstate (back/forward buttons)
      window.addEventListener('popstate', () => logActivity('popstate', {url: window.location.href}));
      
      // Track history API calls
      const originalPushState = window.history.pushState;
      window.history.pushState = function() {
        originalPushState.apply(this, arguments);
        logActivity('pushState', {url: window.location.href});
      };
      
      const originalReplaceState = window.history.replaceState;
      window.history.replaceState = function() {
        originalReplaceState.apply(this, arguments);
        logActivity('replaceState', {url: window.location.href});
      };
      
      // Track visibility changes
      document.addEventListener('visibilitychange', () => logActivity('visibilitychange', {
        hidden: document.hidden,
        url: window.location.href
      }));
      
      // Track hash changes
      window.addEventListener('hashchange', (e) => logActivity('hashchange', {
        oldUrl: e.oldURL,
        newUrl: e.newURL
      }));
      
      // Focus events
      window.addEventListener('focus', () => logActivity('focus', {url: window.location.href}));
      window.addEventListener('blur', () => logActivity('blur', {url: window.location.href}));
      
      // Log initial page visit
      logActivity('pageInitialized', {url: window.location.href});
      
      console.log('Activity tracking initialized. Log size: ' + JSON.stringify(activityLog).length + ' bytes');
    }
    
    // Get statistics about logged activities
    function getStats() {
      const stats = {
        totalEntries: activityLog.length,
        sizeInBytes: JSON.stringify(activityLog).length,
        eventTypes: {},
        keyboardActions: {},
        navigations: {
          reload: 0,
          back_forward: 0,
          fresh_navigation: 0,
          other: 0
        },
        timeSpan: {
          start: activityLog.length > 0 ? activityLog[0].t : null,
          end: activityLog.length > 0 ? activityLog[activityLog.length-1].t : null
        }
      };
      
      // Count event types
      activityLog.forEach(entry => {
        // Count event types
        stats.eventTypes[entry.e] = (stats.eventTypes[entry.e] || 0) + 1;
        
        // Count keyboard actions
        if (entry.e === 'kdn' && entry.k) {
          stats.keyboardActions[entry.k] = (stats.keyboardActions[entry.k] || 0) + 1;
        }
        
        // Count navigation types
        if (entry.e === 'rel') stats.navigations.reload++;
        else if (entry.e === 'bfw') stats.navigations.back_forward++;
        else if (entry.e === 'nav') stats.navigations.fresh_navigation++;
        else if (entry.e === 'pop' || entry.e === 'phd' || entry.e === 'psh') stats.navigations.other++;
      });
      
      return stats;
    }
    
    // Export log as JSON file
    function exportLog() {
      try {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activityLog, null, 2));
        const downloadElement = document.createElement('a');
        downloadElement.setAttribute("href", dataStr);
        downloadElement.setAttribute("download", "activity_log.json");
        document.body.appendChild(downloadElement);
        downloadElement.click();
        downloadElement.remove();
        
        return getStats();
      } catch (e) {
        console.error("Error exporting activity log:", e);
        return null;
      }
    }
    
    // Clear log
    function clearLog() {
      activityLog = [];
      localStorage.setItem(config.storageKey, JSON.stringify(activityLog));
      return { cleared: true, newSize: 0 };
    }
    
    // Initialize module
    function init(options = {}) {
      // Apply custom options
      if (options) {
        config.maxLogEntries = options.maxLogEntries || config.maxLogEntries;
        config.storageKey = options.storageKey || config.storageKey;
        config.enableLogging = options.enableLogging !== undefined ? options.enableLogging : config.enableLogging;
        
      }
      
      // Load existing logs
      loadLogs();
      
      // Set up event tracking
      setupTracking();
      
      // Return public API
      return {
        log: logActivity,
        getStats: getStats,
        export: exportLog,
        clear: clearLog,
        enableLogging: function(enable) {
          config.enableLogging = !!enable;
        }
      };
    }
    
    // Expose to global scope
    window.ActivityTracker = {
      init: init
    };
  })();