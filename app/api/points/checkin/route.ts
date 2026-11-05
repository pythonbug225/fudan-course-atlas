import { env } from 'cloudflare:workers';
import { checkInResponse } from '../../../../lib/points';
import { withStudentAccess } from '../../../../lib/student-access';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  return withStudentAccess(req, verified => checkInResponse(verified, env.DB ?? null));
}
