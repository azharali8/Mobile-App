import streamlit as st
import json, random
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

FILE = "data.json"
REFERENCE_TEMPLATE_PATHS = [
    "assets/receipt_template.png",
    "receipt_template.png",
    r"C:\Users\evo\.cursor\projects\c-Users-evo-T-Apps\assets\c__Users_evo_AppData_Roaming_Cursor_User_workspaceStorage_9257e5cf9c064e25aac6a7ff81398c93_images_WhatsApp_Image_2026-05-04_at_15.55.50-a5495b6e-afea-4df1-ab0f-30842e76d9ff.png",
    r"C:\Users\evo\.cursor\projects\c-Users-evo-T-Apps\assets\c__Users_evo_AppData_Roaming_Cursor_User_workspaceStorage_9257e5cf9c064e25aac6a7ff81398c93_images_WhatsApp_Image_2026-05-04_at_15.55.50-41b8e1c7-f49f-4af8-882a-c71443329ab9.png",
    r"C:\Users\evo\.cursor\projects\c-Users-evo-T-Apps\assets\c__Users_evo_AppData_Roaming_Cursor_User_workspaceStorage_9257e5cf9c064e25aac6a7ff81398c93_images_WhatsApp_Image_2026-05-04_at_15.55.50-00d8792e-58b8-4ffe-a522-7997c0827172.png",
]
LOGO_PATHS = [
    "assets/easypaisa_logo.png",
    "easypaisa_logo.png",
]

# ------------------ DATA ------------------
def load_data():
    try:
        with open(FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    data.setdefault("users", {})
    data.setdefault("transactions", [])

    # Normalize user records (some older entries may use "Name" or other casing).
    for k, u in list(data["users"].items()):
        if not isinstance(u, dict):
            continue
        if "name" not in u:
            if "Name" in u and isinstance(u.get("Name"), str):
                u["name"] = u.get("Name", "").strip()
            else:
                u["name"] = str(u.get("name", "") or "").strip()
        else:
            u["name"] = str(u.get("name", "") or "").strip()
        if "phone" not in u:
            phone = u.get("phone", "")
            if not phone and isinstance(k, str) and k.startswith("03") and k.isdigit():
                phone = k
            u["phone"] = str(phone or "").strip()
    return data

def save_data(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

# ------------------ HELPERS ------------------
def load_font(size, weight="regular"):
    """
    Load system fonts with graceful fallback.
    Tries to match the original Easypaisa receipt look on Windows (Segoe UI).
    """
    weight = (weight or "regular").lower()
    candidates = []
    if weight in ("bold", "b"):
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
    elif weight in ("semibold", "semi", "sb", "600"):
        candidates = [
            "C:/Windows/Fonts/segoeuisb.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]

    candidates.extend(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if weight in ("bold", "b") else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Arial Bold.ttf" if weight in ("bold", "b") else "/Library/Fonts/Arial.ttf",
        ]
    )

    for font_path in candidates:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_centered_text(draw, text, y, font, fill, width):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=fill)


def format_reference_datetime(date_str):
    """Convert existing date format to 01-May-2026  10:08 PM style."""
    known_formats = ["%d %b %Y %I:%M %p", "%d-%b-%Y %I:%M %p", "%Y-%m-%d %H:%M:%S"]
    for fmt in known_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d-%b-%Y  %I:%M %p")
        except Exception:
            continue
    return date_str


def fit_text(draw, text, font, max_width):
    value = str(text or "")
    if (draw.textbbox((0, 0), value, font=font)[2]) <= max_width:
        return value
    truncated = value
    while truncated and (draw.textbbox((0, 0), f"{truncated}...", font=font)[2] > max_width):
        truncated = truncated[:-1]
    return f"{truncated}..."


def find_logo_asset():
    base_dir = Path(__file__).parent
    for candidate in LOGO_PATHS:
        path = Path(candidate)
        if not path.is_absolute():
            path = base_dir / path
        if path.exists():
            return path
    return None


def find_reference_template():
    base_dir = Path(__file__).parent
    for candidate in REFERENCE_TEMPLATE_PATHS:
        path = Path(candidate)
        if not path.is_absolute():
            path = base_dir / path
        if path.exists():
            return path
    return None


def load_brand_logo(max_width):
    """
    Load official logo if present; otherwise crop from reference screenshot.
    Returns a PIL RGBA image or None.
    """
    logo_path = find_logo_asset()
    if logo_path:
        try:
            logo = Image.open(logo_path).convert("RGBA")
            if logo.width > max_width:
                new_h = int((max_width / logo.width) * logo.height)
                logo = logo.resize((max_width, new_h), Image.Resampling.LANCZOS)
            return logo
        except Exception:
            pass
    return None


def generate_receipt_fallback(txn):
    # High resolution canvas for crisp exports.
    width, height = 1242, 2208
    img = Image.new("RGB", (width, height), "#4b475a")
    draw = ImageDraw.Draw(img)

    # Main receipt card
    card_margin = 20
    card_left = card_margin
    card_top = 36
    card_right = width - card_margin
    card_bottom = height - 36
    draw.rounded_rectangle(
        [(card_left, card_top), (card_right, card_bottom)],
        radius=12,
        fill="white",
    )

    content_left = card_left + 90
    content_right = card_right - 90

    # Fonts
    # Typography tuned to match the original receipt (Segoe UI look).
    brand_font = load_font(74, weight="bold")
    title_font = load_font(89, weight="bold")
    subtitle_font = load_font(40, weight="regular")
    section_label_font = load_font(54, weight="semibold")
    section_label_font_plus = load_font(55, weight="semibold")
    field_value_font = load_font(48, weight="regular")
    amount_label_font = load_font(56, weight="semibold")
    rs_font = load_font(53, weight="semibold")
    amount_font = load_font(64, weight="bold")
    meta_font = load_font(40, weight="regular")

    # Close icon
    draw.text((card_right - 68, card_top + 28), "x", font=meta_font, fill="#4c4c4c")

    # Check icon
    cx = width // 2
    cy = card_top + 120
    radius = 58
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill="#12b65c")
    # Draw vector check mark for consistent rendering on every machine.
    check_color = "white"
    draw.line([(cx - 22, cy + 2), (cx - 6, cy + 18)], fill=check_color, width=10)
    draw.line([(cx - 6, cy + 18), (cx + 24, cy - 16)], fill=check_color, width=10)

    # Header brand logo (image if available, text fallback).
    brand_logo = load_brand_logo(max_width=430)
    brand_top = card_top + 212
    if brand_logo is not None:
        logo_x = (width - brand_logo.width) // 2
        img.paste(brand_logo, (logo_x, brand_top), brand_logo)
    else:
        draw_centered_text(draw, "easypaisa", card_top + 224, brand_font, "#2f2f43", width)
    draw_centered_text(draw, "Transaction Successful", card_top + 336, title_font, "#10b35f", width)
    draw_centered_text(draw, "You have sent money.", card_top + 454, subtitle_font, "#6a6a6a", width)

    divider_y = card_top + 560
    draw.line([(card_left + 1, divider_y), (card_right - 1, divider_y)], fill="#e7e7e7", width=3)

    # Meta
    date_text = format_reference_datetime(txn.get("date", ""))
    draw.text((content_left, divider_y + 44), date_text, font=meta_font, fill="#686868")
    draw.text((content_left, divider_y + 104), f"ID#{txn['id']}", font=meta_font, fill="#686868")

    y = divider_y + 210
    max_text_width = content_right - content_left
    details_end_limit = card_bottom - 260

    sections = [
        ("Funding Source", "easypaisa Account", ""),
        ("Sent to", txn.get("receiver_name", txn.get("receiver", "")), txn.get("receiver_phone", "")),
        ("Account Details", txn.get("account_name", txn.get("receiver_name", txn.get("receiver", ""))), ""),
        ("Sent by", txn.get("sender_name", txn.get("sender", "")), txn.get("sender_phone", "")),
        ("Amount", f"{float(txn.get('amount', 0)):.2f}", ""),
        ("Fee / Charge", f"{float(txn.get('fee', 0)):.2f}", ""),
    ]

    # Adaptive spacing prevents any overlap with footer/total area.
    section_count = len(sections)
    lines_count = sum(1 + (1 if line1 else 0) + (1 if line2 else 0) for _, line1, line2 in sections)
    available_h = max(300, details_end_limit - y)
    line_step = max(48, min(66, available_h // (lines_count + section_count)))
    section_gap = max(16, min(34, line_step // 2))

    emphasized_labels = {"Funding Source", "Sent by", "Account Details", "Amount", "Fee / Charge"}

    def section(title, line1=None, line2=None):
        nonlocal y
        label_font = section_label_font_plus if title in emphasized_labels else section_label_font
        draw.text((content_left, y), fit_text(draw, title, label_font, max_text_width), font=label_font, fill="#4b4b4b")
        y += line_step
        if line1:
            draw.text((content_left, y), fit_text(draw, line1, field_value_font, max_text_width), font=field_value_font, fill="#5b5b5b")
            y += line_step
        if line2:
            draw.text((content_left, y), fit_text(draw, line2, field_value_font, max_text_width), font=field_value_font, fill="#5b5b5b")
            y += line_step
        y += section_gap

    for title, line1, line2 in sections:
        section(title, line1, line2)

    total_y = min(y, card_bottom - 220)
    draw.text((content_left, total_y), "Total Amount", font=amount_label_font, fill="#23a867")
    # Match original: smaller "Rs." + bolder numeric amount.
    total_amount = float(txn.get("amount", 0))
    rs_text = "Rs."
    amt_text = f"{total_amount:.2f}"
    base_y = total_y + 76
    draw.text((content_left, base_y), rs_text, font=rs_font, fill="#474747")
    rs_w = draw.textbbox((0, 0), rs_text, font=rs_font)[2]
    draw.text((content_left + rs_w + 18, base_y - 2), amt_text, font=amount_font, fill="#474747")

    return img


def generate_receipt_from_template(txn):
    template_path = find_reference_template()
    if not template_path:
        return None

    src = Image.open(template_path).convert("RGB")
    # 3x upscale for top-notch clarity while keeping original proportions.
    scale = 3
    base_w, base_h = src.size
    img = src.resize((base_w * scale, base_h * scale), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)

    def sx(x):
        return int(x * scale)

    def sy(y):
        return int(y * scale)

    body_bg = "#f1f1f1"
    label_color = "#4e4e4e"
    value_color = "#646464"
    total_green = "#23a867"
    total_color = "#4a4a4a"

    # Clear detail body only, keep original header/footer exactly.
    draw.rectangle([(sx(34), sy(302)), (sx(416), sy(905))], fill=body_bg)

    meta_font = load_font(sy(16), weight="regular")
    label_font = load_font(sy(21), weight="semibold")
    value_font = load_font(sy(16), weight="regular")
    total_label_font = load_font(sy(21), weight="semibold")
    rs_font = load_font(sy(15), weight="semibold")
    total_amount_font = load_font(sy(18), weight="bold")

    left = sx(44)
    draw.text((left, sy(309)), format_reference_datetime(txn.get("date", "")), font=meta_font, fill=value_color)
    draw.text((left, sy(343)), f"ID#{txn.get('id', '')}", font=meta_font, fill=value_color)

    receiver_name = fit_text(draw, txn.get("receiver_name", txn.get("receiver", "")), value_font, sx(280))
    receiver_phone = fit_text(draw, txn.get("receiver_phone", ""), value_font, sx(280))
    account_name = fit_text(draw, txn.get("account_name", receiver_name), value_font, sx(280))
    sender_name = fit_text(draw, txn.get("sender_name", txn.get("sender", "")), value_font, sx(280))
    sender_phone = fit_text(draw, txn.get("sender_phone", ""), value_font, sx(280))
    amount = float(txn.get("amount", 0))
    fee = float(txn.get("fee", 0))

    draw.text((left, sy(392)), "Funding Source", font=label_font, fill=label_color)
    draw.text((sx(73), sy(426)), "easypaisa Account", font=value_font, fill=value_color)
    draw.text((left, sy(478)), "Sent to", font=label_font, fill=label_color)
    draw.text((left, sy(513)), receiver_name, font=value_font, fill=value_color)
    draw.text((left, sy(548)), receiver_phone, font=value_font, fill=value_color)
    draw.text((left, sy(602)), "Account Details", font=label_font, fill=label_color)
    draw.text((left, sy(636)), account_name, font=value_font, fill=value_color)
    draw.text((left, sy(690)), "Sent by", font=label_font, fill=label_color)
    draw.text((left, sy(724)), sender_name, font=value_font, fill=value_color)
    draw.text((left, sy(758)), sender_phone, font=value_font, fill=value_color)
    draw.text((left, sy(812)), "Amount", font=label_font, fill=label_color)
    draw.text((left, sy(846)), f"{amount:.2f}", font=value_font, fill=value_color)
    draw.text((left, sy(878)), "Fee / Charge", font=label_font, fill=label_color)
    draw.text((left, sy(912)), f"{fee:.2f}", font=value_font, fill=value_color)
    draw.text((left, sy(950)), "Total Amount", font=total_label_font, fill=total_green)

    total_x = left
    total_y = sy(986)
    rs_text = "Rs."
    amt_text = f"{amount:.2f}"
    draw.text((total_x, total_y), rs_text, font=rs_font, fill=total_color)
    rs_w = draw.textbbox((0, 0), rs_text, font=rs_font)[2]
    draw.text((total_x + rs_w + sx(6), total_y - sy(1)), amt_text, font=total_amount_font, fill=total_color)

    return img


def generate_receipt(txn):
    return generate_receipt_fallback(txn)


# ------------------ SESSION ------------------
if "data" not in st.session_state:
    st.session_state.data = load_data()

if "user" not in st.session_state:
    st.session_state.user = None

if "pending_user_key" not in st.session_state:
    st.session_state.pending_user_key = None

# ------------------ UI ------------------
st.set_page_config(page_title="Easypaisa", layout="wide")

st.markdown("""
<style>
.card {
    padding: 20px;
    border-radius: 15px;
    background: white;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.balance {
    font-size: 30px;
    font-weight: bold;
    color: #ff6600;
}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGIN ------------------
if not st.session_state.user:
    st.title("🔐 Login")
    
    login_input = st.text_input("Enter Mobile Number (recommended) or Name")
    pending_name = st.text_input("Your Name (only required first time)", disabled=st.session_state.pending_user_key is None and (not login_input.strip().startswith("03")))
    
    if st.button("Login"):
        input_val = login_input.strip()
        
        if input_val:
            # Determine if input is phone or name
            if input_val.startswith("03") and input_val.isdigit():
                user_key = input_val
                # For phone login: ensure we have a profile name
                existing = st.session_state.data["users"].get(user_key, {})
                existing_name = str(existing.get("name", "") or "").strip()
                if not existing_name:
                    entered = pending_name.strip()
                    if not entered:
                        st.session_state.pending_user_key = user_key
                        st.error("Please enter your name (first time only).")
                        st.stop()
                    st.session_state.data["users"][user_key] = {
                        **existing,
                        "balance": existing.get("balance", 10000),
                        "name": entered,
                        "phone": user_key,
                    }
                    save_data(st.session_state.data)
            else:
                user_key = input_val.upper()
                user_name = input_val.strip()
                input_val = ""
            
            if user_key not in st.session_state.data["users"]:
                st.session_state.data["users"][user_key] = {
                    "balance": 10000,
                    "name": user_name,
                    "phone": input_val
                }
                save_data(st.session_state.data)
            
            st.session_state.user = user_key
            st.session_state.pending_user_key = None
            st.rerun()
        else:
            st.error("Enter mobile number or name")    

# ------------------ DASHBOARD ------------------
else:
    user = st.session_state.user
    balance = st.session_state.data["users"][user]["balance"]

    st.title("Easypaisa")
    col1, col2 = st.columns(2)
    col1.markdown(
        f"<div class='card'><div class='balance'>Rs {balance}</div><br>Available Balance</div>",
        unsafe_allow_html=True
    )

    # ---------------- SEND MONEY ----------------
    st.subheader("Send Money")
    receiver = st.text_input("Receiver Name")
    receiver_phone = st.text_input("Receiver Phone (optional)")
    amount = st.number_input("Amount", min_value=1)

    if st.button("Send Money"):
        if not receiver:
            st.error("Enter receiver name")
        elif amount > balance:
            st.error("Insufficient Balance")
        else:
            txn = {
                "id": str(random.randint(1000000000, 9999999999)),
                "sender": user,
                "receiver": receiver,
                "receiver_name": receiver,
                "receiver_phone": receiver_phone.strip(),
                "account_name": receiver,
                "sender_name": (st.session_state.data["users"][user].get("name") or "").strip() or str(user),
                "sender_phone": (st.session_state.data["users"][user].get("phone") or "").strip(),
                "amount": amount,
                "fee": 0.0,
                "date": datetime.now().strftime("%d-%b-%Y %I:%M %p")
            }

            # Deduct balance
            st.session_state.data["users"][user]["balance"] -= amount

            # Save transaction
            st.session_state.data["transactions"].append(txn)
            save_data(st.session_state.data)

            st.success("✅ Transaction Successful")

            # Generate receipt
            img = generate_receipt(txn)
            png_buf = BytesIO()
            img.save(png_buf, format="PNG", optimize=True, compress_level=1, dpi=(300, 300))
            png_buf.seek(0)

            pdf_buf = BytesIO()
            img.convert("RGB").save(pdf_buf, format="PDF", resolution=300.0)
            pdf_buf.seek(0)

            st.image(img, caption="Receipt", use_container_width=True)
            dcol1, dcol2 = st.columns(2)
            dcol1.download_button(
                "📥 Download Receipt (PNG)",
                png_buf,
                file_name=f"receipt_{txn['id']}.png",
                mime="image/png",
                use_container_width=True,
            )
            dcol2.download_button(
                "📄 Download Receipt (PDF)",
                pdf_buf,
                file_name=f"receipt_{txn['id']}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    # ---------------- HISTORY ----------------
    st.subheader("Transaction History")
    txns = [t for t in st.session_state.data["transactions"] if t["sender"] == user]
    if txns:
        st.table(txns)
    else:
        st.info("No transactions yet")

    # ---------------- LOGOUT ----------------
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()