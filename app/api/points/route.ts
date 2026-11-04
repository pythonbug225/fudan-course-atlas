import { env } from 'cloudflare:workers';
import { getPointsResponse } from '../../../lib/points';

export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  return getPointsResponse(req, env.DB ?? null);
}
