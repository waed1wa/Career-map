"""Текст из файла резюме: PDF или DOCX до 5 МБ.

Те же правила, что у Якубова на клиенте (resumeFile.ts), но проверяем ещё раз: клиенту на слово
не верим. Дополнительно смотрим на сами байты файла, а не только на расширение: переименованная
картинка «resume.pdf» не пройдёт.
"""

import io

import docx
import pypdf

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 МБ, как в плане тестирования
_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"  # DOCX — это zip-архив


class ResumeFileError(ValueError):
    """Файл не подходит. Текст ошибки показываем студенту как есть."""


def check_resume_file(filename: str, size: int) -> str:
    """Проверка до чтения файла. Возвращает расширение: «pdf» или «docx»."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename.strip(".") else ""
    if extension not in ("pdf", "docx"):
        raise ResumeFileError("Подойдёт файл PDF или DOCX")
    if size <= 0:
        raise ResumeFileError("Файл пустой — выберите другой")
    if size > MAX_RESUME_BYTES:
        megabytes = f"{size / (1024 * 1024):.2f}".replace(".", ",")
        raise ResumeFileError(f"Файл {megabytes} МБ — это больше 5 МБ. Сожмите его или ответьте на вопросы")
    return extension


def extract_text(filename: str, data: bytes) -> str:
    extension = check_resume_file(filename, len(data))
    if extension == "pdf":
        text = _pdf_text(data)
    else:
        text = _docx_text(data)
    if not text.strip():
        raise ResumeFileError(
            "В файле нет текста — похоже, это скан или картинка. "
            "Сохраните резюме в PDF из Word или Google Docs либо ответьте на вопросы"
        )
    return text


def _pdf_text(data: bytes) -> str:
    if not data.startswith(_PDF_MAGIC):
        raise ResumeFileError("Файл называется .pdf, но внутри не PDF")
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:  # чужой файл может сломать разборщик как угодно — для студента это «повреждён»
        raise ResumeFileError("Не получилось прочитать PDF — возможно, файл повреждён") from error


def _docx_text(data: bytes) -> str:
    if not data.startswith(_ZIP_MAGIC):
        raise ResumeFileError("Файл называется .docx, но внутри не документ Word")
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as error:
        raise ResumeFileError("Не получилось прочитать DOCX — возможно, файл повреждён") from error
    parts = [p.text for p in document.paragraphs]
    # навыки часто пишут в таблицу «Навыки | Уровень»
    parts += [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join(parts)
