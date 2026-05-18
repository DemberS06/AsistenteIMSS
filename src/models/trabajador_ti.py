# models/trabajador_ti.py
from __future__ import annotations
from dataclasses import dataclass

from config import EXCEL_COLUMNS_TI


@dataclass
class TrabajadorTI:
    """Modelo de datos para Trabajador Independiente (TI)."""
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
    def from_row(cls, row: dict) -> TrabajadorTI:
        """Crea un TrabajadorTI desde una fila de Excel."""
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
        """Convierte el TrabajadorTI a una fila de Excel."""
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
        """
        Genera el diccionario de campos para el formulario IMSS TI.
        
        Args:
            captcha: Valor del captcha ingresado por el usuario
            
        Returns:
            Dict con los campos listos para enviar al formulario
        """
        return {
            "curp":              self.curp,
            "rfc":               self.rfc,
            "nss":               self.nss,
            "email":             self.correo,
            "emailConfirmacion": self.correo,
            "captcha":           captcha,
        }
    
    @staticmethod
    def get_excel_columns() -> list[str]:
        """
        Retorna la lista de columnas de Excel para TI.
        Usa la constante centralizada en config.py
        """
        return EXCEL_COLUMNS_TI