import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AreaStats() {
  return (
    <Card>
      <CardHeader><CardTitle>Phase Progress</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-4">
          {[
            { phase: '🔴 Ship It', pct: 100, color: 'bg-red-500' },
            { phase: '🟡 Document It', pct: 100, color: 'bg-yellow-500' },
            { phase: '🟢 Test It', pct: 100, color: 'bg-green-500' },
            { phase: '🔵 Harden It', pct: 100, color: 'bg-blue-500' },
          ].map((p) => (
            <div key={p.phase}>
              <div className="flex justify-between text-sm mb-1">
                <span>{p.phase}</span>
                <span className="font-mono">{p.pct}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div className={`h-full ${p.color} rounded-full`} style={{ width: `${p.pct}%` }} />
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-4">All 4 phases completed — v0.3.9 shipped</p>
      </CardContent>
    </Card>
  );
}
