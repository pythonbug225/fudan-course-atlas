import { env } from 'cloudflare:workers';
import { unlockExamResponse } from '../../../../../lib/points';
import { withStudentAccess } from '../../../../../lib/student-access';

export const dynamic = 'force-dynamic';

export async function POST(req: Request, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params;
  return withStudentAccess(req, verified => unlockExamResponse(verified, env.DB ?? null, fileId));
}
