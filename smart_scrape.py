import os
import undetected_chromedriver as uc

def run_scrape():
    """Scrapes all pages and returns a list of [Name, Full_Link, Image_URL, Base_Link, Price]"""
    print("Setting up Chrome WebDriver...")

    driver = None  # Initialize as None

    try:
        options = uc.ChromeOptions()

        # --- Headless mode for GitHub Actions ---
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(
            'user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Detect if running in GitHub Actions
        if os.getenv('GITHUB_ACTIONS'):
            driver = uc.Chrome(
                options=options,
                version_main=None,
                use_subprocess=False
            )
        else:
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
            # --- Your scraping logic goes here ---
            pass  # placeholder for now

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


# ✅ Safe debug / execution section
if __name__ == "__main__":
    print("Current working directory:", os.getcwd())
    print("Files in directory:", os.listdir())
    run_scrape()
