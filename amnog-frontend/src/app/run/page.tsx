import { Suspense } from "react";
import RunClient from "./RunClient";

export default function Page() {
  return (
    <Suspense fallback={<div style={{ padding: 24 }}>Loading…</div>}>
      <RunClient />
    </Suspense>
  );
}
