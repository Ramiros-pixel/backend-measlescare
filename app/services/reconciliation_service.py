import json

from sqlalchemy.orm import Session

from app.models.gejala import Gejala
from app.models.pakar import HasilPakar, JawabanGejala


VALID_CV_CLASSES = {"Chickenpox", "Cowpox", "HFMD", "Healthy", "Measles", "Monkeypox"}


def evaluate_clinical_evidence(
    db: Session,
    id_gejala: str,
    cv_prediction: str | None,
    cv_confidence: float | None,
    cv_status: str | None,
    expert_category: str | None,
    safety_alert: bool | None,
) -> dict:
    examination = db.get(Gejala, id_gejala)
    if examination is None:
        raise LookupError("Data pemeriksaan tidak ditemukan.")

    temp = examination.Suhu
    if temp is None:
        temp_status = "MISSING"
    elif 30.0 <= temp <= 45.0:
        temp_status = "VALID"
    else:
        temp_status = "INVALID"

    expert_result = (
        db.query(HasilPakar).filter(HasilPakar.id_gejala == id_gejala).first()
    )
    expert_status = "VALID" if expert_result is not None else "MISSING"

    if expert_status == "VALID":
        try:
            ringkasan = json.loads(expert_result.ringkasan) if expert_result.ringkasan else {}
            fc = ringkasan.get("forward_chaining", {})
            expert_category = fc.get("screening_category") or expert_category
        except (json.JSONDecodeError, AttributeError):
            pass
        if expert_category is None:
            if expert_result.hasil:
                expert_category = "PATTERN_NOT_MET"

    answers = (
        db.query(JawabanGejala)
        .filter(JawabanGejala.id_gejala == id_gejala)
        .all()
    )
    answer_map = {row.kode_gejala: row.nilai for row in answers}
    subjective_fever = answer_map.get("DEMAM") == 1

    if cv_status:
        cv_status = cv_status.upper()
    elif cv_prediction is None:
        cv_status = "MISSING"
    elif cv_prediction not in VALID_CV_CLASSES:
        cv_status = "INVALID"
    elif cv_confidence is not None and not 0 <= cv_confidence <= 1:
        cv_status = "INVALID"
    else:
        cv_status = "VALID"

    supporting: list[str] = []
    conflicting: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []

    if temp_status == "MISSING":
        missing.append("Pengukuran suhu tubuh belum tersedia.")
    elif temp_status == "INVALID":
        invalid.append("Pengukuran suhu tubuh berada di luar rentang yang dapat diperiksa.")

    if cv_status == "MISSING":
        missing.append("Analisis foto ruam belum tersedia.")
    elif cv_status == "FAILED":
        missing.append("Analisis foto ruam belum berhasil diproses.")
    elif cv_status == "INVALID":
        invalid.append("Hasil analisis foto ruam tidak dapat diverifikasi.")

    if expert_status == "MISSING":
        missing.append("Evaluasi jawaban gejala belum tersedia.")

    if temp_status == "VALID":
        supporting.append("Pengukuran suhu tubuh dapat diperiksa.")
    if cv_status == "VALID":
        supporting.append("Hasil analisis foto ruam dapat diperiksa.")
    if expert_status == "VALID":
        supporting.append("Evaluasi jawaban gejala dapat diperiksa.")

    if temp_status == "VALID" and cv_status == "VALID" and expert_status == "VALID":
        has_fever = temp >= 37.8
        expert_support = expert_category in {"CLINICAL_AND_SUSPECTED", "CLINICAL_PATTERN_ONLY"}

        if cv_prediction == "Healthy" and not has_fever and not expert_support:
            status = "CONSISTENT"
            summary = "Hasil pemeriksaan yang tersedia saat ini relatif selaras dan belum mengarah pada tanda kuat campak."
            explanation = "Suhu tubuh berada dalam rentang yang tidak menunjukkan demam, foto kulit tidak menunjukkan pola yang diprediksi sebagai campak, dan jawaban gejala belum memenuhi pola yang diperhatikan."
        elif cv_prediction == "Measles" and has_fever and expert_support:
            status = "CONSISTENT"
            summary = "Beberapa hasil pemeriksaan saling mendukung dan perlu pemeriksaan lanjutan."
            explanation = "Suhu tubuh menunjukkan demam, analisis foto menemukan kemiripan dengan campak, dan jawaban gejala juga memberikan pola yang perlu diperhatikan."
        elif cv_prediction in {"Chickenpox", "Cowpox", "HFMD", "Monkeypox"} and not expert_support:
            status = "CONSISTENT"
            summary = "Hasil pemeriksaan yang tersedia relatif selaras dan perlu evaluasi diagnosis banding."
            explanation = "Hasil foto menunjukkan kemiripan dengan kelompok ruam lain dan jawaban gejala belum memenuhi pola campak."
        else:
            status = "CONFLICTING"
            summary = "Hasil pemeriksaan memberikan informasi yang belum sepenuhnya selaras."
            explanation = "Foto kulit, suhu tubuh, dan jawaban gejala memiliki informasi yang berbeda sehingga pemeriksaan langsung oleh tenaga kesehatan diperlukan."

        if cv_prediction == "Measles" and (not expert_support or not has_fever):
            conflicting.append("Analisis foto menunjukkan kemiripan campak, sementara suhu atau pola gejala tidak sepenuhnya mendukung.")
        if cv_prediction == "Healthy" and expert_support:
            conflicting.append("Analisis foto tidak menunjukkan pola campak, sementara jawaban gejala menunjukkan pola yang perlu diperhatikan.")
        if subjective_fever and temp_status == "VALID" and temp < 37.8:
            conflicting.append("Pasien melaporkan demam, sementara pengukuran suhu tidak mencapai ambang demam.")
    else:
        status = "INCOMPLETE"
        summary = "Beberapa informasi pemeriksaan belum tersedia atau belum dapat diverifikasi."
        explanation = "Hasil skrining belum dapat memberikan gambaran yang lengkap karena salah satu bukti pemeriksaan belum tersedia atau tidak valid."

    if safety_alert is None:
        safety_alert = False
        if expert_result:
            try:
                ringkasan = json.loads(expert_result.ringkasan) if expert_result.ringkasan else {}
                decision = ringkasan.get("decision_tree", {})
                safety_alert = bool(decision.get("safety_alert"))
            except (json.JSONDecodeError, AttributeError):
                pass

    if safety_alert:
        status = status
        recommended_action = "Segera arahkan pasien ke fasilitas pelayanan kesehatan darurat atau IGD. Tanda yang dilaporkan memerlukan penanganan segera dan tidak perlu ditunda untuk melengkapi skrining."
        if status == "CONSISTENT":
            status = "CONSISTENT"
    elif status == "CONFLICTING":
        recommended_action = "Konsultasikan kepada tenaga kesehatan untuk pemeriksaan langsung. Hasil foto kulit, suhu tubuh, dan jawaban gejala dapat dinilai kembali agar tidak disimpulkan sendiri oleh pasien."
    elif status == "INCOMPLETE":
        parts = []
        if temp_status != "VALID":
            parts.append("mengukur ulang suhu")
        if cv_status not in {"VALID"}:
            parts.append("mengambil foto ruam yang jelas kembali")
        if expert_status != "VALID":
            parts.append("melengkapi jawaban gejala")
        recommended_action = (
            "Lengkapi pemeriksaan dengan " + ", ".join(parts) + ", lalu meminta bantuan petugas kesehatan bila diperlukan."
            if parts
            else "Minta bantuan petugas untuk melengkapi pemeriksaan."
        )
    elif cv_prediction == "Measles":
        recommended_action = "Segera konsultasikan dengan tenaga kesehatan untuk pemeriksaan lanjutan. Batasi kontak dekat sementara bila dugaan penyakit menular dinilai relevan, tanpa menyimpulkan bahwa pasien pasti mengalami campak."
    else:
        recommended_action = "Pantau perubahan kondisi tubuh. Konsultasikan kepada tenaga kesehatan jika muncul ruam baru, demam, atau kondisi memburuk."

    return {
        "reconciliation_status": status,
        "summary": summary,
        "evidence_validation": {
            "computer_vision": cv_status,
            "body_temperature": temp_status,
            "expert_system": expert_status,
        },
        "cv_prediction": cv_prediction,
        "cv_confidence": cv_confidence,
        "measured_temp": temp,
        "expert_category": expert_category,
        "safety_alert": safety_alert,
        "supporting_evidence": supporting,
        "conflicting_evidence": conflicting,
        "missing_evidence": missing,
        "invalid_evidence": invalid,
        "explanation": explanation,
        "recommended_action": recommended_action,
    }
