import {mine} from '../../../../lib/community';
import {withStudentAccess} from '../../../../lib/student-access';
export const dynamic='force-dynamic';
export async function GET(req:Request){return withStudentAccess(req,mine);}
