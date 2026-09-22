const {test}=require('node:test'),assert=require('node:assert/strict');
const {selectionBounds,cropRegion}=require('../plugin/inpaint.js');
const {makePrompt}=require('../plugin/protocol.js');const template=require('../plugin/pro-template.json');
test('selection bounds retain feathered pixels, offsets, and empty selection',()=>{
 const m=new Uint8Array(15);m[7]=1;m[13]=255;assert.deepEqual(selectionBounds(m,5,3),{left:2,top:1,right:4,bottom:3});assert.equal(selectionBounds(new Uint8Array(15),5,3),null);assert.throws(()=>selectionBounds(m,3,3));
});
test('context crops contain selections and stay inside odd sized, edge and small canvases',()=>{
 for(const [width,height] of [[1013,777],[32,17],[8192,4096]])for(const b of [{left:0,top:0,right:1,bottom:1},{left:width-1,top:height-1,right:width,bottom:height},{left:0,top:0,right:width,bottom:height}]){
 const c=cropRegion({width,height,selectionBounds:b},{maskExpand:8,maskBlur:6});assert.ok(c.x>=0&&c.y>=0&&c.x+c.width<=width&&c.y+c.height<=height);assert.ok(c.x<=b.left&&c.y<=b.top&&c.x+c.width>=b.right&&c.y+c.height>=b.bottom);assert.equal(c.workWidth%16,0);assert.equal(c.workHeight%16,0);assert.equal(Math.max(c.workWidth,c.workHeight),1024);
 }
 assert.throws(()=>cropRegion({width:1024,height:1024},{}),/다시 싱크/);
});
test('inpaint keeps LoRA and reference controls, sampling crop and restoring canvas coordinates',()=>{
 const before=JSON.stringify(template),main={name:'image.png',selection:'mask.png',width:1024,height:1024,selectionBounds:{left:282,top:281,right:783,bottom:406}};
 const settings={inpaint:true,lineart:true,depth:true,pose:true,style:true,maskExpand:8,maskBlur:6,modelRecipe:{checkpoint:'model',loras:[{name:'a',enabled:true,strength:.5},{name:'b',enabled:true,strength:.3}]}};
 const g=makePrompt(template,settings,{main,reference:{name:'reference.png'},style:{name:'style.png'}});
 assert.deepEqual(g['59'].inputs.model,['tb_lora_1',0]);assert.deepEqual(g.tb_inpaint_model.inputs.model,['60',0]);assert.deepEqual(g['38'].inputs.image,g['47'].inputs.image);assert.deepEqual(g['9'].inputs.image,g['31'].inputs.pixels);assert.deepEqual(g.tb_inpaint_mask_crop.inputs.mask,['62',0]);assert.deepEqual(g['65'].inputs.destination,['4',0]);assert.equal(g['65'].inputs.x,g.tb_inpaint_crop.inputs.x);assert.equal(g['65'].inputs.y,g.tb_inpaint_crop.inputs.y);
 for(const n of Object.values(g))for(const v of Object.values(n.inputs))if(Array.isArray(v))assert.ok(g[v[0]],'dangling '+v[0]);
 assert.equal(JSON.stringify(template),before);
 assert.deepEqual(g.tb_inpaint_color.inputs.image_ref,g['31'].inputs.pixels);assert.deepEqual(g.tb_inpaint_color.inputs.image_target,['11',0]);assert.deepEqual(g.tb_inpaint_restore.inputs.image,['tb_inpaint_color',0]);
 const normal=makePrompt(template,{...settings,inpaint:false},{main,reference:{name:'ref'},style:{name:'style'}});assert.equal(normal.tb_inpaint_model,undefined);assert.deepEqual(normal['31'].inputs.pixels,['4',0]);assert.deepEqual(normal['10'].inputs.model,['60',0]);
});
