"""EDINET(金融庁)の企業コードリストを使った、上場企業向けリード収集モジュール。
会社四季報の掲載対象はほぼ全上場企業のため、EDINETの無料公開データで代替する。
"""
import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

_CODELIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
_CACHE_PATH = Path(__file__).parent / "data" / "edinet_codelist_cache.csv"
_CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 1週間（EDINETコードリストは月1回更新程度）

_COLUMN_MAP = {
    "ＥＤＩＮＥＴコード": "edinet_code",
    "提出者種別": "submitter_type",
    "上場区分": "listed_status",
    "提出者名": "company_name",
    "所在地": "address",
    "提出者業種": "industry",
    "証券コード": "securities_code",
}

EDINET_INDUSTRIES = [
    "水産・農林業", "鉱業", "建設業", "食料品", "繊維製品", "パルプ・紙", "化学",
    "医薬品", "石油・石炭製品", "ゴム製品", "ガラス・土石製品", "鉄鋼", "非鉄金属",
    "金属製品", "機械", "電気機器", "輸送用機器", "精密機器", "その他製品",
    "電気・ガス業", "陸運業", "海運業", "空運業", "倉庫・運輸関連", "情報・通信業",
    "卸売業", "小売業", "銀行業", "証券、商品先物取引業", "保険業", "その他金融業",
    "不動産業", "サービス業",
]


def _download_codelist() -> pd.DataFrame:
    resp = requests.get(_CODELIST_URL, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        csv_name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(csv_name) as f:
            df = pd.read_csv(f, encoding="cp932", skiprows=1)
    df = df.rename(columns=_COLUMN_MAP)
    keep_cols = list(_COLUMN_MAP.values())
    df = df[[c for c in keep_cols if c in df.columns]]
    _CACHE_PATH.parent.mkdir(exist_ok=True)
    df.to_csv(_CACHE_PATH, index=False, encoding="utf-8-sig")
    return df


def load_codelist(force_refresh: bool = False) -> pd.DataFrame:
    """EDINETコードリストをキャッシュから読み込む。キャッシュがない/古い場合はダウンロードする。"""
    if not force_refresh and _CACHE_PATH.exists():
        age = time.time() - _CACHE_PATH.stat().st_mtime
        if age < _CACHE_MAX_AGE_SECONDS:
            return pd.read_csv(_CACHE_PATH, encoding="utf-8-sig")
    try:
        return _download_codelist()
    except Exception as e:
        if _CACHE_PATH.exists():
            return pd.read_csv(_CACHE_PATH, encoding="utf-8-sig")
        raise RuntimeError(f"EDINETコードリストの取得に失敗しました: {e}") from e


def search_edinet_companies(
    industry: str,
    region_keyword: str = "",
    max_results: int = 20,
    listed_only: bool = True,
) -> list[dict]:
    """業種・地域（所在地の部分一致）で上場企業を検索する。
    Returns: [{"企業名": str, "業種": str, "所在地": str, "証券コード": str, "EDINETコード": str}, ...]
    """
    df = load_codelist()

    if listed_only and "listed_status" in df.columns:
        df = df[df["listed_status"] == "上場"]

    if industry:
        df = df[df["industry"] == industry]

    if region_keyword.strip():
        df = df[df["address"].astype(str).str.contains(region_keyword.strip(), na=False)]

    df = df.head(max_results)

    leads = []
    for _, row in df.iterrows():
        sec_code = row.get("securities_code", "")
        sec_code_str = "" if pd.isna(sec_code) else str(int(sec_code)) if isinstance(sec_code, float) else str(sec_code)
        leads.append({
            "企業名": row.get("company_name", ""),
            "業種": row.get("industry", ""),
            "所在地": row.get("address", ""),
            "証券コード": sec_code_str,
            "EDINETコード": row.get("edinet_code", ""),
        })
    return leads
