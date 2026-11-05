export const dynamic = 'force-dynamic';

export default function CompassPage() {
  return (
    <main style={{ position: 'fixed', inset: 0, margin: 0, padding: 0, overflow: 'hidden' }}>
      <iframe
        title="课途课程规划器"
        src="/compass/planner.html"
        referrerPolicy="same-origin"
        style={{ display: 'block', width: '100%', height: '100%', border: 0 }}
      />
    </main>
  );
}
