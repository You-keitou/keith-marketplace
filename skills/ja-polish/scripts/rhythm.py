#!/usr/bin/env python3
"""日本語のリズムと LLM 定型句を数える。標準ライブラリのみ。

textlint が拾えない「AI 臭」を数値で示す。判断と書き直しは呼び出し側（Claude）が行う。
usage: rhythm.py <file> [--json]
"""
import json
import re
import statistics
import sys

# 冒頭・末尾・水増し・ぼかし。見つけたら削るか言い切る。
BOILERPLATE = [
    r"^(はい|もちろん|承知(いた)?しました|かしこまりました|了解(です|しました))[、。！!]",
    r"以下の(通り|とおり)です",
    r"について(解説|説明|紹介)(します|していきます)",
    r"見ていきましょう",
    r"いかがでし(ょう|た)か",
    r"(ご確認|ご検討|ご参考)(ください|いただければ幸いです)",
    r"お勧めします|おすすめします",
    r"ご注意ください",
    r"まとめると|結論から(言う|いう)と|このように",
    r"と(言える|いえる)でしょう",
    r"ではないでしょうか",
    r"と(思われ|考えられ)(ます|る)",
    r"かもしれません",
    r"ことが(重要|大切|必要|求められ)(です|だ|ます)",
    r"(非常に|極めて|大変|様々な|さまざまな|多角的|不可欠|革命的|劇的|飛躍的)",
    r"することができ(ます|る|ません|ない)",
    r"を(実施|実行|遂行)(し|する)",
    r"(ソリューション|インサイト|アプローチ|ロバスト|シナジー|レバレッジ|コミット(?!メッセージ))",
    r"(あなた|私たち|我々)(は|が|の)",
    r"(させていただき|させて頂き)",
]

SENT_END = re.compile(r"(?<=[。！？!?])\s*|\n+")
CODE_BLOCK = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`]*`|\[[^\]]*\]\([^)]*\)|https?://\S+")
HEADING_OR_LIST = re.compile(r"^\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|\|)")
VERBAL_END = re.compile(r"(ます|です|でした|ました|ません|ない|た|だ|る|い|う|く|ぶ|ぬ|む|す|つ|ぐ|ある|いる|よう|ください|か)[」）)]?[。！？!?]?$")


def sentences(text):
    text = CODE_BLOCK.sub("", text)
    out = []
    for line in text.splitlines():
        if HEADING_OR_LIST.match(line):
            continue
        line = INLINE.sub("X", line).strip()
        for s in SENT_END.split(line):
            s = s.strip()
            if len(s) >= 4 and re.search(r"[ぁ-んァ-ン一-龥]", s):
                out.append(s)
    return out


def ending(s):
    s = re.sub(r"[」）)。！？!?\s]+$", "", s)
    for e in ("でした", "ました", "ません", "ます", "です", "である", "だろう", "ない", "た", "だ", "る"):
        if s.endswith(e):
            return e
    return "体言" if not VERBAL_END.search(s) else "他"


def analyze(text):
    ss = sentences(text)
    lens = [len(s) for s in ss]
    ends = [ending(s) for s in ss]
    r = {
        "sentences": len(ss),
        "mean_len": round(statistics.mean(lens), 1) if lens else 0,
        "len_cv": round(statistics.pstdev(lens) / statistics.mean(lens), 2) if len(lens) > 1 and statistics.mean(lens) else 0,
        "long_sentences": [s for s in ss if len(s) > 80],
        "same_ending_x3": [],
        "taigen_rate": round(ends.count("体言") / len(ends), 2) if ends else 0,
        "no_x3": [s for s in ss if re.search(r"の[^の、。]{1,10}の[^の、。]{1,10}の", s)],
        "toiu": sum(s.count("という") for s in ss),
        "ga_comma": [s for s in ss if s.count("が、") >= 1 and not re.search(r"(しかし|だが|ものの)", s)],
        "ten_over3": [s for s in ss if s.count("、") > 3],
        "boilerplate": [],
        "polite_form": {"ですます": sum(e in ("ます", "です", "でした", "ました", "ません") for e in ends),
                        "である": sum(e in ("である", "だ", "た", "る", "ない", "だろう") for e in ends)},
    }
    for i in range(len(ends) - 2):
        if ends[i] == ends[i + 1] == ends[i + 2] and ends[i] not in ("他",):
            r["same_ending_x3"].append("／".join(ss[i:i + 3]))
    for pat in BOILERPLATE:
        for s in ss:
            m = re.search(pat, s)
            if m:
                r["boilerplate"].append((m.group(0), s))
    return r


def report(r):
    def show(label, items, limit=5):
        if items:
            print(f"- {label}: {len(items)}件")
            for it in items[:limit]:
                print(f"    ・{it if isinstance(it, str) else it[0] + ' ← ' + it[1]}"[:140])

    print(f"- 文数 {r['sentences']}、平均 {r['mean_len']} 字、文長の変動係数 {r['len_cv']}"
          + ("（0.35 未満: 長さが均一で機械的。短文と長文を混ぜる）" if r["sentences"] > 4 and r["len_cv"] < 0.35 else ""))
    pf = r["polite_form"]
    if pf["ですます"] and pf["である"]:
        print(f"- 文体混在: ですます {pf['ですます']} / である {pf['である']}（どちらかに統一。箇条書き内の常体は可）")
    show("80 字超の文（分割候補）", r["long_sentences"])
    show("同じ文末が 3 連続", r["same_ending_x3"], 3)
    if r["taigen_rate"] > 0.2:
        print(f"- 体言止め率 {r['taigen_rate']}（0.2 超: ぶっきらぼう。文末形を戻す）")
    show("「の」が 3 連続", r["no_x3"])
    if r["toiu"] >= 3:
        print(f"- 「という」{r['toiu']} 回（削って通じるなら削る）")
    show("逆接でない「〜が、」の疑い", r["ga_comma"])
    show("読点が 4 つ以上", r["ten_over3"])
    show("定型句・水増し・ぼかし", r["boilerplate"], 12)
    if not any([r["long_sentences"], r["same_ending_x3"], r["no_x3"], r["ga_comma"], r["ten_over3"], r["boilerplate"]]) \
            and r["taigen_rate"] <= 0.2 and r["toiu"] < 3:
        print("- 指摘なし")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    text = open(sys.argv[1], encoding="utf-8").read()
    res = analyze(text)
    if "--json" in sys.argv:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        report(res)
