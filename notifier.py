
import urllib.request
import urllib.error
import json
import time
import os
import re

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
REPO_URL = "https://api.github.com/repos/juanfont/headscale/releases/latest"
DATA_FILE = "/data/last_version.txt"
CHECK_INTERVAL = 43200  # Check every 12 hours

def check_update():
    if not WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK environment variable not set.")
        return

    try:
        # Fetch the latest release from GitHub
        req = urllib.request.Request(REPO_URL, headers={"User-Agent": "Headscale-Notifier"})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        latest_version = data.get("tag_name")
        release_notes = data.get("body", "")
        release_url = data.get("html_url")

        # Read the last version we alerted on
        last_version = ""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                last_version = f.read().strip()

        # If it's a new version, process and send alert
        if latest_version and latest_version != last_version:
            print(f"New version found: {latest_version}. Analyzing release notes...")

            # Scan for dangerous keywords
            is_breaking = re.search(r'(?i)(breaking\schange|migration|action\srequired)', release_notes)

            if is_breaking:
                color = 16711680 # Red
                status = "⚠️ **WARNING: POTENTIALLY BREAKING CHANGES** ⚠️\nRead the release notes carefully before updating. A database migration or config change may be required."
            else:
                color = 65280 # Green
                status = "✅ **LOOKS SAFE TO UPDATE** ✅\nNo 'Breaking Changes' or 'Migrations' detected in the release notes. A standard `docker compose pull` should be safe."

            # Construct Discord Embed
            payload = {
                "username": "Headscale Monitor",
                "avatar_url": "https://raw.githubusercontent.com/juanfont/headscale/main/docs/logo/headscale3.png",
                "embeds": [{
                    "title": f"New Headscale Release: {latest_version}",
                    "url": release_url,
                    "color": color,
                    "description": f"{status}\n\n**[Read Full Release Notes]({release_url})**"
                }]
            }

            # Send to Discord
            post_req = urllib.request.Request(
                WEBHOOK_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": "Headscale-Notifier"}
            )
            urllib.request.urlopen(post_req)

            # Save the new version so we don't alert again
            with open(DATA_FILE, "w") as f:
                f.write(latest_version)
            print(f"Alert sent for {latest_version}!")
        else:
            print(f"Already up to date or already alerted (Latest: {latest_version}).")

    except Exception as e:
        print(f"Failed to check for updates: {e}")

if __name__ == "__main__":
    print("Headscale Update Notifier started...")
    # Ensure data directory exists
    os.makedirs("/data", exist_ok=True)

    while True:
        check_update()
        time.sleep(CHECK_INTERVAL)
