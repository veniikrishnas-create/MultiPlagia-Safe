import json
SETTINGS_FILE = "settings.json"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        default = {
            "username": "User",
            "email": "user@example.com",
            "password": "",
            "notifications": {"email_reports": True, "sms_alerts": False, "weekly_summary": True},
            "privacy": {"private_uploads": True, "share_data": False, "two_factor": False},
            "theme": "Light",
            "language": "English"
        }
        return default

def save_settings(data):
    settings = load_settings()
    settings.update({
        "username": data.get("username", settings["username"]),
        "email": data.get("email", settings["email"]),
        "theme": data.get("theme", settings["theme"]),
        "language": data.get("language", settings["language"]),
    })
    # Checkboxes
    settings["notifications"]["email_reports"] = "email_reports" in data
    settings["notifications"]["sms_alerts"] = "sms_alerts" in data
    settings["notifications"]["weekly_summary"] = "weekly_summary" in data
    settings["privacy"]["private_uploads"] = "private_uploads" in data
    settings["privacy"]["share_data"] = "share_data" in data
    settings["privacy"]["two_factor"] = "two_factor" in data

    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


import json

SETTINGS_FILE = "settings.json"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        default = {
            "username": "User",
            "email": "user@example.com",
            "password": "",
            "notifications": {"email_reports": True, "sms_alerts": False, "weekly_summary": True},
            "privacy": {"private_uploads": True, "share_data": False, "two_factor": False},
            "theme": "Light",
            "language": "English"
        }
        return default

def save_settings(data):
    settings = load_settings()
    settings.update({
        "username": data.get("username", settings["username"]),
        "email": data.get("email", settings["email"]),
        "password": data.get("password", settings["password"]),
    })
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
