// Run with Playwright installed; uses temporary browser profiles and synthetic data only.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const root=require('node:path').resolve(__dirname, '..');
const fileUrl=p=>require('node:url').pathToFileURL(root+p).href;
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.SYNAPSE_TEST_CHROME ? {executablePath:process.env.SYNAPSE_TEST_CHROME} : {})});
 try {
 const context=await browser.newContext();
 await context.route('http://**/*',r=>r.abort());await context.route('https://**/*',r=>r.abort());
 const page=await context.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.pycmd=()=>{};});
 await page.goto(fileUrl('/web_notebook/index.html'));
 await page.evaluate(()=>loadContent(JSON.stringify({pages:[{id:'A',title:'Page A',icon:'',blocks:[{type:'text',html:'Original A'}]},{id:'B',title:'Page B',icon:'',blocks:[{type:'text',html:'Original B'}]}],activePageId:'A'})));
 await page.locator('#editor .block').first().fill('Edited A');
 await page.keyboard.press('Control+z');
 assert.equal(await page.locator('#editor').innerText(),'Original A');
 await page.keyboard.press('Control+Shift+Z');
 assert.equal(await page.locator('#editor').innerText(),'Edited A');
 // Pending snapshot from A must never appear in B.
 await page.evaluate(()=>loadPage('B'));
 await page.keyboard.press('Control+z');
 assert.equal(await page.locator('#editor').innerText(),'Original B');
 await page.locator('#editor .block').first().fill('Edited B');
 await page.waitForTimeout(1400);await page.keyboard.press('Control+z');
 assert.equal(await page.locator('#editor').innerText(),'Original B');
 await page.keyboard.press('Control+Shift+Z');assert.equal(await page.locator('#editor').innerText(),'Edited B');
 const snapshot=await page.evaluate(()=>{persistNow();return JSON.parse(window.__synapseSnapshotForVerification())});
 assert.equal(snapshot.pages.find(p=>p.id==='A').blocks[0].html,'Edited A');
 assert.equal(snapshot.pages.find(p=>p.id==='B').blocks[0].html,'Edited B');
 console.log('PASS Notebook first-edit undo, delayed undo, redo, page isolation and saved data');
 await page.goto(fileUrl('/web_notebook/todo.html'));
 const task={id:'safe1',text:'Original task',tag:'old',done:true,createdAt:'Jan 2',futureField:'preserve'};
 await page.evaluate(t=>loadTodos(JSON.stringify([t])),task);
 let replies=['Updated task','new'];const dialog=d=>{const a=replies.shift();a===null?d.dismiss():d.accept(a)};page.on('dialog',dialog);
 await page.locator('.todo-item').hover();
 await page.getByRole('button',{name:'Edit',exact:true}).click();
 let saved=await page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload()));assert.deepEqual(saved,[{...task,text:'Updated task',tag:'new'}]);
 replies=['Cancelled text',null];await page.evaluate(()=>editTodo('safe1'));
 assert.deepEqual(await page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload())),saved);
 replies=['   '];await page.evaluate(()=>editTodo('safe1'));
 assert.deepEqual(await page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload())),saved);
 page.off('dialog',dialog);
 console.log('PASS ToDo edit, both cancellation/blank cases, IDs and unknown fields preserved');
 assert.deepEqual(errors,[]);await context.close();
 // Separate browser storage for each recovery scenario; no real profile is read.
 for (const scenario of ['empty','orphan-time','newer-local','fresh']) {
  const c=await browser.newContext();await c.route('https://**/*',r=>r.abort());const p=await c.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
  await p.addInitScript(({scenario})=>{
   const map=name=>({name,nodes:[{id:1,text:name,parent:null,x:0,y:0,width:154,height:51,color:'#0071D3',size:'medium'}]});
   if(scenario!=='fresh') window.__SYNAPSE_MM_RECOVERY__={version:1,saved_at:1000,mindmaps:{saved:map('Recovered')}};
   if(scenario==='orphan-time') localStorage.setItem('mindmaps_saved_at','9000');
   if(scenario==='newer-local'){localStorage.setItem('mindmaps',JSON.stringify({local:map('Current')}));localStorage.setItem('mindmaps_saved_at','9000');}
  },{scenario});
  await p.goto(fileUrl('/index.html'));await p.waitForFunction(()=>window.__synapseFlushMindmap);
  const maps=await p.evaluate(()=>JSON.parse(localStorage.getItem('mindmaps')));
  if(scenario==='fresh') assert.ok(Object.keys(maps).some(k=>k.startsWith('map_tutorial_')));
  else assert.deepEqual(Object.keys(maps),[scenario==='newer-local'?'local':'saved']);
  assert.deepEqual(errs,[]);console.log('PASS Mindmap '+scenario);await c.close();
 }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
