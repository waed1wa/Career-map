import { DemoMap } from "../components/DemoMap";

// Лендинг: сначала показываем карту, потом просим регистрацию.
// Это вывод из интервью: студенты не хотят заполнять анкету, пока не увидят результат.
export function Landing() {
  return (
    <main className="page">
      <header className="hero">
        <p className="eyebrow">Карьерная карта</p>
        <h1>Покажем путь от учёбы до первой работы — по шагам</h1>
        <p className="lead">
          Загрузите резюме или ответьте на 6 вопросов. Мы сравним ваши навыки с вакансиями и соберём карту на
          6–8 шагов с материалами и проектами.
        </p>
        <button className="btn" type="button" disabled title="Появится на неделе 1">
          Построить свою карту
        </button>
      </header>

      <section>
        <h2>Пример карты: Junior Backend</h2>
        <DemoMap />
      </section>
    </main>
  );
}
