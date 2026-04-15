import json
import time
from selenium import webdriver

def extract_endpoints():
    print("Setting up Chrome with Performance Logging...")
    options = webdriver.ChromeOptions()
    # Enable performance logging to capture network traffic invisibly
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    # Initialize WebDriver (Selenium 4.6+ will auto-download the required driver)
    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://online.vtu.ac.in/student/learning/1-data-analytics-with-python"
        print(f"Navigating to {url}")
        driver.get(url)
        
        print("\n" + "="*50)
        print("ACTION REQUIRED:")
        print("1. Please log in with your email and password in the Chrome window.")
        print("2. Wait for the page to load and START PLAYING the video.")
        print("="*50 + "\n")
        
        input("Press ENTER here in the terminal AFTER the video has been playing for a few seconds...")
        
        print("\nMonitoring network traffic for 15 seconds... Keep the video playing.")
        time.sleep(15) 
        
        # Extract network performance logs
        logs = driver.get_log("performance")
        
        endpoints = set()
        print("\n" + "="*20 + " EXTRACTED API ENDPOINTS " + "="*20)
        for entry in logs:
            try:
                log = json.loads(entry["message"])["message"]
                
                # Check for outgoing requests
                if log["method"] == "Network.requestWillBeSent":
                    request = log["params"]["request"]
                    req_url = request["url"]
                    method = request["method"]
                    
                    # Filter for API or progress-related routes (ignoring static files)
                    if "/api/" in req_url or "progress" in req_url.lower() or "learning" in req_url.lower():
                        if req_url not in endpoints:
                            endpoints.add(req_url)
                            print(f"\n[ {method} ] {req_url}")
                            
                            # Check Headers for Authentication tokens
                            headers = request.get("headers", {})
                            auth_header = headers.get("Authorization") or headers.get("authorization")
                            if auth_header:
                                print(f"   Auth Token: {auth_header[:30]}...")
                                
                            # Check Payload for data submitted
                            if "postData" in request:
                                payload = request["postData"]
                                print(f"   Payload: {payload}")
                                
            except Exception as e:
                continue # Safely ignore malformed log entries
                
        if not endpoints:
            print("\nNo specific API endpoints found. The heartbeat might trigger less frequently (e.g. every 30s).")
            
        print("\n" + "="*65)
            
    finally:
        print("\nClosing browser...")
        driver.quit()

if __name__ == "__main__":
    extract_endpoints()
