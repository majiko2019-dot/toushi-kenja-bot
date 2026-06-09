"""既存記事のh2色ダブり一括retrofit。

背景: 2026-06-07〜08のレイアウト改修で bot.py が h2 にインライン color:濃紺 を焼き込み、
SWELLテーマの h2{background:濃紺;color:#fff} と重なって「濃紺背景＋濃紺文字」の色ダブりに
なった（h2のみ・全SWELLサイト共通の回帰）。bot.py側は class="swell-block-..." 付与で修正済だが、
既に公開/予約済みの記事HTMLには旧h2が焼き込まれたまま残るため、本スクリプトで一括是正する。

設計:
- bot.style_article_html() に素のh2を1個通して「このサイトの正規h2開始タグ」を取得（サイト固有色＋
  除外class＋背景白を含む）→ ハードコードなし・bot本体と常に一致。
- 公開(publish)・予約(future)記事を走査し、不具合h2のみ正規タグへ置換。
- 冪等: 既に class="swell-block-ckh2" を含むh2はスキップ（再実行しても二重修正しない）。
- h2以外（p/table/リード/本文）は一切触らない。
- DRY_RUN=1 で更新せずログのみ（既定はDRY_RUN扱い＝安全側。実更新は DRY_RUN=0 を明示）。
"""
import os
import re
import ssl
import xmlrpc.client

import bot  # WP_URL / WP_USERNAME / WP_APP_PASSWORD / style_article_html を再利用

# 既定は安全側（DRY_RUN）。実際に書き換えるときだけ DRY_RUN=0 を明示する。
DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"

# bot本体から「このサイトの正規h2開始タグ」を1個生成して取得
_sample = bot.style_article_html("<h2>sample</h2>")
_m = re.search(r"<h2\b[^>]*>", _sample, flags=re.I)
if not _m or "swell-block-ckh2" not in _m.group(0):
    raise SystemExit("[ABORT] 正規h2タグの取得に失敗（bot.py修正が未反映の可能性）")
GOOD_H2_OPEN = _m.group(0)


def fix_h2(content):
    """contentの不具合h2を正規h2へ置換。(新content, 置換件数)を返す。冪等。"""
    count = [0]

    def repl(m):
        tag = m.group(0)
        if "swell-block-ckh2" in tag:
            return tag  # 修正済み＝触らない
        count[0] += 1
        return GOOD_H2_OPEN

    new = re.sub(r"<h2\b[^>]*>", repl, content, flags=re.I)
    return new, count[0]


def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    server = xmlrpc.client.ServerProxy(bot.WP_URL + "/xmlrpc.php", context=ctx)

    scanned = 0
    targets = 0
    updated = 0
    seen = set()
    for status in ("publish", "future"):
        try:
            posts = server.wp.getPosts(0, bot.WP_USERNAME, bot.WP_APP_PASSWORD,
                {"post_status": status, "number": 100, "post_type": "post"})
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
            new, n = fix_h2(content)
            if n > 0 and new != content:
                targets += 1
                title = (p.get("post_title", "") or "")[:40]
                print(f"[{'DRY' if DRY_RUN else 'FIX'}] ID={pid} status={status} h2修正={n} | {title}")
                if not DRY_RUN:
                    try:
                        server.wp.editPost(0, bot.WP_USERNAME, bot.WP_APP_PASSWORD, pid,
                            {"post_content": new})
                        updated += 1
                    except Exception as e:
                        print(f"  [ERROR] editPost失敗 ID={pid}: {e}")

    mode = "DRY_RUN(変更なし)" if DRY_RUN else "実更新"
    print(f"=== retrofit完了 [{mode}] 走査={scanned} 修正対象={targets} 実更新={updated} ===")


if __name__ == "__main__":
    main()
