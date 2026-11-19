import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.gejala import Gejala
from app.models.pakar import HasilPakar, JawabanGejala
from app.services.reconciliation_service import evaluate_clinical_evidence


class ReconciliationScenarioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://")
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.Session()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def evaluate(self, name, temp, cv, category, safety=False, subjective_fever=0):
        id_gejala = f"test-{name}"
        self.db.add(Gejala(id_gejala=id_gejala, NIK="patient", Batuk=None, Suhu=temp))
        self.db.add(
            HasilPakar(
                id_hasil=ord(name) - ord("A") + 1,
                id_gejala=id_gejala,
                hasil=category,
                skor=None,
                ringkasan='{"forward_chaining":{"screening_category":"' + category + '"}}',
            )
        )
        self.db.add(
            JawabanGejala(
                id_jawaban=ord(name) - ord("A") + 1,
                id_gejala=id_gejala,
                kode_gejala="DEMAM",
                nilai=subjective_fever,
            )
        )
        self.db.commit()
        return evaluate_clinical_evidence(
            db=self.db,
            id_gejala=id_gejala,
            cv_prediction=cv,
            cv_confidence=0.9 if cv else None,
            cv_status=None if cv else "MISSING",
            expert_category=category,
            safety_alert=safety,
        )

    def test_scenarios(self):
        scenarios = [
            ("A", 36.6, "Healthy", "PATTERN_NOT_MET", False, 0, "CONSISTENT"),
            ("B", 36.6, "Healthy", "CLINICAL_PATTERN_ONLY", False, 0, "CONFLICTING"),
            ("C", 38.8, "Measles", "CLINICAL_AND_SUSPECTED", False, 1, "CONSISTENT"),
            ("D", 36.6, None, "PATTERN_NOT_MET", False, 0, "INCOMPLETE"),
            ("E", 52.0, "Measles", "PATTERN_NOT_MET", False, 0, "INCOMPLETE"),
            ("F", 36.6, "Measles", "PATTERN_NOT_MET", False, 0, "CONFLICTING"),
        ]

        for name, temp, cv, category, safety, fever, expected in scenarios:
            with self.subTest(name=name):
                result = self.evaluate(name, temp, cv, category, safety, fever)
                self.assertEqual(result["reconciliation_status"], expected)


if __name__ == "__main__":
    unittest.main()
