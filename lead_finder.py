"""Google Places API (New) を使った、DM送付先リストアップ用のリード収集モジュール。"""
import time
from urllib.parse import urlparse

import requests

from web_scraper import _fetch_page, HEADERS_PC

_PLACES_SEARCHTEXT_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

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
    """Google Places API (New) の Text Search で店舗候補を検索する。
    Returns: [{"place_id": str, "name": str, "address": str}, ...]
    """
    api_key = api_key.strip()
    if not api_key.isascii():
        raise RuntimeError("APIキーに不正な文字（全角文字・改行等）が含まれています。Secretsの値を確認してください。")

    results = []
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,nextPageToken",
    }
    body = {"textQuery": query, "languageCode": "ja", "regionCode": "JP"}
    next_token = None

    while len(results) < max_results:
        if next_token:
            body = {"textQuery": query, "languageCode": "ja", "regionCode": "JP", "pageToken": next_token}
            time.sleep(2)  # pageToken はすぐには有効にならないため待機

        try:
            resp = requests.post(_PLACES_SEARCHTEXT_URL, json=body, headers=headers, timeout=15)
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Google Places API 接続エラー: {e}") from e

        if resp.status_code != 200:
            err = data.get("error", {})
            raise RuntimeError(f"Google Places API エラー: {err.get('status', resp.status_code)} / {err.get('message', '')}")

        for place in data.get("places", []):
            results.append({
                "place_id": place.get("id", ""),
                "name": place.get("displayName", {}).get("text", ""),
                "address": place.get("formattedAddress", ""),
            })
            if len(results) >= max_results:
                break

        next_token = data.get("nextPageToken")
        if not next_token:
            break

    return results[:max_results]


def get_place_details(place_id: str, api_key: str) -> dict:
    """Place Details API (New) で電話番号・ホームページURLを取得する。"""
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "internationalPhoneNumber,nationalPhoneNumber,websiteUri",
    }
    try:
        resp = requests.get(_PLACES_DETAILS_URL.format(place_id=place_id), headers=headers, timeout=15)
        data = resp.json()
    except Exception:
        return {}
    if resp.status_code != 200:
        return {}
    return {
        "phone": data.get("nationalPhoneNumber", "") or data.get("internationalPhoneNumber", ""),
        "website": data.get("websiteUri", ""),
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
