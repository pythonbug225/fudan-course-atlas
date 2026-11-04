import {moderationList,moderate} from '../../../lib/community';
export const dynamic='force-dynamic';
export async function GET(req:Request){return moderationList(req);}
export async function POST(req:Request){return moderate(req);}
