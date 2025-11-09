import os
import csv
import time
import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
BASE_URL = "https://www.brandsforless.com/en-ae/c/women-10002"
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

PRODUCT_CARD_SELECTOR = "a[href*='/p/']"

def setup_chrome_driver():
    """Setup undetected Chrome for GitHub Actions."""
    print("Setting up undetected Chrome WebDriver...")
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        driver = uc.Chrome(options=options, version_main=None, use_subprocess=False)
        print("Chrome WebDriver setup successful!")
        return driver
    except Exception as e:
        print(f"Error: Could not set up Chrome Driver: {e}")
        return None

def scrape_page(driver, url, page_num):
    """Scrape one page."""
    print(f"Navigating to: {url}")
    driver.get(url)
    
    # Wait longer for Cloudflare to process
    print("Waiting for page to load (bypassing Cloudflare)...")
    time.sleep(8)
    
    # Save debug HTML
    debug_path = os.path.join(RESULTS_DIR, f"page_{page_num}_debug.html")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"Saved {debug_path} for inspection.")
    
    # Check if we're still on Cloudflare page
    if "Just a moment" in driver.page_source or "Verify you are human" in driver.page_source:
        print("WARNING: Still on Cloudflare challenge page!")
        return []
    
    # Wait for products to appear
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PRODUCT_CARD_SELECTOR))
        )
    except:
        print("Timeout waiting for products to load")
        return []
    
    # Scroll to load lazy content
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    elements = driver.find_elements(By.CSS_SELECTOR, PRODUCT_CARD_SELECTOR)
    products = []
    
    for el in elements:
        try:
            href = el.get_attribute("href")
            name = el.text.strip()
            if href and 'brandsforless.com' in href:
                products.append({"name": name if name else "No name", "url": href})
        except:
            continue
    
    print(f"Found {len(products)} products on page {page_num}")
    return products

def save_csv_locally(products):
    """Save products to CSV."""
    if not products:
        print("No products to save.")
        # Save empty CSV for debugging
        csv_path = os.path.join(RESULTS_DIR, "products.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "url"])
            writer.writeheader()
            writer.writerow({"name": "No products found", "url": "Check debug HTML files"})
        return
    
    today = datetime.date.today().isoformat()
    csv_path = os.path.join(RESULTS_DIR, f"{today}_products.csv")
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url"])
        writer.writeheader()
        writer.writerows(products)
    print(f"Saved {len(products)} products to {csv_path}")

def main():
    today_date = datetime.date.today()
    print(f"Starting scrape for {today_date.isoformat()}...")

    driver = setup_chrome_driver()
    if not driver:
        return

    all_products = []
    max_pages = 3  # Start with 3 pages for testing
    
    try:
        for page in range(1, max_pages + 1):
            url = f"{BASE_URL}?page={page}"
            print(f"\n--- Scraping page {page}/{max_pages} ---")
            
            products = scrape_page(driver, url, page)
            
            if not products:
                print(f"No products found on page {page}. Stopping.")
                break
            
            all_products.extend(products)
            print(f"Total products so far: {len(all_products)}")
            
            # Random delay between pages
            if page < max_pages:
                delay = 5 + (page * 2)
                print(f"Waiting {delay} seconds before next page...")
                time.sleep(delay)
        
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()
    
    print(f"\nDeduplicating {len(all_products)} total products...")
    unique = {p["url"]: p for p in all_products}
    print(f"After deduplication: {len(unique)} unique products")
    
    save_csv_locally(list(unique.values()))
    print("\nScrape finished successfully.")

if __name__ == "__main__":
    main()
