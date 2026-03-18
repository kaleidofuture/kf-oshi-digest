# KF-OshiDigest

> 推しの最新情報をRSSで一括チェックしてダイジェスト化する。

## The Problem

推し活の情報が多すぎて追いきれない。複数サイトを毎日巡回するのが大変。

## How It Works

1. RSS/AtomフィードのURLを複数登録
2. feedparserで最新記事を一括取得
3. 日付順にダイジェスト表示
4. trafilaturaで本文抽出も可能
5. テキストファイルでエクスポート

## Libraries Used

- **feedparser** — RSS/Atomフィードの解析
- **trafilatura** — Webページからの本文抽出

## Development

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Hosted on [Hugging Face Spaces](https://huggingface.co/spaces/mitoi/kf-oshi-digest).

---

Part of the [KaleidoFuture AI-Driven Development Research](https://kaleidofuture.com) — proving that everyday problems can be solved with existing libraries, no AI model required.
