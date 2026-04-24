# models/trabajador.py
from dataclasses import dataclass


@dataclass
class Trabajador:
    id:          str = ""
    cliente:     str = ""
    nss:         str = ""
    curp:        str = ""
    rfc:         str = ""
    correo:      str = ""
    numero:      str = ""
    carpeta_pdf: str = ""   # CARPETAPDF — carpeta destino de descarga
    pdf:         str = ""   # PDF        — ruta del PDF a enviar por WhatsApp
    mensaje:     str = ""   # MENSAJE    — ruta del PDF global de mensajes

    # ----------------------------------------------------------------
    # Conversión desde/hacia fila del Excel
    # ----------------------------------------------------------------

    @classmethod
    def from_row(cls, row: dict) -> "Trabajador":
        return cls(
            id          = row.get("ID",          ""),
            cliente     = row.get("CLIENTE",     ""),
            nss         = row.get("NSS",         ""),
            curp        = row.get("CURP",        ""),
            rfc         = row.get("RFC",         ""),
            correo      = row.get("CORREO",      ""),
            numero      = row.get("NUMERO",      ""),
            carpeta_pdf = row.get("CARPETAPDF",  ""),
            pdf         = row.get("PDF",         ""),
            mensaje     = row.get("MENSAJE",     ""),
        )

    def to_row(self) -> dict:
        return {
            "ID":         self.id,
            "CLIENTE":    self.cliente,
            "NSS":        self.nss,
            "CURP":       self.curp,
            "RFC":        self.rfc,
            "CORREO":     self.correo,
            "NUMERO":     self.numero,
            "CARPETAPDF": self.carpeta_pdf,
            "PDF":        self.pdf,
            "MENSAJE":    self.mensaje,
        }

    def to_imss_fields(self, captcha: str) -> dict:
        """Dict listo para rellenar el formulario del IMSS."""
        return {
            "curp":              self.curp,
            "rfc":               self.rfc,
            "nss":               self.nss,
            "email":             self.correo,
            "emailConfirmacion": self.correo,
            "captcha":           captcha,
        }