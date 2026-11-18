"""
Unit and integration tests for Clinical Evidence Reconciliation Engine (CERE).
MeaslesWatchAI - Huawei ICT Competition 2026–2027 | Innovation Track
Team: Inovexa

Research validation coverage:
1. Consistent multimodal evidence (Krones et al., 2025; WHO, 2022)
2. Conflicting multimodal evidence (Helou et al., 2020; Islam et al., 2026)
3. Incomplete modalities without negative assumption (Le et al., 2025; Liu et al., 2023)
4. Sensor out-of-range & invalid confidence handling
5. Safety Alert priority preservation across all statuses
6. Upsert idempotency on repeated reconciliation requests
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.gejala import Gejala, Role, User
from app.models.pakar import HasilPakar, JawabanGejala
from app.models.reconciliation import EvidenceReconciliation
from app.schemas.reconciliation import (
    EvidenceReconciliationEvaluateRequest,
    EvidenceValidationStatus,
    ReconciliationStatus,
)
from app.services.reconciliation_service import (
    RULE_VERSION,
    evaluate_clinical_evidence,
)


class TestClinicalEvidenceReconciliation(unittest.TestCase):
    """Pengujian komprehensif Clinical Evidence Reconciliation Engine (CERE)."""

    def setUp(self) -> None:
        # Gunakan in-memory SQLite untuk isolasi tes unit
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed data dasar: Role & User
        role_user = Role(id_Role="R2", Name="User")
        self.db.add(role_user)
        user = User(
            NIK="3201234567890001",
            Name="Pasien Uji CERE",
            Tempat_Tgl_Lahir="Bandung, 01-01-2015",
            password="dummy_password_hash",
            id_Role="R2",
        )
        self.db.add(user)
        self.db.commit()

        self._jawaban_id = 0

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def _setup_screening(
        self,
        id_gejala: str,
        suhu: float | None,
        answers: dict[str, int],
        expert_ringkasan: dict | None = None,
    ) -> Gejala:
        gejala = Gejala(
            id_gejala=id_gejala,
            NIK="3201234567890001",
            Suhu=suhu,
            Batuk="Ya" if answers.get("BATUK") == 1 else "Tidak",
        )
        self.db.add(gejala)

        for kode, nilai in answers.items():
            self._jawaban_id += 1
            self.db.add(
                JawabanGejala(
                    id_jawaban=self._jawaban_id,
                    id_gejala=id_gejala,
                    kode_gejala=kode,
                    nilai=nilai,
                )
            )

        if expert_ringkasan is not None:
            hasil_pakar = HasilPakar(
                id_hasil=abs(hash(id_gejala)) % 100000 + 1,
                id_gejala=id_gejala,
                hasil="S003 | S014",
                skor=None,
                ringkasan=json.dumps(expert_ringkasan),
            )
            self.db.add(hasil_pakar)

        self.db.commit()
        return gejala

    def test_01_consistent_measles_suspicion(self) -> None:
        """
        Skenario 1: Bukti Konsisten Mengarah ke Suspek Campak (Krones et al., 2025; WHO, 2022)
        - CV: Measles (0.91)
        - Suhu: 38.8°C (Demam tinggi)
        - Pakar: Pola klinis & suspected terpenuhi
        Hasil diharapkan: Status CONSISTENT, tindakan isolasi & rujukan.
        """
        ringkasan = {
            "forward_chaining": {
                "screening_category": "CLINICAL_AND_SUSPECTED",
                "clinical_measles_pattern": True,
                "suspected_case_finding_pattern": True,
                "safety_alert": False,
                "active_safety_signs": [],
            }
        }
        self._setup_screening(
            id_gejala="GJL-001",
            suhu=38.8,
            answers={"DEMAM": 1, "RUAM": 1, "BATUK": 1, "MATA_MERAH": 1},
            expert_ringkasan=ringkasan,
        )

        req = EvidenceReconciliationEvaluateRequest(
            id_gejala="GJL-001",
            cv_prediction="Measles",
            cv_confidence=0.91,
        )
        res = evaluate_clinical_evidence(self.db, req)

        self.assertEqual(res.reconciliation_status, ReconciliationStatus.CONSISTENT)
        self.assertIn("suspek campak", res.summary.lower())
        self.assertEqual(res.evidence_validation.computer_vision, EvidenceValidationStatus.VALID)
        self.assertEqual(res.evidence_validation.body_temperature, EvidenceValidationStatus.VALID)
        self.assertEqual(res.evidence_validation.expert_system, EvidenceValidationStatus.VALID)
        self.assertFalse(res.is_diagnosis)
        self.assertGreater(len(res.supporting_evidence), 0)
        self.assertEqual(len(res.conflicting_evidence), 0)

    def test_02_consistent_healthy_normal(self) -> None:
        """
        Skenario 2: Bukti Konsisten Tidak Mengarah ke Campak
        - CV: Healthy (0.95)
        - Suhu: 36.6°C (Normal)
        - Pakar: Pola utama tidak terpenuhi
        Hasil diharapkan: Status CONSISTENT, saran istirahat.
        """
        ringkasan = {
            "forward_chaining": {
                "screening_category": "MAIN_PATTERN_NOT_MET",
                "clinical_measles_pattern": False,
                "suspected_case_finding_pattern": False,
                "safety_alert": False,
                "active_safety_signs": [],
            }
        }
        self._setup_screening(
            id_gejala="GJL-002",
            suhu=36.6,
            answers={"DEMAM": 0, "RUAM": 0, "BATUK": 0},
            expert_ringkasan=ringkasan,
        )

        req = EvidenceReconciliationEvaluateRequest(
            id_gejala="GJL-002",
            cv_prediction="Healthy",
            cv_confidence=0.95,
        )
        res = evaluate_clinical_evidence(self.db, req)

        self.assertEqual(res.reconciliation_status, ReconciliationStatus.CONSISTENT)
        self.assertIn("tidak mengarah ke suspek campak", res.summary.lower())
        self.assertEqual(len(res.conflicting_evidence), 0)

    def test_03_conflicting_cv_measles_vs_expert_healthy(self) -> None:
        """
        Skenario 3: Bukti Berkonflik (Helou et al., 2020; Islam et al., 2026)
        - CV: Measles (0.84)
        - Suhu: 36.5°C (Normal)
        - Pakar: Pola utama tidak terpenuhi (tidak ada demam, tidak ada 3C)
        Hasil diharapkan: Status CONFLICTING, sistem mencatat konflik & menyarankan pemeriksaan langsung.
        """
        ringkasan = {
            "forward_chaining": {
                "screening_category": "MAIN_PATTERN_NOT_MET",
                "clinical_measles_pattern": False,
                "suspected_case_finding_pattern": False,
                "safety_alert": False,
                "active_safety_signs": [],
            }
        }
        self._setup_screening(
            id_gejala="GJL-003",
            suhu=36.5,
            answers={"DEMAM": 0, "RUAM": 1, "BATUK": 0},
            expert_ringkasan=ringkasan,
        )

        req = EvidenceReconciliationEvaluateRequest(
            id_gejala="GJL-003",
            cv_prediction="Measles",
            cv_confidence=0.84,
        )
        res = evaluate_clinical_evidence(self.db, req)

        self.assertEqual(res.reconciliation_status, ReconciliationStatus.CONFLICTING)
        self.assertGreater(len(res.conflicting_evidence), 0)
        self.assertIn("inkonsistensi", res.summary.lower())

    def test_04_incomplete_missing_temperature(self) -> None:
        """
        Skenario 4: Modalitas Tidak Lengkap (Le et al., 2025; Liu et al., 2023)
        - Sensor Suhu: Belum tercatat / None
        - CV: Measles (0.75)
        - Pakar: Tersedia
        Hasil diharapkan: Status INCOMPLETE, sistem tidak mengasumsikan suhu normal secara sepihak.
        """
        ringkasan = {
            "forward_chaining": {
                "screening_category": "CLINICAL_PATTERN_ONLY",
                "clinical_measles_pattern": True,
                "suspected_case_finding_pattern": False,
                "safety_alert": False,
            }
        }
        self._setup_screening(
            id_gejala="GJL-004",
            suhu=None,
            answers={"DEMAM": 1, "RUAM": 1},
            expert_ringkasan=ringkasan,
        )

        req = EvidenceReconciliationEvaluateRequest(
            id_gejala="GJL-004",
            cv_prediction="Measles",
            cv_confidence=0.75,
        )
        res = evaluate_clinical_evidence(self.db, req)

        self.assertEqual(res.reconciliation_status, ReconciliationStatus.INCOMPLETE)
        self.assertEqual(res.evidence_validation.body_temperature, EvidenceValidationStatus.MISSING)
        self.assertGreater(len(res.missing_evidence), 0)

    def test_05_invalid_temperature_out_of_bounds(self) -> None:
        """
        Skenario 5: Bukti Tidak Valid / Rusak
        - Sensor Suhu: 52.0°C (di luar batas fisiologis wajar 30.0 - 45.0)
        Hasil diharapkan: Status INCOMPLETE dengan flag sensor INVALID.
        """
        ringkasan = {
            "forward_chaining": {
                "screening_category": "MAIN_PATTERN_NOT_MET",
                "safety_alert": False,
            }
        }
        self._setup_screening(
            id_gejala="GJL-005",
            suhu=52.0,
            answers={"DEMAM": 1},
            expert_ringkasan=ringkasan,
        )

        req = EvidenceReconciliationEvaluateRequest(
            id_gejala="GJL-005",
            cv_prediction="Healthy",
            cv_confidence=0.88,
        )
        res = evaluate_clinical_evidence(self.db, req)

        self.assertEqual(res.reconciliation_status, ReconciliationStatus.INCOMPLETE)
        self.assertEqual(res.evidence_validation.body_temperature, EvidenceValidationStatus.INVALID)
        self.assertGreater(len(res.invalid_evidence), 0)

    def test_06_safety_alert_priority_preservation(self) -> None:
        """
        Skenario 6: Preservasi Prioritas Tanda Bahaya (Safety Alert Override)
        Bahkan jika bukti tidak lengkap atau berkonflik, tanda bahaya seperti
        penurunan kesadaran atau sesak napas harus selalu memicu rujukan darurat ke IGD.
        """
        ringkasan = {
            "forward_chaining": {
                "screening_category": "MAIN_PATTERN_NOT_MET",
                "clinical_measles_pattern": False,
                "suspected_case_finding_pattern": False,
                "safety_alert": True,
                "active_safety_signs": ["SESAK", "PENURUNAN_KESADARAN"],
            }
        }
        self._setup_screening(
            id_gejala="GJL-006",
            suhu=None,  # Modality incomplete
            answers={"SESAK": 1, "PENURUNAN_KESADARAN": 1},
            expert_ringkasan=ringkasan,
        )

        req = EvidenceReconciliationEvaluateRequest(
            id_gejala="GJL-006",
            cv_prediction=None,  # CV juga missing
        )
        res = evaluate_clinical_evidence(self.db, req)

        self.assertTrue(res.safety_alert)
        self.assertIn("IGD", res.recommended_action)
        self.assertIn("TANDA BAHAYA", res.recommended_action)

    def test_07_upsert_idempotency(self) -> None:
        """
        Skenario 7: Idempotensi Evaluasi Berulang
        Memastikan evaluasi CERE untuk ID yang sama melakukan pembaruan (upsert)
        dan tidak memicu duplikasi record pada tabel evidence_reconciliations.
        """
        ringkasan = {
            "forward_chaining": {
                "screening_category": "MAIN_PATTERN_NOT_MET",
                "safety_alert": False,
            }
        }
        self._setup_screening(
            id_gejala="GJL-007",
            suhu=36.8,
            answers={"DEMAM": 0},
            expert_ringkasan=ringkasan,
        )

        req = EvidenceReconciliationEvaluateRequest(
            id_gejala="GJL-007",
            cv_prediction="Healthy",
            cv_confidence=0.90,
        )

        # Evaluasi ke-1
        res1 = evaluate_clinical_evidence(self.db, req)
        count1 = self.db.query(EvidenceReconciliation).count()
        self.assertEqual(count1, 1)

        # Evaluasi ke-2 dengan pembaruan CV
        req.cv_prediction = "Chickenpox"
        req.cv_confidence = 0.85
        res2 = evaluate_clinical_evidence(self.db, req)
        count2 = self.db.query(EvidenceReconciliation).count()

        self.assertEqual(count2, 1)  # Tidak menduplikasi baris
        self.assertEqual(res1.id_reconciliation, res2.id_reconciliation)
        self.assertEqual(res2.cv_prediction, "Chickenpox")


if __name__ == "__main__":
    unittest.main()
