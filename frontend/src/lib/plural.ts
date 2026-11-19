// «1 шаг», «2 шага», «5 шагов» — русское склонение после числа.
export function pluralRu(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function stepsLeftLabel(n: number): string {
  if (n === 0) return "Все шаги пройдены";
  return `Осталось ${n} ${pluralRu(n, "шаг", "шага", "шагов")}`;
}
