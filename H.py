# H.py - COMPLETE BOT WITH AUTO COMMAND EXECUTION
import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import json
import logging
import threading
import re
import sys
import atexit
import requests
from flask import Flask
from threading import Thread
import base64
import marshal
import zlib
import hashlib

# ====================== CONFIGURATION ======================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join('/tmp', 'upload_bots')
IROTECH_DIR = os.path.join('/tmp', 'inf')
ENCRYPTED_FILES_DIR = os.path.join('/tmp', 'encrypted_files')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

# Create directories
os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)
os.makedirs(ENCRYPTED_FILES_DIR, exist_ok=True)

# Flask app for Render
app = Flask('')

@app.route('/')
def home():
    return "🤖 Bot is running on Render!"

@app.route('/health')
def health():
    return json.dumps({'status': 'ok', 'uptime': get_uptime()})

# Environment variables
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8383721588:AAEJo9BUTxPEujIERWiWRqbbxZfRCDJyV9Q')
OWNER_ID = int(os.environ.get('OWNER_ID', 8406101760))
ADMIN_ID = int(os.environ.get('ADMIN_ID', 8406101760))
YOUR_USERNAME = os.environ.get('YOUR_USERNAME', '@ritikxyz099')
UPDATE_CHANNEL = os.environ.get('UPDATE_CHANNEL', 'https://t.me/ritikxyzhost')

# GROUP JOIN REQUIREMENT
REQUIRED_GROUP_ID = "-1003831128265"  # अपना group ID यहाँ डालें
GROUP_LINK = "https://t.me/ritikxyzhost"  # अपना group link यहाँ डालें

# ENCRYPTION CONFIG
ENCRYPTION_KEY = b"PYTHON_ENCODER_SECRET_KEY_2024"

BOT_START_TIME = datetime.now()

# User state tracking
user_states = {}
user_has_uploaded = {}
user_files_data = {}
current_uploading_file = {}

def get_uptime():
    uptime = datetime.now() - BOT_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

FREE_USER_LIMIT = 20
SUBSCRIBED_USER_LIMIT = 15
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')

bot = telebot.TeleBot(TOKEN)

bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
maintenance_mode = False

# ENCRYPTION METHODS
ENCRYPTION_METHODS = {
    "🔐 DX Encryption": "dx_enc",
    "🛡️ Special Encryption": "special", 
    "🐍 PySpector": "pyspector",
    "📂 Marshal": "marshal",
    "🧹 Zlib": "zlib",
    "📋 Base64": "base64",
    "⚡ Zlib+Base64": "zlib_b64",
    "📄 Base32": "base32",
    "📄 Base16": "base16",
    "📄 Base85": "base85"
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

FILE_STATUS_APPROVED = "approved"
DB_LOCK = threading.Lock()

# ====================== DATABASE FUNCTIONS ======================
def init_db():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, joined_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_files 
                 (user_id INTEGER, file_name TEXT, file_type TEXT, encrypted INTEGER DEFAULT 0,
                  encryption_method TEXT, upload_time TEXT, PRIMARY KEY (user_id, file_name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions 
                 (user_id INTEGER PRIMARY KEY, expiry TEXT, plan TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins 
                 (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS running_scripts 
                 (user_id INTEGER, file_name TEXT, pid INTEGER, start_time TEXT)''')
    
    # Insert default admin
    c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
    if ADMIN_ID != OWNER_ID:
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def load_data():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    
    # Load admins
    c.execute('SELECT user_id FROM admins')
    admin_ids.update(row[0] for row in c.fetchall())
    
    # Load user files
    c.execute('SELECT user_id, file_name, file_type, encrypted, encryption_method FROM user_files')
    for row in c.fetchall():
        user_id, file_name, file_type, encrypted, enc_method = row
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append((file_name, file_type, encrypted, enc_method))
        user_has_uploaded[user_id] = True
    
    # Load subscriptions
    c.execute('SELECT user_id, expiry FROM subscriptions')
    for user_id, expiry in c.fetchall():
        try:
            user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
        except:
            pass
    
    conn.close()
    logger.info(f"Loaded {len(admin_ids)} admins, {len(user_files)} users with files")

init_db()
load_data()

# ====================== ENCRYPTION FUNCTIONS ======================
def encode_dx_enc(data):
    """DX Encryption (XOR based)"""
    result = bytearray()
    key = ENCRYPTION_KEY
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])
    return bytes(result)

def encode_special(data):
    """Special multi-layer encryption"""
    layer1 = zlib.compress(data)
    layer2 = base64.b64encode(layer1)
    layer3 = encode_dx_enc(layer2)
    layer4 = base64.b85encode(layer3)
    return layer4

def encode_pyspector(data):
    """PySpector encryption"""
    layer1 = marshal.dumps(data)
    layer2 = zlib.compress(layer1)
    layer3 = base64.b64encode(layer2)
    layer4 = encode_dx_enc(layer3)
    return layer4

def encode_marshal(data):
    """Marshal encoding"""
    return marshal.dumps(data)

def encode_zlib(data):
    """Zlib compression"""
    return zlib.compress(data)

def encode_base64(data):
    """Base64 encoding"""
    return base64.b64encode(data)

def encode_base32(data):
    """Base32 encoding"""
    return base64.b32encode(data)

def encode_base16(data):
    """Base16 encoding"""
    return base64.b16encode(data)

def encode_base85(data):
    """Base85 encoding"""
    return base64.b85encode(data)

def encode_zlib_b64(data):
    """Zlib + Base64"""
    compressed = zlib.compress(data)
    return base64.b64encode(compressed)

# Encryption mapping
ENCRYPTION_FUNCTIONS = {
    "dx_enc": encode_dx_enc,
    "special": encode_special,
    "pyspector": encode_pyspector,
    "marshal": encode_marshal,
    "zlib": encode_zlib,
    "base64": encode_base64,
    "zlib_b64": encode_zlib_b64,
    "base32": encode_base32,
    "base16": encode_base16,
    "base85": encode_base85
}

def encrypt_file(data, method="dx_enc"):
    """Encrypt file data using specified method"""
    if method in ENCRYPTION_FUNCTIONS:
        return ENCRYPTION_FUNCTIONS[method](data)
    return data

# ====================== HELPER FUNCTIONS ======================
def get_user_folder(user_id):
    """Get or create user's folder"""
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    """Get file limit for user"""
    if user_id == OWNER_ID:
        return OWNER_LIMIT
    if user_id in admin_ids:
        return ADMIN_LIMIT
    if user_id in user_subscriptions:
        expiry = user_subscriptions[user_id].get('expiry')
        if expiry and expiry > datetime.now():
            return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_file_count(user_id):
    """Count files uploaded by user"""
    return len([f for f in user_files.get(user_id, [])])

def save_user_file_db(user_id, file_name, file_type, encrypted=0, enc_method=None):
    """Save file info to database"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        upload_time = datetime.now().isoformat()
        
        c.execute('''INSERT OR REPLACE INTO user_files 
                     (user_id, file_name, file_type, encrypted, encryption_method, upload_time)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                 (user_id, file_name, file_type, encrypted, enc_method, upload_time))
        
        conn.commit()
        conn.close()
        
        # Update cache
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append((file_name, file_type, encrypted, enc_method))
        user_has_uploaded[user_id] = True

def check_group_membership(user_id):
    """Check if user is in required group"""
    try:
        chat_member = bot.get_chat_member(REQUIRED_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

def require_group_membership(func):
    """Decorator to require group membership"""
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if user_id in admin_ids:
            return func(message, *args, **kwargs)
        
        if not check_group_membership(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Join Group", url=GROUP_LINK))
            markup.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_joined"))
            
            bot.send_message(
                message.chat.id,
                "⚠️ **GROUP MEMBERSHIP REQUIRED**\n\n"
                "To use this bot, you must join our group first!\n\n"
                "1. Click 'Join Group' button below\n"
                "2. After joining, click 'I Joined'\n\n"
                "This is required for security purposes.",
                reply_markup=markup
            )
            return
        
        return func(message, *args, **kwargs)
    return wrapper

def require_file_upload(func):
    """Decorator to require at least one file upload"""
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if user_id in admin_ids:
            return func(message, *args, **kwargs)
        
        if not user_has_uploaded.get(user_id, False):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(types.KeyboardButton("📤 Upload File First"))
            
            bot.reply_to(
                message,
                "⚠️ **FIRST UPLOAD A FILE!**\n\n"
                "You need to upload at least one file before using bot features.\n\n"
                "Please upload a .py, .js or .zip file first!",
                reply_markup=markup
            )
            return
        
        return func(message, *args, **kwargs)
    return wrapper

# ====================== AUTO COMMAND EXECUTION SYSTEM ======================
def execute_system_command(command, timeout=60):
    """Execute system command and return output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=BASE_DIR  # Run from bot directory
        )
        
        output = ""
        if result.stdout:
            output += f"✅ **Output:**\n```\n{result.stdout[:4000]}\n```"
        if result.stderr:
            output += f"\n\n❌ **Errors:**\n```\n{result.stderr[:2000]}\n```"
        
        return output if output else "✅ Command executed successfully (no output)"
    
    except subprocess.TimeoutExpired:
        return "⏰ Command timed out after 60 seconds"
    except Exception as e:
        return f"❌ Error executing command: {str(e)}"

def run_file_with_command(file_path, command=None, timeout=120):
    """Run file with specific command"""
    try:
        if command:
            # Use custom command
            full_command = f"{command} {file_path}"
        elif file_path.endswith('.py'):
            full_command = f"python3 {file_path}"
        elif file_path.endswith('.js'):
            full_command = f"node {file_path}"
        elif file_path.endswith('.sh'):
            full_command = f"bash {file_path}"
        else:
            full_command = f"./{file_path}"
        
        logger.info(f"Executing command: {full_command}")
        
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(file_path) if os.path.dirname(file_path) else BASE_DIR
        )
        
        output = ""
        if result.stdout:
            output += f"✅ **Output:**\n```\n{result.stdout[:4000]}\n```"
        if result.stderr:
            output += f"\n\n❌ **Errors:**\n```\n{result.stderr[:2000]}\n```"
        
        return {
            'success': result.returncode == 0,
            'output': output if output else "✅ Script executed (no output)",
            'returncode': result.returncode
        }
    
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': "⏰ Script timed out after 2 minutes",
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'output': f"❌ Error: {str(e)}",
            'returncode': -1
        }

def create_command_keyboard():
    """Create keyboard for command options"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    commands = [
        "📁 List Files", "📊 System Info",
        "💾 Disk Space", "📡 Ping Test",
        "🔧 Install Package", "🔄 Restart Bot",
        "🧹 Clear Cache", "📈 Process List"
    ]
    
    for i in range(0, len(commands), 2):
        markup.add(*[types.KeyboardButton(cmd) for cmd in commands[i:i+2]])
    
    markup.add(types.KeyboardButton("⌨️ Custom Command"))
    markup.add(types.KeyboardButton("▶️ Auto Run Script"))
    markup.add(types.KeyboardButton("↩️ Back"))
    
    return markup

# ====================== FILE OWNER NOTIFICATION ======================
def send_file_to_owner(user_id, file_name, file_data, file_type, encryption_method, user_info):
    """Send uploaded file info to owner"""
    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
        temp_file.write(file_data)
        temp_file.close()
        
        # Prepare message for owner
        user_info_text = f"""
👤 **NEW FILE UPLOADED**

📌 **User Info:**
├─ ID: `{user_id}`
├─ Username: @{user_info.get('username', 'N/A')}
└─ Name: {user_info.get('first_name', 'N/A')}

📁 **File Info:**
├─ Name: `{file_name}`
├─ Type: {file_type}
├─ Encryption: {encryption_method if encryption_method else 'No Encryption'}
├─ Size: {len(file_data)} bytes
└─ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Send to owner
        with open(temp_file.name, 'rb') as file_to_send:
            bot.send_document(
                OWNER_ID,
                file_to_send,
                caption=user_info_text,
                parse_mode='Markdown'
            )
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        logger.info(f"File {file_name} sent to owner from user {user_id}")
    except Exception as e:
        logger.error(f"Error sending file to owner: {e}")

# ====================== KEYBOARD CREATION ======================
def create_main_keyboard(user_id):
    """Create main menu keyboard"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    base_buttons = [
        ["📤 Upload File", "📂 My Files"],
        ["▶️ Run Script", "⚙️ Run Command"],  # Auto command feature
        ["⚡ Bot Speed", "📊 Statistics"],
        ["⏱ Uptime", "📞 Contact"]
    ]
    
    if user_id in admin_ids:
        base_buttons.append(["👑 Admin Panel", "🔧 Maintenance"])
    
    for row in base_buttons:
        markup.add(*[types.KeyboardButton(btn) for btn in row])
    
    return markup

def create_encryption_keyboard():
    """Create encryption method selection keyboard"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    methods = list(ENCRYPTION_METHODS.keys())
    rows = [methods[i:i+2] for i in range(0, len(methods), 2)]
    
    for row in rows:
        markup.add(*[types.KeyboardButton(method) for method in row])
    
    markup.add(types.KeyboardButton("🚫 No Encryption"))
    markup.add(types.KeyboardButton("↩️ Back"))
    
    return markup

def create_run_script_keyboard(user_id):
    """Create keyboard for running scripts"""
    if user_id not in user_files or not user_files[user_id]:
        return None
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    files = user_files[user_id]
    buttons = []
    
    for file_name, file_type, encrypted, enc_method in files[:10]:  # Max 10 files
        button_text = f"▶️ {file_name[:20]}"
        if encrypted:
            button_text += " 🔐"
        buttons.append(button_text)
    
    # Arrange in rows of 2
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        markup.add(*[types.KeyboardButton(btn) for btn in row])
    
    markup.add(types.KeyboardButton("⌨️ Custom Command"))
    markup.add(types.KeyboardButton("🛑 Stop All"))
    markup.add(types.KeyboardButton("↩️ Back"))
    
    return markup

# ====================== COMMAND HANDLERS ======================
@bot.message_handler(commands=['start', 'help'])
@require_group_membership
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Add to active users
    active_users.add(user_id)
    
    # Add user to database
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, joined_date) VALUES (?, ?, ?)',
              (user_id, message.from_user.username, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Check if user has uploaded before
    has_uploaded = user_has_uploaded.get(user_id, False)
    
    welcome_text = f"""
🎉 **Welcome {user_name}!**

🤖 *Advanced Script Hosting Bot*

✅ **Group membership verified!**

🚀 **NEW FEATURES:**
• Auto Command Execution
• Run scripts with custom commands
• System command execution
• Real-time output monitoring
• File encryption & security

📌 *Available Commands:*
• `▶️ Run Script` - Run your uploaded files
• `⚙️ Run Command` - Execute system commands
• `⌨️ Custom Command` - Run any terminal command
• `📁 List Files` - View server files
• `📊 System Info` - Check server status
"""
    
    if has_uploaded:
        welcome_text += "\n✅ *You have uploaded files before*\nUse '▶️ Run Script' to execute them!"
        markup = create_main_keyboard(user_id)
    else:
        welcome_text += "\n⚠️ **FIRST STEP:** Upload a file to unlock all features!\n\nClick '📤 Upload File' below:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton("📤 Upload File First"))
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=markup
    )

# ====================== AUTO COMMAND EXECUTION HANDLERS ======================
@bot.message_handler(func=lambda msg: msg.text == "⚙️ Run Command")
@require_group_membership
@require_file_upload
def run_command_menu(message):
    user_id = message.from_user.id
    
    markup = create_command_keyboard()
    
    bot.reply_to(
        message,
        "⚙️ **AUTO COMMAND EXECUTION**\n\n"
        "Select a command to execute on server:\n\n"
        "📁 **List Files** - View all files in directory\n"
        "📊 **System Info** - Check system information\n"
        "💾 **Disk Space** - Check disk usage\n"
        "📡 **Ping Test** - Ping Google server\n"
        "🔧 **Install Package** - Install Python packages\n"
        "🔄 **Restart Bot** - Restart bot service\n"
        "🧹 **Clear Cache** - Clear temporary files\n"
        "📈 **Process List** - View running processes\n\n"
        "Or use:\n"
        "• `⌨️ Custom Command` - Run any terminal command\n"
        "• `▶️ Auto Run Script` - Run scripts automatically",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "📁 List Files")
@require_group_membership
def list_files_command(message):
    user_id = message.from_user.id
    
    msg = bot.reply_to(message, "📁 Listing files in current directory...")
    
    # Get list of files
    try:
        files = os.listdir(BASE_DIR)
        files_text = "\n".join([f"📄 {f}" for f in files[:50]])
        
        if len(files) > 50:
            files_text += f"\n\n... and {len(files) - 50} more files"
        
        bot.edit_message_text(
            f"📁 **Files in directory:**\n\n{files_text}",
            message.chat.id, msg.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error listing files: {str(e)}",
            message.chat.id, msg.message_id
        )

@bot.message_handler(func=lambda msg: msg.text == "📊 System Info")
@require_group_membership
def system_info_command(message):
    user_id = message.from_user.id
    
    msg = bot.reply_to(message, "📊 Getting system information...")
    
    try:
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory info
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024**3)  # GB
        memory_used = memory.used / (1024**3)    # GB
        memory_percent = memory.percent
        
        # Disk info
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3)      # GB
        disk_used = disk.used / (1024**3)        # GB
        disk_percent = disk.percent
        
        # Uptime
        uptime = datetime.now() - BOT_START_TIME
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        info_text = f"""
🖥️ **SYSTEM INFORMATION**

⚙️ **CPU:**
├─ Usage: {cpu_percent}%
└─ Cores: {cpu_count}

💾 **MEMORY:**
├─ Total: {memory_total:.2f} GB
├─ Used: {memory_used:.2f} GB
└─ Usage: {memory_percent}%

💽 **DISK:**
├─ Total: {disk_total:.2f} GB
├─ Used: {disk_used:.2f} GB
└─ Usage: {disk_percent}%

⏱️ **BOT UPTIME:**
└─ {days}d {hours}h {minutes}m {seconds}s

📊 **STATS:**
├─ Active Users: {len(active_users)}
├─ Total Files: {sum(len(f) for f in user_files.values())}
└─ Running Scripts: {len(bot_scripts)}
"""
        
        bot.edit_message_text(
            info_text,
            message.chat.id, msg.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error getting system info: {str(e)}",
            message.chat.id, msg.message_id
        )

@bot.message_handler(func=lambda msg: msg.text == "💾 Disk Space")
@require_group_membership
def disk_space_command(message):
    user_id = message.from_user.id
    
    msg = bot.reply_to(message, "💾 Checking disk space...")
    
    command = "df -h"
    output = execute_system_command(command)
    
    bot.edit_message_text(
        f"💾 **Disk Space Usage:**\n\n{output}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "📡 Ping Test")
@require_group_membership
def ping_test_command(message):
    user_id = message.from_user.id
    
    msg = bot.reply_to(message, "📡 Pinging Google server...")
    
    command = "ping -c 4 google.com"
    output = execute_system_command(command, timeout=10)
    
    bot.edit_message_text(
        f"📡 **Ping Test Results:**\n\n{output}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "🔧 Install Package")
@require_group_membership
def install_package_command(message):
    user_id = message.from_user.id
    
    msg = bot.reply_to(message, "📝 Enter package name to install (e.g., requests, numpy):")
    bot.register_next_step_handler(msg, process_package_install)

def process_package_install(message):
    user_id = message.from_user.id
    package_name = message.text.strip()
    
    if not package_name:
        bot.reply_to(message, "❌ Please provide a package name!")
        return
    
    msg = bot.reply_to(message, f"🔧 Installing {package_name}...")
    
    command = f"pip install {package_name}"
    output = execute_system_command(command)
    
    bot.edit_message_text(
        f"🔧 **Package Installation:**\n\n{output}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "🧹 Clear Cache")
@require_group_membership
def clear_cache_command(message):
    user_id = message.from_user.id
    
    msg = bot.reply_to(message, "🧹 Clearing cache...")
    
    commands = [
        "rm -rf /tmp/* 2>/dev/null || true",
        "find . -name '*.pyc' -delete",
        "find . -name '__pycache__' -delete",
        "echo '✅ Cache cleared successfully!'"
    ]
    
    output = ""
    for cmd in commands:
        output += execute_system_command(cmd) + "\n\n"
    
    bot.edit_message_text(
        f"🧹 **Cache Clear Results:**\n\n{output}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "📈 Process List")
@require_group_membership
def process_list_command(message):
    user_id = message.from_user.id
    
    msg = bot.reply_to(message, "📈 Getting process list...")
    
    command = "ps aux | head -20"
    output = execute_system_command(command)
    
    bot.edit_message_text(
        f"📈 **Running Processes (Top 20):**\n\n{output}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "⌨️ Custom Command")
@require_group_membership
def custom_command_handler(message):
    user_id = message.from_user.id
    
    # Check if admin for security
    if user_id not in admin_ids:
        bot.reply_to(
            message,
            "⚠️ **ADMIN ACCESS REQUIRED**\n\n"
            "Custom command execution is only available for admins for security reasons.",
            parse_mode='Markdown'
        )
        return
    
    msg = bot.reply_to(
        message,
        "⌨️ **ENTER CUSTOM COMMAND**\n\n"
        "Type any terminal command to execute:\n\n"
        "⚠️ **WARNING:** Be careful with commands!\n"
        "❌ Don't run: rm -rf /, :(){ :|:& };:\n"
        "✅ Safe: ls, pwd, cat, echo, etc.",
        parse_mode='Markdown'
    )
    
    bot.register_next_step_handler(msg, process_custom_command)

def process_custom_command(message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        return
    
    command = message.text.strip()
    
    if not command:
        bot.reply_to(message, "❌ Please enter a command!")
        return
    
    # Check for dangerous commands
    dangerous_patterns = [
        r'rm\s+-rf\s+/\s*',
        r':\(\)\{.*:\|.*&\s*\};.*',
        r'mkfs',
        r'dd\s+if=.*',
        r'>/dev/sda',
        r'chmod\s+777\s+/',
        r'wget.*\|\s*sh',
        r'curl.*\|\s*sh'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            bot.reply_to(
                message,
                "❌ **DANGEROUS COMMAND BLOCKED!**\n\n"
                "This command could damage the system.\n"
                "Please contact owner for permission.",
                parse_mode='Markdown'
            )
            return
    
    msg = bot.reply_to(message, f"⏳ Executing: `{command}`")
    
    output = execute_system_command(command)
    
    bot.edit_message_text(
        f"⌨️ **Command Output:**\n\n**Command:** `{command}`\n\n{output}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "▶️ Auto Run Script")
@require_group_membership
def auto_run_script_handler(message):
    user_id = message.from_user.id
    
    if user_id not in user_files or not user_files[user_id]:
        bot.reply_to(message, "📭 No files to run! Upload a file first.")
        return
    
    markup = create_run_script_keyboard(user_id)
    
    bot.reply_to(
        message,
        "🚀 **AUTO RUN SCRIPT**\n\n"
        "Select a file to run automatically:\n\n"
        "📌 **Features:**
• Auto-detects file type
• Runs Python, JS, Bash files
• Real-time output
• Timeout protection\n\n"
        "Click a file below or use:\n"
        "• `⌨️ Custom Command` - Run with custom command\n"
        "• `🛑 Stop All` - Stop all running scripts",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# Handle script selection for auto run
@bot.message_handler(func=lambda msg: msg.text.startswith("▶️"))
@require_group_membership
def handle_auto_run_selection(message):
    user_id = message.from_user.id
    
    # Extract file name from button text
    button_text = message.text
    file_display = button_text.replace("▶️", "").replace("🔐", "").strip()
    
    # Find matching file
    target_file = None
    for file_name, file_type, encrypted, enc_method in user_files.get(user_id, []):
        if file_name.startswith(file_display.split("...")[0] if "..." in file_display else file_display):
            target_file = file_name
            break
    
    if not target_file:
        bot.reply_to(message, f"❌ File not found: {file_display}")
        return
    
    # Ask for custom command or use default
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton(f"🚀 Run {target_file[:15]}..."))
    markup.add(types.KeyboardButton(f"⌨️ Custom Command for {target_file[:15]}..."))
    markup.add(types.KeyboardButton("↩️ Back"))
    
    bot.reply_to(
        message,
        f"📁 **Selected File:** `{target_file}`\n\n"
        "Choose execution method:\n"
        "• `🚀 Run` - Auto-run with detected interpreter\n"
        "• `⌨️ Custom Command` - Run with custom command\n\n"
        "Example custom commands:\n"
        "• `python3 -u file.py`\n"
        "• `node --trace-warnings file.js`\n"
        "• `bash file.sh`",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    # Store selected file
    user_states[user_id] = {'auto_run_file': target_file}

# Handle run confirmation
@bot.message_handler(func=lambda msg: msg.text.startswith("🚀 Run"))
@require_group_membership
def confirm_auto_run(message):
    user_id = message.from_user.id
    
    if user_id not in user_states or 'auto_run_file' not in user_states[user_id]:
        bot.reply_to(message, "❌ No file selected!")
        return
    
    file_name = user_states[user_id]['auto_run_file']
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, file_name)
    
    if not os.path.exists(file_path):
        bot.reply_to(message, f"❌ File not found: `{file_name}`")
        return
    
    msg = bot.reply_to(message, f"⏳ Starting `{file_name}`...")
    
    # Run the file
    result = run_file_with_command(file_path)
    
    # Clear state
    if user_id in user_states:
        del user_states[user_id]
    
    bot.edit_message_text(
        f"🚀 **Script Execution Complete:**\n\n"
        f"**File:** `{file_name}`\n\n"
        f"{result['output']}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

# Handle custom command for file
@bot.message_handler(func=lambda msg: msg.text.startswith("⌨️ Custom Command for"))
@require_group_membership
def custom_command_for_file(message):
    user_id = message.from_user.id
    
    if user_id not in user_states or 'auto_run_file' not in user_states[user_id]:
        bot.reply_to(message, "❌ No file selected!")
        return
    
    file_name = user_states[user_id]['auto_run_file']
    
    msg = bot.reply_to(
        message,
        f"⌨️ **ENTER CUSTOM COMMAND FOR:** `{file_name}`\n\n"
        "Type the command (include file name):\n\n"
        "**Examples:**\n"
        f"• `python3 {file_name}`\n"
        f"• `python3 -u {file_name}`\n"
        f"• `node {file_name}`\n"
        f"• `bash {file_name}`\n\n"
        "**Advanced:**\n"
        f"• `python3 {file_name} arg1 arg2`\n"
        f"• `node {file_name} --env=prod`",
        parse_mode='Markdown'
    )
    
    bot.register_next_step_handler(msg, process_file_custom_command)

def process_file_custom_command(message):
    user_id = message.from_user.id
    
    if user_id not in user_states or 'auto_run_file' not in user_states[user_id]:
        return
    
    file_name = user_states[user_id]['auto_run_file']
    command = message.text.strip()
    
    if not command:
        bot.reply_to(message, "❌ Please enter a command!")
        return
    
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, file_name)
    
    if not os.path.exists(file_path):
        bot.reply_to(message, f"❌ File not found: `{file_name}`")
        return
    
    msg = bot.reply_to(message, f"⏳ Executing: `{command}`")
    
    # Run with custom command
    result = run_file_with_command(file_path, command)
    
    # Clear state
    if user_id in user_states:
        del user_states[user_id]
    
    bot.edit_message_text(
        f"⌨️ **Custom Command Execution:**\n\n"
        f"**Command:** `{command}`\n\n"
        f"{result['output']}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

# ====================== STOP ALL COMMAND ======================
@bot.message_handler(func=lambda msg: msg.text == "🛑 Stop All")
@require_group_membership
def stop_all_command(message):
    user_id = message.from_user.id
    
    # Stop all running processes
    stopped = 0
    for script_key, script_info in list(bot_scripts.items()):
        if script_info['user_id'] == user_id:
            try:
                script_info['process'].terminate()
                stopped += 1
            except:
                pass
    
    # Also kill any other processes
    try:
        os.system("pkill -f 'python3.*tmp' 2>/dev/null")
        os.system("pkill -f 'node.*tmp' 2>/dev/null")
    except:
        pass
    
    bot.reply_to(
        message,
        f"🛑 **Stopped {stopped} running scripts**\n\n"
        "All your running processes have been terminated.",
        parse_mode='Markdown'
    )

# ====================== UPLOAD FILE HANDLERS ======================
@bot.message_handler(func=lambda msg: msg.text == "📤 Upload File First" or msg.text == "📤 Upload File")
@require_group_membership
def upload_file_command(message):
    user_id = message.from_user.id
    
    bot.reply_to(
        message,
        "📁 **UPLOAD YOUR FILE**\n\n"
        "Send your Python (.py), JavaScript (.js) or ZIP (.zip) file.\n\n"
        "⚠️ *File will be encrypted before uploading!*\n"
        "⚠️ *File will be sent to owner for security!*\n\n"
        "Max size: 20MB\n"
        "Supported: .py, .js, .zip, .sh",
        parse_mode='Markdown'
    )
    
    user_states[user_id] = 'awaiting_file'

@bot.message_handler(content_types=['document'])
@require_group_membership
def handle_document(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if user_states.get(user_id) != 'awaiting_file' and not user_has_uploaded.get(user_id, False):
        bot.reply_to(message, "⚠️ Please click '📤 Upload File' button first!")
        return
    
    doc = message.document
    file_name = doc.file_name
    file_size = doc.file_size
    
    if not file_name:
        bot.reply_to(message, "❌ File has no name!")
        return
    
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.zip', '.sh']:
        bot.reply_to(message, "❌ Unsupported file type! Only .py, .js, .zip, .sh allowed.")
        return
    
    if file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "❌ File too large! Max 20MB.")
        return
    
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        bot.reply_to(message, f"❌ File limit reached! ({current_files}/{file_limit})")
        return
    
    download_msg = bot.reply_to(message, f"⬇️ Downloading `{file_name}`...")
    
    try:
        file_info = bot.get_file(doc.file_id)
        file_data = bot.download_file(file_info.file_path)
        
        current_uploading_file[user_id] = {
            'name': file_name,
            'data': file_data,
            'original_data': file_data,
            'ext': file_ext,
            'type': 'py' if file_ext == '.py' else 'js' if file_ext == '.js' else 'sh' if file_ext == '.sh' else 'zip'
        }
        
        bot.edit_message_text(
            f"✅ Downloaded: `{file_name}`\n"
            f"📏 Size: {file_size} bytes\n\n"
            "🔐 **Select encryption method:**",
            chat_id, download_msg.message_id,
            parse_mode='Markdown'
        )
        
        bot.send_message(
            chat_id,
            "Choose how to encrypt your file before uploading:",
            reply_markup=create_encryption_keyboard()
        )
        
        user_states[user_id] = 'awaiting_encryption'
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        bot.reply_to(message, f"❌ Error downloading file: {str(e)}")

# Encryption method selection
@bot.message_handler(func=lambda msg: msg.text in ENCRYPTION_METHODS or msg.text in ["🚫 No Encryption", "↩️ Back"])
def handle_encryption_choice(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if user_id not in current_uploading_file:
        bot.reply_to(message, "❌ No file to encrypt! Upload a file first.")
        return
    
    file_info = current_uploading_file[user_id]
    
    if message.text == "↩️ Back":
        bot.send_message(chat_id, "Upload cancelled.", reply_markup=create_main_keyboard(user_id))
        if user_id in current_uploading_file:
            del current_uploading_file[user_id]
        if user_id in user_states:
            del user_states[user_id]
        return
    
    processing_msg = bot.reply_to(message, "⏳ Processing file...")
    
    try:
        file_data = file_info['data']
        file_name = file_info['name']
        file_type = file_info['type']
        original_data = file_info.get('original_data', file_data)
        
        encrypted = 0
        enc_method = None
        
        if message.text != "🚫 No Encryption":
            enc_method_name = ENCRYPTION_METHODS.get(message.text)
            if enc_method_name and enc_method_name in ENCRYPTION_FUNCTIONS:
                file_data = ENCRYPTION_FUNCTIONS[enc_method_name](file_data)
                encrypted = 1
                enc_method = enc_method_name
                
                bot.edit_message_text(
                    f"🔐 Encrypting with {message.text}...",
                    chat_id, processing_msg.message_id
                )
        
        user_folder = get_user_folder(user_id)
        
        if file_info['ext'] == '.zip':
            temp_zip = os.path.join(user_folder, f"temp_{file_name}")
            with open(temp_zip, 'wb') as f:
                f.write(file_data)
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(user_folder)
            
            os.remove(temp_zip)
            
            extracted_files = os.listdir(user_folder)
            py_files = [f for f in extracted_files if f.endswith('.py')]
            js_files = [f for f in extracted_files if f.endswith('.js')]
            sh_files = [f for f in extracted_files if f.endswith('.sh')]
            
            if py_files:
                main_file = py_files[0]
                file_type = 'py'
            elif js_files:
                main_file = js_files[0]
                file_type = 'js'
            elif sh_files:
                main_file = sh_files[0]
                file_type = 'sh'
            else:
                main_file = file_name.replace('.zip', '.py')
                file_type = 'py'
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            main_file = file_name
        
        save_user_file_db(user_id, main_file, file_type, encrypted, enc_method)
        
        user_info = {
            'id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name
        }
        send_file_to_owner(
            user_id, 
            main_file, 
            original_data, 
            file_type, 
            enc_method, 
            user_info
        )
        
        user_has_uploaded[user_id] = True
        
        if user_id in current_uploading_file:
            del current_uploading_file[user_id]
        if user_id in user_states:
            del user_states[user_id]
        
        enc_status = f"with {message.text}" if encrypted else "without encryption"
        bot.edit_message_text(
            f"✅ **FILE UPLOADED SUCCESSFULLY!**\n\n"
            f"📁 File: `{main_file}`\n"
            f"🔐 Encryption: {enc_status}\n"
            f"📊 Type: {file_type}\n"
            f"👑 Sent to owner for review\n\n"
            f"🎉 **Now you can run it with '▶️ Run Script'!**",
            chat_id, processing_msg.message_id,
            parse_mode='Markdown'
        )
        
        time.sleep(1)
        bot.send_message(
            chat_id,
            "👇 **Use buttons below to run your file:**",
            reply_markup=create_main_keyboard(user_id)
        )
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        bot.edit_message_text(
            f"❌ Error processing file: {str(e)}",
            chat_id, processing_msg.message_id
        )

# ====================== OTHER COMMANDS ======================
@bot.message_handler(func=lambda msg: msg.text == "📂 My Files")
@require_group_membership
@require_file_upload
def my_files_command(message):
    user_id = message.from_user.id
    
    if user_id not in user_files or not user_files[user_id]:
        bot.reply_to(message, "📭 No files uploaded yet!")
        return
    
    files_list = user_files[user_id]
    response = "📁 **YOUR FILES:**\n\n"
    
    for idx, (file_name, file_type, encrypted, enc_method) in enumerate(files_list, 1):
        enc_status = f"🔐 {enc_method}" if encrypted else "🔓 No encryption"
        response += f"{idx}. `{file_name}`\n   📊 {file_type} | {enc_status}\n\n"
    
    response += "\n👉 Click '▶️ Run Script' to run any of these!"
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "▶️ Run Script")
@require_group_membership
@require_file_upload
def run_script_menu(message):
    user_id = message.from_user.id
    
    if user_id not in user_files or not user_files[user_id]:
        bot.reply_to(message, "📭 No files to run! Upload a file first.")
        return
    
    markup = create_run_script_keyboard(user_id)
    if markup:
        bot.reply_to(
            message,
            "🚀 **SELECT FILE TO RUN**\n\n"
            "Choose a file from the list below:\n\n"
            "🟢 Running files show ▶️\n"
            "🔒 Encrypted files show 🔐",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "📭 No files uploaded yet!")

@bot.message_handler(func=lambda msg: msg.text == "⚡ Bot Speed")
@require_group_membership
def bot_speed_command(message):
    start_time = time.time()
    msg = bot.reply_to(message, "🏃 Testing speed...")
    
    time.sleep(0.5)
    
    end_time = time.time()
    response_time = round((end_time - start_time) * 1000, 2)
    
    bot.edit_message_text(
        f"⚡ **BOT SPEED TEST**\n\n"
        f"Response time: {response_time} ms\n"
        f"Status: {'🔒 Locked' if bot_locked else '🔓 Unlocked'}\n"
        f"Maintenance: {'🔧 ON' if maintenance_mode else '✅ OFF'}",
        message.chat.id, msg.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "📊 Statistics")
@require_group_membership
@require_file_upload
def statistics_command(message):
    user_id = message.from_user.id
    
    total_users = len(set().union(*[set(files) for files in user_files.values()])) if user_files else 0
    total_files = sum(len(files) for files in user_files.values())
    user_files_count = len(user_files.get(user_id, []))
    
    stats = f"""
📊 **BOT STATISTICS**

👥 Total Users: {total_users}
📁 Total Files: {total_files}
🚀 Running Scripts: {len(bot_scripts)}

👤 **YOUR STATS:**
📂 Your Files: {user_files_count}
📈 File Limit: {get_user_file_count(user_id)}/{get_user_file_limit(user_id)}

🛠️ **SYSTEM:**
⏱️ Uptime: {get_uptime()}
🔒 Status: {'Locked' if bot_locked else 'Unlocked'}
🔧 Maintenance: {'ON' if maintenance_mode else 'OFF'}
"""
    
    bot.reply_to(message, stats, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "⏱ Uptime")
@require_group_membership
def uptime_command(message):
    bot.reply_to(message, f"⏱ **Bot Uptime:** {get_uptime()}")

@bot.message_handler(func=lambda msg: msg.text == "📞 Contact")
@require_group_membership
def contact_command(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📞 Contact Owner", url=f"https://t.me/{YOUR_USERNAME.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL))
    
    bot.reply_to(
        message,
        "📞 **CONTACT INFORMATION**\n\n"
        "For support, questions or feedback:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "↩️ Back")
@require_group_membership
def back_command(message):
    user_id = message.from_user.id
    bot.send_message(
        message.chat.id,
        "↩️ Returning to main menu...",
        reply_markup=create_main_keyboard(user_id)
    )

# ====================== ADMIN COMMANDS ======================
@bot.message_handler(func=lambda msg: msg.text == "👑 Admin Panel")
def admin_panel_command(message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        bot.reply_to(message, "❌ Admin access required!")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📊 Admin Stats", "👥 User List")
    markup.add("🔧 Toggle Maintenance", "🔒 Toggle Lock")
    markup.add("📢 Broadcast", "💳 Manage Subs")
    markup.add("🟢 Run All Scripts")
    markup.add("↩️ Back to Main")
    
    bot.reply_to(
        message,
        "👑 **ADMIN PANEL**\n\n"
        "Select an option:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: msg.text == "🟢 Run All Scripts")
def run_all_scripts_command(message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        bot.reply_to(message, "❌ Admin access required!")
        return
    
    progress_msg = bot.reply_to(message, "⏳ Starting all user scripts...")
    
    started = 0
    failed = 0
    
    for uid, files_list in user_files.items():
        for file_name, file_type, encrypted, enc_method in files_list:
            try:
                user_folder = get_user_folder(uid)
                file_path = os.path.join(user_folder, file_name)
                
                if os.path.exists(file_path):
                    result = run_file_with_command(file_path)
                    if result['success']:
                        started += 1
                    else:
                        failed += 1
            except:
                failed += 1
    
    bot.edit_message_text(
        f"✅ **ALL SCRIPTS STARTED**\n\n"
        f"✅ Started: {started}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {started + failed}",
        message.chat.id, progress_msg.message_id,
        parse_mode='Markdown'
    )

# ====================== CALLBACK HANDLERS ======================
@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_joined_callback(call):
    user_id = call.from_user.id
    
    if check_group_membership(user_id):
        bot.answer_callback_query(call.id, "✅ Verified! Welcome.")
        
        bot.edit_message_text(
            "✅ **GROUP MEMBERSHIP VERIFIED!**\n\n"
            "You can now use the bot. Click /start to begin.",
            call.message.chat.id, call.message.message_id,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

# ====================== FLASK SERVER ======================
def run_flask_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def start_keep_alive():
    t = Thread(target=run_flask_server, daemon=True)
    t.start()
    logger.info("✅ Flask server started for Render")

# ====================== CLEANUP ======================
def cleanup():
    logger.info("🔄 Cleaning up...")
    
    for script_key, script_info in list(bot_scripts.items()):
        try:
            if script_info.get('process'):
                script_info['process'].terminate()
        except:
            pass
    
    logger.info("✅ Cleanup complete")

atexit.register(cleanup)

# ====================== MAIN ======================
if __name__ == "__main__":
    start_keep_alive()
    
    logger.info("🤖 Bot starting...")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info(f"Admins: {admin_ids}")
    logger.info(f"Group required: {REQUIRED_GROUP_ID}")
    
    print("=" * 60)
    print("🤖 ADVANCED SCRIPT HOSTING BOT WITH AUTO COMMANDS")
    print("=" * 60)
    print(f"Token: {TOKEN[:10]}...")
    print(f"Owner: {OWNER_ID}")
    print(f"Update Channel: {UPDATE_CHANNEL}")
    print("=" * 60)
    print("🚀 **AUTO COMMAND FEATURES:**")
    print("• ⚙️ Run Command - System commands")
    print("• ⌨️ Custom Command - Any terminal command")
    print("• ▶️ Auto Run Script - Auto file execution")
    print("• 📁 List Files - Directory listing")
    print("• 📊 System Info - Server monitoring")
    print("• 🔧 Install Package - Package installation")
    print("=" * 60)
    print("✅ Bot is ready!")
    print("=" * 60)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        time.sleep(10)