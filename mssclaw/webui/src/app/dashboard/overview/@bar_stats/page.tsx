import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function BarStats() {
  return (
    <Card>
      <CardHeader><CardTitle>Sprint Velocity</CardTitle></CardHeader>
      <CardContent>
        <div className="flex items-end gap-2 h-40">
          {[35, 45, 58, 72, 85, 99, 106].map((v, i) => (
            <div key={i} className="flex-1 bg-primary/20 rounded-t" style={{ height: `${(v/106)*100}%` }}>
              <div className="text-xs text-center mt-1 -rotate-90 origin-left translate-x-4">{v}</div>
            </div>
          ))}
        </div>
        <div className="flex justify-between text-xs text-muted-foreground mt-2">
          <span>S0</span><span>S20</span><span>S40</span><span>S60</span><span>S80</span><span>S99</span><span>S106</span>
        </div>
      </CardContent>
    </Card>
  );
}
