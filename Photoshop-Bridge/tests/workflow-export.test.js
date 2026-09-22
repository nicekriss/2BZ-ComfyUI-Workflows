const {test}=require('node:test');
const assert=require('node:assert/strict');
const {executionGraph}=require('../plugin/workflow-export.js');
const template=require('../plugin/pro-template.json');
test('export preserves all execution values and links without sharing references',()=>{
  const out=executionGraph(template);
  for(const [id,node] of Object.entries(template)) {
    assert.equal(out[id].class_type,node.class_type);
    assert.deepEqual(out[id].inputs,node.inputs);
    assert.notEqual(out[id].inputs,node.inputs);
  }
});
test('export strips non-execution metadata and handles dynamic LoRA IDs',()=>{
  const out=executionGraph({'1':{class_type:'Loader',inputs:{name:'model'},token:'secret',_meta:{title:'선화',private:'secret'}},tb_lora_1:{class_type:'LoraLoader',inputs:{model:['1',0],strength_model:0.55}}});
  assert.equal(JSON.stringify(out).includes('secret'),false);
  assert.equal(out['1']._meta.title,'라인아트');
  assert.deepEqual(out.tb_lora_1.inputs.model,['1',0]);
  assert.throws(()=>executionGraph({base:'http://localhost',token:'secret'}));
  assert.throws(()=>executionGraph({'1':{class_type:'X',inputs:{image:['missing',0]}}}));
});
