# PhishGuardian Nexus v2.3  

*A Next-Generation Phishing Simulation & Awareness Platform*  

![image](https://github.com/user-attachments/assets/a8144ce3-67db-4127-9abc-e60e15f919cc)

---

## 🔥 Next-Level Features
- **AI-Powered Phishing Content Generation** using Google Gemini
- **Real-Time Tracking Dashboard** with engagement metrics
- **Auto-SSL Ngrok Integration** for instant public URLs
- **Smart Email Spoof Protection** simulations
- **Credential Harvesting Analysis** (Educational Purposes Only)
- **Beginner-Friendly GUI** with 4-step workflow
- **Instagram-Style Spoof Template** included
- **Live HTTP Server** with phishing page rendering

---

## ⚠️ Critical Disclaimer  
**This tool must ONLY be used for:**  
✅ Authorized security awareness training  
✅ Ethical penetration testing with written consent  
✅ Academic research on social engineering  
❌ **Never** use for illegal/malicious purposes  
*By using this software, you agree to bear full responsibility for its proper ethical application.*

---

## 🚀 Getting Started

### **Prerequisites**
```bash
# Install Python 3.10+ then:
pip install google-generativeai pyngrok requests tkinter

# To run the app simply:
python app.py
```


### **API Keys Setup**
1. **Google AI Studio**  
   - Go to [Google AI Studio](https://aistudio.google.com/)
   - Create API key → Copy key → Paste in Settings

2. **Ngrok Auth Token**  
   - Sign up at [Ngrok](https://ngrok.com/)
   - Dashboard → Your Authtoken → Copy → Paste in Settings

3. **Gmail App Password**  
   - Enable 2FA on Google Account
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Other" → Name it → Generate → Copy password

---

## 🛠️ Configuration Walkthrough

1. **Initial Setup**  
   - Launch application → Navigate to *Settings* tab  
   - Input all API keys → Click *Save Settings*

2. **Template Selection**  
   - Pre-made templates:
     - `instagram.html` - Social Media template
     - `finance.html` - Banking template
     - `corporate.html` - Internal IT template
     - `shipping.html` - Shipping Template
   - In Settings → *Template Mappings*:  
     - Select purpose → Click Browse → Choose template file

3. **Company Branding**  
   - In *Company Names* section:  
     - Financial: "ABC Bank"  
     - Social Media: "Instagram Security Team"  
     - Corporate: "XYZ IT Department"
     - Shipping: "ABC Delivery"
    
---

## 📁 Target CSV Format
email,first_name,last_name ( No header Required)
```csv
john.doe@company.com,John,Doe
sarah.smith@example.com,Sarah,Smith 
mark.z@corp.net,Mark,Zhang
```

---

## 🎯 Launching Campaigns
1. Load CSV with targets
2. Select campaign purpose
3. Generate AI-powered template
4. Click *Launch Campaign*
5. Monitor progress bar
6. **Refresh Results** periodically using toolbar button

---

## 🔍 Viewing Credentials
1. Go to *Results* tab  
2. Double-click any row with "Yes" in Credentials column  
3. See captured credentials in pop-up window  

---

## 🐛 Known Issues (Development Build)
```markdown
- First email in CSV may fail (temporary workaround: add dummy first row)
- Ngrok free tier shows warning page (paid account removes this)
- GUI may freeze during large campaigns (normal behavior)
- Fix glitches by restarting Python environment
```
### 📧 Email Infrastructure Setup
1. **You Need**  
   ✅ **Any Gmail Account** (not necessarily the target's)  
   ✅ **Gmail App Password** (as shown in previous setup)  

2. **You *Don't* Need**  
   ❌ Local mail servers (Postfix/Sendmail/etc)  
   ❌ Separate email hosting  
   ❌ MX record configuration  

---

### Why Gmail SMTP?
- Built-in SSL encryption via `smtplib`  
- Avoids spam filters (when used responsibly)  
- Handles email routing automatically  
- Free tier allows ~100 emails/day  

---

### ⚠️ Important Notes
1. **Daily Limits**  
   Google blocks bulk sends - stay under 100 emails/day  
2. **Sender Reputation**  
   Use a **dedicated Gmail account** (not your primary email)  
3. **App Password Requirement**  
   Standard Gmail passwords won't work - must use [app password](https://myaccount.google.com/apppasswords)  

---

## 💡 Advanced Customization
1. **Create Custom Templates**  
   - Make HTML files with these required variables:  
     `{{tracking_link}}`, `{{first_name}}`, `{{company}}`  
   - Add realistic logos using Base64 encoding  
   - Store in same directory → Map in Settings

2. **Modify Spoof Pages**  
   - Edit `instagram.html`:  
     - Change color scheme  
     - Add custom CSS animations  
     - Modify form submission logic

3. **Enhance Tracking**  
   - Modify `TrackingHandler` class to:  
     - Capture user-agent strings  
     - Log IP addresses  
     - Add geo-location lookup


---

**Contribute on GitHub** | *Report issues responsibly* | #EthicalHacking  
*"With great power comes great responsibility" - Uncle Ben (Spider-Man)*
