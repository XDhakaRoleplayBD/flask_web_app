from flask import Flask, request, redirect, url_for, send_file, session
from pymongo import MongoClient
import random, io
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- Config -----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "static", "solaimani font", "SolaimanLipi_22-02-2012.ttf")
LOGO_PATH = os.path.join(BASE_DIR, "static", "UU-New-logo-mobile-version.png")
pending_verification = {}

# ---------------- MongoDB -----------------
MONGO_URI = "mongodb+srv://saddatsaddat:787898456321@cluster0.fxx7luu.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["mydatabase"]
users_col = db["users"]

# ---------------- Gmail OTP -----------------
def generate_otp():
    return random.randint(100000, 999999)

def send_email(to_email, subject, body):
    from_email = "saddat0007@gmail.com"
    app_password = "ltmnrgdkycbkecvm"
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Email error: {e}")

def send_email_async(to_email, subject, body):
    threading.Thread(target=send_email, args=(to_email, subject, body)).start()

# ---------------- PDF Generation -----------------
def create_pdf_bytes(text: str) -> bytes:
    if not os.path.exists(FONT_PATH):
        raise Exception(f"Font file not found: {FONT_PATH}")

    pdfmetrics.registerFont(TTFont("BanglaFont", FONT_PATH))
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595, 842))  # A4
    width, height = 595, 842
    x_margin, y_margin = 40, 40
    max_width = width - 2 * x_margin
    current_y = height - y_margin
    font_name = "BanglaFont"
    font_size = 14
    line_height = font_size * 1.6
    c.setFont(font_name, font_size)

    for paragraph in text.split("\n"):
        if paragraph.strip() == "":
            current_y -= line_height
            if current_y < y_margin:
                c.showPage()
                c.setFont(font_name, font_size)
                current_y = height - y_margin
            continue
        words = paragraph.split(" ")
        line = ""
        for w in words:
            test_line = w if line == "" else line + " " + w
            if stringWidth(test_line, font_name, font_size) <= max_width:
                line = test_line
            else:
                c.drawString(x_margin, current_y, line)
                current_y -= line_height
                if current_y < y_margin:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    current_y = height - y_margin
                line = w
        if line:
            c.drawString(x_margin, current_y, line)
            current_y -= line_height
            if current_y < y_margin:
                c.showPage()
                c.setFont(font_name, font_size)
                current_y = height - y_margin
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ---------------- HTML Templates with Modern CSS -----------------
def render_page(title, body_html):
    return f"""
    <html>
    <head>
        <title>{title}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
            body {{ font-family: 'Roboto', sans-serif; background: linear-gradient(135deg, #74ABE2, #5563DE); margin:0; padding:0; }}
            .container {{
                width: 500px; max-width: 95%; margin: 60px auto; background-color: #fff;
                padding: 40px; border-radius: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.2); text-align: center;
            }}
            h2 {{ color: #333; font-size: 28px; margin: 20px 0; }}
            input[type=text], input[type=password], input[type=email], textarea {{
                width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ccc; border-radius: 8px; font-size: 16px;
            }}
            input[type=submit] {{
                width: 100%; background-color: #4CAF50; color: white; padding: 14px; border: none;
                border-radius: 8px; cursor: pointer; font-size: 18px; transition: 0.3s;
            }}
            input[type=submit]:hover {{ background-color: #45a049; }}
            a {{ text-decoration: none; color: #007BFF; }}
            .link {{ text-align: center; margin-top: 15px; }}
            textarea {{ resize: vertical; }}
            .note {{ font-size: 14px; color: #555; margin-top: 10px; }}
            img.logo {{ max-width: 200px; height: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            {body_html}
        </div>
    </body>
    </html>
    """

# ---------------- Routes -----------------
@app.route("/")
def index():
    return render_page("Text to PDF Converter", f"""
        <img src='/static/UU-New-logo-mobile-version.png' class='logo'><br>
        <h2>Text to PDF Converter</h2>
        <div class='link'>
            <a href='/register'>Register</a> | <a href='/login'>Login</a>
        </div>
    """)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        if users_col.find_one({"email": email}):
            return render_page("Register", "<h2>Email already exists</h2><a href='/register'>Back</a>")
        otp = generate_otp()
        pending_verification[email] = {"password": password, "code": otp}
        send_email_async(email, "Verify your account", f"Your OTP is: {otp}")
        session["verify_email"] = email
        return redirect(url_for("verify_otp"))
    return render_page("Register", """
        <h2>Register</h2>
        <form method='post'>
            Email: <input type='email' name='email' required><br>
            Password: <input type='password' name='password' required><br>
            <input type='submit' value='Register'>
        </form>
        <div class='link'><a href='/login'>Already have an account? Login</a></div>
    """)

@app.route("/verify", methods=["GET", "POST"])
def verify_otp():
    email = session.get("verify_email")
    if not email:
        return redirect(url_for("index"))
    if request.method == "POST":
        code = request.form["otp"].strip()
        if str(pending_verification[email]["code"]) == code:
            users_col.insert_one({"email": email, "password": pending_verification[email]["password"]})
            del pending_verification[email]
            return render_page("Verified", "<h2>Registration successful!</h2><a href='/login'>Login</a>")
        else:
            return render_page("Verify OTP", "<h2>Wrong OTP</h2><a href='/verify'>Try Again</a>")
    return render_page("Verify OTP", f"""
        <h2>Verify OTP for {email}</h2>
        <form method='post'>
            Enter OTP: <input type='text' name='otp' required><br>
            <input type='submit' value='Verify'>
        </form>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        user = users_col.find_one({"email": email, "password": password})
        if user:
            session["user_email"] = email
            send_email_async(email, "Login Notification", f"You logged in at {datetime.now()}")
            return redirect(url_for("converter"))
        else:
            return render_page("Login", "<h2>Email or password incorrect</h2><a href='/login'>Try Again</a>")
    return render_page("Login", """
        <h2>Login</h2>
        <form method='post'>
            Email: <input type='email' name='email' required><br>
            Password: <input type='password' name='password' required><br>
            <input type='submit' value='Login'>
        </form>
        <div class='link'><a href='/register'>Register</a></div>
    """)

@app.route("/converter", methods=["GET", "POST"])
def converter():
    if "user_email" not in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        text = request.form["text"].strip()
        fname = request.form.get("filename", "")
        if not fname:
            fname = "text_to_pdf_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_bytes = create_pdf_bytes(text)
        return send_file(io.BytesIO(pdf_bytes), as_attachment=True, download_name=f"{fname}.pdf", mimetype="application/pdf")
    return render_page("Text to PDF", f"""
        <h2>Convert Text to PDF</h2>
        <form method='post'>
            PDF Name (optional): <input type='text' name='filename'><br>
            Enter Text:<br>
            <textarea name='text' rows='10'></textarea><br>
            <input type='submit' value='Generate PDF'>
        </form>
        <div class='link'><a href='/logout'>Logout</a></div>
    """)

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
