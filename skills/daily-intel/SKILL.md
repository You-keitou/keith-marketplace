---
name: daily-intel
license: MIT
description: "Daily automated intel collection: scan AI-company blogs (OpenAI, DeepMind, Google Research, AWS, Cloudflare, DeepSeek, Moonshot…), engineering blogs and arXiv via RSS, then package the best items into actionable learning notes (summary, why-it-matters, one hands-on exercise each). Also generates a self-contained quiz HTML for any article and deploys it to Cloudflare Pages, and scans Japanese freelance gig sites (オシジョブ, クラウドワークス, ランサーズ, Findy Freelance…) for 生成AI × 週10時間 × リモート side-work. Use when the user says 情報収集, daily digest, 今日のAIニュース, intel, quizを作って, 副業案件を探して, or schedules a recurring run via claude -p / codex."
metadata:
  author: "keith <youkeitou327@gmail.com>"
  version: "0.1.0"
  tags: "rss, arxiv, digest, quiz, cloudflare-pages, freelance, automation"
---

# daily-intel

3つのサブコマンド（args で切り替え）: **digest**（既定）/ **quiz** / **gigs**。
設計原則: 決定論的な収集は `scripts/fetch.py`（stdlibのみ・LLM不使用、SSL証明書に certifi があったら使う）、要約・選定・クイズ生成だけ LLM がやる。収集が失敗しても raw digest は残る。arXiv は週末に配信が止まるので土日の0件は正常。

## digest（既定）

### 1. 収集（決定論的）

```bash
python3 <skill dir>/scripts/fetch.py <skill dir>/references/feeds.txt \
  --days 2 --max 15 --out /tmp/daily-intel
```

- 出力: `/tmp/daily-intel/intel-raw-YYYY-MM-DD.md`（新着のみ、既読は `~/.daily-intel/seen.json` で除外済み）
- 末尾に `## FAILED feeds` があれば、そのソースは直近24hを WebSearch で補完する
  （特に Anthropic / Mistral / Meta AI は RSS が無い: `Anthropic news <今日の日付>` 等で検索）

### 2. 選定と package 化（LLM）

raw digest を読み、**5〜10件**を選ぶ。基準:  hands-on できるか（触れるAPI/コード/論文か）、
読者のスタック（Python, FastAPI, RAG, Agent, LLM harness）に効くか。マーケティング記事は落とす。

出力先: keito-vault 内で実行中なら `<vault>/logs/intel/YYYY-MM-DD.md`、それ以外はカレント。
OKF frontmatter を付ける:

```yaml
---
type: reference
title: "Daily intel YYYY-MM-DD"
description: "1行サマリ（この日のハイライト）"
tags: [ai-news, digest]
area: logs
status: current
source: generated
regenerable: true
provenance: "intel-raw-YYYY-MM-DD.md"
created: YYYY-MM-DD
updated: YYYY-MM-DD
intended_use: "日々の技術キャッチアップ + 実践候補の発掘"
---
```

各エントリの形式（これ以外は書かない）:

```markdown
## <記事タイトル>
- **要約**: 3行以内
- **なぜ重要**: 1行（自分のスタック・副業とどう繋がるか）
- **やってみる**: 今日30分でできる具体的な一歩（コード片/試すAPI/再現手順）
- source: <URL>（1文で「なぜ繋がるか」を書いてからリンクする）
```

論文（arXiv）の場合は「やってみる」を *abstract の核心アイデアを最小コードで再現する手順* か
*HF/Colab の実装を探す* にする。読めない量の実践リストを作らないこと。

### 3. クイズへの接続

ハイライト1件につき、末尾に一行提案: `→ /daily-intel quiz <URL> で理解度クイズを生成できます`。
ユーザーが定期実行（`claude -p "/daily-intel digest"` / codex 同等）で回す場合は提案行だけ書いて停止する。

## quiz

対象記事の理解度を測る自己完結HTMLを生成し、Cloudflare Pages に deploy する。

1. **記事取得**: URL を WebFetch で読む。失敗したら digest の要約をベースにする（旨を明記）。
2. **クイズ生成**: 単一HTMLファイル（外部JS/CSS禁止、すべてインライン）。要件:
   - 5〜8問: 概念理解2、コード穴埋め2、適用シナリオ（この技術を自分のRAG/Agentにどう使うか）2 を目安に
   - 各問に正答と**解説**（なぜそれが正解か、原文のどの主張に基づくか）
   - スコア表示、リトライ可能、`prefers-color-scheme` の dark/light 対応、スマホ幅で読める
   - `<title>` は「記事名 Quiz」
3. **deploy**:

```bash
mkdir -p /tmp/daily-intel-quiz && cp quiz.html /tmp/daily-intel-quiz/<slug>-quiz.html
npx wrangler pages deploy /tmp/daily-intel-quiz --project-name daily-intel-quiz
```

   初回だけ `wrangler pages project create daily-intel-quiz` が必要。
   deploy 済みディレクトリを毎回まるごと上げる（Pages はディレクトリ単位デプロイ、過去クイズのURLも維持される）。
4. 返すもの: 記事ごとの直接URL（`.../slug-quiz.html`）。digest に追記してよい。

## gigs

日本の副業サイトから「生成AI × 週10時間前後 × リモート」の新着案件を探す。

1. `<skill dir>/references/gig-sites.md` を読む（巡回先リストと検索クエリテンプレ）。
2. リストの上から順に WebSearch / WebFetch で探索する。検索URLがブロックされていたら
   サイト名 + キーワードの WebSearch にフォールバック。全部は回らない — **優先度高の5サイトで打ち止め**。
3. フィルタ: 生成AI/LLM/RAG/エージェント系、週2〜3日以下 or 週15h以下、リモート可、時給換算2,000円以上。
4. 既報除外: `~/.daily-intel/gigs-seen.json`（`{"<案件URL>": "<ISO日付>"}` 形式）を読み、
   新規のみ報告して追記する（fetch.py の `load_state`/`save_state` と同じ形式。スクリプトは書かずインラインpythonで可）。
5. 報告形式（digest と同じ frontmatter 規則で `logs/intel/gigs-YYYY-MM-DD.md` にも保存）:

```markdown
## <案件名> — <サイト名>
- 条件: 週Xh / リモート可否 / 単価（時給換算を書く）
- 匹配理由: 自分のスタック（Python/FastAPI/RAG/Agent）のどこが刺さるか1行
- 次の一手: 応募文のたたき台1行 or プロフィールで強調すべき点
- URL: <案件URL>
```

該当ゼロなら「本日は条件に合う新規案件なし」と1行だけ。無理に水増ししない。

## 運用メモ

- 定期実行はエージェント側の cron / launchd / `claude -p "/daily-intel digest"` に任せる（skill自体は常駐しない）。
- seen.json が増えすぎたら 90日で自動 prune される（fetch.py 内）。
- feeds の追加・削除は `references/feeds.txt` を編集するだけ。404 が出たらその場で直す。
- fetch.py の自己検証: `python3 scripts/fetch.py --selftest`
