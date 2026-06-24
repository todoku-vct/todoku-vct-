import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_EMAIL_EXCLUDE = {"example.com", "test.com", "domain.com", "gmail.com", "yahoo.co.jp",
                  "hotmail.com", "sentry.io", "w3.org", "schema.org"}


def extract_emails_from_pages(pages: list[dict]) -> list[str]:
    """スクレイピング結果のページ群からメールアドレスを抽出して返す。"""
    found: set[str] = set()
    for page in pages:
        text = page.get("text", "") + " " + page.get("url", "")
        for email in _EMAIL_RE.findall(text):
            domain = email.split("@")[-1].lower()
            if domain not in _EMAIL_EXCLUDE:
                found.add(email.lower())
    return sorted(found)

HEADERS_PC = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
HEADERS_SP = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
SKIP_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".mp4", ".mp3", ".svg", ".ico", ".webp"}
MAX_TEXT_PER_PAGE = 2000
# requestsでテキストがこの文字数未満ならPlaywrightにフォールバック
_JS_FALLBACK_THRESHOLD = 80


def _same_domain(base: str, url: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def _clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()
    # <nav> と <footer> のみ除去。<header> は除去しない
    # （コンテンツを <header> に配置するサイトがあるため）
    for tag in soup(["nav", "footer"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.find(id="content") or soup.find("body")
    if not main:
        return ""
    lines = [l.strip() for l in main.get_text(separator="\n").split("\n") if l.strip()]
    text = "\n".join(lines)
    # テキストが少なすぎる場合、body 全体を再試行（header 残しで）
    if len(text) < 50:
        body = soup.find("body")
        if body:
            lines = [l.strip() for l in body.get_text(separator="\n").split("\n") if l.strip()]
            text = "\n".join(lines)
    return text[:MAX_TEXT_PER_PAGE]


def _get_headers(device: str) -> dict:
    return HEADERS_SP if device == "mobile" else HEADERS_PC


def _fetch_sitemap_urls(start_url: str) -> list[str]:
    """sitemap.xml からURL一覧を取得する。取得できなければ空リスト。"""
    parsed = urlparse(start_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap/sitemap.xml",
    ]
    for sitemap_url in candidates:
        try:
            resp = requests.get(sitemap_url, headers=HEADERS_PC, timeout=8)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.content, "xml")
            urls = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
            # サイトマップインデックスの場合、子サイトマップを再帰取得
            if soup.find("sitemapindex"):
                child_urls = []
                for child_loc in urls[:5]:
                    try:
                        cr = requests.get(child_loc, headers=HEADERS_PC, timeout=8)
                        cs = BeautifulSoup(cr.content, "xml")
                        child_urls += [l.get_text(strip=True) for l in cs.find_all("loc")]
                    except Exception:
                        pass
                urls = child_urls
            # 同ドメインのHTMLページのみ
            urls = [
                u for u in urls
                if _same_domain(start_url, u)
                and not any(urlparse(u).path.lower().endswith(ext) for ext in SKIP_EXTS)
            ]
            if urls:
                return urls
        except Exception:
            continue
    return []


def _fetch_page_playwright(url: str, device: str = "pc") -> tuple[dict | None, str]:
    """Playwright（ヘッドレスChromium）でJS描画後のテキストを取得する。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "Playwright未インストール"
    try:
        with sync_playwright() as p:
            is_mobile = device == "mobile"
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=HEADERS_SP["User-Agent"] if is_mobile else HEADERS_PC["User-Agent"],
                is_mobile=is_mobile,
                viewport={"width": 390, "height": 844} if is_mobile else {"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.goto(url, timeout=20000, wait_until="networkidle")
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url
        raw_links = [a.get("href", "") for a in soup.find_all("a", href=True) if a.get("href")]
        text = _clean_text(soup)
        if not text:
            return None, "Playwright後もテキストが取得できなかった（認証・エラーページの可能性）"
        return {"url": url, "title": title, "text": text, "raw_links": raw_links, "_via_playwright": True}, ""
    except Exception as e:
        return None, f"Playwright取得エラー ({type(e).__name__})"


def _fetch_page(url: str, device: str = "pc") -> tuple[dict | None, str]:
    """1ページを取得してテキストを返す。(result, failure_reason) のタプル。
    result には "raw_links" キーでクリーニング前の全 href リストを含む。
    """
    clean_url = urlparse(url)._replace(fragment="", query="").geturl()
    if any(urlparse(clean_url).path.lower().endswith(ext) for ext in SKIP_EXTS):
        return None, "対象外ファイル形式"
    try:
        resp = requests.get(clean_url, headers=_get_headers(device), timeout=12, allow_redirects=True)
    except Exception as e:
        return None, f"接続エラー ({type(e).__name__})"
    if resp.status_code == 403:
        return None, "アクセス拒否 (403)"
    if resp.status_code == 404:
        return None, "ページが存在しない (404)"
    if resp.status_code != 200:
        return None, f"HTTPエラー ({resp.status_code})"
    if "text/html" not in resp.headers.get("content-type", ""):
        return None, "HTML以外のコンテンツ"
    soup = BeautifulSoup(resp.content, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else clean_url
    # ★ クリーニング前に全リンクを収集（_clean_text が nav/footer を in-place 削除するため）
    raw_links = [a.get("href", "") for a in soup.find_all("a", href=True) if a.get("href")]
    text = _clean_text(soup)

    # テキストが閾値以下 → JSレンダリングの可能性。Playwrightでフォールバック
    if len(text) < _JS_FALLBACK_THRESHOLD:
        pw_result, pw_reason = _fetch_page_playwright(clean_url, device=device)
        if pw_result:
            return pw_result, ""
        # Playwrightも失敗した場合は元のテキストが少しでもあれば使用、なければ失敗
        if not text:
            return None, f"JS描画ページ（Playwright: {pw_reason}）"

    return {"url": clean_url, "title": title, "text": text, "raw_links": raw_links}, ""


def scrape_site(start_url: str, max_pages: int = 10, progress_cb=None, device: str = "pc") -> list[dict]:
    """
    1. sitemap.xml があればそこからURL収集
    2. なければリンクをたどるクロール
    Returns: [{"url": str, "title": str, "text": str}, ...]
    失敗URLは各dictの "failed" キーに {"url": ..., "reason": ...} のリストとして付与する
    （最後の要素として {"_failed": [...]} を返す）
    """
    pages: list[dict] = []
    visited: set[str] = set()
    failed: list[dict] = []

    # --- サイトマップ優先 ---
    sitemap_urls = _fetch_sitemap_urls(start_url)
    if sitemap_urls:
        # トップページを先頭に
        clean_start = urlparse(start_url)._replace(fragment="", query="").geturl()
        if clean_start not in sitemap_urls:
            sitemap_urls.insert(0, start_url)
        queue = sitemap_urls
        use_sitemap = True
    else:
        queue = [start_url]
        use_sitemap = False

    i = 0
    while i < len(queue) and len(pages) < max_pages:
        url = queue[i]
        i += 1
        clean_url = urlparse(url)._replace(fragment="", query="").geturl()
        if clean_url in visited:
            continue
        visited.add(clean_url)

        result, reason = _fetch_page(clean_url, device=device)
        if result:
            raw_links = result.pop("raw_links", [])
            pages.append(result)
            if progress_cb:
                progress_cb(len(pages), min(max_pages, len(queue)), result["title"])

            # サイトマップがなかった場合のみリンク収集
            # ★ nav/footer 削除前に収集した raw_links を使う
            if not use_sitemap:
                for href_raw in raw_links:
                    href = urljoin(clean_url, href_raw)
                    href_clean = urlparse(href)._replace(fragment="", query="").geturl()
                    if (
                        _same_domain(start_url, href_clean)
                        and href_clean not in visited
                        and not any(urlparse(href_clean).path.lower().endswith(ext) for ext in SKIP_EXTS)
                    ):
                        queue.append(href_clean)
        else:
            if reason not in ("対象外ファイル形式",):
                failed.append({"url": clean_url, "reason": reason})

        time.sleep(0.3)

    # 失敗URLをメタデータとして末尾に付与
    if failed:
        pages.append({"_failed": failed})

    return pages
