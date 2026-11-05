import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
process.stdin.setEncoding('utf8');if(process.stdin.isTTY)process.stdin.setRawMode(true);
console.log('Ready for private asset publication JSON on stdin (input is hidden).');
const line=await new Promise(resolve=>{let value='';process.stdin.on('data',chunk=>{value+=chunk;const end=value.search(/[\r\n]/);if(end>=0)resolve(value.slice(0,end));});});
process.stdin.pause();if(process.stdin.isTTY)process.stdin.setRawMode(false);
const child=spawn('python',[fileURLToPath(new URL('./publish_private_assets.py',import.meta.url))],{stdio:['pipe','inherit','inherit']});
child.stdin.end(line+'\n');child.on('error',()=>{console.error('Python 3 is required for the asset publisher.');process.exitCode=1;});child.on('exit',code=>process.exit(code??1));
