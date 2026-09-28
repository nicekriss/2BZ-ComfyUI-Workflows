const {test}=require('node:test'); const assert=require('node:assert/strict');
const {connection,applyPaths,resolveModel,resolvePaths,loaderOptions,missingMessage,MODEL_FIELDS}=require('../plugin/connection');
const template=()=>JSON.parse(JSON.stringify(require('../plugin/pro-template.json')));
test('installer connection accepts only a local endpoint, pairing token and known relative model paths',()=>{
  const valid={token:'a'.repeat(64),server:'http://127.0.0.1:8189',modelPaths:{'7':'test_controlnet2/cn.safetensors'}};
  const value=connection(valid),graph=template();
  applyPaths(graph,value); assert.equal(graph['7'].inputs.control_net_name,valid.modelPaths['7']);
  for(const change of [{token:''},{server:'https://example.com'},{server:'http://localhost:0'},{modelPaths:{'7':'../../outside'}},{modelPaths:{'999':'anything'}},{modelPaths:{'7':'D:/file'}}]) assert.throws(()=>connection({...valid,...change}));
});
test('model names match the server list exactly, then separator-insensitively, then by unique file name',()=>{
  const list=['test_controlnet2\\CN-anytest4_illustrious2_B.safetensors','test_controlnet2\\CN-anytest4_illustrious2_B_fp16.safetensors','xinsir\\controlnet-union-sdxl-promax.safetensors'];
  assert.equal(resolveModel('xinsir\\controlnet-union-sdxl-promax.safetensors',list),list[2]);
  assert.equal(resolveModel('test_controlnet2/CN-anytest4_illustrious2_B_fp16.safetensors',list),list[1]);
  assert.equal(resolveModel('CN-anytest4_illustrious2_B_fp16.safetensors',list),list[1]);
  assert.equal(resolveModel('other/CN-anytest4_illustrious2_B_fp16.safetensors',list),list[1]);
  assert.equal(resolveModel('ip-adapter-plus_sdxl_vit-h.safetensors',[]),null);
  assert.equal(resolveModel('a.safetensors',['x\\a.safetensors','y\\a.safetensors']),null);
  assert.equal(resolveModel('a.safetensors',null),null);
  assert.equal(resolveModel(undefined,['a.safetensors']),null);
});
test('loader options read both list schemas and report absent nodes',()=>{
  assert.deepEqual(loaderOptions({X:{input:{required:{f:[['a','b'],{}]}}}},'X','f'),['a','b']);
  assert.deepEqual(loaderOptions({X:{input:{required:{f:['COMBO',{options:['c']}]}}}},'X','f'),['c']);
  assert.deepEqual(loaderOptions({X:{input:{required:{}}}},'X','f'),[]);
  assert.equal(loaderOptions({},'X','f'),null);
});
test('resolvePaths rewrites the graph to server strings and lists what is missing, mirroring the Desktop failure',()=>{
  const graph=template();
  graph['7'].inputs.control_net_name='test_controlnet2/CN-anytest4_illustrious2_B_fp16.safetensors';
  graph['40'].inputs.control_net_name='xinsir/controlnet-union-sdxl-promax.safetensors';
  const controlnets=['test_controlnet2\\CN-anytest4_illustrious2_B.safetensors','test_controlnet2\\CN-anytest4_illustrious2_B_fp16.safetensors','xinsir\\controlnet-union-sdxl-promax.safetensors'];
  const info={};
  for(const id of Object.keys(MODEL_FIELDS)){
    const node=graph[id],field=MODEL_FIELDS[id];
    const options=id==='58'?[]:(id==='7'||id==='40')?controlnets:[node.inputs[field]];
    info[node.class_type]={input:{required:{[field]:[options,{}]}}};
  }
  const before=JSON.stringify(graph);
  const result=resolvePaths(graph,info);
  assert.equal(graph['7'].inputs.control_net_name,controlnets[1]);
  assert.equal(graph['40'].inputs.control_net_name,controlnets[2]);
  assert.deepEqual(result.missingNodes,[]);
  assert.deepEqual(result.missing.map(m=>[m.id,m.kind,m.desired]),[['58','ipadapter','ip-adapter-plus_sdxl_vit-h.safetensors']]);
  assert.notEqual(JSON.stringify(graph),before);
  const message=missingMessage(result,{ipadapter:['C:\\ComfyUI\\ComfyUI\\models\\ipadapter','C:\\Shared\\models\\ipadapter']});
  assert.match(message,/IP-Adapter: ip-adapter-plus_sdxl_vit-h\.safetensors → 넣을 폴더: C:\\ComfyUI\\ComfyUI\\models\\ipadapter 또는 C:\\Shared\\models\\ipadapter/);
  assert.match(missingMessage(result,undefined),/ComfyUI의 ipadapter 모델 폴더/);
  // A subset check (connection time) ignores the model-library loaders.
  const partial=resolvePaths(template(),{},['7','58']);
  assert.deepEqual(partial.missingNodes,['ControlNetLoader','IPAdapterModelLoader']);
  assert.match(missingMessage(partial),/필요한 노드가 없습니다: ControlNetLoader, IPAdapterModelLoader/);
  // Unchanged when everything already matches exactly.
  const ok=template(),okInfo={};
  for(const id of Object.keys(MODEL_FIELDS)){
    const entry=okInfo[ok[id].class_type]||(okInfo[ok[id].class_type]={input:{required:{[MODEL_FIELDS[id]]:[[],{}]}}});
    entry.input.required[MODEL_FIELDS[id]][0].push(ok[id].inputs[MODEL_FIELDS[id]]);
  }
  const snapshot=JSON.stringify(ok); const fine=resolvePaths(ok,okInfo);
  assert.deepEqual(fine,{missing:[],missingNodes:[]}); assert.equal(JSON.stringify(ok),snapshot);
});
