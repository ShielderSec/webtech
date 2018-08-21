import os.path
import time
import requests


INSTALLATION_DIR = os.path.realpath(os.path.dirname(__file__))
DATABASE_FILE = os.path.join(INSTALLATION_DIR, "apps.json")
WAPPALYZER_DATABASE = "https://raw.githubusercontent.com/AliasIO/Wappalyzer/master/src/apps.json"
DAYS = 60 * 60 * 24


def download_database_file(url):
    print("Updating database...")
    r = requests.get(url, stream=True)
    with open(DATABASE_FILE, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    print("Database updated successfully!")


def update_database(args=None):
    # option to force the DB update

    if not os.path.isfile(DATABASE_FILE):
        print("Database file not present.")
        download_database_file(WAPPALYZER_DATABASE)
        # set timestamp in filename
    else:
        last_update = int(os.path.getmtime(DATABASE_FILE))
        now = int(time.time())

        if last_update < now - 30 * DAYS:
            print("Database file is older than 30 days.")
            os.remove(DATABASE_FILE)
            download_database_file(WAPPALYZER_DATABASE)


update_database()
