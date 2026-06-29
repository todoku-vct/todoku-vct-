import json
import os
import re
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

PROMPTS_DIR = Path(__file__).parent / "prompts"

FAST_MODEL = "claude-haiku-4-5-20251001"   # ペルソナ反応（安い・速い）
SMART_MODEL = "claude-sonnet-4-6"           # レポート生成（高品質・安定）


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _format_prompt(template: str, **kwargs) -> str:
    for key, value in kwargs.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def _extract_json(text: str) -> dict:
    try:
        match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
        if match:
            return json.loads(match.group(1))
        # ```なしのJSONを試みる
        return json.loads(text.strip())
    except (json.JSONDecodeError, AttributeError):
        # JSONとして解析できない場合は空の安全なデフォルトを返す
        return {"error": "レスポンスの解析に失敗しました", "raw": text[:200]}


def _call_claude(model: str, prompt: str, max_tokens: int) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
            else:
                raise RuntimeError("APIが混雑しています。しばらく待ってから再試行してください。") from None
        except anthropic.APIError as e:
            raise RuntimeError(f"Claude API エラー: {e}") from e


def get_persona_reaction(persona: dict, lp_text: str, mode: str = "lp") -> dict:
    prompt_file = "sns_reaction_prompt.txt" if mode == "sns" else "reaction_prompt.txt"
    prompt_template = _load_prompt(prompt_file)

    prompt = _format_prompt(
        prompt_template,
        age=persona["age"],
        gender=persona["gender"],
        problem_type=persona["problem_type"],
        problem_detail=persona["problem_detail"],
        it_literacy=persona["it_literacy"],
        price_sensitivity=persona["price_sensitivity"],
        urgency=persona["urgency"],
        trust_factor=persona["trust_factor"],
        profession=persona["profession"],
        lp_text=lp_text,
    )

    text = _call_claude(FAST_MODEL, prompt, max_tokens=512)
    return _extract_json(text)


def generate_report(personas: list[dict], reactions: list[dict], lp_text: str, mode: str = "lp") -> dict:
    prompt_file = "sns_report_prompt.txt" if mode == "sns" else "report_prompt.txt"
    prompt_template = _load_prompt(prompt_file)

    if mode == "sns":
        test_results_lines = []
        for i, (p, r) in enumerate(zip(personas, reactions), 1):
            line = (
                f"ユーザー{i}（{p['age']}歳 {p['gender']}・{p['problem_type']}）: "
                f"停止={r.get('will_stop_scrolling','?')} / "
                f"いいね={r.get('will_like','?')} / "
                f"プロフ訪問={r.get('will_visit_profile','?')} / "
                f"理由={r.get('reason','?')} / "
                f"目に留まった={r.get('caught_attention','?')} / "
                f"引っかかった={r.get('turn_off','?')}"
            )
            test_results_lines.append(line)
    else:
        test_results_lines = []
        for i, (p, r) in enumerate(zip(personas, reactions), 1):
            line = (
                f"ペルソナ{i}（{p['age']}歳 {p['gender']}・{p['problem_type']}）: "
                f"問い合わせ={r.get('will_inquire','?')} / "
                f"理由={r.get('reason','?')} / "
                f"良かった点={r.get('caught_attention','?')} / "
                f"不安点={r.get('concern','?')}"
            )
            test_results_lines.append(line)

    prompt = _format_prompt(
        prompt_template,
        lp_text=lp_text,
        test_results="\n".join(test_results_lines),
        persona_count=len(personas),
    )

    text = _call_claude(SMART_MODEL, prompt, max_tokens=1024)
    return _extract_json(text)


def generate_improved_copy(lp_text: str, report: dict, mode: str = "lp") -> str:
    weaknesses = report.get("weaknesses", [])
    weak_summary = "\n".join(
        f"- {w.get('point','')}: {w.get('suggestion','')}" for w in weaknesses
    )
    priority = report.get("priority_action", "")

    if mode == "sns":
        instruction = "SNS投稿文（X・Instagram）"
        goal = "スクロール停止率・いいね率・プロフィール訪問率を高める"
    else:
        instruction = "LP・ホームページのコピー文章"
        goal = "問い合わせ率を高める"

    prompt = f"""あなたは一流のセールスコピーライターです。
以下の{instruction}を、仮想顧客テストの結果に基づいて改善してください。

## 改善すべき問題点
{weak_summary}

## 最重要改善アクション
{priority}

## 改善目標
{goal}

## 元のテキスト
{lp_text}

## 指示
- 元のテキストの意図・サービス内容・トーンを維持しながら改善する
- 上記の問題点をすべて解消した改善版を書く
- 改善版のみを出力する（説明文・コメントは不要）
"""

    return _call_claude(SMART_MODEL, prompt, max_tokens=2000)


def analyze_site(pages: list[dict], profession: str, device: str = "pc", customer_profile: str = "") -> dict:
    prompt_template = _load_prompt("site_report_prompt.txt")

    pages_summary = "\n".join(f"・{p['title']}（{p['url']}）" for p in pages)
    pages_content = ""
    for p in pages:
        pages_content += f"\n\n=== {p['title']} ({p['url']}) ===\n{p['text']}"

    if device == "mobile":
        device_label = "スマートフォン（iPhone / Android）"
        device_note = "スマホユーザーとして評価してください。3秒以内に興味を持てなければ離脱します。縦スクロール前提、タップしやすさ、電話ボタンのワンタップ発信、文字サイズ、横スクロールが必要な表・料金表などに厳しく注目してください。"
    else:
        device_label = "パソコン（デスクトップ / ノートPC）"
        device_note = "PCユーザーとして評価してください。横幅を活かしたレイアウト、情報量、ナビゲーションのわかりやすさを重視してください。"

    if customer_profile:
        device_note += f"\n\n【対象顧客プロファイル】{customer_profile}\nこのプロファイルに合った顧客の視点でサイト全体を評価してください。"

    prompt = _format_prompt(
        prompt_template,
        profession=profession,
        device_label=device_label,
        device_note=device_note,
        pages_summary=pages_summary,
        pages_content=pages_content[:12000],
    )

    text = _call_claude(SMART_MODEL, prompt, max_tokens=6000)
    return _extract_json(text)


def generate_ab_report(
    personas: list[dict],
    reactions_a: list[dict],
    reactions_b: list[dict],
    text_a: str,
    text_b: str,
    mode: str = "lp",
) -> dict:
    prompt_template = _load_prompt("ab_report_prompt.txt")

    def summarize(reactions):
        lines = []
        for i, (p, r) in enumerate(zip(personas, reactions), 1):
            if mode == "sns":
                line = (
                    f"ユーザー{i}（{p['age']}歳 {p['gender']}）: "
                    f"停止={r.get('will_stop_scrolling','?')} / "
                    f"いいね={r.get('will_like','?')} / "
                    f"プロフ訪問={r.get('will_visit_profile','?')} / "
                    f"理由={r.get('reason','?')}"
                )
            else:
                line = (
                    f"ペルソナ{i}（{p['age']}歳 {p['gender']}）: "
                    f"問い合わせ={r.get('will_inquire','?')} / "
                    f"理由={r.get('reason','?')}"
                )
            lines.append(line)
        return "\n".join(lines)

    prompt = _format_prompt(
        prompt_template,
        text_a=text_a,
        text_b=text_b,
        results_a=summarize(reactions_a),
        results_b=summarize(reactions_b),
        persona_count=len(personas),
    )

    text = _call_claude(SMART_MODEL, prompt, max_tokens=1200)
    return _extract_json(text)


def generate_consultation_script(
    site_report: dict,
    site_url: str,
    profession: str,
    power_score: int,
) -> dict:
    """30分Zoom解説セッション用の台本をAIで生成する。"""
    prompt_template = _load_prompt("script_prompt.txt")
    prompt = _format_prompt(
        prompt_template,
        site_url=site_url,
        profession=profession,
        power_score=power_score,
        inquiry_rate=site_report.get("inquiry_rate", "不明"),
        drm_score=site_report.get("marketing_insights", {}).get("drm_score", "不明"),
        report_json=json.dumps(site_report, ensure_ascii=False, indent=2),
    )
    text = _call_claude(SMART_MODEL, prompt, max_tokens=8000)
    return _extract_json(text)
