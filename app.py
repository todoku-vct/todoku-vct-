# v2026-06-26c
import json
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from persona_generator import (
    generate_personas,
    format_persona_label, PROFESSION_GROUPS
)
from llm_client import get_persona_reaction, generate_report, generate_ab_report, generate_improved_copy, analyze_site
from web_scraper import scrape_site, extract_emails_from_pages
from email_sender import send_report as send_email_report, is_configured as email_is_configured
from db import save_result, load_history, load_detail, load_client_names, delete_record
from pdf_generator import generate_pdf, generate_ab_pdf, generate_site_pdf, generate_summary_pdf, generate_script_pdf
from llm_client import generate_consultation_script, generate_ai_personas, compare_device_reports, extract_representative_name
from lead_finder import build_lead_list
from edinet_finder import search_edinet_companies, EDINET_INDUSTRIES

st.set_page_config(page_title="トドク VCT", page_icon="🏛", layout="wide")

# ===== 日本語専用化（翻訳ポップアップ完全防止） =====
st.markdown("""
<script>
(function(){
  function enforceJa(){
    var h = document.documentElement;
    h.lang = 'ja';
    h.setAttribute('translate','no');
    h.classList.add('notranslate');
    if(document.body){ document.body.classList.add('notranslate'); }
    if(document.head && !document.querySelector('meta[name="google"][content="notranslate"]')){
      var m = document.createElement('meta');
      m.name='google'; m.content='notranslate';
      document.head.insertBefore(m, document.head.firstChild);
    }
  }
  enforceJa();
  // StreamlitがReact初期化でlang="en"に戻すのを監視して即座に上書き
  new MutationObserver(function(ml){
    ml.forEach(function(m){ if(m.attributeName==='lang'||m.attributeName==='translate'){ enforceJa(); } });
  }).observe(document.documentElement,{attributes:true});
  // 念のため数回実行
  [200,800,2000,5000].forEach(function(t){ setTimeout(enforceJa,t); });
})();
</script>
""", unsafe_allow_html=True)

# ===== カスタムCSS =====
st.markdown("""
<style>
/* ── 全体背景（温かみのあるオフホワイト） ─── */
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="stMain"] { background: #f5f4f0 !important; }
header[data-testid="stHeader"] { background: #f5f4f0 !important; box-shadow: none !important; }
.block-container { padding-top: 0 !important; padding-bottom: 2rem !important; max-width: 1200px !important; }

/* ── 英語UI非表示 ─────────────────────────── */
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDeployButton"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }

/* ── 基本テキスト（body継承で全要素に暗色、div個別ルールなし）── */
body, p, label { color: #1c1917; }
h1,h2,h3 { color: #1c1917 !important; }
h4 { color: #44403c !important; }
[data-testid="stCaptionContainer"] p { color: #78716c !important; }

/* ── ヘッダー・フォトカード（念のためクラスでも白を強制） ── */
.vct-header { color: white !important; }
.vct-header * { color: white !important; }
.vct-header .txt-gold { color: #d4af37 !important; }
.vct-header .txt-muted { color: rgba(255,255,255,0.52) !important; }
.vct-header .txt-sub { color: rgba(255,255,255,0.78) !important; }
.photo-card { color: white !important; }
.photo-card * { color: white !important; }
.photo-card .card-tag { color: rgba(255,255,255,0.58) !important; }

/* ── タブ（ゴールドアンダーライン） ──────── */
[data-testid="stTabs"] { border-bottom: 1px solid #d6d3d1 !important; }
[data-testid="stTabs"] button {
    font-weight: 600 !important;
    color: #a8a29e !important;
    font-size: 0.88rem !important;
    padding: 10px 22px !important;
    border-radius: 0 !important;
    letter-spacing: 0.02em !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #1c1917 !important;
    border-bottom: 2.5px solid #b8860b !important;
    background: transparent !important;
    font-weight: 700 !important;
}
[data-testid="stTabs"] button:hover { color: #1c1917 !important; background: #ede8e3 !important; }

/* ── 入力フォーム ────────────────────────── */
textarea, input[type="text"], input[type="number"] {
    background: #ffffff !important;
    color: #1c1917 !important;
    border: 1px solid #d6d3d1 !important;
    border-radius: 8px !important;
    font-size: 0.92rem !important;
}
textarea:focus, input:focus {
    border-color: #44403c !important;
    box-shadow: 0 0 0 3px rgba(68,64,60,0.1) !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    color: #1c1917 !important;
    border: 1px solid #d6d3d1 !important;
    border-radius: 8px !important;
}

/* ── スライダー（Streamlitバージョン差異でDOM構造が変わっても効くよう、
   直下子(>)ではなく子孫セレクタ＋新旧testid両対応にする） ── */
[data-testid="stSlider"] [data-baseweb="slider"] > div > div:last-child {
    background: linear-gradient(90deg,#1a1a3e,#44403c) !important;
    background-image: linear-gradient(90deg,#1a1a3e,#44403c) !important;
}
[data-testid="stSlider"] [role="slider"] {
    background-color: #1a1a3e !important;
    border-color: #1a1a3e !important;
    box-shadow: 0 0 0 3px rgba(26,26,62,0.18) !important;
}
[data-testid="stSlider"] [data-testid="stThumbValue"],
[data-testid="stSlider"] [data-testid="stSliderThumbValue"] { color: #1a1a3e !important; font-weight: 700 !important; }
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"],
[data-testid="stSlider"] [data-testid="stSliderTickBarMin"],
[data-testid="stSlider"] [data-testid="stSliderTickBarMax"] { color: #78716c !important; }

/* ── ラジオ・チェック・トグル ──────────── */
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label { color: #44403c !important; font-size: 0.9rem !important; }
[data-testid="stToggle"] label { color: #1c1917 !important; font-weight: 600 !important; }

/* ── ボタン（プレミアム ネイビー）
   ★ ボタン内のp/span/divも白にしないと body, p { color:#1c1917 } で上書きされる ── */
[data-testid="stButton"] button[kind="primary"],
[data-testid="stBaseButton-primary"],
button[kind="primary"] {
    background: #1a1a3e !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.8rem !important;
    letter-spacing: 0.04em !important;
    box-shadow: 0 3px 12px rgba(26,26,62,0.22) !important;
    transition: all 0.18s !important;
}
/* ボタン内の子要素（p, span, div）も白字を強制 */
[data-testid="stButton"] button[kind="primary"] p,
[data-testid="stButton"] button[kind="primary"] span,
[data-testid="stButton"] button[kind="primary"] div,
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span,
[data-testid="stBaseButton-primary"] div,
button[kind="primary"] p,
button[kind="primary"] span,
button[kind="primary"] div { color: #ffffff !important; }

[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: #2d1b6e !important;
    box-shadow: 0 6px 20px rgba(26,26,62,0.32) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stDownloadButton"] button {
    background: #292524 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    border: none !important;
    font-size: 0.9rem !important;
}
[data-testid="stDownloadButton"] button p,
[data-testid="stDownloadButton"] button span,
[data-testid="stDownloadButton"] button div { color: #ffffff !important; }
[data-testid="stButton"] button[kind="secondary"] {
    background: white !important;
    color: #1a1a3e !important;
    border: 1.5px solid #1a1a3e !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

/* ── メトリクスカード（ゴールド左ボーダー） ─ */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border-radius: 10px !important;
    padding: 1rem 1.2rem !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06) !important;
    border-left: 3px solid #b8860b !important;
}
[data-testid="stMetricLabel"] > div {
    color: #78716c !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] > div { color: #1c1917 !important; font-size: 1.7rem !important; font-weight: 800 !important; }

/* ── アラート ────────────────────────────── */
[data-testid="stAlert"] { border-radius: 8px !important; }

/* ── エクスパンダー ──────────────────────── */
details {
    background: #ffffff !important;
    border-radius: 10px !important;
    border: 1px solid #e7e5e4 !important;
    box-shadow: 0 1px 5px rgba(0,0,0,0.04) !important;
    margin-bottom: 8px !important;
}
details summary { font-weight: 700 !important; color: #1c1917 !important; font-size: 0.9rem !important; }
details[open] summary { color: #1a1a3e !important; }

/* ── プログレスバー ──────────────────────── */
[data-testid="stProgress"] > div { background: #e7e5e4 !important; border-radius: 99px !important; height: 5px !important; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg,#1a1a3e,#b8860b) !important; border-radius: 99px !important; }

/* ── divider ────────────────────────────── */
hr { border-color: #e7e5e4 !important; margin: 0.8rem 0 !important; }

/* ── マーケティングインサイトカード（テキスト切れ防止）── */
/* Streamlit の stMarkdown コンテナが overflow:hidden を持つため、
   CSS クラスで明示的に visible にしてカードを自動伸長させる    */
[data-testid="stMarkdown"],
[data-testid="stMarkdown"] > div {
    overflow: visible !important;
    height: auto !important;
}
.mi-card-grid {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 0.7rem !important;
    overflow: visible !important;
    height: auto !important;
}
.mi-card-item {
    background: white !important;
    border-radius: 8px !important;
    padding: 0.8rem 1rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07) !important;
    overflow: visible !important;
    height: auto !important;
    min-height: 0 !important;
}
.mi-card-label {
    font-size: 0.72rem !important;
    color: #6b7280 !important;
    font-weight: 700 !important;
    margin-bottom: 2px !important;
}
.mi-card-sub {
    font-size: 0.65rem !important;
    color: #9ca3af !important;
    margin-bottom: 6px !important;
}
.mi-card-text {
    color: #1a1a3e !important;
    font-size: 0.88rem !important;
    word-break: break-all !important;
    overflow-wrap: anywhere !important;
    white-space: normal !important;
    line-height: 1.6 !important;
    overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)

# ===== ヘッダー（写真が見えるサイドグラデーション + フォトカード） =====
st.markdown("""
<div style="height:3px;background:linear-gradient(90deg,#6b4e0a,#d4af37,#f8e388,#d4af37,#6b4e0a);"></div>

<!-- ★ 左テキスト(確実に暗背景) + 右写真(装飾) の2カラム構成 -->
<div class="vct-header" style="
  display:flex;overflow:hidden;
  border-radius:0 0 16px 16px;
  margin-bottom:1rem;
  box-shadow:0 8px 36px rgba(0,0,0,0.24);
">
  <!-- 左：純粋な暗グラデーション（テキストエリア） -->
  <div style="
    flex:1;min-width:0;
    background:linear-gradient(145deg,#08082a 0%,#161660 60%,#0c0c38 100%);
    padding:1.8rem 2rem 1.6rem;
  ">
    <div class="txt-gold" style="font-size:0.6rem;letter-spacing:0.32em;text-transform:uppercase;margin-bottom:10px;font-weight:700;">LIFE DESIGN LAB</div>
    <b style="font-size:1.75rem;display:block;letter-spacing:-0.4px;line-height:1.15;">
      トドク VCT
      <small class="txt-muted" style="font-size:0.88rem;font-weight:400;margin-left:10px;letter-spacing:0;">シンセティックデータ × マーケティング診断</small>
    </b>
    <small class="txt-sub" style="font-size:0.8rem;display:block;margin-top:12px;padding-top:11px;border-top:1px solid rgba(255,255,255,0.15);">
      AIシンセティックデータで顧客反応を予測・サイトをブランド力視点で診断
    </small>
  </div>
  <!-- 右：オフィス写真（テキストなし、装飾のみ） -->
  <div style="
    width:38%;flex-shrink:0;
    background-image:url('https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=600&q=75');
    background-size:cover;background-position:center 30%;
  "></div>
</div>

<!-- フォトカード3枚 -->
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">
  <div class="photo-card" style="
    border-radius:12px;overflow:hidden;min-height:148px;
    background-image:linear-gradient(175deg,rgba(4,4,14,0.05) 0%,rgba(4,4,14,0.74) 100%),
      url('https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?auto=format&fit=crop&w=600&q=80');
    background-size:cover;background-position:center;
    display:flex;align-items:flex-end;
    box-shadow:0 4px 16px rgba(0,0,0,0.14);
  ">
    <div style="padding:16px 18px 14px;">
      <div class="card-tag" style="font-size:0.6rem;letter-spacing:0.22em;text-transform:uppercase;margin-bottom:6px;font-weight:600;">01 — テスト</div>
      <div style="font-size:0.9rem;font-weight:700;">公開前テスト</div>
      <div style="font-size:0.75rem;margin-top:4px;opacity:0.82;">AI仮想顧客がリアルに反応・評価</div>
    </div>
  </div>
  <div class="photo-card" style="
    border-radius:12px;overflow:hidden;min-height:148px;
    background-image:linear-gradient(175deg,rgba(4,4,14,0.05) 0%,rgba(4,4,14,0.74) 100%),
      url('https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80');
    background-size:cover;background-position:center;
    display:flex;align-items:flex-end;
    box-shadow:0 4px 16px rgba(0,0,0,0.14);
  ">
    <div style="padding:16px 18px 14px;">
      <div class="card-tag" style="font-size:0.6rem;letter-spacing:0.22em;text-transform:uppercase;margin-bottom:6px;font-weight:600;">02 — 分析</div>
      <div style="font-size:0.9rem;font-weight:700;">DRMスコア分析</div>
      <div style="font-size:0.75rem;margin-top:4px;opacity:0.82;">DRMマーケティング評価</div>
    </div>
  </div>
  <div class="photo-card" style="
    border-radius:12px;overflow:hidden;min-height:148px;
    background-image:linear-gradient(175deg,rgba(4,4,14,0.05) 0%,rgba(4,4,14,0.74) 100%),
      url('https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=600&q=80');
    background-size:cover;background-position:center;
    display:flex;align-items:flex-end;
    box-shadow:0 4px 16px rgba(0,0,0,0.14);
  ">
    <div style="padding:16px 18px 14px;">
      <div class="card-tag" style="font-size:0.6rem;letter-spacing:0.22em;text-transform:uppercase;margin-bottom:6px;font-weight:600;">03 — 改善</div>
      <div style="font-size:0.9rem;font-weight:700;">改善版コピー生成</div>
      <div style="font-size:0.75rem;margin-top:4px;opacity:0.82;">問題点をAIが自動修正・再生成</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ===== ヘルパー =====
def _mc(label, value, color, sub=""):
    sub_html = f'<div style="font-size:0.75rem;color:#6b7280;margin-top:3px;">{sub}</div>' if sub else ""
    return f"""<div style="background:white;border-radius:10px;padding:1rem 1.2rem;
        box-shadow:0 2px 8px rgba(0,0,0,0.08);border-top:3px solid {color};height:90px;">
        <div style="color:#6b7280;font-size:0.78rem;margin-bottom:5px;">{label}</div>
        <div style="color:#1a1a3e;font-size:1.75rem;font-weight:800;line-height:1.1;">{value}</div>
        {sub_html}</div>"""

def _canva_text(report: dict, report_type: str, profession: str) -> str:
    """Canvaテンプレートへ貼り付けしやすい形式でレポートをテキスト化する。"""
    now = datetime.now().strftime("%Y年%m月%d日")
    sep = "━" * 30
    L = []
    L += [sep, f"VCT 分析レポート  ｜  {profession}", f"作成日: {now}", sep, ""]

    if report_type == "LP":
        L += [f"■ 推定問い合わせ率　{report.get('inquiry_rate', '-')}", ""]
    elif report_type == "SNS":
        L += [
            f"■ スクロール停止率　{report.get('stop_rate', '-')}",
            f"■ いいね率　　　　　{report.get('like_rate', '-')}",
            f"■ プロフィール訪問率　{report.get('profile_visit_rate', '-')}", "",
        ]
    elif report_type == "SITE":
        L += [
            f"■ 推定問い合わせ率（回遊後）　{report.get('inquiry_rate', '-')}",
            "", "■ 第一印象", report.get("overall_impression", ""), "",
        ]

    L += ["■ 総評", report.get("summary", ""), ""]

    L.append("◆ 強み")
    for i, s in enumerate(report.get("strengths", []), 1):
        L += [f"  {i}. {s.get('point', '')}", f"     {s.get('reason', '')}"]
    L.append("")

    L.append("◆ 改善点")
    for i, w in enumerate(report.get("weaknesses", []), 1):
        L += [f"  {i}. {w.get('point', '')}", f"     {w.get('reason', '')}"]
        if w.get("suggestion"):
            L.append(f"     → {w['suggestion']}")
    L.append("")

    L += ["◆ 今すぐやるべき最重要改善", report.get("priority_action", ""), ""]

    if report_type == "SITE":
        for ni in report.get("navigation_issues", []):
            L += [f"◆ 導線問題　[{ni.get('page', '')}]",
                  f"  問題: {ni.get('issue', '')}", f"  改善: {ni.get('suggestion', '')}", ""]
        miss = report.get("missing_pages", [])
        if miss:
            L.append("◆ あると効果的なページ")
            L += [f"  ・{m}" for m in miss]
            L.append("")

    mi = report.get("marketing_insights", {})
    if mi:
        L += [f"◆ マーケティング評価（DRM）　{mi.get('drm_score', '-')}", ""]
        for label, key, sub in [
            ("ファーストビュー", "first_view", "最初に目に入る画面・第一印象"),
            ("信頼構築", "trust_building", "実績・口コミ・資格で安心感を作る施策"),
            ("差別化", "differentiation", "競合との違いの見せ方・独自ポジション"),
            ("CTA 行動喚起", "cta_strength", "問い合わせや申込みを促すボタン・文章"),
            ("地味だけどヤバい改善ポイント", "hidden_gem", ""),
        ]:
            L += [f"  [{label}]{' ─ ' + sub if sub else ''}", f"  {mi.get(key, '')}", ""]

    L += [sep, "Powered by トドク VCT  ｜  LIFE DESIGN LAB", sep]
    return "\n".join(L)


def _canva_copy_ui(report: dict, report_type: str, profession: str):
    """Canva貼り付けテキストをコードブロック＋コピーボタンで表示する。"""
    text = _canva_text(report, report_type, profession)
    uid = report_type.lower()
    st.markdown(
        f"""
<div style="background:#fdf8f0;border:1.5px solid #d4af37;border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
    <span style="font-size:1.1rem;">📋</span>
    <span style="font-weight:700;color:#92400e;font-size:0.9rem;">Canva テンプレート貼り付け用テキスト</span>
    <button onclick="navigator.clipboard.writeText(document.getElementById('canva-txt-{uid}').innerText).then(()=>{{this.innerText='コピー済み ✓';setTimeout(()=>this.innerText='コピー',2000)}})"
      style="margin-left:auto;background:#d4af37;color:white;border:none;border-radius:6px;
             padding:4px 14px;font-size:0.82rem;font-weight:700;cursor:pointer;">
      コピー
    </button>
  </div>
  <pre id="canva-txt-{uid}" style="background:#fff8e8;border-radius:6px;padding:0.8rem;font-size:0.78rem;
       line-height:1.7;white-space:pre-wrap;word-break:break-all;overflow-wrap:anywhere;
       color:#1a1a3e;margin:0;max-height:260px;overflow-y:auto;">{text}</pre>
</div>""",
        unsafe_allow_html=True,
    )


def _mi_html(mi, margin_top="0.7rem"):
    """マーケティングインサイト（DRMスコア＋4カード）の共通HTMLを生成する"""
    drm = mi.get("drm_score", "C")
    drm_color = {"A":"#16a34a","B":"#2563eb","C":"#d97706","D":"#dc2626"}.get(drm,"#6b7280")
    drm_desc = {
        "A": "集客・教育・販売がすべて機能している。このまま広告をかけると費用対効果が高い。",
        "B": "基本はできているが、1〜2か所の改善で大きく伸びる伸びしろがある状態。",
        "C": "構造に問題あり。改善なく広告をかけると費用を無駄にする可能性が高い。",
        "D": "根本から作り直しが必要。現状のまま運用しても成果は出にくい。",
    }.get(drm, "")
    return f"""
<div style="background:linear-gradient(135deg,#1a1a3e,#2d1b6e);border-radius:12px;padding:1.2rem 1.5rem;color:white;margin-top:{margin_top};margin-bottom:0.7rem;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
    <div style="background:{drm_color};border-radius:8px;padding:4px 14px;font-size:1.3rem;font-weight:900;">{drm}</div>
    <div>
      <div style="font-size:1rem;font-weight:700;">マーケティング総合評価</div>
      <div style="font-size:0.78rem;opacity:0.65;">DRM（ダイレクトレスポンスマーケティング）：集客→教育→販売の観点</div>
    </div>
  </div>
  <div style="background:rgba(255,255,255,0.1);border-radius:6px;padding:0.6rem 0.9rem;margin-bottom:10px;font-size:0.88rem;word-break:break-all;overflow-wrap:anywhere;line-height:1.6;">{drm_desc}</div>
  <div style="color:#a78bfa;font-size:0.78rem;font-weight:600;margin-bottom:4px;">地味だけどヤバい改善ポイント</div>
  <div style="font-size:0.92rem;font-weight:600;color:#ffffff;word-break:break-all;overflow-wrap:anywhere;white-space:normal;line-height:1.6;">{mi.get('hidden_gem','')}</div>
</div>
<div class="mi-card-grid">
  <div class="mi-card-item">
    <div class="mi-card-label">ファーストビュー</div>
    <div class="mi-card-sub">最初に目に入る画面・第一印象</div>
    <div class="mi-card-text">{mi.get('first_view','')}</div>
  </div>
  <div class="mi-card-item">
    <div class="mi-card-label">信頼構築</div>
    <div class="mi-card-sub">実績・口コミ・資格で安心感を作る施策</div>
    <div class="mi-card-text">{mi.get('trust_building','')}</div>
  </div>
  <div class="mi-card-item">
    <div class="mi-card-label">差別化</div>
    <div class="mi-card-sub">競合との違いの見せ方・独自ポジション</div>
    <div class="mi-card-text">{mi.get('differentiation','')}</div>
  </div>
  <div class="mi-card-item">
    <div class="mi-card-label">CTA 行動喚起</div>
    <div class="mi-card-sub">問い合わせや申込みを促すボタン・文章</div>
    <div class="mi-card-text">{mi.get('cta_strength','')}</div>
  </div>
</div>"""

# ===== タブ =====
tab_site, tab_leads, tab_test, tab_history = st.tabs(["🌐 サイト全体分析", "🎯 リストアップ", "テスト実行", "履歴・トラッキング"])


# =====================================================================
# TAB 1: テスト実行
# =====================================================================
with tab_test:
    st.divider()
    col1, col2 = st.columns([2, 1])

    with col2:
        # クライアント名・案件名
        existing_clients = load_client_names()
        st.markdown('<p style="font-size:0.85rem;font-weight:700;color:#6b46c1;margin-bottom:4px;">📁 クライアント名・案件名（履歴の絞り込みに使います）</p>', unsafe_allow_html=True)
        client_name = st.text_input(
            "クライアント名・案件名",
            placeholder="例：山川社長、Aクリニック",
            label_visibility="collapsed",
        )
        if existing_clients:
            st.caption("過去の案件: " + "　/　".join(existing_clients[:5]))

        st.divider()
        test_mode = st.radio(
            "テストタイプ",
            ["LP / ホームページ", "SNS投稿（X・Instagram）", "A/Bテスト（2案比較）"],
        )
        mode = "sns" if "SNS" in test_mode else "lp"
        ab_mode = "A/B" in test_mode

        st.divider()
        all_professions = [p for group in PROFESSION_GROUPS.values() for p in group]
        profession = st.selectbox("ジャンル", all_professions)
        custom_service = ""
        if profession == "カスタム（自由入力）":
            custom_service = st.text_input("サービス・業種名", placeholder="例：整体院、英会話スクール")

        persona_count = st.slider("仮想顧客の人数", min_value=3, max_value=10, value=5)

        # --- カスタムペルソナ設定 ---
        st.divider()
        use_custom_persona = st.toggle("カスタムペルソナ設定を使う", value=False)
        custom_settings = {}

        if use_custom_persona:
            st.caption("ターゲット顧客の情報を入力するとAIがリアルなペルソナを自動生成します")
            target_description = st.text_area(
                "ターゲット顧客の補足情報（任意）",
                placeholder="例：\n40〜60代の女性が中心\n美容に関心が高く、SNSでよく情報収集する\n価格より効果・安心感を重視する傾向がある",
                height=100,
            )

    with col1:
        if ab_mode:
            # 改善コピーからA/Bテストに遷移してきた場合は自動入力
            prefilled_a = st.session_state.pop("ab_text_a", "")
            prefilled_b = st.session_state.pop("ab_text_b", "")
            if st.session_state.pop("ab_prefilled", False) and prefilled_a and prefilled_b:
                st.info("改善版を自動入力しました。そのまま「▶ テストを開始する」を押してください。")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### バージョン A（元のテキスト）")
                text_a = st.text_area("現行 or 案A", height=260, placeholder="現在使っているLP・コピーを貼り付け", key="text_a", value=prefilled_a)
            with col_b:
                st.markdown("#### バージョン B（AI改善版）")
                text_b = st.text_area("改善案 or 案B", height=260, placeholder="比較したい新しいバージョンを貼り付け", key="text_b", value=prefilled_b)
            lp_text = None
        else:
            placeholder = (
                "例：\n【相続手続き、一人で抱え込んでいませんか？】\n\n親が亡くなった後の手続きって\nこんなに多いって知ってましたか？\n..."
                if mode == "sns"
                else "例：\n初回相談無料！浜松市の相続専門行政書士\n親が亡くなった後の手続き、全部お任せください。\n..."
            )
            label = "テスト対象のSNS投稿文" if mode == "sns" else "テスト対象のLP・コピー文章"
            lp_text = st.text_area(label, height=320, placeholder=placeholder)
            text_a = text_b = None

    run_btn = st.button("▶ テストを開始する", type="primary", use_container_width=True)

    if run_btn:
        if ab_mode:
            if not (text_a and text_a.strip()) or not (text_b and text_b.strip()):
                st.error("バージョンAとBの両方を入力してください。")
                st.stop()
        else:
            if not lp_text or not lp_text.strip():
                st.error("テキストを入力してください。")
                st.stop()
        if use_custom_persona and profession == "カスタム（自由入力）" and not custom_service:
            st.error("サービス・業種名を入力してください。")
            st.stop()

        display_profession = custom_service if (profession == "カスタム（自由入力）" and custom_service) else profession

        def make_personas():
            if use_custom_persona:
                raw = generate_ai_personas(display_profession, persona_count, target_description)
                for p in raw:
                    p.setdefault("profession", display_profession)
                return raw
            return generate_personas(profession, persona_count, custom_label=display_profession)

        # --- A/Bテストモード ---
        if ab_mode:
            personas = make_personas()
            reactions_a, reactions_b = [], []
            st.divider()
            progress = st.progress(0, text="バージョンAを評価中...")
            for i, persona in enumerate(personas):
                progress.progress((i + 1) / (persona_count * 2), text=f"バージョンA: ペルソナ {i+1}/{persona_count} 評価中...")
                reactions_a.append(get_persona_reaction(persona, text_a, mode=mode))
            for i, persona in enumerate(personas):
                progress.progress((persona_count + i + 1) / (persona_count * 2), text=f"バージョンB: ペルソナ {i+1}/{persona_count} 評価中...")
                reactions_b.append(get_persona_reaction(persona, text_b, mode=mode))
            progress.empty()

            st.subheader("同一ペルソナによる比較結果")
            rows = []
            for i, (p, ra, rb) in enumerate(zip(personas, reactions_a, reactions_b), 1):
                if mode == "sns":
                    lm = {"yes": "停止する", "maybe": "迷う", "no": "スルー"}
                    rows.append({"#": i, "ペルソナ": format_persona_label(p),
                        "A: 停止": lm.get(ra.get("will_stop_scrolling","?"), "?"),
                        "B: 停止": lm.get(rb.get("will_stop_scrolling","?"), "?"),
                        "A: 印象": ra.get("first_impression", ""), "B: 印象": rb.get("first_impression", "")})
                else:
                    lm = {"yes": "する", "maybe": "迷う", "no": "しない"}
                    rows.append({"#": i, "ペルソナ": format_persona_label(p),
                        "A: 問い合わせ": lm.get(ra.get("will_inquire","?"), "?"),
                        "B: 問い合わせ": lm.get(rb.get("will_inquire","?"), "?"),
                        "A: 理由": ra.get("reason",""), "B: 理由": rb.get("reason","")})
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("比較レポート")
            with st.spinner("AIが比較分析中..."):
                ab_report = generate_ab_report(personas, reactions_a, reactions_b, text_a, text_b, mode=mode)

            winner = ab_report.get("winner", "?")
            st.markdown(f"### 判定: **{winner} が勝利**" if winner in ["A","B"] else "### 判定: **引き分け**")
            st.info(ab_report.get("winner_reason", ""))
            mc1, mc2 = st.columns(2)
            mc1.metric("バージョン A スコア", f"{ab_report.get('score_a','?')} / 100")
            mc2.metric("バージョン B スコア", f"{ab_report.get('score_b','?')} / 100")
            st.write(f"**総評:** {ab_report.get('summary','')}")
            col_a2, col_b2 = st.columns(2)
            with col_a2:
                st.markdown("#### A の強み")
                for point in ab_report.get("a_strengths", []):
                    st.success(point)
            with col_b2:
                st.markdown("#### B の強み")
                for point in ab_report.get("b_strengths", []):
                    st.success(point)
            st.divider()
            st.markdown("#### 両方の良いとこどり最強バージョンの方向性")
            st.warning(ab_report.get("best_of_both",""))
            st.markdown("#### 今すぐやるべき改善")
            st.error(ab_report.get("priority_action",""))

            # DRM分析
            ab_mi = ab_report.get("marketing_insights")
            if ab_mi:
                st.divider()
                st.markdown(_mi_html(ab_mi), unsafe_allow_html=True)

            # A/Bテスト結果を履歴に保存
            winner_rate = f"勝者:{ab_report.get('winner','?')} A={ab_report.get('score_a','?')} B={ab_report.get('score_b','?')}"
            save_result(
                test_mode=test_mode, profession=display_profession,
                lp_text=f"[A] {text_a[:200]}\n[B] {text_b[:200]}",
                persona_count=persona_count,
                main_rate=winner_rate,
                report=ab_report,
                personas=personas,
                reactions=reactions_a,
                client_name=client_name,
            )

            # PDFダウンロード
            st.divider()
            try:
                pdf_bytes = generate_ab_pdf(
                    ab_report=ab_report, personas=personas,
                    reactions_a=reactions_a, reactions_b=reactions_b,
                    text_a=text_a, text_b=text_b,
                    mode=mode, profession=display_profession,
                    persona_count=persona_count,
                )
                fname = f"VCT_AB_{display_profession}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.download_button("PDF レポートをダウンロード", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.warning(f"PDF生成に失敗しました: {e}")

            st.stop()

        # --- 通常テスト ---
        personas = make_personas()
        reactions = []
        st.divider()
        st.subheader("SNS仮想ユーザーの反応" if mode == "sns" else "仮想顧客の反応")
        progress = st.progress(0, text="仮想顧客を生成中...")
        rows = []
        for i, persona in enumerate(personas):
            progress.progress((i + 1) / persona_count, text=f"ペルソナ {i+1}/{persona_count} を評価中...")
            reaction = get_persona_reaction(persona, lp_text, mode=mode)
            reactions.append(reaction)
            if mode == "sns":
                stop = reaction.get("will_stop_scrolling","no")
                rows.append({"#": i+1, "ペルソナ": format_persona_label(persona),
                    "停止": {"yes":"停止する","maybe":"迷う","no":"スルー"}.get(stop,stop),
                    "いいね": "する" if reaction.get("will_like")=="yes" else "しない",
                    "プロフ訪問": "する" if reaction.get("will_visit_profile")=="yes" else "しない",
                    "目に留まった": reaction.get("caught_attention",""), "引っかかった": reaction.get("turn_off",""),
                    "第一印象": reaction.get("first_impression","")})
            else:
                verdict = reaction.get("will_inquire","maybe")
                rows.append({"#": i+1, "ペルソナ": format_persona_label(persona),
                    "問題": persona["problem_detail"][:28]+"…",
                    "緊急度": persona["urgency"].split("（")[0],
                    "反応": {"yes":"問い合わせする","maybe":"迷っている","no":"しない"}.get(verdict,verdict),
                    "第一印象": reaction.get("first_impression",""),
                    "良かった点": reaction.get("caught_attention",""), "不安点": reaction.get("concern","")})
        progress.empty()
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("改善レポート")
        with st.spinner("レポートを生成中..."):
            report = generate_report(personas, reactions, lp_text, mode=mode)

        if mode == "sns":
            stop_yes   = sum(1 for r in reactions if r.get("will_stop_scrolling")=="yes")
            stop_maybe = sum(1 for r in reactions if r.get("will_stop_scrolling")=="maybe")
            like_count = sum(1 for r in reactions if r.get("will_like")=="yes")
            visit_count = sum(1 for r in reactions if r.get("will_visit_profile")=="yes")
            main_rate  = report.get("stop_rate", f"{int(stop_yes/persona_count*100)}%")
            cols = st.columns(5)
            cards = [
                ("スクロール停止率", main_rate, "#6b46c1"),
                ("停止する", f"{stop_yes}人", "#16a34a"),
                ("検討中", f"{stop_maybe}人", "#d97706"),
                ("いいね率", report.get("like_rate", f"{int(like_count/persona_count*100)}%"), "#2563eb"),
                ("プロフ訪問率", report.get("profile_visit_rate", f"{int(visit_count/persona_count*100)}%"), "#7c3aed"),
            ]
            for col, (label, val, color) in zip(cols, cards):
                col.markdown(_mc(label, val, color), unsafe_allow_html=True)
        else:
            yes_count   = sum(1 for r in reactions if r.get("will_inquire")=="yes")
            maybe_count = sum(1 for r in reactions if r.get("will_inquire")=="maybe")
            no_count    = sum(1 for r in reactions if r.get("will_inquire")=="no")
            main_rate   = report.get("inquiry_rate", f"{int(yes_count/persona_count*100)}%")
            cols = st.columns(4)
            cards = [
                ("推定問い合わせ率", main_rate, "#6b46c1"),
                ("問い合わせする", f"{yes_count}人", "#16a34a"),
                ("検討中", f"{maybe_count}人", "#d97706"),
                ("しない", f"{no_count}人", "#dc2626"),
            ]
            for col, (label, val, color) in zip(cols, cards):
                col.markdown(_mc(label, val, color), unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

        # 総評バナー
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#f0f4ff,#faf5ff);border-left:4px solid #6b46c1;
     border-radius:8px;padding:1rem 1.2rem;margin:0.5rem 0;">
  <div style="font-size:0.75rem;color:#6b46c1;font-weight:700;letter-spacing:0.5px;margin-bottom:4px;">総評</div>
  <div style="color:#1a1a3e;font-size:1rem;font-weight:600;">{report.get('summary','')}</div>
</div>""", unsafe_allow_html=True)

        # 強み・弱みを2カラム
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("#### 効果的だった点")
            for s in report.get("strengths", []):
                st.markdown(f"""
<div style="background:#f0fdf4;border-left:3px solid #16a34a;border-radius:6px;
     padding:0.7rem 1rem;margin-bottom:0.5rem;">
  <div style="color:#16a34a;font-weight:700;font-size:0.9rem;">✓ {s.get('point','')}</div>
  <div style="color:#374151;font-size:0.85rem;margin-top:3px;">{s.get('reason','')}</div>
</div>""", unsafe_allow_html=True)

        with col_r:
            st.markdown("#### 改善が必要な箇所")
            for w in report.get("weaknesses", []):
                st.markdown(f"""
<div style="background:#fef2f2;border-left:3px solid #dc2626;border-radius:6px;
     padding:0.7rem 1rem;margin-bottom:0.5rem;">
  <div style="color:#dc2626;font-weight:700;font-size:0.9rem;">✗ {w.get('point','')}</div>
  <div style="color:#374151;font-size:0.85rem;margin-top:3px;">{w.get('reason','')}</div>
  <div style="background:#dcfce7;border-radius:4px;padding:0.4rem 0.6rem;margin-top:6px;
       color:#16a34a;font-size:0.82rem;font-weight:600;">改善案: {w.get('suggestion','')}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        st.markdown(f"""
<div style="background:#fffbeb;border:2px solid #d97706;border-radius:8px;padding:1rem 1.2rem;">
  <div style="font-size:0.75rem;color:#d97706;font-weight:700;letter-spacing:0.5px;margin-bottom:4px;">今すぐやるべき最重要改善</div>
  <div style="color:#1a1a3e;font-size:1rem;font-weight:700;">{report.get('priority_action','')}</div>
</div>""", unsafe_allow_html=True)

        # マーケティング視点（DRM分析）
        mi = report.get("marketing_insights")
        if mi:
            st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
            st.markdown(_mi_html(mi), unsafe_allow_html=True)

        # 履歴に保存
        save_result(
            test_mode=test_mode, profession=display_profession,
            lp_text=lp_text, persona_count=persona_count,
            main_rate=main_rate, report=report,
            personas=personas, reactions=reactions,
            client_name=client_name,
        )
        st.success("テスト結果を履歴に保存しました")

        # session_state に結果を保存（ボタン押下後も維持するため）
        st.session_state["vct_result"] = {
            "report": report, "lp_text": lp_text, "reactions": reactions,
            "personas": personas, "main_rate": main_rate, "mode": mode,
            "display_profession": display_profession, "persona_count": persona_count,
            "client_name": client_name,
        }
        if "vct_improved" in st.session_state:
            del st.session_state["vct_improved"]

        # PDFダウンロード
        st.divider()
        try:
            pdf_bytes = generate_pdf(
                report=report, personas=personas, reactions=reactions,
                mode=mode, profession=display_profession,
                persona_count=persona_count, main_rate=main_rate,
                test_mode=test_mode,
            )
            fname = f"VCT_{display_profession}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button("PDF レポートをダウンロード", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.warning(f"PDF生成に失敗しました: {e}")

    # ── 商談用サマリー＆改善コピー（session_stateから表示・ボタン押下後も維持）──
    if "vct_result" in st.session_state:
        res = st.session_state["vct_result"]
        r = res["report"]
        _rate = res["main_rate"]
        _mode = res["mode"]
        _lp = res["lp_text"]

        st.divider()
        with st.expander("商談用サマリー（画面で見せる用）", expanded=False):
            rate_num = int(''.join(filter(str.isdigit, _rate)) or "0")
            rate_color = "#16a34a" if rate_num >= 50 else "#dc2626"
            rate_label = "スクロール停止率" if _mode == "sns" else "推定問い合わせ率"
            best = r.get("strengths", [{}])[0].get("point", "—") if r.get("strengths") else "—"
            worst = r.get("weaknesses", [{}])[0].get("point", "—") if r.get("weaknesses") else "—"
            action = r.get("priority_action", "—")
            client_tag = res["client_name"] or res["display_profession"]
            st.markdown(f"""
<div style="background:#1a1a3e;border-radius:12px;padding:1.5rem 2rem;color:white;">
  <div style="font-size:0.8rem;opacity:0.55;margin-bottom:8px;">{client_tag} ｜ {res['persona_count']}人の仮想顧客テスト</div>
  <div style="font-size:0.85rem;font-weight:600;opacity:0.75;margin-bottom:4px;">{rate_label}</div>
  <div style="font-size:3.2rem;font-weight:900;color:{rate_color};line-height:1.1;">{_rate}</div>
</div>
<div style="margin-top:0.8rem;display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;">
  <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:0.9rem;border-radius:8px;">
    <div style="font-size:0.72rem;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:5px;">最も効果的だった点</div>
    <div style="font-size:0.95rem;color:#1a1a3e;font-weight:700;">{best}</div>
  </div>
  <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:0.9rem;border-radius:8px;">
    <div style="font-size:0.72rem;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:5px;">最優先の改善ポイント</div>
    <div style="font-size:0.95rem;color:#1a1a3e;font-weight:700;">{worst}</div>
  </div>
</div>
<div style="margin-top:0.8rem;background:#fffbeb;border-left:4px solid #d97706;padding:0.9rem;border-radius:8px;">
  <div style="font-size:0.72rem;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:5px;">今すぐやるべきこと</div>
  <div style="font-size:0.95rem;color:#1a1a3e;font-weight:700;">{action}</div>
</div>
""", unsafe_allow_html=True)

        st.divider()
        st.markdown("#### AIが改善版を自動生成")
        st.caption("テスト結果の問題点をすべて解消した改善バージョンをAIが書き直します")
        if st.button("改善コピーを生成する", use_container_width=True, key="btn_improve"):
            with st.spinner("AIが改善版を執筆中...（15〜30秒）"):
                st.session_state["vct_improved"] = generate_improved_copy(_lp, r, mode=_mode)

        if "vct_improved" in st.session_state:
            col_orig, col_new = st.columns(2)
            with col_orig:
                st.markdown("**元のテキスト**")
                st.text_area("", value=_lp, height=300, disabled=True, key="orig_copy")
            with col_new:
                st.markdown("**AI改善版**")
                st.text_area("", value=st.session_state["vct_improved"], height=300, key="improved_copy")

            st.markdown("""
<div style="background:#f0f4ff;border-radius:10px;padding:1rem 1.2rem;margin-top:0.8rem;">
  <div style="font-weight:700;color:#1a1a3e;margin-bottom:4px;">次のステップ</div>
  <div style="font-size:0.88rem;color:#44403c;">このまま元のテキストと改善版をA/Bテストで比較できます</div>
</div>""", unsafe_allow_html=True)

            if st.button("▶ このままA/Bテストで比較する", type="primary", use_container_width=True, key="btn_ab_from_improved"):
                st.session_state["ab_text_a"] = _lp
                st.session_state["ab_text_b"] = st.session_state["vct_improved"]
                st.session_state["ab_prefilled"] = True
                st.rerun()


# =====================================================================
# TAB 2: サイト全体分析
# =====================================================================
with tab_site:
    st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a3e,#2d1b6e);border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1.2rem;color:white;">
  <b style="font-size:1.1rem;display:block;">🌐 サイト全体分析</b>
  <small style="font-size:0.82rem;margin-top:4px;display:block;opacity:0.75;">URLを入力するだけで、サイト内の複数ページを自動収集 → 仮想顧客が回遊した場合の問題点を発見します</small>
</div>
""", unsafe_allow_html=True)

    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        site_url = st.text_input("サイトURL", placeholder="https://example.com", help="トップページのURLを入力してください")
    with col_s2:
        site_max_pages = st.slider("収集するページ数（最大）", min_value=3, max_value=40, value=15, step=1)

    col_s3, col_s4 = st.columns([2, 1])
    with col_s3:
        site_all_professions = [p for group in PROFESSION_GROUPS.values() for p in group]
        site_profession_raw = st.selectbox("ジャンル", site_all_professions, key="site_profession")
        site_custom_service = ""
        if site_profession_raw == "カスタム（自由入力）":
            site_custom_service = st.text_input("サービス・業種名", placeholder="例：皮膚科、整体院、英会話スクール", key="site_custom")
        site_profession = site_custom_service if site_custom_service else site_profession_raw
    with col_s4:
        device_option = st.radio(
            "閲覧デバイス",
            ["💻 パソコン", "📱 スマホ"],
            horizontal=True,
            key="site_device",
        )
        site_device = "mobile" if "スマホ" in device_option else "pc"

    compare_devices = st.toggle(
        "PC＋スマホ両方で比較分析する（Proプラン相当・分析時間とAPI費用が約2倍になります）",
        value=False,
        key="site_compare_devices",
    )

    st.divider()
    use_site_custom = st.toggle("カスタムペルソナ設定を使う", value=False, key="site_custom_toggle")

    if use_site_custom:
        st.caption("ターゲット顧客を設定するとAIがその顧客視点でサイトを評価します")

        site_age = st.slider("お客さんの年齢帯", 20, 75, (35, 65), step=5, format="%d歳", key="site_age")
        site_gender_opt = st.selectbox("男女比", ["半々（5:5）", "男性が多め（7:3）", "女性が多め（7:3）", "男性のみ", "女性のみ"], key="site_gender")

        st.caption("お客さんが重視すること（複数選択可）")
        site_trust_presets = [
            "実績・件数が多い", "料金が明確", "対応が丁寧", "初回相談が無料",
            "地元・近所", "口コミ・評判が良い", "専門性が高い", "レスポンスが早い",
            "アフターサポートが充実", "オンライン対応可"
        ]
        site_trust_selected = []
        s_cols = st.columns(2)
        for i, opt in enumerate(site_trust_presets):
            if s_cols[i % 2].checkbox(opt, key=f"site_trust_{i}"):
                site_trust_selected.append(opt)
        site_trust_custom = st.text_input("その他（カンマ区切りで追加）", placeholder="例：土日対応, 女性担当者希望", key="site_trust_custom")
        if site_trust_custom:
            site_trust_selected += [t.strip() for t in site_trust_custom.split(",") if t.strip()]
        site_trust_selected = site_trust_selected[:10] or ["信頼性・実績を重視"]

        site_target_note = st.text_area(
            "ターゲット顧客の補足情報（任意）",
            placeholder="例：スマホ検索が多い、価格より効果重視、SNSで情報収集する層",
            height=80, key="site_target_note"
        )

        customer_profile = (
            f"年齢帯：{site_age[0]}〜{site_age[1]}歳 / 性別：{site_gender_opt} / "
            f"重視すること：{', '.join(site_trust_selected)}"
        )
        if site_target_note.strip():
            customer_profile += f" / 補足：{site_target_note.strip()[:200]}"
    else:
        customer_profile = ""
    st.divider()

    site_btn = st.button("🌐 サイト全体を分析する", type="primary", key="site_btn")

    def _run_device_analysis(device: str):
        """指定デバイスでスクレイピング＋AI分析を実行し、(scraped_pages, site_report) を返す。失敗時はNoneを返す。"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(f"{'スマホ' if device == 'mobile' else 'PC'}視点でページを収集中...")

        def _progress(done, total, title):
            progress_bar.progress(min(done / total, 1.0))
            status_text.text(f"収集中 ({done}/{total}): {title[:40]}")

        with st.spinner(f"{'スマホ' if device == 'mobile' else 'PC'}視点でサイトを巡回中..."):
            scraped = scrape_site(site_url, max_pages=site_max_pages, progress_cb=_progress, device=device)

        progress_bar.progress(1.0)
        status_text.empty()

        failed = []
        if scraped and "_failed" in scraped[-1]:
            failed = scraped[-1]["_failed"]
            scraped = scraped[:-1]

        if not scraped:
            st.error("ページを取得できませんでした。URLを確認してください。")
            if failed:
                with st.expander(f"取得失敗したページ（{len(failed)}件）"):
                    for f in failed:
                        st.markdown(f"- `{f['url']}` — **{f['reason']}**")
            return None

        st.success(f"{len(scraped)}ページを収集しました（{'スマホ' if device == 'mobile' else 'PC'}）")
        if failed:
            st.warning(f"取得できなかったページが {len(failed)} 件あります（ボット対策・JS描画等）")
            with st.expander("取得失敗ページの詳細"):
                for f in failed:
                    st.markdown(f"- `{f['url']}` — {f['reason']}")

        with st.expander(f"収集したページ一覧（{'スマホ' if device == 'mobile' else 'PC'}）"):
            for p in scraped:
                st.markdown(f"- **{p['title']}** — `{p['url']}`")

        with st.spinner("AIがサイト全体を分析中..."):
            report = analyze_site(scraped, site_profession, device=device, customer_profile=customer_profile)

        if report.get("error"):
            st.error(f"AI分析に失敗しました: {report.get('error')}")
            st.caption(f"詳細: {report.get('raw', '')}")
            return None

        return scraped, report

    if site_btn:
        if not site_url or not site_url.startswith("http"):
            st.error("正しいURLを入力してください（https:// から始まるURL）")
        elif compare_devices:
            pc_result = _run_device_analysis("pc")
            mobile_result = _run_device_analysis("mobile")
            if pc_result and mobile_result:
                pc_pages, pc_report = pc_result
                mobile_pages, mobile_report = mobile_result
                with st.spinner("PC・スマホの結果を比較中..."):
                    comparison = compare_device_reports(pc_report, mobile_report, site_profession)
                st.session_state["site_device_label"] = "💻 パソコン"
                st.session_state["site_report"] = pc_report
                st.session_state["site_pages"] = pc_pages
                st.session_state["site_mobile_report"] = mobile_report
                st.session_state["site_comparison"] = comparison
            else:
                st.stop()
        else:
            result = _run_device_analysis(site_device)
            if result:
                scraped_pages, site_report = result
                st.session_state["site_device_label"] = "📱 スマホ" if site_device == "mobile" else "💻 パソコン"
                st.session_state["site_report"] = site_report
                st.session_state["site_pages"] = scraped_pages
                st.session_state.pop("site_mobile_report", None)
                st.session_state.pop("site_comparison", None)
            else:
                st.stop()

    if "site_report" in st.session_state:
        sr = st.session_state["site_report"]
        pages = st.session_state.get("site_pages", [])
        device_label = st.session_state.get("site_device_label", "💻 PC")

        st.divider()
        st.markdown(f'<span style="background:#1a1a3e;color:white;font-size:0.8rem;font-weight:700;padding:4px 14px;border-radius:20px;">{device_label} 視点での分析結果</span>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # 全体評価
        inquiry_rate = sr.get("inquiry_rate", "—")
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            st.markdown(f"""
<div style="background:white;border-radius:12px;padding:1.2rem 1.5rem;box-shadow:0 2px 10px rgba(0,0,0,0.07);border-top:4px solid #6b46c1;">
  <div style="color:#6b7280;font-size:0.78rem;margin-bottom:6px;">サイト全体の第一印象</div>
  <div style="color:#1a1a3e;font-size:0.95rem;line-height:1.7;">{sr.get('overall_impression','')}</div>
</div>""", unsafe_allow_html=True)
        with col_r2:
            st.markdown(_mc("推定問い合わせ率（回遊後）", inquiry_rate, "#6b46c1"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 強み・弱み
        col_sw, col_ww = st.columns(2)
        with col_sw:
            st.markdown("#### ✅ 強み")
            for s in sr.get("strengths", []):
                st.markdown(f"""
<div style="background:#f0fdf4;border-left:4px solid #16a34a;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px;">
  <div style="font-weight:700;color:#16a34a;font-size:0.88rem;">{s.get('point','')}</div>
  <div style="color:#374151;font-size:0.82rem;margin-top:4px;">{s.get('reason','')}</div>
</div>""", unsafe_allow_html=True)
        with col_ww:
            st.markdown("#### ⚠️ 弱み")
            for w in sr.get("weaknesses", []):
                st.markdown(f"""
<div style="background:#fff7ed;border-left:4px solid #ea580c;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px;">
  <div style="font-weight:700;color:#ea580c;font-size:0.88rem;">{w.get('point','')}</div>
  <div style="color:#374151;font-size:0.82rem;margin-top:4px;">{w.get('reason','')}</div>
  <div style="color:#6b7280;font-size:0.78rem;margin-top:4px;font-style:italic;">→ {w.get('suggestion','')}</div>
</div>""", unsafe_allow_html=True)

        # 導線の問題
        nav_issues = sr.get("navigation_issues", [])
        if nav_issues:
            st.markdown("#### 🔗 導線・ナビゲーションの問題")
            for ni in nav_issues:
                st.markdown(f"""
<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 14px;margin-bottom:8px;display:flex;gap:12px;">
  <div style="background:#fef3c7;color:#92400e;font-size:0.72rem;font-weight:800;padding:3px 10px;border-radius:4px;white-space:nowrap;height:fit-content;">{ni.get('page','')}</div>
  <div>
    <div style="font-size:0.88rem;font-weight:600;color:#dc2626;">{ni.get('issue','')}</div>
    <div style="font-size:0.82rem;color:#6b7280;margin-top:3px;">→ {ni.get('suggestion','')}</div>
  </div>
</div>""", unsafe_allow_html=True)

        # 不足ページ
        missing = sr.get("missing_pages", [])
        if missing:
            st.markdown("#### 📄 あると効果的なページ（現在なし）")
            cols_m = st.columns(min(len(missing), 3))
            for i, m in enumerate(missing):
                with cols_m[i % 3]:
                    st.markdown(f"""
<div style="background:#f1f5f9;border-radius:8px;padding:8px 12px;text-align:center;font-size:0.85rem;font-weight:600;color:#1a1a3e;">
  📌 {m}
</div>""", unsafe_allow_html=True)

        # 最重要改善
        st.divider()
        st.markdown("#### 今すぐやるべき改善")
        st.error(sr.get("priority_action", ""))

        # DRM分析
        mi = sr.get("marketing_insights")
        if mi:
            st.markdown(_mi_html(mi, margin_top="1rem"), unsafe_allow_html=True)

        # PC/スマホ比較結果（Proプラン）
        comparison = st.session_state.get("site_comparison")
        if comparison:
            st.divider()
            st.markdown("#### 📱💻 PC / スマホ比較分析（Pro）")
            st.info(comparison.get("score_diff_summary", ""))
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                st.markdown("**PC閲覧時のみの問題**")
                for item in comparison.get("pc_only_issues", []):
                    st.markdown(f"- {item}")
            with col_c2:
                st.markdown("**スマホ閲覧時のみの問題**")
                for item in comparison.get("mobile_only_issues", []):
                    st.markdown(f"- {item}")
            with col_c3:
                st.markdown("**PC・スマホ共通の問題**")
                for item in comparison.get("shared_issues", []):
                    st.markdown(f"- {item}")
            if comparison.get("priority_reason"):
                st.warning(f"優先デバイス: {comparison.get('priority_device','')} — {comparison.get('priority_reason','')}")
            if comparison.get("recommendation"):
                st.success(comparison.get("recommendation", ""))

        # PDFダウンロード
        st.divider()
        try:
            site_pdf_bytes = generate_site_pdf(
                site_report=sr,
                scraped_pages=pages,
                profession=st.session_state.get("site_profession", ""),
                device_label=device_label,
                site_url=pages[0]["url"].split("/")[0] + "//" + pages[0]["url"].split("/")[2] if pages else "",
                comparison=comparison,
            )
            st.session_state["site_pdf_bytes"] = site_pdf_bytes
            _now_str = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M')
            fname_site = f"VCT_サイト分析_{st.session_state.get('site_profession','')}_{_now_str}.pdf"
            st.download_button(
                "📄 サイト分析レポートをPDFでダウンロード",
                data=site_pdf_bytes,
                file_name=fname_site,
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
            st.caption("コンビニのネットプリントでPDFの登録に失敗する場合は、下のJPEG（ZIP）版をお使いください。")
            if st.button("🖼️ JPEG画像（ZIP）に変換する", use_container_width=True, key="btn_site_jpeg"):
                with st.spinner("JPEGに変換中..."):
                    from pdf_generator import pdf_to_jpeg_zip
                    zip_bytes = pdf_to_jpeg_zip(site_pdf_bytes, base_name="VCTレポート")
                st.download_button(
                    "📦 JPEG（ZIP）をダウンロード",
                    data=zip_bytes,
                    file_name=f"VCT_サイト分析_{st.session_state.get('site_profession','')}_{_now_str}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
        except Exception as e:
            st.warning(f"PDF生成に失敗しました: {e}")

        # ── Zoom解説台本PDF ────────────────────────────────────────
        st.divider()
        st.markdown("#### 🎤 30分Zoom解説台本（コンサルタント専用）")
        st.caption("このボタンはあなた専用です。クライアントには渡しません。")
        if st.button("台本を生成する", use_container_width=True):
            with st.spinner("台本を生成中…（30秒ほどかかります）"):
                try:
                    _script_url = pages[0]["url"].split("/")[0] + "//" + pages[0]["url"].split("/")[2] if pages else ""
                    _power_score, _, _, _ = __import__("pdf_generator")._calc_power_score(sr)
                    script_data = generate_consultation_script(
                        site_report=sr,
                        site_url=_script_url,
                        profession=st.session_state.get("site_profession", ""),
                        power_score=_power_score,
                    )
                    if "error" in script_data:
                        st.error(f"台本生成エラー: {script_data.get('error')} / {str(script_data.get('raw',''))[:200]}")
                        st.stop()
                    script_pdf_bytes = generate_script_pdf(
                        script=script_data,
                        site_url=_script_url,
                        profession=st.session_state.get("site_profession", ""),
                    )
                    fname_script = f"VCT_台本_{st.session_state.get('site_profession','')}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M')}.docx"
                    st.download_button(
                        "📋 Zoom解説台本をダウンロード（Word / Googleドキュメント用）",
                        data=script_pdf_bytes,
                        file_name=fname_script,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        type="primary",
                    )
                    st.caption("ダウンロード後、GoogleドライブにアップロードするとそのままGoogleドキュメントとしてZoom中に開けます。")
                except Exception as e:
                    st.warning(f"台本生成に失敗しました: {e}")

        # ── 簡略版PDF（無料配布・メール添付用） ────────────────────
        st.divider()
        st.markdown("#### 📨 簡略版サマリーをメールで送る（無料配布用）")
        st.caption("診断結果の要点だけを1ページにまとめた簡易PDF。懇親会でその場で送れます。")

        try:
            _summary_url = pages[0]["url"].split("/")[0] + "//" + pages[0]["url"].split("/")[2] if pages else site_url
            summary_pdf_bytes = generate_summary_pdf(
                site_report=sr,
                site_url=_summary_url,
                profession=st.session_state.get("site_profession", ""),
                device_label=device_label,
            )
            st.session_state["summary_pdf_bytes"] = summary_pdf_bytes
            fname_summary = f"VCT_無料診断_{st.session_state.get('site_profession','')}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "📄 簡略版PDFをダウンロード",
                    data=summary_pdf_bytes,
                    file_name=fname_summary,
                    mime="application/pdf",
                    use_container_width=True,
                )
            with col_dl2:
                if st.button("🖼️ JPEGに変換する", use_container_width=True, key="btn_summary_jpeg"):
                    with st.spinner("JPEGに変換中..."):
                        from pdf_generator import pdf_to_jpeg_pages
                        _jpeg_pages = pdf_to_jpeg_pages(summary_pdf_bytes)
                    st.download_button(
                        "🖼️ JPEGをダウンロード",
                        data=_jpeg_pages[0],
                        file_name=f"VCT_無料診断_{st.session_state.get('site_profession','')}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M')}.jpg",
                        mime="image/jpeg",
                        use_container_width=True,
                    )
            st.caption("コンビニのネットプリントでPDFの登録に失敗する場合は、JPEG版をお使いください。")
        except Exception as e:
            st.warning(f"簡略版PDF生成に失敗しました: {e}")

        # 簡略版メール送信フォーム
        _found_emails = extract_emails_from_pages(pages)
        _default_email = _found_emails[0] if _found_emails else ""
        _prof_name = st.session_state.get("site_profession", "")

        summary_to = st.text_input(
            "送信先メールアドレス（簡略版）",
            value=_default_email,
            placeholder="info@example.com",
            key="summary_to_email",
        )
        summary_subject = st.text_input(
            "件名（簡略版）",
            value=f"【無料診断】{_prof_name}様のホームページ診断サマリー",
            key="summary_subject",
        )
        summary_body_default = (
            f"はじめまして。LIFE DESIGN LAB の斉藤かおりと申します。\n\n"
            f"{_prof_name}様のホームページを拝見し、"
            f"集客改善のヒントになればと、無料の診断サマリーを作成いたしました。\n\n"
            f"添付のPDF（1枚）をぜひご確認ください。\n\n"
            f"詳細な改善提案や改善コピーの作成も承っております。\n"
            f"お気軽にご返信ください。\n\n"
            f"---\n斉藤かおり（橘実柑）\nLIFE DESIGN LAB / トドク\n"
            f"inquiry.lifedesignlab@gmail.com"
        )
        summary_body = st.text_area("本文（簡略版）", value=summary_body_default, height=180, key="summary_body")

        if not email_is_configured():
            st.info("💡 `.env` に `SENDER_EMAIL` と `SENDER_APP_PASSWORD` を設定すると送信できます。")
        else:
            if st.button("📨 簡略版PDFを添付して送信", type="primary", use_container_width=True, key="btn_send_summary"):
                if not summary_to or "@" not in summary_to:
                    st.error("送信先メールアドレスを入力してください。")
                elif "summary_pdf_bytes" not in st.session_state:
                    st.error("先に簡略版PDFを生成してください。")
                else:
                    with st.spinner(f"{summary_to} に送信中..."):
                        ok, err = send_email_report(
                            to_email=summary_to,
                            subject=summary_subject,
                            body=summary_body,
                            pdf_bytes=st.session_state["summary_pdf_bytes"],
                            pdf_filename=f"VCT無料診断_{_prof_name}.pdf",
                        )
                    if ok:
                        st.success(f"✅ {summary_to} に簡略版PDFを送信しました！")
                    else:
                        st.error(f"送信に失敗しました。\n{err}")

        # ── 詳細版メール送信 ──────────────────────────────────────────────
        st.divider()
        st.markdown("#### 📧 詳細版レポートをメールで送信する")

        found_emails = extract_emails_from_pages(pages)
        default_email = found_emails[0] if found_emails else ""

        col_mail1, col_mail2 = st.columns([2, 1])
        with col_mail1:
            to_email = st.text_input(
                "送信先メールアドレス",
                value=default_email,
                placeholder="info@example-law.com",
                help="サイトから自動検出したアドレスが入っています。変更も可能です。",
            )
        with col_mail2:
            if found_emails:
                st.caption("サイトから自動検出したアドレス：")
                for e in found_emails[:3]:
                    st.caption(f"・{e}")

        prof_name = st.session_state.get("site_profession", "")
        default_subject = f"【トドクVCT 無料診断レポート】{prof_name}様のホームページ診断結果"
        mail_subject = st.text_input("件名", value=default_subject)

        default_body = (
            f"はじめまして。LIFE DESIGN LAB の斉藤かおりと申します。\n\n"
            f"先日、{prof_name}様のホームページを拝見し、"
            f"集客改善のヒントになればと思い、無料診断レポートを作成いたしました。\n\n"
            f"PDFを添付しておりますので、ぜひご覧ください。\n\n"
            f"ご質問やご相談があれば、お気軽にご返信ください。\n\n"
            f"---\n"
            f"斉藤かおり（橘実柑）\n"
            f"LIFE DESIGN LAB / トドク\n"
            f"inquiry.lifedesignlab@gmail.com"
        )
        mail_body = st.text_area("本文", value=default_body, height=200)

        if not email_is_configured():
            st.info(
                "💡 **メール送信の準備方法**\n\n"
                "Gmailアカウント作成後、`.env` ファイルを開いて以下の2行を入力するだけで送信できます：\n\n"
                "```\nSENDER_EMAIL=作成したGmailアドレス\nSENDER_APP_PASSWORD=16桁のアプリパスワード\n```\n\n"
                "アプリパスワードは：Googleアカウント → セキュリティ → 2段階認証 → アプリパスワード で生成できます。"
            )
        else:
            if "site_pdf_bytes" not in st.session_state:
                st.warning("先にPDFを生成してください。")
            elif st.button("📧 PDFを添付して送信する", type="primary", use_container_width=True):
                if not to_email or "@" not in to_email:
                    st.error("送信先メールアドレスを正しく入力してください。")
                else:
                    with st.spinner(f"{to_email} に送信中..."):
                        ok, err = send_email_report(
                            to_email=to_email,
                            subject=mail_subject,
                            body=mail_body,
                            pdf_bytes=st.session_state["site_pdf_bytes"],
                            pdf_filename=f"VCT診断レポート_{prof_name}.pdf",
                        )
                    if ok:
                        st.success(f"✅ {to_email} に送信しました！")
                    else:
                        st.error(f"送信に失敗しました。\n{err}")


# =====================================================================
# TAB: リストアップ（DM送付先候補の収集）
# =====================================================================
with tab_leads:
    st.subheader("🎯 DM送付先リストアップ")

    lead_source = st.radio(
        "検索方法",
        ["🗺️ Google Map検索（店舗・中小企業向け）", "📊 四季報掲載企業（上場企業・EDINETデータ）"],
        horizontal=True,
        key="lead_source",
    )

    if lead_source.startswith("📊"):
        st.caption(
            "会社四季報の掲載対象はほぼ全上場企業のため、金融庁EDINETの無料公開データ（EDINETコード一覧）で代替検索します。"
            "業種は東証33業種分類（四季報と同じ分類）です。"
        )

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            edinet_industry = st.selectbox("業種", EDINET_INDUSTRIES, key="edinet_industry")
        with col_e2:
            edinet_region = st.text_input("所在地キーワード（部分一致・空欄で全国）", placeholder="例：東京都、大阪市", key="edinet_region")

        edinet_keyword = st.text_input(
            "絞り込みキーワード（社名に含む文字・任意）",
            placeholder="例：ソフト、広告、通信 など業種のさらに細かい絞り込みに",
            key="edinet_keyword",
            help="EDINETデータには業種のサブカテゴリ（例：情報・通信業→ソフトウェア／広告／通信キャリア）が含まれないため、社名に含まれる文字での簡易絞り込みです。",
        )

        edinet_max = st.slider("最大取得件数", min_value=5, max_value=100, value=20, step=5, key="edinet_max")

        edinet_btn = st.button("🔍 検索する", type="primary", use_container_width=True, key="edinet_search_btn")

        if edinet_btn:
            with st.spinner("EDINETコードリストを検索中..."):
                try:
                    edinet_leads = search_edinet_companies(
                        industry=edinet_industry,
                        region_keyword=edinet_region,
                        name_keyword=edinet_keyword,
                        max_results=edinet_max,
                    )
                    st.session_state["edinet_lead_list"] = edinet_leads
                except Exception as e:
                    st.error(f"検索に失敗しました: {e}")
                    edinet_leads = None

            if edinet_leads is not None:
                st.success(f"{len(edinet_leads)}件の上場企業が見つかりました。")

        if "edinet_lead_list" in st.session_state and st.session_state["edinet_lead_list"]:
            edinet_leads = st.session_state["edinet_lead_list"]
            df_edinet = pd.DataFrame(edinet_leads)
            st.dataframe(df_edinet, use_container_width=True)

            csv_bytes = df_edinet.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📄 CSVでダウンロード",
                data=csv_bytes,
                file_name=f"四季報リストアップ_{st.session_state.get('edinet_industry','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="edinet_csv_download",
            )

    else:
        st.caption("業種・地域からGoogle Places APIで候補店舗を検索し、店名・住所・電話番号・ホームページURL・代表者名・SNSを一覧化します。")

        google_api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
        if google_api_key and not google_api_key.isascii():
            st.error("GOOGLE_PLACES_API_KEY に日本語や全角文字など、キーとして不正な文字が含まれています。Secretsの値を貼り直してください。")
            google_api_key = ""
        if not google_api_key:
            st.warning(
                "💡 **利用の準備方法**\n\n"
                "Google Cloud Platformで「Places API」を有効化し、APIキーを発行してください。\n"
                "`.env`（Streamlit Cloudの場合はSecrets）に以下を追加すると使えます：\n\n"
                "```\nGOOGLE_PLACES_API_KEY=発行したAPIキー\n```"
            )

        col_l1, col_l2 = st.columns(2)
        with col_l1:
            lead_all_professions = [p for group in PROFESSION_GROUPS.values() for p in group]
            lead_profession_raw = st.selectbox("業種", lead_all_professions, key="lead_profession")
            lead_custom_service = ""
            if lead_profession_raw == "カスタム（自由入力）":
                lead_custom_service = st.text_input("業種名（自由入力）", placeholder="例：皮膚科", key="lead_custom")
            lead_profession = lead_custom_service if lead_custom_service else lead_profession_raw
        with col_l2:
            lead_region = st.text_input("地域", placeholder="例：東京都渋谷区", key="lead_region")

        col_l3, col_l4 = st.columns(2)
        with col_l3:
            lead_max = st.slider("最大取得件数", min_value=5, max_value=60, value=20, step=5, key="lead_max")
        with col_l4:
            lead_extract_name = st.toggle("代表者名も推定する（AI・時間がかかります）", value=True, key="lead_extract_name")

        lead_btn = st.button("🔍 検索する", type="primary", use_container_width=True, disabled=not google_api_key, key="lead_search_btn")

        if lead_btn:
            if not lead_region.strip():
                st.error("地域を入力してください。")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def _lead_progress(done, total, name):
                    progress_bar.progress(min(done / total, 1.0) if total else 0)
                    status_text.text(f"取得中 ({done}/{total}): {name}")

                with st.spinner("店舗情報を検索中..."):
                    try:
                        leads = build_lead_list(
                            profession=lead_profession,
                            region=lead_region.strip(),
                            api_key=google_api_key,
                            max_results=lead_max,
                            progress_cb=_lead_progress,
                            extract_representative_name_fn=extract_representative_name if lead_extract_name else None,
                        )
                        st.session_state["lead_list"] = leads
                    except Exception as e:
                        st.error(f"検索に失敗しました: {e}")
                        leads = None

                progress_bar.progress(1.0)
                status_text.empty()

                if leads is not None:
                    st.success(f"{len(leads)}件の候補が見つかりました。")

        if "lead_list" in st.session_state and st.session_state["lead_list"]:
            leads = st.session_state["lead_list"]
            df_leads = pd.DataFrame(leads)
            st.dataframe(df_leads, use_container_width=True)

            csv_bytes = df_leads.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📄 CSVでダウンロード",
                data=csv_bytes,
                file_name=f"リストアップ_{st.session_state.get('lead_profession','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="lead_csv_download",
            )


# =====================================================================
# TAB 3: 履歴・トラッキング
# =====================================================================
with tab_history:
    st.subheader("テスト履歴")
    client_names = load_client_names()
    filter_col, _ = st.columns([1, 2])
    with filter_col:
        filter_client = st.selectbox(
            "クライアントで絞り込む",
            ["すべて"] + client_names,
        )
    history = load_history(client_name="" if filter_client == "すべて" else filter_client)

    if not history:
        st.info("まだテスト履歴がありません。「テスト実行」タブでテストを行うと自動的に保存されます。")
    else:
        # 改善トラッキンググラフ
        import re, pandas as pd
        lp_history = [h for h in history if "SNS" not in h["test_mode"] and "A/B" not in h["test_mode"]]
        if len(lp_history) >= 2:
            chart_data = []
            for h in reversed(lp_history[-20:]):
                rate_str = h.get("main_rate", "0%")
                # "40%" → 40 のみ抽出。100超・URLの数字混入を除外
                nums = [int(n) for n in re.findall(r"\d+", rate_str) if int(n) <= 100]
                rate_num = nums[0] if nums else None
                if rate_num is not None:
                    client_tag = f"[{h['client_name']}] " if h.get("client_name") else ""
                    chart_data.append({
                        "日時": h["created_at"],
                        "問い合わせ率(%)": rate_num,
                        "案件": f"{client_tag}{h['profession']}",
                    })
            if len(chart_data) >= 2:
                st.markdown("#### 問い合わせ率の推移")
                df = pd.DataFrame(chart_data)
                st.line_chart(df.set_index("日時")["問い合わせ率(%)"])
            elif lp_history:
                st.info("グラフはテストを2回以上実行すると表示されます")

        # 履歴テーブル
        st.markdown("#### テスト一覧")
        for h in history:
            mode_icon = "SNS" if "SNS" in h["test_mode"] else ("A/B" if "A/B" in h["test_mode"] else "LP")
            client_tag = f"【{h['client_name']}】 " if h.get("client_name") else ""
            with st.expander(f"[{mode_icon}] {client_tag}{h['created_at']} — {h['profession']} — {h['main_rate'] or '—'}"):
                st.caption(f"テキスト冒頭: {h['lp_text'][:80]}…")

                try:
                    report = json.loads(h["report_json"])
                    st.write(f"**総評:** {report.get('summary','')}")
                    st.markdown("**改善が必要な箇所:**")
                    for w in report.get("weaknesses",[]):
                        st.write(f"- {w.get('point','')}: {w.get('suggestion','')}")
                    st.markdown(f"**最重要改善:** {report.get('priority_action','')}")
                except Exception:
                    pass

                if st.button("削除", key=f"del_{h['id']}"):
                    delete_record(h["id"])
                    st.rerun()
