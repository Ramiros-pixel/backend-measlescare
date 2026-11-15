
from sqlalchemy.orm import Session

from app.expert_system.knowledge_base import get_knowledge_base


# 1. EVALUASI KONDISI

def evaluate_condition(
    actual_value,
    operator: str,
    expected_value: str,
) -> bool:
    """
    Membandingkan fakta dengan nilai kondisi aturan.

    Operator yang didukung:
    =, >, <, >=, <=
    """

    if actual_value is None:
        return False

    # Coba konversi menjadi angka.
    try:
        actual = float(actual_value)
        expected = float(expected_value)

        numeric_comparison = True

    except (ValueError, TypeError):
        actual = str(actual_value).strip().lower()
        expected = str(expected_value).strip().lower()

        numeric_comparison = False

    if operator == "=":
        return actual == expected

    if not numeric_comparison:
        raise ValueError(
            f"Operator {operator} membutuhkan nilai numerik."
        )

    if operator == ">":
        return actual > expected

    if operator == "<":
        return actual < expected

    if operator == ">=":
        return actual >= expected

    if operator == "<=":
        return actual <= expected

    raise ValueError(
        f"Operator kondisi tidak dikenal: {operator}"
    )


# 2. FORWARD CHAINING

def run_forward_chaining(
    db: Session,
    facts: dict,
) -> dict:
    """
    Menjalankan Forward Chaining berdasarkan
    aturan yang tersimpan di database.

    Parameter:
        db    : SQLAlchemy database session
        facts : Dictionary fakta gejala pasien

    Contoh:
        {
            "DEMAM": 1,
            "RUAM": 1,
            "BATUK": 1,
            "PILEK": 0
        }
    """

    knowledge_base = get_knowledge_base(db)

    if not knowledge_base:
        raise ValueError(
            "Knowledge Base kosong. "
            "Jalankan seeder aturan pakar terlebih dahulu."
        )

    matched_rules = []
    evaluated_rules = []
    conclusions = set()

    # Evaluasi seluruh aturan.
    for rule in knowledge_base:

        conditions = rule["kondisi"]

        # Aturan tanpa detail tidak boleh aktif.
        if not conditions:
            continue

        all_conditions_met = True
        condition_results = []

        # Evaluasi setiap kondisi dalam satu aturan.
        for condition in conditions:

            kode = condition["kode_gejala"]

            actual_value = facts.get(kode)

            expected_value = condition["nilai_kondisi"]

            operator = condition["operator"]

            is_match = evaluate_condition(
                actual_value,
                operator,
                expected_value,
            )

            condition_results.append(
                {
                    "kode_gejala": kode,
                    "nilai_fakta": actual_value,
                    "operator": operator,
                    "nilai_kondisi": expected_value,
                    "terpenuhi": is_match,
                }
            )

            if not is_match:
                all_conditions_met = False

        rule_result = {
            "id_aturan": rule["id_aturan"],
            "nama_aturan": rule["nama_aturan"],
            "kesimpulan": rule["kesimpulan"],
            "keterangan": rule["keterangan"],
            "kondisi": condition_results,
            "aktif": all_conditions_met,
        }

        evaluated_rules.append(rule_result)

        # Jika seluruh kondisi terpenuhi,
        # aturan menghasilkan kesimpulan.
        if all_conditions_met:

            matched_rules.append(rule_result)

            conclusions.add(
                rule["kesimpulan"]
            )

    # 3. INTERPRETASI KESIMPULAN

    clinical_pattern = (
        "CLINICAL_MEASLES_PATTERN" in conclusions
    )

    suspected_pattern = (
        "SUSPECTED_CASE_FINDING_PATTERN" in conclusions
    )

    safety_alert = (
        "SAFETY_ALERT" in conclusions
    )

    if clinical_pattern and suspected_pattern:

        category = "CLINICAL_AND_SUSPECTED"

        category_label = (
            "Pola clinical dan suspected case-finding terpenuhi"
        )

    elif clinical_pattern:

        category = "CLINICAL_PATTERN_ONLY"

        category_label = (
            "Pola clinical measles terpenuhi"
        )

    elif suspected_pattern:

        category = "SUSPECTED_PATTERN_ONLY"

        category_label = (
            "Pola suspected case-finding terpenuhi"
        )

    else:

        category = "MAIN_PATTERN_NOT_MET"

        category_label = (
            "Pola gejala utama yang dimodelkan belum terpenuhi"
        )

    # Ambil kondisi tanda bahaya yang benar-benar aktif.
    active_safety_signs = []

    for rule in matched_rules:

        if rule["kesimpulan"] == "SAFETY_ALERT":

            for condition in rule["kondisi"]:

                if condition["terpenuhi"]:
                    active_safety_signs.append(
                        condition["kode_gejala"]
                    )

    # 4. OUTPUT INFERENCE ENGINE

    return {
        "metode": "Forward Chaining",

        "jumlah_aturan": len(knowledge_base),

        "jumlah_aturan_aktif": len(matched_rules),

        "evaluated_rules": evaluated_rules,

        "matched_rules": matched_rules,

        "conclusions": sorted(conclusions),

        "clinical_measles_pattern": clinical_pattern,

        "suspected_case_finding_pattern": suspected_pattern,

        "screening_category": category,

        "screening_category_label": category_label,

        "safety_alert": safety_alert,

        "active_safety_signs": active_safety_signs,

        "total_fakta": len(facts),
    }
