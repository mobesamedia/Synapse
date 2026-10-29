// Release-review regressions. Only synthetic notes and a temporary browser profile.
// Optional SYNAPSE_REVIEW_ROOT points to an extracted older release for comparison.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const failures=[];
  try{
    const page=await browser.newPage();
    await page.route('https://**/*',route=>route.abort());
    await page.addInitScript(()=>window.pycmd=()=>{});
    const root=process.env.SYNAPSE_REVIEW_ROOT||path.resolve(__dirname,'..');
    const load=async data=>{
      await page.goto(pathToFileURL(path.join(root,'web_notebook/index.html')).href);
      await page.evaluate(data=>loadContent(JSON.stringify(data)),data);
    };
    const state=()=>page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload()));
    await load({pages:[{id:'A',title:'Toggle test',icon:'',blocks:[{type:'toggle',html:'',body:'<b>IMPORTANT BODY CONTENT</b>',open:true}]}],activePageId:'A'});
    await page.locator('.toggle-title').focus();
    await page.keyboard.press('Backspace');
    try{
      assert.ok(JSON.stringify(await state()).includes('IMPORTANT BODY CONTENT'),'Backspace in an empty title must preserve the nonempty toggle body');
      console.log('PASS empty toggle title preserves its body');
    }catch(error){failures.push(error.message);}
    // A blank title can still contain an image, and an invisible/protected body
    // can still contain original data. Neither may be replaced with an empty block.
    for (const [html, body] of [
      ['', '<img src="data:image/png;base64,iVBORw0KGgo=">'],
      ['', '<script>window.shouldNotExecute=true</script>'],
      ['<img src="data:image/png;base64,iVBORw0KGgo=">', ''],
      ['', '   '],
    ]) {
      const blocks=[{type:'toggle',html,body,open:false,extra:{keep:true}}];
      await load({pages:[{id:'A',title:'Preserve',icon:'',blocks}],activePageId:'A'});
      await page.evaluate(()=>document.querySelector('.toggle-title').dispatchEvent(new KeyboardEvent('keydown',{key:'Backspace',bubbles:true,cancelable:true})));
      try{assert.deepEqual((await state()).pages[0].blocks,blocks);}
      catch(error){failures.push('Toggle image/protected content/metadata: '+error.message);}
    }
    await load({pages:[{id:'A',title:'Empty toggle',icon:'',blocks:[{type:'toggle',html:'',body:'',open:true,extra:'keep'}]}],activePageId:'A'});
    await page.locator('.toggle-title').focus();await page.keyboard.press('Backspace');
    try{
      assert.equal((await state()).pages[0].blocks[0].type,'text');
      assert.equal((await state()).pages[0].blocks[0].extra,'keep');
      await page.keyboard.press('Control+z');
      assert.equal((await state()).pages[0].blocks[0].type,'toggle');
    }catch(error){failures.push('Empty toggle conversion and undo: '+error.message);}
    await load({pages:[
      {id:'same',title:'First original',icon:'',blocks:[{type:'text',html:'FIRST UNIQUE CONTENT'}]},
      {id:'same',title:'Second original',icon:'',blocks:[{type:'text',html:'SECOND UNIQUE CONTENT'}]},
    ],activePageId:'same'});
    await page.evaluate(()=>addNewPage());
    await page.keyboard.press('Control+z');
    try{
      const result=JSON.stringify(await state());
      assert.ok(result.includes('FIRST UNIQUE CONTENT')&&result.includes('SECOND UNIQUE CONTENT'),'Undoing page creation must preserve both originals when legacy page IDs collide');
      console.log('PASS colliding legacy page IDs preserve both original contents');
    }catch(error){failures.push(error.message);}
    try{
      const current=await state();
      assert.equal(current.pages.length,3,'Unsafe history must leave page creation in place');
      assert.equal(current.pages[0].id,'same');assert.equal(current.pages[1].id,'same');
      assert.equal(await page.locator('#notebook-back').isDisabled(),true);
      await page.keyboard.press('Control+Shift+z');
      assert.deepEqual((await state()).pages,current.pages,'Redo must also preserve colliding IDs');
      await page.evaluate(()=>deletePage({stopPropagation(){}},'same'));
      assert.deepEqual((await state()).pages,current.pages,'An ambiguous delete must not remove either original page');
    }catch(error){failures.push('Unsafe history no-op: '+error.message);}
  }finally{await browser.close();}
  failures.forEach(message=>console.error('FAIL '+message));
  if(failures.length)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
