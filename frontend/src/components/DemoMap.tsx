import { useEffect, useState } from "react";

import { getDemoMap, type CareerMap, type StepStatus } from "../api/client";
import { stepsLeftLabel } from "../lib/plural";

const STATUS_LABEL: Record<StepStatus, string> = {
  done: "Пройдено",
  current: "Сейчас",
  todo: "Дальше",
};

// Спринт 0: карта списком. В спринте 3 заменим на граф на React Flow (@xyflow/react).
export function DemoMap() {
  const [map, setMap] = useState<CareerMap | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getDemoMap()
      .then(setMap)
      .catch(() => setError(true));
  }, []);

  if (error) return <p className="muted">Не удалось загрузить карту. Запущен ли API?</p>;
  if (!map) return <p className="muted">Строим карту…</p>;

  return (
    <div>
      <p className="steps-left">{stepsLeftLabel(map.steps_left)}</p>
      <ol className="map">
        {map.steps.map((step) => (
          <li key={step.skill} className={`step step--${step.status}`}>
            <span className="step__num">{step.order}</span>
            <div>
              <span className="step__badge">{STATUS_LABEL[step.status]}</span>
              <h3>{step.title}</h3>
              <p className="muted">{step.why}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
