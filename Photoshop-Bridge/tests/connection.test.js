const {test}=require('node:test'); const assert=require('node:assert/strict');
const {connection,applyPaths}=require('../plugin/connection');
test('installer connection accepts only a local endpoint, pairing token and known relative model paths',()=>{
  const valid={token:'a'.repeat(64),server:'http://127.0.0.1:8189',modelPaths:{'7':'test_controlnet2/cn.safetensors'}};
  const value=connection(valid),template=JSON.parse(JSON.stringify(require('../plugin/pro-template.json')));
  applyPaths(template,value); assert.equal(template['7'].inputs.control_net_name,valid.modelPaths['7']);
  for(const change of [{token:''},{server:'https://example.com'},{server:'http://localhost:0'},{modelPaths:{'7':'../../outside'}},{modelPaths:{'999':'anything'}},{modelPaths:{'7':'D:/file'}}]) assert.throws(()=>connection({...valid,...change}));
});
