import {json,user,isModerator} from '../../../lib/community';
export const dynamic='force-dynamic';
export async function GET(req:Request){return json({signedIn:!!user(req),isModerator:isModerator(req)});}
