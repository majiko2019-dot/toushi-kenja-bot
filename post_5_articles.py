import anthropic
import httpx
import xmlrpc.client
import random
import re
import os
import io
from PIL import Image, ImageDraw, ImageFont

WP_URL = "https://toushi-kenja.com"
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]
WP_USERNAME = os.environ["TOUSHI_WP_USERNAME"]
WP_APP_PASSWORD = os.environ["TOUSHI_WP_APP_PASSWORD"]

KEYWORDS = [
    "FX おすすめ 口座 2026 初心者",
    "証券口座 おすすめ 2026 初心者",
    "NISA 口座 どこがいい 比較",
    "FX 始め方 初心者 手順",
    "投資 初心者 何から始める",
    "つみたてNISA 銘柄 おすすめ 2026",
    "FX 口座 比較 スプレッド 手数料",
    "株式投資 初心者 始め方 証券口座",
    "iDeCo 証券会社 選び方 比較",
    "積立投資 月1万円 シミュレーション",
]


def get_font(size):
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def generate_eyecatch(title, kw):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    bg_start = (10, 20, 60)
    bg_end = (20, 40, 100)
    accent = (212, 175, 55)

    for y in range(H):
        r = int(bg_start[0] + (bg_end[0] - bg_start[0]) * y / H)
        g = int(bg_start[1] + (bg_end[1] - bg_start[1]) * y / H)
        b = int(bg_start[2] + (bg_end[2] - bg_start[2]) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    draw.rectangle([0, 0, W, 10], fill=accent)
    draw.rectangle([0, H - 10, W, H], fill=accent)

    font_badge = get_font(28)
    badge_text = f"#{kw}"
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw, bh = bbox[2] - bbox[0] + 30, bbox[3] - bbox[1] + 16
    draw.rounded_rectangle([60, 55, 60 + bw, 55 + bh], radius=18, fill=accent)
    draw.text((75, 63), badge_text, font=font_badge, fill=(10, 20, 60))

    font_site = get_font(26)
    site_text = "投資の賢者 | toushi-kenja.com"
    bbox = draw.textbbox((0, 0), site_text, font=font_site)
    draw.text((W - bbox[2] + bbox[0] - 60, 68), site_text, font=font_site, fill=(212, 175, 55))

    margin = 80
    max_w = W - margin * 2
    chosen_lines, chosen_size = [], 48
    for fs in [64, 56, 48, 40, 34]:
        font_t = get_font(fs)
        lines = wrap_text(draw, title, font_t, max_w)
        total_h = len(lines) * (fs + 18)
        if total_h <= 320 and len(lines) <= 4:
            chosen_lines, chosen_size = lines, fs
            break

    font_title = get_font(chosen_size)
    total_h = len(chosen_lines) * (chosen_size + 18)
    start_y = (H - total_h) // 2 + 25
    for i, line in enumerate(chosen_lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        x = (W - (bbox[2] - bbox[0])) // 2
        y = start_y + i * (chosen_size + 18)
        draw.text((x + 3, y + 3), line, font=font_title, fill=(0, 0, 0))
        draw.text((x, y), line, font=font_title, fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def upload_media_xmlrpc(server, image_bytes, filename):
    try:
        data = {
            'name': filename,
            'type': 'image/jpeg',
            'bits': xmlrpc.client.Binary(image_bytes),
            'overwrite': False,
        }
        result = server.wp.uploadFile(0, WP_USERNAME, WP_APP_PASSWORD, data)
        return result.get('id')
    except Exception as e:
        print("画像アップロードエラー:", str(e))
        return None


def make_article(kw):
    http_client = httpx.Client(verify=False)
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, http_client=http_client)
    from datetime import datetime
    year = datetime.now().year
    t = f"あなたはFX・株式投資・証券口座に精通したSEOライターです。\n"
    t += f"現在の年は{year}年です。タイトルや本文に年を記載する場合は必ず{year}年と書いてください。\n"
    t += f"以下のテーマでSEOに強いHTML形式の記事を書いてください。広告・アフィリエイトリンクは一切含めないでください。\n"
    t += f"テーマ：{kw}\n\n"
    t += "【SEOルール】\n"
    t += "・タイトルにキーワードを含め、数字を入れてクリック率を上げる\n"
    t += "・h2見出しにも関連キーワードを自然に含める\n"
    t += "・最初の100字以内にキーワードを入れてリード文を書く\n"
    t += "・2000字以上の充実した内容にする\n"
    t += "・比較表（tableタグ）を必ず1つ以上入れる\n\n"
    t += "【構成】\n"
    t += "<h1>タイトル</h1>\n"
    t += "<p>リード文</p>\n"
    t += "<h2>ポイント解説</h2>\n"
    t += "<h2>比較表</h2>\n"
    t += "<h2>詳細解説</h2>\n"
    t += "<h2>よくある質問（FAQ）</h2>\n"
    t += "<h2>まとめ</h2>\n\n"
    t += "HTML形式で書いてください。FAQはschema.org対応の構造化データも含めてください。"

    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=5000,
        messages=[{"role": "user", "content": t}],
    )
    return msg.content[0].text


def get_title(html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return "投資・FX情報記事"


def get_categories(kw):
    fx_keywords = ["FX", "外為", "スワップ", "スプレッド", "ドル円"]
    stock_keywords = ["証券", "株", "NISA", "iDeCo", "ETF", "投資信託", "IPO", "配当"]
    how_keywords = ["始め方", "やり方", "方法", "コツ", "手順", "シミュレーション"]
    categories = []
    if any(k in kw for k in fx_keywords):
        categories.append("FX口座比較")
    if any(k in kw for k in stock_keywords):
        categories.append("証券口座比較")
    if any(k in kw for k in how_keywords):
        categories.append("投資ノウハウ")
    return categories or ["投資ノウハウ"]


def post(server, title, content, kw, num):
    thumbnail_id = None
    try:
        image_bytes = generate_eyecatch(title, kw)
        safe_kw = re.sub(r"[^\w]", "_", kw)
        filename = f"eyecatch_{safe_kw}.jpg"
        thumbnail_id = upload_media_xmlrpc(server, image_bytes, filename)
    except Exception as e:
        print("アイキャッチエラー:", str(e))

    post_data = {
        'post_title': title,
        'post_content': content,
        'post_status': 'publish',
        'post_type': 'post',
        'terms_names': {'category': get_categories(kw)},
    }
    if thumbnail_id:
        post_data['post_thumbnail'] = int(thumbnail_id)

    result = server.wp.newPost(0, WP_USERNAME, WP_APP_PASSWORD, post_data)
    print(f"[{num}/5] 投稿成功 ID:{result} - {title}")


def main():
    server = xmlrpc.client.ServerProxy(WP_URL + "/xmlrpc.php")
    keywords = random.sample(KEYWORDS, 5)

    for i, kw in enumerate(keywords, 1):
        print(f"\n[{i}/5] キーワード: {kw}")
        print("記事生成中...")
        html = make_article(kw)
        title = get_title(html)
        print(f"タイトル: {title}")
        post(server, title, html, kw, i)

    print("\n5記事の投稿完了！")


if __name__ == "__main__":
    main()
