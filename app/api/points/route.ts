import { env } from 'cloudflare:workers';
import { getPointsResponse } from '../../../lib/points';
import { withStudentAccess } from '../../../lib/student-access';

export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  return withStudentAccess(req, verified => getPointsResponse(verified, env.DB ?? null));
}
