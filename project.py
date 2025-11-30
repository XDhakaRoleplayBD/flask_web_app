import flet as ft
import os
import random
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from pymongo import MongoClient

# ---------------- Config -----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "static", "solaimani font", "SolaimanLipi_22-02-2012.ttf")

pending_verification = {}   # Email verification temp store
pdf_bytes_global = b""      # global variable to hold generated PDF bytes

# ---------------- MongoDB -----------------
MONGO_URI = "mongodb+srv://saddatsaddat:787898456321@cluster0.fxx7luu.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["mydatabase"]
users_col = db["users"]

# ---------------- Email OTP -----------------
def generate_otp():
    return random.randint(100000, 999999)

# ---------------- PDF Generate -----------------
def create_pdf_bytes(text: str) -> bytes:
    if not os.path.exists(FONT_PATH):
        raise Exception(f"Font file not found: {FONT_PATH}")

    pdfmetrics.registerFont(TTFont("BanglaFont", FONT_PATH))

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    x_margin = 40
    y_margin = 40
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

# ---------------- Gmail Notification -----------------
def send_gmail_notification(to_email, subject, body):
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
        print(f"Email sent successfully to {to_email}!")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_email_async(to_email, subject, body):
    threading.Thread(target=send_gmail_notification,
                     args=(to_email, subject, body)).start()

# ---------------- Main App -----------------
def main(page: ft.Page):
    page.title = "Login → Text to PDF"
    page.window_width = 700
    page.window_height = 650
    page.theme_mode = "light"
    page.scroll = "adaptive"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    # Global UI fields
    reg_email = None
    reg_pass = None
    reg_msg = None
    log_email = None
    log_pass = None
    log_msg = None
    text_area = None
    filename_field = None
    conv_msg = None
    download_button = None

    # Dark Mode Button
    dark_mode_btn = ft.ElevatedButton("Dark Mode")
    def toggle_dark_mode(e):
        page.theme_mode = "dark" if page.theme_mode == "light" else "light"
        dark_mode_btn.text = "Dark Mode" if page.theme_mode == "light" else "Light Mode"
        page.update()
    dark_mode_btn.on_click = toggle_dark_mode

    # ---------- Navigation ----------    
    def show_login_view():
        page.clean()
        page.add(
            ft.Column([
                ft.Row([dark_mode_btn], alignment=ft.MainAxisAlignment.START),
                login_view_container()
            ], alignment=ft.MainAxisAlignment.START,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=6)
        )
        page.update()

    def show_register_view(e=None):
        page.clean()
        page.add(
            ft.Column([
                ft.Row([dark_mode_btn], alignment=ft.MainAxisAlignment.START),
                register_view_container()
            ], alignment=ft.MainAxisAlignment.START,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=6)
        )
        page.update()

    def show_converter_view(user_email: str):
        page.clean()
        page.add(
            ft.Column([
                ft.Row([dark_mode_btn], alignment=ft.MainAxisAlignment.START),
                converter_view(user_email)
            ], alignment=ft.MainAxisAlignment.START,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=6)
        )
        page.update()

    # ---------- OTP Verify Screen ----------
    def show_code_verify_view(user_email):
        page.clean()
        code_field = ft.TextField(label="Enter 6 digit code", width=300)
        msg = ft.Text("", color="red")

        def verify_code(e):
            code = code_field.value.strip()
            if len(code) != 6 or not code.isdigit():
                msg.value = "Invalid code!"
                page.update()
                return

            real_code = pending_verification[user_email]["code"]
            if str(real_code) == code:
                users_col.insert_one({
                    "email": user_email,
                    "password": pending_verification[user_email]["password"]
                })
                del pending_verification[user_email]
                msg.value = "Registration Successful!"
                msg.color = "green"
                page.update()
            else:
                msg.value = "Wrong code!"
                msg.color = "red"
                page.update()

        page.add(
            ft.Column([
                ft.Text("Email Verification", size=24, weight="bold"),
                ft.Text(f"Verification sent to: {user_email}"),
                code_field,
                ft.ElevatedButton("Verify", on_click=verify_code),
                msg,
                ft.TextButton("Back to Login", on_click=lambda e: show_login_view())
            ], alignment=ft.MainAxisAlignment.START,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               spacing=6)
        )

    # ---------- Registration ----------
    def register_user(e):
        nonlocal reg_email, reg_pass, reg_msg
        email = reg_email.value.strip()
        password = reg_pass.value.strip()
        if not email or not password:
            reg_msg.value = "Fill all information"
            page.update()
            return

        if users_col.find_one({"email": email}):
            reg_msg.value = "This Email is already used"
            page.update()
            return

        otp = generate_otp()
        pending_verification[email] = {
            "password": password,
            "code": otp
        }
        send_email_async(email, "Verify your account", f"Your verification code is: {otp}")
        reg_msg.value = "Verification code sent!"
        page.update()
        show_code_verify_view(email)

    # ---------- Login ----------
    def login_user(e):
        nonlocal log_email, log_pass, log_msg
        email = log_email.value.strip()
        password = log_pass.value.strip()
        if not email or not password:
            log_msg.value = "Fill all information"
            page.update()
            return

        user = users_col.find_one({"email": email, "password": password})
        if user:
            send_email_async(
                email,
                "Login Notification",
                f"You logged in at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
            )
            show_converter_view(email)
        else:
            log_msg.value = "Email or Password incorrect"
            page.update()

    # ---------- PDF Conversion + Download ----------
    def convert_to_pdf(e):
        nonlocal text_area, filename_field, conv_msg, download_button
        global pdf_bytes_global
        txt = text_area.value.strip()
        fname = filename_field.value.strip()
        if txt == "":
            conv_msg.value = "Please give text"
            page.update()
            return
        if fname == "":
            fname = "text_to_pdf_" + datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            pdf_bytes_global = create_pdf_bytes(txt)
            conv_msg.value = f"PDF generated successfully! Saved on Desktop as {fname}.pdf"
            download_button.disabled = True  # download now automatic
            save_pdf_to_desktop(fname, pdf_bytes_global)
        except Exception as ex:
            conv_msg.value = f"Error: {ex}"
            download_button.disabled = True

        page.update()

    def save_pdf_to_desktop(fname, pdf_bytes):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop_path, f"{fname}.pdf")
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"PDF saved to Desktop: {file_path}")

    def logout(e):
        show_login_view()

    # ---------- UI Containers ----------
    def register_view_container():
        nonlocal reg_email, reg_pass, reg_msg
        reg_email = ft.TextField(label="Email (Gmail)", width=420)
        reg_pass = ft.TextField(label="Password", password=True, can_reveal_password=True, width=420)
        reg_msg = ft.Text("", color="green")
        return ft.Column([
            ft.Text("Register", size=26, weight="bold"),
            reg_email,
            reg_pass,
            ft.Row([
                ft.ElevatedButton("Register", on_click=register_user),
                ft.TextButton("Already have an account? Login", on_click=lambda e: show_login_view())
            ], alignment=ft.MainAxisAlignment.CENTER),
            reg_msg
        ], alignment=ft.MainAxisAlignment.START,
           horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           spacing=6)

    def login_view_container():
        nonlocal log_email, log_pass, log_msg
        log_email = ft.TextField(label="Email (Gmail)", width=420)
        log_pass = ft.TextField(label="Password", password=True, can_reveal_password=True, width=420)
        log_msg = ft.Text("", color="red")
        return ft.Column([
            ft.Text("Login", size=26, weight="bold"),
            log_email,
            log_pass,
            ft.Row([
                ft.ElevatedButton("Login", on_click=login_user),
                ft.TextButton("Create new account", on_click=show_register_view)
            ], alignment=ft.MainAxisAlignment.CENTER),
            log_msg
        ], alignment=ft.MainAxisAlignment.START,
           horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           spacing=6)

    def converter_view(user_email: str):
        nonlocal text_area, filename_field, conv_msg, download_button
        text_area = ft.TextField(label="Enter text", multiline=True,
                                 min_lines=12, max_lines=12, width=620)
        filename_field = ft.TextField(label="Give PDF name", width=420)
        conv_msg = ft.Text("", color="green")
        download_button = ft.ElevatedButton("PDF will save to Desktop automatically", disabled=True)
        return ft.Column([
            ft.Row([
                ft.Text(f"Welcome, {user_email}", size=16, weight="bold"),
                ft.ElevatedButton("Logout", on_click=logout)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            text_area,
            ft.Row([
                filename_field,
                ft.ElevatedButton("Convert to PDF", on_click=convert_to_pdf)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([conv_msg], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([download_button], alignment=ft.MainAxisAlignment.CENTER)
        ], spacing=6,
           alignment=ft.MainAxisAlignment.START,
           horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # ---------- On App Load ----------
    page.add(
        ft.Column([
            ft.Row([dark_mode_btn], alignment=ft.MainAxisAlignment.START),
            ft.Text("UTTARA UNIVERSITY", size=28, weight="bold", color="Blue"),
            ft.Image(src="UU-New-logo-mobile-version.png", width=200, height=150),
            ft.Text("Text to PDF - Login Required", size=28, weight="bold"),
            login_view_container()
        ], alignment=ft.MainAxisAlignment.START,
           horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           spacing=6)
    )

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, assets_dir="static")
