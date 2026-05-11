from pydantic import BaseModel


class OcrRequest(BaseModel):
    image_base64: str
    language: str = "es"


class OcrLine(BaseModel):
    text: str
    confidence: float
    bbox: list[list[float]]


class OcrResponse(BaseModel):
    text: str
    confidence: float
    lines: list[OcrLine]
    processing_time_ms: int


class BatchOcrRequest(BaseModel):
    images: list[dict]
    language: str = "es"


class BatchOcrResponse(BaseModel):
    results: list[dict]


class IneOcrResponse(BaseModel):
    frente: OcrResponse
    reverso: OcrResponse | None = None
    combined_text: str
    processing_time_ms: int


class IneExtractData(BaseModel):
    nombre: str | None = None
    apellidoPaterno: str | None = None
    apellidoMaterno: str | None = None
    curp: str | None = None
    curpDerivado: bool = False
    claveElector: str | None = None
    fechaNacimiento: str | None = None
    sexo: str | None = None
    domicilio: str | None = None
    colonia: str | None = None
    codigoPostal: str | None = None
    municipio: str | None = None
    estado: str | None = None
    seccion: str | None = None
    vigencia: str | None = None
    anioRegistro: str | None = None
    emision: str | None = None
    estadoClave: str | None = None
    municipioClave: str | None = None
    localidad: str | None = None
    fuenteExtraccion: str | None = None


class OcrConfidence(BaseModel):
    frente: float
    reverso: float | None = None


class IneExtractResponse(BaseModel):
    success: bool
    extraction_id: str
    data: IneExtractData
    ocr_confidence: OcrConfidence
    raw_text: str
    processing_time_ms: int
    upload_method: str
