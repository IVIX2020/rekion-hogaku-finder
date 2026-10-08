"""List the 国立国会図書館「歴史的音源」 recordings that are open on the internet (rights expired), by genre.

Uses the digital collection's own search (collection 歴史的音源, internet-open only) for each genre keyword,
and writes 台本/歴史的音源_公開一覧.md and .csv.

    python3 scripts/rekion_catalog.py
"""

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENRES = [
    ("民謡", ["民謡", "俚謡"]),
    ("端唄・小唄・俗曲", ["端唄", "小唄", "俗曲", "うた沢"]),
    ("わらべうた・子守唄・童謡", ["子守", "わらべ", "童謡"]),
    ("長唄", ["長唄"]),
    ("清元・常磐津・新内", ["清元", "常磐津", "新内"]),
    ("義太夫", ["義太夫"]),
    ("地歌・箏曲", ["地唄", "箏曲", "琴曲"]),
    ("尺八", ["尺八"]),
    ("雅楽", ["雅楽"]),
]
API = "https://dl.ndl.go.jp/api/item/search"
REKION = "A00024"  # the 歴史的音源 collection


def search(keyword):
    """All internet-open 歴史的音源 items matching the keyword (digital-collection search API)."""
    out, page = [], 0
    while True:
        body = {"accessRestrictions": ["internet"], "fullText": False, "pageNum": str(page), "pageSize": "100",
                "sortKey": "SCORE", "order": "DESC", "collection": [REKION], "keyword": keyword, "eraType": "AD"}
        req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
        except Exception:
            break
        hits = d.get("searchHits") or []
        out += [h["content"] for h in hits]
        if len(hits) < 100 or page > 30:
            break
        page += 1
    return out


def row(c):
    m = c["meta"]
    people = m.get("0010Dtct", [])
    authored = [p for p in people if ("[作詞]" in p or "[作曲]" in p) and not any(x in p for x in ("民謡", "不詳", "PD", "端唄", "俚謡"))]
    return {
        "pid": c["itemId"],
        "title": m.get("0001Dtct", [""])[0],
        "people": " ".join(dict.fromkeys(people)),
        "date": m.get("0059Dk", [""])[0].replace("0000", "").strip(),
        "label": m.get("0020Dtct", [""])[0],
        "duration": (m.get("0074Dt", [""])[0] or "").replace("収録時間 : ", ""),
        "check": "作者の没年を確認" if authored else "",
        "url": f"https://dl.ndl.go.jp/pid/{c['itemId']}",
    }


def main():
    rows = {}
    for genre, words in GENRES:
        n = 0
        for w in words:
            for c in search(w):
                if c["itemId"] in rows:
                    continue
                r = row(c)
                r["genre"] = genre
                rows[c["itemId"]] = r
                n += 1
        print(genre, n)

    order = [g for g, _ in GENRES]
    items = sorted(rows.values(), key=lambda r: (order.index(r["genre"]), r["title"]))
    with open(ROOT / "台本/歴史的音源_公開一覧.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["genre", "title", "people", "date", "label", "duration", "check", "pid", "url"])
        w.writeheader()
        w.writerows(items)

    lines = [
        "# 国立国会図書館「歴史的音源」インターネット公開（保護期間満了）の邦楽一覧",
        "",
        "`python3 scripts/rekion_catalog.py` で作った一覧（国立国会図書館デジタルコレクションの検索で、コレクション「歴史的音源」・インターネット公開に絞り、ジャンル名で検索）。検索語にかからないものは入っていない。",
        "",
        "- 公開範囲「インターネット公開（保護期間満了）」は、手続きなしで二次利用できると国立国会図書館が案内している（実演・レコードの権利が切れている）",
        "- **「作者の没年を確認」**：作詞・作曲者の名がある新作。曲そのものの著作権は、日本では1967年以前に亡くなった作者なら切れている。それ以後なら使えない",
        "- 伝承曲（作者が「民謡」「不詳」など）は、曲の権利の問題はない",
        "- 音は SP の針音そのまま（ノイズ除去なし）",
        "",
    ]
    for genre in order:
        sub = [r for r in items if r["genre"] == genre]
        if not sub:
            continue
        lines += [f"## {genre}（{len(sub)}件）", "", "| 曲名 | 演奏者・作者など | 年 | レーベル | 長さ | 注意 | リンク |", "|---|---|---|---|---|---|---|"]
        for r in sub:
            people = r["people"].replace("|", "／")
            if len(people) > 70:
                people = people[:70] + "…"
            lines.append(f"| {r['title'].replace('|', '／')} | {people} | {r['date']} | {r['label']} | {r['duration']} | {r['check']} | [{r['pid']}]({r['url']}) |")
        lines.append("")
    (ROOT / "台本/歴史的音源_公開一覧.md").write_text("\n".join(lines) + "\n")
    print("wrote 台本/歴史的音源_公開一覧.md and .csv:", len(items), "items")


if __name__ == "__main__":
    main()
