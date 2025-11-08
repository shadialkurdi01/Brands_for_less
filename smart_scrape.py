
import undetected_chromedriver as uc

import time
import csv
import os
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
DRIVE_FOLDER_ID = "1z9oGLaFXYZTZ9i51AvICsEggrdJsijlG"

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
        file_metadata = {'name': file_name, 'parents': [folder_id]}
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
        query = (
            f"'{folder_id}' in parents and "
            f"trashed=false"
        )
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

        print(f"No previous product files found for comparison.")
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
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        csv_content = fh.read().decode('utf-8')
        csv_file = io.StringIO(csv_content)
        reader = csv.reader(csv_file)
        next(reader, None) # Skip header
        return [row for row in reader]
        
    except HttpError as error:
        print(f"An error occurred downloading file: {error}")
        return []

# --- MODIFIED: Enhanced Scraping Function ---


def run_scrape():
    """Scrapes all pages and returns a list of [Name, Full_Link, Image_URL, Base_Link, Price]"""
    print("Setting up Chrome WebDriver...")
    
    driver = None  # Initialize as None
    
    try:
     options = uc.ChromeOptions()

# Headless mode for GitHub Actions
options.add_argument('--headless')  # Changed from '--headless=new'
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--window-size=1920,1080')
options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Detect if running in GitHub Actions
import os
if os.getenv('GITHUB_ACTIONS'):
    # Running in GitHub Actions - use headless
    driver = uc.Chrome(
        options=options,
        version_main=None,
        use_subprocess=False  # Changed to False for GitHub Actions
    )
else:
    # Running locally
    driver = uc.Chrome(
        options=options,
        version_main=141,
        use_subprocess=True
    )
        
        print("Chrome WebDriver setup successful!")
        
    except Exception as e:
        print(f"Error: Could not set up Chrome Driver: {e}")
        return []

    all_products_data = []
    
    try:
        for page_num in range(1, TOTAL_PAGES + 1):
            # ... all your existing scraping code ...
            pass  # (keeping the full code you already have)
                
    except Exception as e:
        print(f"A critical error occurred during scraping: {e}")
    finally:
        # Improved cleanup that prevents the handle error
        if driver:
            try:
                driver.quit()
            except (OSError, Exception):
                pass  # Silently ignore cleanup errors
            
            # Prevent the destructor from running again
            try:
                del driver
            except:
                pass
        
    print(f"\nDeduplicating {len(all_products_data)} total products...")
    unique_products_map = {item[3]: item for item in all_products_data}
    unique_products_list = list(unique_products_map.values())
    print(f"After deduplication: {len(unique_products_list)} unique products")
    
    return unique_products_list

# --- CSV Saving Function ---
def save_csv_locally(product_list, file_name):
    """Saves the full product list to a local CSV file with a 5-column header."""
    with open(file_name, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Product Name', 'URL', 'Image URL', 'Base URL', 'Price'])
        writer.writerows(product_list)
    print(f"Saved {len(product_list)} items to local file: {file_name}")

# --- HTML Saving Function ---
def save_html_locally(product_list, file_name):
    """Saves the list of new products to a visual HTML file."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Newly Added Products</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; background-color: #f4f4f4; }
            .container { max-width: 1400px; margin: 20px auto; padding: 20px; }
            h1 { color: #333; }
            .grid-container {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 20px;
            }
            .product-card {
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 8px;
                overflow: hidden;
                text-decoration: none;
                color: #333;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .product-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .product-image {
                width: 100%;
                height: auto;
                aspect-ratio: 1 / 1;
                object-fit: cover;
            }
            .product-name {
                font-size: 0.9rem;
                font-weight: 600;
                padding: 10px 12px 5px 12px;
                overflow: hidden;
                text-overflow: ellipsis;
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
            }
            .product-price {
                font-size: 1rem;
                font-weight: 700;
                color: #e74c3c;
                padding: 5px 12px 10px 12px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Newly Added Products</h1>
            <p>Found <strong>""" + str(len(product_list)) + """</strong> new items.</p>
            <div class="grid-container">
    """
    
    for item in product_list:
        name = item[0]
        url = item[1]      # This is the full, clickable URL
        image_url = item[2]
        price = item[4] if len(item) > 4 else "N/A"  # Handle old data without price
        
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
    
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saved {len(product_list)} new items to visual HTML file: {file_name}")
    except Exception as e:
        print(f"Error saving HTML file: {e}")

# --- Main Function ---
def main():
    today_date = datetime.date.today()
    
    today_filename_csv = f"{today_date.isoformat()}-products.csv"
    new_items_filename_html = f"{today_date.isoformat()}-NEWLY-ADDED.html"

    # --- 1. RUN THE SCRAPE ---
    print(f"Starting scrape for {today_date.isoformat()}...")
    today_products_list = run_scrape()
    
    if not today_products_list:
        print("Scrape finished with no products. Exiting.")
        return
        
    print(f"\n=== SCRAPE COMPLETE ===")
    print(f"Found {len(today_products_list)} total unique products.")

    # --- 2. SAVE AND UPLOAD TODAY'S FULL CSV FILE ---
    save_csv_locally(today_products_list, today_filename_csv)
    
    print("\n--- Connecting to Google Drive ---")
    drive_service = authenticate_google_drive()
    
    if not drive_service:
        print("Could not authenticate with Google Drive. Exiting.")
        return
        
    upload_to_drive(drive_service, today_filename_csv, today_filename_csv, DRIVE_FOLDER_ID, 'text/csv')

    # --- 3. FIND AND DOWNLOAD LATEST FILE ---
    print(f"\n--- Starting Comparison ---")
    print(f"Searching for the most recent previous file...")
    previous_file_id = find_latest_product_file(drive_service, DRIVE_FOLDER_ID, today_filename_csv)
    
    if not previous_file_id:
        print("No previous file found. Cannot run comparison.")
        print("This is normal on the first run. The script will exit.")
        return

    previous_products_list = download_and_parse_csv(drive_service, previous_file_id)
    if not previous_products_list:
        print("Previous file was found but could not be read or was empty. Exiting.")
        return
    
    print(f"Successfully downloaded and parsed {len(previous_products_list)} items from previous file.")

    # --- 4. COMPARE AND SAVE NEW ITEMS ---
    
    # Create a lookup map for today's data (Base_URL -> [Name, Full_URL, Image_URL, Base_URL, Price])
    today_lookup_map = {row[3]: row for row in today_products_list}
    
    # Create a set of today's BASE URLs (index 3)
    set_today_urls = {row[3] for row in today_products_list}
    
    # --- Backwards-compatible logic for previous file ---
    set_previous_urls = set()
    if previous_products_list:
        num_cols = len(previous_products_list[0])
        print(f"Previous file has {num_cols} columns. Normalizing...")
        
        if num_cols >= 4: # It's a new 4-column or 5-column file
            set_previous_urls = {row[3] for row in previous_products_list if len(row) > 3}
        elif num_cols == 3: # It's an old 3-column file
            set_previous_urls = {row[1].split('?')[0] for row in previous_products_list if len(row) > 1}
            
    # This is the accurate comparison:
    new_item_base_urls = set_today_urls - set_previous_urls
    
    # Now, build the final list of new items using the lookup map
    new_items_list = [today_lookup_map[base_url] for base_url in new_item_base_urls]
    
    if not new_items_list:
        print("No new items found today.")
        print("\n=== All tasks complete. ===")
        return
        
    print(f"Comparison complete: Found {len(new_items_list)} new items!")

    # --- 5. SAVE AND UPLOAD THE "NEWLY-ADDED" HTML FILE ---
    save_html_locally(new_items_list, new_items_filename_html)
    
    upload_to_drive(drive_service, new_items_filename_html, new_items_filename_html, DRIVE_FOLDER_ID, 'text/html')
    
    # --- 6. AUTOMATICALLY OPEN THE HTML FILE ---
    print(f"Opening '{new_items_filename_html}' in your default browser...")
    try:
        file_path = os.path.abspath(new_items_filename_html)
        webbrowser.open_new_tab('file://' + file_path)
    except Exception as e:
        print(f"Error: Could not automatically open the file in your browser.")
        print(f"You can find it here: {file_path}")
        print(f"Details: {e}")
    
    print(f"\n=== All tasks complete. ===")

# --- This runs the main function when you execute the script ---
if __name__ == "__main__":

    main()

