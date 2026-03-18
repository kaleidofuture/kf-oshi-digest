"""KF-OshiDigest — Aggregate RSS feeds into a daily digest for your favorites."""

import streamlit as st

st.set_page_config(
    page_title="KF-OshiDigest",
    page_icon="\U00002B50",
    layout="wide",
)

from components.header import render_header
from components.footer import render_footer
from components.i18n import t

import json
import feedparser
import trafilatura
from datetime import datetime, date
import time
import re
import io
from streamlit_js_eval import streamlit_js_eval

STORAGE_KEY = "kf-oshi-digest-data"

# --- Header ---
render_header()

# --- Session state ---
if "feed_urls" not in st.session_state:
    st.session_state.feed_urls = []
if "articles" not in st.session_state:
    st.session_state.articles = []
if "keywords" not in st.session_state:
    st.session_state.keywords = []
if "expenses" not in st.session_state:
    st.session_state.expenses = []

# --- Load from localStorage ---
if "data_loaded" not in st.session_state:
    stored = streamlit_js_eval(js_expressions=f'localStorage.getItem("{STORAGE_KEY}")')
    if stored and stored != "null":
        try:
            loaded = json.loads(stored)
            if "feed_urls" in loaded:
                st.session_state.feed_urls = loaded["feed_urls"]
            if "keywords" in loaded:
                st.session_state.keywords = loaded["keywords"]
            if "expenses" in loaded:
                st.session_state.expenses = loaded["expenses"]
        except Exception:
            pass
    st.session_state.data_loaded = True


def save_to_local_storage():
    """Save feed_urls, keywords, and expenses to browser localStorage."""
    data = {
        "feed_urls": st.session_state.feed_urls,
        "keywords": st.session_state.keywords,
        "expenses": st.session_state.expenses,
    }
    data_json = json.dumps(data, ensure_ascii=False)
    streamlit_js_eval(js_expressions=f'localStorage.setItem("{STORAGE_KEY}", {json.dumps(data_json)})')

# --- Genre preset feeds ---
GENRE_PRESETS = {
    "idol": {
        "label_key": "genre_idol",
        "feeds": [
            ("Natalie Music", "https://natalie.mu/music/feed/news"),
            ("ORICON NEWS Music", "https://www.oricon.co.jp/news/rss/music/"),
            ("Billboard Japan", "https://www.billboard-japan.com/rss/news"),
        ],
    },
    "anime": {
        "label_key": "genre_anime",
        "feeds": [
            ("Anime News Network", "https://www.animenewsnetwork.com/all/rss.xml"),
            ("Natalie Comic", "https://natalie.mu/comic/feed/news"),
            ("Anime! Anime!", "https://animeanime.jp/rss/index.rdf"),
        ],
    },
    "seiyuu": {
        "label_key": "genre_seiyuu",
        "feeds": [
            ("Seiyuu Grand Prix Web", "https://seigura.com/feed/"),
            ("animate Times Voice Actor", "https://www.animatetimes.com/tag/seiyuu/rss.php"),
            ("Cho Animedia", "https://cho-animedia.jp/feed/"),
        ],
    },
    "vtuber": {
        "label_key": "genre_vtuber",
        "feeds": [
            ("MoguLive", "https://www.moguravr.com/feed/"),
            ("Kai-You VTuber", "https://kai-you.net/rss/category/vtuber"),
            ("Panora VR", "https://panora.tokyo/feed"),
        ],
    },
    "game": {
        "label_key": "genre_game",
        "feeds": [
            ("4Gamer.net", "https://www.4gamer.net/rss/index.xml"),
            ("Famitsu", "https://www.famitsu.com/feed/"),
            ("Game Watch", "https://game.watch.impress.co.jp/data/rss/1.0/gmw/feed.rdf"),
        ],
    },
}


def parse_feed(url: str) -> list[dict]:
    """Parse an RSS/Atom feed and return article entries."""
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            return []

        articles = []
        feed_title = feed.feed.get("title", url)

        for entry in feed.entries[:20]:  # Limit per feed
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])

            articles.append({
                "feed_title": feed_title,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": entry.get("summary", ""),
            })

        return articles
    except Exception:
        return []


def extract_body(url: str) -> str | None:
    """Extract article body text using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            return text
    except Exception:
        pass
    return None


def matches_keywords(article: dict, keywords: list[str]) -> bool:
    """Check if an article title or summary matches any keyword."""
    if not keywords:
        return False
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    return any(kw.lower() in text for kw in keywords)


# =============================================================
# TAB LAYOUT
# =============================================================
tab_feed, tab_keywords, tab_expense = st.tabs([
    t("tab_feeds"),
    t("tab_keywords"),
    t("tab_expense"),
])

# =============================================================
# TAB 1: FEEDS & ARTICLES
# =============================================================
with tab_feed:
    st.subheader(t("input_title"))
    st.caption(t("input_help"))

    # --- Genre presets ---
    with st.expander(t("genre_preset_title"), expanded=False):
        st.markdown(t("genre_preset_help"))
        cols = st.columns(len(GENRE_PRESETS))
        for idx, (genre_key, preset) in enumerate(GENRE_PRESETS.items()):
            with cols[idx]:
                if st.button(t(preset["label_key"]), key=f"genre_{genre_key}", use_container_width=True):
                    added = 0
                    for name, url in preset["feeds"]:
                        if url not in st.session_state.feed_urls:
                            st.session_state.feed_urls.append(url)
                            added += 1
                    if added > 0:
                        save_to_local_storage()
                        st.rerun()

    # Preset examples
    with st.expander(t("preset_title")):
        st.markdown(t("preset_examples"))

    new_url = st.text_input(t("url_label"), placeholder="https://example.com/feed.xml")

    col_add, col_clear = st.columns([1, 1])
    with col_add:
        if st.button(t("add_button"), type="primary") and new_url.strip():
            if new_url.strip() not in st.session_state.feed_urls:
                st.session_state.feed_urls.append(new_url.strip())
                save_to_local_storage()
                st.rerun()
    with col_clear:
        if st.button(t("clear_feeds")):
            st.session_state.feed_urls = []
            st.session_state.articles = []
            save_to_local_storage()
            st.rerun()

    # Show registered feeds
    if st.session_state.feed_urls:
        st.markdown(f"**{t('registered_feeds')}** ({len(st.session_state.feed_urls)})")
        for i, url in enumerate(st.session_state.feed_urls):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.caption(url)
            with col2:
                if st.button("\U0001F5D1", key=f"del_feed_{i}"):
                    st.session_state.feed_urls.pop(i)
                    save_to_local_storage()
                    st.rerun()

        # --- Fetch button ---
        if st.button(t("fetch_button"), type="primary"):
            all_articles = []
            progress = st.progress(0, text=t("fetching"))

            for i, url in enumerate(st.session_state.feed_urls):
                progress.progress(
                    (i + 1) / len(st.session_state.feed_urls),
                    text=t("fetching_feed").format(num=i + 1, total=len(st.session_state.feed_urls)),
                )
                articles = parse_feed(url)
                all_articles.extend(articles)

            # Sort by date (newest first), None dates go to end
            all_articles.sort(
                key=lambda a: a["published"] or datetime.min,
                reverse=True,
            )

            st.session_state.articles = all_articles
            progress.empty()
            st.rerun()

    # --- Display articles ---
    if st.session_state.articles:
        articles = st.session_state.articles
        keywords = st.session_state.keywords

        # Separate keyword-matched and others
        matched = [a for a in articles if matches_keywords(a, keywords)]
        unmatched = [a for a in articles if not matches_keywords(a, keywords)]
        sorted_articles = matched + unmatched

        # --- Summary card ---
        st.markdown("---")
        summary_cols = st.columns(3)
        with summary_cols[0]:
            st.metric(t("summary_total"), len(articles))
        with summary_cols[1]:
            st.metric(t("summary_keyword_match"), len(matched))
        with summary_cols[2]:
            feed_count = len(set(a["feed_title"] for a in articles))
            st.metric(t("summary_sources"), feed_count)
        st.markdown("---")

        # Option to extract full text
        extract_full = st.checkbox(t("extract_full_text"))

        for i, article in enumerate(sorted_articles):
            is_matched = matches_keywords(article, keywords)
            date_str = article["published"].strftime("%Y-%m-%d %H:%M") if article["published"] else "-"
            badge = " \U0001F31F" if is_matched else ""
            label = f"[{date_str}] {article['title']}  ({article['feed_title']}){badge}"

            with st.expander(label):
                if is_matched:
                    matched_kws = [kw for kw in keywords if kw.lower() in (article.get("title", "") + " " + article.get("summary", "")).lower()]
                    st.info(t("keyword_matched_label").format(keywords=", ".join(matched_kws)))

                if article["link"]:
                    st.markdown(f"[{t('open_link')}]({article['link']})")

                # Show summary
                if article["summary"]:
                    clean_summary = re.sub(r"<[^>]+>", "", article["summary"])
                    if len(clean_summary) > 500:
                        clean_summary = clean_summary[:500] + "..."
                    st.markdown(clean_summary)

                # Extract full text on demand
                if extract_full and article["link"]:
                    if st.button(t("extract_button"), key=f"extract_{i}"):
                        with st.spinner(t("extracting")):
                            body = extract_body(article["link"])
                            if body:
                                st.text_area(
                                    t("full_text"),
                                    body[:3000],
                                    height=200,
                                    key=f"body_{i}",
                                )
                            else:
                                st.warning(t("extract_failed"))

        # --- Export ---
        st.markdown("---")
        export_lines = []
        for article in sorted_articles:
            date_str = article["published"].strftime("%Y-%m-%d %H:%M") if article["published"] else "-"
            kw_tag = " [KEYWORD MATCH]" if matches_keywords(article, keywords) else ""
            export_lines.append(f"[{date_str}] {article['title']}{kw_tag}")
            export_lines.append(f"  Source: {article['feed_title']}")
            export_lines.append(f"  URL: {article['link']}")
            if article["summary"]:
                clean = re.sub(r"<[^>]+>", "", article["summary"])
                if len(clean) > 300:
                    clean = clean[:300] + "..."
                export_lines.append(f"  {clean}")
            export_lines.append("")

        export_text = "\n".join(export_lines)

        st.download_button(
            label=t("export_button"),
            data=export_text.encode("utf-8"),
            file_name="oshi_digest.txt",
            mime="text/plain",
        )

    elif st.session_state.feed_urls:
        st.info(t("ready_to_fetch"))
    else:
        st.info(t("no_feeds"))

# =============================================================
# TAB 2: KEYWORD FILTER
# =============================================================
with tab_keywords:
    st.subheader(t("keyword_title"))
    st.caption(t("keyword_help"))

    new_kw = st.text_input(t("keyword_input_label"), placeholder=t("keyword_placeholder"))
    if st.button(t("keyword_add_button"), type="primary") and new_kw.strip():
        if new_kw.strip() not in st.session_state.keywords:
            st.session_state.keywords.append(new_kw.strip())
            save_to_local_storage()
            st.rerun()

    if st.session_state.keywords:
        st.markdown(f"**{t('keyword_registered')}**")
        for i, kw in enumerate(st.session_state.keywords):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"`{kw}`")
            with col2:
                if st.button("\U0001F5D1", key=f"del_kw_{i}"):
                    st.session_state.keywords.pop(i)
                    save_to_local_storage()
                    st.rerun()
    else:
        st.info(t("keyword_none"))

# =============================================================
# TAB 3: EXPENSE TRACKER
# =============================================================
with tab_expense:
    st.subheader(t("expense_title"))
    st.caption(t("expense_help"))

    with st.form("expense_form", clear_on_submit=True):
        exp_cols = st.columns([3, 2, 2])
        with exp_cols[0]:
            item_name = st.text_input(t("expense_item"), placeholder=t("expense_item_placeholder"))
        with exp_cols[1]:
            amount = st.number_input(t("expense_amount"), min_value=0, step=100, value=0)
        with exp_cols[2]:
            expense_date = st.date_input(t("expense_date"), value=date.today())
        submitted = st.form_submit_button(t("expense_add_button"), type="primary")
        if submitted and item_name.strip() and amount > 0:
            st.session_state.expenses.append({
                "item": item_name.strip(),
                "amount": amount,
                "date": expense_date.isoformat(),
            })
            save_to_local_storage()
            st.rerun()

    if st.session_state.expenses:
        # Monthly totals for bar chart
        monthly = {}
        for exp in st.session_state.expenses:
            month_key = exp["date"][:7]  # YYYY-MM
            monthly[month_key] = monthly.get(month_key, 0) + exp["amount"]

        # Current month total
        current_month = date.today().strftime("%Y-%m")
        current_total = monthly.get(current_month, 0)
        st.metric(t("expense_monthly_total").format(month=current_month), f"\U000000A5{current_total:,}")

        # Bar chart
        if monthly:
            import pandas as pd
            chart_data = pd.DataFrame(
                list(monthly.items()),
                columns=[t("expense_chart_month"), t("expense_chart_amount")],
            )
            chart_data = chart_data.sort_values(t("expense_chart_month"))
            st.bar_chart(chart_data, x=t("expense_chart_month"), y=t("expense_chart_amount"))

        # Expense list
        st.markdown(f"**{t('expense_history')}**")
        for i, exp in enumerate(reversed(st.session_state.expenses)):
            real_idx = len(st.session_state.expenses) - 1 - i
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.text(exp["item"])
            with col2:
                st.text(f"\U000000A5{exp['amount']:,}")
            with col3:
                st.text(exp["date"])
            with col4:
                if st.button("\U0001F5D1", key=f"del_exp_{real_idx}"):
                    st.session_state.expenses.pop(real_idx)
                    save_to_local_storage()
                    st.rerun()

        # Clear all expenses
        if st.button(t("expense_clear_all")):
            st.session_state.expenses = []
            save_to_local_storage()
            st.rerun()
    else:
        st.info(t("expense_none"))

# --- Footer ---
render_footer(libraries=["feedparser", "trafilatura"], repo_name="kf-oshi-digest")
