from fpdf import FPDF
from datetime import datetime
import os
import tempfile
from PIL import Image as _PILImage

# Windows フォントパス（游明朝 → 游ゴシック → メイリオ の優先順）
_FONT_MINCHO_R = r"C:\Windows\Fonts\yumin.ttf"
_FONT_MINCHO_B = r"C:\Windows\Fonts\yumindb.ttf"
_FONT_GOTHIC_R = r"C:\Windows\Fonts\YuGothR.ttc"
_FONT_GOTHIC_B = r"C:\Windows\Fonts\YuGothB.ttc"
_FONT_R = r"C:\Windows\Fonts\meiryo.ttc"
_FONT_B = r"C:\Windows\Fonts\meiryob.ttc"
_FONT_FALLBACK = r"C:\Windows\Fonts\msgothic.ttc"

# Linux フォントパス（Streamlit Cloud / Ubuntu — fonts-noto-cjk パッケージ）
_LINUX_FONT_DIRS = [
    "/usr/share/fonts/opentype/noto",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/noto",
    "/usr/share/fonts",
]
_LINUX_FONT_R_NAMES = ["NotoSansCJK-Regular.ttc", "NotoSansCJKjp-Regular.otf", "NotoSansJP-Regular.ttf"]
_LINUX_FONT_B_NAMES = ["NotoSansCJK-Bold.ttc", "NotoSansCJKjp-Bold.otf", "NotoSansJP-Bold.ttf"]

# ロゴ・キャラクター画像パス
_LOGO_PATH      = os.path.join(os.path.dirname(__file__), "logo.png")
_CHARACTER_PATH = os.path.join(os.path.dirname(__file__), "profile_dark.png")

# 変換済み一時ファイルキャッシュ
_converted_cache: dict = {}

def _make_cover_char(src_path: str, bg=(8, 8, 8), fade_frac: float = 0.45) -> str:
    """表紙用キャラクター: 左・上方向を多方向グラデーションで背景に自然に溶け込ませる。"""
    key = ("cover_char_v3", src_path, bg, fade_frac)
    if key in _converted_cache and os.path.exists(_converted_cache[key]):
        return _converted_cache[key]
    from PIL import ImageDraw
    img = _PILImage.open(src_path).convert("RGBA")
    w, h = img.size
    # アルファマスク（255=完全不透明、0=完全透明）
    mask = _PILImage.new("L", (w, h), 255)

    # 左フェード（45%幅・なだらかな曲線）
    fade_w = int(w * fade_frac)
    for x in range(fade_w):
        t = x / fade_w
        alpha = int(255 * (t ** 1.6))
        for y in range(h):
            cur = mask.getpixel((x, y))
            mask.putpixel((x, y), min(cur, alpha))

    # 上フェード（20%高さ・ホワイトボード上端を自然に溶かす）
    fade_h = int(h * 0.20)
    for y in range(fade_h):
        t = y / fade_h
        alpha = int(255 * (t ** 1.6))
        for x in range(w):
            cur = mask.getpixel((x, y))
            mask.putpixel((x, y), min(cur, alpha))

    img.putalpha(mask)
    bg_img = _PILImage.new("RGB", (w, h), bg)
    bg_img.paste(img, mask=img.split()[-1])
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    bg_img.save(tmp.name, "PNG")
    _converted_cache[key] = tmp.name
    return tmp.name

def _to_rgb_path(src_path: str, bg=(8, 8, 8)) -> str:
    """RGBA/P モードの画像を指定背景色でRGBに合成し、一時ファイルパスを返す。"""
    key = (src_path, bg)
    if key in _converted_cache and os.path.exists(_converted_cache[key]):
        return _converted_cache[key]
    img = _PILImage.open(src_path)
    if img.mode in ("RGBA", "LA", "P"):
        background = _PILImage.new("RGB", img.size, bg)
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name, "PNG")
    _converted_cache[key] = tmp.name
    return tmp.name

# ブランドカラー (R, G, B) — Black & Gold テーマ
NAVY      = (18, 18, 18)      # 本文・テキスト用の深黒（旧NAVY代替）
NAVY_DARK = (8, 8, 8)         # カバー背景用の最深黒
PURPLE    = (107, 70, 193)
WHITE     = (255, 255, 255)
LIGHT     = (248, 246, 240)   # 温かみのあるオフホワイト
GRAY      = (130, 125, 115)   # ウォームグレー
GREEN_BG  = (236, 253, 245)
GREEN_T   = (21, 128, 61)
RED_BG    = (254, 242, 242)
RED_T     = (185, 28, 28)
AMBER_BG  = (255, 251, 220)
AMBER_T   = (146, 64, 14)
BLUE_MID  = (37, 99, 235)
GREEN_MID = (22, 163, 74)
GOLD      = (212, 175, 55)    # メインゴールド
GOLD_LIGHT = (235, 205, 100)  # 明るいゴールド（ハイライト用）
GOLD_BG   = (252, 248, 230)   # ゴールド背景色
CHARCOAL  = (35, 32, 28)      # 深いチャコール（カード背景）
CHARCOAL2 = (50, 46, 40)      # 少し明るいチャコール


def _calc_power_score(site_report: dict) -> tuple:
    """AI総合パワースコア（100点満点）: DRM(30) + BrandZ(40) + GEO(30)。"""
    mi = site_report.get("marketing_insights", {})
    drm = mi.get("drm_score", "C")
    drm_pts = {"A": 30, "B": 22, "C": 14, "D": 6}.get(drm, 14)

    bz = site_report.get("brandz_score", {})
    bz_vals = []
    for key in ("meaningful", "different", "salient"):
        v = bz.get(key, {}).get("score", 5)
        try:
            bz_vals.append(int(v))
        except (ValueError, TypeError):
            bz_vals.append(5)
    bz_avg = sum(bz_vals) / len(bz_vals) if bz_vals else 5.0
    bz_pts = round(bz_avg / 10 * 40)

    geo = site_report.get("geo_score", {})
    try:
        geo_num = int(geo.get("score", 5))
    except (ValueError, TypeError):
        geo_num = 5
    geo_pts = round(geo_num / 10 * 30)

    return drm_pts + bz_pts + geo_pts, drm_pts, bz_pts, geo_pts


def _find_linux_font(names: list) -> str:
    """Linux環境でNoto CJKフォントを探索する。"""
    for d in _LINUX_FONT_DIRS:
        for name in names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                return path
    return ""


def _resolve_font():
    """游明朝 → 游ゴシック → メイリオ → Noto CJK（Linux）の優先順でフォントを解決。"""
    if os.path.exists(_FONT_MINCHO_R) and os.path.exists(_FONT_MINCHO_B):
        return _FONT_MINCHO_R, _FONT_MINCHO_B
    if os.path.exists(_FONT_GOTHIC_R) and os.path.exists(_FONT_GOTHIC_B):
        return _FONT_GOTHIC_R, _FONT_GOTHIC_B
    if os.path.exists(_FONT_R) and os.path.exists(_FONT_B):
        return _FONT_R, _FONT_B
    if os.path.exists(_FONT_FALLBACK):
        return _FONT_FALLBACK, _FONT_FALLBACK
    # Linux (Streamlit Cloud) fallback
    r = _find_linux_font(_LINUX_FONT_R_NAMES)
    b = _find_linux_font(_LINUX_FONT_B_NAMES)
    if r:
        return r, (b if b else r)
    return None, None


class _Base(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.alias_nb_pages()
        r_path, b_path = _resolve_font()
        if r_path:
            self.add_font("M", fname=r_path)
            self.add_font("M", style="B", fname=b_path)
            self._font = "M"
        else:
            self._font = "Helvetica"
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(15, 32, 15)
        self._accent = PURPLE  # サブクラスで上書き可能

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 28, style="F")
        self.set_y(6)
        self.set_font(self._font, "B", 13)
        self.set_text_color(*WHITE)
        self.cell(0, 8, "トドク VCT  仮想顧客テストレポート", align="C")
        self.set_y(16)
        self.set_font(self._font, "", 8)
        self.set_text_color(160, 160, 210)
        self.cell(0, 6, "Powered by LIFE DESIGN LAB", align="C")
        self.ln(14)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font(self._font, "", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 10, f"© LIFE DESIGN LAB  ·  {datetime.now().strftime('%Y年%m月%d日')}  ·  {self.page_no()} / {{nb}} ページ", align="C")

    def section_bar(self, text: str):
        self.set_fill_color(*PURPLE)
        self.set_text_color(*WHITE)
        self.set_font(self._font, "B", 9)
        y = self.get_y()
        self.rect(self.l_margin, y, 180, 7.5, style="F")
        self.set_xy(self.l_margin + 3, y + 1)
        self.cell(174, 5.5, text)
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def colored_block(self, text: str, bg, tc, indent=0):
        lm = self.l_margin + indent
        w = 180 - indent
        self.set_fill_color(*bg)
        self.set_text_color(*tc)
        self.set_font(self._font, "", 9)
        self.set_x(lm)
        self.multi_cell(w, 5.5, text, fill=True, padding=(2, 3, 2, 3))
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def meta_line(self, profession, persona_count, test_mode):
        self.set_font(self._font, "", 8)
        self.set_text_color(*GRAY)
        self.set_x(self.l_margin)
        self.cell(0, 5, (
            f"テスト日時: {datetime.now().strftime('%Y年%m月%d日  %H:%M')}"
            f"　｜　ジャンル: {profession}"
            f"　｜　仮想顧客数: {persona_count}人"
            f"　｜　モード: {test_mode}"
        ))
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def metric_box(self, label, value, bg, tc, x, y, w=43, h=20):
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, style="F")
        # 背景が暗い場合はラベルを白っぽく、明るい場合はグレーに
        label_color = (200, 200, 220) if tc == WHITE else GRAY
        self.set_xy(x, y + 2)
        self.set_font(self._font, "", 7)
        self.set_text_color(*label_color)
        self.cell(w, 4, label, align="C")
        self.set_xy(x, y + 7)
        self.set_font(self._font, "B", 13)
        self.set_text_color(*tc)
        self.cell(w, 9, str(value), align="C")
        self.set_text_color(0, 0, 0)

    def cta_footer(self):
        self.ln(6)
        lm = self.l_margin
        y = self.get_y()
        self.set_fill_color(*NAVY_DARK)
        self.rect(lm, y, 180, 18, style="F")
        self.set_fill_color(*GOLD)
        self.rect(lm, y, 180, 0.8, style="F")
        self.rect(lm, y + 17.2, 180, 0.8, style="F")
        self.set_xy(lm, y + 4)
        self.set_font(self._font, "B", 10)
        self.set_text_color(*GOLD)
        self.cell(180, 6, "このレポートはトドクがプロ視点で分析しました", align="C")
        self.set_y(y + 11)
        self.set_font(self._font, "", 8)
        self.set_text_color(160, 148, 100)
        self.cell(180, 5, "LP改善・マンガ制作・コンテンツ戦略のご相談はLIFE DESIGN LABまで", align="C")
        self.set_text_color(0, 0, 0)

    def _final_footer(self):
        """最終ページ専用: ブランドメッセージ + CTAを1本の帯に統合。ロゴ・キャラ付き。"""
        remaining = 297 - self.get_y() - 22
        y = self.get_y() + max(6, remaining * 0.3)
        lm = self.l_margin
        box_h = 28  # 統合帯の高さ

        # 黒背景帯（横幅いっぱい）
        self.set_fill_color(*NAVY_DARK)
        self.rect(0, y, 210, box_h, style="F")
        # 上下ゴールドライン（横幅いっぱい）
        self.set_fill_color(*GOLD)
        self.rect(0, y, 210, 0.8, style="F")
        self.rect(0, y + box_h - 0.8, 210, 0.8, style="F")

        # テキスト（ロゴなし・全幅中央揃え）
        self.set_xy(0, y + 4)
        self.set_font(self._font, "B", 9.5)
        self.set_text_color(*GOLD)
        self.cell(210, 6, "あなたのサイトを、選ばれる事務所へ。", align="C")
        self.set_xy(0, y + 12)
        self.set_font(self._font, "", 7.5)
        self.set_text_color(*WHITE)
        self.cell(210, 5, "このレポートはトドクがプロ視点で分析しました", align="C")
        self.set_xy(0, y + 19)
        self.set_font(self._font, "", 6.5)
        self.set_text_color(160, 148, 100)
        self.cell(210, 4.5, "LP改善・マンガ制作・コンテンツ戦略  ·  LIFE DESIGN LAB", align="C")
        self.set_text_color(0, 0, 0)

    def _drm_score_colors(self, mi: dict):
        score = mi.get("drm_score", "C")
        score_color = {"A": GREEN_MID, "B": BLUE_MID, "C": (217, 119, 6), "D": (185, 28, 28)}.get(score, GRAY)
        desc = {
            "A": "集客・教育・販売がすべて機能。広告をかけると費用対効果が高い状態。",
            "B": "基本はできているが1〜2か所の改善で大きく伸びる伸びしろがある状態。",
            "C": "構造に問題あり。改善なく広告をかけると費用を無駄にする可能性が高い。",
            "D": "根本から作り直しが必要。現状のまま運用しても成果は出にくい。",
        }.get(score, "")
        return score, score_color, desc

    def drm_overview(self, mi: dict):
        """p.4用: DRM解説・グレードカード・スコアバッジ・地味だけどヤバいポイント"""
        if not mi:
            return
        lm = self.l_margin
        score, score_color, desc = self._drm_score_colors(mi)

        self.section_bar("マーケティング総合評価（DRM：ダイレクトレスポンスマーケティング）")

        # DRM解説ボックス（動的高さ）
        lm = self.l_margin
        ex_y = self.get_y()
        _drm_explain = (
            "「集客 → 教育 → 販売」の3ステップで見込み客を顧客へと育てるマーケティング手法です。"
            "単に広告を出すのではなく、信頼関係を築きながら自然な流れで問い合わせ・成約へ導く導線設計が核心です。"
        )
        _drm_lines = max(2, -(-len(_drm_explain) // 36))
        ex_h = max(30, _drm_lines * 5 + 16)
        self.set_fill_color(248, 244, 234)
        self.rect(lm, ex_y, 180, ex_h, style="F")
        self.set_fill_color(*GOLD)
        self.rect(lm, ex_y, 3, ex_h, style="F")
        self.set_xy(lm + 6, ex_y + 2.5)
        self.set_font(self._font, "B", 7.5)
        self.set_text_color(*GOLD)
        self.cell(170, 4.5, "DRM（ダイレクトレスポンスマーケティング）とは")
        self.set_xy(lm + 6, ex_y + 8)
        self.set_font(self._font, "", 7.5)
        self.set_text_color(22, 18, 10)
        self.set_auto_page_break(auto=False)
        self.multi_cell(171, 4.5, _drm_explain)
        self.set_auto_page_break(auto=True, margin=22)
        self.set_y(ex_y + ex_h + 4)

        # A〜D グレード説明（横一列）
        grade_y = self.get_y()
        grades = [
            ("A", GREEN_MID,       "広告投下タイミング",
             "集客・教育・販売の導線がすべて機能。今すぐ広告をかけると費用対効果が高い。"),
            ("B", BLUE_MID,        "改善で大きく伸びる",
             "基本はできているが1〜2か所の改善で大幅アップが狙える伸びしろ十分な状態。"),
            ("C", (217, 119, 6),   "改善してから広告を",
             "構造的な問題あり。このまま広告費をかけると無駄になる可能性が高い。"),
            ("D", (185, 28, 28),   "根本的な見直しが必要",
             "集客の仕組みが機能していない。まず導線設計から作り直すことを推奨。"),
        ]
        gw = 43
        for i, (g, gc, g_title, g_desc) in enumerate(grades):
            gx = lm + i * (gw + 2)
            # 背景
            self.set_fill_color(248, 244, 234)
            self.rect(gx, grade_y, gw, 26, style="F")
            # グレードバッジ
            self.set_fill_color(*gc)
            self.rect(gx, grade_y, gw, 8, style="F")
            self.set_xy(gx, grade_y + 0.5)
            self.set_font(self._font, "B", 12)
            self.set_text_color(*WHITE)
            self.cell(gw, 7, g, align="C")
            # タイトル
            self.set_xy(gx + 2, grade_y + 9.5)
            self.set_font(self._font, "B", 6.5)
            self.set_text_color(*gc)
            self.cell(gw - 4, 4, g_title, align="C")
            # 説明文
            self.set_xy(gx + 2, grade_y + 14.5)
            self.set_font(self._font, "", 6)
            self.set_text_color(75, 65, 45)
            self.multi_cell(gw - 4, 3.5, g_desc)
        self.set_y(grade_y + 30)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        # 今回のスコアバッジ + 総評
        y0 = self.get_y()
        self.set_fill_color(42, 36, 22)
        self.rect(lm, y0, 180, 28, style="F")
        self.set_fill_color(*score_color)
        self.rect(lm + 4, y0 + 4, 18, 20, style="F")
        self.set_xy(lm + 4, y0 + 8)
        self.set_font(self._font, "B", 14)
        self.set_text_color(*WHITE)
        self.cell(18, 10, score, align="C")
        self.set_xy(lm + 26, y0 + 4)
        self.set_font(self._font, "B", 8)
        self.set_text_color(160, 148, 100)
        self.cell(150, 5, "今回のサイトの総合評価")
        self.set_xy(lm + 26, y0 + 10)
        self.set_font(self._font, "B", 8.5)
        self.set_text_color(*WHITE)
        self.set_auto_page_break(auto=False)
        self.multi_cell(150, 5.5, desc)
        self.set_auto_page_break(auto=True, margin=22)
        self.set_y(y0 + 32)
        self.set_text_color(0, 0, 0)

        # 地味だけどヤバい改善ポイント
        gem = mi.get("hidden_gem", "")
        if gem:
            if (297 - self.get_y() - 22) < 36:
                self.add_page()
            y_gem = self.get_y()
            # 高さを事前計算（動的）
            _gem_lines = max(2, -(-len(gem) // 40))
            _gem_body_h = _gem_lines * 5.5 + 10
            # ヘッダーバー
            self.set_fill_color(*self._accent)
            self.rect(lm, y_gem, 180, 7, style="F")
            self.set_xy(lm + 5, y_gem + 1)
            self.set_font(self._font, "B", 8.5)
            self.set_text_color(*WHITE)
            self.cell(170, 5, "◆  地味だけどヤバい改善ポイント")
            # 本文エリア（動的高さ）
            self.set_fill_color(250, 244, 222)
            self.rect(lm, y_gem + 7, 180, _gem_body_h, style="F")
            self.set_fill_color(*self._accent)
            self.rect(lm, y_gem + 7, 3, _gem_body_h, style="F")
            self.set_xy(lm + 7, y_gem + 11)
            self.set_font(self._font, "", 9)
            self.set_text_color(*NAVY)
            self.set_auto_page_break(auto=False)
            self.multi_cell(170, 5.5, gem)
            self.set_auto_page_break(auto=True, margin=22)
            self.set_y(y_gem + 7 + _gem_body_h + 4)
            self.ln(2)

        self.set_text_color(0, 0, 0)

    def drm_axis(self, mi: dict):
        """p.5用: DRM 4軸詳細カード"""
        if not mi:
            return
        lm = self.l_margin
        self.section_bar("DRM 4軸詳細分析")
        axis_items = [
            ("ファーストビュー", "最初に目に入る画面・第一印象", "first_view"),
            ("信頼構築", "実績・口コミ・資格で安心感を作る施策", "trust_building"),
            ("差別化", "競合との違いの見せ方・独自ポジション", "differentiation"),
            ("CTA（行動喚起）", "問い合わせや申込みを促すボタン・文章", "cta_strength"),
        ]
        for label, sub, key in axis_items:
            txt = mi.get(key, "")
            if (297 - self.get_y() - 22) < 40:
                self.add_page()
            y = self.get_y()

            # body_h を先に計算してカード全体の高さを確定
            chars_per_line = 55
            lines = max(1, -(-len(txt) // chars_per_line))
            body_h = lines * 5.5 + 7
            card_h = 11.8 + body_h

            # カード全体クリーム背景
            self.set_fill_color(248, 244, 234)
            self.rect(lm, y, 180, card_h, style="F")
            # ゴールド上ライン・左バー（全高）
            self.set_fill_color(*GOLD)
            self.rect(lm, y, 180, 0.8, style="F")
            self.rect(lm, y, 3, card_h, style="F")
            # ヘッダー/ボディ区切り
            self.set_fill_color(201, 169, 110)
            self.rect(lm + 3, y + 11.4, 177, 0.3, style="F")

            # ヘッダーテキスト（ダーク）
            self.set_xy(lm + 7, y + 3)
            self.set_font(self._font, "B", 9)
            self.set_text_color(42, 36, 22)
            label_w = self.get_string_width(label)
            self.cell(label_w + 2, 5.5, label)
            self.set_font(self._font, "", 6.5)
            self.set_text_color(120, 110, 80)
            self.cell(160, 5.5, f"  —  {sub}")

            # 本文テキスト
            self.set_auto_page_break(auto=False)
            self.set_xy(lm + 8, y + 15)
            self.set_font(self._font, "", 9)
            self.set_text_color(22, 18, 10)
            self.multi_cell(168, 6, txt)
            self.set_auto_page_break(auto=True, margin=22)
            self.set_y(y + card_h + 5)
        self.set_text_color(0, 0, 0)

    def drm_section(self, mi: dict):
        """後方互換ラッパー（overview + axis を連続実行）"""
        self.drm_overview(mi)
        self.drm_axis(mi)

    def brandz_section(self, bz: dict):
        """BrandZ（Kantar）3軸スコアページ"""
        if not bz:
            return
        lm = self.l_margin
        self.section_bar("BrandZ スコア（Kantar ブランドエクイティ分析）")

        axes = [
            ("意味性  Meaningful", "顧客ニーズへの機能的・感情的適合度", "meaningful", (180, 140, 60)),
            ("差別性  Different",  "競合との明確な差別化・唯一のポジション", "different",  (100, 140, 80)),
            ("顕著性  Salient",    "想起容易性・AI検索（GEO）での発見可能性", "salient",   (80, 120, 180)),
        ]

        for label, sub, key, accent in axes:
            data = bz.get(key, {})
            score = int(data.get("score", 5)) if str(data.get("score", "5")).isdigit() else 5
            comment = data.get("comment", "")

            chars_per_line = 52
            lines = max(1, -(-len(comment) // chars_per_line))
            body_h = lines * 5.5 + 7
            card_h = 14 + body_h

            if (297 - self.get_y() - 22) < card_h + 4:
                self.add_page()

            y = self.get_y()
            # カード背景
            self.set_fill_color(248, 244, 234)
            self.rect(lm, y, 180, card_h, style="F")
            self.set_fill_color(*GOLD)
            self.rect(lm, y, 180, 0.8, style="F")
            self.set_fill_color(*accent)
            self.rect(lm, y, 3, card_h, style="F")

            # スコアバッジ（右側 — 大きめの円 + /10表記）
            cx = lm + 171
            cy = y + card_h / 2 - 3
            r = 10
            self.set_fill_color(*accent)
            self.ellipse(cx - r, cy - r, r * 2, r * 2, style="F")
            self.set_font(self._font, "B", 13)
            self.set_text_color(255, 255, 255)
            self.set_xy(cx - r, cy - 5)
            self.cell(r * 2, 8, str(score), align="C")
            self.set_xy(cx - r, cy + 3)
            self.set_font(self._font, "", 6)
            self.cell(r * 2, 4, "/10", align="C")

            # ヘッダー
            self.set_xy(lm + 7, y + 3)
            self.set_font(self._font, "B", 9)
            self.set_text_color(42, 36, 22)
            self.cell(100, 5.5, label)
            self.set_font(self._font, "", 6.5)
            self.set_text_color(120, 110, 80)
            self.set_xy(lm + 7, y + 8.5)
            self.cell(150, 4, sub)

            # 区切り線
            self.set_fill_color(201, 169, 110)
            self.rect(lm + 3, y + 13.5, 177, 0.3, style="F")

            # コメント（スコア円と重ならないよう幅を調整）
            self.set_auto_page_break(auto=False)
            self.set_xy(lm + 8, y + 16)
            self.set_font(self._font, "", 8.5)
            self.set_text_color(22, 18, 10)
            self.multi_cell(148, 5.5, comment)
            self.set_auto_page_break(auto=True, margin=22)
            self.set_y(y + card_h + 4)

        # BrandZ総評
        total_comment = bz.get("brandz_comment", "")
        if total_comment:
            y = self.get_y() + 2
            self.set_fill_color(42, 36, 22)
            self.rect(lm, y, 180, 0.8, style="F")
            self.set_xy(lm, y + 4)
            self.set_font(self._font, "B", 8.5)
            self.set_text_color(*GOLD)
            self.cell(20, 5, "総評")
            self.set_font(self._font, "", 8.5)
            self.set_text_color(22, 18, 10)
            self.multi_cell(160, 5.5, total_comment)

        self.set_text_color(0, 0, 0)

    def geo_section(self, geo: dict):
        """GEO（AI検索最適化）スコアセクション — 5ステップ＋11項目チェックリスト"""
        if not geo:
            return
        lm = self.l_margin
        self.ln(4)
        self.section_bar("GEO スコア（AI検索最適化 / Generative Engine Optimization）")

        score = int(geo.get("score", 5)) if str(geo.get("score", "5")).isdigit() else 5

        # ── 総合スコアバー ──
        y = self.get_y()
        self.set_fill_color(42, 36, 22)
        self.rect(lm, y, 180, 14, style="F")
        self.set_fill_color(*GOLD)
        self.rect(lm, y, 3, 14, style="F")
        self.set_font(self._font, "B", 10)
        self.set_text_color(*GOLD)
        self.set_xy(lm + 8, y + 3.5)
        self.cell(60, 6, f"GEO 総合スコア：{score} / 10")
        self.set_font(self._font, "", 7.5)
        self.set_text_color(220, 200, 150)
        self.cell(110, 6, "AIに推薦・引用されやすさ（Kantar GEO対策基準）")
        self.set_y(y + 17)

        # ── 5ステップスコア ──
        step_scores = geo.get("step_scores", {})
        steps = [
            ("S1 構造化", "step1_structure"),
            ("S2 How to", "step2_howto"),
            ("S3 Q&A",   "step3_qa"),
            ("S4 比較表", "step4_comparison"),
            ("S5 事例",  "step5_case"),
        ]
        if step_scores:
            y = self.get_y()
            self.set_fill_color(248, 244, 234)
            self.rect(lm, y, 180, 18, style="F")
            self.set_fill_color(*GOLD)
            self.rect(lm, y, 180, 0.6, style="F")
            self.set_font(self._font, "B", 7.5)
            self.set_text_color(42, 36, 22)
            self.set_xy(lm + 4, y + 3)
            self.cell(180, 4, "GEO対策 5ステップ評価（各5点）")
            col_w = 34
            for i, (label, key) in enumerate(steps):
                val = step_scores.get(key, "–")
                cx = lm + 4 + i * col_w
                self.set_xy(cx, y + 9)
                self.set_font(self._font, "", 6.5)
                self.set_text_color(80, 70, 50)
                self.cell(col_w - 2, 4, label, align="C")
                self.set_xy(cx, y + 13)
                self.set_font(self._font, "B", 9)
                self.set_text_color(42, 36, 22)
                self.cell(col_w - 2, 4, f"{val} / 5", align="C")
            self.set_y(y + 21)

        # ── チェックリスト（縦並び：切れ防止） ──
        ok_items = geo.get("checklist_ok", [])
        ng_items = geo.get("checklist_missing", [])
        if ok_items or ng_items:
            y = self.get_y()
            self.set_fill_color(248, 244, 234)
            self.rect(lm, y, 180, 0.6, style="F")
            self.set_y(y + 3)
            # ✅ 揃っている項目
            if ok_items:
                self.set_x(lm + 4)
                self.set_font(self._font, "B", 7.5)
                self.set_text_color(22, 80, 40)
                self.cell(176, 4.5, f"✅ 揃っている項目（{len(ok_items)}）")
                self.ln(5)
                for ok in ok_items[:6]:
                    self.set_x(lm + 8)
                    self.set_font(self._font, "", 8)
                    self.set_text_color(22, 100, 50)
                    self.multi_cell(172, 4.5, f"✅ {ok}")
            self.ln(2)
            # ❌ 不足している項目
            if ng_items:
                self.set_x(lm + 4)
                self.set_font(self._font, "B", 7.5)
                self.set_text_color(140, 20, 20)
                self.cell(176, 4.5, f"❌ 不足している項目（{len(ng_items)}）")
                self.ln(5)
                for ng in ng_items[:6]:
                    self.set_x(lm + 8)
                    self.set_font(self._font, "", 8)
                    self.set_text_color(160, 30, 30)
                    self.multi_cell(172, 4.5, f"❌ {ng}")
            self.ln(3)

        # ── 原因と改善アクション ──
        for items, title, color in [
            (geo.get("issues", []), "AIに無視される原因", (185, 28, 28)),
            (geo.get("actions", []), "最優先 GEO改善アクション", (22, 120, 60)),
        ]:
            if not items:
                continue
            y = self.get_y()
            self.set_fill_color(*color)
            self.rect(lm, y, 180, 6, style="F")
            self.set_font(self._font, "B", 8)
            self.set_text_color(255, 255, 255)
            self.set_xy(lm + 4, y + 1)
            self.cell(180, 4, title)
            self.set_y(y + 8)
            for item in items[:3]:
                self.set_xy(lm + 6, self.get_y())
                self.set_font(self._font, "", 8.5)
                self.set_text_color(22, 18, 10)
                self.cell(4, 5.5, "•")
                self.multi_cell(170, 5.5, str(item))
            self.ln(2)

        self.set_text_color(0, 0, 0)

    def persona_table(self, personas, reactions, mode):
        self.section_bar("仮想顧客ペルソナ一覧")
        lm = self.l_margin
        for i, (p, r) in enumerate(zip(personas, reactions), 1):
            if mode == "sns":
                verdict = r.get("will_stop_scrolling", "no")
                v_label = {"yes": "◎ 停止する", "maybe": "△ 迷う", "no": "✗ スルー"}.get(verdict, verdict)
                impression = r.get("first_impression", "")
            else:
                verdict = r.get("will_inquire", "maybe")
                v_label = {"yes": "◎ 問い合わせする", "maybe": "△ 迷う", "no": "✗ しない"}.get(verdict, verdict)
                impression = r.get("first_impression", "")
            self.set_fill_color(*LIGHT)
            y0 = self.get_y()
            self.rect(lm, y0, 180, 15, style="F")
            self.set_xy(lm + 2, y0 + 2)
            self.set_font(self._font, "B", 8.5)
            self.set_text_color(*NAVY)
            self.cell(130, 5, f"No.{i}  {p['age']}歳 {p['gender']}  —  {p['problem_type']}")
            self.set_font(self._font, "B", 8.5)
            self.set_text_color(*PURPLE)
            self.cell(44, 5, v_label, align="R")
            self.ln(6)
            self.set_x(lm + 4)
            self.set_font(self._font, "", 7.5)
            self.set_text_color(*GRAY)
            self.cell(174, 4, str(impression)[:80])
            self.ln(6)
            self.set_text_color(0, 0, 0)


# ─────────────────────────────────────────────────────────
# 通常テスト (LP / SNS)
# ─────────────────────────────────────────────────────────
def generate_pdf(
    report: dict, personas: list, reactions: list,
    mode: str, profession: str, persona_count: int,
    main_rate: str, test_mode: str = "LP",
) -> bytes:
    pdf = _Base()
    pdf.add_page()
    lm = pdf.l_margin

    pdf.meta_line(profession, persona_count, test_mode)

    # メトリクス
    y0 = pdf.get_y()
    if mode == "sns":
        stop_yes   = sum(1 for r in reactions if r.get("will_stop_scrolling") == "yes")
        stop_maybe = sum(1 for r in reactions if r.get("will_stop_scrolling") == "maybe")
        like_ct    = sum(1 for r in reactions if r.get("will_like") == "yes")
        visit_ct   = sum(1 for r in reactions if r.get("will_visit_profile") == "yes")
        boxes = [
            ("スクロール停止率", report.get("stop_rate", main_rate), PURPLE, WHITE),
            ("停止する",         f"{stop_yes}人",  GREEN_MID,  WHITE),
            ("迷う",             f"{stop_maybe}人", AMBER_BG,  AMBER_T),
            ("いいね率",         report.get("like_rate", "-"), BLUE_MID, WHITE),
            ("プロフ訪問率",     report.get("profile_visit_rate", "-"), (80,40,160), WHITE),
        ]
    else:
        yes_ct   = sum(1 for r in reactions if r.get("will_inquire") == "yes")
        maybe_ct = sum(1 for r in reactions if r.get("will_inquire") == "maybe")
        no_ct    = sum(1 for r in reactions if r.get("will_inquire") == "no")
        boxes = [
            ("推定問い合わせ率", report.get("inquiry_rate", main_rate), PURPLE,     WHITE),
            ("する",             f"{yes_ct}人",                          GREEN_MID,  WHITE),
            ("迷う",             f"{maybe_ct}人",                        AMBER_BG,   AMBER_T),
            ("しない",           f"{no_ct}人",                           (200,50,50), WHITE),
        ]

    gap, bw = 3, 43
    for i, (label, val, bg, tc) in enumerate(boxes):
        pdf.metric_box(label, val, bg, tc, lm + i * (bw + gap), y0)
    pdf.set_y(y0 + 24)
    pdf.ln(4)

    # 総評
    pdf.section_bar("総評")
    pdf.set_font(pdf._font, "", 10)
    pdf.set_x(lm)
    pdf.multi_cell(180, 6, report.get("summary", ""))
    pdf.ln(4)

    # 強み
    pdf.section_bar("効果的だった点")
    for s in report.get("strengths", []):
        text = f"✓  {s.get('point', '')}  —  {s.get('reason', '')}"
        pdf.colored_block(text, GREEN_BG, GREEN_T)
    pdf.ln(2)

    # 弱み
    pdf.section_bar("改善が必要な箇所")
    for w in report.get("weaknesses", []):
        pdf.colored_block(f"✗  {w.get('point', '')}  —  {w.get('reason', '')}", RED_BG, RED_T)
        if w.get("suggestion"):
            pdf.colored_block(f"→ 改善案: {w['suggestion']}", GREEN_BG, GREEN_T, indent=6)
    pdf.ln(2)

    # 最重要改善
    pdf.section_bar("今すぐやるべき最重要改善")
    pdf.set_fill_color(*AMBER_BG)
    pdf.set_draw_color(*AMBER_T)
    pdf.set_text_color(*AMBER_T)
    pdf.set_font(pdf._font, "B", 10)
    pdf.set_x(lm)
    pdf.multi_cell(180, 6, report.get("priority_action", ""), fill=True, border=1, padding=(3, 4, 3, 4))
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # DRM分析
    mi = report.get("marketing_insights")
    if mi:
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.drm_section(mi)

    # ペルソナ一覧
    if pdf.get_y() > 220:
        pdf.add_page()
    pdf.persona_table(personas, reactions, mode)

    pdf.cta_footer()
    return bytes(pdf.output())


# ─────────────────────────────────────────────────────────
# A/B テスト専用
# ─────────────────────────────────────────────────────────
def generate_ab_pdf(
    ab_report: dict, personas: list, reactions_a: list, reactions_b: list,
    text_a: str, text_b: str, mode: str, profession: str, persona_count: int,
) -> bytes:
    pdf = _Base()
    pdf.add_page()
    lm = pdf.l_margin

    pdf.meta_line(profession, persona_count, "A/Bテスト")

    # 勝者バナー
    winner = ab_report.get("winner", "?")
    banner_bg = GREEN_MID if winner in ["A", "B"] else (100, 100, 140)
    pdf.set_fill_color(*banner_bg)
    y_b = pdf.get_y()
    pdf.rect(lm, y_b, 180, 14, style="F")
    pdf.set_xy(lm, y_b + 2)
    pdf.set_font(pdf._font, "B", 14)
    pdf.set_text_color(*WHITE)
    label = f"判定：バージョン {winner} が勝利" if winner in ["A", "B"] else "判定：引き分け"
    pdf.cell(180, 10, label, align="C")
    pdf.ln(16)
    pdf.set_text_color(0, 0, 0)

    # スコアボックス
    y0 = pdf.get_y()
    pdf.metric_box("バージョン A スコア", f"{ab_report.get('score_a', '?')} / 100", LIGHT, NAVY, lm,      y0, w=87)
    pdf.metric_box("バージョン B スコア", f"{ab_report.get('score_b', '?')} / 100", LIGHT, NAVY, lm + 93, y0, w=87)
    pdf.set_y(y0 + 24)
    pdf.ln(2)

    # 勝利理由
    pdf.section_bar("勝利理由")
    pdf.set_x(lm)
    pdf.set_font(pdf._font, "", 10)
    pdf.multi_cell(180, 6, ab_report.get("winner_reason", ""))
    pdf.ln(4)

    # 総評
    pdf.section_bar("総評")
    pdf.set_x(lm)
    pdf.multi_cell(180, 6, ab_report.get("summary", ""))
    pdf.ln(4)

    # A/B それぞれの強み（2カラム）
    pdf.section_bar("各バージョンの強み")
    col_w = 87
    y_start = pdf.get_y()
    x_a, x_b = lm, lm + 93

    # A の強み
    pdf.set_fill_color(*LIGHT)
    pdf.set_font(pdf._font, "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.rect(x_a, y_start, col_w, 7, style="F")
    pdf.set_xy(x_a + 2, y_start + 1)
    pdf.cell(col_w - 4, 5, "バージョン A の強み")
    y_a_body = y_start + 8
    pdf.set_text_color(0, 0, 0)
    for point in ab_report.get("a_strengths", []):
        pdf.set_xy(x_a, y_a_body)
        pdf.set_fill_color(*GREEN_BG)
        pdf.set_text_color(*GREEN_T)
        pdf.set_font(pdf._font, "", 8.5)
        pdf.multi_cell(col_w, 5, f"✓  {point}", fill=True, padding=2)
        y_a_body = pdf.get_y() + 1
    y_after_a = y_a_body

    # B の強み（同じ高さから描画）
    pdf.set_fill_color(*LIGHT)
    pdf.set_font(pdf._font, "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.rect(x_b, y_start, col_w, 7, style="F")
    pdf.set_xy(x_b + 2, y_start + 1)
    pdf.cell(col_w - 4, 5, "バージョン B の強み")
    y_b_body = y_start + 8
    pdf.set_text_color(0, 0, 0)
    for point in ab_report.get("b_strengths", []):
        pdf.set_xy(x_b, y_b_body)
        pdf.set_fill_color(*GREEN_BG)
        pdf.set_text_color(*GREEN_T)
        pdf.set_font(pdf._font, "", 8.5)
        pdf.multi_cell(col_w, 5, f"✓  {point}", fill=True, padding=2)
        y_b_body = pdf.get_y() + 1
    y_after_b = y_b_body

    pdf.set_y(max(y_after_a, y_after_b) + 4)
    pdf.set_text_color(0, 0, 0)

    # 良いとこどり
    pdf.section_bar("両方の良いとこどり — 最強バージョンの方向性")
    pdf.colored_block(ab_report.get("best_of_both", ""), AMBER_BG, AMBER_T)
    pdf.ln(2)

    # 最重要改善
    pdf.section_bar("今すぐやるべき最重要改善")
    pdf.set_fill_color(*AMBER_BG)
    pdf.set_draw_color(*AMBER_T)
    pdf.set_text_color(*AMBER_T)
    pdf.set_font(pdf._font, "B", 10)
    pdf.set_x(lm)
    pdf.multi_cell(180, 6, ab_report.get("priority_action", ""), fill=True, border=1, padding=(3, 4, 3, 4))
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # DRM分析
    ab_mi = ab_report.get("marketing_insights")
    if ab_mi:
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.drm_section(ab_mi)

    # ペルソナ
    if pdf.get_y() > 210:
        pdf.add_page()
    pdf.persona_table(personas, reactions_a, mode)

    pdf.cta_footer()
    return bytes(pdf.output())


# ─────────────────────────────────────────────────────────
# サイト全体分析 PDF（高級ホテル調デザイン）
# ─────────────────────────────────────────────────────────

class _SitePDF(_Base):
    """Four Seasons / Aman Tokyo スタイルの高級感あるサイト分析PDF。"""

    def __init__(self):
        super().__init__()
        self._accent = GOLD  # DRM説明ボックスなどをゴールドに

    def header(self):
        if self.page_no() == 1:
            return  # カバーページは自前で描画
        # 黒ヘッダー背景
        self.set_fill_color(*NAVY_DARK)
        self.rect(0, 0, 210, 28, style="F")
        # ゴールド極細ライン（ヘッダー下）
        self.set_fill_color(*GOLD)
        self.rect(0, 28, 210, 0.3, style="F")

        # ロゴ（左端に小さく配置）
        if os.path.exists(_LOGO_PATH):
            self.image(_to_rgb_path(_LOGO_PATH, bg=(8,8,8)), x=4, y=2, w=22)

        # テキストを全幅（210mm）中央揃え
        self.set_xy(0, 5)
        self.set_font(self._font, "", 6.5)
        self.set_text_color(*GOLD)
        self.cell(210, 4.5, "LIFE DESIGN LAB  ·  TODOKU", align="C")
        self.set_xy(0, 12)
        self.set_font(self._font, "B", 10.5)
        self.set_text_color(*WHITE)
        self.cell(210, 6, "サイト全体分析レポート", align="C")
        self.ln(18)
        self.set_text_color(0, 0, 0)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*GOLD)
        self.rect(0, 293, 210, 1.5, style="F")
        self.set_y(-14)
        self.set_font(self._font, "", 7.5)
        self.set_text_color(*GRAY)
        self.cell(
            0, 10,
            f"© LIFE DESIGN LAB  ·  {datetime.now().strftime('%Y年%m月%d日')}"
            f"  ·  {self.page_no()} / {{nb}} ページ",
            align="C",
        )
        self.set_text_color(0, 0, 0)

    def section_bar(self, text: str):
        """黒背景+ゴールドアクセントのセクションヘッダー。"""
        lm = self.l_margin
        y = self.get_y()
        bar_h = 12
        # ヘッダー背景（温かみのあるダーク）
        self.set_fill_color(42, 36, 22)
        self.rect(lm, y, 180, bar_h, style="F")
        # ゴールド上ライン
        self.set_fill_color(*GOLD)
        self.rect(lm, y, 180, 0.8, style="F")
        # ゴールド縦バー（左アクセント）
        self.rect(lm, y, 3.5, bar_h, style="F")
        # セクションタイトル
        self.set_xy(lm + 8, y + 2.5)
        self.set_font(self._font, "B", 9.5)
        self.set_text_color(*WHITE)
        self.cell(155, 7, text)
        # ◆ 右端
        self.set_xy(lm + 158, y + 2.5)
        self.set_font(self._font, "", 8)
        self.set_text_color(*GOLD)
        self.cell(22, 7, "◆", align="R")
        # 下ライン
        self.set_fill_color(*GOLD)
        self.rect(lm, y + bar_h, 180, 0.3, style="F")
        self.ln(16)
        self.set_text_color(0, 0, 0)

    def _fill_page_bottom(self):
        """p.2〜p.5 下部: 余白があればゴールドラインとブランド名のみ（シンプル）。"""
        remaining = 297 - self.get_y() - 22
        if remaining < 12:
            return
        lm = self.l_margin
        y = self.get_y() + max(6, remaining * 0.45)
        self.set_fill_color(*GOLD)
        self.rect(0, y, 210, 0.3, style="F")
        self.set_xy(0, y + 3)
        self.set_font(self._font, "", 6.5)
        self.set_text_color(140, 128, 88)
        self.cell(210, 4, "LIFE DESIGN LAB  ·  TODOKU  ·  サイト改善支援サービス", align="C")
        self.set_text_color(0, 0, 0)

    def guide_page(self):
        """各スコア・指標の見方を解説するガイドページ（1ページ収録）。"""
        self.add_page()
        lm = self.l_margin
        self.section_bar("このレポートの見方 — 各指標・スコアガイド")

        guides = [
            (
                "推定問い合わせ率",
                "仮想顧客10人が「問い合わせする・しない・迷う」を判定した割合。15%以上=高水準 / 8〜14%=標準 / 7%以下=要改善",
                (22, 120, 60),
            ),
            (
                "AI 総合パワースコア（/100）",
                "DRM(30点)+BrandZ(40点)+GEO(30点)を統合した総合点。80点以上=広告投下タイミング / 60〜79=改善で伸びる / 59以下=要見直し",
                (180, 140, 20),
            ),
            (
                "DRMスコア（A〜D）",
                "集客→教育→販売の導線設計の評価。A=すべて機能 / B=1〜2か所改善で大幅アップ / C=構造問題あり / D=根本見直し",
                BLUE_MID,
            ),
            (
                "BrandZ 3軸スコア（各/10）",
                "意味性=悩みに応えているか / 差別性=競合と違うか / 顕著性=真っ先に思い出されるか。3軸揃ってブランドパワーになる",
                (100, 140, 80),
            ),
            (
                "GEO総合スコア（/10）",
                "ChatGPT・Gemini・ClaudeなどのAIに推薦・引用されやすいかの評価。7以上=AI引用されやすい / 3以下=AIに無視される状態",
                (80, 120, 180),
            ),
            (
                "GEO 5ステップ評価（各/5）",
                "S1構造化=数字・ファクト整理 / S2 How to=方法・手順コンテンツ / S3 Q&A=向いている人・いない人明記 / S4比較表=自社他社比較 / S5事例=数字入りビフォーアフター",
                (80, 120, 180),
            ),
            (
                "11項目チェックリスト（AI必須要素）",
                "①誰向け ②悩み解決 ③他社差 ④料金 ⑤対応エリア ⑥利用の流れ ⑦よくある質問 ⑧向いている人 ⑨向いていない人 ⑩お客様の声 ⑪事例 ⑫専門性の根拠。不足項目から順に追加するとAIに評価されやすくなる",
                (80, 120, 180),
            ),
        ]

        for title, body, accent in guides:
            y = self.get_y()
            card_h = 19 + max(1, -(-len(body) // 50)) * 4.2 + 2
            self.set_fill_color(248, 244, 234)
            self.rect(lm, y, 180, card_h, style="F")
            self.set_fill_color(*accent)
            self.rect(lm, y, 3, card_h, style="F")
            self.set_fill_color(*GOLD)
            self.rect(lm, y, 180, 0.5, style="F")
            self.set_xy(lm + 7, y + 2.5)
            self.set_font(self._font, "B", 8.5)
            self.set_text_color(42, 36, 22)
            self.cell(168, 5, title)
            self.set_fill_color(201, 169, 110)
            self.rect(lm + 3, y + 9.5, 177, 0.3, style="F")
            self.set_xy(lm + 7, y + 11.5)
            self.set_font(self._font, "", 7.5)
            self.set_text_color(22, 18, 10)
            self.set_auto_page_break(auto=False)
            self.multi_cell(170, 4.2, body)
            self.set_auto_page_break(auto=True, margin=22)
            self.set_y(y + card_h + 2)

        self.set_text_color(0, 0, 0)
        self._final_footer()

    def cover_page(self, site_url: str, profession: str, page_count: int):
        self.set_auto_page_break(auto=False)
        self.add_page()

        # ━━ ① 黒背景（最下レイヤー）━━
        self.set_fill_color(*NAVY_DARK)
        self.rect(0, 0, 210, 297, style="F")

        # ━━ ② テキスト（全幅中央揃え） ━━  ※キャラより先に描画
        logo_y = 36
        if os.path.exists(_LOGO_PATH):
            logo_size = 46
            self.image(_to_rgb_path(_LOGO_PATH, bg=(8,8,8)), x=105 - logo_size / 2, y=logo_y, w=logo_size)
            logo_y += logo_size + 6
        else:
            self.set_y(logo_y + 6)
            self.set_font(self._font, "B", 12)
            self.set_text_color(*GOLD)
            self.cell(210, 8, "LIFE DESIGN LAB", align="C")
            logo_y += 24

        # 区切りライン
        self.set_fill_color(*GOLD)
        self.rect(105 - 28, logo_y, 56, 0.2, style="F")
        logo_y += 8

        # メインタイトル
        self.set_xy(0, logo_y)
        self.set_font(self._font, "B", 24)
        self.set_text_color(*WHITE)
        self.cell(210, 14, "サイト全体分析レポート", align="C")
        self.ln(12)

        # 英語サブタイトル
        self.set_font(self._font, "", 9)
        self.set_text_color(*GOLD)
        self.cell(210, 6, "Website  Analysis  Report", align="C")
        self.ln(9)

        # 区切りライン
        self.set_fill_color(*GOLD)
        self.rect(105 - 28, self.get_y(), 56, 0.2, style="F")
        self.ln(9)

        # キャプション
        self.set_font(self._font, "", 7)
        self.set_text_color(155, 143, 96)
        self.cell(210, 5, "仮想顧客テスト  ·  Powered by Claude AI", align="C")

        # URLカード（全幅内）
        self.ln(14)
        bx, by = 14, self.get_y()
        bw, bh = 182, 36
        self.set_fill_color(18, 16, 12)
        self.rect(bx, by, bw, bh, style="F")
        self.set_fill_color(*GOLD)
        self.rect(bx, by, bw, 0.3, style="F")
        self.rect(bx, by + bh - 0.3, bw, 0.3, style="F")
        self.rect(bx, by, 1.5, bh, style="F")

        self.set_xy(bx + 6, by + 6)
        self.set_font(self._font, "", 6)
        self.set_text_color(*GOLD)
        self.cell(bw - 8, 4, "分析対象サイト")

        self.set_xy(bx + 6, by + 12)
        self.set_font(self._font, "B", 7.5)
        self.set_text_color(*WHITE)
        url_disp = site_url[:42] + ("…" if len(site_url) > 42 else "")
        self.cell(bw - 8, 5.5, url_disp)

        self.set_xy(bx + 6, by + 23)
        self.set_font(self._font, "", 6.5)
        self.set_text_color(155, 143, 96)
        self.cell(bw - 8, 5, f"ジャンル: {profession}  ·  {page_count}ページ収集")

        # 作成日
        self.set_y(by + bh + 9)
        self.set_font(self._font, "", 7)
        self.set_text_color(115, 105, 70)
        self.cell(210, 5, f"作成日:  {datetime.now().strftime('%Y年%m月%d日')}", align="C")

        # ━━ ③ キャラクター（URLカードの上・金枠の下） ━━
        if os.path.exists(_CHARACTER_PATH):
            try:
                char_path = _make_cover_char(_CHARACTER_PATH, bg=(8, 8, 8), fade_frac=0.45)
                img = _PILImage.open(char_path)
                char_h = 170  # ホワイトボードが見える高さ
                char_w = round(char_h * img.width / img.height, 1)
                self.image(char_path, x=210 - char_w, y=297 - char_h, w=char_w, h=char_h)
            except Exception:
                pass

        # ━━ ④ ゴールドフレーム（最上レイヤー・キャラの上に重ねる） ━━
        self.set_draw_color(*GOLD)
        self.set_line_width(0.4)
        self.rect(4, 4, 202, 289)
        for cx, cy in [(4, 4), (206, 4), (4, 293), (206, 293)]:
            self.set_xy(cx - 1.5, cy - 1.5)
            self.set_font(self._font, "", 4.5)
            self.set_text_color(*GOLD)
            self.cell(3, 3, "●", align="C")

        # 注意書き
        self.set_xy(0, 287)
        self.set_font(self._font, "", 6)
        self.set_text_color(88, 80, 54)
        self.cell(210, 4, "本レポートはトドク（LIFE DESIGN LAB）が作成したものです。", align="C")


def generate_site_pdf(
    site_report: dict,
    scraped_pages: list,
    profession: str,
    device_label: str = "💻 パソコン",
    site_url: str = "",
) -> bytes:
    """サイト全体分析レポートのPDF（高級ホテル調デザイン）。"""
    pdf = _SitePDF()
    lm = pdf.l_margin

    pdf.cover_page(site_url, profession, len(scraped_pages))
    pdf.set_auto_page_break(auto=True, margin=22)  # カバー後に再有効化
    pdf.add_page()

    # ── メタ情報行（p.2〜共通） ──
    def _meta_bar(p):
        device_str = device_label.replace("💻 ", "PC").replace("📱 ", "スマホ")
        p.set_font(p._font, "", 7)
        p.set_text_color(*GRAY)
        p.set_x(lm)
        p.cell(0, 5, (
            f"分析日時: {datetime.now().strftime('%Y年%m月%d日  %H:%M')}"
            f"  ｜  ジャンル: {profession}"
            f"  ｜  収集ページ数: {len(scraped_pages)}ページ"
            f"  ｜  閲覧デバイス: {device_str}"
        ))
        p.ln(7)
        p.set_text_color(0, 0, 0)

    _meta_bar(pdf)

    # ─────────────────────────────────────────────
    # p.2  KPI ダッシュボード + 強み/弱み
    # ─────────────────────────────────────────────
    inquiry_rate = site_report.get("inquiry_rate", "—")
    overall      = site_report.get("overall_impression", "")

    try:
        rate_num = int(''.join(filter(str.isdigit, str(inquiry_rate))))
    except ValueError:
        rate_num = 0
    if rate_num >= 15:
        rate_color, rate_badge = GREEN_MID, "高水準"
    elif rate_num >= 8:
        rate_color, rate_badge = (217, 119, 6), "標準"
    else:
        rate_color, rate_badge = (185, 28, 28), "要改善"

    # ── KPI ヒーロー ──
    y0 = pdf.get_y()
    hero_h = 38
    pdf.set_fill_color(*rate_color)
    pdf.rect(lm, y0, 180, 1.5, style="F")
    # 左: 第一印象
    left_w = 112
    pdf.set_fill_color(244, 241, 233)
    pdf.rect(lm, y0 + 1.5, left_w, hero_h - 1.5, style="F")
    pdf.set_fill_color(*GOLD)
    pdf.rect(lm, y0 + 1.5, 3, hero_h - 1.5, style="F")
    pdf.set_xy(lm + 8, y0 + 6)
    pdf.set_font(pdf._font, "", 7)
    pdf.set_text_color(140, 128, 90)
    pdf.cell(100, 4.5, "サイト全体の第一印象")
    pdf.set_xy(lm + 8, y0 + 12)
    pdf.set_font(pdf._font, "", 9)
    pdf.set_text_color(22, 18, 10)
    pdf.multi_cell(100, 5.5, overall[:120])
    # 右: KPI
    rx, rw = lm + left_w + 4, 64
    pdf.set_fill_color(42, 36, 22)
    pdf.rect(rx, y0 + 1.5, rw, hero_h - 1.5, style="F")
    pdf.set_fill_color(*rate_color)
    pdf.rect(rx, y0 + 1.5, rw, 1.5, style="F")
    pdf.set_xy(rx, y0 + 6)
    pdf.set_font(pdf._font, "", 7)
    pdf.set_text_color(160, 148, 100)
    pdf.cell(rw, 4.5, "推定問い合わせ率", align="C")
    pdf.set_xy(rx, y0 + 12)
    pdf.set_font(pdf._font, "B", 26)
    pdf.set_text_color(*rate_color)
    pdf.cell(rw, 13, str(inquiry_rate), align="C")
    gy = y0 + 27
    bw_g = rw - 16
    fill_w = min(rate_num / 25.0, 1.0) * bw_g
    pdf.set_fill_color(35, 32, 25)
    pdf.rect(rx + 8, gy, bw_g, 3, style="F")
    if fill_w > 0:
        pdf.set_fill_color(*rate_color)
        pdf.rect(rx + 8, gy, fill_w, 3, style="F")
    pdf.set_xy(rx, gy + 4.5)
    pdf.set_font(pdf._font, "B", 7)
    pdf.set_text_color(*rate_color)
    pdf.cell(rw, 4, rate_badge, align="C")

    pdf.set_y(y0 + hero_h + 6)
    pdf.set_text_color(0, 0, 0)

    # ── AI 総合パワースコア ──
    total_ps, drm_pts, bz_pts, geo_pts = _calc_power_score(site_report)
    ps_color = GREEN_MID if total_ps >= 70 else ((217, 119, 6) if total_ps >= 50 else (185, 28, 28))
    y_ps = pdf.get_y()
    pdf.set_fill_color(42, 36, 22)
    pdf.rect(lm, y_ps, 180, 16, style="F")
    pdf.set_fill_color(*ps_color)
    pdf.rect(lm, y_ps, 180, 0.8, style="F")
    pdf.set_xy(lm + 6, y_ps + 2.5)
    pdf.set_font(pdf._font, "", 7)
    pdf.set_text_color(160, 148, 100)
    pdf.cell(50, 4, "AI 総合パワースコア")
    pdf.set_xy(lm + 6, y_ps + 7)
    pdf.set_font(pdf._font, "B", 15)
    pdf.set_text_color(*ps_color)
    pdf.cell(20, 7, f"{total_ps}")
    pdf.set_font(pdf._font, "", 8)
    pdf.set_text_color(160, 148, 100)
    pdf.cell(18, 7, "/ 100")
    x_sub = lm + 80
    for sub_l, sub_v in [("DRM", f"{drm_pts}/30"), ("BrandZ", f"{bz_pts}/40"), ("GEO", f"{geo_pts}/30")]:
        pdf.set_xy(x_sub, y_ps + 3)
        pdf.set_font(pdf._font, "", 6.5)
        pdf.set_text_color(140, 128, 90)
        pdf.cell(30, 4, sub_l, align="C")
        pdf.set_xy(x_sub, y_ps + 8)
        pdf.set_font(pdf._font, "B", 9)
        pdf.set_text_color(*GOLD)
        pdf.cell(30, 5.5, sub_v, align="C")
        x_sub += 32
    pdf.set_y(y_ps + 20)
    pdf.set_text_color(0, 0, 0)

    # ── 強み / 弱み ──
    pdf.section_bar("強み・弱み分析")
    col_w = 87
    y_sw = pdf.get_y()

    strengths = site_report.get("strengths", [])
    pdf.set_fill_color(232, 250, 240)
    pdf.set_font(pdf._font, "B", 8.5)
    pdf.set_text_color(*GREEN_T)
    pdf.rect(lm, y_sw, col_w, 8, style="F")
    pdf.set_xy(lm + 5, y_sw + 2)
    pdf.cell(col_w - 8, 4.5, "◆  強み")
    y_s = y_sw + 10
    for s in strengths:
        txt = f"◆ {s.get('point', '')}\n   {s.get('reason', '')}"
        pdf.set_xy(lm, y_s)
        pdf.set_fill_color(240, 253, 247)
        pdf.set_text_color(*GREEN_T)
        pdf.set_font(pdf._font, "", 8)
        pdf.multi_cell(col_w, 5, txt, fill=True, padding=(3, 4, 3, 4))
        y_s = pdf.get_y() + 3
    y_after_s = y_s

    weaknesses = site_report.get("weaknesses", [])
    wx = lm + col_w + 6
    pdf.set_fill_color(255, 236, 232)
    pdf.set_font(pdf._font, "B", 8.5)
    pdf.set_text_color(*RED_T)
    pdf.rect(wx, y_sw, col_w, 8, style="F")
    pdf.set_xy(wx + 5, y_sw + 2)
    pdf.cell(col_w - 8, 4.5, "▲  弱み・改善点")
    y_w = y_sw + 10
    for w in weaknesses:
        txt = f"▲ {w.get('point', '')}\n   {w.get('reason', '')}"
        if w.get("suggestion"):
            txt += f"\n   → {w.get('suggestion', '')}"
        pdf.set_xy(wx, y_w)
        pdf.set_fill_color(255, 245, 243)
        pdf.set_text_color(*RED_T)
        pdf.set_font(pdf._font, "", 8)
        pdf.multi_cell(col_w, 5, txt, fill=True, padding=(3, 4, 3, 4))
        y_w = pdf.get_y() + 3
    y_after_w = y_w

    pdf.set_y(max(y_after_s, y_after_w) + 6)
    pdf.set_text_color(0, 0, 0)
    pdf._fill_page_bottom()

    # ─────────────────────────────────────────────
    # p.3  導線問題 + あると効果的なページ
    # ─────────────────────────────────────────────
    pdf.add_page()
    _meta_bar(pdf)

    nav_issues = site_report.get("navigation_issues", [])
    if nav_issues:
        pdf.section_bar("導線・ナビゲーションの問題")
        for ni in nav_issues:
            issue_text = ni.get("issue", "")
            suggestion_text = ni.get("suggestion", "")
            page_name = ni.get("page", "")
            # カード高さを事前計算
            _i_lines = max(1, -(-len(issue_text) // 36))
            _s_lines = max(1, -(-len(suggestion_text) // 40))
            _card_h = 7 + _i_lines * 5.5 + 6 + _s_lines * 5.5 + 8
            if (297 - pdf.get_y() - 22) < _card_h + 4:
                pdf.add_page()
                _meta_bar(pdf)
            y_ni = pdf.get_y()
            # ページ名バッジ（全幅）
            pdf.set_fill_color(42, 36, 22)
            pdf.rect(lm, y_ni, 180, 7, style="F")
            pdf.set_fill_color(*GOLD)
            pdf.rect(lm, y_ni, 3.5, 7, style="F")
            pdf.set_xy(lm + 8, y_ni + 1.5)
            pdf.set_font(pdf._font, "B", 8)
            pdf.set_text_color(*GOLD)
            pdf.cell(168, 4, page_name[:35])
            # 問題テキスト（折り返し対応）
            pdf.set_xy(lm, y_ni + 8)
            pdf.set_font(pdf._font, "B", 8.5)
            pdf.set_text_color(*RED_T)
            pdf.set_fill_color(255, 245, 245)
            pdf.multi_cell(180, 5.5, issue_text, fill=True, padding=(2, 4, 2, 4))
            # 改善提案ボックス（折り返し対応）
            pdf.set_xy(lm, pdf.get_y() + 2)
            pdf.set_fill_color(248, 244, 234)
            pdf.set_font(pdf._font, "", 8)
            pdf.set_text_color(22, 18, 10)
            pdf.multi_cell(180, 5.5, f"→ 改善提案: {suggestion_text}", fill=True, padding=(2, 4, 2, 8))
            pdf.set_y(pdf.get_y() + 5)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    missing = site_report.get("missing_pages", [])
    if missing:
        if (297 - pdf.get_y() - 22) < 40:
            pdf.add_page()
            _meta_bar(pdf)
        pdf.section_bar("あると効果的なページ（現在なし）")
        for m in missing[:6]:
            _m_lines = max(1, -(-len(m) // 46))
            _m_h = max(13, _m_lines * 5.5 + 8)
            if (297 - pdf.get_y() - 22) < _m_h + 5:
                pdf.add_page()
                _meta_bar(pdf)
            y_m = pdf.get_y()
            pdf.set_fill_color(248, 244, 234)
            pdf.rect(lm, y_m, 180, _m_h, style="F")
            pdf.set_fill_color(*GOLD)
            pdf.rect(lm, y_m, 3, _m_h, style="F")
            pdf.set_xy(lm + 8, y_m + 4)
            pdf.set_font(pdf._font, "B", 9)
            pdf.set_text_color(22, 18, 10)
            pdf.multi_cell(168, 5.5, f"◆  {m}")
            pdf.set_y(y_m + _m_h + 3)
        pdf.set_text_color(0, 0, 0)

    pdf._fill_page_bottom()

    # ─────────────────────────────────────────────
    # p.4  最重要改善 + DRM概要
    # ─────────────────────────────────────────────
    pdf.add_page()
    _meta_bar(pdf)

    pdf.section_bar("今すぐやるべき最重要改善アクション")
    priority = site_report.get("priority_action", "")
    y_p = pdf.get_y()
    box_h = max(22, -(-len(priority) // 42) * 6 + 10)
    pdf.set_fill_color(248, 244, 234)
    pdf.rect(lm, y_p, 180, box_h, style="F")
    pdf.set_fill_color(*GOLD)
    pdf.rect(lm, y_p, 4, box_h, style="F")
    pdf.rect(lm, y_p, 180, 0.5, style="F")
    pdf.rect(lm, y_p + box_h - 0.5, 180, 0.5, style="F")
    pdf.set_xy(lm + 9, y_p + 5)
    pdf.set_font(pdf._font, "B", 9.5)
    pdf.set_text_color(42, 36, 22)
    pdf.multi_cell(167, 6.5, priority)
    pdf.set_y(y_p + box_h + 8)
    pdf.set_text_color(0, 0, 0)

    mi = site_report.get("marketing_insights")
    if mi:
        pdf.drm_overview(mi)

    pdf._fill_page_bottom()

    # ─────────────────────────────────────────────
    # p.5  DRM 4軸詳細
    # ─────────────────────────────────────────────
    if mi:
        pdf.add_page()
        _meta_bar(pdf)
        pdf.drm_axis(mi)
        pdf._fill_page_bottom()

    # ─────────────────────────────────────────────
    # p.6  BrandZ スコア
    # ─────────────────────────────────────────────
    bz = site_report.get("brandz_score")
    if bz:
        pdf.add_page()
        _meta_bar(pdf)
        pdf.brandz_section(bz)
        pdf._fill_page_bottom()

    # ─────────────────────────────────────────────
    # p.7  GEO スコア
    # ─────────────────────────────────────────────
    geo = site_report.get("geo_score")
    if geo:
        pdf.add_page()
        _meta_bar(pdf)
        pdf.geo_section(geo)
        pdf._fill_page_bottom()

    # ─────────────────────────────────────────────
    # p.8  収集ページ一覧
    # ─────────────────────────────────────────────
    pdf.add_page()
    _meta_bar(pdf)

    pdf.section_bar(f"収集したページ一覧（全 {len(scraped_pages)} ページ）")
    # 2列レイアウト
    col_pw = 86
    for i, page in enumerate(scraped_pages[:30]):
        col_x = lm if i % 2 == 0 else lm + col_pw + 8
        if i % 2 == 0:
            y_row_p = pdf.get_y()
        y_p2 = y_row_p
        title = page.get("title", "（タイトルなし）")[:24]
        url   = page.get("url", "")[:34]
        pdf.set_fill_color(244, 241, 233)
        pdf.rect(col_x, y_p2, col_pw, 11, style="F")
        pdf.set_fill_color(*GOLD)
        pdf.rect(col_x, y_p2, 2, 11, style="F")
        pdf.set_xy(col_x + 5, y_p2 + 1.5)
        pdf.set_font(pdf._font, "B", 7.5)
        pdf.set_text_color(22, 18, 10)
        pdf.cell(col_pw - 6, 4.5, f"{i+1}. {title}")
        pdf.set_xy(col_x + 5, y_p2 + 6.5)
        pdf.set_font(pdf._font, "", 6.5)
        pdf.set_text_color(*GRAY)
        pdf.cell(col_pw - 6, 4, url)
        if i % 2 == 1 or i == len(scraped_pages) - 1:
            pdf.set_y(y_p2 + 14)
    if len(scraped_pages) > 30:
        pdf.set_font(pdf._font, "", 7.5)
        pdf.set_text_color(*GRAY)
        pdf.set_x(lm)
        pdf.cell(0, 5, f"…他 {len(scraped_pages) - 30} ページ（合計 {len(scraped_pages)} ページ収集）")
        pdf.ln(5)
    pdf.set_text_color(0, 0, 0)

    # ─────────────────────────────────────────────
    # 最終ページ  各指標の見方ガイド
    # ─────────────────────────────────────────────
    pdf.guide_page()
    return bytes(pdf.output())
