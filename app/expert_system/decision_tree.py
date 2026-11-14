# MEASLESCARE - DECISION TREE
# Node keputusan : C001 - C012
# Leaf keputusan : S001 - S014
# Branch          : Y (Yes) / N (No)

# Evaluasi:
# 1. Main symptom decision tree
# 2. Independent safety decision tree

# 1. KONFIGURASI NODE DAN LEAF
NODE_LABELS = {
    "C001": "Demam",
    "C002": "Ruam makulopapular",
    "C003": "Ruam menyeluruh",
    "C004": "Batuk",
    "C005": "Pilek",
    "C006": "Mata merah",
    "C007": "Batuk",
    "C008": "Pilek",
    "C009": "Mata merah",
    "C010": "Kesulitan bernapas",
    "C011": "Kejang",
    "C012": "Penurunan kesadaran",
}

LEAF_LABELS = {
    "S001": "Kriteria ruam tidak terpenuhi",
    "S002": "Kriteria demam tidak terpenuhi",
    "S003": "Suspected dan clinical pattern terpenuhi - batuk",
    "S004": "Suspected dan clinical pattern terpenuhi - pilek",
    "S005": "Suspected dan clinical pattern terpenuhi - mata merah",
    "S006": "Hanya suspected pattern terpenuhi",
    "S007": "Clinical pattern terpenuhi - batuk",
    "S008": "Clinical pattern terpenuhi - pilek",
    "S009": "Clinical pattern terpenuhi - mata merah",
    "S010": "Kedua pola utama tidak terpenuhi",
    "S011": "Tanda bahaya: kesulitan bernapas",
    "S012": "Tanda bahaya: kejang",
    "S013": "Tanda bahaya: penurunan kesadaran",
    "S014": "Tanda bahaya yang diperiksa tidak ditemukan",
}

REQUIRED_FACTS = [
    "DEMAM",
    "RUAM",
    "RUAM_MENYELURUH",
    "BATUK",
    "PILEK",
    "MATA_MERAH",
    "SESAK",
    "KEJANG",
    "PENURUNAN_KESADARAN",
]


# 2. VALIDASI FAKTA
def normalize_fact(value, kode_gejala):
    """
    Mengubah jawaban gejala menjadi boolean.

    Nilai yang diterima:
    1, 0, True, False, Y, N, YES, NO.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in (0, 1):
        return value == 1

    if isinstance(value, str):

        normalized = value.strip().upper()

        if normalized in ("1", "Y", "YES", "YA", "TRUE"):
            return True

        if normalized in ("0", "N", "NO", "TIDAK", "FALSE"):
            return False

    raise ValueError(
        f"Nilai gejala {kode_gejala} tidak valid: {value}"
    )


def validate_facts(facts):
    """
    Memastikan seluruh fakta yang dibutuhkan tersedia.
    Jawaban kosong tidak otomatis dianggap No.
    """

    missing = [
        kode
        for kode in REQUIRED_FACTS
        if kode not in facts or facts[kode] is None
    ]

    if missing:
        raise ValueError(
            "Fakta gejala belum lengkap: "
            + ", ".join(missing)
        )

    return {
        kode: normalize_fact(facts[kode], kode)
        for kode in REQUIRED_FACTS
    }


# 3. HELPER PENELUSURAN NODE
def create_decision(
    node_code,
    answer,
    next_node,
):
    """
    Membuat dokumentasi satu langkah keputusan.
    """

    return {
        "node": node_code,
        "pertanyaan": NODE_LABELS[node_code],
        "jawaban": "Y" if answer else "N",
        "hasil": "Ya" if answer else "Tidak",
        "next": next_node,
    }


# 4. MAIN SYMPTOM DECISION TREE

def evaluate_main_tree(facts):
    """
    Mengevaluasi pola utama gejala campak.

    Jalur:
    C001 -> C002 -> C003

    Jika ruam menyeluruh:
    C004 -> C005 -> C006

    Jika tidak menyeluruh:
    C007 -> C008 -> C009
    """

    path = []

    # C001: Demam?
    if not facts["DEMAM"]:

        path.append(
            create_decision("C001", False, "S002")
        )

        return {
            "leaf": "S002",
            "hasil": LEAF_LABELS["S002"],
            "clinical_pattern": False,
            "suspected_pattern": False,
            "path": path,
        }

    path.append(
        create_decision("C001", True, "C002")
    )

    # C002: Ruam makulopapular?
    if not facts["RUAM"]:

        path.append(
            create_decision("C002", False, "S001")
        )

        return {
            "leaf": "S001",
            "hasil": LEAF_LABELS["S001"],
            "clinical_pattern": False,
            "suspected_pattern": False,
            "path": path,
        }

    path.append(
        create_decision("C002", True, "C003")
    )

    # C003: Ruam menyeluruh?
    generalized = facts["RUAM_MENYELURUH"]

    path.append(
        create_decision(
            "C003",
            generalized,
            "C004" if generalized else "C007",
        )
    )

    # -------------------------------------------------
    # CABANG A: RUAM MENYELURUH
    # -------------------------------------------------

    if generalized:

        # C004: Batuk?
        if facts["BATUK"]:

            path.append(
                create_decision("C004", True, "S003")
            )

            leaf = "S003"

        else:

            path.append(
                create_decision("C004", False, "C005")
            )

            # C005: Pilek?
            if facts["PILEK"]:

                path.append(
                    create_decision("C005", True, "S004")
                )

                leaf = "S004"

            else:

                path.append(
                    create_decision("C005", False, "C006")
                )

                # C006: Mata merah?
                if facts["MATA_MERAH"]:

                    path.append(
                        create_decision("C006", True, "S005")
                    )

                    leaf = "S005"

                else:

                    path.append(
                        create_decision("C006", False, "S006")
                    )

                    leaf = "S006"

        clinical_pattern = leaf in (
            "S003",
            "S004",
            "S005",
        )

        suspected_pattern = True

    # -------------------------------------------------
    # CABANG B: RUAM TIDAK MENYELURUH
    # -------------------------------------------------

    else:

        # C007: Batuk?
        if facts["BATUK"]:

            path.append(
                create_decision("C007", True, "S007")
            )

            leaf = "S007"

        else:

            path.append(
                create_decision("C007", False, "C008")
            )

            # C008: Pilek?
            if facts["PILEK"]:

                path.append(
                    create_decision("C008", True, "S008")
                )

                leaf = "S008"

            else:

                path.append(
                    create_decision("C008", False, "C009")
                )

                # C009: Mata merah?
                if facts["MATA_MERAH"]:

                    path.append(
                        create_decision("C009", True, "S009")
                    )

                    leaf = "S009"

                else:

                    path.append(
                        create_decision("C009", False, "S010")
                    )

                    leaf = "S010"

        clinical_pattern = leaf in (
            "S007",
            "S008",
            "S009",
        )

        suspected_pattern = False

    return {
        "leaf": leaf,
        "hasil": LEAF_LABELS[leaf],
        "clinical_pattern": clinical_pattern,
        "suspected_pattern": suspected_pattern,
        "path": path,
    }


# 5. SAFETY DECISION TREE

def evaluate_safety_tree(facts):
    """
    Evaluasi tanda bahaya secara independen
    dari hasil pola utama.
    """

    path = []

    # C010: Kesulitan bernapas?
    if facts["SESAK"]:

        path.append(
            create_decision("C010", True, "S011")
        )

        leaf = "S011"

    else:

        path.append(
            create_decision("C010", False, "C011")
        )

        # C011: Kejang?
        if facts["KEJANG"]:

            path.append(
                create_decision("C011", True, "S012")
            )

            leaf = "S012"

        else:

            path.append(
                create_decision("C011", False, "C012")
            )

            # C012: Penurunan kesadaran?
            if facts["PENURUNAN_KESADARAN"]:

                path.append(
                    create_decision("C012", True, "S013")
                )

                leaf = "S013"

            else:

                path.append(
                    create_decision("C012", False, "S014")
                )

                leaf = "S014"

    return {
        "leaf": leaf,
        "hasil": LEAF_LABELS[leaf],
        "safety_alert": leaf != "S014",
        "path": path,
    }


# 6. MAIN DECISION TREE ENGINE

def run_decision_tree(facts):
    """
    Menjalankan seluruh evaluasi Decision Tree.

    Menghasilkan:
    - Hasil pola gejala utama
    - Hasil pemeriksaan tanda bahaya
    - Jalur keputusan Y/N
    - Leaf masing-masing cabang
    """

    normalized_facts = validate_facts(facts)

    main_result = evaluate_main_tree(normalized_facts)

    safety_result = evaluate_safety_tree(normalized_facts)

    return {
        "metode": "Decision Tree",

        "main_result": main_result,

        "safety_result": safety_result,

        "main_leaf": main_result["leaf"],

        "safety_leaf": safety_result["leaf"],

        "clinical_pattern": main_result["clinical_pattern"],

        "suspected_pattern": main_result["suspected_pattern"],

        "safety_alert": safety_result["safety_alert"],

        "decision_path": {
            "main": main_result["path"],
            "safety": safety_result["path"],
        },

        "summary": {
            "main": main_result["hasil"],
            "safety": safety_result["hasil"],
        },
    }
