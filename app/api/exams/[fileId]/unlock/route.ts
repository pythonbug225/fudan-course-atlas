import { env } from 'cloudflare:workers';
import { unlockExamResponse } from '../../../../../lib/points';

export const dynamic = 'force-dynamic';

export async function POST(req: Request, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params;
  return unlockExamResponse(req, env.DB ?? null, fileId);
}
