const {test} = require("node:test");
const assert = require("node:assert/strict");
const M = require("../plugin/model-settings.js");
const {makePrompt} = require("../plugin/protocol.js");
const template = require("../plugin/pro-template.json");
const input = {main:{name:"TooBusyPS/test.png"}};
const graph = recipe => makePrompt(template,{workflow:"pro",modelRecipe:recipe},input);
test("legacy LoRA weight migrates; reset is a fresh immutable default", () => {
  const original = JSON.stringify(template);
  const migrated = M.migrateRecipe({lora:0.8},template);
  assert.equal(migrated.loras[0].strength,0.8);
  migrated.loras.length=0;
  assert.equal(M.defaultRecipe(template).loras[0].strength,0.55);
  assert.equal(JSON.stringify(template),original);
});
test("checkpoint switch preserves VAE and control graph while chaining model and CLIP through two LoRAs", () => {
  const recipe = {checkpoint:"illustrious/other.safetensors",loras:[{name:"paint.safetensors",enabled:true,strength:0.55},{name:"character.safetensors",enabled:true,strength:0.3}]};
  const g=graph(recipe);
  assert.equal(g["1"].inputs.ckpt_name,recipe.checkpoint);
  assert.deepEqual(g["17"].inputs.model,["1",0]);
  assert.deepEqual(g.tb_lora_1.inputs.model,["17",0]);
  assert.deepEqual(g.tb_lora_1.inputs.clip,["17",1]);
  for(const [id,node] of Object.entries(template)) if(id!=="17") for(const [key,value] of Object.entries(node.inputs)) {
    if(Array.isArray(value)&&value[0]==="17") assert.deepEqual(g[id].inputs[key],["tb_lora_1",value[1]]);
    if(Array.isArray(value)&&value[0]==="1"&&value[1]===2) assert.deepEqual(g[id].inputs[key],value);
  }
  assert.equal(g["9"].class_type,template["9"].class_type);
  assert.equal(g.tb_lora_1.inputs.strength_clip,0.3);
});
test("disabled and zero-weight missing LoRAs are pruned, leaving valid base MODEL and CLIP links", () => {
  const recipe={checkpoint:"base",loras:[{name:"missing",enabled:false,strength:1},{name:"missing2",enabled:true,strength:0}]};
  const g=graph(recipe);
  assert.equal(g["17"],undefined);
  assert.deepEqual(g["2"].inputs.clip,["1",1]);
  for(const node of Object.values(g)) for(const value of Object.values(node.inputs)) if(Array.isArray(value)) assert.ok(g[value[0]],"dangling link "+value[0]);
});
test("eight LoRAs connect in order without mutating recipe or template", () => {
  const recipe={checkpoint:"base",loras:Array.from({length:8},(_,i)=>({name:i+".safetensors",enabled:true,strength:0.1}))};
  const before=JSON.stringify({recipe,template});const g=graph(recipe);
  assert.deepEqual(g["2"].inputs.clip,["tb_lora_7",1]);
  assert.equal(JSON.stringify({recipe,template}),before);
  recipe.loras.push({name:"9",enabled:true,strength:1});assert.throws(()=>graph(recipe));
});
test("installed files work without registration; resolution refuses ambiguity and missing enabled weights", () => {
  const recipe={checkpoint:"old/base.safetensors",loras:[{name:"old/a.safetensors",enabled:true,strength:0.3}]};
  const available={checkpoints:["client\\base.safetensors"],loras:["client\\a.safetensors"]};
  const resolved=M.resolveRecipe(recipe,available);
  assert.equal(resolved.checkpoint,"client\\base.safetensors");
  assert.equal(resolved.loras[0].name,"client\\a.safetensors");
  assert.throws(()=>M.resolveRecipe(recipe,{...available,loras:[]}),/없는/);
  assert.throws(()=>M.resolveFile("old/base.safetensors",["a/base.safetensors","b/base.safetensors"]),/여러/);
});
test("invalid strengths and duplicate active LoRAs are rejected before submission", () => {
  const recipe=M.defaultRecipe(template);
  for(const value of [NaN,Infinity,-3,3,"0.5"]) {recipe.loras[0].strength=value;assert.throws(()=>M.normalizeRecipe(recipe));}
  recipe.loras[0].strength=0.5;recipe.loras.push({...recipe.loras[0]});assert.throws(()=>M.normalizeRecipe(recipe),/중복/);
});
test("preset round trip owns a snapshot, rejects duplicate names and corrupt recipes", () => {
  const recipe=M.defaultRecipe(template), presets=M.savePreset([],"My blend",recipe);
  recipe.loras[0].strength=1.2;
  assert.equal(JSON.parse(JSON.stringify(presets))[0].recipe.loras[0].strength,0.55);
  assert.throws(()=>M.savePreset(presets,"My blend",recipe),/이미/);
  assert.throws(()=>M.savePreset(presets," ",recipe));
});
