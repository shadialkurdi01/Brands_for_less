import os
import csv
import time
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---- Configuration ----
BASE_URL = "https://www.brandsforless.com/en-ae/c/women-10002"
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)
CSV_PATH = os.path.join(RESULTS_DIR, "products.csv")

# Flexible selector (will adjust once you upload page_debug.html)
PRODUCT_CARD_SELECTOR = "a[href*='brandsforless.com/en-ae/p/']"

def setup_chrome_driver():
    """Setup Chrome for GitHub Actions."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(options=options)
        print("Chrome WebDriver setup successful!")
        return driver
    except WebDriverException as e:
        print(f"Error: Could not set up Chrome Driver: {e}")
        return None

def scrape_page(driver, url):
    """Scrape one page."""
    driver.get(url)
    driver.implicitly_wait(10)
    time.sleep(5)
    debug_path = os.path.join(RESULTS_DIR, "page_debug.html")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"✅ Saved {debug_path} for inspection.")
    elements = driver.find_elements(By.CSS_SELECTOR, PRODUCT_CARD_SELECTOR)
    products = []
    for el in elements:
        href = el.get_attribute("href")
        name = el.text.strip()
        if href:
            products.append({"name": name, "url": href})
    print(f"Found {len(products)} products on this page.")
    return products

def save_csv_locally(products):
    """Save products to CSV."""
    if not products:
        print("No products to save.")
        return
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url"])
        writer.writeheader()
        writer.writerows(products)
    print(f"✅ Saved results to {CSV_PATH}")

def upload_to_drive():
    import json
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    import os

    print("📤 Uploading to Google Drive...")

    creds_path = "google_creds.json"
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")

    if not creds_json:
        print("⚠️ No GOOGLE_CREDENTIALS found in environment.")
        return

    try:
        creds_data = json.loads(creds_json)
        # Save credentials temporarily
        with open(creds_path, "w") as f:
            json.dump(creds_data, f)

        creds = Credentials.from_authorized_user_file(creds_path, scopes=["https://www.googleapis.com/auth/drive"])
        service = build("drive", "v3", credentials=creds)

        # Upload the latest CSV file
        results_dir = "results"
        latest_file = max(
            [os.path.join(results_dir, f) for f in os.listdir(results_dir) if f.endswith(".csv")],
            key=os.path.getctime,
        )

        file_metadata = {"name": os.path.basename(latest_file)}
        media = MediaFileUpload(latest_file, mimetype="text/csv")

        service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        print("✅ File uploaded successfully!")

    except Exception as e:
        print(f"⚠️ Google Drive upload failed: {e}")


def main():
    today_date = datetime.date.today()
    print(f"Starting scrape for {today_date.isoformat()}...")

    driver = setup_chrome_driver()
    if not driver:
        return

    all_products = []
    page = 1
    while True:
        url = f"{BASE_URL}?page={page}"
        print(f"Scraping page {page}...")
        products = scrape_page(driver, url)
        if not products:
            print("No products found on page. Stopping scrape.")
            break
        all_products.extend(products)
        page += 1
        if page > 30:
            break

    if not unique:
        print("⚠️ No products found. Saving empty CSV for debugging.")
        save_csv_locally([{"name": "No products found", "url": "N/A"}])
    else:
        save_csv_locally(list(unique))
        
    save_csv_locally(list(unique))
    upload_to_drive()
    print("✅ Scrape finished successfully.")

if __name__ == "__main__":
    main()



