"""Чтение резюме из файла. Граничные значения размера (лекция 9) — те же, что на клиенте у Якубова."""

import io
import zipfile
from pathlib import Path

import docx
import pypdf
import pytest

from app.modules.profile.resume_file import (
    MAX_RESUME_BYTES,
    ResumeFileError,
    check_resume_file,
    extract_text,
)

FIXTURES = Path(__file__).parent / "fixtures"
MB = 1024 * 1024


def make_docx(*paragraphs: str, table: list[list[str]] | None = None) -> bytes:
    document = docx.Document()
    for p in paragraphs:
        document.add_paragraph(p)
    if table:
        t = document.add_table(rows=len(table), cols=len(table[0]))
        for r, row in enumerate(table):
            for c, value in enumerate(row):
                t.cell(r, c).text = value
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def blank_pdf() -> bytes:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# ---------- размер и расширение ----------


@pytest.mark.parametrize(
    "size",
    [1, int(4.99 * MB), MAX_RESUME_BYTES],
    ids=["one_byte", "4_99_mb", "exactly_5_mb"],
)
def test_allowed_sizes(size):
    assert check_resume_file("cv.pdf", size) == "pdf"


@pytest.mark.parametrize(
    ("size", "message"),
    [
        (0, "Файл пустой"),
        (MAX_RESUME_BYTES + 1, "Файл 5,00 МБ — это больше 5 МБ"),
        (int(5.01 * MB), "Файл 5,01 МБ — это больше 5 МБ"),
    ],
    ids=["empty", "5_mb_plus_1_byte", "5_01_mb"],
)
def test_rejected_sizes(size, message):
    with pytest.raises(ResumeFileError, match=message):
        check_resume_file("cv.pdf", size)


@pytest.mark.parametrize("name", ["CV.PDF", "резюме.Docx", "cv.v2.final.pdf"])
def test_allowed_names(name):
    assert check_resume_file(name, 100) in ("pdf", "docx")


@pytest.mark.parametrize("name", ["cv.doc", "cv.jpg", "cv", ".pdf", "cv.pdf.exe"])
def test_rejected_names(name):
    with pytest.raises(ResumeFileError, match="Подойдёт файл PDF или DOCX"):
        check_resume_file(name, 100)


# ---------- содержимое ----------


def test_text_from_pdf():
    text = extract_text("cv.pdf", (FIXTURES / "resume_text.pdf").read_bytes())

    assert "Навыки: Python, Git, PostgreSQL." in text


def test_text_from_docx_with_table():
    data = make_docx("Учебные проекты", table=[["Навыки", "Python, SQL"]])

    text = extract_text("cv.docx", data)

    assert "Учебные проекты" in text
    assert "Python, SQL" in text


def test_scan_without_text():
    with pytest.raises(ResumeFileError, match="похоже, это скан"):
        extract_text("scan.pdf", blank_pdf())


def test_renamed_picture():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    with pytest.raises(ResumeFileError, match="внутри не PDF"):
        extract_text("cv.pdf", png)


def test_pdf_named_docx():
    with pytest.raises(ResumeFileError, match="внутри не документ Word"):
        extract_text("cv.docx", (FIXTURES / "resume_text.pdf").read_bytes())


def test_broken_pdf():
    with pytest.raises(ResumeFileError, match="Не получилось прочитать PDF"):
        extract_text("cv.pdf", b"%PDF-1.7\n" + b"\x00" * 500)


def test_zip_that_is_not_docx():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("hello.txt", "не документ")

    with pytest.raises(ResumeFileError, match="Не получилось прочитать DOCX"):
        extract_text("cv.docx", buffer.getvalue())
