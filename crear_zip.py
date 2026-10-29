#!/usr/bin/env python3
"""Genera eduperu_ia.zip con todo el proyecto listo para subir a GitHub / Streamlit Cloud.

Uso:   python crear_zip.py            → crea  eduperu_ia.zip  junto a este archivo
       python crear_zip.py salida.zip → usa otro nombre

No incluye secretos (.streamlit/secrets.toml), cachés ni zips anteriores.
"""
import os
import sys
import zipfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "eduperu_ia.zip")
EXCLUIR_DIRS = {"__pycache__", ".git", ".venv", "venv", ".idea", ".vscode"}
EXCLUIR_ARCH = {"secrets.toml"}


def main():
    n = 0
    with zipfile.ZipFile(SALIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for carpeta, dirs, archivos in os.walk(RAIZ):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUIR_DIRS)
            for nombre in sorted(archivos):
                ruta = os.path.join(carpeta, nombre)
                if nombre in EXCLUIR_ARCH or nombre.endswith((".pyc", ".zip")) or os.path.abspath(ruta) == os.path.abspath(SALIDA):
                    continue
                z.write(ruta, os.path.relpath(ruta, RAIZ))
                n += 1
    print(f"✅ {n} archivos → {SALIDA}")


if __name__ == "__main__":
    main()
