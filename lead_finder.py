"""Google Places API を使った、DM送付先リストアップ用のリード収集モジュール。"""
import time
from urllib.parse import urlparse

import requests

from web_scraper import _fetch_page, HEADERS_PC

_PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

_SNS_DOMAINS = {
    "instagram.com": "Instagram",
    "twitter.com": "X (Twitter)",
    "x.com": "X (Twitter)",
    "facebook.com": "Facebook",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "line.me": "LINE",
    "tiktok.com": "TikTok",
}


def search_places(query: str, api_key: str, max_results: int = 20) -> list[dict]:
    """Google Places API (Text Search) で店舗候補を検索する。
    Returns: [{"place_id": str, "name": str, "address": str}, ...]
    """
    results = []
    params = {"query": query, "key": api_key, "language": "ja", "region": "jp"}
    next_token = None

    while len(results) < max_results:
        if next_token:
            params = {"pagetoken": next_token, "key": api_key}
            time.sleep(2)  # next_page_token はすぐには有効にならないため待機

        try:
            resp = requests.get(_PLACES_TEXTSEARCH_URL, params=params, timeout=15)
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Google Places API 接続エラー: {e}") from e

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            raise RuntimeError(f"Google Places API エラー: {status} / {data.get('error_message', '')}")

        for place in data.get("results", []):
            results.append({
                "place_id": place.get("place_id", ""),
                "name": place.get("name", ""),
                "address": place.get("formatted_address", ""),
            })
            if len(results) >= max_results:
                break

        next_token = data.get("next_page_token")
        if not next_token:
            break

    return results[:max_results]


def get_place_details(place_id: str, api_key: str) -> dict:
    """Place Details API で電話番号・ホームページURLを取得する。"""
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,website,formatted_address",
        "key": api_key,
        "language": "ja",
    }
    try:
        resp = requests.get(_PLACES_DETAILS_URL, params=params, timeout=15)
        data = resp.json()
    except Exception:
        return {}
    if data.get("status") != "OK":
        return {}
    r = data.get("result", {})
    return {
        "phone": r.get("formatted_phone_number", ""),
        "website": r.get("website", ""),
    }


def extract_sns_links(raw_links: list[str]) -> dict:
    """ページ内のリンクからSNSアカウントを検出する。Returns: {"Instagram": url, ...}"""
    found = {}
    for href in raw_links:
        try:
            domain = urlparse(href).netloc.lower().replace("www.", "")
        except Exception:
            continue
        for sns_domain, label in _SNS_DOMAINS.items():
            if domain == sns_domain or domain.endswith("." + sns_domain):
                if label not in found:
                    found[label] = href
    return found


def enrich_with_website_info(website_url: str, device: str = "pc") -> dict:
    """ホームページを1ページ取得し、SNSリンクとページ本文（代表者名抽出用）を返す。"""
    if not website_url:
        return {"sns": {}, "page_text": ""}
    result, _reason = _fetch_page(website_url, device=device)
    if not result:
        return {"sns": {}, "page_text": ""}
    raw_links = result.get("raw_links", [])
    sns = extract_sns_links(raw_links)
    return {"sns": sns, "page_text": result.get("text", "")}


def build_lead_list(
    profession: str,
    region: str,
    api_key: str,
    max_results: int = 20,
    progress_cb=None,
    extract_representative_name_fn=None,
) -> list[dict]:
    """業種・地域からDM送付先候補リストを作成する。
    extract_representative_name_fn: (page_text, profession) -> str を渡すと代表者名も抽出する（AI呼び出し・任意）。
    """
    query = f"{profession} {region}"
    places = search_places(query, api_key, max_results=max_results)

    leads = []
    total = len(places)
    for i, place in enumerate(places):
        details = get_place_details(place["place_id"], api_key)
        website = details.get("website", "")

        sns_str = ""
        representative_name = ""
        if website:
            info = enrich_with_website_info(website)
            sns = info["sns"]
            sns_str = " / ".join(f"{k}: {v}" for k, v in sns.items())
            if extract_representative_name_fn and info["page_text"]:
                try:
                    representative_name = extract_representative_name_fn(info["page_text"], profession)
                except Exception:
                    representative_name = ""

        leads.append({
            "店名": place["name"],
            "住所": place["address"],
            "電話番号": details.get("phone", ""),
            "ホームページURL": website,
            "代表者名（AI推定）": representative_name,
            "SNS": sns_str,
        })

        if progress_cb:
            progress_cb(i + 1, total, place["name"])

    return leads
