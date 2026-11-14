from pydantic import BaseModel, Field, ConfigDict

class JawabanGejalaInput(BaseModel):
    kode_gejala: str = Field(
        min_length=1,
        max_length=30,
    )

    nilai: int = Field(
        ge=0,
        le=1,
        description="1 = Ya, 0 = Tidak",
    )

class EvaluasiPakarRequest(BaseModel):
    id_gejala: str = Field(
        min_length=1,
        max_length=20,
    )

    jawaban: list[JawabanGejalaInput] = Field(
        min_length=9,
        description="Jawaban kuesioner gejala pasien",
    )

class EvaluasiPakarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_hasil: int
    id_gejala: str
    hasil: str
    skor: int | None = None
    ringkasan: str | None = None
