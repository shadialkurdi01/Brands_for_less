import os
import csv
import time
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---- Config ----
BASE_URL = "https://www.brandsforless.com/en-ae/c/women-10002"  # Example starting page
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)
CSV_PATH = os.path.join(RESULTS_DIR, "products.csv")

# ✅ Stronger, broader selector
PRODUCT_CARD_SELECTOR = (
    "div.product-item a, div.product-card a, li.product-item a, "
    "div.product-item__link, article.product-tile a"
)

def setup_chrome_driver():
    """Set up Chrome WebDriver for GitHub Actions."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
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
    """Scrape products from a single page."""
    driver.get(url)
    driver.implicitly_wait(10)
    time.sleep(5)

    # Save HTML for inspection (so we can see structure)
    with open("page_debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("✅ Saved page_debug.html for inspection.")

    elements = driver.find_elements(By.CSS_SELECTOR, PRODUCT_CARD_SELECTOR)
    products = []
    for el in elements:
        try:
            href = el.get_attribute("href")
            name = el.text.strip()
            if href:
                products.append({"name": name, "url": href})
        except Exception:
            continue
    print(f"Found {len(products)} products on this page.")
    return products

def save_csv_locally(products):
    """Save scraped products to CSV."""
    if not products:
        print("No products to save.")
        return
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url"])
        writer.writeheader()
        writer.writerows(products)
    print(f"✅ Saved results to {CSV_PATH}")

def upload_to_drive():
    """Upload CSV to Google Drive (if configured)."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    if not creds_json or not folder_id:
        print("⚠️ Skipping Google Drive upload (missing credentials).")
        return

    creds_path = "credentials.json"
    with open(creds_path, "w") as f:
        f.write(creds_json)

    creds = Credentials.from_authorized_user_file(creds_path)
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": os.path.basename(CSV_PATH), "parents": [folder_id]}
    media = MediaFileUpload(CSV_PATH, mimetype="text/csv")
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    print(f"✅ Uploaded to Google Drive, File ID: {file.get('id')}")

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
        if page > 30:  # safety stop
            break

    driver.quit()
    print(f"Deduplicating {len(all_products)} total products...")

    # Deduplicate by URL
    unique = {p["url"]: p for p in all_products}.values()
    print(f"After deduplication: {len(unique)} unique products")

    save_csv_locally(list(unique))
    upload_to_drive()

    print("Scrape finished successfully.")

if __name__ == "__main__":
    main()
