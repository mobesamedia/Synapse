const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),{pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..'),link={version:1,kind:'note',noteGuid:'test-guid',noteId:'123',label:'Mitochondrion'},card={...link,kind:'card',cardId:'456',cardOrd:0,template:'Card 1'};
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const errors=[];
 for(const file of ['index.html','web_roadmap/index.html']){
  const page=await browser.newPage({viewport:{width:1100,height:800}});page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{localStorage.setItem('mindmaps',JSON.stringify({test:{name:'Links',nodes:[{id:1,parent:null,text:'Mitochondrion',x:100,y:100}]}}));});
  await page.goto(pathToFileURL(path.join(root,file)).href);
  await page.evaluate(()=>{window.__SYNAPSE_MM_HOSTED__=true;window.__synapseMindmapCommand=command=>window.command=command;});
  if(file==='index.html'){
   await page.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});await page.locator('#node-1 .node-textarea').click({button:'right'});
   await page.locator('#context-menu').getByRole('button',{name:'Link Card',exact:true}).click();
  }else{
   await page.locator('#add-menu summary').click();await page.locator('[data-shape=rect]').click();
   await page.locator('#object-toolbar').getByRole('button',{name:'Link Card',exact:true}).click();
  }
  const request=await page.evaluate(()=>JSON.parse(decodeURIComponent(command.slice(command.indexOf(':')+1))));assert.equal(request.links.length,0);
  await page.evaluate(({request,link})=>__workspaceLinksPicked({requestId:request.requestId,links:[link]}),{request,link});
  const badge=page.locator('.workspace-anki-link');await badge.click();assert.match(await page.evaluate(()=>command),/^anki-open:/);
  await badge.focus();await page.keyboard.press('Space');assert.match(await page.evaluate(()=>command),/^anki-open:/);
  const doc=await page.evaluate(()=>__workspaceDocument());const entries=doc.nodes||doc.objects;assert.deepEqual(entries[0].ankiLinks,[link]);
  await page.locator(file==='index.html'?'#undo-btn':'#undo').click();assert.equal(await badge.count(),0);
  await page.locator(file==='index.html'?'#redo-btn':'#redo').click();assert.equal(await badge.count(),1);
  // Native cancellation cannot remove an existing reference; multiple links use the manager.
  await page.evaluate(({link,card})=>workspacePickLinks([link],'',value=>window.linkResult=value),{link,card});
  const r=await page.evaluate(()=>JSON.parse(decodeURIComponent(command.split(':').slice(1).join(':'))));
  await page.evaluate(r=>__workspaceLinksPicked({requestId:r.requestId,links:null}),r);assert.equal(await page.evaluate(()=>window.linkResult),undefined);
  // Import/export preserves references, rejects malformed links without replacing current data.
  const payload=file==='index.html'?doc:{version:1,active:doc.id,maps:[doc]};
  await page.evaluate(payload=>__workspaceImported(payload),payload);
  assert.deepEqual((await page.evaluate(()=>__workspaceDocument())).nodes?.[0].ankiLinks||(await page.evaluate(()=>__workspaceDocument())).objects[0].ankiLinks,[link]);
  await page.screenshot({path:path.join(root,'docs',file==='index.html'?'mindmap-anki-links.png':'roadmap-anki-links.png')});
  const invalid=JSON.parse(JSON.stringify(payload));(invalid.nodes||invalid.maps[0].objects)[0].ankiLinks=[{kind:'note',noteId:'123'}];
  await page.evaluate(payload=>__workspaceImported(payload),invalid);
  assert.deepEqual((await page.evaluate(()=>__workspaceDocument())).nodes?.[0].ankiLinks||(await page.evaluate(()=>__workspaceDocument())).objects[0].ankiLinks,[link]);
  await page.close();
 }
 const p=await browser.newPage();p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{window.__ROADMAP_DATA__={version:1,active:'map',maps:[{id:'map',name:'Labels',objects:[{id:'arrow',kind:'arrow',a:{x:100,y:100},b:{x:400,y:100},stroke:'#252525',route:'straight',tip:'triangle',dash:'solid',label:''}],view:{x:0,y:0,scale:1}}]};});
 await p.goto(pathToFileURL(path.join(root,'web_roadmap/index.html')).href);
 p.on('dialog',()=>{throw new Error('Arrow label must not use a JavaScript prompt');});
 const point=await p.locator('[data-arrow=arrow]').evaluate(e=>{const p=e.getPointAtLength(e.getTotalLength()/2),s=new DOMPoint(p.x,p.y).matrixTransform(e.getScreenCTM());return {x:s.x,y:s.y,hit:document.elementFromPoint(s.x,s.y)?.outerHTML};});await p.mouse.dblclick(point.x,point.y);
 await p.locator('#arrow-label-input').fill('Arrow text');await p.locator('#arrow-label-form button[type=submit]').click();
 assert.equal(await p.locator('.arrow-label').textContent(),'Arrow text');
 await p.locator('[data-label=arrow]').click();await p.locator('#arrow-label-input').fill('Cancelled');await p.locator('#arrow-label-cancel').click();assert.equal(await p.locator('.arrow-label').textContent(),'Arrow text');
 await p.locator('button[title="Label arrow"]').click();await p.locator('#arrow-label-size').selectOption('24');await p.locator('#arrow-label-form button[type=submit]').click();assert.equal(await p.locator('.arrow-label').getAttribute('font-size'),'24');
 assert.deepEqual(errors,[]);console.log('PASS both editors: links, badges, open command, undo/redo, cancellation, export/import; direct arrow label + double click');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
