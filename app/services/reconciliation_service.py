"""
Clinical Evidence Reconciliation Engine (CERE) Service
MeaslesWatchAI - Huawei ICT Competition 2026–2027 | Innovation Track
Team: Inovexa

Research Foundations:
- Krones et al. (2025): Multimodal clinical fusion, multi-source evidence synthesis.
- Liu et al. (2023): Modality dropout / handling missing modalities gracefully with attention contrast.
- Le et al. (2025): Multimodal missing data completeness validation without negative assumptions.
- Helou et al. (2020): Clinical uncertainty taxonomies in AI decision support.
- Islam et al. (2026): Data-centric, robust, explainable multimodal deep learning for CDS.
- WHO (2022): Measles Outbreak Guide (clinical guidelines for measles suspect criteria).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.gejala import Camera, Gejala
from app.models.pakar import HasilPakar, JawabanGejala
from app.models.reconciliation import EvidenceReconciliation
from app.schemas.reconciliation import (
    EvidenceReconciliationEvaluateRequest,
    EvidenceValidationDetail,
    EvidenceValidationStatus,
    ReconciliationResponse,
    ReconciliationStatus,
)

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "Hasil evaluasi Clinical Evidence Reconciliation Engine (CERE) ini merupakan "
    "rekonsiliasi bukti klinis untuk skrining awal, bukan diagnosis medis definitif. "
    "Penentuan diagnosis dan penanganan tetap memerlukan pemeriksaan langsung "
    "oleh dokter atau tenaga medis profesional."
)

KNOWN_CV_CLASSES = {
    "Chickenpox",
    "Cowpox",
    "HFMD",
    "Healthy",
    "Measles",
    "Monkeypox",
}

RULE_VERSION = "CERE-v1.0"


def evaluate_clinical_evidence(
    db: Session,
    request: EvidenceReconciliationEvaluateRequest,
) -> ReconciliationResponse:
    """
    Mengevaluasi dan merekonsiliasi bukti klinis multimodal untuk satu pemeriksaan gejala (id_gejala).
    
    Langkah kerja:
    1. Pengambilan dan validasi bukti dari 3 modalitas:
       a. Sensor Suhu MLX90614 (dari tabel Gejala)
       b. Computer Vision MobileNetV3 (dari payload request atau tabel Camera)
       c. Sistem Pakar Forward Chaining / Decision Tree (dari tabel HasilPakar)
    2. Identifikasi bukti hilang/tidak lengkap (Le et al., 2025; Liu et al., 2023)
    3. Deteksi konflik antar modalitas (Helou et al., 2020; Islam et al., 2026)
    4. Deteksi konsistensi bukti klinis (Krones et al., 2025; WHO, 2022)
    5. Prioritas tanda bahaya (Safety Alert Override)
    6. Pembentukan rekomendasi dan penjelasan yang transparan
    7. Persistensi ke database (idempotent / upsert)
    """
    id_gejala = request.id_gejala

    # 1. Ambil data Gejala
    gejala = db.get(Gejala, id_gejala)
    if gejala is None:
        raise ValueError(f"Data pemeriksaan {id_gejala} tidak ditemukan")

    supporting_evidence: list[str] = []
    conflicting_evidence: list[str] = []
    missing_evidence: list[str] = []
    invalid_evidence: list[str] = []

    # -------------------------------------------------------------
    # A. Validasi Modalitas 1: Sensor Suhu Tubuh (MLX90614)
    # -------------------------------------------------------------
    measured_temp = gejala.Suhu
    temp_status = EvidenceValidationStatus.VALID

    if measured_temp is None:
        temp_status = EvidenceValidationStatus.MISSING
        missing_evidence.append("Data suhu tubuh sensor belum tercatat.")
    elif measured_temp < 30.0 or measured_temp > 45.0:
        temp_status = EvidenceValidationStatus.INVALID
        invalid_evidence.append(
            f"Nilai suhu tubuh ({measured_temp}°C) berada di luar batas biologis wajar (30.0°C - 45.0°C)."
        )
    else:
        temp_status = EvidenceValidationStatus.VALID

    is_fever = measured_temp is not None and measured_temp >= 37.8

    # -------------------------------------------------------------
    # B. Validasi Modalitas 2: Computer Vision (MobileNetV3)
    # -------------------------------------------------------------
    cv_prediction = request.cv_prediction
    cv_confidence = request.cv_confidence
    cv_status = EvidenceValidationStatus.VALID

    # Jika payload tidak menyediakan CV, cari rekaman Camera terkait
    if cv_prediction is None:
        camera_record = (
            db.query(Camera)
            .filter(Camera.id_gejala == id_gejala)
            .order_by(Camera.Tanggal.desc())
            .first()
        )
        if camera_record and camera_record.Status:
            cv_prediction = camera_record.Status
            cv_confidence = 0.85  # Default confidence jika hanya status tersimpan

    if cv_prediction is None:
        cv_status = EvidenceValidationStatus.MISSING
        missing_evidence.append("Hasil analisis citra ruam (Computer Vision) belum tersedia.")
    elif cv_prediction not in KNOWN_CV_CLASSES:
        cv_status = EvidenceValidationStatus.INVALID
        invalid_evidence.append(
            f"Kelas prediksi Computer Vision '{cv_prediction}' tidak dikenali oleh sistem."
        )
    elif cv_confidence is not None and (cv_confidence < 0.0 or cv_confidence > 1.0):
        cv_status = EvidenceValidationStatus.INVALID
        invalid_evidence.append(
            f"Nilai confidence CV ({cv_confidence}) tidak valid (harus antara 0.0 dan 1.0)."
        )
    else:
        cv_status = EvidenceValidationStatus.VALID

    # -------------------------------------------------------------
    # C. Validasi Modalitas 3: Sistem Pakar (Forward Chaining & Decision Tree)
    # -------------------------------------------------------------
    hasil_pakar = (
        db.query(HasilPakar)
        .filter(HasilPakar.id_gejala == id_gejala)
        .first()
    )
    expert_status = EvidenceValidationStatus.VALID
    expert_category: str | None = None
    safety_alert: bool = False
    active_safety_signs: list[str] = []
    clinical_measles_pattern: bool = False
    suspected_case_finding_pattern: bool = False

    # Periksa juga jawaban kuesioner jika ada
    jawaban_rows = (
        db.query(JawabanGejala)
        .filter(JawabanGejala.id_gejala == id_gejala)
        .all()
    )
    facts_dict = {j.kode_gejala: j.nilai for j in jawaban_rows}
    reported_fever = facts_dict.get("DEMAM") == 1
    reported_rash = facts_dict.get("RUAM") == 1

    if hasil_pakar is None:
        expert_status = EvidenceValidationStatus.MISSING
        missing_evidence.append("Evaluasi Sistem Pakar belum dijalankan untuk pemeriksaan ini.")
    else:
        try:
            ringkasan = json.loads(hasil_pakar.ringkasan or "{}")
            fc = ringkasan.get("forward_chaining", {})
            expert_category = fc.get("screening_category")
            safety_alert = bool(fc.get("safety_alert", False))
            active_safety_signs = fc.get("active_safety_signs", [])
            clinical_measles_pattern = bool(fc.get("clinical_measles_pattern", False))
            suspected_case_finding_pattern = bool(fc.get("suspected_case_finding_pattern", False))
            expert_status = EvidenceValidationStatus.VALID
        except Exception as e:
            logger.warning(f"Gagal membaca JSON ringkasan pakar {id_gejala}: {e}")
            expert_status = EvidenceValidationStatus.FAILED
            invalid_evidence.append("Format data hasil Sistem Pakar rusak atau tidak dapat diuraikan.")

    evidence_validation = EvidenceValidationDetail(
        computer_vision=cv_status,
        body_temperature=temp_status,
        expert_system=expert_status,
    )

    # -------------------------------------------------------------
    # D. Determinasi Status Rekonsiliasi (CERE Core Engine)
    # -------------------------------------------------------------
    reconciliation_status: ReconciliationStatus
    summary: str
    explanation_parts: list[str] = []
    recommended_action: str

    has_missing = any(
        s == EvidenceValidationStatus.MISSING
        for s in (cv_status, temp_status, expert_status)
    )
    has_invalid_or_failed = any(
        s in (EvidenceValidationStatus.INVALID, EvidenceValidationStatus.FAILED)
        for s in (cv_status, temp_status, expert_status)
    )

    # 1. Pengecekan Kelengkapan (Le et al., 2025; Liu et al., 2023)
    if has_missing or has_invalid_or_failed:
        reconciliation_status = ReconciliationStatus.INCOMPLETE
        summary = "Bukti klinis belum lengkap atau terdapat modalitas yang tidak valid."
        explanation_parts.append(
            "Sistem mendeteksi bahwa tidak semua modalitas pemeriksaan (kamera ruam, sensor suhu, kuesioner pakar) "
            "berhasil dikumpulkan secara lengkap dan valid. Sesuai prinsip data-centric CDS, sistem tidak mengasumsikan "
            "modalitas yang hilang sebagai hasil negatif (Le et al., 2025)."
        )
        if missing_evidence:
            explanation_parts.append("Modalitas belum lengkap: " + "; ".join(missing_evidence))
        if invalid_evidence:
            explanation_parts.append("Modalitas tidak valid: " + "; ".join(invalid_evidence))

        if safety_alert:
            recommended_action = (
                "PERHATIAN KHUSUS: Meskipun modalitas belum lengkap, sistem mendeteksi TANDA BAHAYA "
                f"({', '.join(active_safety_signs) if active_safety_signs else 'gejala kritis'}). "
                "Segera rujuk pasien ke instalasi gawat darurat (IGD) atau konsultasikan ke dokter jaga tanpa menunda!"
            )
        else:
            recommended_action = (
                "Lengkapi modalitas pemeriksaan yang belum lengkap (foto ruam kulit / pengukuran suhu / kuesioner) "
                "atau lakukan evaluasi pemeriksaan fisik manual oleh petugas kesehatan."
            )

    else:
        # Seluruh modalitas VALID. Evaluasi Konflik vs Konsistensi
        is_expert_measles = clinical_measles_pattern or suspected_case_finding_pattern
        is_cv_measles = cv_prediction == "Measles" and (cv_confidence is None or cv_confidence >= 0.50)
        is_cv_healthy = cv_prediction == "Healthy" and (cv_confidence is None or cv_confidence >= 0.60)
        is_cv_other_rash = cv_prediction in {"Chickenpox", "Cowpox", "HFMD", "Monkeypox"}

        # Konflik 1: Suhu sensor vs Laporan kuesioner
        if is_fever and not reported_fever:
            conflicting_evidence.append(
                f"Sensor mencatat suhu tinggi ({measured_temp}°C), tetapi kuesioner menyatakan tidak ada demam."
            )
        elif not is_fever and reported_fever and measured_temp is not None and measured_temp < 37.0:
            conflicting_evidence.append(
                f"Kuesioner melaporkan adanya riwayat demam, tetapi sensor suhu saat ini normal ({measured_temp}°C). "
                "Kemungkinan pasien telah meminum antipiretik atau demam bersifat intermiten."
            )

        # Konflik 2: CV menyatakan Measles, tetapi Sistem Pakar menyatakan pola utama tidak terpenuhi
        if is_cv_measles and not is_expert_measles:
            conflicting_evidence.append(
                f"Computer Vision mendeteksi pola ruam Campak (confidence: {(cv_confidence or 0)*100:.1f}%), "
                "namun riwayat gejala kuesioner tidak memenuhi kriteria klinis campak WHO (tidak ada demam/3C)."
            )

        # Konflik 3: CV menyatakan Kulit Sehat / Normal, tetapi kuesioner melaporkan ruam menyeluruh & pola campak
        if is_cv_healthy and is_expert_measles and reported_rash:
            conflicting_evidence.append(
                f"Computer Vision memprediksi kulit normal (Healthy, confidence: {(cv_confidence or 0)*100:.1f}%), "
                "tetapi riwayat gejala pasien memenuhi pola klinis campak dengan ruam aktif."
            )

        # Konflik 4: CV memprediksi ruam lain (mis. HFMD/Chickenpox) dengan confidence tinggi, namun Pakar sangat mengarah ke campak
        if is_cv_other_rash and clinical_measles_pattern and cv_confidence and cv_confidence >= 0.70:
            conflicting_evidence.append(
                f"Computer Vision mengindikasikan ruam banding ({cv_prediction}, confidence: {cv_confidence*100:.1f}%), "
                "sementara pola trias kataral campak (3C) dan demam terpenuhi pada sistem pakar."
            )

        # Evaluasi akhir Konsisten vs Konflik
        if len(conflicting_evidence) > 0 and (is_cv_measles != is_expert_measles or (is_cv_healthy and reported_rash)):
            reconciliation_status = ReconciliationStatus.CONFLICTING
            summary = "Terdapat ketidaksesuaian (inkonsistensi) antara bukti citra visual dan riwayat klinis."
            explanation_parts.append(
                "Sistem mendeteksi adanya divergensi bukti klinis antar-modalitas (Helou et al., 2020; Islam et al., 2026). "
                "Hal ini umum terjadi pada stadium awal erupsi campak, pencahayaan foto yang kurang optimal, "
                "atau presentasi klinis atipikal yang memerlukan verifikasi tenaga medis."
            )
            for c in conflicting_evidence:
                explanation_parts.append(f"• {c}")

            if safety_alert:
                recommended_action = (
                    "PERINGATAN TANDA BAHAYA: Ditemukan tanda kegawatan klinis "
                    f"({', '.join(active_safety_signs) if active_safety_signs else 'tanda bahaya aktif'}). "
                    "Segera lakukan pemeriksaan langsung dan stabilisasi oleh dokter, sampingkan ketidakpastian AI!"
                )
            else:
                recommended_action = (
                    "Lakukan pemeriksaan fisik langsung dan anamnesis ulang oleh petugas kesehatan/dokter. "
                    "Pertimbangkan pemeriksaan laboratorium penunjang jika kecurigaan klinis tetap ada."
                )

        else:
            # Bukti Konsisten!
            reconciliation_status = ReconciliationStatus.CONSISTENT

            if is_cv_measles and is_expert_measles:
                summary = "Seluruh modalitas secara konsisten mengindikasikan suspek campak (Measles Suspect)."
                supporting_evidence.append(
                    f"Computer Vision mendeteksi karakteristik ruam morbiliform campak (confidence: {(cv_confidence or 0)*100:.1f}%)."
                )
                supporting_evidence.append(
                    f"Sistem Pakar mengonfirmasi kriteria gejala suspek campak ({expert_category})."
                )
                if is_fever:
                    supporting_evidence.append(
                        f"Pengukuran suhu tubuh objektif mengonfirmasi demam ({measured_temp}°C)."
                    )

                explanation_parts.append(
                    "Sintesis multimodal menunjukkan konvergensi kuat antara karakteristik ruam visual, "
                    "temuan suhu objektif, dan riwayat klinis sesuai pedoman WHO (Krones et al., 2025)."
                )

                if safety_alert:
                    recommended_action = (
                        "KASUS SUSPEK DENGAN TANDA BAHAYA: Pasien memenuhi kriteria suspek campak dan memiliki tanda bahaya "
                        f"({', '.join(active_safety_signs) if active_safety_signs else 'gejala gawat'}). "
                        "Segera lakukan isolasi droplet dan rujuk darurat ke dokter/IGD untuk penanganan intensif!"
                    )
                else:
                    recommended_action = (
                        "Pasien teridentifikasi mengarah ke suspek campak. Segera lakukan isolasi sementara untuk mencegah penularan "
                        "dan arahkan ke ruang konsultasi dokter untuk pemeriksaan serologis/penanganan medis lebih lanjut."
                    )

            elif (is_cv_healthy or is_cv_other_rash) and not is_expert_measles:
                summary = "Seluruh modalitas konsisten tidak mengarah ke suspek campak."
                if cv_prediction == "Healthy":
                    supporting_evidence.append(
                        f"Computer Vision mendeteksi integritas kulit normal (Healthy, confidence: {(cv_confidence or 0)*100:.1f}%)."
                    )
                else:
                    supporting_evidence.append(
                        f"Computer Vision mendeteksi kemungkinan diagnosis banding: {cv_prediction} (confidence: {(cv_confidence or 0)*100:.1f}%)."
                    )

                supporting_evidence.append(
                    "Sistem Pakar mengonfirmasi bahwa pola gejala klinis utama campak tidak terpenuhi."
                )
                if not is_fever and measured_temp is not None:
                    supporting_evidence.append(
                        f"Suhu tubuh tercatat dalam rentang normal ({measured_temp}°C)."
                    )

                explanation_parts.append(
                    "Tidak ditemukan bukti konvergen yang mendukung infeksi campak pada ketiga modalitas pemeriksaan."
                )

                if safety_alert:
                    recommended_action = (
                        "Meskipun bukan mengarah ke campak, pasien mengalami TANDA BAHAYA "
                        f"({', '.join(active_safety_signs) if active_safety_signs else 'gejala kritis'}). "
                        "Segera periksakan pasien ke fasilitas gawat darurat!"
                    )
                else:
                    recommended_action = (
                        "Gejala saat ini belum memenuhi kriteria suspek campak. Sarankan pasien beristirahat dan "
                        "segera periksa ke fasilitas kesehatan bila muncul demam tinggi atau ruam baru."
                    )

            else:
                summary = "Modalitas pemeriksaan menunjukkan keselarasan umum non-spesifik."
                explanation_parts.append(
                    "Pola bukti yang terkumpul konsisten dengan kondisi klinis umum yang dievaluasi."
                )
                if safety_alert:
                    recommended_action = "Ditemukan tanda bahaya. Rujuk pasien untuk evaluasi dokter segera."
                else:
                    recommended_action = "Konsultasikan hasil dengan tenaga medis di fasilitas pelayanan kesehatan."

    explanation = "\n".join(explanation_parts)

    # -------------------------------------------------------------
    # E. Persistensi ke Database (Idempotent / Upsert)
    # -------------------------------------------------------------
    reconciliation_row = (
        db.query(EvidenceReconciliation)
        .filter(EvidenceReconciliation.id_gejala == id_gejala)
        .first()
    )

    if reconciliation_row is None:
        rec_id = str(uuid.uuid4())
        reconciliation_row = EvidenceReconciliation(
            id_reconciliation=rec_id,
            id_gejala=id_gejala,
            reconciliation_status=reconciliation_status.value,
            summary=summary,
            cv_status=cv_status.value,
            temp_status=temp_status.value,
            expert_status=expert_status.value,
            cv_prediction=cv_prediction,
            cv_confidence=cv_confidence,
            measured_temp=measured_temp,
            expert_category=expert_category,
            safety_alert=safety_alert,
            supporting_evidence=supporting_evidence,
            conflicting_evidence=conflicting_evidence,
            missing_evidence=missing_evidence,
            invalid_evidence=invalid_evidence,
            explanation=explanation,
            recommended_action=recommended_action,
            rule_version=RULE_VERSION,
            is_diagnosis=False,
        )
        db.add(reconciliation_row)
    else:
        reconciliation_row.reconciliation_status = reconciliation_status.value
        reconciliation_row.summary = summary
        reconciliation_row.cv_status = cv_status.value
        reconciliation_row.temp_status = temp_status.value
        reconciliation_row.expert_status = expert_status.value
        reconciliation_row.cv_prediction = cv_prediction
        reconciliation_row.cv_confidence = cv_confidence
        reconciliation_row.measured_temp = measured_temp
        reconciliation_row.expert_category = expert_category
        reconciliation_row.safety_alert = safety_alert
        reconciliation_row.supporting_evidence = supporting_evidence
        reconciliation_row.conflicting_evidence = conflicting_evidence
        reconciliation_row.missing_evidence = missing_evidence
        reconciliation_row.invalid_evidence = invalid_evidence
        reconciliation_row.explanation = explanation
        reconciliation_row.recommended_action = recommended_action
        reconciliation_row.rule_version = RULE_VERSION
        reconciliation_row.is_diagnosis = False

    db.commit()
    db.refresh(reconciliation_row)

    return ReconciliationResponse(
        id_reconciliation=reconciliation_row.id_reconciliation,
        id_gejala=reconciliation_row.id_gejala,
        reconciliation_status=reconciliation_status,
        summary=reconciliation_row.summary,
        evidence_validation=evidence_validation,
        cv_prediction=reconciliation_row.cv_prediction,
        cv_confidence=reconciliation_row.cv_confidence,
        measured_temp=reconciliation_row.measured_temp,
        expert_category=reconciliation_row.expert_category,
        safety_alert=reconciliation_row.safety_alert,
        supporting_evidence=supporting_evidence,
        conflicting_evidence=conflicting_evidence,
        missing_evidence=missing_evidence,
        invalid_evidence=invalid_evidence,
        explanation=reconciliation_row.explanation,
        recommended_action=reconciliation_row.recommended_action,
        rule_version=reconciliation_row.rule_version,
        is_diagnosis=False,
        disclaimer=DISCLAIMER_TEXT,
        created_at=reconciliation_row.created_at.isoformat() if reconciliation_row.created_at else None,
    )

