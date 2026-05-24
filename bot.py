import anthropic
import httpx
import xmlrpc.client
import ssl
import random
import re
import os
import io
from datetime import datetime, timezone, timedelta
import time
import sys
from PIL import Image, ImageDraw, ImageFont

JST = timezone(timedelta(hours=9))

def get_publish_datetime():
    """当日20:00 JSTを返す。22時以降は翌日20:00に回す（GitHub Actions遅延考慮）"""
    now = datetime.now(JST)
    target = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if now.hour >= 22:
        target += timedelta(days=1)
    return target

import time
import sys


def get_existing_future_dates(server):
    """既存future投稿の日付(YYYYMMDD)セット"""
    try:
        posts = server.wp.getPosts(0, WP_USERNAME, WP_APP_PASSWORD,
            {"post_status": "future", "number": 50, "post_type": "post"})
        dates = set()
        for p in posts:
            pd = p.get("post_date")
            if pd is None:
                continue
            pd_str = str(pd)
            if len(pd_str) >= 8:
                dates.add(pd_str[:8])
        return dates
    except Exception as e:
        print(f"[WARN] 既存future取得失敗: {e}")
        return set()


def fix_missed_posts(server):
    """過去日付のままfuture状態で残っている投稿を強制publish化（現在時刻に日付更新）"""
    try:
        posts = server.wp.getPosts(0, WP_USERNAME, WP_APP_PASSWORD,
            {"post_status": "future", "number": 50, "post_type": "post",
             "orderby": "post_date", "order": "ASC"})
        now = datetime.now(JST)
        now_xmlrpc = xmlrpc.client.DateTime(now.strftime("%Y%m%dT%H:%M:%S"))
        fixed = 0
        for p in posts:
            pd = p.get("post_date")
            if pd is None:
                continue
            try:
                pd_dt = datetime.strptime(str(pd), "%Y%m%dT%H:%M:%S").replace(tzinfo=JST)
                if pd_dt < now - timedelta(minutes=10):
                    print(f"[ALERT] Missed Schedule発見: ID={p['post_id']} date={pd} title={p.get('post_title','')[:40]}")
                    server.wp.editPost(0, WP_USERNAME, WP_APP_PASSWORD, p['post_id'],
                        {"post_status": "publish", "post_date": now_xmlrpc})
                    print(f"  → 強制publish化完了（date={now.strftime('%Y-%m-%d %H:%M')}）")
                    fixed += 1
            except Exception as e:
                print(f"  パース失敗 ID={p.get('post_id')}: {e}")
        if fixed > 0:
            print(f"[INFO] Missed Schedule {fixed}件を自動修復")
        return fixed
    except Exception as e:
        print(f"[WARN] missed posts check失敗: {e}")
        return 0


def get_publish_datetime_safe(server):
    """重複しない次の20:00 JST スロット（既存futureを避けて翌日以降にシフト）"""
    now = datetime.now(JST)
    target = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if now.hour >= 22:
        target += timedelta(days=1)
    existing = get_existing_future_dates(server)
    while target.strftime("%Y%m%d") in existing:
        print(f"[INFO] {target.strftime('%Y-%m-%d')} 既存予約あり、翌日にシフト")
        target += timedelta(days=1)
    return target


def retry(func, *args, attempts=3, wait=20, label="", **kwargs):
    """失敗時に最大attempts回リトライ（指数バックオフ: 20秒→40秒→停止）"""
    for i in range(1, attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == attempts:
                print(f"[FAIL] {label} | 試行{i}/{attempts} 最終失敗: {e}")
                raise
            wait_sec = wait * (2 ** (i - 1))
            print(f"[WARN] {label} | 試行{i}/{attempts} 失敗: {e}")
            print(f"       {wait_sec}秒後にリトライします...")
            time.sleep(wait_sec)


def validate_article(html, min_chars=1500):
    """生成記事の品質チェック"""
    if not html or len(html) < min_chars:
        raise ValueError(
            f"記事が短すぎます ({len(html) if html else 0}文字 / 最低{min_chars}文字必要)"
        )
    if "<h1" not in html.lower():
        raise ValueError("H1タグが見つかりません（記事生成失敗の可能性）")
    print(f"[OK] 記事バリデーション通過 ({len(html)}文字)")
    return True


def check_env(keys):
    """必要な環境変数の存在確認（起動時に必ず実行）"""
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        print(f"[FATAL] 環境変数未設定: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] 環境変数確認: {', '.join(keys)}")



WP_URL = "https://toushi-kenja.com"
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]
WP_USERNAME = os.environ["TOUSHI_WP_USERNAME"]
WP_APP_PASSWORD = os.environ["TOUSHI_WP_APP_PASSWORD"]

# A8.net・もしもアフィリエイトのFX・証券口座リンク（承認後に差し替え）
AFFILIATE_LINKS = {
    "XServer VPS for FX プレミアム": "https://px.a8.net/svt/ejp?a8mat=4B3U75+805VVU+CO4+44UKYA",
    "シンクラウドデスクトップ for FX": "https://px.a8.net/svt/ejp?a8mat=4B3U75+893DYI+5GDG+HV7V6",
    "FXTF（ゴールデンウェイ・ジャパン）": "https://px.a8.net/svt/ejp?a8mat=4B3U75+89OTKA+48D0+6A4FM",
    "シストレセレクト365（FX自動売買）": "https://px.a8.net/svt/ejp?a8mat=4B3U75+8BH4DM+34QW+BWVTE",
    "GMOクリック証券【FXneo】": "https://toushi-kenja.com",
    "SBI FXトレード": "https://toushi-kenja.com",
    "外為どっとコム": "https://toushi-kenja.com",
    "みんなのFX": "https://toushi-kenja.com",
    "ヒロセ通商 LION FX": "https://toushi-kenja.com",
    "OANDA証券": "https://toushi-kenja.com",
    "IG証券": "https://toushi-kenja.com",
    "楽天FX": "https://toushi-kenja.com",
    "SBI証券": "https://toushi-kenja.com",
    "楽天証券": "https://toushi-kenja.com",
    "マネックス証券": "https://toushi-kenja.com",
    "松井証券": "https://px.a8.net/svt/ejp?a8mat=4B3U75+8TXK4Q+3XCC+6AZAQ",
    "auカブコム証券": "https://toushi-kenja.com",
    "岡三オンライン証券": "https://toushi-kenja.com",
    "PayPay証券": "https://toushi-kenja.com",
    "JFX（2025年オリコン顧客満足度FX総合1位）": "https://px.a8.net/svt/ejp?a8mat=4B3U75+8EGAEI+25B2+5YZ76",
    "ALTERNA（オルタナ・三井物産グループデジタル証券）": "https://px.a8.net/svt/ejp?a8mat=4B3U75+9713FU+5PYG+5YJRM",
    # 不動産投資系
    "クロスハウス（不動産管理・空室対策）": "https://px.a8.net/svt/ejp?a8mat=4B3WJ8+9FD5WQ+4EZ2+NTJWY",
    "JPリターンズ（マンション投資・無料面談）": "https://px.a8.net/svt/ejp?a8mat=4B3WJ8+AP7JHM+40OC+BWVTE",
    "不動産投資ドットコム（企業比較・紹介）": "https://af.moshimo.com/af/c/click?a_id=5580543&p_id=3600&pc_id=8700&pl_id=50665",
    "音羽トレンディ（新築一戸建・仲介手数料無料）": "https://af.moshimo.com/af/c/click?a_id=5580542&p_id=4123&pc_id=10449&pl_id=56548",
    "Oh!Ya（不動産投資一括資料請求）": "https://af.moshimo.com/af/c/click?a_id=5580538&p_id=4996&pc_id=13383&pl_id=66149",
    "Oh!Ya（不動産投資無料相談）": "https://af.moshimo.com/af/c/click?a_id=5580537&p_id=4998&pc_id=13387&pl_id=66153",
    "リフォームガイド（マンションリノベーション）": "https://af.moshimo.com/af/c/click?a_id=5580535&p_id=5572&pc_id=15281&pl_id=71782",
    "解体工事見積りnet（解体工事一括見積り）": "https://af.moshimo.com/af/c/click?a_id=5580530&p_id=7529&pc_id=21742&pl_id=94384",
}

KEYWORDS = [
    # ★超低難易度・高ボリューム（Ubersuggest実データ）
    "FX 税金 確定申告 やり方",           # Vol:8,100 SEO:17
    "FX 口座開設 ボーナス おすすめ",      # Vol:2,400 SEO:12
    "FX 複利計算 シミュレーション",       # Vol:1,600 SEO:15
    "FX 損失 確定申告 申告方法",          # Vol:1,600 SEO:16
    "FX 手法 初心者 おすすめ",           # Vol:880 SEO:17
    "FX 口座 おすすめ 比較 2026",        # Vol:2,400 SEO:26
    "FX チャートパターン 種類 見方",      # Vol:1,600 SEO:26
    # FX口座・サービス系
    "FX おすすめ 口座 2026 初心者",
    "FX 口座 比較 スプレッド 手数料",
    "FX 始め方 初心者 手順",
    "FX 自動売買 おすすめ EA",           # Vol:6,600 SEO:38
    "FXTF 評判 口コミ スプレッド",       # Vol:6,600 SEO:39
    "FX チャート 見方 初心者",           # Vol:12,100 SEO:42
    "GMOクリック証券 評判 口コミ FX",
    "SBI FXトレード 評判 スプレッド",
    "外為どっとコム 評判 特徴",
    "みんなのFX 評判 スワップ",
    "ヒロセ通商 LION FX 評判",
    "OANDA証券 評判 スプレッド",
    "楽天証券 FX 評判 スプレッド",       # Vol:1,900 SEO:36
    "FX スワップポイント おすすめ 長期",  # Vol:1,300 SEO:45
    "FX アプリ おすすめ スマホ",         # Vol:1,300 SEO:44
    "FX スキャルピング 口座 おすすめ",   # Vol:2,400 SEO:36
    "FX スプレッド 比較 最狭",           # Vol:1,000 SEO:35
    "FX レバレッジ 最大 規制 仕組み",    # Vol:1,000 SEO:34
    "FX インジケーター おすすめ 初心者", # Vol:1,300 SEO:34
    "FX ロット 計算 方法",               # Vol:880 SEO:38
    "FX 取引時間 市場 24時間",           # Vol:880 SEO:35
    "FX デイトレード 手法 初心者",
    "FX 少額 1万円 始める",
    "FX 勝率 上げる 方法",
    "FX 専業トレーダー 条件 年収",
    "ドル円 FX 取引 コツ",
    "FX スプレッド 比較 狭い",
    "FX ポジション 管理 コツ",
    "FX 移動平均線 使い方",
    "FX RSI MACD 使い方",
    # 証券口座系
    "証券口座 おすすめ 2026 初心者",
    "ネット証券 比較 手数料 ランキング",
    "SBI証券 評判 口コミ 2026",
    "楽天証券 評判 口コミ 2026",
    "マネックス証券 評判 特徴",
    "松井証券 評判 手数料",
    "auカブコム証券 評判 NISA",
    "岡三オンライン証券 評判",
    "証券口座 開設 方法 手順",
    "証券口座 複数 使い分け メリット",
    "NISA 口座 どこがいい 比較",
    "つみたてNISA 銘柄 おすすめ 2026",
    "iDeCo 証券会社 選び方 比較",
    "米国株 証券口座 おすすめ 手数料",
    "投資信託 始め方 初心者 手順",
    "株式投資 初心者 始め方 証券口座",
    "配当金 高配当株 おすすめ 証券",
    "ETF 投資 おすすめ 証券口座",
    "IPO 当選確率 証券会社 比較",
    "証券口座 手数料 無料 比較",
    # Ubersuggest追加（2026-05-20）
    "FX 初心者 口座開設 おすすめ",               # Vol:10  SEO:15
    "FX 口座開設 日数",                           # Vol:10  SEO:23
    # 投資全般
    "投資 初心者 何から始める",
    "資産形成 方法 おすすめ 2026",
    "積立投資 月1万円 シミュレーション",
    "投資 リスク 分散 やり方",
    "株 デイトレード 始め方 口座",
    "長期投資 証券口座 おすすめ",
    "インデックス投資 始め方 証券",
    "証券口座 スマホ アプリ 使いやすい",
    "株 配当生活 いくら必要",
    "投資 税金 節税 方法",
]


def get_font(size):
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
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

    # ネイビー×ゴールド（投資・金融テーマ）
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

    # キーワードバッジ
    font_badge = get_font(28)
    badge_text = f"#{kw}"
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw, bh = bbox[2] - bbox[0] + 30, bbox[3] - bbox[1] + 16
    draw.rounded_rectangle([60, 55, 60 + bw, 55 + bh], radius=18, fill=accent)
    draw.text((75, 63), badge_text, font=font_badge, fill=(10, 20, 60))

    # サイト名
    font_site = get_font(26)
    site_text = "投資の賢者 | toushi-kenja.com"
    bbox = draw.textbbox((0, 0), site_text, font=font_site)
    draw.text((W - bbox[2] + bbox[0] - 60, 68), site_text, font=font_site, fill=(212, 175, 55))

    # タイトル（折り返し・自動フォントサイズ）
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
    def _upload():
        data = {
            'name': filename,
            'type': 'image/jpeg',
            'bits': xmlrpc.client.Binary(image_bytes),
            'overwrite': False,
        }
        result = server.wp.uploadFile(0, WP_USERNAME, WP_APP_PASSWORD, data)
        attachment_id = result.get('id')
        print("画像アップロード成功 ID:", attachment_id)
        return attachment_id
    try:
        return retry(_upload, label="画像アップロード", attempts=3, wait=10)
    except Exception as e:
        print("画像アップロード失敗（投稿は続行）:", str(e))
        return None


def make_affiliate_html(kw):
    items = random.sample(list(AFFILIATE_LINKS.items()), min(3, len(AFFILIATE_LINKS)))
    html = '<div style="background:#f8f4e0;padding:20px;margin:20px 0;border-radius:8px;border-left:4px solid #d4af37;">'
    html += f'<p style="font-weight:bold;font-size:16px;">▼ {kw}でおすすめのFX・証券口座はこちら</p>'
    for name, url in items:
        html += f'<p>✅ <a href="{url}" target="_blank" rel="nofollow" style="color:#b8860b;font-weight:bold;">{name}【公式】無料口座開設はこちら</a></p>'
    html += '</div>'
    return html


def make_article(kw):
    http_client = httpx.Client(verify=False, timeout=120.0)
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, http_client=http_client)
    from datetime import datetime
    year = datetime.now().year
    t = f"あなたはFX・株式投資・証券口座に精通したSEOとアフィリエイト収益化のプロライターです。\n"
    t += f"現在の年は{year}年です。タイトルや本文に年を記載する場合は必ず{year}年と書いてください。\n"
    t += f"以下のテーマで検索上位を狙えるSEOに強いHTML形式の記事を書いてください。\n"
    t += f"テーマ：{kw}\n\n"
    t += "【SEOルール】\n"
    t += "・タイトルにキーワードを含め、数字や「比較」「おすすめ」「選び方」を入れてクリック率を上げる\n"
    t += "・h2見出しにも関連キーワードを自然に含める\n"
    t += "・最初の100字以内にキーワードを入れてリード文を書く\n"
    t += "・2500字以上の充実した内容にする\n"
    t += "・比較表（tableタグ）を必ず1つ以上入れる\n\n"
    t += "【収益強化ルール】\n"
    t += "・FX口座・証券口座のメリット・デメリットを正直に書いて信頼性を高める\n"
    t += "・「こんな人におすすめ」を明確に書く\n"
    t += "・無料口座開設を促すCTA文を各サービス紹介の後に入れる\n"
    t += "・スプレッド・手数料・取扱通貨ペア・ツールの使いやすさを具体的な数字・事実で書く\n\n"
    t += "【構成】\n"
    t += "<h1>【数字・年入り・クリックされやすいタイトル】</h1>\n"
    t += "<p>リード文（読者の投資の悩みに共感し、この記事で解決できると伝える）</p>\n"
    t += "<h2>【キーワード】の選び方3つのポイント</h2>\n"
    t += "<h2>おすすめFX・証券口座比較表</h2>\n"
    t += "AFFILIATE_LINK\n"
    t += "<h2>各サービスの詳細レビュー</h2>\n"
    t += "<h2>FX・投資の始め方・活用術</h2>\n"
    t += "<h2>よくある質問（FAQ）</h2>\n"
    t += "<h2>まとめ</h2>\n\n"
    t += "HTML形式で書いてください。比較表はtableタグで作成し、FAQはschema.org対応の構造化データも含めてください。"

    def _call_claude():
        msg = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=5000,
            messages=[{"role": "user", "content": t}],
        )
        return msg.content[0].text

    article = retry(_call_claude, label="Claude API", attempts=3, wait=30)
    article = article.replace("AFFILIATE_LINK", make_affiliate_html(kw))
    # 不動産投資LP誘導バナーを記事末尾に追加
    lp_banner = '''
<div style="background:#0f2a1a;border:2px solid #c8a84b;border-radius:8px;padding:24px;margin:40px 0;text-align:center;">
  <p style="font-size:13px;color:#c8a84b;font-weight:bold;letter-spacing:2px;margin-bottom:8px">▼ 不動産投資で資産形成を始めたい方へ</p>
  <p style="font-size:13px;color:#aaa;margin-bottom:16px">厳選7社から無料で相談・資料請求できます。相談料0円・勧誘なし。</p>
  <a href="https://toushi-kenja.com/lp/" style="display:inline-block;background:#c8a84b;color:#000;padding:14px 32px;border-radius:4px;font-weight:bold;font-size:15px;text-decoration:none;">不動産投資 無料相談はこちら →</a>
</div>
'''
    article = article + lp_banner
    # KDP書籍誘導バナーを記事末尾に追加（マルヒデ収益化現状マップ準拠）
    kdp_banner = '''
<!-- KDP_BOOK_BANNER_v1 -->
<div style="background:#0a1a4a;border:2px solid #d4af37;border-radius:8px;padding:28px;margin:40px 0;text-align:center;">
  <p style="font-size:13px;color:#d4af37;font-weight:bold;letter-spacing:2px;margin:0 0 12px 0">📚 著者の体験記 — Amazon Kindle 発売中</p>
  <p style="font-size:22px;color:#fff;font-weight:bold;margin:8px 0 4px;line-height:1.4">生成AIが人生を変えた。</p>
  <p style="font-size:13px;color:#bbb;margin:0 0 16px;line-height:1.6">中卒・借金・うつ病「平成最後の愚か者」が<br>AIと組んで1週間で人生を変えた全記録</p>
  <p style="font-size:13px;color:#d4af37;margin:0 0 18px">¥499（Kindle Unlimited会員は無料で読み放題）</p>
  <a href="https://www.amazon.co.jp/dp/B0H29VZJVG" target="_blank" rel="nofollow" style="display:inline-block;background:#d4af37;color:#0a1a4a;padding:14px 36px;border-radius:4px;font-weight:bold;font-size:15px;text-decoration:none;">▶ Amazonで読む</a>
  <p style="font-size:11px;color:#888;margin:14px 0 0">著者：まじこ（マルヒデ代表）</p>
</div>
'''
    article = article + kdp_banner
    return article


def get_title(html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return "FX・証券口座おすすめ記事"


def get_categories(kw):
    fx_keywords = ["FX", "外為", "スワップ", "スプレッド", "EA", "スキャルピング", "ドル円"]
    stock_keywords = ["証券", "株", "NISA", "iDeCo", "ETF", "投資信託", "IPO", "配当"]
    how_keywords = ["始め方", "やり方", "方法", "コツ", "手順", "仕組み"]
    categories = []
    if any(k in kw for k in fx_keywords):
        categories.append("FX口座比較")
    if any(k in kw for k in stock_keywords):
        categories.append("証券口座比較")
    if any(k in kw for k in how_keywords):
        categories.append("投資ノウハウ")
    if not categories:
        categories = ["投資ノウハウ"]
    return categories


def post(title, content, kw):
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        server = xmlrpc.client.ServerProxy(WP_URL + "/xmlrpc.php", context=context)

        thumbnail_id = None
        try:
            print("アイキャッチ画像を生成中...")
            image_bytes = generate_eyecatch(title, kw)
            filename = f"eyecatch_{int(time.time())}.jpg"  # ASCII-only
            thumbnail_id = upload_media_xmlrpc(server, image_bytes, filename)
        except Exception as e:
            print("アイキャッチ生成エラー（投稿は続行）:", str(e))

        fix_missed_posts(server)
        target = get_publish_datetime_safe(server)
        post_date = xmlrpc.client.DateTime(target.strftime("%Y%m%dT%H:%M:%S"))
        print(f"予約投稿時刻（JST）: {target.strftime('%Y-%m-%d %H:%M')}")

        post_data = {
            'post_title': title,
            'post_content': content,
            'post_status': 'future',
            'post_date': post_date,
            'post_type': 'post',
            'terms_names': {'category': get_categories(kw)},
        }
        if thumbnail_id:
            post_data['post_thumbnail'] = int(thumbnail_id)

        result = retry(
            lambda: server.wp.newPost(0, WP_USERNAME, WP_APP_PASSWORD, post_data),
            label="WordPress投稿", attempts=3, wait=15
        )
        print("投稿成功！投稿ID:", result)
    except Exception as e:
        print("Error:", str(e))
        raise


def main():
    start = datetime.now(JST)
    print(f"[START] {start.strftime('%Y-%m-%d %H:%M:%S JST')}")
    check_env(["CLAUDE_API_KEY", "TOUSHI_WP_USERNAME", "TOUSHI_WP_APP_PASSWORD"])
    kw = random.choice(KEYWORDS)
    print("キーワード:", kw)
    print("記事を生成中... (1〜2分かかります)")
    html = make_article(kw)
    title = get_title(html)
    print("タイトル:", title)
    print("WordPressに投稿中...")
    post(title, html, kw)
    end = datetime.now(JST)
    print(f"[END] {end.strftime('%Y-%m-%d %H:%M:%S JST')} (所要時間: {int((end-start).total_seconds())}秒)")


if __name__ == "__main__":
    main()
