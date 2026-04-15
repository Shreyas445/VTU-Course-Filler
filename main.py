import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CREDENTIALS_FILE = "credentials.json"

def load_credentials():
    # Create the credentials file if it doesn't exist
    if not os.path.exists(CREDENTIALS_FILE):
        default_creds = {
            "email": "your_email@gmail.com",
            "password": "your_password"
        }
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(default_creds, f, indent=4)
        print(f"⚠️ Created {CREDENTIALS_FILE}. Please fill in your email and password, then restart the script.")
        exit()
        
    with open(CREDENTIALS_FILE, "r") as f:
        creds = json.load(f)
        
    if creds["email"] == "your_email@gmail.com":
        print(f"❌ Please update {CREDENTIALS_FILE} with your actual VTU credentials!")
        exit()
        
    return creds

def run_vtu_automator():
    creds = load_credentials()
    print("🚀 Starting VTU Video Progress Automator (V3 - Fully Automated)...")
    
    # --- MODIFICATION: Ask for the URL before opening the browser ---
    print("\n" + "="*50)
    course_url = input("📝 Please paste the VTU course URL here and press Enter:\n> ").strip()
    
    if not course_url.startswith("http"):
        print("❌ Invalid URL provided. Please restart and provide a valid http/https link.")
        exit()
    print("="*50 + "\n")
    # ----------------------------------------------------------------

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    
    try:
        # Automated Login
        login_url = "https://online.vtu.ac.in/auth/login"
        print(f"🔄 Navigating to login page...")
        driver.get(login_url)
        
        print("🔑 Logging in automatically...")
        wait = WebDriverWait(driver, 15)
        
        # XPaths provided by you!
        email_field = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[1]/div[1]/div[2]/div/form/div[1]/input")))
        email_field.send_keys(creds["email"])
        
        password_field = driver.find_element(By.XPATH, "/html/body/div/div[1]/div[1]/div[2]/div/form/div[2]/div[2]/input")
        password_field.send_keys(creds["password"])
        
        login_btn = driver.find_element(By.XPATH, "/html/body/div/div[1]/div[1]/div[2]/div/form/button")
        login_btn.click()
        
        print("✅ Login submitted! Waiting for authentication to complete...")
        
        # We wait until the URL changes from the login screen
        WebDriverWait(driver, 20).until(EC.url_changes(login_url))
        
        # Navigate to VTU Learning Course automatically using the inputted URL
        print(f"📚 Going to the course module: {course_url}")
        driver.get(course_url)
        
        print("\n" + "="*50)
        print("🎯 WHAT TO DO NOW:")
        print("1. Click on ANY video in the curriculum sidebar.")
        print("2. Hit play. The script will rapidly fire smaller (+30s) updates.")
        print("3. Wait until you see the Green Success Popup on the screen.")
        print("4. Move to the NEXT video and repeat. You do NOT need to restart this script!")
        print("="*50)

        js_hook = """
        if (!window.__vtu_completed) {
            console.log('%c[VTU Automator] Batch-Progress Interceptor Injected!', 'color: lime; font-size: 20px;');
            window.__vtu_completed = {};
            const originalFetch = window.fetch;
            
            window.fetch = async function(...args) {
                const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
                
                if (url.includes('/progress') && url.includes('lectures')) {
                    if (args[1] && typeof args[1].body === 'string') {
                        const lectureMatch = url.match(/lectures\\/(\\d+)\\//);
                        const lectureId = lectureMatch ? lectureMatch[1] : 'unknown';
                        
                        // We only fast-forward the API if we haven't completed this video page yet.
                        if (!window.__vtu_completed[lectureId]) {
                            window.__vtu_completed[lectureId] = true;
                            
                            try {
                                let payload = JSON.parse(args[1].body);
                                
                                if (payload.total_duration_seconds) {
                                    let total = Math.floor(payload.total_duration_seconds);
                                    console.log(`🚀 [VTU Automator] Firing batch sequence for Lecture ${lectureId} (Total: ${total}s)...`);
                                    
                                    // Start the batch request sequence asynchronously!
                                    setTimeout(async () => {
                                        for (let watchTime = 30; watchTime <= total + 30; watchTime += 30) {
                                            let p = { ...payload };
                                            p.current_time_seconds = Math.min(watchTime, total);
                                            p.seconds_just_watched = 30; // 30s chunks so backend accepts it safely
                                            
                                            let newOpts = { ...args[1] };
                                            newOpts.body = JSON.stringify(p);
                                            
                                            // Silently send the forged chunk to the server
                                            await originalFetch(url, newOpts);
                                            
                                            // Sleep slightly longer (125ms) so it finishes seamlessly without rushing the backend
                                            // NOTE: We increased the delay slightly so that the popup timing is perfectly matched with VTU backend.
                                            await new Promise(r => setTimeout(r, 125));
                                        }
                                        console.log(`✅ [VTU Automator] Lecture ${lectureId} pushed to 100%!`);
                                        
                                        // Show a nice green success popup!
                                        let uiElement = document.createElement('div');
                                        uiElement.innerHTML = `
                                        <div style="position:fixed;bottom:20px;right:20px;background:#00c853;color:white;padding:20px;z-index:999999;border-radius:8px;font-family:sans-serif;font-weight:bold;font-size:16px;box-shadow: 0 4px 6px rgba(0,0,0,0.1);animation: fadeOut 8s forwards;">
                                            ✅ Lecture ${lectureId} 100% Synced to Server! just unpause the video and wait few seconds<br><span style="font-size:13px;font-weight:normal;">Backend tracking perfectly aligned. You can click the next video!</span>
                                        </div>
                                        <style>@keyframes fadeOut { 0% {opacity:1;} 80% {opacity:1;} 100% {opacity:0;display:none;} }</style>
                                        `;
                                        document.body.appendChild(uiElement);
                                        
                                    }, 50);
                                }
                            } catch(e) {}
                        }
                    }
                }
                return originalFetch.apply(this, args);
            };
            return true; // Indicating it was injected
        }
        return false; // Already injected
        """
        
        # We start an infinite loop that constantly checks if our payload monitor is active.
        # This solves the problem where if a user refreshes the page, or goes to a completely new URL, the monitor gets wiped out.
        while True:
            try:
                # We check the window URL. If we are on the course page, we check and inject.
                if "learning" in driver.current_url:
                    injected = driver.execute_script(js_hook)
                    if injected:
                        print("✅ Re-injected VTU hooks into the page session.")
            except Exception as e:
                pass # Usually happens during a page reload (StaleElement or NoWindow)
                
            time.sleep(2) # check lazily every 2 seconds heartbeat
            
    except KeyboardInterrupt:
        print("\n🛑 Exiting python script...")
    finally:
        print("\n👋 Closing Browser...")
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    run_vtu_automator()
