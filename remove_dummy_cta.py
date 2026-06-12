"""既存記事に残る「自サイト仮置きダミーCTA（空リンク）」を一括削除する（案A：削除のみ）。

背景: 提携承認未取得の証券・FX12社（GMOクリック証券/SBI FXトレード/外為どっとコム/
みんなのFX/OANDA証券/IG証券/楽天FX/SBI証券/楽天証券/auカブコム証券/岡三オンライン証券/
PayPay証券）のCTAは、href が本物ASPではなく自サイトトップ（WP_URL）を指す「空リンク」
だった。収益ゼロ＋信頼毀損のため bot.py 側は削除済（今後の記事は本物リンクのみ）。
本スクリプトは既に公開/予約済みの記事DB内に残るダミーCTAを是正する。

判定基準（誤爆防止の肝）:
- 本物リンクは必ず外部ASP（px.a8.net / af.moshimo.com / h.accesstrade.net / click.j-a-net.jp）。
- ダミーは <a href> が自サイトドメイン（WP_URL）を指す。
- 削除の結果、CTA div 内に本物CTAが1件も残らなければ div ごと削除（空箱を残さない）。

安全装置:
- DRY_RUN 既定（実更新は DRY_RUN=0 を明示）。
- 実更新時は更新前の post_content を backup/ に <ID>.html で保存（ロールバック用）。
- 冪等: ダミーCTAが無い記事はスキップ。再実行しても二重処理しない。
"""
import os
import re
import ssl
import xmlrpc.client
from urllib.parse import urlparse

import bot  # WP_URL / WP_USERNAME / WP_APP_PASSWORD を再利用

DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")

SITE_HOST = urlparse(bot.WP_URL).netloc.lower()

# CTAの1行（投資の make_affiliate_html 出力に対応）
CTA_P_RE = re.compile(
    r'<p>\s*✅\s*<a\s+href="([^"]*)"[^>]*>[^<]*【公式】無料口座開設はこちら</a>\s*</p>',
    flags=re.I,
)
# CTAボックス全体（背景 #f8f4e0）
CTA_DIV_RE = re.compile(
    r'<div style="background:#f8f4e0;[^"]*">.*?</div>',
    flags=re.I | re.S,
)


def _is_dummy(href):
    host = urlparse(href).netloc.lower()
    return host == SITE_HOST or host == ""


def clean_content(content):
    removed = [0]

    def fix_div(m):
        block = m.group(0)

        def drop_dummy_p(pm):
            href = pm.group(1)
            if _is_dummy(href):
                removed[0] += 1
                return ""
            return pm.group(0)

        new_block = CTA_P_RE.sub(drop_dummy_p, block)
        if not CTA_P_RE.search(new_block):
            return ""
        return new_block

    new = CTA_DIV_RE.sub(fix_div, content)
    return new, removed[0]


def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    server = xmlrpc.client.ServerProxy(bot.WP_URL + "/xmlrpc.php", context=ctx)

    scanned = targets = updated = removed_total = 0
    seen = set()
    for status in ("publish", "future"):
        try:
            posts = server.wp.getPosts(0, bot.WP_USERNAME, bot.WP_APP_PASSWORD,
                {"post_status": status, "number": 200, "post_type": "post"})
        except Exception as e:
            print(f"[WARN] getPosts({status})失敗: {e}")
            continue
        for p in posts:
            pid = p.get("post_id")
            if pid in seen:
                continue
            seen.add(pid)
            scanned += 1
            content = p.get("post_content", "") or ""
            new, n = clean_content(content)
            if n > 0 and new != content:
                targets += 1
                removed_total += n
                title = (p.get("post_title", "") or "")[:40]
                print(f"[{'DRY' if DRY_RUN else 'FIX'}] ID={pid} status={status} ダミー削除={n} | {title}")
                if not DRY_RUN:
                    with open(os.path.join(BACKUP_DIR, f"{pid}.html"), "w", encoding="utf-8") as f:
                        f.write(content)
                    try:
                        server.wp.editPost(0, bot.WP_USERNAME, bot.WP_APP_PASSWORD, pid,
                            {"post_content": new})
                        updated += 1
                    except Exception as e:
                        print(f"  [ERROR] editPost失敗 ID={pid}: {e}")

    mode = "DRY_RUN(変更なし)" if DRY_RUN else "実更新"
    print(f"=== ダミーCTA除去完了 [{mode}] 走査={scanned} 対象記事={targets} "
          f"削除リンク総数={removed_total} 実更新={updated} ===")


if __name__ == "__main__":
    main()
