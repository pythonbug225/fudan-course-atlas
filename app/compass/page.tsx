export const dynamic = 'force-dynamic';

type CompassQuery = { cohort?: string; plan?: string; department?: string };

export default async function CompassPage({ searchParams }: { searchParams: Promise<CompassQuery> }) {
  const query = await searchParams;
  const historical = ['2023', '2024', '2025'].includes(query.cohort ?? '');
  const mapQuery = new URLSearchParams({ year: historical ? query.cohort! : '2025' });
  if (typeof query.plan === 'string' && query.plan) mapQuery.set('plan', query.plan);
  if (typeof query.department === 'string' && query.department) mapQuery.set('department', query.department);
  return (
    <main style={{ position: 'fixed', inset: 0, display: 'flex', flexDirection: 'column', margin: 0, overflow: 'hidden' }}>
      <nav aria-label="课程地图年级" style={{ display: 'flex', gap: 18, padding: '6px 16px', background: '#fff', color: '#254760', borderBottom: '1px solid #d6dfe6', fontSize: 14 }}>
        <a href="/compass" aria-current={historical ? undefined : 'page'}>2026 级课途</a>
        <a href="/compass?cohort=2025" aria-current={historical ? 'page' : undefined}>2023–2025 级课程地图</a>
      </nav>
      <iframe
        title={historical ? '往届课程地图' : '课途课程规划器'}
        src={historical ? '/compass/cohort-map.html?' + mapQuery.toString() : '/compass/planner.html'}
        referrerPolicy="same-origin"
        style={{ display: 'block', width: '100%', flex: 1, minHeight: 0, border: 0 }}
      />
    </main>
  );
}
