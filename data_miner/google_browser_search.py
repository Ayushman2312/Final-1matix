"""
Google Search functions using browser automation to avoid detection.
This module provides reliable Google search capabilities that mimic human behavior.
"""

import asyncio
import logging
import os
import random
import time
import traceback
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse, quote
import json

import tldextract
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import nest_asyncio

# Configure logger
logger = logging.getLogger('GoogleBrowserSearch')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class GoogleBrowserSearch:
    """Class for performing Google searches using browser automation to avoid detection."""
    
    def __init__(self, debug_mode=False):
        """Initialize the search utility with configurable options.
        
        Args:
            debug_mode: Whether to save screenshots and debug information.
        """
        self.debug_mode = debug_mode
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.browser_initialized = False
        
        # Create debug directory
        if self.debug_mode:
            os.makedirs("debug_html", exist_ok=True)

    async def initialize_browser(self):
        """Initialize the browser with stealth settings to avoid detection.
        
        Returns:
            bool: True if browser was successfully initialized.
        """
        if self.browser_initialized and self.browser and self.page:
            logger.info("Browser already initialized")
            return True
            
        try:
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            
            # Browser arguments to avoid detection
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=BlockCredentialedSubresources',
                # Disable proxy settings to use direct connection
                '--no-proxy-server'
            ]
            
            # Launch browser with realistic configuration
            launch_options = {
                "headless": True,
                "args": browser_args,
                "timeout": 60000,  # 60 second timeout
                "ignore_default_args": ["--enable-automation"],
                "chromium_sandbox": False,
                "handle_sigint": False,
                "handle_sigterm": False,
                "handle_sighup": False
            }
            
            # Try to launch the browser
            try:
                self.browser = await self.playwright.chromium.launch(**launch_options)
                logger.info("Browser launched successfully")
            except Exception as e:
                logger.error(f"Error launching browser: {e}")
                await self._cleanup_resources()
                return False
            
            # Create a browser context with human-like settings
            try:
                viewport_sizes = [
                    {"width": 1920, "height": 1080},
                    {"width": 1366, "height": 768},
                    {"width": 1536, "height": 864},
                    {"width": 1440, "height": 900}
                ]
                context_options = {
                    "viewport": random.choice(viewport_sizes),
                    "user_agent": self._get_random_user_agent(),
                    "locale": "en-IN",  # Use Indian locale
                    "timezone_id": "Asia/Kolkata",  # Indian timezone
                    "geolocation": {"longitude": 77.2090, "latitude": 28.6139, "accuracy": 100},  # New Delhi
                    "permissions": ["geolocation"],
                    "is_mobile": random.random() < 0.2,  # 20% chance of mobile device
                    "color_scheme": "no-preference",
                    "reduced_motion": "no-preference"
                }
                
                self.context = await self.browser.new_context(**context_options)
                
                # Apply stealth settings
                await self._apply_stealth_settings()
                logger.info("Applied enhanced stealth settings with Google-specific protections")
                logger.info("Browser context created with stealth settings")
            except Exception as e:
                logger.error(f"Error creating browser context: {e}")
                await self._cleanup_resources()
                return False
            
            # Create page
            try:
                self.page = await self.context.new_page()
                
                # Set extra HTTP headers
                await self.page.set_extra_http_headers({
                    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua": "\"Google Chrome\";v=\"113\", \"Chromium\";v=\"113\", \"Not-A.Brand\";v=\"24\""
                })
                
                logger.info("Browser page created")
            except Exception as e:
                logger.error(f"Error creating browser page: {e}")
                await self._cleanup_resources()
                return False
            
            # Test navigation
            try:
                # Use a simple, reliable test site
                await self.page.goto("https://www.google.com", timeout=30000)
                await asyncio.sleep(1)
                logger.info("Browser test navigation successful")
            except Exception as e:
                logger.error(f"Test navigation failed: {e}")
                await self._cleanup_resources()
                return False
            
            self.browser_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Error during browser initialization: {e}")
            logger.error(traceback.format_exc())
            await self._cleanup_resources()
            return False

    async def _cleanup_resources(self):
        """Clean up browser resources."""
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
            
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
            
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
            
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
            
        self.browser_initialized = False
        logger.info("Browser resources cleaned up")

    async def _apply_stealth_settings(self):
        """Apply stealth settings to avoid bot detection."""
        if not self.context:
            return
            
        # Enhanced stealth script with more comprehensive fingerprint protection
        await self.context.add_init_script("""
        () => {
            // ====== NAVIGATOR PROPERTIES CLOAKING ======
            // Override navigator properties to hide automation
            const navigatorPrototypes = [
                Navigator.prototype,
                Object.getPrototypeOf(navigator)
            ];
            
            // Helper to safely override properties
            const safeOverride = (obj, prop, value) => {
                try {
                    Object.defineProperty(obj, prop, {
                        get: function() { return value; }
                    });
                } catch(e) {}
            };
            
            // Hide webdriver flag - multiple approaches
            for (const proto of navigatorPrototypes) {
                safeOverride(proto, 'webdriver', false);
            }
            safeOverride(navigator, 'webdriver', false);
            
            // In case Object.getPrototypeOf is being detected
            if (navigator.__proto__) {
                delete navigator.__proto__.webdriver;
            }
            
            // Advanced: Intercept and modify property descriptors to defeat more sophisticated checks
            const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(obj, prop) {
                const descriptor = originalGetOwnPropertyDescriptor(obj, prop);
                if (obj === navigator && prop === 'webdriver') {
                    return undefined;
                }
                return descriptor;
            };
            
            // ====== LANGUAGES AND GEOLOCATION ======
            // Add languages with Indian locale hints
            safeOverride(navigator, 'languages', ['en-IN', 'en', 'hi']);
            
            // Hardware concurrency (CPU cores) - realistic value for modern systems
            safeOverride(navigator, 'hardwareConcurrency', 4 + Math.floor(Math.random() * 4));
            
            // Device memory - realistic value
            safeOverride(navigator, 'deviceMemory', 4 + Math.floor(Math.random() * 4));
            
            // Make navigator.platform consistent with navigator.userAgent
            const userAgent = navigator.userAgent;
            let platform = 'Win32';
            if (userAgent.includes('Macintosh') || userAgent.includes('Mac OS X')) {
                platform = 'MacIntel';
            } else if (userAgent.includes('Linux')) {
                platform = 'Linux x86_64';
            } else if (userAgent.includes('Android')) {
                platform = 'Android';
            }
            safeOverride(navigator, 'platform', platform);
            
            // ====== PLUGINS AND MIMETYPE SPOOFING ======
            // Make plugins non-empty with realistic values
            if (navigator.plugins.length === 0 || navigator.plugins.length === undefined) {
                const makeFakePluginArray = () => {
                    const plugins = [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client Executable' }
                    ];
                    
                    const pluginArray = Object.create(PluginArray.prototype);
                    Object.defineProperties(pluginArray, {
                        length: { value: plugins.length },
                        item: { value: index => plugins[index] },
                        namedItem: { value: name => plugins.find(p => p.name === name) },
                        refresh: { value: () => {} }
                    });
                    
                    plugins.forEach((plugin, i) => {
                        pluginArray[i] = plugin;
                    });
                    
                    return pluginArray;
                };
                
                safeOverride(navigator, 'plugins', makeFakePluginArray());
            }
            
            // ====== WINDOW PROPERTIES ======
            // Fix window dimensions to realistic values
            if (window.outerWidth === 0) {
                safeOverride(window, 'outerWidth', window.innerWidth);
            }
            if (window.outerHeight === 0) {
                safeOverride(window, 'outerHeight', window.innerHeight + 74);
            }
            
            // ====== BROWSER FEATURE DETECTION EVASION ======
            // Add Chrome-specific properties if missing
            if (!window.chrome) {
                window.chrome = {
                    app: {
                        isInstalled: false,
                        InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
                        RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }
                    },
                    runtime: {
                        OnInstalledReason: {
                            INSTALL: 'install',
                            UPDATE: 'update',
                            CHROME_UPDATE: 'chrome_update',
                            SHARED_MODULE_UPDATE: 'shared_module_update'
                        },
                        OnRestartRequiredReason: {
                            APP_UPDATE: 'app_update',
                            OS_UPDATE: 'os_update',
                            PERIODIC: 'periodic'
                        },
                        PlatformArch: {
                            ARM: 'arm',
                            ARM64: 'arm64',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformNaclArch: {
                            ARM: 'arm',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformOs: {
                            ANDROID: 'android',
                            CROS: 'cros',
                            LINUX: 'linux',
                            MAC: 'mac',
                            OPENBSD: 'openbsd',
                            WIN: 'win'
                        },
                        RequestUpdateCheckStatus: {
                            THROTTLED: 'throttled',
                            NO_UPDATE: 'no_update',
                            UPDATE_AVAILABLE: 'update_available'
                        }
                    }
                };
            }
            
            // ====== CANVAS FINGERPRINTING PROTECTION ======
            // Prevent canvas fingerprinting with subtle modifications
            if (CanvasRenderingContext2D.prototype.getImageData) {
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                    const imageData = originalGetImageData.call(this, x, y, w, h);
                    
                    if (imageData && imageData.data && imageData.data.length > 0) {
                        // Create a deterministic but unique seed for this session
                        const seed = (Math.floor(performance.now()) % 2000) + navigator.userAgent.length + window.screen.height;
                        
                        // Apply very subtle noise to certain pixels
                        for (let i = 0; i < imageData.data.length; i += Math.floor(50 + (seed % 30))) {
                            // Only modify alpha for minimal visual impact
                            if (i % 4 === 3 && imageData.data[i] > 0 && imageData.data[i] < 255) {
                                const diff = ((seed + i) % 3) - 1; // -1, 0, or 1
                                imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + diff));
                            }
                        }
                    }
                    return imageData;
                };
            }
            
            // Protect toDataURL as well - another canvas fingerprinting method
            if (HTMLCanvasElement.prototype.toDataURL) {
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
                    // Only modify specific canvas elements that are likely for fingerprinting
                    const isFingerprintingCanvas = 
                        this.width === 16 && this.height === 16 || 
                        this.width <= 3 && this.height <= 3 ||
                        this.width === 0 || this.height === 0;
                    
                    if (isFingerprintingCanvas) {
                        // Add a transparent watermark pixel that won't affect visuals but changes the hash
                        const ctx = this.getContext('2d');
                        if (ctx) {
                            const oldAlpha = ctx.globalAlpha;
                            ctx.globalAlpha = 0.05; // Nearly invisible
                            ctx.fillStyle = '#ffffff';
                            ctx.fillRect(this.width - 1, this.height - 1, 1, 1);
                            ctx.globalAlpha = oldAlpha;
                        }
                    }
                    return originalToDataURL.apply(this, arguments);
                };
            }
            
            // ====== PERMISSIONS AND NOTIFICATION API SPOOF ======
            // Spoof permissions API for common permission requests
            if (navigator.permissions) {
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(parameters) {
                    // Special handling for notifications
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: "prompt" });
                    }
                    
                    // Frequently checked permissions for fingerprinting
                    if (parameters.name === 'clipboard-read' || 
                        parameters.name === 'clipboard-write' ||
                        parameters.name === 'camera' || 
                        parameters.name === 'microphone') {
                        return Promise.resolve({ state: "prompt" });
                    }
                    
                    return originalQuery.call(navigator.permissions, parameters);
                };
            }
            
            // ====== MEDIA DEVICES PROTECTION ======
            // Spoof enumerateDevices
            if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
                navigator.mediaDevices.enumerateDevices = function() {
                    return originalEnumerateDevices.call(navigator.mediaDevices)
                        .then(devices => {
                            // If no devices, create fake ones to appear more realistic
                            if (!devices || devices.length === 0) {
                                return [
                                    { deviceId: 'default', kind: 'audioinput', label: '', groupId: 'default' },
                                    { deviceId: 'default', kind: 'audiooutput', label: '', groupId: 'default' },
                                    { deviceId: 'default', kind: 'videoinput', label: '', groupId: 'default' }
                                ];
                            }
                            return devices;
                        });
                };
            }
            
            // ====== TIMING ATTACK PREVENTION ======
            // Randomize performance timing functions slightly to prevent time-based fingerprinting
            if (window.performance && window.performance.now) {
                const originalNow = window.performance.now;
                let lastNow = 0;
                window.performance.now = function() {
                    const perfectNow = originalNow.call(window.performance);
                    const nextNowDelta = Math.random() * 0.01;
                    lastNow = Math.max(lastNow + nextNowDelta, perfectNow);
                    return lastNow;
                };
            }
            
            // Date protection is also important for timing attacks
            const originalDateNow = Date.now;
            Date.now = function() {
                return originalDateNow() + (Math.random() * 0.01);
            };
            
            // ====== BROWSER BEHAVIOUR ======
            // Make google.com believe we're scrolling and moving the mouse
            if (window.location.hostname.includes('google')) {
                // Record legitimate mouse position for more realistic movements
                window.mouseX = window.innerWidth / 2;
                window.mouseY = window.innerHeight / 3;
                
                document.addEventListener('mousemove', function(e) {
                    window.mouseX = e.clientX;
                    window.mouseY = e.clientY;
                }, { passive: true });
                
                // Add natural scroll activity data for Google's behavioral analysis
                let lastScrollTime = Date.now();
                let lastScrollPos = 0;
                
                window.addEventListener('scroll', function() {
                    const now = Date.now();
                    const scrollPos = window.scrollY;
                    
                    // Calculate scroll speed and acceleration (metrics Google tracks)
                    const timeDelta = now - lastScrollTime;
                    const scrollDelta = scrollPos - lastScrollPos;
                    
                    // Update global properties that Google's scripts might check
                    window.lastScrollSpeed = timeDelta > 0 ? scrollDelta / timeDelta : 0;
                    
                    // Update for next event
                    lastScrollTime = now;
                    lastScrollPos = scrollPos;
                }, { passive: true });
                
                // Simulate legitimate page lifecycle events
                document.addEventListener('visibilitychange', function() {
                    // Record visibility states - helps appear more human-like
                    window.lastVisibilityEvent = {
                        time: Date.now(),
                        state: document.visibilityState
                    };
                });
            }
            
            // Finally, try to prevent detection of this stealth script itself
            // Make toString() of our overridden functions return the original string representation
            const originalToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                // Special case for prototype methods we've modified
                if (this === HTMLCanvasElement.prototype.toDataURL ||
                    this === CanvasRenderingContext2D.prototype.getImageData || 
                    this === navigator.permissions.query ||
                    this === window.performance.now ||
                    this === Date.now) {
                    return originalToString.call(originalToString);
                }
                
                // Default behavior
                return originalToString.call(this);
            };
        }
        """)
        
        # Set Google-specific cookies for non-tracked browsing experience
        cookies = [
            # NID cookie - Google uses this to remember your preferences
            {
                'name': 'NID',
                'value': '511='+(''.join(random.choices('0123456789', k=12))),
                'domain': '.google.com',
                'path': '/'
            },
            # Same for google.co.in
            {
                'name': 'NID',
                'value': '511='+(''.join(random.choices('0123456789', k=12))),
                'domain': '.google.co.in',
                'path': '/'
            },
            # Consent cookie - indicates we've already seen consent dialogs
            {
                'name': 'CONSENT',
                'value': f'YES+{random.randint(100,999)}',
                'domain': '.google.com',
                'path': '/'
            },
            {
                'name': 'CONSENT',
                'value': f'YES+{random.randint(100,999)}',
                'domain': '.google.co.in',
                'path': '/'
            },
            # DV cookie - used for storing user preferences
            {
                'name': '1P_JAR',
                'value': datetime.now().strftime('%Y-%m-%d-%H'),
                'domain': '.google.com',
                'path': '/'
            },
            {
                'name': '1P_JAR',
                'value': datetime.now().strftime('%Y-%m-%d-%H'),
                'domain': '.google.co.in',
                'path': '/'
            },
            # ANID cookie - advertising ID
            {
                'name': 'ANID',
                'value': 'AHWqTUl'+(''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=16))),
                'domain': '.google.com', 
                'path': '/'
            }
        ]
        
        await self.context.add_cookies(cookies)
        
        # Additional per-page stealth settings applied to any new page
        await self.context.add_init_script("""
        () => {
            // Configure window.chrome deeply
            if (window.chrome) {
                // Make sure chrome.runtime appears legitimate
                if (!window.chrome.runtime) {
                    window.chrome.runtime = {};
                }
                // Add sendMessage and other critical chrome APIs
                if (!window.chrome.runtime.sendMessage) {
                    window.chrome.runtime.sendMessage = () => {
                        return Promise.resolve();
                    };
                }
                
                // Add chrome.app appearance
                if (!window.chrome.app) {
                    window.chrome.app = {
                        InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
                        RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
                        getDetails: function() { return null; },
                        getIsInstalled: function() { return false; },
                        isInstalled: false
                    };
                }
                
                // Ensure chrome.csi exists (Chrome Speed Index)
                if (!window.chrome.csi) {
                    window.chrome.csi = function() {
                        return {
                            onloadT: Date.now(),
                            startE: Date.now(),
                            pageT: Date.now() - window.performance.timing.navigationStart,
                            tran: 15
                        };
                    };
                }
            }
            
            // Fix iframe contentWindow.chrome
            const patchIframeChrome = function() {
                Array.from(document.querySelectorAll('iframe')).forEach(iframe => {
                    try {
                        if (iframe.contentWindow && !iframe.contentWindow.chrome) {
                            iframe.contentWindow.chrome = window.chrome;
                        }
                    } catch (e) {
                        // Ignore cross-origin issues
                    }
                });
            };
            
            // Patch iframes once document is loaded
            if (document.readyState === 'complete') {
                patchIframeChrome();
            } else {
                window.addEventListener('load', patchIframeChrome);
            }
        }
        """)
        
        logger.info("Applied enhanced stealth settings with Google-specific protections")

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string that looks like a real browser."""
        chrome_versions = ['111.0.0.0', '112.0.0.0', '113.0.0.0', '114.0.0.0']
        chrome_build = random.choice(chrome_versions)
        
        return f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_build} Safari/537.36'

    async def _simulate_human_browsing(self):
        """Simulate human-like browsing behavior to avoid detection."""
        if not self.page:
            return
            
        try:
            # Get viewport size
            viewport_size = await self.page.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollHeight: Math.max(
                            document.body ? document.body.scrollHeight : 0,
                            document.documentElement ? document.documentElement.scrollHeight : 0
                        )
                    };
                }
            """)
            
            width = viewport_size.get('width', 1366)
            height = viewport_size.get('height', 768)
            scroll_height = viewport_size.get('scrollHeight', 1500)
            
            # NEW: Different browsing personas that behave differently
            personas = [
                "methodical",   # Careful, deliberate browsing
                "skimmer",      # Quick scan through content
                "researcher",   # Thorough reading with multiple interactions
                "casual",       # Random, less predictable behavior
                "impatient"     # Quick jumpy browsing
            ]
            
            # Select a persona for this session
            persona = random.choice(personas)
            logger.debug(f"Using '{persona}' browsing persona")
            
            # Random initial pause with natural variance based on persona
            initial_pause = {
                "methodical": random.uniform(2.0, 4.0),
                "skimmer": random.uniform(0.5, 1.5),
                "researcher": random.uniform(1.5, 3.0),
                "casual": random.uniform(1.0, 2.5),
                "impatient": random.uniform(0.3, 1.0)
            }
            await asyncio.sleep(initial_pause[persona])
            
            # NEW: Sometimes interact with Google features first
            if random.random() > 0.7:
                # Potential elements to interact with
                interaction_targets = [
                    "input[name='q']",           # Search box
                    ".hdtb-mitem",               # Menu items (All, Images, etc)
                    ".MUFPAc",                   # Search tools
                    "div[role='navigation']"     # Pagination
                ]
                
                # Select an element to interact with
                target_selector = random.choice(interaction_targets)
                
                try:
                    elements = await self.page.query_selector_all(target_selector)
                    if elements and len(elements) > 0:
                        # Choose a random element
                        target_element = random.choice(elements)
                        box = await target_element.bounding_box()
                        
                        if box:
                            # Generate realistic mouse movement
                            start_x, start_y = width/2, height/2
                            
                            # More refined bezier-curve based movement with variation based on persona
                            steps = {
                                "methodical": random.randint(8, 12),
                                "skimmer": random.randint(4, 7),
                                "researcher": random.randint(6, 10),
                                "casual": random.randint(5, 9),
                                "impatient": random.randint(3, 5)
                            }[persona]
                            
                            # Control points for the bezier curve
                            cp1x = start_x + (box['x'] - start_x) * random.uniform(0.1, 0.4)
                            cp1y = start_y + (box['y'] - start_y) * random.uniform(0.1, 0.4)
                            cp2x = start_x + (box['x'] - start_x) * random.uniform(0.6, 0.9)
                            cp2y = start_y + (box['y'] - start_y) * random.uniform(0.6, 0.9)
                            
                            # Calculate the end position with some randomness within the element
                            end_x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
                            end_y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
                            
                            # Move the mouse along the path
                            for step in range(steps + 1):
                                t = step / steps
                                # Cubic bezier curve formula
                                x = (1-t)**3 * start_x + 3*(1-t)**2 * t * cp1x + 3*(1-t) * t**2 * cp2x + t**3 * end_x
                                y = (1-t)**3 * start_y + 3*(1-t)**2 * t * cp1y + 3*(1-t) * t**2 * cp2y + t**3 * end_y
                                
                                # Add subtle human-like shakiness
                                shake_intensity = {
                                    "methodical": 0.5,
                                    "skimmer": 1.5,
                                    "researcher": 0.8,
                                    "casual": 1.2,
                                    "impatient": 2.0
                                }[persona]
                                
                                if 0 < step < steps:
                                    x += random.uniform(-shake_intensity, shake_intensity)
                                    y += random.uniform(-shake_intensity, shake_intensity)
                                
                                await self.page.mouse.move(x, y)
                                
                                # Varying speed at different parts of the motion
                                if step == 0 or step == steps:
                                    # Slower at the very beginning and end
                                    await asyncio.sleep(random.uniform(0.03, 0.06))
                                elif step < steps / 4 or step > 3 * steps / 4:
                                    # Still somewhat slow near beginning/end
                                    await asyncio.sleep(random.uniform(0.02, 0.04))
                                else:
                                    # Faster in the middle of the motion
                                    await asyncio.sleep(random.uniform(0.01, 0.03))
                            
                            # Pause before clicking
                            await asyncio.sleep(random.uniform(0.1, 0.3))
                            
                            # Sometimes actually click (except search box, just hover on that)
                            if target_selector != "input[name='q']" and random.random() > 0.5:
                                await self.page.mouse.click(end_x, end_y)
                                await asyncio.sleep(random.uniform(0.3, 0.8))
                            else:
                                # Just hover for a bit
                                await asyncio.sleep(random.uniform(0.2, 0.7))
                except Exception as e:
                    logger.debug(f"Error during initial interaction: {e}")
            
            # Perform scrolling based on persona
            if scroll_height > height:
                # Different scrolling patterns for different personas
                scroll_style = {
                    "methodical": "smooth",        # Smooth, deliberate scrolling
                    "skimmer": "quick_scan",       # Quick scroll down and maybe back up
                    "researcher": "thorough",      # Careful scrolling with pauses to "read"
                    "casual": "variable",          # Mixture of scrolling speeds and pauses
                    "impatient": "jumpy"           # Large, infrequent scrolls
                }[persona]
                
                current_position = 0
                
                if scroll_style == "smooth":
                    # Smooth, methodical scrolling
                    scroll_positions = []
                    while current_position < scroll_height:
                        # Smaller, deliberate scrolls
                        scroll_amount = random.randint(80, 160)
                        current_position += scroll_amount
                        if current_position > scroll_height:
                            current_position = scroll_height
                        scroll_positions.append(current_position)
                    
                    # Execute scrolls with consistent timing
                    for position in scroll_positions:
                        await self.page.evaluate(f"window.scrollTo(0, {position})")
                        # Brief pauses
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        
                        # Sometimes pause longer to read content
                        if random.random() > 0.7:
                            await asyncio.sleep(random.uniform(0.5, 1.2))
                
                elif scroll_style == "quick_scan":
                    # Quick scan down
                    scroll_step = random.randint(300, 600)
                    num_steps = min(4, max(2, scroll_height // scroll_step))
                    
                    for i in range(num_steps):
                        current_position += scroll_step
                        if current_position > scroll_height:
                            current_position = scroll_height
                            
                        await self.page.evaluate(f"window.scrollTo(0, {current_position})")
                        await asyncio.sleep(random.uniform(0.1, 0.25))
                    
                    # Maybe scroll back up to something interesting
                    if random.random() > 0.6:
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        
                        # Scroll back up to a random position
                        up_position = random.randint(
                            int(current_position * 0.3), 
                            int(current_position * 0.7)
                        )
                        
                        await self.page.evaluate(f"window.scrollTo(0, {up_position})")
                        await asyncio.sleep(random.uniform(0.8, 1.5))
                
                elif scroll_style == "thorough":
                    # Thorough reader - careful scrolling with longer pauses
                    scroll_positions = []
                    while current_position < scroll_height:
                        # Smaller, more deliberate scrolls
                        scroll_amount = random.randint(100, 200)
                        current_position += scroll_amount
                        if current_position > scroll_height:
                            current_position = scroll_height
                        scroll_positions.append(current_position)
                    
                    # Execute scrolls with longer pauses as if actually reading content
                    for position in scroll_positions:
                        await self.page.evaluate(f"window.scrollTo(0, {position})")
                        
                        # Longer variable pauses as if reading the content
                        read_time = random.uniform(0.8, 2.5)
                        await asyncio.sleep(read_time)
                        
                        # Sometimes go back up slightly as if re-reading
                        if random.random() > 0.8:
                            up_amount = random.randint(30, 70)
                            await self.page.evaluate(f"window.scrollTo(0, {position - up_amount})")
                            await asyncio.sleep(random.uniform(0.5, 1.0))
                            await self.page.evaluate(f"window.scrollTo(0, {position})")
                            await asyncio.sleep(random.uniform(0.3, 0.7))
                
                elif scroll_style == "variable":
                    # Variable speed scrolling with irregular pauses
                    scroll_positions = []
                    while current_position < scroll_height:
                        # Highly variable scroll amounts
                        scroll_amount = random.randint(80, 350)
                        current_position += scroll_amount
                        if current_position > scroll_height:
                            current_position = scroll_height
                        scroll_positions.append(current_position)
                    
                    # Execute scrolls with variable timing
                    for position in scroll_positions:
                        await self.page.evaluate(f"window.scrollTo(0, {position})")
                        
                        # Highly variable pauses
                        pause_time = random.choice([
                            random.uniform(0.1, 0.3),    # Quick glance
                            random.uniform(0.5, 1.2),    # Brief read
                            random.uniform(1.5, 2.5)     # Careful read
                        ])
                        await asyncio.sleep(pause_time)
                
                else:  # jumpy scrolling for impatient persona
                    # Large, jumpy scrolls
                    num_jumps = random.randint(2, 4)
                    for _ in range(num_jumps):
                        # Big jumps
                        jump_position = random.randint(
                            int(scroll_height * 0.2),
                            int(scroll_height * 0.9)
                        )
                        await self.page.evaluate(f"window.scrollTo(0, {jump_position})")
                        await asyncio.sleep(random.uniform(0.3, 0.8))
            
                # NEW: Sometimes scroll back to the top before continuing
                if random.random() > 0.7:
                    await self.page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # NEW: Interactive mouse movements over search results with improved realism
            try:
                # Find search result containers
                result_selectors = [
                    "div.g", "div.yuRUbf > a", "h3.LC20lb", 
                    "a[ping]", "div[data-sokoban-container]",
                    ".MjjYud", ".v7W49e", "div[jscontroller]"
                ]
                
                for selector in result_selectors:
                    results = await self.page.query_selector_all(selector)
                    if results and len(results) > 0:
                        # For thorough personas, examine more results; for impatient ones, fewer
                        num_to_examine = {
                            "methodical": random.randint(3, 5),
                            "skimmer": random.randint(1, 3),
                            "researcher": random.randint(4, 7),
                            "casual": random.randint(2, 4),
                            "impatient": random.randint(1, 2)
                        }[persona]
                        
                        # Choose random results to examine (weighted toward the top)
                        weighted_indices = []
                        for i in range(min(10, len(results))):
                            # Add index multiple times based on position (more weight to top results)
                            weight = max(1, 10 - i)  # Higher weight for earlier results
                            weighted_indices.extend([i] * weight)
                        
                        examined_indices = set()
                        for _ in range(min(num_to_examine, len(results))):
                            if not weighted_indices:
                                break
                            idx = random.choice(weighted_indices)
                            # Remove all occurrences of this index
                            weighted_indices = [i for i in weighted_indices if i != idx]
                            if idx not in examined_indices:
                                examined_indices.add(idx)
                                result = results[idx]
                                
                                # Get element position
                                box = await result.bounding_box()
                                if box:
                                    # First make sure element is in view
                                    await self.page.evaluate(f"""
                                        window.scrollTo({{
                                            top: {max(0, box['y'] - 100)},
                                            behavior: 'smooth'
                                        }})
                                    """)
                                    await asyncio.sleep(random.uniform(0.2, 0.5))
                                    
                                    # Get current mouse position
                                    current_pos = await self.page.evaluate("""
                                        () => { 
                                            return {
                                                x: window.mouseX || window.innerWidth/2,
                                                y: window.mouseY || window.innerHeight/3
                                            }
                                        }
                                    """)
                                    start_x = current_pos.get('x', width/2)
                                    start_y = current_pos.get('y', height/3)
                                    
                                    # Choose a point in the element to move to
                                    target_x = box['x'] + box['width'] * random.uniform(0.1, 0.9)
                                    target_y = box['y'] + box['height'] * random.uniform(0.1, 0.9)
                                    
                                    # Define control points for bezier curve
                                    cp1x = start_x + (target_x - start_x) * random.uniform(0.2, 0.4)
                                    cp1y = start_y + (target_y - start_y) * random.uniform(0.1, 0.3)
                                    cp2x = start_x + (target_x - start_x) * random.uniform(0.6, 0.8)
                                    cp2y = start_y + (target_y - start_y) * random.uniform(0.7, 0.9)
                                    
                                    # Number of steps based on distance and persona
                                    distance = ((target_x - start_x)**2 + (target_y - start_y)**2)**0.5
                                    base_steps = max(4, min(12, int(distance / 50)))
                                    steps = {
                                        "methodical": base_steps + random.randint(2, 4),
                                        "skimmer": base_steps - random.randint(1, 2),
                                        "researcher": base_steps + random.randint(1, 3),
                                        "casual": base_steps,
                                        "impatient": max(3, base_steps - random.randint(2, 3))
                                    }[persona]
                                    
                                    # Simulate human-like mouse movement with bezier curve
                                    for step in range(steps + 1):
                                        t = step / steps
                                        # Cubic bezier curve
                                        x = (1-t)**3 * start_x + 3*(1-t)**2 * t * cp1x + 3*(1-t) * t**2 * cp2x + t**3 * target_x
                                        y = (1-t)**3 * start_y + 3*(1-t)**2 * t * cp1y + 3*(1-t) * t**2 * cp2y + t**3 * target_y
                                        
                                        # Add natural hand shakiness
                                        shake_factor = {
                                            "methodical": 0.7,
                                            "skimmer": 1.5,
                                            "researcher": 1.0,
                                            "casual": 1.2,
                                            "impatient": 2.0
                                        }[persona]
                                        
                                        if 0 < step < steps:
                                            x += random.uniform(-shake_factor, shake_factor)
                                            y += random.uniform(-shake_factor, shake_factor)
                                        
                                        # Move mouse
                                        await self.page.mouse.move(x, y)
                                        
                                        # Variable speed throughout motion
                                        if step == 0 or step == steps:
                                            # Slower at the very beginning and end
                                            await asyncio.sleep(random.uniform(0.03, 0.06))
                                        elif step < steps / 4 or step > 3 * steps / 4:
                                            # Still somewhat slow near beginning/end
                                            await asyncio.sleep(random.uniform(0.02, 0.04))
                                        else:
                                            # Faster in the middle of the motion
                                            await asyncio.sleep(random.uniform(0.01, 0.03))
                                    
                                    # Hover for a moment
                                    hover_time = {
                                        "methodical": random.uniform(0.8, 2.0),
                                        "skimmer": random.uniform(0.2, 0.6),
                                        "researcher": random.uniform(1.0, 2.5),
                                        "casual": random.uniform(0.5, 1.5),
                                        "impatient": random.uniform(0.1, 0.4)
                                    }[persona]
                                    await asyncio.sleep(hover_time)
                                    
                                    # Sometimes click on the result (but don't actually navigate)
                                    if random.random() < 0.1:
                                        await self.page.mouse.click(target_x, target_y, button='left', clickCount=1, delay=50)
                                        # After click, wait briefly then press browser back (simulating an actual navigation)
                                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        # After examining results, break out of the selectors loop
                        break
            
            except Exception as e:
                logger.debug(f"Error during result interaction: {e}")
            
            # NEW: Occasionally interact with search filters or tools
            if random.random() > 0.75:
                filter_selectors = [
                    ".MUFPAc", ".t2vtad", ".hdtb-mitem"
                ]
                
                for selector in filter_selectors:
                    try:
                        filters = await self.page.query_selector_all(selector)
                        if filters and len(filters) > 0:
                            # Pick a random filter
                            filter_elem = random.choice(filters)
                            box = await filter_elem.bounding_box()
                            
                            if box:
                                # Move to the element
                                await self.page.mouse.move(
                                    box['x'] + box['width']/2, 
                                    box['y'] + box['height']/2
                                )
                                await asyncio.sleep(random.uniform(0.3, 0.7))
                                
                                # Usually just hover, occasionally click
                                if random.random() < 0.3:
                                    await self.page.mouse.click(
                                        box['x'] + box['width']/2, 
                                        box['y'] + box['height']/2
                                    )
                                    await asyncio.sleep(random.uniform(0.5, 1.0))
                            
                            # Just try one filter interaction
                            break
                    except Exception as e:
                        logger.debug(f"Error interacting with filters: {e}")
            
            # Final random pause
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logger.warning(f"Error in human browsing simulation: {e}")
            logger.debug(traceback.format_exc())

    async def _detect_captcha(self):
        """Check if the current page contains a CAPTCHA or other security checks.
        
        Returns:
            bool: True if a CAPTCHA or security check is detected, False otherwise.
        """
        if not self.page:
            return False
            
        try:
            # Take a screenshot for debugging
            if self.debug_mode:
                try:
                    await self.page.screenshot(path=f"debug_html/captcha_check_{int(time.time())}.png")
                except Exception:
                    pass
            
            # Check URL for CAPTCHA and security check indicators
            # Enhanced with more Google-specific patterns
            current_url = self.page.url
            security_url_indicators = [
                # Standard CAPTCHA indicators
                "captcha", "recaptcha", "challenge", "security-check", 
                "verify", "unusual_traffic", "sorry/index", "consent.google",
                
                # Google-specific security pages
                "ipv4.google", "accounts.google", "/sorry/", "/interstitial",
                "iplookup", "safetylock", "block_session", "google.com/sorry",
                
                # Additional Google security mechanisms
                "google.com/accounts/recovery", "support.google.com/websearch",
                "ipv6.google", "signin/v2/challenge", "g-recaptcha", 
                "www.google.com/tools/feedback", "consent.youtube.com",
                
                # New patterns for silent security mechanisms
                "search-sentinel", "ap/drt", "verified-access", "google.com/gen_204",
                "client_204", "ctxs", "checkConnection", "g-recaptcha-response",
                "captchaPerimeter", "sitekey", "gws_rd", "pwa-mirror"
            ]
            
            for indicator in security_url_indicators:
                if indicator in current_url.lower():
                    logger.warning(f"Security check likely - URL contains '{indicator}'")
                    return True
            
            # Check HTTP response status
            response = await self.page.evaluate("""
                () => {
                    try {
                        const entries = window.performance.getEntries();
                        for (const entry of entries) {
                            if (entry.name === window.location.href && entry.responseStatus) {
                                return entry.responseStatus;
                            }
                        }
                        return null;
                    } catch (e) {
                        return null;
                    }
                }
            """)
            
            if response in [403, 429, 503]:
                logger.warning(f"Security check indicated by HTTP status {response}")
                return True
            
            # Improved comprehensive page content analysis covering Google-specific cases
            security_detected = await self.page.evaluate("""
                () => {
                    // Helper to get visible text
                    const getVisibleText = () => {
                        // Get all text nodes
                        const textNodes = [];
                        const walk = document.createTreeWalker(
                            document.body, 
                            NodeFilter.SHOW_TEXT, 
                            null, 
                            false
                        );
                        
                        let node;
                        while(node = walk.nextNode()) {
                            // Skip nodes with no text or hidden elements
                            if (node.textContent.trim() !== '' && 
                                !isHidden(node.parentElement)) {
                                textNodes.push(node.textContent.trim());
                            }
                        }
                        
                        return textNodes.join(' ').toLowerCase();
                    };
                    
                    // Helper to check if an element is hidden
                    const isHidden = (el) => {
                        if (!el) return true;
                        
                        const style = window.getComputedStyle(el);
                        return style.display === 'none' || 
                               style.visibility === 'hidden' || 
                               style.opacity === '0' ||
                               el.offsetParent === null;
                    };
                    
                    // Get all visible text in the page
                    const pageText = getVisibleText();
                    
                    // Check page title - Google often changes the title for security pages
                    const pageTitle = document.title.toLowerCase();
                    const suspiciousTitles = [
                        'unusual traffic', 'verify', 'robot check', 'captcha',
                        'security check', 'sorry', 'security alert', 'confirm',
                        'automated queries', 'blocked', 'error'
                    ];
                    
                    for (const title of suspiciousTitles) {
                        if (pageTitle.includes(title)) {
                            return {
                                detected: true,
                                reason: `Suspicious page title: "${title}"`,
                                type: "title"
                            };
                        }
                    }
                    
                    // Enhanced list of security check indicators specific to Google
                    const securityPhrases = [
                        // Standard CAPTCHA indicators
                        "captcha", "i'm not a robot", "verify you are human", 
                        "human verification", "robot verification", "bot check",
                        
                        // Traffic/behavior indicators
                        "unusual traffic", "suspicious activity", "unusual activity",
                        "automated queries", "automated access", "too many requests",
                        "unusual amount of traffic", "high volume", "traffic from your network",
                        
                        // Google-specific messages 
                        "our systems have detected unusual traffic",
                        "your computer or network may be sending automated queries",
                        "before continuing to google search",
                        "sending automated queries to google",
                        "restricted or unavailable",
                        "please try your request again",
                        "we can't process your request",
                        "sign in to continue to google search",
                        "page may be temporarily unavailable",
                        "confirm you're not a robot",
                        "something about your browser made us think you were a robot",
                        "solving the captcha below proves you're a person",
                        "to continue, please type the characters below",
                        "to continue, please allow cookies in your browser settings",
                        "to get back on track, solve the puzzle below",
                        "coming from your network looks suspicious",
                        "we've detected suspicious activity",
                        "enter the letters you see in the image",
                        "this page checks to see",
                        "this page appears when google automatically detects",
                        "enter the characters",
                        "ip address",
                        "enter the code",
                        "contact the website owner",
                        "press and hold",
                        "search the web for"
                    ];
                    
                    // Check each security phrase
                    for (const phrase of securityPhrases) {
                        if (pageText.includes(phrase)) {
                            return {
                                detected: true,
                                reason: `Text contains: "${phrase}"`,
                                type: "text"
                            };
                        }
                    }
                    
                    // Google-specific CAPTCHA elements
                    const captchaSelectors = [
                        // Google reCAPTCHA elements
                        'iframe[src*="recaptcha"]',
                        'iframe[src*="captcha"]',
                        'div.g-recaptcha',
                        'div[class*="recaptcha"]',
                        'div[data-sitekey]',
                        'textarea[name="g-recaptcha-response"]',
                        'div#recaptcha',
                        'div.rc-anchor',
                        
                        // Google security page elements
                        'form[action*="ServiceLogin"]',
                        'div.fsa-eh',
                        'button#submit_approve_access',
                        'div#recaptcha-anchor',
                        'div.rc-anchor-container',
                        'div.rc-anchor',
                        'form#captcha-form',
                        'div#captcha',
                        'img[src*="captcha"]',
                        
                        // Google security checks
                        'form[action*="sorry"]',
                        'form[action*="interstitial"]',
                        'input[name="continue"]',
                        'form[id*="challenge"]',
                        'div[class*="challenge"]',
                        'div#verify-details',
                        'div#main-frame-error',
                        'div.error-code',
                        'div#error-information-popup-container',
                        'div.interstitial-wrapper',
                        
                        // Specific Google security form elements
                        '#Captcha',
                        '#captcha-box',
                        '#captcha-wrapper',
                        '#gs_captcha',
                        '.g-button-submit-challenge',
                        '.goog-inline-block.rc-button-reload',
                        'input[name="q"][disabled]',
                        'input[type="button"][value*="verify"]',
                        'input[type="button"][value*="continue"]'
                    ];
                    
                    // Check for any security-related elements
                    for (const selector of captchaSelectors) {
                        try {
                            const el = document.querySelector(selector);
                            if (el && !isHidden(el)) {
                                return {
                                    detected: true,
                                    reason: `Found element: "${selector}"`,
                                    type: "element"
                                };
                            }
                        } catch (e) {
                            // Ignore errors in selectors
                        }
                    }
                    
                    // Check Google-specific objects and functions in the page
                    if (
                        window.___grecaptcha_cfg ||
                        window.grecaptcha ||
                        window._submitform ||
                        window.recaptcha ||
                        window.HSW ||
                        window.botguard ||
                        window.__google_recaptcha_client
                    ) {
                        return {
                            detected: true,
                            reason: "Found CAPTCHA/security JavaScript objects",
                            type: "javascript"
                        };
                    }
                    
                    // Check for Google's security check form submissions
                    const checkForms = () => {
                        const forms = document.forms;
                        for (let i = 0; i < forms.length; i++) {
                            const form = forms[i];
                            
                            // Check form action
                            if (form.action && (
                                form.action.includes('/sorry/') ||
                                form.action.includes('ServiceLogin') ||
                                form.action.includes('accounts.google.com') ||
                                form.action.includes('challenge')
                            )) {
                                return true;
                            }
                            
                            // Check form elements and input names
                            const securityInputs = ['captcha', 'challenge', 'verify', 'token', 'g-recaptcha-response'];
                            for (const input of form.elements) {
                                if (input.name && securityInputs.some(name => input.name.includes(name))) {
                                    return true;
                                }
                            }
                        }
                        return false;
                    };
                    
                    if (checkForms()) {
                        return {
                            detected: true,
                            reason: "Security form detected",
                            type: "form"
                        };
                    }
                    
                    // Check for lack of expected search results
                    if (window.location.hostname.includes('google')) {
                        // A Google search page should have these elements
                        const hasSearchBox = document.querySelector('input[name="q"]') !== null;
                        const hasResults = document.querySelectorAll('#search .g, .MjjYud, div[data-sokoban-container], div.yuRUbf').length > 0;
                        const hasNextPage = document.querySelector('#pnnext') !== null;
                        const hasNoResultsMessage = pageText.includes('no results found') || pageText.includes('did not match any documents');
                        
                        // If we're on Google search but missing expected elements
                        if (hasSearchBox && !hasResults && !hasNoResultsMessage) {
                            // Check if the search box is disabled (common in security checks)
                            const searchBox = document.querySelector('input[name="q"]');
                            if (searchBox && (searchBox.disabled || searchBox.readOnly)) {
                                return {
                                    detected: true,
                                    reason: "Search box is disabled/readonly",
                                    type: "search_disabled"
                                };
                            }
                            
                            // It's a search page with no search results or error message
                            return {
                                detected: true,
                                reason: "Search page has no results and no error message",
                                type: "no_results"
                            };
                        }
                    }
                    
                    // No security features detected
                    return {
                        detected: false
                    };
                }
            """)
            
            if security_detected.get('detected', False):
                reason = security_detected.get('reason', 'Unknown')
                security_type = security_detected.get('type', 'Unknown')
                logger.warning(f"Security check detected: {reason} (Type: {security_type})")
                
                # Additional information for debugging
                if self.debug_mode:
                    try:
                        # Save the HTML for analysis
                        content = await self.page.content()
                        with open(f"debug_html/security_check_{int(time.time())}.html", "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        # Save page metadata
                        metadata = {
                            "url": self.page.url,
                            "title": await self.page.title(),
                            "reason": reason,
                            "type": security_type,
                            "time": datetime.now().isoformat()
                        }
                        
                        with open(f"debug_html/security_check_{int(time.time())}.json", "w", encoding="utf-8") as f:
                            json.dump(metadata, f, indent=2)
                    except Exception as e:
                        logger.error(f"Error saving security check debug info: {e}")
                
                return True
            
            # Final check: Look for severe layout changes in Google
            layout_check = await self.page.evaluate("""
                () => {
                    // Only apply this check on Google domains
                    if (!window.location.hostname.includes('google')) {
                        return false;
                    }
                    
                    try {
                        // Google search results should have certain layout characteristics
                        const mainSearchContent = document.querySelector('#main, #center_col, #res, #search');
                        if (!mainSearchContent) {
                            return true; // Missing main content containers
                        }
                        
                        // Check for the presence of sidebars/navigation that should be there
                        const hasCommonElements = 
                            document.querySelector('input[name="q"]') || // Search box
                            document.querySelector('#appbar, #hdtb, .hdtb-mitem') || // Navigation bar
                            document.querySelector('#foot, #footer, #footcnt'); // Footer
                        
                        if (!hasCommonElements) {
                            return true; // Suspicious absence of common elements
                        }
                        
                        // Check for interstitial elements that take over the page
                        const hasInterstitial = 
                            document.querySelector('.interstitial-wrapper, #main-frame-error, #error-information-popup-container') ||
                            document.querySelector('form[action*="/sorry/"]') ||
                            document.body.innerHTML.length < 5000; // Suspiciously short page
                        
                        return hasInterstitial;
                    } catch (e) {
                        return false;
                    }
                }
            """)
            
            if layout_check:
                logger.warning("Detected abnormal Google page layout, likely a security page")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in security check detection: {e}")
            logger.error(traceback.format_exc())
            # If we can't check properly, assume it might be a security check
            return True

    async def _detect_no_results_message(self):
        """Check if the page contains a 'no results found' message."""
        try:
            # Check for common phrases indicating no results
            no_results_text = await self.page.evaluate("""
                () => {
                    const searchElement = document.getElementById('search') || 
                                          document.getElementById('center_col') ||
                                          document.getElementById('res');
                                          
                    if (!searchElement) return '';
                    return searchElement.innerText.toLowerCase();
                }
            """)
            
            # Phrases that indicate no results in various languages
            no_results_indicators = [
                'no results found',
                'did not match any documents',
                'your search did not match any documents',
                'no information is available',
                'не найдено ни одного документа',  # Russian
                'no se ha encontrado ningún resultado',  # Spanish
                'aucun document ne correspond',  # French
                '找不到', # Chinese
                '見つかりません'  # Japanese
            ]
            
            if no_results_text and any(indicator in no_results_text for indicator in no_results_indicators):
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking for no results message: {e}")
            return False
            
    async def _extract_search_results(self):
        """Extract search result URLs from the current page."""
        try:
            # Extract URLs using JavaScript
            page_results = await self.page.evaluate("""
                () => {
                    // Helper to normalize URLs
                    const normalizeUrl = (url) => {
                        try {
                            if (!url) return '';
                            
                            // Basic URL cleaning
                            if (url.startsWith('https://www.google.com/url?') || 
                                url.startsWith('https://www.google.co.in/url?')) {
                                // Extract destination URL from Google's redirect
                                const urlParams = new URLSearchParams(url.split('?')[1]);
                                const actualUrl = urlParams.get('url') || urlParams.get('q');
                                if (actualUrl) return actualUrl;
                            }
                            
                            // Remove tracking parameters
                            if (url.includes('?')) {
                                const [baseUrl, params] = url.split('?');
                                // Keep only essential parameters
                                const essentialParams = params.split('&').filter(param => {
                                    const paramName = param.split('=')[0].toLowerCase();
                                    return !['utm_', 'ref', 'source', 'fbclid', 'gclid', 'msclkid'].some(
                                        prefix => paramName.startsWith(prefix)
                                    );
                                });
                                
                                return essentialParams.length > 0 ? 
                                    `${baseUrl}?${essentialParams.join('&')}` : baseUrl;
                            }
                            return url;
                        } catch (e) {
                            return url || '';
                        }
                    };
                    
                    // Comprehensive selectors for finding result links
                    const selectors = [
                        // Main result links
                        'div.yuRUbf > a',
                        'div[data-snc] a',
                        'div[data-sokoban-container] a',
                        '.g .yuRUbf a',
                        '.MjjYud .yuRUbf a',
                        '.DKV0Md a',
                        '.g a',
                        'a[ping]',
                        'a[data-ved]',
                        '#search a[href^="http"]:not([href*="google"])'
                    ];
                    
                    // Set to track seen URLs
                    const seenUrls = new Set();
                    const results = [];
                    
                    // Collect URLs from each selector
                    for (const selector of selectors) {
                        try {
                            document.querySelectorAll(selector).forEach(element => {
                                // Only process elements that look like real search results
                                const isSearchResult = 
                                    element.closest('#search') || 
                                    element.closest('#center_col') || 
                                    element.closest('#res');
                                
                                // Skip navigation elements
                                const isNavigation = 
                                    element.closest('#top_nav') ||
                                    element.closest('#hdtb') ||
                                    element.closest('#appbar') ||
                                    element.closest('footer') ||
                                    element.closest('#footcnt');
                                
                                if (isSearchResult && !isNavigation) {
                                    const href = element.href;
                                    if (href && 
                                        href.startsWith('http') && 
                                        !href.includes('google.') &&
                                        !href.includes('youtube.com/watch') &&
                                        !href.includes('maps.google.') &&
                                        !seenUrls.has(href)) {
                                        
                                        seenUrls.add(href);
                                        results.push(normalizeUrl(href));
                                    }
                                }
                            });
                        } catch (e) {
                            console.error(`Error with selector ${selector}:`, e);
                        }
                    }
                    
                    return results;
                }
            """)
            
            # Filter results - basic URL validation
            filtered_results = []
            for url in page_results:
                if not url or not isinstance(url, str):
                    continue
                    
                # Basic URL validation
                if not url.startswith('http'):
                    continue
                
                try:
                    # Parse URL to get domain
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()
                    
                    # Skip Google-owned domains and other non-relevant results
                    skip_domains = [
                        'google.', 'youtube.com', 'blogger.com', 'blogspot.',
                        'googleusercontent.', 'doubleclick.net', 'gstatic.com',
                        'googlesyndication.com', 'amp.dev', 'ampproject.org'
                    ]
                    
                    if any(skip_domain in domain for skip_domain in skip_domains):
                        continue
                        
                    # Add to filtered results if not already present
                    if url not in filtered_results:
                        filtered_results.append(url)
                        
                except Exception as url_error:
                    logger.debug(f"Error processing URL {url}: {url_error}")
                    continue
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
            return []

    async def search_google(self, query: str, num_results: int = 10, page: int = 0) -> List[str]:
        """
        Perform a Google search using browser automation with advanced evasion techniques.
        
        Args:
            query: The search query string
            num_results: Maximum number of results to return
            page: Page number (0-indexed)
            
        Returns:
            List of result URLs
        """
        # Auto-correct common spelling mistakes in the query
        common_misspellings = {
            "wholeseller": "wholesaler",
            "wholesellers": "wholesalers",
            "manufacturor": "manufacturer",
            "manufacturors": "manufacturers",
            "distributer": "distributor",
            "distributers": "distributors",
            "suplier": "supplier",
            "supliers": "suppliers"
        }
        
        corrected_query = query
        for misspelling, correction in common_misspellings.items():
            corrected_query = corrected_query.replace(misspelling, correction)
            
        if corrected_query != query:
            logger.info(f"Corrected query from '{query}' to '{corrected_query}'")
            query = corrected_query
        
        # Initialize browser if needed
        if not self.browser_initialized:
            success = await self.initialize_browser()
            if not success:
                logger.error("Failed to initialize browser")
                return []
        
        results = []
        start_index = page * 10
        
        # Format the query using advanced techniques
        query_variations = []
        
        # Default variation: If site:.in not already specified, add it for Indian results
        if 'site:' not in query:
            query_variations.append(f'"{query}" site:.in')
        else:
            query_variations.append(query)
            
        # Alternative variation: Without quotes - sometimes helps with different results
        if 'site:' not in query:
            query_variations.append(f'{query} site:.in')
        else:
            query_variations.append(query.replace('"', ''))
            
        # Another variation: Use .com suffix for broader results in case .in has issues
        if 'site:' not in query:
            query_variations.append(f'"{query}"')
        
        logger.info(f"Using query variations: {query_variations}")
        
        # Try each query variation until we get results
        for search_query in query_variations:
            # Create Google search URL with parameters designed to avoid personalization and tracking
            google_domains = [
                "google.co.in",  # Primary: Indian Google
                "google.com",     # Secondary: Global Google
            ]
            
            # Try different Google domains
            for google_domain in google_domains:
                # Create custom parameters for this attempt
                params = {
                    "q": quote(search_query),
                    "start": start_index,
                    "gl": "in",            # Geo-location: India
                    "hl": "en-IN",         # Language: Indian English
                    "pws": "0",            # Personalized Web Search: Off
                    "filter": "0",         # Filter duplicate results: Off
                    "nfpr": "1",           # No auto-correction of search terms
                    "safe": "active",      # Safe search setting
                    "sourceid": "chrome",  # Pretend to be Chrome browser
                    "ie": "UTF-8",         # Input encoding
                    "oe": "UTF-8",         # Output encoding
                    "num": min(20, num_results * 2)  # Request more results than needed to account for filtering
                }
                
                # Add small parameter variations to appear more organic
                if random.random() > 0.5:
                    params["adtest"] = "off"  # Disable test ads
                
                # Build URL with parameters
                param_string = "&".join([f"{k}={v}" for k, v in params.items()])
                google_url = f"https://www.{google_domain}/search?{param_string}"
                
                logger.info(f"Searching Google: {google_url}")
                
                try:
                    # Randomized pre-search delay
                    delay_time = random.uniform(2, 5)
                    logger.debug(f"Adding pre-search delay of {delay_time:.2f}s")
                    await asyncio.sleep(delay_time)
                    
                    # Navigate directly to search URL
                    try:
                        response = await self.page.goto(google_url, wait_until="domcontentloaded", timeout=60000)
                        
                        # Save debug screenshot
                        if self.debug_mode:
                            try:
                                await self.page.screenshot(path=f"debug_html/google_search_{int(time.time())}.png")
                            except Exception:
                                pass
                            
                        # Check if Google blocked our request
                        is_security_check = await self._detect_security_check()
                        if is_security_check:
                            logger.warning(f"Google security check detected for query: {search_query}. Saving screenshot.")
                            timestamp = int(time.time())
                            await self.page.screenshot(path=f"google_captcha_{timestamp}.png")
                            
                            # Try with a different variation/domain
                            continue
                            
                        # Check for no results message
                        no_results = await self._detect_no_results_message()
                        if no_results:
                            logger.warning(f"No results found in the page - error type: no_results_message")
                            continue
                            
                        # Extract URLs from the page
                        extracted_results = await self._extract_search_results()
                        
                        # Log the number of results found
                        logger.info(f"Found {len(extracted_results)} results for query '{search_query}' on {google_domain}")
                        
                        # Filter results
                        filtered_results = extracted_results
                        
                        # If we found results after filtering, return them
                        if filtered_results:
                            results.extend(filtered_results)
                            # Break both domain and query loops
                            break
                            
                    except PlaywrightTimeoutError:
                        logger.warning(f"Timeout waiting for Google search results on {google_domain}")
                        timestamp = int(time.time())
                        try:
                            await self.page.screenshot(path=f"google_timeout_{timestamp}.png")
                        except:
                            pass
                        continue
                    except Exception as e:
                        logger.error(f"Error navigating to Google: {e}")
                        continue
                    
                except Exception as e:
                    logger.error(f"Error performing Google search: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Save page for debugging
                    if self.debug_mode:
                        try:
                            await self.page.screenshot(path=f"debug_html/google_error_{int(time.time())}.png")
                            content = await self.page.content()
                            with open(f"debug_html/google_error_{int(time.time())}.html", "w", encoding="utf-8") as f:
                                f.write(content)
                        except Exception:
                            pass
            
            # If we got results from this query variation, break the loop
            if results:
                break

        # De-duplicate results in case of overlapping
        unique_results = []
        seen_domains = set()
        
        # First pass: Get unique URLs
        for url in results:
            if url not in unique_results:
                unique_results.append(url)
        
        return unique_results[:num_results]

    async def close(self):
        """Close browser and clean up resources."""
        await self._cleanup_resources()

    async def _detect_security_check(self):
        """Detect if the current page contains a security check or CAPTCHA."""
        try:
            # Check for security elements via JavaScript
            has_security = await self.page.evaluate("""
                () => {
                    // Common security check elements
                    const securitySelectors = [
                        'form#captcha-form', 
                        'iframe[src*="recaptcha"]', 
                        'iframe[src*="captcha"]',
                        'div.g-recaptcha', 
                        'input[name="g-recaptcha-response"]',
                        'form[action*="/sorry/"]', 
                        'div#recaptcha-anchor',
                        '#captcha'
                    ];
                    
                    // Check if any security element exists
                    for (const selector of securitySelectors) {
                        if (document.querySelector(selector)) {
                            return true;
                        }
                    }
                    
                    // Check for text indicators in the page content
                    const bodyText = document.body.innerText.toLowerCase();
                    const securityPhrases = [
                        'unusual traffic',
                        'suspicious activity',
                        'automated queries',
                        'solve this puzzle',
                        'security check',
                        'captcha',
                        'human verification',
                        'verify you are a human',
                        'robot check',
                        'bot check',
                        'we apologize for the inconvenience',
                        'our systems have detected unusual traffic',
                        'your computer or network may be sending automated queries'
                    ];
                    
                    return securityPhrases.some(phrase => bodyText.includes(phrase));
                }
            """);
            
            if has_security:
                logger.warning("Security check detected on Google")
                return True
                
            # Check for unusual page layout, which might indicate a security page
            layout_check = await self.page.evaluate("""
                () => {
                    // Normal Google search results page should have these elements
                    const hasSearchBox = !!document.querySelector('input[name="q"]');
                    const hasResults = !!document.querySelector('#search') || 
                                       !!document.querySelector('#center_col') ||
                                       !!document.querySelector('#rso');
                    const hasNavigation = !!document.querySelector('#hdtb') || 
                                          !!document.querySelector('#appbar');
                                          
                    // If the page has a search box but no results or navigation,
                    // it's likely a security check or an unusual page
                    return hasSearchBox && (!hasResults || !hasNavigation);
                }
            """);
            
            if layout_check:
                logger.warning("Detected abnormal Google page layout, likely a security page")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in security check detection: {e}")
            logger.error(traceback.format_exc())
            # If we can't check properly, assume it might be a security check
            return True

# Synchronous wrapper function for the Google search
def search_google(query: str, num_results: int = 10, page: int = 0, debug_mode: bool = False) -> List[str]:
    """
    Perform a Google search using browser automation (synchronous API).
    
    Args:
        query: The search query string
        num_results: Maximum number of results to return
        page: Page number (0-indexed)
        debug_mode: Whether to save screenshots and debug info
        
    Returns:
        List of result URLs
    """
    async def _run_search():
        search = GoogleBrowserSearch(debug_mode=debug_mode)
        try:
            return await search.search_google(query, num_results, page)
        finally:
            await search.close()
    
    # Check if we're already in an event loop to avoid nested loop errors
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in a running event loop, create a new one in a separate thread
            nest_asyncio.apply()
    except RuntimeError:
        # No event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_run_search())
    except Exception as e:
        logger.error(f"Error in search_google: {e}")
        logger.error(traceback.format_exc())
        return []

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        query = sys.argv[1]
        results = search_google(query, debug_mode=True)
        print(f"Found {len(results)} results:")
        for i, url in enumerate(results, 1):
            print(f"{i}. {url}")
    else:
        print("Usage: python google_browser_search.py 'your search query'") 