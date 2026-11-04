import { env } from 'cloudflare:workers';
import { createCommunity } from './community-core';
const community=createCommunity(env);
export const {json,user,checkWrite,list,submit,remove,attachment,isModerator,mine,moderationList,moderate}=community;
