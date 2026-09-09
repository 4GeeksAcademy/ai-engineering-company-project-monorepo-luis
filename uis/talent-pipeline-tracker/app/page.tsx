import { Suspense } from "react";

import CandidateList from "./candidate-list";

export default function Home() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f6f7f2]" />}>
      <CandidateList />
    </Suspense>
  );
}
