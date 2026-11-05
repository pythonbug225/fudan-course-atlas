import {remove} from '../../../../lib/community';
import {withStudentAccess} from '../../../../lib/student-access';
export const dynamic='force-dynamic';
export async function DELETE(req:Request,{params}:{params:Promise<{id:string}>}){const id=(await params).id;return withStudentAccess(req,verified=>remove(verified,id));}
