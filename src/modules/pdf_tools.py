# modules/pdf_tools.py
import os
import shutil


class PDFTools:
    def __init__(self):
        pass

    def move_temp_to_final(self, temp_folder, download_folder, only_extensions={".pdf"}, subfolder_name="PDFs"):
        temp_folder = os.path.abspath(temp_folder)
        download_folder = os.path.abspath(download_folder)
        final_folder = os.path.join(download_folder, subfolder_name)
        os.makedirs(final_folder, exist_ok=True)
        moved = []

        try:
            for name in os.listdir(temp_folder):
                src = os.path.join(temp_folder, name)
                if not os.path.isfile(src):
                    continue
                if name.endswith(".crdownload"):
                    continue
                if only_extensions:
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in {e.lower() for e in only_extensions}:
                        continue

                dest = os.path.join(final_folder, name)
                if os.path.exists(dest):
                    base, ext = os.path.splitext(name)
                    i = 1
                    while True:
                        candidate = os.path.join(final_folder, f"{base} ({i}){ext}")
                        if not os.path.exists(candidate):
                            dest = candidate
                            break
                        i += 1

                shutil.move(src, dest)
                moved.append(dest)
        except Exception as e:
            print(f"[PDFTools] Error moviendo PDFs: {e}")
        return moved

    def move_specific_files(self, paths, dest_folder):
        os.makedirs(dest_folder, exist_ok=True)
        moved = []
        for p in paths:
            if not os.path.exists(p):
                continue
            name = os.path.basename(p)
            dest = os.path.join(dest_folder, name)
            if os.path.exists(dest):
                base, ext = os.path.splitext(name)
                i = 1
                while True:
                    candidate = os.path.join(dest_folder, f"{base} ({i}){ext}")
                    if not os.path.exists(candidate):
                        dest = candidate
                        break
                    i += 1
            shutil.move(p, dest)
            moved.append(dest)
        return moved

    def process_moved_files(self, moved_paths, download_folder, subfolder_name, client_name):
        import os, traceback, shutil

        result = {"final_paths": [], "dest_folder": "", "pdf_to_save": "", "errors": []}
        try:
            if not moved_paths:
                result["errors"].append("No hay archivos a procesar.")
                return result

            dest_folder = os.path.abspath(os.path.join(download_folder, subfolder_name)) if subfolder_name else os.path.dirname(moved_paths[0])
            result["dest_folder"] = dest_folder

            def _safe_client_name(name: str):
                if not name:
                    return "Cliente"
                invalid = '<>:"/\\|?*\n\r\t'
                s = "".join(ch for ch in str(name) if ch not in invalid).strip()
                while "  " in s:
                    s = s.replace("  ", " ")
                return s[:200] or "Cliente"

            client_clean = _safe_client_name(client_name)
            final_paths = []

            for src in moved_paths:
                try:
                    base = os.path.basename(src)
                    name_lower = base.lower()
                    suffix = None
                    if "comprobante" in name_lower:
                        suffix = "Comprobante"
                    elif "lineacaptura" in name_lower or "linea" in name_lower or "captura" in name_lower:
                        suffix = "lineaCaptura"

                    if suffix:
                        root, ext = os.path.splitext(base)
                        ext = ext or ".pdf"
                        new_base = f"{client_clean}_{suffix}{ext}"
                        candidate = os.path.join(dest_folder, new_base)
                        i = 1
                        while os.path.exists(candidate):
                            candidate = os.path.join(dest_folder, f"{client_clean}_{suffix} ({i}){ext}")
                            i += 1
                        try:
                            os.rename(src, candidate)
                        except Exception:
                            try:
                                shutil.move(src, candidate)
                            except Exception:
                                candidate = os.path.abspath(src)
                        final_paths.append(os.path.abspath(candidate))
                    else:
                        final_paths.append(os.path.abspath(src))
                except Exception as e:
                    result["errors"].append(f"Error procesando {src}: {e}")
                    try:
                        final_paths.append(os.path.abspath(src))
                    except Exception:
                        pass

            result["final_paths"] = final_paths

            comprobante_path = None
            try:
                for f in os.listdir(dest_folder):
                    fl = f.lower()
                    if fl.startswith(client_clean.lower()) and "comprobante" in fl and f.lower().endswith(".pdf"):
                        comprobante_path = os.path.join(dest_folder, f)
                        break
            except Exception:
                pass

            if not comprobante_path:
                for p in final_paths:
                    if "_comprobante" in os.path.basename(p).lower():
                        comprobante_path = p
                        break

            result["pdf_to_save"] = comprobante_path or (final_paths[0] if final_paths else "")
            return result
        except Exception as e:
            result["errors"].append(str(e))
            result["errors"].append(traceback.format_exc())
            return result

    def move_and_process_temp(self, temp_folder, download_folder, subfolder_name, client_name, only_extensions={".pdf"}):
        import traceback, os

        result = {"final_paths": [], "dest_folder": "", "pdf_to_save": "", "errors": []}
        try:
            try:
                moved = self.move_temp_to_final(temp_folder, download_folder, only_extensions=only_extensions, subfolder_name=subfolder_name)
            except Exception as e:
                result["errors"].append(f"Error moviendo archivos: {e}")
                result["errors"].append(traceback.format_exc())
                return result

            if not moved:
                result["errors"].append("No se detectaron archivos para mover desde la carpeta temporal.")
                return result

            proc = self.process_moved_files(moved, download_folder, subfolder_name, client_name)
            if proc.get("errors"):
                result["errors"].extend(proc.get("errors"))
            result["final_paths"] = proc.get("final_paths", [])
            result["dest_folder"] = proc.get("dest_folder", "")
            result["pdf_to_save"] = proc.get("pdf_to_save", "")
            return result
        except Exception as e:
            result["errors"].append(str(e))
            result["errors"].append(traceback.format_exc())
            return result

    # ------------------ PDF global search / text extraction ------------------

    def _normalize(self, s: str) -> str:
        try:
            import unicodedata
            if not s:
                return ""
            s = unicodedata.normalize("NFD", s)
            s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
            return s.lower()
        except Exception:
            return (s or "").lower()

    def get_pdf_pages_text(self, pdf_path: str):
        pdf_path = os.path.abspath(pdf_path)
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF no existe: {pdf_path}")

        pages = []
        try:
            import fitz  # pymupdf
            doc = fitz.open(pdf_path)
            for i in range(len(doc)):
                try:
                    page = doc.load_page(i)
                    text = page.get_text("text") or ""
                except Exception:
                    text = ""
                pages.append(text)
            doc.close()
            return pages
        except Exception:
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                for p in reader.pages:
                    try:
                        txt = p.extract_text() or ""
                    except Exception:
                        txt = ""
                    pages.append(txt)
                return pages
            except Exception as e:
                raise RuntimeError(f"No se pudo extraer texto del PDF (ni fitz ni pypdf disponibles o fallaron): {e}")

    def get_page_text(self, pdf_path: str, page_idx: int):
        pages = self.get_pdf_pages_text(pdf_path)
        if page_idx < 0 or page_idx >= len(pages):
            raise IndexError("page_idx fuera de rango")
        return pages[page_idx]

    def find_message_for_client_in_pdf(self, pdf_path: str, client_name: str, fuzzy: bool = True):
        res = {"found": False, "page_idx": None, "text": "", "snippet": "", "errors": []}
        try:
            if not client_name or not client_name.strip():
                return res
            if not os.path.exists(pdf_path):
                res["errors"].append(f"PDF no existe: {pdf_path}")
                return res

            client_norm = self._normalize(client_name)

            try:
                pages = self.get_pdf_pages_text(pdf_path)
            except Exception as e:
                res["errors"].append(f"Error extrayendo texto: {e}")
                return res

            for i, pg in enumerate(pages):
                if client_norm in self._normalize(pg):
                    txt = (pg or "").strip()
                    res.update({"found": True, "page_idx": i, "text": txt, "snippet": (txt[:160] + "...") if len(txt) > 160 else txt})
                    return res

            if fuzzy:
                parts = [p for p in client_name.split() if p.strip()]
                tokens = []
                if len(parts) >= 2:
                    tokens.append(parts[-1])   
                    tokens.append(parts[-2])   
                elif parts:
                    tokens.append(parts[0])
                tokens = [self._normalize(t) for t in tokens if t]

                for token in tokens:
                    if not token:
                        continue
                    for i, pg in enumerate(pages):
                        if token in self._normalize(pg):
                            txt = (pg or "").strip()
                            res.update({"found": True, "page_idx": i, "text": txt, "snippet": (txt[:160] + "...") if len(txt) > 160 else txt})
                            return res

            try:
                import difflib
                snippets = []
                for pg in pages:
                    s = (pg or "").strip()
                    s_snip = s[:300] if len(s) > 300 else s
                    snippets.append(s_snip)

                candidates = [client_norm]
                if parts:
                    candidates.extend([self._normalize(p) for p in parts if len(p) >= 3])
                for cand in candidates:
                    matches = difflib.get_close_matches(cand, [self._normalize(t) for t in snippets], n=3, cutoff=0.6)
                    if matches:
                        match_norm = matches[0]
                        for i, s in enumerate(snippets):
                            if match_norm == self._normalize(s):
                                txt = (pages[i] or "").strip()
                                res.update({"found": True, "page_idx": i, "text": txt, "snippet": (txt[:160] + "...") if len(txt) > 160 else txt})
                                return res
            except Exception:
                pass

            return res

        except Exception as e:
            import traceback
            res["errors"].append(str(e))
            res["errors"].append(traceback.format_exc())
            return res
