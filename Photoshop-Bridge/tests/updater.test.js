const {test} = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {latest, compare, sha256, verify, check, download, RELEASES} = require('../plugin/updater.js');
const bytes = new Uint8Array([80,75,3,4,1,2,3]).buffer;
const digest = crypto.createHash('sha256').update(Buffer.from(bytes)).digest('hex');
function release(v) { return {tag_name:'photoshop-bridge-v'+v,prerelease:true,assets:[{name:'toobusy.photoshop.bridge_PS.ccx',size:bytes.byteLength,digest:'sha256:'+digest,browser_download_url:RELEASES+'/download/photoshop-bridge-v'+v+'/toobusy.photoshop.bridge_PS.ccx'}]}; }
test('selects only Bridge release, compares numeric versions, permits our prereleases',()=>{
  assert.equal(compare('0.2.10','0.2.9'),1);
  assert.equal(latest([{tag_name:'yue2-v99.0.0'},release('0.2.9'),release('0.2.10'),{...release('9.0.0'),draft:true},{tag_name:'photoshop-bridge-v9.0.0-rc1'}],'0.2.2').version,'0.2.10');
  assert.equal(latest([release('0.2.2')],'0.2.2'),null);
  assert.equal(latest([release('0.2.1')],'0.2.2'),null);
});
test('old releases offer page fallback without guessing an asset',()=>{
  assert.equal(latest([{...release('0.2.2'),assets:[]}],'0.2.0').asset,null);
  assert.throws(()=>latest({},'0.2.0'));
  assert.throws(()=>latest([],'0.2.0'));
});
test('rejects mismatched origin, oversized assets and missing digest',()=>{
  for(const change of [{browser_download_url:'https://evil.example/file.ccx'},{size:100000000},{digest:null},{size:-1}]) {
    const r=release('0.2.2');Object.assign(r.assets[0],change);
    assert.throws(()=>latest([r],'0.2.0'));
  }
});
test('SHA-256 agrees with Node crypto at block/padding boundaries and real-sized data',()=>{
  for(const length of [0,1,55,56,63,64,65,127,128,1000000]) {
    const data=crypto.randomBytes(length);
    assert.equal(sha256(data),crypto.createHash('sha256').update(data).digest('hex'));
  }
});
test('modified or truncated downloads cannot be installed',()=>{
  const asset=latest([release('0.2.2')],'0.2.0').asset;
  verify(bytes,asset);
  assert.throws(()=>verify(new Uint8Array(7).buffer,asset));
  assert.throws(()=>verify(new Uint8Array(6).buffer,asset));
});
test('GitHub requests do not contain local/Civitai tokens; paginated lookup',async()=>{
  let calls=0;
  const fetcher=async(url,options)=>{
    calls++; assert.equal(options.credentials,'omit');assert.deepEqual(Object.keys(options.headers),['Accept']);
    return {ok:true,json:async()=>calls===1?Array.from({length:100},()=>({tag_name:'unrelated'})):[release('0.2.2')]};
  };
  assert.equal((await check('0.2.0',fetcher)).version,'0.2.2');assert.equal(calls,2);
});
test('rate limit and network failure are retryable, never reported as up to date',async()=>{
  await assert.rejects(check('0.2.0',async()=>({ok:false,status:403})),/한도/);
  await assert.rejects(check('0.2.0',async()=>{throw new Error('offline');}),/offline/);
});
test('download verifies response before returning bytes',async()=>{
  const u=latest([release('0.2.2')],'0.2.0');
  const response=data=>async()=>({ok:true,headers:{get:()=>String(data.byteLength)},arrayBuffer:async()=>data});
  assert.equal(await download(u,response(bytes)),bytes);
  await assert.rejects(download(u,response(new Uint8Array(7).buffer)),/검증/);
});
