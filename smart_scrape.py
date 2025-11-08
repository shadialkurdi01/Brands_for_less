import undetected_chromedriver as uc
import os
import time
import csv
import datetime
import io
import webbrowser
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# --- CONFIGURATION ---
BASE_URL = "https://www.brandsforless.com/en-sa/men/new-arrivals/"
TOTAL_PAGES = 99
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1z9oGLaFXYZTZ9i51AvICsEggrdJsijlG")

PRODUCT_CARD_SELECTOR = "#product-listing ul li a"
PRODUCT_NAME_SELECTOR = "h1"
PRODUCT_IMAGE_SELECTOR = "img"
PRODUCT_PRICE_SELECTOR = "span.price.red"

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'token.json'
CREDS_FILE = 'credentials.json'

# --- Ensure results directory exists ---
os.makedirs("results", exist_ok=True)

# --- Google Drive Auth ---
def authenticate_google_drive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                print(f"Error: '{CREDS_FILE}' not found.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f"Drive service error: {error}")
        return None

# --- Google Drive Helpers ---
def upload_to_drive(service, file_path, file_name, folder_id, mimetype):
    try:
        file_metadata = {'name': os.path.basename(file_name), 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Uploaded '{file_name}' → ID: {file.get('id')}")
        return file.get('id')
    except HttpError as error:
        print(f"Upload error: {error}")
        return None

def find_latest_product_file(service, folder_id, today_filename):
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        response = service.files().list(
            q=query, spaces='drive',
            fields='files(id, name, createdTime)',
            orderBy='createdTime desc', pageSize=10
        ).execute()
        for file in response.get('files', []):
            if file['name'].endswith('-products.csv') and file['name'] != today_filename:
                return file['id']
        return None
    except HttpError as error:
        print(f"Search error: {error}")
        return None

def download_and_parse_csv(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        content = fh.read().decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        next(reader, None)
        return [row for row in reader]
    except HttpError as error:
        print(f"Download error: {error}")
        return []

# --- Scraper ---
def run_scrape():
    print("Setting up Chrome WebDriver...")
    driver = None
    all_products_data = []

    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        driver = uc.Chrome(options=options, version_main=None, use_subprocess=False)
        print("Chrome WebDriver setup successful!")

        for page_num in range(1, TOTAL_PAGES + 1):
            print(f"Scraping page {page_num}...")
            url = f"{BASE_URL}?page={page_num}"
            driver.get(url)
            time.sleep(3)

            products = driver.find_elements(By.CSS_SELECTOR, PRODUCT_CARD_SELECTOR)
            if not products:
                print(f"No products found on page {page_num}. Stopping scrape.")
                break

            for product in products:
                try:
                    link = product.get_attribute("href")
                    img_el = product.find_element(By.CSS_SELECTOR, PRODUCT_IMAGE_SELECTOR)
                    img_url = img_el.get_attribute("src") if img_el else "N/A"
                    name = product.get_attribute("title") or "N/A"
                    price = "N/A"
                    all_products_data.append([name, link, img_url, link.split("?")[0], price])
                except Exception as e:
                    print(f"Error parsing product: {e}")

        print(f"\nDeduplicating {len(all_products_data)} total products...")
        unique_map = {item[3]: item for item in all_products_data}
        result = list(unique_map.values())
        print(f"After deduplication: {len(result)} unique products")
        return result

    except Exception as e:
        print(f"Error setting up Chrome Driver: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

# --- File Helpers ---
def save_csv_locally(product_list, file_name):
    with open(file_name, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Product Name', 'URL', 'Image URL', 'Base URL', 'Price'])
        writer.writerows(product_list)
    print(f"Saved {len(product_list)} items to local file: {file_name}")

# --- Main Execution ---
def main():
    today = datetime.date.today()
    today_csv = f"results/{today.isoformat()}-products.csv"
    today_html = f"results/{today.isoformat()}-NEWLY-ADDED.html"

    print(f"Starting scrape for {today.isoformat()}...")
    products = run_scrape()

    if not products:
        print("Scrape finished with no products. Exiting.")
        return

    save_csv_locally(products, today_csv)

    drive_service = authenticate_google_drive()
    if not drive_service:
        print("Google Drive auth failed.")
        return

    upload_to_drive(drive_service, today_csv, today_csv, DRIVE_FOLDER_ID, 'text/csv')
    print("✅ All tasks complete.")

if __name__ == "__main__":
    print(f"📂 Current working directory: {os.getcwd()}")
    print(f"📄 Files in directory: {os.listdir()}")
    main()
