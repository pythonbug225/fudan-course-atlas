import {env} from 'cloudflare:workers';
import {createStudentAuth} from '../../../lib/student-auth';
export const dynamic='force-dynamic';
export async function GET(req:Request){return (await createStudentAuth(env).handle(req)).response!;}
