import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from '@/components/ui/card';

const commits = [
  { name: 'Sprint 106', desc: 'Overview cards → mssclaw data', hash: 'f837596' },
  { name: 'Sprint 105', desc: 'Dashboard LIVE — 200 OK', hash: '61ded13' },
  { name: 'Sprint 104', desc: 'Next.js dashboard integrated', hash: '1db9d91' },
  { name: 'Sprint 103', desc: 'Absorbed top frontends', hash: 'd8767a6' },
  { name: 'Sprint 101', desc: 'Real Ollama test 5/5', hash: 'fb779d4' },
];

export function RecentSales() {
  return (
    <Card className='h-full'>
      <CardHeader>
        <CardTitle>Recent Commits</CardTitle>
        <CardDescription>106 sprints delivered.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-8'>
          {commits.map((c, i) => (
            <div key={i} className='flex items-center'>
              <Avatar className='h-9 w-9'>
                <AvatarFallback>{c.hash.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <div className='ml-4 space-y-1'>
                <p className='text-sm leading-none font-medium'>{c.name}</p>
                <p className='text-muted-foreground text-sm'>{c.desc}</p>
              </div>
              <code className='ml-auto text-xs text-muted-foreground font-mono'>{c.hash}</code>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
