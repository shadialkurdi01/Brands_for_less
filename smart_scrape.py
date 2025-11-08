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


# --- Google Drive Authentication and Upload ---
def authenticate_google_drive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refres
