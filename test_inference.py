
from app.db.session import SessionLocal
from app.expert_system.inference_engine import run_forward_chaining


db = SessionLocal()

try:
    # Simulasi fakta pasien
    fakta_pasien = {
        "DEMAM": 1,
        "RUAM": 1,
        "RUAM_MENYELURUH": 1,
        "BATUK": 1,
        "PILEK": 0,
        "MATA_MERAH": 0,
        "KOPLIK": 0,
        "DIARE": 0,
        "SESAK": 0,
        "KEJANG": 0,
        "PENURUNAN_KESADARAN": 0,
    }

    hasil = run_forward_chaining(
        db,
        fakta_pasien,
    )

    print("\nHASIL FORWARD CHAINING")

    print("Metode:", hasil["metode"])

    print("Jumlah aturan:", hasil["jumlah_aturan"])

    print(
        "Jumlah aturan aktif:",
        hasil["jumlah_aturan_aktif"],
    )

    print(
        "\nKategori:",
        hasil["screening_category_label"],
    )

    print("\nAturan yang aktif:")

    for rule in hasil["matched_rules"]:
        print(
            f"- {rule['id_aturan']}: "
            f"{rule['nama_aturan']}"
        )

    print(
        "\nClinical pattern:",
        hasil["clinical_measles_pattern"],
    )

    print(
        "Suspected pattern:",
        hasil["suspected_case_finding_pattern"],
    )

    print(
        "Safety alert:",
        hasil["safety_alert"],
    )

finally:
    db.close()
