import xmlrpc.client
import os

WP_URL = "https://toushi-kenja.com"
WP_USERNAME = os.environ["TOUSHI_WP_USERNAME"]
WP_APP_PASSWORD = os.environ["TOUSHI_WP_APP_PASSWORD"]

SITE_NAME = "投資の賢者"
SITE_URL = "https://toushi-kenja.com"
OPERATOR_NAME = "マルヒデ"
OPERATOR_ADDRESS = "〒103-0026 東京都中央区日本橋兜町17-2 兜町第6葉山ビル4F"
OPERATOR_TEL = "03-6555-3724"
OPERATOR_EMAIL = "majiko2019@gmail.com"

PAGES = [
    {
        "title": "プライバシーポリシー",
        "slug": "privacy-policy",
        "content": f"""
<p>当サイト「{SITE_NAME}」（{SITE_URL}）では、お客様の個人情報の取り扱いについて、以下のとおりプライバシーポリシーを定めます。</p>

<h2>アフィリエイト広告について</h2>
<p>当サイトは、A8.net・もしもアフィリエイト等のアフィリエイトプログラムに参加しています。記事内に広告リンクが含まれており、リンクを経由してFX口座・証券口座へご登録いただいた場合、当サイトに報酬が発生することがあります。なお、広告の有無にかかわらず、当サイトは公正・中立な立場で情報を提供します。</p>

<h2>投資に関する注意事項</h2>
<p>当サイトで紹介するFX・株式投資・証券口座に関する情報は、投資の勧誘を目的とするものではありません。投資にはリスクが伴います。実際の投資判断はご自身の責任において行ってください。</p>

<h2>個人情報の収集について</h2>
<p>当サイトでは、お問い合わせの際にお名前・メールアドレス等の個人情報をご提供いただく場合があります。収集した個人情報は、お問い合わせへの返答以外の目的には使用しません。</p>

<h2>アクセス解析ツールについて</h2>
<p>当サイトでは、Googleによるアクセス解析ツール「Googleアナリティクス」を使用しています。このGoogleアナリティクスはデータ収集のためにCookieを使用しています。このデータは匿名で収集されており、個人を特定するものではありません。Cookieを無効にすることで収集を拒否することができます。詳しくは<a href="https://policies.google.com/privacy" target="_blank" rel="nofollow">Googleのプライバシーポリシー</a>をご確認ください。</p>

<h2>広告の配信について</h2>
<p>当サイトでは、第三者配信の広告サービス（Googleアドセンス等）を利用する場合があります。このような広告配信事業者はユーザーの興味に応じた広告を表示するためにCookieを使用することがあります。</p>

<h2>Cookieについて</h2>
<p>当サイトでは、一部のページでCookieを使用しています。お使いのブラウザの設定でCookieを無効にすることができますが、その場合、一部のサービスが正常に機能しない場合があります。</p>

<h2>免責事項</h2>
<p>当サイトの情報は、正確性・最新性の確保に努めていますが、内容の正確性・安全性・有用性等について保証するものではありません。当サイトの情報を利用して生じたいかなる損害についても、当サイトは一切の責任を負いません。</p>

<h2>著作権について</h2>
<p>当サイトに掲載されているコンテンツ（文章・画像等）の著作権は、当サイト運営者に帰属します。無断転載・複製を禁じます。</p>

<h2>プライバシーポリシーの変更</h2>
<p>当サイトは、必要に応じて本プライバシーポリシーを変更することがあります。変更後のポリシーは本ページに掲載した時点で効力を生じます。</p>

<h2>お問い合わせ</h2>
<p>本ポリシーに関するお問い合わせは、<a href="{SITE_URL}/contact/">お問い合わせページ</a>よりご連絡ください。</p>

<p>制定日：2026年5月19日<br>運営者：{OPERATOR_NAME}</p>
"""
    },
    {
        "title": "免責事項",
        "slug": "disclaimer",
        "content": f"""
<h2>投資リスクについて</h2>
<p>当サイト「{SITE_NAME}」（{SITE_URL}）で紹介するFX・株式投資・証券口座に関する情報は、投資の勧誘を目的とするものではありません。FX取引・株式投資にはリスクが伴い、元本割れが生じる可能性があります。実際の投資判断はご自身の責任において行ってください。</p>

<h2>情報の正確性について</h2>
<p>当サイトに掲載されている情報は、正確性・最新性の確保に努めていますが、FX・証券会社のサービス内容・スプレッド・手数料等は予告なく変更される場合があります。最新情報は必ず各社の公式サイトでご確認ください。</p>

<h2>損害について</h2>
<p>当サイトの情報を利用して生じたいかなる損害（直接的・間接的を問わず）についても、当サイト運営者は一切の責任を負いません。投資・取引に関する最終的なご判断はご自身の責任のもとで行ってください。</p>

<h2>外部リンクについて</h2>
<p>当サイトには外部サイトへのリンクが含まれています。リンク先のサイトのコンテンツについて、当サイトは責任を負いません。</p>

<h2>アフィリエイトリンクについて</h2>
<p>当サイトはアフィリエイト広告を含みます。アフィリエイトリンクを経由してのFX口座・証券口座のご開設については、各社の利用規約が適用されます。</p>

<p>制定日：2026年5月19日<br>運営者：{OPERATOR_NAME}</p>
"""
    },
    {
        "title": "運営者情報",
        "slug": "about",
        "content": f"""
<p>当サイト「{SITE_NAME}」の運営者情報をご案内します。</p>

<table>
<tbody>
<tr><th>屋号</th><td>{OPERATOR_NAME}</td></tr>
<tr><th>所在地</th><td>{OPERATOR_ADDRESS}</td></tr>
<tr><th>電話番号</th><td>{OPERATOR_TEL}</td></tr>
<tr><th>メールアドレス</th><td>{OPERATOR_EMAIL}</td></tr>
<tr><th>サイト名</th><td>{SITE_NAME}</td></tr>
<tr><th>サイトURL</th><td>{SITE_URL}</td></tr>
<tr><th>運営開始</th><td>2026年5月</td></tr>
<tr><th>事業内容</th><td>FX・証券口座比較・投資情報の提供</td></tr>
</tbody>
</table>

<h2>サイトについて</h2>
<p>「{SITE_NAME}」は、FX口座・証券口座の比較と投資ノウハウ情報を提供するメディアサイトです。初心者から経験者まで、あなたに最適なFX口座・証券口座選びをサポートします。</p>

<p>当サイトはアフィリエイト広告を含みます。広告の有無にかかわらず、公正・中立な情報提供を心がけています。</p>

<h2>投資に関する注意</h2>
<p>当サイトの情報は投資の勧誘を目的としません。FX・株式投資にはリスクが伴います。投資判断はご自身の責任でお願いします。</p>
"""
    },
    {
        "title": "著者プロフィール",
        "slug": "profile",
        "content": f"""
<h2>著者プロフィール</h2>
<p><strong>まじこ</strong>（マルヒデ代表）</p>

<p>中卒・借金・うつ病という「どん底」から、生成AIと組んで複数の事業を立ち上げた実践者です。その全記録をまとめた電子書籍『生成AIが人生を変えた。』をAmazon Kindleで出版しました。</p>

<p>「専門用語だらけで挫折した」という自分自身の経験から、初心者が本当に知りたいことを<strong>正直に・分かりやすく</strong>伝えることをモットーに、「{SITE_NAME}」の記事を執筆・監修しています。</p>

<p>FX・証券口座・投資の情報は、公開情報や各社公式サイトに基づき、メリットだけでなくデメリットも含めて中立的にお伝えすることを心がけています。</p>

<h2>著書</h2>
<p>📚 <a href="https://www.amazon.co.jp/dp/B0H29VZJVG" target="_blank" rel="nofollow">生成AIが人生を変えた。</a>（Amazon Kindle）</p>

<h2>運営</h2>
<p>運営者：{OPERATOR_NAME}（<a href="{SITE_URL}/about/">運営者情報はこちら</a>）</p>
"""
    },
    {
        "title": "お問い合わせ",
        "slug": "contact",
        "content": f"""
<p>「{SITE_NAME}」へのお問い合わせは、以下の方法にてお受けしております。</p>

<h2>お問い合わせ先</h2>
<table>
<tbody>
<tr><th>運営者</th><td>{OPERATOR_NAME}</td></tr>
<tr><th>電話番号</th><td>{OPERATOR_TEL}</td></tr>
<tr><th>メールアドレス</th><td>{OPERATOR_EMAIL}</td></tr>
<tr><th>所在地</th><td>{OPERATOR_ADDRESS}</td></tr>
</tbody>
</table>

<h2>対応時間</h2>
<p>平日 9:00〜18:00（土日祝日を除く）<br>
※お問い合わせ内容によっては、ご返答までにお時間をいただく場合があります。</p>

<h2>お問い合わせの前に</h2>
<p>FX・証券口座の取引に関するお問い合わせは、各社へ直接お問い合わせください。当サイトでは個別の投資・取引についてのご相談はお受けしておりません。</p>
"""
    },
]


def get_existing_pages(server):
    """既存固定ページのslug・タイトル集合を返す（重複作成防止）"""
    existing = set()
    try:
        pages = server.wp.getPosts(0, WP_USERNAME, WP_APP_PASSWORD,
            {"post_type": "page", "number": 100})
        for pg in pages:
            if pg.get("post_name"):
                existing.add(pg["post_name"])
            if pg.get("post_title"):
                existing.add(pg["post_title"])
    except Exception as e:
        print(f"[WARN] 既存ページ取得失敗（全件作成を試みます）: {e}")
    return existing


def create_page(server, page):
    post_data = {
        'post_title': page['title'],
        'post_content': page['content'],
        'post_status': 'publish',
        'post_type': 'page',
        'wp_slug': page['slug'],
    }
    result = server.wp.newPost(0, WP_USERNAME, WP_APP_PASSWORD, post_data)
    print(f"✅ 作成完了：{page['title']}（ID: {result}）")
    return result


def main():
    server = xmlrpc.client.ServerProxy(WP_URL + "/xmlrpc.php")

    print(f"=== {SITE_NAME} 固定ページ作成開始 ===")
    existing = get_existing_pages(server)
    for page in PAGES:
        if page['slug'] in existing or page['title'] in existing:
            print(f"⏭ スキップ（既存）：{page['title']}")
            continue
        try:
            create_page(server, page)
        except Exception as e:
            print(f"❌ エラー：{page['title']} - {e}")
    print("=== 完了 ===")


if __name__ == "__main__":
    main()
