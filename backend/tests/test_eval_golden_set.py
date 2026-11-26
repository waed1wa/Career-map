"""Замер точности. Резюме здесь — две строки с навыками, собранные прямо в тесте, а не настоящие люди."""

import json

import pytest

from app.tools.eval_golden_set import Score, main, score


def test_score_counts():
    s = score({"python", "git", "sql"}, {"python", "git", "docker"})

    assert (s.hits, s.extra, s.missed) == (2, 1, 1)
    assert s.precision == pytest.approx(2 / 3)
    assert s.recall == pytest.approx(2 / 3)


def test_nothing_found_means_no_extra():
    """Граница: пустой ответ не «ошибается», но всё пропускает."""
    s = score({"python"}, set())

    assert (s.precision, s.recall) == (1.0, 0.0)


def test_nothing_expected_nothing_found():
    assert score(set(), set()) == Score(0, 0, 0)
    assert (Score(0, 0, 0).precision, Score(0, 0, 0).recall) == (1.0, 1.0)


def test_scores_add_up_over_resumes():
    assert score({"a"}, {"a"}) + score({"b"}, {"c"}) == Score(1, 1, 1)


def put(folder, name: str, text: str, skills: list[str]) -> None:
    (folder / f"{name}.txt").write_text(text, encoding="utf-8")
    (folder / f"{name}.json").write_text(
        json.dumps({"profession_id": "backend-junior", "skills": skills}), encoding="utf-8"
    )


def test_main_passes_on_good_markup(tmp_path, capsys):
    put(tmp_path, "resume_01", "Навыки: Python, Git", ["python", "git"])
    put(tmp_path, "resume_02", "Делал API на Django, база PostgreSQL", ["http-api", "web-framework", "sql"])

    assert main(["--dir", str(tmp_path)]) == 0
    assert "ИТОГО" in capsys.readouterr().out


def test_main_fails_below_threshold(tmp_path, capsys):
    """Словарь находит Docker, хотя студент пишет, что не работал с ним, — лишний навык."""
    put(tmp_path, "resume_01", "Python. С Docker не работал. Excel, Git, Linux", ["python"])

    assert main(["--dir", str(tmp_path)]) == 1
    assert "сигнал риска Р-6" in capsys.readouterr().out


def test_main_on_empty_folder(tmp_path, capsys):
    assert main(["--dir", str(tmp_path)]) == 2
    assert "нет резюме" in capsys.readouterr().out
