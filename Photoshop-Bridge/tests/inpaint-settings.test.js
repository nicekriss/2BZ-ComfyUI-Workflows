const {test}=require('node:test'),assert=require('node:assert/strict');
const policy=require('../plugin/inpaint-settings.js');
const {makePrompt}=require('../plugin/protocol.js'),template=require('../plugin/pro-template.json');
test('legacy saved inpainting switches off lineart without losing model settings or denoise',()=>{
 const old={inpaint:true,lineart:true,denoise:.6,modelRecipe:{checkpoint:'user-model',loras:[]},prompt:'closed eyes'};const saved=policy.restore(old);
 assert.equal(saved.lineart,false);assert.equal(saved.denoise,.6);assert.deepEqual(saved.modelRecipe,old.modelRecipe);assert.equal(old.lineart,true);
 assert.equal(policy.restore({...old,inpaint:false}).lineart,true);assert.equal(policy.restore(null),null);
});
test('enable event persists lineart off before generation, explicit override survives reload',()=>{
 const input=checked=>({checked,addEventListener(name,handler){this.change=handler;}});
 const inpaint=input(false),lineart=input(true),denoise={value:'1'};let saved,notice;
 policy.bind({inpaint,lineart,denoise,persist(){saved={inpaint:inpaint.checked,lineart:lineart.checked,denoise:Number(denoise.value),inpaintLineartPolicy:policy.POLICY};},status(s){notice=s;}});
 inpaint.checked=true;inpaint.change();assert.equal(saved.lineart,false);assert.equal(saved.denoise,.75);assert.match(notice,/라인아트/);
 const main={name:'input.png',selection:'mask.png',width:1024,height:1024,selectionBounds:{left:300,top:300,right:700,bottom:420}};
 assert.equal(makePrompt(template,saved,{main})['53'].inputs.value,false);
 saved.lineart=true;const restored=policy.restore(JSON.parse(JSON.stringify(saved)));assert.equal(restored.lineart,true);assert.equal(makePrompt(template,restored,{main})['53'].inputs.value,true);
 lineart.checked=true;inpaint.checked=false;inpaint.change();assert.equal(saved.lineart,true);
 inpaint.checked=true;inpaint.change();assert.equal(saved.lineart,false);
});
