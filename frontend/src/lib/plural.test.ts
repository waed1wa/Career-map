import { describe, expect, it } from "vitest";

import { stepsLeftLabel } from "./plural";

// Классы эквивалентности (лекция 9): 1 / 2–4 / 5–20 / 11–14 как исключение / 0
describe("stepsLeftLabel", () => {
  it.each([
    [1, "Осталось 1 шаг"],
    [21, "Осталось 21 шаг"],
    [3, "Осталось 3 шага"],
    [5, "Осталось 5 шагов"],
    [11, "Осталось 11 шагов"],
    [14, "Осталось 14 шагов"],
    [0, "Все шаги пройдены"],
  ])("%i → %s", (n, label) => {
    expect(stepsLeftLabel(n)).toBe(label);
  });
});
