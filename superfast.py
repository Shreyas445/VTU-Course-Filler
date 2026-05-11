import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from background_activity import BackgroundLogger

CREDENTIALS_FILE = "credentials.json"

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        default_creds = {
            "email": "your_email@gmail.com",
            "password": "your_password"
        }
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(default_creds, f, indent=4)
        print(f"Created {CREDENTIALS_FILE}. Please fill in your email and password, then restart.")
        exit()

    with open(CREDENTIALS_FILE, "r") as f:
        creds = json.load(f)

    if creds["email"] == "your_email@gmail.com":
        print(f"Please update {CREDENTIALS_FILE} with your actual VTU credentials!")
        exit()

    return creds


def get_js_hook():
    """
    SUPERFAST hook — completely different architecture from fast.py.

    fast.py waits for the WEBSITE to send POST /progress (~30 seconds).
    superfast.py intercepts GET /lectures/{id} (instant on click) + YouTube play detection.

    How it works:
    1. Hooks fetch to intercept GET /lectures/{id} responses → extracts lecture ID + duration
    2. Listens for YouTube postMessage → detects when video starts playing
    3. After 5 seconds of play → immediately starts its own heartbeat loop
    4. Sequential heartbeats, one at a time, with configurable speed
    """
    return """
    if (!window.__vtu_hooked) {
        window.__vtu_hooked = true;
        window.__vtu_done = {};
        window.__vtu_log = [];

        function addLog(msg) {
            var ts = new Date().toLocaleTimeString();
            var line = '[' + ts + '] ' + msg;
            console.log(line);
            window.__vtu_log.push(line);
        }

        /* ── Inject CSS ── */
        var style = document.createElement('style');
        style.textContent = [
            '@keyframes vtuSlideUp { from{transform:translateY(100%);opacity:0} to{transform:translateY(0);opacity:1} }',
            '@keyframes vtuDot { 0%,80%,100%{opacity:0.3} 40%{opacity:1} }'
        ].join(' ');
        document.head.appendChild(style);

        /* ── Slim bottom-center bar ── */
        var panel = document.createElement('div');
        panel.id = '__vtu_panel';
        panel.style.cssText = [
            'position:fixed',
            'bottom:12px',
            'left:50%',
            'transform:translateX(-50%)',
            'height:44px',
            'min-width:420px',
            'max-width:620px',
            'background:rgba(15,15,30,0.92)',
            'color:#ccc',
            'padding:0 20px',
            'z-index:999999',
            'border-radius:22px',
            'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif',
            'font-size:13px',
            'display:flex',
            'align-items:center',
            'gap:12px',
            'box-shadow:0 4px 24px rgba(0,0,0,0.4)',
            'border:1px solid rgba(255,255,255,0.08)',
            'animation:vtuSlideUp 0.3s ease-out',
            'backdrop-filter:blur(12px)',
            '-webkit-backdrop-filter:blur(12px)'
        ].join(';');

        panel.innerHTML = [
            '<div id="__vtu_dot" style="width:8px;height:8px;border-radius:50%;background:#64b5f6;flex-shrink:0;"></div>',
            '<div id="__vtu_body" style="flex:1;display:flex;align-items:center;gap:10px;white-space:nowrap;overflow:hidden;">',
            '  <span style="font-weight:600;color:#fff;font-size:12px;">SUPERFAST Mode</span>',
            '  <span style="color:rgba(255,255,255,0.35);font-size:12px;">Click a lecture, then press play</span>',
            '</div>'
        ].join('');
        document.body.appendChild(panel);

        function setPanel(state, data) {
            var body = document.getElementById('__vtu_body');
            var dot = document.getElementById('__vtu_dot');
            if (!body) return;

            if (state === 'waiting') {
                if (dot) dot.style.background = '#ab47bc';
                body.innerHTML = [
                    '<span style="font-weight:600;color:#ab47bc;font-size:12px;">Lec ' + data.id + ' ready</span>',
                    '<span style="color:rgba(255,255,255,0.35);font-size:12px;">Press play to start (' + data.mins + 'min video)</span>'
                ].join('');
            }

            else if (state === 'countdown') {
                if (dot) dot.style.background = '#ffa726';
                body.innerHTML = [
                    '<span style="font-weight:600;color:#ffa726;font-size:12px;">Lec ' + data.id + '</span>',
                    '<span style="color:rgba(255,255,255,0.5);font-size:12px;">Starting in ' + data.sec + 's...</span>'
                ].join('');
            }

            else if (state === 'syncing') {
                var hasErrors = (data.errors || 0) > 0;
                var barColor = hasErrors ? 'linear-gradient(90deg,#e65100,#ff9800)' : 'linear-gradient(90deg,#7c4dff,#448aff)';
                var pctColor = hasErrors ? '#ff9800' : '#448aff';
                var dotColor = hasErrors ? '#ff9800' : '#7c4dff';
                if (dot) dot.style.background = dotColor;
                var pct = data.pct || 0;
                body.innerHTML = [
                    '<span style="font-weight:600;color:#fff;font-size:12px;">Lec ' + data.id + '</span>',
                    '<div style="flex:1;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;min-width:80px;overflow:hidden;">',
                    '  <div style="width:' + pct + '%;height:100%;background:' + barColor + ';border-radius:2px;transition:width 0.3s ease;"></div>',
                    '</div>',
                    '<span style="font-weight:700;color:' + pctColor + ';font-size:13px;min-width:36px;text-align:right;">' + pct + '%</span>',
                    hasErrors ? '<span style="color:#ef5350;font-size:11px;">' + data.errors + ' err</span>' : '<span style="color:rgba(255,255,255,0.3);font-size:11px;">' + data.mins + 'min</span>',
                    '<span style="display:flex;gap:3px;align-items:center;">',
                    '  <span style="width:4px;height:4px;border-radius:50%;background:' + dotColor + ';animation:vtuDot 1.2s infinite 0s;"></span>',
                    '  <span style="width:4px;height:4px;border-radius:50%;background:' + dotColor + ';animation:vtuDot 1.2s infinite 0.2s;"></span>',
                    '  <span style="width:4px;height:4px;border-radius:50%;background:' + dotColor + ';animation:vtuDot 1.2s infinite 0.4s;"></span>',
                    '</span>'
                ].join('');
            }

            else if (state === 'done') {
                var allFailed = data.errors > 0 && data.sent === 0;
                var partial = data.errors > 0 && data.sent > 0;
                if (allFailed) {
                    if (dot) dot.style.background = '#ef5350';
                    body.innerHTML = [
                        '<span style="color:#ef5350;font-size:14px;">&#10007;</span>',
                        '<span style="font-weight:600;color:#ef5350;font-size:12px;">Lec ' + data.id + ' Failed</span>',
                        '<span style="color:rgba(255,255,255,0.4);font-size:11px;margin-left:auto;">Server error (VTU issue). Try later.</span>'
                    ].join('');
                } else if (partial) {
                    if (dot) dot.style.background = '#ff9800';
                    body.innerHTML = [
                        '<span style="color:#ff9800;font-size:14px;">&#9888;</span>',
                        '<span style="font-weight:600;color:#ff9800;font-size:12px;">Lec ' + data.id + ' Partial</span>',
                        '<span style="color:rgba(255,255,255,0.35);font-size:11px;">' + data.sent + ' ok, ' + data.errors + ' failed</span>',
                        '<span style="color:rgba(255,255,255,0.3);font-size:11px;margin-left:auto;">Unpause, then next video</span>'
                    ].join('');
                } else {
                    if (dot) dot.style.background = '#66bb6a';
                    body.innerHTML = [
                        '<span style="color:#66bb6a;font-size:14px;">&#10003;</span>',
                        '<span style="font-weight:600;color:#66bb6a;font-size:12px;">Lec ' + data.id + ' Complete</span>',
                        '<span style="color:rgba(255,255,255,0.35);font-size:11px;">' + data.mins + 'min synced</span>',
                        '<span style="color:rgba(255,255,255,0.3);font-size:11px;margin-left:auto;">Click next video</span>'
                    ].join('');
                }
            }

            else if (state === 'idle') {
                if (dot) dot.style.background = '#64b5f6';
                body.innerHTML = [
                    '<span style="font-weight:600;color:#fff;font-size:12px;">SUPERFAST Mode</span>',
                    '<span style="color:rgba(255,255,255,0.35);font-size:12px;">Click a lecture, then press play</span>'
                ].join('');
            }
        }

        /* ══════════════════════════════════════════════════════════
           PHASE 1: Intercept GET /lectures/{id} to extract info
           This fires INSTANTLY when user clicks a lecture
           ══════════════════════════════════════════════════════════ */
        var _origFetch = window.fetch;
        window.__vtu_lecture_info = null;   // {id, total, url, headers}
        window.__vtu_active = null;
        addLog('SUPERFAST hook installed. Click any lecture to begin.');

        window.fetch = async function() {
            var args = arguments;
            var url = typeof args[0] === 'string' ? args[0] : '';

            // ── Detect lecture GET: /lectures/{id} (NOT /progress, NOT /notes) ──
            if (url.indexOf('/lectures/') !== -1
                && url.indexOf('/progress') === -1
                && url.indexOf('/notes') === -1
                && (!args[1] || !args[1].method || args[1].method === 'GET')) {

                var lectureId = 'unknown';
                var parts = url.split('/');
                for (var i = 0; i < parts.length; i++) {
                    if (parts[i] === 'lectures' && i + 1 < parts.length) {
                        lectureId = parts[i + 1];
                        break;
                    }
                }

                // Cancel any old lecture loop
                if (window.__vtu_active && window.__vtu_active !== lectureId) {
                    addLog('Switched to Lecture ' + lectureId);
                }
                window.__vtu_active = lectureId;

                // Pass through the request, but read the response to get duration
                var response = await _origFetch.apply(this, args);
                try {
                    var clone = response.clone();
                    var data = await clone.json();

                    if (data && data.data) {
                        var lecData = data.data;
                        var total = 0;

                        // Try multiple possible fields for duration
                        if (lecData.total_duration_seconds) total = Math.floor(lecData.total_duration_seconds);
                        else if (lecData.duration_seconds) total = Math.floor(lecData.duration_seconds);
                        else if (lecData.duration) total = Math.floor(lecData.duration);
                        else if (lecData.video_duration) total = Math.floor(lecData.video_duration);

                        if (total > 0) {
                            // Build the progress URL from the lecture URL
                            var progressUrl = url + '/progress';

                            window.__vtu_lecture_info = {
                                id: lectureId,
                                total: total,
                                progressUrl: progressUrl,
                                mins: Math.round(total / 60)
                            };

                            addLog('Lecture ' + lectureId + ' loaded | Duration: ' + total + 's (' + window.__vtu_lecture_info.mins + 'min)');
                            setPanel('waiting', { id: lectureId, mins: window.__vtu_lecture_info.mins });
                        }
                    }
                } catch(e) {
                    // Couldn't parse response — not a JSON lecture response
                }
                return response;
            }

            // ── Also intercept POST /progress to hijack the response for UI ──
            if (url.indexOf('/progress') !== -1 && url.indexOf('lectures') !== -1) {
                var response;
                try {
                    response = await _origFetch.apply(this, args);
                } catch(e) {
                    return Promise.reject(e);
                }

                try {
                    var clone = response.clone();
                    var data = await clone.json();
                    var modified = false;
                    if (data && typeof data === 'object') {
                        if ('progress' in data) { data.progress = 100; modified = true; }
                        if ('progress_percent' in data) { data.progress_percent = 100; modified = true; }
                        if ('progress_bar' in data) { data.progress_bar = 100; modified = true; }
                        if ('percentage' in data) { data.percentage = 100; modified = true; }
                        if ('completed' in data) { data.completed = true; modified = true; }
                        if (modified) {
                            return new Response(JSON.stringify(data), {
                                status: response.status,
                                statusText: response.statusText,
                                headers: response.headers
                            });
                        }
                    }
                } catch(e) {}
                return response;
            }

            return _origFetch.apply(this, args);
        };

        /* ══════════════════════════════════════════════════════════
           PHASE 2: YouTube play detection via postMessage
           YouTube sends state changes when enablejsapi=1
           State 1 = PLAYING
           ══════════════════════════════════════════════════════════ */
        window.addEventListener('message', function(event) {
            try {
                var msg = JSON.parse(event.data);
                var playing = false;

                // YouTube sends: {"event":"onStateChange","info":1}
                if (msg.event === 'onStateChange' && msg.info === 1) {
                    playing = true;
                }
                // Also: {"event":"infoDelivery","info":{"playerState":1}}
                if (msg.event === 'infoDelivery' && msg.info && msg.info.playerState === 1) {
                    playing = true;
                }

                if (playing && window.__vtu_lecture_info && !window.__vtu_done[window.__vtu_lecture_info.id]) {
                    addLog('Video PLAYING detected for Lecture ' + window.__vtu_lecture_info.id);
                    startHeartbeatLoop(window.__vtu_lecture_info);
                }
            } catch(e) {
                // Not a JSON message or not from YouTube — ignore
            }
        });

        /* ══════════════════════════════════════════════════════════
           PHASE 3: Heartbeat loop — fires 5 seconds after play
           ══════════════════════════════════════════════════════════ */
        async function startHeartbeatLoop(info) {
            var myId = info.id;
            if (window.__vtu_done[myId]) return;
            window.__vtu_done[myId] = true;

            var total = info.total;
            var mins = info.mins;
            var progressUrl = info.progressUrl;

            // ── PLAY_WAIT: Seconds to wait after play detected before starting (in ms) ──
            var PLAY_WAIT = 5000;
            // ── CHUNK SIZE: Seconds per heartbeat (increase = fewer requests) ──
            var CHUNK = 60;
            // ── REQUEST GAP: Delay between successful requests in ms (increase = slower/safer) ──
            var REQUEST_GAP = 300;

            var numReqs = Math.ceil(total / CHUNK);
            var sent = 0;
            var errors = 0;

            // Countdown 5 seconds
            for (var s = 5; s > 0; s--) {
                if (window.__vtu_active !== myId) return;
                setPanel('countdown', { id: myId, sec: s });
                await new Promise(function(r) { setTimeout(r, 1000); });
            }

            addLog('Starting heartbeats for Lecture ' + myId + ' | ' + numReqs + ' requests');
            setPanel('syncing', { id: myId, mins: mins, total: total, pct: 0, current: 0, errors: 0 });

            // Sequential loop — one request at a time, in order
            for (var t = CHUNK; t <= total + CHUNK; t += CHUNK) {
                if (window.__vtu_active !== myId) {
                    addLog('Lecture ' + myId + ' cancelled (switched video)');
                    return;
                }
                var currentT = Math.min(t, total);

                var p = {};
                p.current_time_seconds = currentT;
                p.total_duration_seconds = total;
                p.seconds_just_watched = CHUNK;

                var ok = false;
                for (var attempt = 0; attempt < 3; attempt++) {
                    if (window.__vtu_active !== myId) return;

                    try {
                        var resp = await _origFetch(progressUrl, {
                            method: 'POST',
                            headers: {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest'
                            },
                            body: JSON.stringify(p),
                            credentials: 'same-origin'
                        });
                        if (resp.ok) {
                            ok = true;
                            sent++;
                            break;
                        }
                        addLog('Heartbeat ' + currentT + 's: status ' + resp.status + ', retry ' + (attempt+1));
                        // ── RETRY DELAY: Time to wait before retrying a failed request (in ms) ──
                        await new Promise(function(r) { setTimeout(r, 1500); });
                    } catch(e) {
                        addLog('Heartbeat ' + currentT + 's: error, retry ' + (attempt+1));
                        // ── RETRY DELAY: Same as above ──
                        await new Promise(function(r) { setTimeout(r, 1500); });
                    }
                }
                if (!ok) errors++;

                if (window.__vtu_active !== myId) return;

                var pct = Math.min(100, Math.round((sent / numReqs) * 100));
                setPanel('syncing', { id: myId, mins: mins, total: total, pct: pct, current: currentT, errors: errors });

                if ((sent + errors) % 5 === 0 || currentT === total) {
                    addLog(pct + '% | ' + currentT + '/' + total + 's | OK: ' + sent + ' Err: ' + errors);
                }

                // ── REQUEST GAP: Pause between requests ──
                await new Promise(function(r) { setTimeout(r, REQUEST_GAP); });
            }

            if (window.__vtu_active === myId) {
                addLog('Lecture ' + myId + ' done. Sent: ' + sent + '/' + numReqs + ', Errors: ' + errors);
                setPanel('done', { id: myId, mins: mins, errors: errors, sent: sent });
            }
        }

        /* ══════════════════════════════════════════════════════════
           FALLBACK: If YouTube postMessage doesn't work,
           also listen for the website's own POST /progress
           This is the same trigger as fast.py but as a backup
           ══════════════════════════════════════════════════════════ */
        var _realFetch = window.fetch;
        window.fetch = (function(prevFetch) {
            return async function() {
                var args = arguments;
                var url = typeof args[0] === 'string' ? args[0] : '';

                // If website sends its own POST /progress, use it as a fallback trigger
                if (url.indexOf('/progress') !== -1 && url.indexOf('lectures') !== -1
                    && args[1] && args[1].method === 'POST' && args[1].body) {

                    // Extract lecture ID
                    var lectureId = 'unknown';
                    var parts = url.split('/');
                    for (var i = 0; i < parts.length; i++) {
                        if (parts[i] === 'lectures' && i + 1 < parts.length && parts[i+1] !== 'progress') {
                            lectureId = parts[i + 1];
                            break;
                        }
                    }

                    // Update active
                    if (window.__vtu_active && window.__vtu_active !== lectureId) {
                        setPanel('idle', {});
                    }
                    window.__vtu_active = lectureId;

                    // If not already started by YouTube play detection, start now
                    if (!window.__vtu_done[lectureId]) {
                        try {
                            var payload = JSON.parse(args[1].body);
                            var total = Math.floor(payload.total_duration_seconds || 0);
                            if (total > 0) {
                                addLog('Fallback trigger from website heartbeat for Lecture ' + lectureId);
                                var progressUrl = url;
                                startHeartbeatLoop({
                                    id: lectureId,
                                    total: total,
                                    progressUrl: progressUrl,
                                    mins: Math.round(total / 60)
                                });
                            }
                        } catch(e) {}
                    }
                }

                return prevFetch.apply(this, args);
            };
        })(window.fetch);

        return true;
    }
    return false;
    """


def run_vtu_automator():
    creds = load_credentials()
    print("=" * 55)
    print("  VTU Video Progress Automator — SUPERFAST MODE")
    print("=" * 55)

    print()
    course_url = input("Paste the VTU course URL and press Enter:\n> ").strip()
    if not course_url.startswith("http"):
        print("Invalid URL. Restart and provide a valid https link.")
        exit()
    print()

    options = webdriver.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(options=options)

    bg_logger = BackgroundLogger(driver)

    try:
        # ── Login ──
        login_url = "https://online.vtu.ac.in/auth/login"
        print("[1/3] Opening login page...")
        driver.get(login_url)

        print("[2/3] Filling credentials...")
        wait = WebDriverWait(driver, 15)

        email_field = wait.until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div/div[1]/div[1]/div[2]/div/form/div[1]/input")))
        email_field.send_keys(creds["email"])

        password_field = driver.find_element(
            By.XPATH, "/html/body/div/div[1]/div[1]/div[2]/div/form/div[2]/div[2]/input")
        password_field.send_keys(creds["password"])

        login_btn = driver.find_element(
            By.XPATH, "/html/body/div/div[1]/div[1]/div[2]/div/form/button")
        login_btn.click()

        print("[2/3] Login submitted. Waiting for redirect (up to 2 min)...")
        WebDriverWait(driver, 120).until(EC.url_changes(login_url))
        print("[2/3] Login successful!")

        bg_logger.start()

        print(f"[3/3] Navigating to course: {course_url}")
        driver.get(course_url)

        print()
        print("=" * 55)
        print("  SUPERFAST READY!")
        print("  1. Click any lecture in the sidebar")
        print("  2. Press PLAY on the video")
        print("  3. Automation starts in 5 seconds")
        print("  4. Then click next video. No restart needed!")
        print("=" * 55)
        print()
        print("--- Live Log ---")

        js_hook = get_js_hook()
        last_log_idx = 0
        stats_counter = 0

        while True:
            try:
                current_url = driver.current_url
                if "learning" in current_url:
                    result = driver.execute_script(js_hook)
                    if result:
                        print("[Hook] SUPERFAST injected")
                        last_log_idx = 0

                    logs = driver.execute_script("return window.__vtu_log || [];")
                    if logs and len(logs) > last_log_idx:
                        for entry in logs[last_log_idx:]:
                            print(f"  >> {entry}")
                        last_log_idx = len(logs)

                stats_counter += 1
                if stats_counter % 10 == 0:
                    stats = bg_logger.get_stats()
                    print(f"  [NET] Total: {stats['total_requests']} | API: {stats['api_requests']} | Progress: {stats['progress_requests']} | Errors: {stats['errors']}")

            except Exception:
                last_log_idx = 0

            time.sleep(1.5)

    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    finally:
        print("Stopping background logger...")
        try:
            bg_logger.stop()
        except:
            pass
        print("Closing browser...")
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    run_vtu_automator()
