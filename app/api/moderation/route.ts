import {moderationList,moderate} from '../../../lib/community';
import {withStudentAccess} from '../../../lib/student-access';
export const dynamic='force-dynamic';
export async function GET(req:Request){return withStudentAccess(req,moderationList);}
export async function POST(req:Request){return withStudentAccess(req,moderate);}
