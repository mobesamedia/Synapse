const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),{pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const errors=[],mm=await browser.newPage({viewport:{width:760,height:680}});mm.on('pageerror',e=>errors.push(e.message));
 await mm.addInitScript(()=>{localStorage.setItem('mindmaps',JSON.stringify({test:{name:'Cell biology',nodes:[{id:1,parent:null,text:'Mitochondrion',x:120,y:180}]}}));window.__SYNAPSE_MM_DARK__=false;});
 await mm.goto(pathToFileURL(path.join(root,'index.html')).href);await mm.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});
 const openMenu=async()=>{await mm.evaluate(()=>document.querySelector('#node-1').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:360,clientY:210})));};
 await openMenu();await mm.getByRole('button',{name:'Bold',exact:true}).click();await mm.locator('#node-font-size').selectOption('18');
 assert.equal(await mm.locator('#context-menu').isVisible(),true);assert.equal(await mm.getByRole('button',{name:'Bold',exact:true}).getAttribute('aria-pressed'),'true');
 await mm.locator('#node-size-select').selectOption('large');assert.equal((await mm.evaluate(()=>__workspaceDocument())).nodes[0].size,'large');
 for(const dark of [false,true]){await mm.evaluate(d=>document.documentElement.classList.toggle('dark',d),dark);await mm.screenshot({path:path.join(root,'docs/node-menu-'+(dark?'dark':'light')+'.png')});}
 await mm.setViewportSize({width:360,height:560});await openMenu();const menu=await mm.locator('#context-menu').boundingBox();assert(menu.x>=0&&menu.x+menu.width<=360&&menu.y+menu.height<=560);assert(menu.y>=(await mm.locator('#mindmap-container').boundingBox()).y);await mm.screenshot({path:path.join(root,'docs/node-menu-narrow.png')});
 await mm.locator('#node-font-size').press('Escape');assert.equal(await mm.locator('#context-menu').isVisible(),false);
 const rm=await browser.newPage({viewport:{width:760,height:680}});rm.on('pageerror',e=>errors.push(e.message));rm.on('dialog',()=>{throw Error('Unexpected native JS prompt')});
 await rm.addInitScript(()=>{window.__SYNAPSE_MM_DARK__=false;window.__ROADMAP_DATA__={version:1,active:'map',maps:[{id:'map',name:'Learning path',objects:[{id:'arrow',kind:'arrow',a:{x:180,y:200},b:{x:550,y:400},route:'rounded',stroke:'#252525',tip:'triangle',dash:'solid',label:'Produces ATP',labelSize:16}],view:{x:0,y:0,scale:1}}]};});
 await rm.goto(pathToFileURL(path.join(root,'web_roadmap/index.html')).href);
 const point=await rm.locator('[data-arrow=arrow]').evaluate(e=>{const p=e.getPointAtLength(e.getTotalLength()/2);const s=new DOMPoint(p.x,p.y).matrixTransform(e.getScreenCTM());return {x:s.x,y:s.y}});
 await rm.mouse.click(point.x,point.y);assert.equal(await rm.locator('[data-label=arrow]').count(),1);
 await rm.locator('[data-label=arrow]').focus();await rm.keyboard.press('Enter');assert.equal(await rm.locator('#arrow-label-input').inputValue(),'Produces ATP');
 for(const dark of [false,true]){await rm.evaluate(d=>document.documentElement.classList.toggle('dark',d),dark);await rm.screenshot({path:path.join(root,'docs/arrow-label-'+(dark?'dark':'light')+'.png')});}
 await rm.locator('#arrow-label-input').fill('Not saved');await rm.keyboard.press('Escape');assert.equal(await rm.locator('.arrow-label').textContent(),'Produces ATP');
 await rm.locator('[data-label=arrow]').click();await rm.locator('#arrow-label-input').fill('Electron transport');await rm.locator('#arrow-label-size').selectOption('20');await rm.locator('#arrow-label-input').press('Enter');assert.equal(await rm.locator('.arrow-label').textContent(),'Electron transport');
 await rm.locator('#undo').click();assert.equal(await rm.locator('.arrow-label').textContent(),'Produces ATP');await rm.locator('#redo').click();assert.equal(await rm.locator('.arrow-label').textContent(),'Electron transport');
 await rm.mouse.click(point.x,point.y);await rm.locator('[data-label=arrow]').click();await rm.setViewportSize({width:360,height:560});const dialog=await rm.locator('#arrow-label-dialog').boundingBox();assert(dialog.x>=0&&dialog.x+dialog.width<=360&&dialog.y+dialog.height<=560);await rm.screenshot({path:path.join(root,'docs/arrow-label-narrow.png')});
 assert.deepEqual(errors,[]);console.log('PASS compact menu controls, persistent formatting, narrow/light/dark layouts, T-button keyboard, Escape/Enter, label undo/redo; no native JS prompt');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
