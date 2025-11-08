import undetected_chromedriver as uc
import os
import time
import csv
import datetime
import io
import webbrowser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- Google Drive Imports ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# --- SCRIPT CONFIGURATION ---
BASE_URL = "https://www.brandsforless.com/en-sa/men/new-arrivals/"
TOTAL_PAGES = 99
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1z9oGLaFXYZTZ9i51AvICsEggrdJsijlG")

# --- SELECTORS ---
PRODUCT_CARD_SELECTOR = "#product-listing ul li a"
PRODUCT_NAME_SELECTOR = "h1"
PRODUCT_IMAGE_SELECTOR = "img"
PRODUCT_PRICE_SELECTOR = "span.price.red"

# --- Google Auth Configuration ---
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'token.json'
CREDS_FILE = 'credentials.json'

# --- Authentication and Drive Functions ---
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
        print(f"An error occurred building the Drive service: {error}")
        return None


def upload_to_drive(service, file_path, file_name, folder_id, mimetype):
    try:
        file_metadata = {'name': os.path.basename(file_name), 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype=mimetype)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"Uploaded '{file_name}' (ID: {file.get('id')})")
        return file.get('id')
    except HttpError as error:
        print(f"An error occurred uploading '{file_name}': {error}")
        return None


def find_latest_product_file(service, folder_id, today_filename):
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, createdTime)',
            pageSize=10,
            orderBy='createdTime desc'
        ).execute()
        files = response.get('files', [])

        if not files:
            print("No files found in the Drive folder.")
            return None

        for file in files:
            file_name = file.get('name')
            if file_name.endswith('-products.csv') and file_name != today_filename:
                print(f"Found latest comparison file: {file_name}")
                return file.get('id')

        print("No previous product files found for comparison.")
        return None

    except HttpError as error:
        print(f"An error occurred searching for files: {error}")
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
        csv_content = fh.read().decode('utf-8')
        csv_file = io.StringIO(csv_content)
        reader = csv.reader(csv_file)
        next(reader, None)  # Skip header
        return [row for row in reader]

    except HttpError as error:
        print(f"An error occurred downloading file: {error}")
        return []


# --- Scraping Function ---
def run_scrape():
    """Scrapes all pages and returns a list of [Name, Full_Link, Image_URL, Base_Link, Price]"""
    import undetected_chromedriver as uc
    import os

    print("Setting up Chrome WebDriver...")

    driver = None

    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # ✅ Works on both local and GitHub Actions
        driver = uc.Chrome(options=options, use_subprocess=True)
        print("Chrome WebDriver setup successful!")

    except Exception as e:
        print(f"Error: Could not set up Chrome Driver: {e}")
        return []

    all_products_data = []

    try:
        for page_num in range(1, TOTAL_PAGES + 1):
            # --- Your scraping logic goes here ---
            print(f"Scraping page {page_num}...")
            pass  # placeholder
    except Exception as e:
        print(f"A critical error occurred during scraping: {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            try:
                del driver
            except Exception:
                pass

    print(f"\nDeduplicating {len(all_products_data)} total products...")
    unique_products_map = {item[3]: item for item in all_products_data}
    unique_products_list = list(unique_products_map.values())
    print(f"After deduplication: {len(unique_products_list)} unique products")

    return unique_products_list


# Debug info
import os
print("📂 Current working directory:", os.getcwd())
print("📄 Files in directory:", os.listdir())

# --- CSV Saving Function ---
def save_csv_locally(product_list, file_name):
    with open(file_name, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Product Name', 'URL', 'Image URL', 'Base URL', 'Price'])
        writer.writerows(product_list)
    print(f"Saved {len(product_list)} items to local file: {file_name}")


# --- HTML Saving Function ---
def save_html_locally(product_list, file_name):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Newly Added Products</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; }}
            .container {{ max-width: 1400px; margin: 20px auto; padding: 20px; }}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 20px;
            }}
            .product-card {{
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-decoration: none;
                color: #333;
                overflow: hidden;
            }}
            .product-image {{ width: 100%; height: auto; }}
            .product-name {{ padding: 10px; font-weight: bold; }}
            .product-price {{ padding: 0 10px 10px; color: #e74c3c; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Newly Added Products</h1>
            <p>Found <strong>{len(product_list)}</strong> new items.</p>
            <div class="grid-container">
    """

    for item in product_list:
        name = item[0]
        url = item[1]
        image_url = item[2]
        price = item[4] if len(item) > 4 else "N/A"
        html_content += f"""
                <a href="{url}" class="product-card" target="_blank">
                    <img src="{image_url}" alt="{name}" class="product-image">
                    <div class="product-name">{name}</div>
                    <div class="product-price">{price}</div>
                </a>
        """

    html_content += """
            </div>
        </div>
    </body>
    </html>
    """

    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Saved {len(product_list)} new items to visual HTML file: {file_name}")


# --- Main Function ---
os.makedirs("results", exist_ok=True)

def main():
    today_date = datetime.date.today()
    today_filename_csv = f"results/{today_date.isoformat()}-products.csv"
    new_items_filename_html = f"results/{today_date.isoformat()}-NEWLY-ADDED.html"

    print(f"Starting scrape for {today_date.isoformat()}...")
    today_products_list = run_scrape()

    if not today_products_list:
        print("Scrape finished with no products. Exiting.")
        return

    print(f"\n=== SCRAPE COMPLETE ===")
    print(f"Found {len(today_products_list)} total unique products.")

    save_csv_locally(today_products_list, today_filename_csv)

    print("\n--- Connecting to Google Drive ---")
    drive_service = authenticate_google_drive()

    if not drive_service:
        print("Could not authenticate with Google Drive. Exiting.")
        return

    upload_to_drive(drive_service, today_filename_csv, today_filename_csv, DRIVE_FOLDER_ID, 'text/csv')

    print(f"\n--- Starting Comparison ---")
    previous_file_id = find_latest_product_file(drive_service, DRIVE_FOLDER_ID, today_filename_csv)

    if not previous_file_id:
        print("No previous file found. Cannot run comparison. Exiting.")
        return

    previous_products_list = download_and_parse_csv(drive_service, previous_file_id)
    if not previous_products_list:
        print("Previous file was found but could not be read or was empty. Exiting.")
        return

    today_lookup_map = {row[3]: row for row in today_products_list}
    set_today_urls = {row[3] for row in today_products_list}

    set_previous_urls = set()
    if previous_products_list:
        num_cols = len(previous_products_list[0])
        if num_cols >= 4:
            set_previous_urls = {row[3] for row in previous_products_list if len(row) > 3}
        elif num_cols == 3:
            set_previous_urls = {row[1].split('?')[0] for row in previous_products_list if len(row) > 1}

    new_item_base_urls = set_today_urls - set_previous_urls
    new_items_list = [today_lookup_map[base_url] for base_url in new_item_base_urls]

    if not new_items_list:
        print("No new items found today.")
        return

    print(f"Comparison complete: Found {len(new_items_list)} new items!")

    save_html_locally(new_items_list, new_items_filename_html)
    upload_to_drive(drive_service, new_items_filename_html, new_items_filename_html, DRIVE_FOLDER_ID, 'text/html')

    try:
        webbrowser.open_new_tab('file://' + os.path.abspath(new_items_filename_html))
    except Exception as e:
        print(f"Could not open HTML file automatically: {e}")

    print(f"\n=== All tasks complete. ===")


if __name__ == "__main__":
    main()

