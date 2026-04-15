# VTU Video Progress Automator

🚀 A highly automated Python script that intercepts network requests to batch-sync video progress for VTU online learning modules. 

> **⚠️ Disclaimer:** This project is provided for educational and research purposes only. Automating API requests to bypass course completion constraints violates platform Terms of Service and may result in academic penalties or account suspension. Use at your own risk.

## Features
* **Automated Authentication:** Logs in automatically using Selenium WebDriver.
* **Network Interception:** Overrides `window.fetch` to intercept and reverse-engineer the YouTube IFrame API progress payload.
* **Batch Processing:** Sends calculated 30-second heartbeat chunks to satisfy backend database tracking.
* **In-Page UI Injection:** Injects a custom success overlay directly into the DOM once synchronization is complete.

## Prerequisites
* Python 3.8+
* Google Chrome installed
* [Selenium](https://pypi.org/project/selenium/)

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/Shreyas445/VTU-Course-Filler.git
   ```
2. Install the required packages:
   ```bash
   pip install selenium
   ```

## Usage
1. Run the script once to generate the `credentials.json` template:
   ```bash
   python main.py
   ```
2. Open `credentials.json` and enter your valid login credentials.
3. Run the script again. The browser will launch, log you in, and navigate to the learning module.
4. Click on any video. The injected script will handle the rest and show a green success popup when the backend is synced.

## ⚠️ Warning!
<img width="200" height="100" alt="WarningGIF" src="https://github.com/user-attachments/assets/1c4b1510-434e-4c1a-a638-24044e3c4716" />

1. this is for educational purpose only
2. developer is not responsible for any academic penalties or account suspension
3. use it at your own risk


## License
This project is licensed under the [MIT License](LICENSE).
