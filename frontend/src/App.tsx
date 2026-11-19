import { useEffect, useState } from "react";

import { getHealth, type Health } from "./api/client";
import { Landing } from "./pages/Landing";

export function App() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <>
      <Landing />
      <footer className="footer">
        API:{" "}
        {health
          ? `${health.status} · база ${health.database ? "✓" : "✗"} · очередь ${health.redis ? "✓" : "✗"}`
          : "не отвечает"}
      </footer>
    </>
  );
}
