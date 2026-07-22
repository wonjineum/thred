import React from 'react';

// Mocked score data — Phase 4 replaces this with a real API response.
const mockScore = {
  total: 72,
  brand: { points: 28, max: 34, note: 'Average brand, no verified sustainability practices found' },
  material: { points: 15, max: 33, note: '60% polyester, 40% cotton blend' },
  userHistory: { points: 29, max: 33, note: 'No similar item in your wardrobe or recent purchases' },
};

function ScoreBar({ label, points, max, note }: { label: string; points: number; max: number; note: string }) {
  const pct = Math.round((points / max) * 100);
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span>{points}/{max}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full bg-green-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-400 mt-1">{note}</p>
    </div>
  );
}

export default function Popup() {
  return (
    <div className="w-80 p-4 font-sans">
      <div className="flex items-baseline justify-between mb-4">
        <p className="text-sm font-medium">Sustainability score</p>
        <p className="text-2xl font-medium">
          {mockScore.total}
          <span className="text-sm text-gray-400">/100</span>
        </p>
      </div>
      <ScoreBar label="Brand" {...mockScore.brand} />
      <ScoreBar label="Material" {...mockScore.material} />
      <ScoreBar label="User history" {...mockScore.userHistory} />
    </div>
  );
}
