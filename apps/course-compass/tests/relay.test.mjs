import test from 'node:test';import assert from 'node:assert/strict';import {handleModel} from '../lib/model-relay.mjs';
test('relay never calls provider without a key',async()=>{const r=await handleModel(new Request('https://example.test/api/model',{method:'POST',body:'{}'}));assert.equal(r.status,401);});
test('relay rejects cross-origin submission before processing credentials',async()=>{const r=await handleModel(new Request('https://example.test/api/model',{method:'POST',headers:{origin:'https://another.test'},body:'{}'}));assert.equal(r.status,403);});
test('relay rejects unsupported method',async()=>{assert.equal((await handleModel(new Request('https://example.test/api/model'))).status,405);});
