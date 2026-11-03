import { env } from 'cloudflare:workers';
import { checkInResponse } from '../../../../lib/points';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  return checkInResponse(req, env.DB ?? null);
}
