import { redirect } from 'next/navigation';

export default async function Page() {
  // mssclaw: no auth required, go straight to dashboard
  redirect('/dashboard/overview');
}
