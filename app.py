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

import feedparser
import trafilatura
from datetime import datetime
import time
import io

# --- Header ---
render_header()

# --- Session state ---
if "feed_urls" not in st.session_state:
    st.session_state.feed_urls = []
if "articles" not in st.session_state:
    st.session_state.articles = []


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


# --- Feed URL input ---
st.subheader(t("input_title"))
st.caption(t("input_help"))

# Preset examples
with st.expander(t("preset_title")):
    st.markdown(t("preset_examples"))

new_url = st.text_input(t("url_label"), placeholder="https://example.com/feed.xml")

col_add, col_clear = st.columns([1, 1])
with col_add:
    if st.button(t("add_button"), type="primary") and new_url.strip():
        if new_url.strip() not in st.session_state.feed_urls:
            st.session_state.feed_urls.append(new_url.strip())
            st.rerun()
with col_clear:
    if st.button(t("clear_feeds")):
        st.session_state.feed_urls = []
        st.session_state.articles = []
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
    st.success(t("found_articles").format(count=len(articles)))

    # Option to extract full text
    extract_full = st.checkbox(t("extract_full_text"))

    for i, article in enumerate(articles):
        date_str = article["published"].strftime("%Y-%m-%d %H:%M") if article["published"] else "-"
        with st.expander(f"[{date_str}] {article['title']}  ({article['feed_title']})"):
            if article["link"]:
                st.markdown(f"[{t('open_link')}]({article['link']})")

            # Show summary
            if article["summary"]:
                # Strip HTML tags from summary
                import re
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
    for article in articles:
        date_str = article["published"].strftime("%Y-%m-%d %H:%M") if article["published"] else "-"
        export_lines.append(f"[{date_str}] {article['title']}")
        export_lines.append(f"  Source: {article['feed_title']}")
        export_lines.append(f"  URL: {article['link']}")
        if article["summary"]:
            import re
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

# --- Footer ---
render_footer(libraries=["feedparser", "trafilatura"])
