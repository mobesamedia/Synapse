const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),{pathToFileURL}=require('node:url');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
for(const file of ['index.html','web_roadmap/index.html']){
 const page=await browser.newPage({viewport:{width:1100,height:800}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('mindmaps',JSON.stringify({test:{name:'Resize',nodes:[{id:1,parent:null,text:'Image',x:100,y:100,image:'a'.repeat(64)+'.png',imageWidth:120,imageHeight:80}]}})));
 await page.goto(pathToFileURL(path.resolve(__dirname,'..',file)).href);
 await page.waitForFunction(()=>!!window.__synapseSetWindow);
 await page.evaluate(()=>{for(const active of [true,false,true,false]){__synapseSetWindow(active,{enter:'Enlarge',exit:'Reduce'});__synapseSetFullscreen(active,{enter:'Fullscreen',exit:'Exit'});}});
 assert.equal(await page.locator('#workspace-window').getAttribute('title'),'Enlarge');assert.equal(await page.locator('#workspace-full').getAttribute('title'),'Fullscreen');
 assert.deepEqual(errors,[]);
 if(file==='index.html'){
  await page.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});
  const handle=page.locator('#node-1 .node-resize-handle'),box=await handle.boundingBox();
  await page.mouse.move(box.x+8,box.y+8);await page.mouse.down();await page.mouse.move(box.x+150,box.y+100,{steps:8});await page.mouse.up();
  let doc=await page.evaluate(()=>__workspaceDocument());assert(doc.nodes[0].imageDisplayWidth>230);assert.equal(doc.nodes[0].imageWidth,120);
  assert.equal(await page.locator('.node-image').evaluate(e=>e.style.maxHeight),'none');
  const before=await page.evaluate(()=>localStorage.getItem('mindmaps'));
  await page.evaluate(()=>window.dispatchEvent(new ErrorEvent('error',{error:new Error('Synthetic failure')})));
  assert.equal((await page.evaluate(()=>__synapseFlushMindmap())).snapshot,null);
  assert.equal(await page.evaluate(()=>localStorage.getItem('mindmaps')),before);
  assert(await page.evaluate(()=>__workspaceDocument()));
 }else{
  await page.locator('#add-menu summary').click();await page.locator('[data-shape=rect]').click();
  await page.evaluate(()=>document.documentElement.classList.add('dark'));
  await page.waitForFunction(()=>document.querySelector('.object-hit rect')?.getAttribute('fill')==='#2c2c2c');
  assert.equal(await page.locator('.shape-text').first().evaluate(e=>e.style.color),'rgb(255, 255, 255)');
  await page.evaluate(()=>document.documentElement.classList.remove('dark'));
  await page.waitForFunction(()=>document.querySelector('.object-hit rect')?.getAttribute('fill')==='#ffffff');
  await page.locator('#object-toolbar input[type=color]').nth(1).evaluate(e=>{e.value='#ffffff';e.dispatchEvent(new Event('change'));});
  await page.evaluate(()=>document.documentElement.classList.add('dark'));
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(await page.locator('.object-hit rect').first().getAttribute('fill'),'#ffffff');
  await page.evaluate(()=>window.dispatchEvent(new ErrorEvent('error',{error:new Error('Synthetic failure')})));
  assert.equal(await page.evaluate(()=>__roadmapSnapshot()),null);
  assert.match(await page.locator('#message').innerText(),/Editing paused/);
  assert(await page.evaluate(()=>__workspaceDocument()));
 }
 await page.close();
}
const page=await browser.newPage();await page.goto(pathToFileURL(path.resolve(__dirname,'../web_roadmap/index.html')).href);
assert.equal(await page.evaluate(()=>{const u=Array(50).fill('x'.repeat(200000)),r=Array(20).fill('y'.repeat(200000));workspaceTrimHistory(u,r);return u.concat(r).reduce((n,s)=>n+s.length,0);}),8000000);
await page.evaluate(()=>workspaceCheckSize(Array(1999).fill({text:'small'}),'small'));assert.equal(await page.locator('#message').isVisible(),false);
await page.evaluate(()=>workspaceCheckSize(Array(2000).fill({text:'large'}),'large'));assert.match(await page.locator('#message').innerText(),/Large document/);
console.log('PASS window/fullscreen label objects, image scaling, live dark theme, error write fence, bounded undo/redo');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
