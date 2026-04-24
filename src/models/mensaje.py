# models/mensaje.py
from dataclasses import dataclass


@dataclass
class Mensaje:
    texto:    str  = ""
    encontrado: bool = False
    page_idx: int  = -1
    pdf_path: str  = ""

    def es_valido(self) -> bool:
        return self.encontrado and bool(self.texto.strip())
