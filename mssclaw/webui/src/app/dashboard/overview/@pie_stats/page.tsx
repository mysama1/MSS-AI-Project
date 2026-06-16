import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function PieStats() {
  return (
    <Card className="h-full">
      <CardHeader><CardTitle>Module Distribution</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-3">
          {[
            { label: 'Core Agent', pct: 35, color: 'bg-blue-500' },
            { label: 'Vault Stack', pct: 20, color: 'bg-green-500' },
            { label: 'L2 Meaning', pct: 15, color: 'bg-purple-500' },
            { label: 'Specialty (MSS)', pct: 20, color: 'bg-amber-500' },
            { label: 'WebUI', pct: 10, color: 'bg-pink-500' },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded ${item.color}`} />
              <span className="flex-1 text-sm">{item.label}</span>
              <span className="text-sm font-mono text-muted-foreground">{item.pct}%</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
