import {mine} from '../../../../lib/community';
export const dynamic='force-dynamic';
export async function GET(req:Request){return mine(req);}
