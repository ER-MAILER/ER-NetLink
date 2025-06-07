import sys
import os
import csv
import uuid
import socket
import requests
import chardet
import base64
import random
import string
import pyfiglet
import firebase
import pyrebase
from PyQt5.QtGui import QColor, QPalette
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from colorama import init, Fore
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QTimer
import pdfkit
import logging
import time
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QMessageBox, QFileDialog,
    QRadioButton, QButtonGroup, QTextEdit, QTextBrowser, QHBoxLayout, QScrollArea, QProgressBar, QDialog, QFormLayout,
    QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5.QtCore import Qt, QSize
import subprocess
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO

# Check if QWebEngineView is available
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

# Initialize colorama for colored output
init(autoreset=True)

# Logging configuration to suppress less important messages
logger = logging.getLogger('pdfkit')
logger.setLevel(logging.ERROR)

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

# Configuration paths
CONTENT_DIR = './Content/'
CREDENTIAL_DIR = './Credential'

# Ensure the Content directory exists
if not os.path.exists(CONTENT_DIR):
    os.makedirs(CONTENT_DIR)

# Ensure the Credential directory exists
if not os.path.exists(CREDENTIAL_DIR):
    os.makedirs(CREDENTIAL_DIR)

# Determine if the script is running as a PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as EXE, use the _MEIPASS folder for the base path
    base_dir = sys._MEIPASS
else:
    # Running as script, use the current directory
    base_dir = os.path.dirname(os.path.realpath(__file__))

# Define the paths to wkhtmltopdf and wkhtmltoimage
wkhtmltopdf_path = os.path.join(base_dir, "wkhtmltopdf", "wkhtmltopdf.exe")
wkhtmltoimage_path = os.path.join(base_dir, "wkhtmltopdf", "wkhtmltoimage.exe")

# Add the wkhtmltopdf folder to the system PATH for DLLs
if os.path.exists(os.path.join(base_dir, "wkhtmltopdf")):
    os.environ['PATH'] += os.pathsep + os.path.join(base_dir, "wkhtmltopdf")

# Configure pdfkit with the custom path
pdf_config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

# Image and PDF format settings (default values)
class AttachmentSettings:
    def __init__(self):
        self.image_format = "jpg"
        self.pdf_format = "standard"
        
    def set_image_format(self, fmt):
        self.image_format = fmt.lower()
        
    def set_pdf_format(self, fmt):
        self.pdf_format = fmt.lower()

attachment_settings = AttachmentSettings()

# Function to generate an image using wkhtmltoimage while hiding the CMD window
def generate_image_without_cmd(html_content, output_filename):
    try:
        # Use subprocess to call wkhtmltoimage directly
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Build the command
        command = [wkhtmltoimage_path, '--quiet', '-', output_filename]

        # Run the command
        process = subprocess.Popen(command, stdin=subprocess.PIPE, startupinfo=startupinfo)
        process.communicate(input=html_content.encode('utf-8'))
        process.wait()

        return True
    except Exception as e:
        print(f"Error generating image: {e}")
        return False

def optimize_pdf_attachment(file_path):
    """PDF অ্যাটাচমেন্টকে আরও বাস্তবসম্মত এবং লিগিটিমেট দেখানোর জন্য অপ্টিমাইজেশন"""
    try:
        doc = fitz.open(file_path)
        
        # রিয়েলিস্টিক মেটাডাটা অ্যাড করুন
        meta = {
            "producer": "Microsoft® Word 2016",
            "creator": "Microsoft® Word 2016",
            "creationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
            "modDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
            "title": "Document_" + str(random.randint(1000, 9999)),
            "author": random.choice(["John Smith", "Sarah Johnson", "Michael Brown"]),
            "subject": "Important Document",
            "keywords": "document, important"
        }
        
        doc.set_metadata(meta)
        
        # PDF ট্রেলার অপ্টিমাইজেশন
        trailer = "\n".join([
            "%%EOF",
            "%%DocumentProcessColors: Cyan Magenta Yellow Black",
            "%%DocumentSuppliedResources: procset Adobe_ColorImage_CMYK",
            "%%+ procset Adobe_Illustrator_AI3",
            "%%+ procset Adobe_PS5_ColorImage_Binary",
            "%%Creator: Microsoft® Word 2016"
        ])
        
        # Save with different compression based on selected format
        if attachment_settings.pdf_format == "raw":
            # Minimal compression for "raw" format
            output_path = os.path.join(CONTENT_DIR, f"optimized_{os.path.basename(file_path)}")
            doc.save(output_path, deflate=False, garbage=0)
        else:
            # Standard compression
            output_path = os.path.join(CONTENT_DIR, f"optimized_{os.path.basename(file_path)}")
            doc.save(output_path, deflate=True)
        
        doc.close()
        
        # Replace original file
        os.remove(file_path)
        os.rename(output_path, file_path)
        
        return True
        
    except Exception as e:
        print(f"PDF optimization error: {str(e)}")
        return False

def optimize_image_attachment(file_path):
    """ইমেজ অ্যাটাচমেন্টকে আরও বাস্তবসম্মত দেখানোর জন্য অপ্টিমাইজেশন"""
    try:
        with Image.open(file_path) as img:
            # Convert to selected format
            output_path = os.path.join(CONTENT_DIR, f"optimized_{os.path.basename(file_path)}")
            
            if attachment_settings.image_format in ["jpg", "jpeg"]:
                img.save(output_path, 
                       format='JPEG',
                       quality=random.randint(85, 95),
                       optimize=True,
                       progressive=True)
            elif attachment_settings.image_format == "png":
                img.save(output_path, format='PNG', compress_level=6)
            elif attachment_settings.image_format == "gif":
                img.save(output_path, format='GIF')
            elif attachment_settings.image_format == "bmp":
                img.save(output_path, format='BMP')
            elif attachment_settings.image_format in ["raw", "cr2", "nef", "arw", "dng"]:
                # For RAW formats, we'll save as TIFF which is closest
                img.save(output_path.replace('.jpg', '.tiff'), format='TIFF')
                output_path = output_path.replace('.jpg', '.tiff')
            
            # Replace original file
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(output_path, file_path)
            
            return True
            
    except Exception as e:
        print(f"Image optimization error: {str(e)}")
        return False

def generate_legitimate_filename(extension):
    """সন্দেহজনক না দেখায় এমন ফাইলনেম জেনারেট করুন"""
    prefixes = [
        "Document", "Report", "Invoice", "Statement",
        "Notice", "Letter", "Presentation", "Proposal"
    ]
    
    suffixes = [
        "Final", "Revised", "Updated", "Draft",
        "Confidential", "V2", "Approved", "Signed"
    ]
    
    prefix = random.choice(prefixes)
    suffix = random.choice(suffixes)
    number = random.randint(1, 20)
    
    return f"{prefix}_{suffix}_{number}.{extension}"

def html_to_pdf_advanced(html_content, replacements):
    """HTML থেকে PDF জেনারেট করার উন্নত মেথড"""
    try:
        html_content = replace_shortcuts(html_content, replacements)
        
        # PDF অপশনস সেট করুন
        options = {
            'quiet': '',
            'encoding': "UTF-8",
            'no-outline': None,
            'margin-top': '0.5in',
            'margin-right': '0.5in',
            'margin-bottom': '0.5in',
            'margin-left': '0.5in',
            'footer-center': f'Page [page] of [topage] - {datetime.now().year}',
            'footer-font-size': '8',
            'footer-font-name': 'Arial',
            'javascript-delay': '1000',
            'enable-local-file-access': '',
            'load-error-handling': 'ignore'
        }
        
        # Special options for different PDF formats
        if attachment_settings.pdf_format == "pdfa":
            options['pdfa'] = None
        elif attachment_settings.pdf_format == "pdfx":
            options['pdfx'] = None
        
        # লিগিটিমেট ফাইলনেম জেনারেট করুন
        filename = generate_legitimate_filename("pdf")
        output_path = os.path.join(CONTENT_DIR, filename)
        
        # PDF জেনারেট করুন
        pdfkit.from_string(html_content, output_path, 
                          configuration=pdf_config,
                          options=options)
        
        # PDF অপ্টিমাইজ করুন
        optimize_pdf_attachment(output_path)
        
        print(Fore.GREEN + f"PDF successfully generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(Fore.RED + f"Failed to generate PDF: {str(e)}")
        return None

def html_to_image_advanced(html_content, replacements):
    """HTML থেকে ইমেজ জেনারেট করার উন্নত মেথড"""
    try:
        html_content = replace_shortcuts(html_content, replacements)
        
        # লিগিটিমেট ফাইলনেম জেনারেট করুন
        filename = generate_legitimate_filename(attachment_settings.image_format)
        output_path = os.path.join(CONTENT_DIR, filename)
        
        # Temporary file for initial generation
        temp_path = os.path.join(CONTENT_DIR, f"temp_{generate_unique_filename()}.jpg")
        
        # ইমেজ জেনারেট করুন
        if generate_image_without_cmd(html_content, temp_path):
            # ইমেজ অপ্টিমাইজ করুন
            optimize_image_attachment(temp_path)
            
            # Rename to final path if needed
            if temp_path != output_path:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_path, output_path)
                
            print(Fore.GREEN + f"Image successfully generated: {output_path}")
            return output_path
        else:
            print(Fore.RED + "Failed to generate image.")
            return None
            
    except Exception as e:
        print(Fore.RED + f"An error occurred: {str(e)}")
        return None

def simulate_warmup(service, sender_email):
    """Simulate SMTP warmup by sending test emails"""
    try:
        # Send initial warmup email
        warmup_msg = MIMEMultipart()
        warmup_msg['From'] = sender_email
        warmup_msg['To'] = sender_email
        warmup_msg['Subject'] = "Server Warmup Test"
        warmup_msg.attach(MIMEText("This is a warmup email to establish sender reputation.", 'plain'))
        
        raw_msg = base64.urlsafe_b64encode(warmup_msg.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_msg}).execute()
        
        # Random delay between 0.8-1.5 seconds
        time.sleep(random.uniform(0.8, 1.5))
        
        # Send second warmup email with different content
        warmup_msg2 = MIMEMultipart()
        warmup_msg2['From'] = sender_email
        warmup_msg2['To'] = sender_email
        warmup_msg2['Subject'] = "Test Message"
        warmup_msg2.attach(MIMEText("Another warmup message to improve IP reputation.", 'plain'))
        
        raw_msg2 = base64.urlsafe_b64encode(warmup_msg2.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_msg2}).execute()
        
    except Exception as e:
        print(f"Warmup simulation failed: {str(e)}")

# Utility functions
def generate_unique_filename():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))

def generate_dynamic_replacements(recipient_email, sender_name):
    """Generate personalized dynamic replacements for email content"""
    # Sample addresses data
    addresses = [
        "1358 Elm Street\nSpringfield, IL 62704",
        "5678 Oak Avenue\nAustin, TX 73301",
        "9101 Maple Drive\nDenver, CO 80202"
    ]
    
    regards_names = ["Alex John", "Emily Smith", "Michael Brown", "Sophia Johnson"]
    
    try:
        first_name = recipient_email.split('@')[0].split('.')[0].title()
        current_hour = datetime.now().hour
        greeting = "Good morning" if 5 <= current_hour < 12 else \
                  "Good afternoon" if 12 <= current_hour < 17 else \
                  "Good evening"

        return {
            '#KEY#': str(uuid.uuid4()),
            '#DATE#': datetime.now().strftime("%b %d, %Y"),
            '#DAY#': datetime.now().strftime("%A"),
            '#EMAIL#': recipient_email,
            '#NAME#': recipient_email.split('@')[0].replace('.', ' ').title(),
            '#FIRSTNAME#': first_name,
            '#GREETING#': greeting,
            '#TIME#': datetime.now().strftime("%I:%M %p"),
            '#INVOICE#': ''.join(random.choices(string.ascii_uppercase + string.digits, k=18)),
            '#INVOICENUMBER#': f"INV-{random.randint(100000000000, 999999999999)}",
            '#NUMBER#': str(random.randint(1000000000, 999999999999)),
            '#SNUMBER#': f"SNU-{random.randint(1000000000, 9999999999)}",
            '#LETTERS#': ''.join(random.choices(string.ascii_uppercase, k=16)),
            '#RANDOM#': ''.join(random.choices(string.ascii_letters + string.digits, k=15)),
            '#REGARDS#': random.choice(regards_names),
            '#ADDRESS#': random.choice(addresses),
            '#AMOUNT#': f"$ {random.uniform(200, 1000):.2f}",
            '#ABC#': f"POWFG-{random.randint(10000, 99999)}-POY",
            '#COMPANY#': random.choice(["Company", "Organization", "Team", "Group"]),
            '#CITY#': random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
            '#PRODUCT#': random.choice(["service", "product", "solution", "offer"])
        }
    except Exception as e:
        print(f"Error generating replacements: {str(e)}")
        return {}

def replace_shortcuts(content, replacements):
    """Replace all shortcuts in the content with their corresponding values"""
    if not content or not replacements:
        return content
    
    try:
        for shortcut, value in replacements.items():
            content = content.replace(shortcut, str(value))
        return content
    except Exception as e:
        print(f"Error replacing shortcuts: {str(e)}")
        return content

def check_for_spam_words(content):
    """Check content for common spam trigger words"""
    spam_words = [
        "free", "win", "prize", "urgent", "guarantee", 
        "risk-free", "act now", "limited time", "click here"
    ]
    
    found_words = [word for word in spam_words if word.lower() in content.lower()]
    return found_words if found_words else None

def generate_random_ip_headers():
    """Generate varying X-Originating-IP headers"""
    octets = [str(random.randint(1, 255)) for _ in range(4)]
    return ".".join(octets)

def add_email_authentication_headers(message, sender_email):
    """Add email authentication headers to improve deliverability"""
    domain = sender_email.split('@')[-1]
    message['DKIM-Signature'] = f"v=1; a=rsa-sha256; d={domain}; s=selector1;"
    message['Authentication-Results'] = f"spf=pass smtp.mailfrom={domain}; dkim=pass header.d={domain}; dmarc=pass"
    message['Received-SPF'] = "Pass (sender SPF authorized)"
    return message

def add_improved_headers(message, sender_email, campaign_id=None):
    """Add professional email headers with automatic domain detection"""
    domain = sender_email.split('@')[-1]
    if not campaign_id:
        campaign_id = f"campaign-{random.randint(100000, 999999)}"
    
    message['X-Entity-Ref-ID'] = str(uuid.uuid4())
    message['List-Unsubscribe'] = f"<mailto:unsubscribe@{domain}?subject=Unsubscribe>, <https://{domain}/unsubscribe>"
    message['Precedence'] = "bulk"
    message['X-Campaign-ID'] = campaign_id
    message['X-Sender-IP'] = get_public_ip()
    message['X-Report-Abuse'] = f"Please report abuse to abuse@{domain}"
    return message

def get_public_ip():
    """Get the public IP address of the sender"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            return response.json()['ip']
    except:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "unknown"

class AuthWorker(QThread):
    finished = pyqtSignal(object, str)  # Signal to return service and email
    error = pyqtSignal(str)  # Signal to return error message

    def __init__(self, json_file_path):
        super().__init__()
        self.json_file_path = json_file_path

    def run(self):
        try:
            # Check if JSON file exists
            if not os.path.exists(self.json_file_path):
                self.error.emit(f"JSON file not found at {self.json_file_path}")
                return

            # Use the same name as the imported json file but with .token extension
            token_filename = os.path.basename(self.json_file_path).replace('.json', '.token')
            token_path = os.path.join(CREDENTIAL_DIR, token_filename)
            
            creds = None
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.json_file_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            email = profile['emailAddress']
            
            # Perform warmup sequence
            simulate_warmup(service, email)
            
            self.finished.emit(service, email)
        except Exception as e:
            self.error.emit(f"Authentication failed: {str(e)}")

class EmailWorker(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, service, email, email_data_path, name_input, subject_input, body_input, html_input, attachment_format, body_mode):
        super().__init__()
        self.service = service
        self.email = email
        self.email_data_path = email_data_path
        self.name_input = name_input
        self.subject_input = subject_input
        self.body_input = body_input
        self.html_input = html_input
        self.attachment_format = attachment_format
        self.body_mode = body_mode
        self.stop_sending = False
        self.template_cache = {}
        self.sender_names = []
        self.subjects = []
        self.pdf_options = {
            'quiet': '',
            'no-stop-slow-scripts': '',
            'javascript-delay': '1000',
            'enable-local-file-access': '',
            'load-error-handling': 'ignore'
        }

    def run(self):
        try:
            # Preload all data before processing emails
            self._preload_all_data()

            # Read email data
            data_reader = self._read_email_data()
            if not data_reader:
                self.status.emit("[ ERROR ] Failed to read email data!")
                return

            total_emails = len(data_reader)
            self.progress.emit(0)

            # Process emails with controlled timing
            for i, data_row in enumerate(data_reader):
                if self.stop_sending:
                    self.status.emit("Email sending stopped by user")
                    break

                if len(data_row) < 1:
                    continue

                start_time = time.time()
                recipient = data_row[0].strip()

                # Process email
                success = self._process_single_email(i, total_emails, recipient)
                if not success:
                    continue

                # Enforce minimum delay between emails
                processing_time = time.time() - start_time
                sleep_time = max(0.8 - processing_time, 0)
                time.sleep(sleep_time)

                # Update progress
                progress_percentage = int(((i + 1) / total_emails) * 100)
                self.progress.emit(progress_percentage)
                QApplication.processEvents()

            self.finished.emit()
        except Exception as e:
            self.status.emit(f"[ ERROR ] {str(e)}")

    def _preload_all_data(self):
        """Preload all necessary data before processing emails"""
        # Preload sender names
        if os.path.isfile(self.name_input):
            self.sender_names = self._load_data_file(self.name_input)
        else:
            self.sender_names = [self.name_input]

        # Preload subjects
        if os.path.isfile(self.subject_input):
            self.subjects = self._load_data_file(self.subject_input)
        else:
            self.subjects = [self.subject_input]

    def _load_data_file(self, file_path):
        """Load data from file (CSV, TXT, or XLSX)"""
        try:
            if file_path.endswith('.csv'):
                with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
                    return [row[0] for row in csv.reader(f) if row]
            elif file_path.endswith('.txt'):
                with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
                    return [line.strip() for line in f.readlines() if line.strip()]
            elif file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
                return df.iloc[:, 0].tolist()
        except Exception as e:
            self.status.emit(f"[ WARNING ] Error loading file {file_path}: {str(e)}")
            return []

    def _read_email_data(self):
        """Read email data from file"""
        try:
            if self.email_data_path.endswith('.csv'):
                with open(self.email_data_path, mode='r', encoding='utf-8', errors='replace') as f:
                    return list(csv.reader(f))
            elif self.email_data_path.endswith('.txt'):
                with open(self.email_data_path, mode='r', encoding='utf-8', errors='replace') as f:
                    return [line.strip().split(',') for line in f.readlines()]
            elif self.email_data_path.endswith('.xlsx'):
                df = pd.read_excel(self.email_data_path)
                return df.values.tolist()
        except Exception as e:
            self.status.emit(f"[ ERROR ] Failed to read email data: {str(e)}")
            return None

    def _process_single_email(self, index, total, recipient):
        """Process and send a single email"""
        try:
            # Get sender name and subject
            sender_name = random.choice(self.sender_names)
            subject = random.choice(self.subjects)

            # Generate replacements
            replacements = generate_dynamic_replacements(recipient, sender_name)

            # Process templates with caching
            processed_subject = self._process_template(subject, replacements)
            processed_body = self._process_template(self.body_input, replacements)
            processed_html = self._process_template(self.html_input, replacements)

            # Check for spam words
            spam_words = check_for_spam_words(processed_body) or check_for_spam_words(processed_html)
            if spam_words:
                self.status.emit(f'<font color="orange">[ WARNING ] Spam words detected for {recipient}: {", ".join(spam_words)}</font>')

            # Create and send email
            if self.attachment_format == "none":
                # Fast path for no attachments
                self._send_email_without_attachments(
                    sender_name,
                    recipient,
                    processed_subject,
                    processed_body,
                    processed_html
                )
            else:
                # Handle attachments
                self._send_email_with_attachments(
                    sender_name,
                    recipient,
                    processed_subject,
                    processed_body,
                    processed_html
                )

            self.status.emit(f"[ {index+1}/{total} ] Successfully Sent to {recipient}")
            return True

        except Exception as e:
            self.status.emit(f'<font color="red">[ {index+1}/{total} ] Failed send to {recipient}: {str(e)}</font>')
            return False

    def _process_template(self, template, replacements):
        """Process template with replacements using caching"""
        cache_key = hash(template + str(replacements))
        if cache_key not in self.template_cache:
            self.template_cache[cache_key] = replace_shortcuts(template, replacements)
        return self.template_cache[cache_key]

    def _send_email_without_attachments(self, sender_name, recipient, subject, body, html_content):
        """Optimized path for emails without attachments"""
        message = MIMEMultipart()
        
        # Add all authentication and improved headers
        message = add_email_authentication_headers(message, self.email)
        message = add_improved_headers(message, self.email)
        
        # Standard headers
        message['From'] = f'{sender_name} <{self.email}>'
        message['To'] = recipient
        message['Subject'] = subject
        message['X-Priority'] = "1"
        message['X-Originating-IP'] = generate_random_ip_headers()
        message['Return-Path'] = self.email
        message['Reply-To'] = self.email

        if self.body_mode == "html":
            message.attach(MIMEText(body, 'html'))
        else:
            message.attach(MIMEText(body, 'plain'))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {'raw': raw_message}
        self.service.users().messages().send(userId='me', body=message_body).execute()

    def _send_email_with_attachments(self, sender_name, recipient, subject, body, html_content):
        """Handle emails with all new improvements"""
        message = MIMEMultipart()
    
        # Add all authentication and improved headers
        message = add_email_authentication_headers(message, self.email)
        message = add_improved_headers(message, self.email)
        
        # Standard headers
        message['From'] = f'{sender_name} <{self.email}>'
        message['To'] = recipient
        message['Subject'] = subject
        message['X-Priority'] = "1"
        message['X-Originating-IP'] = generate_random_ip_headers()
        message['Return-Path'] = self.email
        message['Reply-To'] = self.email

        # Add body based on mode
        if self.attachment_format == "inline":
            message.attach(MIMEText(html_content, 'html'))
        else:
            if self.body_mode == "html":
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))

        # Handle attachments with optimization
        if self.attachment_format == "pdf":
            pdf_path = html_to_pdf_advanced(html_content, {})
            if pdf_path:
                with open(pdf_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
                    message.attach(part)
                os.remove(pdf_path)
            
        elif self.attachment_format == "jpg":
            image_path = html_to_image_advanced(html_content, {})
            if image_path:
                with open(image_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(image_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(image_path)}"'
                    message.attach(part)
                os.remove(image_path)

        # Send the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {'raw': raw_message}
        
        try:
            self.service.users().messages().send(userId='me', body=message_body).execute()
        except HttpError as error:
            self.status.emit(f'<font color="red">[ ERROR ] API error: {str(error)}</font>')

    def stop(self):
        self.stop_sending = True

class ImageFormatDialog(QDialog):
    # Keep track of last selected format (class-level)
    selected_format = "bmp"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Image Format")
        self.setFixedSize(300, 250)
        self.setWindowIcon(QIcon(r'ec\icon.ico'))

        layout = QVBoxLayout()
        group_box = QGroupBox("Available Image Formats")
        group_layout = QVBoxLayout()

        self.formats = {
            "jpeg": QCheckBox("JPEG"),
            "png": QCheckBox("PNG"),
            "gif": QCheckBox("GIF"),
            "bmp": QCheckBox("BMP"),
            "raw": QCheckBox("RAW (.raw, .cr2, .nef)"),
            "dng": QCheckBox("Adobe DNG")
        }

        # Set previously selected format as checked
        if ImageFormatDialog.selected_format in self.formats:
            self.formats[ImageFormatDialog.selected_format].setChecked(True)

        for fmt in self.formats.values():
            group_layout.addWidget(fmt)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)

        layout.addLayout(button_box)
        self.setLayout(layout)

    def get_selected_format(self):
        for fmt_name, checkbox in self.formats.items():
            if checkbox.isChecked():
                ImageFormatDialog.selected_format = fmt_name  # save selection
                return fmt_name
        return ImageFormatDialog.selected_format

class PdfFormatDialog(QDialog):
    selected_format = "raw"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select PDF Format")
        self.setFixedSize(300, 300)
        self.setWindowIcon(QIcon(r'ec\icon.ico'))

        layout = QVBoxLayout()
        group_box = QGroupBox("Available PDF Formats")
        group_layout = QVBoxLayout()

        self.formats = {
            "standard": QCheckBox("Standard PDF"),
            "raw": QCheckBox("RAW PDF (Minimal Compression)"),
            "pdfa": QCheckBox("PDF/A (Archival)"),
            "pdfx": QCheckBox("PDF/X (Printing)"),
            "pdfe": QCheckBox("PDF/E (Engineering)"),
            "pdfua": QCheckBox("PDF/UA (Accessibility)"),
            "interactive": QCheckBox("Interactive PDF")
        }

        # Set previously selected format as checked
        if PdfFormatDialog.selected_format in self.formats:
            self.formats[PdfFormatDialog.selected_format].setChecked(True)

        for fmt in self.formats.values():
            group_layout.addWidget(fmt)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)

        layout.addLayout(button_box)
        self.setLayout(layout)

    def get_selected_format(self):
        for fmt_name, checkbox in self.formats.items():
            if checkbox.isChecked():
                PdfFormatDialog.selected_format = fmt_name
                return fmt_name
        return PdfFormatDialog.selected_format


# Firebase Configuration
firebase_config = {
    "apiKey": "AIzaSyCasCG96aP6kzQptuOp82CKHj3JK9nyrHc",
    "authDomain": "er-mailer.firebaseapp.com",
    "databaseURL": "https://er-mailer-default-rtdb.firebaseio.com",
    "projectId": "er-mailer",
    "storageBucket": "er-mailer.appspot.com",
    "messagingSenderId": "19117499773",
    "appId": "1:19117499773:web:60ed4e74d61baf7b8b1814"
}

# Initialize Firebase with additional config
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

class SessionManager(QObject):
    logout_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.device_id = str(uuid.getnode())
        self.firebase_config = {
            "apiKey": "AIzaSyCasCG96aP6kzQptuOp82CKHj3JK9nyrHc",
            "authDomain": "er-mailer.firebaseapp.com",
            "databaseURL": "https://er-mailer-default-rtdb.firebaseio.com",
            "projectId": "er-mailer",
            "storageBucket": "er-mailer.appspot.com",
            "messagingSenderId": "19117499773",
            "appId": "1:19117499773:web:60ed4e74d61baf7b8b1814"
        }
        self.firebase = pyrebase.initialize_app(self.firebase_config)
        self.auth = self.firebase.auth()
        self.db = self.firebase.database()
        self.session_ref_path = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_last_active)
        self.cleanup_done = False
        self.poll_timer = None

    def initialize_session(self, user):
        try:
            self.current_user = user
            user_info = self.auth.get_account_info(user['idToken'])
            uid = user_info['users'][0]['localId']
            email = user_info['users'][0]['email']

            session_data = {
                'device_id': self.device_id,
                'status': 'active',
                'last_active': int(time.time() * 1000),
                'ip_address': self._get_ip_address(),
                'app_version': 'V5.0.9',
                'user_email': email
            }

            # Write with token for security
            self.db.child("users").child(uid).child("sessions").child(self.device_id).set(
                session_data, 
                token=user['idToken']
            )
            
            self.session_ref_path = f"users/{uid}/sessions/{self.device_id}"
            self.update_timer.start(30000)  # 30 seconds interval
            self.start_polling(uid)

        except Exception as e:
            error_msg = f"Session initialization error: {str(e)}"
            print(error_msg)
            raise RuntimeError(error_msg)

    def update_last_active(self):
        if self.current_user and self.session_ref_path:
            try:
                self.db.child(self.session_ref_path).update(
                    {'last_active': int(time.time() * 1000)},
                    token=self.current_user['idToken']
                )
            except Exception as e:
                print(f"Update error: {str(e)}")

    def start_polling(self, uid):
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(lambda: self.poll_session_status(uid))
        self.poll_timer.start(30000)  # 30 seconds interval

    def poll_session_status(self, uid):
        try:
            # Check user status
            user_status = self.db.child("users").child(uid).child("status").get(
                token=self.current_user['idToken']
            ).val()
            
            if user_status == 'inactive':
                self.logout_signal.emit("Your account has been deactivated")
                return
            elif user_status is None:
                self.logout_signal.emit("Account not found")
                return

            # Check session status
            session_status = self.db.child("users").child(uid).child("sessions").child(
                self.device_id).child("status").get(
                token=self.current_user['idToken']
            ).val()
            
            if session_status == 'terminated':
                self.logout_signal.emit("Session terminated by admin")
            elif session_status is None:
                self.logout_signal.emit("Session expired")

        except Exception as e:
            print(f"Polling error: {str(e)}")

    def logout(self, normal_logout=True):
        try:
            if self.update_timer and self.update_timer.isActive():
                self.update_timer.stop()
            if self.poll_timer and self.poll_timer.isActive():
                self.poll_timer.stop()

            if not self.cleanup_done and self.current_user and self.session_ref_path:
                self.db.child(self.session_ref_path).update(
                    {'status': 'inactive', 'last_active': int(time.time() * 1000)},
                    token=self.current_user['idToken']
                )
        except Exception as e:
            print(f"Logout error: {str(e)}")
        finally:
            self.current_user = None
            self.session_ref_path = None
            self.cleanup_done = True

    def _get_ip_address(self):
        try:
            return requests.get('https://api.ipify.org', timeout=5).text
        except:
            return "unknown"


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.session_manager.logout_signal.connect(self.force_logout)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("ER MAILER-2 [ V5.0.9 ]")
        self.setFixedSize(400, 220)
        self.setWindowIcon(QIcon(r'ec\icon.ico'))
        
        self.setStyleSheet("""
            QDialog {
                background-color: #06121d;
            }
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #00242e;
                color: white;
                border: 1px solid #00444f;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #00ff99;
                color: black;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00cc77;
            }
        """)

        layout = QVBoxLayout()

        title = QLabel("Login ER User")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form_layout = QVBoxLayout()
        
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        
        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        login_btn = QPushButton("Login")
        login_btn.setFixedSize(80, 30)
        login_btn.clicked.connect(self.check_credentials)
        
        button_layout.addWidget(login_btn)
        layout.addLayout(button_layout)

        footer = QLabel("© ER MAILER-2 | VERSION: V5.0.9")
        footer.setFont(QFont("Arial", 10))
        footer.setAlignment(Qt.AlignLeft)
        footer.setStyleSheet("color: #00ff99;")
        layout.addWidget(footer)

        self.setLayout(layout)

    def check_credentials(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Login Failed", "Email and password required")
            return

        try:
            # Firebase authentication
            user = self.session_manager.auth.sign_in_with_email_and_password(email, password)
            
            # Verify token
            user_info = self.session_manager.auth.get_account_info(user['idToken'])
            uid = user_info['users'][0]['localId']
            
            # Check existing sessions
            sessions = self.session_manager.db.child("users").child(uid).child("sessions").get(
                token=user['idToken']
            ).val() or {}
            
            # Handle multiple sessions
            active_sessions = [sid for sid, data in sessions.items() 
                             if data.get('status') == 'active' 
                             and sid != self.session_manager.device_id]
            
            if active_sessions:
                reply = QMessageBox.question(
                    self,
                    "Active Session",
                    "Terminate other sessions?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    for sid in active_sessions:
                        self.session_manager.db.child("users").child(uid).child("sessions").child(sid).update(
                            {'status': 'terminated'},
                            token=user['idToken']
                        )
                else:
                    return
            
            # Initialize new session
            self.session_manager.initialize_session(user)
            self.show_login_success()
            self.accept()
            
        except Exception as e:
            self.handle_login_error(e)

    def show_login_success(self):
        msg = QMessageBox()
        msg.setWindowTitle("ACCESS GRANTED")
        msg.setWindowIcon(QIcon(r'ec\icon.ico'))
        
        message = """
        <div style='color:#00ff99;font-size:18px;font-weight:bold;text-align:center;'>
            ✔ LOGIN SUCCESSFUL
        </div>
        <div style='font-size:13px;margin:15px 0;'>
            Welcome to <b>ER MAILER-2 V5.0.9</b><br><br>
            <b>Developed by:</b> E-R<br>
            <b>Contact:</b> er.mailer2@gmail.com
        </div>
        <div style='color:#ff9966;font-weight:bold;border-top:1px solid #00444f;padding-top:10px;'>
            IMPORTANT: For authorized use only
        </div>
        """
        
        msg.setText(message)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #06121d;
                border: 2px solid #00ff99;
            }
            QPushButton {
                min-width: 80px;
            }
        """)
        msg.exec_()

    def handle_login_error(self, error):
        error_msg = str(error)
        
        if "INVALID_EMAIL" in error_msg or "INVALID_PASSWORD" in error_msg:
            msg = "Invalid email or password"
        elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
            msg = "Too many attempts. Please try again later."
        elif "EMAIL_NOT_FOUND" in error_msg:
            msg = "Email not registered"
        else:
            msg = f"Login error: {error_msg}"
            
        QMessageBox.warning(self, "Login Failed", msg)

    def force_logout(self, message):
        try:
            QMessageBox.critical(self, "Session Terminated", message)
            self.session_manager.logout(normal_logout=False)
            QApplication.instance().quit()
        except Exception as e:
            print(f"Error in force logout: {str(e)}")
            try:
                QApplication.instance().quit()
            except:
                os._exit(1)

    def closeEvent(self, event):
        try:
            self.session_manager.cleanup_on_exit()
        except Exception as e:
            print(f"Error during close event: {str(e)}")
        super().closeEvent(event)

# PyQt GUI
class EmailSenderApp(QMainWindow):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.task_windows = []
        self.initUI()
        self.email_worker = None  # EmailWorker instance
        self.auth_worker = None  # AuthWorker instance

        # Set window icon
        self.setWindowIcon(QIcon(r'ec\icon.ico'))  # Set the window icon

    def on_auth_error(self, error_message):
        self.show_message("Authentication Error", error_message, QMessageBox.Critical)
        self.send_button.setText("Send Emails")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #008000;
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #006600;
            }
        """)

    def initUI(self):
        self.setWindowTitle("ER MAILER-2 [ V5.0.9 ]")
        self.setGeometry(100, 100, 900, 600)  # Wider window to accommodate status box

        # Set background color and style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #06121d;
            }
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #00242e;
                color: white;
                border: 1px solid #00444f;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #00ff99;
                color: black;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00cc77;
            }
            QTextEdit {
                background-color: #00242e;
                color: white;
                border: 1px solid #00444f;
                padding: 5px;
                font-size: 12px;
            }
            QProgressBar {
                background-color: #00242e;
                color: white;
                border: 1px solid #00444f;
                padding: 5px;
                font-size: 12px;
            }
            QRadioButton {
                color: white;
                font-size: 12px;
            }
            QMessageBox {
                background-color: #06121d;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #00ff99;
                color: black;
                border-radius: 5px;
                font-size: 12px;
                padding: 5px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00cc77;
            }
        """)

        # Main horizontal layout
        main_h_layout = QHBoxLayout()
        left_v_layout = QVBoxLayout()
        right_v_layout = QVBoxLayout()

        # Title Label and Reset Button (Top Left Corner)
        self.title_label = QLabel("                    ER Mailer 2")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #00ff99; text-align: center;")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setStyleSheet("background-color: #FF5733; color: white; font-size: 12px; padding: 2px;")
        self.reset_button.setFixedSize(60, 30)  # Small size
        self.reset_button.clicked.connect(self.reset_application)

        # Contact Button
        self.contact_button = QPushButton("Contact")
        self.contact_button.setStyleSheet("background-color: #FFC107; color: white; font-size: 12px; padding: 2px;")
        self.contact_button.setFixedSize(60, 30)
        self.contact_button.clicked.connect(self.show_contact)

        # Hashtag Button
        self.hashtag_button = QPushButton("Hashtag")
        self.hashtag_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 12px; padding: 2px;")
        self.hashtag_button.setFixedSize(60, 30)
        self.hashtag_button.clicked.connect(self.show_hashtag)

        # Add Task Button
        self.add_task_button = QPushButton("Add Task")
        self.add_task_button.setStyleSheet("background-color: #9C27B0; color: white; font-size: 12px; padding: 2px;")
        self.add_task_button.setFixedSize(60, 30)
        self.add_task_button.clicked.connect(self.add_task)

        # Title Layout
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.reset_button, alignment=Qt.AlignLeft)
        title_layout.addWidget(self.contact_button, alignment=Qt.AlignLeft)
        title_layout.addWidget(self.hashtag_button, alignment=Qt.AlignLeft)
        title_layout.addWidget(self.add_task_button, alignment=Qt.AlignLeft)
        title_layout.addWidget(self.title_label, alignment=Qt.AlignCenter)
        left_v_layout.addLayout(title_layout)

        # Sender Name & Browse Button (Horizontal Layout)
        name_layout = QHBoxLayout()
        self.name_label = QLabel("NAME")
        self.name_label.setStyleSheet("font-size: 12px; color: white;")
        self.name_input = QLineEdit()
        self.name_input.setFixedWidth(300)
        self.name_input.setStyleSheet("font-size: 12px; padding: 3px;")
        self.name_button = QPushButton("LOAD NAME")
        self.name_button.setFixedWidth(250)
        self.name_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 12px; padding: 4px;")
        self.name_button.clicked.connect(self.browse_name_file)

        # Add name field and button to the name_layout (horizontal)
        name_layout.addWidget(self.name_label)
        name_layout.addWidget(self.name_input)
        name_layout.addWidget(self.name_button)

        # Subject & Browse Button (Horizontal Layout)
        subject_layout = QHBoxLayout()
        self.subject_label = QLabel("SUBJECT")
        self.subject_label.setStyleSheet("font-size: 12px; color: white;")
        self.subject_input = QLineEdit()
        self.subject_input.setFixedWidth(300)
        self.subject_input.setStyleSheet("font-size: 12px; padding: 3px;")
        self.subject_button = QPushButton("LOAD SUBJECT")
        self.subject_button.setFixedWidth(250)
        self.subject_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 12px; padding: 4px;")
        self.subject_button.clicked.connect(self.browse_subject_file)

        # Add subject field and button to the subject_layout (horizontal)
        subject_layout.addWidget(self.subject_label)
        subject_layout.addWidget(self.subject_input)
        subject_layout.addWidget(self.subject_button)

        # Email Data & Browse Button (Horizontal Layout)
        email_layout = QHBoxLayout()
        self.email_label = QLabel("DATA")
        self.email_label.setStyleSheet("font-size: 12px; color: white;")
        self.email_input = QLineEdit()
        self.email_input.setFixedWidth(300)
        self.email_input.setStyleSheet("font-size: 12px; padding: 3px;")
        self.email_button = QPushButton("LOAD DATA")
        self.email_button.setFixedWidth(250)
        self.email_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 12px; padding: 4px;")
        self.email_button.clicked.connect(self.browse_email)

        # Add email field and button to the email_layout (horizontal)
        email_layout.addWidget(self.email_label)
        email_layout.addWidget(self.email_input)
        email_layout.addWidget(self.email_button)

        # JSON File & Browse Button (Horizontal Layout)
        json_layout = QHBoxLayout()
        self.json_label = QLabel("API")
        self.json_label.setStyleSheet("font-size: 12px; color: white;")
        self.json_input = QLineEdit()
        self.json_input.setFixedWidth(300)
        self.json_input.setStyleSheet("font-size: 12px; padding: 3px;")
        self.json_button = QPushButton("IMPORT JSON")
        self.json_button.setFixedWidth(250)
        self.json_button.setStyleSheet("background-color: #9C27B0; color: white; font-size: 12px; padding: 4px;")
        self.json_button.clicked.connect(self.browse_json)

        # Add json field and button to the json_layout (horizontal)
        json_layout.addWidget(self.json_label)
        json_layout.addWidget(self.json_input)
        json_layout.addWidget(self.json_button)

        # Now, add each horizontal layout to the left vertical layout
        left_v_layout.addLayout(name_layout)
        left_v_layout.addLayout(subject_layout)
        left_v_layout.addLayout(email_layout)
        left_v_layout.addLayout(json_layout)

        # Body Input
        self.body_label = QLabel("Body:")
        self.body_label.setStyleSheet("font-size: 12px; color: white;")

        self.body_input = QTextEdit()
        self.body_input.setFixedHeight(80)
        self.body_input.setStyleSheet("font-size: 12px; padding: 5px;")

        # স্টাইল (Load বাটনের মতো সবুজ)
        active_style = "background-color: #4CAF50; color: white; font-size: 12px; padding: 5px; border-radius: 4px;"
        inactive_style = "background-color: #2196F3; color: white; font-size: 12px; padding: 5px; border-radius: 4px;"

        # HTML Body Button
        self.html_body_button = QPushButton("HTML Body")
        self.html_body_button.setCheckable(True)
        self.html_body_button.setStyleSheet(inactive_style)

        # Plain Text Button
        self.plain_text_button = QPushButton("Plain Text")
        self.plain_text_button.setCheckable(True)
        self.plain_text_button.setStyleSheet(active_style)  # Default active

        # Toggle Logic
        def switch_body_mode(mode):
            if mode == "html":
                self.set_html_body()
                self.html_body_button.setStyleSheet(active_style)
                self.html_body_button.setChecked(True)
                self.plain_text_button.setStyleSheet(inactive_style)
                self.plain_text_button.setChecked(False)
            else:
                self.set_plain_text()
                self.plain_text_button.setStyleSheet(active_style)
                self.plain_text_button.setChecked(True)
                self.html_body_button.setStyleSheet(inactive_style)
                self.html_body_button.setChecked(False)
        # Connect Buttons
        self.html_body_button.clicked.connect(lambda: switch_body_mode("html"))
        self.plain_text_button.clicked.connect(lambda: switch_body_mode("plain"))

        # Layout
        body_button_layout = QHBoxLayout()
        body_button_layout.addWidget(self.html_body_button)
        body_button_layout.addWidget(self.plain_text_button)

        left_v_layout.addWidget(self.body_label)
        left_v_layout.addWidget(self.body_input)
        left_v_layout.addLayout(body_button_layout)


        # HTML Content Input
        self.html_label = QLabel("HTML Content:")
        self.html_label.setStyleSheet("font-size: 12px; color: white;")
        self.html_input = QTextEdit()
        self.html_input.setStyleSheet("font-size: 12px; padding: 5px;")
        left_v_layout.addWidget(self.html_label)
        left_v_layout.addWidget(self.html_input)
        
        # HTML Preview Button
        self.html_preview_button = QPushButton('Preview HTML')
        self.html_preview_button.setStyleSheet("font-size: 12px; padding: 5px; background-color: #2196F3; color: white;")
        self.html_preview_button.clicked.connect(self.preview_html)
        left_v_layout.addWidget(self.html_preview_button)

        # Attachment Format Selection
        self.attachment_label = QLabel("Attachment Format:")
        self.attachment_label.setStyleSheet("font-size: 12px; color: white;")
        
        # Radio buttons
        self.jpeg_radio = QRadioButton("JPEG")
        self.pdf_radio = QRadioButton("PDF")
        self.inline_radio = QRadioButton("Direct Invoice")
        self.no_attachment_radio = QRadioButton("Non-Attachment")
        self.jpeg_radio.setChecked(True)
        
        # Small buttons for format modification
        self.modify_image_btn = QPushButton("Modify Image Format")
        self.modify_image_btn.setFixedSize(120, 25)
        self.modify_image_btn.setStyleSheet("font-size: 10px; padding: 2px;")
        self.modify_image_btn.clicked.connect(self.modify_image_format)
        
        self.modify_pdf_btn = QPushButton("Modify PDF Format")
        self.modify_pdf_btn.setFixedSize(120, 25)
        self.modify_pdf_btn.setStyleSheet("font-size: 10px; padding: 2px;")
        self.modify_pdf_btn.clicked.connect(self.modify_pdf_format)
        
        # Layout for attachment format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(self.jpeg_radio)
        format_layout.addWidget(self.pdf_radio)
        format_layout.addWidget(self.inline_radio)
        format_layout.addWidget(self.no_attachment_radio)
        
        # Layout for modify buttons
        modify_layout = QHBoxLayout()
        modify_layout.addWidget(self.modify_image_btn)
        modify_layout.addWidget(self.modify_pdf_btn)
        modify_layout.addStretch()
        
        # Add to main layout
        left_v_layout.addWidget(self.attachment_label)
        left_v_layout.addLayout(format_layout)
        left_v_layout.addLayout(modify_layout)

        # Send Button
        self.send_button = QPushButton("Send Emails")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #008000;
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #006600;
            }
        """)
        self.send_button.clicked.connect(self.send_emails)
        left_v_layout.addWidget(self.send_button)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("font-size: 12px;")
        left_v_layout.addWidget(self.progress_bar)

        # Add logout button
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)

        # Right side - Status Box
        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setStyleSheet("""
            QTextEdit {
                background-color: #00242e;
                color: #00ff99;
                border: 1px solid #00444f;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        self.status_box.setMinimumWidth(300)
        right_v_layout.addWidget(QLabel("Email Sending Status:"))
        right_v_layout.addWidget(self.status_box)

        # Add layouts to main layout
        main_h_layout.addLayout(left_v_layout)
        main_h_layout.addLayout(right_v_layout)
        
        container = QWidget()
        container.setLayout(main_h_layout)
        self.setCentralWidget(container)

        # Initialize body mode (HTML or Plain Text)
        self.body_mode = "plain"  # Default to plain

    def show_contact(self):
        self.contact_window = ContactWindow()
        self.contact_window.show()

    def show_hashtag(self):
        self.copy_window = CopyWindow()
        self.copy_window.show()

    def add_task(self):
        self.show_message("Add Task", "Task adding feature is under development.", QMessageBox.Information)

    def preview_html(self):
        """Display HTML preview in a new window with proper rendering."""
        html_content = self.html_input.toPlainText()
        self.preview_window = QWidget()
        self.preview_window.setWindowTitle("HTML Preview")
        self.preview_window.setGeometry(200, 200, 600, 500)

        layout = QVBoxLayout()

        if WEB_ENGINE_AVAILABLE:
            self.html_viewer = QWebEngineView()
            self.html_viewer.setHtml(html_content)
        else:
            self.html_viewer = QTextBrowser()
            self.html_viewer.setHtml(html_content)

        layout.addWidget(self.html_viewer)
        self.preview_window.setLayout(layout)
        self.preview_window.show()

    def browse_name_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Name File", "", "CSV/TXT/XLSX Files (*.csv *.txt *.xlsx)")
        if file_path:
            self.name_input.setText(file_path)
            self.progress_bar.setValue(0)

    def browse_subject_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Subject File", "", "CSV/TXT/XLSX Files (*.csv *.txt *.xlsx)")
        if file_path:
            self.subject_input.setText(file_path)
            self.progress_bar.setValue(0)

    def browse_email(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Email Data File", "", "CSV/TXT/XLSX Files (*.csv *.txt *.xlsx)")
        if file_path:
            self.email_input.setText(file_path)
            self.progress_bar.setValue(0)

    def browse_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.json_input.setText(file_path)
            print(Fore.GREEN + "JSON file imported successfully!")

    def set_html_body(self):
        self.body_mode = "html"
        print(Fore.GREEN + "Body mode set to HTML")

    def set_plain_text(self):
        self.body_mode = "plain"
        print(Fore.GREEN + "Body mode set to Plain Text")

    def closeEvent(self, event):
    # Clean up all temporary files
        for dir_path in [CONTENT_DIR, CREDENTIAL_DIR]:
            if os.path.exists(dir_path):
                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                            print(Fore.YELLOW + f"Deleted: {file_path}")
                    except Exception as e:
                        print(Fore.RED + f"Failed to delete {file_path}: {str(e)}")
    
        # Logout from session
        if hasattr(self, 'session_manager') and self.session_manager:
            self.session_manager.logout(normal_logout=False)
    
        reply = QMessageBox.question(self, 'Confirm Exit', 'Are you sure you want to close the application?',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def send_emails(self):
        if self.email_worker and self.email_worker.isRunning():
            # If sending is in progress, stop it
            self.email_worker.stop()
            self.send_button.setText("Send Emails")
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #008000;
                    color: white;
                    font-size: 14px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #006600;
                }
            """)
        else:
            # Start sending emails
            sender_name = self.name_input.text() or "No Name"
            subject = self.subject_input.text() or "No Subject"
            body = self.body_input.toPlainText() or "No Body"
            json_file_path = self.json_input.text()
            email_data_path = self.email_input.text()

            if not json_file_path or not email_data_path:
                self.show_message("Input Error", "JSON File and Email Data File are required!", QMessageBox.Warning)
                return

            # Change button to stop
            self.send_button.setText("Stop Sending")
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff0000;
                    color: white;
                    font-size: 14px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #cc0000;
                }
            """)
            
            # Clear status box
            self.status_box.clear()
            
            # Start authentication
            self.auth_worker = AuthWorker(json_file_path)
            self.auth_worker.finished.connect(lambda service, email: self.on_auth_success(service, email, email_data_path))
            self.auth_worker.error.connect(self.on_auth_error)
            self.auth_worker.start()

    def on_auth_success(self, service, email, email_data_path):
        # Continue with email sending in a separate thread
        self.email_worker = EmailWorker(service, email, email_data_path, self.name_input.text(), self.subject_input.text(),
                                       self.body_input.toPlainText(), self.html_input.toPlainText(),
                                       self.get_attachment_format(), self.body_mode)
        self.email_worker.progress.connect(self.update_progress)
        self.email_worker.status.connect(self.update_status)
        self.email_worker.finished.connect(self.on_email_sending_finished)
        self.email_worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, status):
        self.status_box.append(status)
        # Auto-scroll to bottom
        self.status_box.verticalScrollBar().setValue(self.status_box.verticalScrollBar().maximum())

    def on_email_sending_finished(self):
        self.send_button.setText("Send Emails")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #008000;
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #006600;
            }
        """)
        self.status_box.append("All emails processed")

    def logout(self):
        self.session_manager.logout()
        self.close()

    def get_attachment_format(self):
        if self.no_attachment_radio.isChecked():
            return "none"
        elif self.jpeg_radio.isChecked():
            return "jpg"
        elif self.pdf_radio.isChecked():
            return "pdf"
        elif self.inline_radio.isChecked():
            return "inline"
        else:
            return "jpg"  # Default

    def modify_image_format(self):
        dialog = ImageFormatDialog()
        if dialog.exec_() == QDialog.Accepted:
            selected_format = dialog.get_selected_format()
            attachment_settings.set_image_format(selected_format)
            self.show_message("Image Format", f"Image format set to: {selected_format.upper()}")

    def modify_pdf_format(self):
        dialog = PdfFormatDialog()
        if dialog.exec_() == QDialog.Accepted:
            selected_format = dialog.get_selected_format()
            attachment_settings.set_pdf_format(selected_format)
            self.show_message("PDF Format", f"PDF format set to: {selected_format.upper()}")

    def reset_application(self):
        # Reset logic here
        self.name_input.clear()
        self.subject_input.clear()
        self.body_input.clear()
        self.html_input.clear()
        self.json_input.clear()
        self.email_input.clear()
        self.progress_bar.setValue(0)
        self.status_box.clear()
        self.jpeg_radio.setChecked(True)  # Default selection
        self.body_mode = "plain"  # Default body mode

        self.show_message("Reset", "Application fields have been reset successfully!", QMessageBox.Information)

    def show_message(self, title, message, icon=QMessageBox.Information):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setWindowIcon(QIcon(r'ec\icon.ico'))  # Set the message box icon
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #06121d;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #00ff99;
                color: black;
                border-radius: 5px;
                font-size: 12px;
                padding: 5px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00cc77;
            }
        """)
        msg_box.exec_()

class ContactWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Contact Info")
        self.setGeometry(300, 300, 350, 180)  # Compact & professional size

        # Set window icon
        self.setWindowIcon(QIcon(r'ec\icon.ico'))  # Set the window icon

        # Set modern gradient background
        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #74b9ff, stop:1 #a29bfe);
            border-radius: 12px;
        """)

        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Create main layout
        layout = QVBoxLayout()

        # Title Label
        title_label = QLabel("📞 Need Help?")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        title_label.setAlignment(Qt.AlignCenter)

        # Contact Message Label
        contact_label = QLabel("Contact me on WhatsApp:")
        contact_label.setFont(QFont("Arial", 12))
        contact_label.setStyleSheet("color: white;")
        contact_label.setAlignment(Qt.AlignCenter)

        # Phone Number Label (Highlighted)
        phone_label = QLabel("+880179-554-1326")
        phone_label.setFont(QFont("Arial", 16, QFont.Bold))
        phone_label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 0.3);
            padding: 8px;
            border-radius: 10px;
        """)
        phone_label.setAlignment(Qt.AlignCenter)

        # Copy Button
        copy_button = QPushButton("Copy Number")
        copy_button.setFont(QFont("Arial", 10, QFont.Bold))
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #fdcb6e;
                color: black;
                padding: 6px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e17055;
                color: white;
            }
        """)
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(phone_label.text()))

        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(contact_label)
        layout.addWidget(phone_label)
        layout.addWidget(copy_button)

        # Set layout
        main_widget.setLayout(layout)

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

class CopyWindow(QMainWindow):
    def __init__(self, recipient_email=""):
        super().__init__()

        self.recipient_email = recipient_email
        self.regards_names = ["Alex John", "Sarah Smith", "Michael Brown",
                              "Emily Davis", "David Wilson"]
        self.addresses = [
            "1925 Mill Street, Greenville, SC 29607",
            "123 Main Street, New York, NY 10001",
            "456 Oak Avenue, Chicago, IL 60601",
            "789 Pine Road, Los Angeles, CA 90001"
        ]

        self.setWindowTitle("ER Mailer Hashtags")
        self.setGeometry(200, 200, 700, 500)
        self.setWindowIcon(QIcon(r'ec\icon.ico'))
        self.setStyleSheet("background: #dfe6e9;")
        self.statusBar().showMessage("Ready")

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

        layout = QVBoxLayout()

        first_name = self.extract_name_from_email(recipient_email).split()[0] if recipient_email else "User"
        greeting = self.get_greeting()

        hashtags_content = {
            '#ABC#': f"POWFG-{random.randint(10000, 99999)}-POY",
            '#AMOUNT#': f"$ {random.uniform(200, 1000):.2f}",
            '#ADDRESS#': random.choice(self.addresses),
            '#CITY#': random.choice(["New York", "London", "Tokyo", "Sydney", "Dubai"]),
            '#COMPANY#': random.choice(["Company", "Organization", "Team", "Group"]),
            '#DATE#': datetime.now().strftime("%b %d, %Y"),
            '#DAY#': datetime.now().strftime("%A"),
            '#EMAIL#': recipient_email if recipient_email else "user@example.com",
            '#FIRSTNAME#': first_name,
            '#GREETING#': greeting,
            '#INVOICE#': ''.join(random.choices(string.ascii_uppercase + string.digits, k=18)),
            '#INVOICENUMBER#': f"INV-{random.randint(100000000000, 999999999999)}",
            '#KEY#': str(uuid.uuid4()),
            '#LETTERS#': ''.join(random.choices(string.ascii_uppercase, k=16)),
            '#NAME#': self.extract_name_from_email(recipient_email) if recipient_email else "John Doe",
            '#NUMBER#': str(random.randint(1000000000, 999999999999)),
            '#PRODUCT#': random.choice(["service", "product", "solution", "offer"]),
            '#RANDOM#': ''.join(random.choices(string.ascii_letters + string.digits, k=15)),
            '#REGARDS#': random.choice(self.regards_names),
            '#SNUMBER#': f"SNU-{random.randint(1000000000, 9999999999)}",
            '#TIME#': datetime.now().strftime("%I:%M %p")
        }

        # 🔽 Sort hashtags by length of hashtag (short to long)
        sorted_hashtags = sorted(hashtags_content.items(), key=lambda x: len(x[0]))

        for hashtag, content in sorted_hashtags:
            h_layout = QHBoxLayout()

            # Left: Hashtag label
            hashtag_label = QLabel(hashtag)
            hashtag_label.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                color: #6c5ce7;
                padding: 5px;
                min-width: 90px;
            """)

            # Middle: Content label
            content_label = QLabel(str(content))
            content_label.setAlignment(Qt.AlignCenter)  # Center-align the content
            content_label.setStyleSheet("""
                font-size: 14px;
                color: #2d3436;
                background-color: #ffffff;
                border: 1px solid #b2bec3;
                padding: 5px;
                border-radius: 4px;
                min-height: 30px;
            """)
            content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            content_label.setWordWrap(True)

            # Right: Copy button
            button = QPushButton("Copy")
            button.setStyleSheet("""
                QPushButton {
                    background-color: #0984e3;
                    color: white;
                    font-size: 13px;
                    padding: 4px 8px;
                    border: 1px solid #74b9ff;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #74b9ff;
                }
                QPushButton:pressed {
                    background-color: #40739e;
                }
            """)
            button.clicked.connect(lambda checked, text=hashtag: self.copy_to_clipboard(text))

            h_layout.addWidget(hashtag_label)
            h_layout.addWidget(content_label, stretch=1)
            h_layout.addWidget(button)
            layout.addLayout(h_layout)

        container.setLayout(layout)

    def copy_to_clipboard(self, content):
        clipboard = QApplication.clipboard()
        clipboard.setText(content)
        self.statusBar().showMessage(f"Copied {content} to clipboard", 2000)

    def extract_name_from_email(self, email):
        if not email:
            return "John Doe"
        name_part = email.split('@')[0]
        name_part = name_part.replace('.', ' ').replace('_', ' ')
        name = ' '.join([word.capitalize() for word in name_part.split()])
        return name if name else "John Doe"

    def get_greeting(self):
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning"
        elif 12 <= hour < 17:
            return "Good afternoon"
        elif 17 <= hour < 22:
            return "Good evening"
        else:
            return "Hello"

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # লগইন ডায়ালোগ দেখান
    login_dialog = LoginDialog()
    
    if login_dialog.exec_() == QDialog.Accepted:
        # লগইন সফল হলে মেইন উইন্ডো খুলুন
        main_window = EmailSenderApp(login_dialog.session_manager)
        main_window.show()
        
        # সেশন ম্যানেজারের লগআউট সিগন্যাল কানেক্ট করুন
        login_dialog.session_manager.logout_signal.connect(main_window.close)
        
        sys.exit(app.exec_())
    else:
        # লগইন ব্যর্থ হলে প্রোগ্রাম বন্ধ করুন
        sys.exit()
