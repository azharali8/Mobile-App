import streamlit as st
import json, random
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

FILE = "data.json"
APP_BUILD = "receipt-timezone-fix-2026-06-25-0005"
RECEIPT_TIMEZONE = ZoneInfo("Asia/Karachi")
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
FONT_SOURCES_USED = set()
LAST_RECEIPT_RENDER_MODE = "unknown"
BITMAP_FONT = ImageFont.load_default()

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
    base_dir = Path(__file__).parent
    font_file = "AppSans-Bold.ttf" if weight in ["bold", "semibold"] else "AppSans-Regular.ttf"
    font_path = base_dir / "assets" / "fonts" / font_file
    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass
    try:
        FONT_SOURCES_USED.add(f"PIL_DEFAULT_FONT_SIZE_{size}")
        return ImageFont.load_default(size=size)
    except TypeError:
        FONT_SOURCES_USED.add("PIL_DEFAULT_FONT_LEGACY")
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
            return dt.strftime("%d %B %Y  %I:%M %p")
        except Exception:
            continue
    return date_str


def current_receipt_datetime():
    return datetime.now(RECEIPT_TIMEZONE).strftime("%d-%b-%Y %I:%M %p")


def fit_text(draw, text, font, max_width):
    value = str(text or "")
    if (draw.textbbox((0, 0), value, font=font)[2]) <= max_width:
        return value
    truncated = value
    while truncated and (draw.textbbox((0, 0), f"{truncated}...", font=font)[2] > max_width):
        truncated = truncated[:-1]
    return f"{truncated}..."


def _bitmap_scaled_size(text, target_height):
    value = str(text or "")
    bbox = BITMAP_FONT.getbbox(value if value else " ")
    base_w = max(1, bbox[2] - bbox[0])
    base_h = max(1, bbox[3] - bbox[1])
    scale = max(1.0, float(target_height) / float(base_h))
    return int(base_w * scale), int(base_h * scale), scale


def draw_bitmap_scaled_text(img, text, x, y, target_height, fill):
    value = str(text or "")
    if not value:
        return 0, 0
    base_bbox = BITMAP_FONT.getbbox(value)
    base_w = max(1, base_bbox[2] - base_bbox[0])
    base_h = max(1, base_bbox[3] - base_bbox[1])
    _, _, scale = _bitmap_scaled_size(value, target_height)

    text_layer = Image.new("RGBA", (base_w + 4, base_h + 4), (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(text_layer)
    layer_draw.text((2, 2), value, font=BITMAP_FONT, fill=fill)
    out_w = max(1, int((base_w + 4) * scale))
    out_h = max(1, int((base_h + 4) * scale))
    scaled = text_layer.resize((out_w, out_h), Image.Resampling.NEAREST)
    img.paste(scaled, (int(x), int(y)), scaled)
    return out_w, out_h


def fit_bitmap_scaled_text(text, target_height, max_width):
    value = str(text or "")
    if not value:
        return value
    w, _, _ = _bitmap_scaled_size(value, target_height)
    if w <= max_width:
        return value
    truncated = value
    while truncated:
        candidate = f"{truncated}..."
        cw, _, _ = _bitmap_scaled_size(candidate, target_height)
        if cw <= max_width:
            return candidate
        truncated = truncated[:-1]
    return "..."


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

def draw_branded_easypaisa(img, draw, y, brand_font, width):
    text = "easypaisa"
    dark = "#2f2f43"
    text_bb = draw.textbbox((0, 0), text, font=brand_font)
    text_w = text_bb[2] - text_bb[0]
    x0 = (width - text_w) // 2
    draw.text((x0, y), text, font=brand_font, fill=dark)


def generate_receipt_fallback(txn):
    width = 1242

    sections = [
        ("Sent to",
            txn.get("receiver_bank", ""),
            txn.get("receiver_name", txn.get("receiver", "")),
            txn.get("receiver_phone", "")),
        ("Sent by", txn.get("sender_name", txn.get("sender", "")), txn.get("sender_phone", ""), ""),
        ("Amount", f"{float(txn.get('amount', 0)):.2f}", "", ""),
        ("Fee / Charge", f"{float(txn.get('fee', 0)):.2f}", "", ""),
    ]

    card_top = 90  # Upper dark space
    
    # Tighter header spacing for compact layout
    divider_y = card_top + 460
    y_start = divider_y + 170

    line_step = 60
    section_gap = 26
    
    # Precise pre-calculation using the same logic as drawing
    curr_y = y_start
    for _, line1, line2, line3 in sections:
        curr_y += line_step
        if line1: curr_y += line_step
        if line2: curr_y += line_step
        if line3: curr_y += line_step
        curr_y += section_gap

    total_y = curr_y + 14
    base_y = total_y + 66
    
    card_bottom = base_y + 450
    height = 2600

    bg_color = "#4b475a"
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    card_margin = 40
    card_left = card_margin
    card_right = width - card_margin
    
    # White background for whole card
    draw.rectangle(
        [(card_left, card_top), (card_right, card_bottom)],
        fill="white",
    )
    
    # Light grey background for the upper section above divider
    draw.rectangle(
        [(card_left, card_top), (card_right, divider_y)],
        fill="#f8f8f8",
    )

    content_left = card_left + 60
    content_right = card_right - 60

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
    icon_font = load_font(36, weight="regular")

    draw.text((card_right - 68, card_top + 28), "x", font=meta_font, fill="#4c4c4c")

    cx = width // 2
    cy = card_top + 90
    radius = 50
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill="#12b65c")
    check_color = "white"
    draw.line([(cx - 22, cy + 2), (cx - 6, cy + 18)], fill=check_color, width=10)
    draw.line([(cx - 6, cy + 18), (cx + 24, cy - 16)], fill=check_color, width=10)

    brand_logo = load_brand_logo(max_width=430)
    brand_top = card_top + 170
    if brand_logo is not None:
        logo_x = (width - brand_logo.width) // 2
        img.paste(brand_logo, (logo_x, brand_top), brand_logo)
    else:
        draw_branded_easypaisa(img, draw, card_top + 180, brand_font, width)
    draw_centered_text(draw, "Transaction Successful", card_top + 276, title_font, "#10b35f", width)
    draw_centered_text(draw, "Money has been sent", card_top + 378, subtitle_font, "#6a6a6a", width)

    # Draw divider to match the perfect template
    draw.line([(card_left + 1, divider_y), (card_right - 1, divider_y)], fill="#e7e7e7", width=3)

    date_text = format_reference_datetime(txn.get("date", ""))
    draw.text((content_left, divider_y + 44), date_text, font=meta_font, fill="#686868")
    draw.text((content_left, divider_y + 104), f"ID#{txn['id']}", font=meta_font, fill="#686868")

    y = y_start
    max_text_width = content_right - content_left
    emphasized_labels = {"Sent by", "Amount", "Fee / Charge"}

    def section(title, line1=None, line2=None, line3=None):
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
        if line3:
            draw.text((content_left, y), fit_text(draw, line3, field_value_font, max_text_width), font=field_value_font, fill="#5b5b5b")
            y += line_step
        y += section_gap

    for title, line1, line2, line3 in sections:
        section(title, line1, line2, line3)

    total_y = y + 20
    draw.text((content_left, total_y), "Total Amount", font=amount_label_font, fill="#23a867")
    total_amount = float(txn.get("amount", 0))
    rs_text = "Rs."
    amt_text = f"{total_amount:.2f}"
    base_y = total_y + 76
    draw.text((content_left, base_y), rs_text, font=rs_font, fill="#474747")
    rs_w = draw.textbbox((0, 0), rs_text, font=rs_font)[2]
    draw.text((content_left + rs_w + 18, base_y - 2), amt_text, font=amount_font, fill="#474747")

    # Perforated edges
    perf_radius = 10
    perf_spacing = 30
    for px in range(card_left + 15, card_right, perf_spacing):
        draw.ellipse([(px - perf_radius, card_top - perf_radius), (px + perf_radius, card_top + perf_radius)], fill=bg_color)
        draw.ellipse([(px - perf_radius, card_bottom - perf_radius), (px + perf_radius, card_bottom + perf_radius)], fill=bg_color)

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
    sender_name = fit_text(draw, txn.get("sender_name", txn.get("sender", "")), value_font, sx(280))
    sender_phone = fit_text(draw, txn.get("sender_phone", ""), value_font, sx(280))
    amount = float(txn.get("amount", 0))
    fee = float(txn.get("fee", 0))

    draw.text((left, sy(392)), "Sent to", font=label_font, fill=label_color)
    draw.text((left, sy(426)), receiver_name, font=value_font, fill=value_color)
    draw.text((left, sy(460)), receiver_phone, font=value_font, fill=value_color)
    draw.text((left, sy(510)), "Sent by", font=label_font, fill=label_color)
    draw.text((left, sy(544)), sender_name, font=value_font, fill=value_color)
    draw.text((left, sy(578)), sender_phone, font=value_font, fill=value_color)
    draw.text((left, sy(628)), "Amount", font=label_font, fill=label_color)
    draw.text((left, sy(662)), f"{amount:.2f}", font=value_font, fill=value_color)
    draw.text((left, sy(694)), "Fee / Charge", font=label_font, fill=label_color)
    draw.text((left, sy(728)), f"{fee:.2f}", font=value_font, fill=value_color)
    draw.text((left, sy(766)), "Total Amount", font=total_label_font, fill=total_green)

    total_x = left
    total_y = sy(800)
    rs_text = "Rs."
    amt_text = f"{amount:.2f}"
    draw.text((total_x, total_y), rs_text, font=rs_font, fill=total_color)
    rs_w = draw.textbbox((0, 0), rs_text, font=rs_font)[2]
    draw.text((total_x + rs_w + sx(6), total_y - sy(1)), amt_text, font=total_amount_font, fill=total_color)

    return img


def generate_receipt_zero_risk(txn):
    template_path = find_reference_template()
    if not template_path:
        return generate_receipt_fallback(txn)

    src = Image.open(template_path).convert("RGB")
    scale = 3
    base_w, base_h = src.size
    img = src.resize((base_w * scale, base_h * scale), Image.Resampling.LANCZOS)

    def sx(x):
        return int(x * scale)

    def sy(y):
        return int(y * scale)

    body_bg = "#f1f1f1"
    label_color = "#4e4e4e"
    value_color = "#646464"
    total_green = "#23a867"
    total_color = "#4a4a4a"

    draw = ImageDraw.Draw(img)
    draw.rectangle([(sx(34), sy(302)), (sx(416), sy(905))], fill=body_bg)

    left = sx(44)
    draw_bitmap_scaled_text(img, format_reference_datetime(txn.get("date", "")), left, sy(309), sy(16), value_color)
    draw_bitmap_scaled_text(img, f"ID#{txn.get('id', '')}", left, sy(343), sy(16), value_color)

    max_text_w = sx(280)
    receiver_name = fit_bitmap_scaled_text(txn.get("receiver_name", txn.get("receiver", "")), sy(16), max_text_w)
    receiver_phone = fit_bitmap_scaled_text(txn.get("receiver_phone", ""), sy(16), max_text_w)
    sender_name = fit_bitmap_scaled_text(txn.get("sender_name", txn.get("sender", "")), sy(16), max_text_w)
    sender_phone = fit_bitmap_scaled_text(txn.get("sender_phone", ""), sy(16), max_text_w)
    amount = float(txn.get("amount", 0))
    fee = float(txn.get("fee", 0))

    draw_bitmap_scaled_text(img, "Sent to", left, sy(392), sy(21), label_color)
    draw_bitmap_scaled_text(img, receiver_name, left, sy(426), sy(16), value_color)
    draw_bitmap_scaled_text(img, receiver_phone, left, sy(460), sy(16), value_color)
    draw_bitmap_scaled_text(img, "Sent by", left, sy(510), sy(21), label_color)
    draw_bitmap_scaled_text(img, sender_name, left, sy(544), sy(16), value_color)
    draw_bitmap_scaled_text(img, sender_phone, left, sy(578), sy(16), value_color)
    draw_bitmap_scaled_text(img, "Amount", left, sy(628), sy(21), label_color)
    draw_bitmap_scaled_text(img, f"{amount:.2f}", left, sy(662), sy(16), value_color)
    draw_bitmap_scaled_text(img, "Fee / Charge", left, sy(694), sy(21), label_color)
    draw_bitmap_scaled_text(img, f"{fee:.2f}", left, sy(728), sy(16), value_color)
    draw_bitmap_scaled_text(img, "Total Amount", left, sy(766), sy(21), total_green)

    rs_w, _ = draw_bitmap_scaled_text(img, "Rs.", left, sy(800), sy(15), total_color)
    draw_bitmap_scaled_text(img, f"{amount:.2f}", left + rs_w + sx(6), sy(799), sy(18), total_color)
    FONT_SOURCES_USED.add("PIL_BITMAP_SCALED_ENGINE")
    return img


def generate_receipt(txn):
    global LAST_RECEIPT_RENDER_MODE
    LAST_RECEIPT_RENDER_MODE = "fallback"
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
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        
        /* Hide main menu and header */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        div[data-testid="stDecoration"] {display: none;}
        
        /* Allow responsive vertical scrolling while keeping background static */
        html, body, [data-testid="stAppViewContainer"], .stApp {
            overflow-x: hidden !important;
            overflow-y: auto !important;
            min-height: 100vh !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stAppViewContainer"] {
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }
        [data-testid="stMainBlockContainer"] {
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }
        /* Hide scrollbars */
        ::-webkit-scrollbar {
            display: none !important;
        }
        
        /* Premium light green to pale yellow mesh gradient background */
        .stApp {
            background: linear-gradient(135deg, #9deecb 0%, #dbf5d7 50%, #fdf7bc 100%) !important;
            font-family: 'Poppins', sans-serif !important;
        }
        
        /* Transparent outer wrapper container - Centered with max-width of 500px */
        .main .block-container:has(.login-title),
        [data-testid="stAppViewBlockContainer"]:has(.login-title) {
            max-width: 500px !important;
            margin: 0 auto !important;
            margin-top: 6vh !important;
            padding: 20px !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            z-index: 10 !important;
            width: 100% !important;
        }

        /* Bank Logo */
        .illustration-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 20px;
            margin-top: -10px;
        }
        .illustration-glow {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100px;
            height: 100px;
            background: linear-gradient(135deg, #b8f5dc 0%, #e8faf0 60%, #fdf7bc 100%) !important;
            border-radius: 50% !important;
            border: 2px solid rgba(11, 163, 118, 0.25) !important;
            box-shadow: 0 8px 28px rgba(11, 163, 118, 0.18), 0 2px 8px rgba(0,0,0,0.06) !important;
            overflow: hidden !important;
        }
        .bank-logo-img {
            width: 80px;
            height: 80px;
            object-fit: contain;
            mix-blend-mode: multiply;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.08));
        }

        /* Titles */
        .login-title {
            text-align: center;
            font-size: 38px;
            font-weight: 800;
            margin-bottom: 6px;
            color: #000000 !important;
            font-family: 'Poppins', sans-serif !important;
        }
        
        .login-subtitle {
            text-align: center;
            font-size: 16px;
            color: #4a5568 !important;
            margin-bottom: 30px;
            font-weight: 500;
            font-family: 'Poppins', sans-serif !important;
        }

        /* Centered login form wrapper - max-width 500px */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.stTextInput),
        div[data-testid="stVerticalBlock"]:has(.stTextInput) {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin-top: 15px !important;
            color: #000000 !important;
            max-width: 500px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            width: 100% !important;
        }
        
        /* Customize vertical gaps */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            gap: 16px !important;
        }

        /* Inputs label */
        div[data-testid="stTextInput"] label {
            color: #000000 !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            margin-bottom: 8px;
            font-family: 'Poppins', sans-serif !important;
        }
        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            background-color: #ffffff !important;
            border: 1px solid #cbece0 !important;
            border-radius: 16px !important;
            transition: all 0.3s ease !important;
            position: relative !important;
            padding-left: 16px !important;
            height: 56px !important;
        }
        div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
            border-color: #0ba376 !important;
            box-shadow: 0 0 0 3px rgba(11, 163, 118, 0.12) !important;
            background-color: #ffffff !important;
        }
        div[data-testid="stTextInput"] input {
            color: #000000 !important;
            font-size: 15px !important;
            font-family: 'Poppins', sans-serif !important;
            background: transparent !important;
            border: none !important;
            padding: 14px 14px 14px 0 !important;
        }
        div[data-testid="stTextInput"] input::placeholder {
            color: #8c9ba5 !important;
            opacity: 1 !important;
        }
        div[data-testid="stTextInput"] input:-webkit-autofill,
        div[data-testid="stTextInput"] input:-webkit-autofill:hover, 
        div[data-testid="stTextInput"] input:-webkit-autofill:focus, 
        div[data-testid="stTextInput"] input:-webkit-autofill:active {
            -webkit-box-shadow: 0 0 0 30px white inset !important;
            -webkit-text-fill-color: #000000 !important;
        }

        /* Button styling matching the solid green button */
        div[data-testid="stButton"] {
            margin-top: 20px;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: #0ba376 !important;
            color: #ffffff !important;
            border-radius: 24px !important;
            width: 100% !important;
            height: 56px !important;
            border: none !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            transition: all 0.3s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-family: 'Poppins', sans-serif !important;
            box-shadow: none !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #098f66 !important;
            transform: translateY(-1px) !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:focus {
            box-shadow: none !important;
        }
        
        div[data-testid="stButton"] button[kind="secondary"] {
            background: transparent !important;
            color: #4a5568 !important;
            border: 1px solid #cbece0 !important;
            border-radius: 24px !important;
            height: 50px !important;
            width: 100% !important;
            font-weight: 600 !important;
            font-family: 'Poppins', sans-serif !important;
            margin-top: 10px;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- Bank logo: user-provided image, base64 encoded ---
    import base64 as _b64, os as _os
    _logo_path = _os.path.join(_os.path.dirname(__file__), "assets", "bank_logo.jpg")
    if _os.path.exists(_logo_path):
        with open(_logo_path, "rb") as _f:
            _logo_b64 = _b64.b64encode(_f.read()).decode()
        _mime = "image/jpeg"
    else:
        _logo_b64 = ""
        _mime = ""
    _img_tag = f'<img src="data:{_mime};base64,{_logo_b64}" class="bank-logo-img" alt="Bank Logo" />' if _logo_b64 else "🏦"
    st.markdown(f"""
        <div class="illustration-container">
            <div class="illustration-glow">
                {_img_tag}
            </div>
        </div>
        <div class="login-title">Digital Bank</div>
        <div class="login-subtitle">Securely access your account</div>
    """, unsafe_allow_html=True)
    
    card = st.container(border=True)
    with card:
        login_input = st.text_input("Mobile Number", placeholder="Enter mobile number")
        pending_name = st.text_input("Name (for new users)", placeholder="Your full name", disabled=st.session_state.pending_user_key is None and (not login_input.strip().startswith("03")))
        sign_in_clicked = st.button("Sign In", type="primary")
        
        cancel_clicked = False
        if st.session_state.pending_user_key is not None:
            cancel_clicked = st.button("Cancel Registration", key="cancel_reg")
            
    if sign_in_clicked:
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
                        st.error("Please enter your password/name (first time only).")
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

    if st.session_state.pending_user_key is not None:
        if cancel_clicked:
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
    receiver_bank = st.text_input("Bank Name (optional)", placeholder="e.g. HBL, Meezan, UBL")
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
                "receiver_bank": receiver_bank.strip(),
                "account_name": receiver,
                "sender_name": (st.session_state.data["users"][user].get("name") or "").strip() or str(user),
                "sender_phone": (st.session_state.data["users"][user].get("phone") or "").strip(),
                "amount": amount,
                "fee": 0.0,
                "date": current_receipt_datetime()
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

            if st.checkbox("Show render diagnostics", value=False):
                using_default_font = "PIL_DEFAULT_FONT" in FONT_SOURCES_USED
                template_path = find_reference_template()
                st.caption(
                    f"Renderer: {LAST_RECEIPT_RENDER_MODE} | "
                    f"Template: {str(template_path) if template_path else 'not found'} | "
                    f"Fonts: {', '.join(sorted(FONT_SOURCES_USED)) if FONT_SOURCES_USED else 'none'}"
                )
                if using_default_font:
                    st.error("Diagnostic: app is still using PIL default font (tiny-text fallback).")

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
