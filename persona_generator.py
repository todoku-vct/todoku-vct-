import json
import random
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "data" / "persona_templates"

PROFESSION_MAP = {
    # 士業
    "行政書士": "gyoseishoshi",
    "税理士": "zeirishi",
    "社会保険労務士": "sharoushi",
    "弁護士": "bengoshi",
    "司法書士": "shihoshoshi",
    # その他業種
    "不動産業": "fudosan",
    "医療・クリニック": "iryo",
    # 無形商材
    "コーチング": "coaching",
    "コンサルティング": "consulting",
    "オンライン講座・スクール": "online_school",
    "物販スクール": "hanbai_school",
    "金融セミナー": "kinyu_seminar",
    # カスタム
    "カスタム（自由入力）": "custom",
}

PROFESSION_GROUPS = {
    "士業": ["行政書士", "税理士", "社会保険労務士", "弁護士", "司法書士"],
    "その他業種": ["不動産業", "医療・クリニック"],
    "無形商材": ["コーチング", "コンサルティング", "オンライン講座・スクール", "物販スクール", "金融セミナー"],
    "カスタム": ["カスタム（自由入力）"],
}


def load_template(profession: str) -> dict:
    filename = PROFESSION_MAP[profession]
    with open(TEMPLATE_DIR / f"{filename}.json", encoding="utf-8") as f:
        return json.load(f)


def _weighted_choice(items: list, weights: list) -> str:
    return random.choices(items, weights=weights, k=1)[0]


def generate_persona(profession: str, custom_label: str = "") -> dict:
    t = load_template(profession)

    # 年齢生成
    age_min, age_max = t["age_range"]
    age = random.randint(age_min, age_max)

    # 性別
    genders = list(t["gender_ratio"].keys())
    gender_weights = list(t["gender_ratio"].values())
    gender = _weighted_choice(genders, gender_weights)

    # 問題タイプ
    problem = random.choice(t["problems"])

    # ITリテラシー
    it_literacy = _weighted_choice(t["it_literacy"], t["it_weights"])

    # 価格感度
    price_sensitivity = _weighted_choice(
        t["price_sensitivity"], t["price_weights"]
    )

    # 緊急度
    urgency = _weighted_choice(t["urgency"], t["urgency_weights"])

    # 重視ポイント
    trust_factor = random.choice(t["trust_factors"])

    return {
        "profession": custom_label if custom_label else profession,
        "age": age,
        "gender": gender,
        "problem_type": problem["type"],
        "problem_detail": problem["detail"],
        "it_literacy": it_literacy,
        "price_sensitivity": price_sensitivity,
        "urgency": urgency,
        "trust_factor": trust_factor,
    }


def generate_personas(profession: str, count: int, custom_label: str = "") -> list[dict]:
    return [generate_persona(profession, custom_label=custom_label) for _ in range(count)]


def generate_custom_personas(custom_settings: dict, count: int) -> list[dict]:
    """UIで設定したカスタム属性からペルソナを生成する"""
    personas = []
    for _ in range(count):
        age_min, age_max = custom_settings["age_range"]
        age = random.randint(age_min, age_max)

        gender_ratio = custom_settings["gender_ratio"]
        gender = random.choices(
            list(gender_ratio.keys()), weights=list(gender_ratio.values()), k=1
        )[0]

        problem = random.choice(custom_settings["problems"]) if custom_settings.get("problems") else {
            "type": "サービスを検討中",
            "detail": custom_settings.get("problem_text", "このサービスに興味がある")
        }

        personas.append({
            "profession": custom_settings.get("profession", "カスタム"),
            "age": age,
            "gender": gender,
            "problem_type": problem["type"] if isinstance(problem, dict) else "検討中",
            "problem_detail": problem["detail"] if isinstance(problem, dict) else problem,
            "it_literacy": custom_settings.get("it_literacy", "普通（日常的にスマホ・PCを使う）"),
            "price_sensitivity": custom_settings.get("price_sensitivity", "普通（価値と価格のバランスを重視）"),
            "urgency": custom_settings.get("urgency", "中程度（近いうちに決めたい）"),
            "trust_factor": random.choice(custom_settings.get("trust_factors", ["信頼性・実績を重視"])),
        })
    return personas


def format_persona_label(p: dict) -> str:
    return f"{p['age']}歳 {p['gender']}・{p['problem_type']}"
