# 副業巡回先リスト（生成AI × 週10時間前後 × リモート）

条件フィルタ: 生成AI/LLM/RAG/エージェント 関連、週2〜3日以下 or 週15h以下、リモート可。
URLは変わりうるので、ブロックされていたらサイト内検索 or WebSearch にフォールバックする。

## 優先度高（週10h級の案件が実在する）

| サイト | 探索方法 |
|---|---|
| オシジョブ <https://oshi-job.com/fukugyo/worker/projects> | 「週10時間から」が看板。AIエージェント/業務自動化カテゴリを直接見る |
| クラウドワークス | WebSearch: `site:crowdworks.jp 生成AI` / `site:crowdworks.jp LLM 副業`。公開案件ページは WebFetch できることが多い |
| ランサーズ | WebSearch: `site:lancers.jp 生成AI` / `site:lancers.jp RAG`。検索URLはブロックされがちなので検索エンジン経由 |
| Findy Freelance <https://freelance.findy-code.io/> | 「週2〜3日稼働」「生成AI」で絞り込み。フルリモート比率84% |
| 日本ビジネスアート <https://www.jbakk.co.jp/recruit-freelance-jobs.html> | AIワークフローエンジニアの週10h〜案件あり。募集ページを直接 WebFetch |

## 優先度中

| サイト | 探索方法 |
|---|---|
| Workship <https://go.workship.com/> | 副業前提のマッチング。WebSearch: `site:go.workship.com 生成AI` |
| freeanken <https://freeanken.com/> | フリーランス案件毎日更新。生成AI活用・業務改革カテゴリ |
| harowaka <https://www.harowaka.com/> | 在宅可案件を職種別に毎日更新 |
| Wantedly | WebSearch: `site:wantedly.com 生成AI 副業` |
| Indeed | WebSearch: `site:jp.indeed.com 生成AI リモート 週2` |
| numoment | 生成AI受託(週10〜20h、時給5,000円〜)。WebSearch: `numoment 生成AI 副業` |

## 探索クエリのテンプレ

WebSearch にそのまま渡す:

- `生成AI 副業 週10時間 リモート 業務委託 2026`
- `LLM RAG エンジニア 副業 週2日 フルリモート`
- `AIエージェント開発 業務委託 副業 土日`
- `site:<ドメイン> 生成AI`（サイト別ドリルダウン）

## メモ

- 単価目安: 週10h × 時給5,000円 ≒ 月20万円。時給2,000円以下の案件は報告から除外してよい。
- 応募前提スキル: Python/FastAPI、RAG(マルチテナント、検索評価)、Agent tool calling、本番運用。
- 新規案件のみ報告する（seen台帳は `~/.daily-intel/gigs-seen.json`、fetch.pyのstateと同じ形式で扱う）。
