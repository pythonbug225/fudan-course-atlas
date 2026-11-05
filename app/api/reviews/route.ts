import {list,submit,json} from '../../../lib/community';
import {withStudentAccess} from '../../../lib/student-access';
export const dynamic='force-dynamic';
export async function GET(req:Request){return withStudentAccess(req,list);}
export async function POST(req:Request){try{return await withStudentAccess(req,submit);}catch{return json({error:'保存失败，请稍后重试，填写内容仍保留在页面中。'},500);}}
