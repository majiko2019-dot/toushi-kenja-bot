"""ダミーCTA除去でCTAが空になった記事へ、本物リンクのCTAを挿入し直す（案B・実リンク埋め戻し）。

背景: remove_dummy_cta.py で自サイト仮置きの空リンクCTAを削除した結果、ダミーのみで
構成されていた記事はCTAボックスごと消え、CTAが1つも無い状態になった。代表方針
「空なら実リンクを入れればいい」に従い、本物ASPリンクのCTAを埋め戻す。

設計:
- CTAボックス（<div style="background:#f8f4e0;...）を1つも持たない記事のみ対象（冪等）。
- 挿入CTAは bot.make_affiliate_html(タイトル) で生成 → 必ず本物ASP（px.a8/もしも/アクセトレ等）のみ。
- 挿入位置は本体と同じく「最初の </h2> 直後」。h2が無ければ末尾に追加。
- DRY_RUN 既定。実更新時は更新前 post_content を backup_backfill/ に保全（ロールバック用）。
"""
import os
import re
import ssl
import xmlrpc.client

import bot  # WP_URL / 認証情報 / make_affiliate_html を再利用

DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_backfill")

CTA_DIV_RE = re.compile(r'<div style="background:#f8f4e0;', flags=re.I)


def has_cta(content):
    return bool(CTA_DIV_RE.search(content))


def insert_cta(content, title):
    if has_cta(content):
        return content, False
    cta = bot.make_affiliate_html(title or "FX・証券口座")
    if "</h2>" in content:
        head, tail = content.split("</h2>", 1)
        new = head + "</h2>" + cta + tail
    else:
        new = content + cta
    return new, True


def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    server = xmlrpc.client.ServerProxy(bot.WP_URL + "/xmlrpc.php", context=ctx)

    scanned = targets = updated = 0
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
            title = (p.get("post_title", "") or "")
            new, did = insert_cta(content, title)
            if did and new != content:
                targets += 1
                print(f"[{'DRY' if DRY_RUN else 'FIX'}] ID={pid} status={status} CTA挿入 | {title[:40]}")
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
    print(f"=== CTA埋め戻し完了 [{mode}] 走査={scanned} 対象記事={targets} 実更新={updated} ===")


if __name__ == "__main__":
    main()
