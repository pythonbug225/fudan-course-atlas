import {env} from 'cloudflare:workers';
import {createStudentAuth} from './student-auth';
/** Route-level validation also covers framework previews and server dispatch. */
export async function withStudentAccess(req:Request, next:(verified:Request)=>Promise<Response>){
  const access=await createStudentAuth(env).handle(req);
  return access.response ?? next(access.request!);
}
