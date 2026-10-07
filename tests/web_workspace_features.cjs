const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..'),catalog=require('../workspace_translations.json');
const imageBuffer=fs.readFileSync(path.join(__dirname,'fixtures/workspace-image.png')),asset=require('node:crypto').createHash('sha256').update(imageBuffer).digest('hex')+'.png',imageDir=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'synapse-browser-images-'));fs.writeFileSync(path.join(imageDir,asset),imageBuffer);const imageBase=pathToFileURL(imageDir+'/').href;
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
const errors=[];
for(const lang of ['en','de','es','ko','pt','fr','vi','zh','hi','pl']){
 const page=await browser.newPage({viewport:{width:1100,height:800},colorScheme:'dark'});page.on('pageerror',e=>errors.push(e.message));
 const dict=Object.fromEntries(Object.entries(catalog).map(([key,values])=>[key,lang==='en'?key:values[lang]]));
 await page.addInitScript(({dict})=>{window.__WORKSPACE_I18N__=dict;window.__SYNAPSE_MM_DARK__=false;window.__WORKSPACE_TOOLS__={mindmap:false,roadmap:true};},{dict});
 await page.goto(pathToFileURL(path.join(root,'web_roadmap/index.html')).href);
 assert.equal(await page.locator('#new-map').innerText(),dict.New);assert.equal(await page.locator('#workspace-settings').getAttribute('title'),dict.Settings);
 assert.equal(await page.locator('#workspace-nav .tool').count(),1);assert.equal(await page.locator('#workspace').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(255, 255, 255)');
 await page.locator('#add-menu summary').click();assert.equal(await page.locator('[data-shape=rect]').innerText(),dict.Rectangle);
 await page.locator('[data-shape=rect]').click();assert.equal(await page.locator('[aria-label="'+dict.Shape+'"]').count(),1);
 await page.evaluate(()=>document.documentElement.classList.add('dark'));assert.equal(await page.locator('#workspace').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(44, 44, 44)');
 await page.close();
}
const mm=await browser.newPage({viewport:{width:1100,height:800}});mm.on('pageerror',e=>errors.push(e.message));
await mm.addInitScript(()=>localStorage.setItem('mindmaps',JSON.stringify({test:{name:'Text styles',nodes:[{id:1,text:'My topic',parent:null,x:100,y:100}]}})));
await mm.goto(pathToFileURL(path.join(root,'index.html')).href);await mm.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});
const node=mm.locator('#node-1 .node-textarea');await node.click({button:'right'});await mm.locator('#context-menu').getByRole('button',{name:'Bold',exact:true}).click();assert.equal(await node.evaluate(e=>getComputedStyle(e).fontWeight),'700');
await mm.locator('#context-menu').getByRole('button',{name:'Italic',exact:true}).click();assert.equal(await node.evaluate(e=>getComputedStyle(e).fontStyle),'italic');
await mm.locator('#node-font-size').selectOption('28');assert.equal(await node.evaluate(e=>getComputedStyle(e).fontSize),'28px');
await mm.locator('[data-fill="#e4f5e9"]').click();await mm.waitForFunction(()=>getComputedStyle(document.getElementById('node-1')).backgroundColor==='rgb(228, 245, 233)');assert.equal(await mm.locator('#node-1').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(228, 245, 233)');assert.equal(await node.evaluate(e=>getComputedStyle(e).color),'rgb(17, 17, 17)');
const doc=await mm.evaluate(()=>window.__workspaceDocument());assert.equal(doc.nodes[0].fontSize,28);assert.equal(doc.nodes[0].bold,true);assert.equal(doc.nodes[0].italic,true);assert.equal(doc.nodes[0].fill,'#e4f5e9');
await mm.locator('#node-font-size').press('Escape');await mm.locator('#zoom-in-btn').click();assert.notEqual(await mm.locator('#mindmap-zoom-label').innerText(),'100%');
// Exercise real image callbacks without opening a native file dialog.

await mm.evaluate(base=>{window.__SYNAPSE_MM_HOSTED__=true;window.__WORKSPACE_IMAGE_BASE__=base;window.__synapseMindmapCommand=command=>window.lastCommand=command;},imageBase);
await node.click({button:'right'});await mm.locator('#context-menu').getByRole('button',{name:'Add image',exact:true}).click();assert.equal(await mm.evaluate(()=>lastCommand),'image-add');
await mm.evaluate(image=>__workspaceImageAdded({image,width:120,height:80}),asset);assert.equal(await mm.locator('.node-image').count(),1);assert.equal((await mm.evaluate(()=>__workspaceDocument())).nodes[0].image,asset);
await mm.locator('#hamburger-btn').click();await mm.locator('#export-btn').click();assert.equal(await mm.evaluate(()=>lastCommand),'workspace-export');
await mm.evaluate(()=>{window.__SYNAPSE_MM_HOSTED__=false});
await mm.waitForFunction(()=>document.querySelector('.node-image').naturalWidth===120);await mm.bringToFront();await mm.waitForTimeout(350);await mm.screenshot({path:path.join(root,'docs/mindmap-formatting.png')});
const rm=await browser.newPage({viewport:{width:1100,height:800}});rm.on('pageerror',e=>errors.push(e.message));await rm.goto(pathToFileURL(path.join(root,'web_roadmap/index.html')).href);
await rm.evaluate(base=>{window.__SYNAPSE_MM_HOSTED__=true;window.__WORKSPACE_IMAGE_BASE__=base;window.__synapseMindmapCommand=command=>window.lastCommand=command;},imageBase);
await rm.locator('#add-menu summary').click();await rm.locator('#add-image').click();await rm.evaluate(image=>__workspaceImageAdded({image,width:120,height:80}),asset);assert.equal(await rm.locator('#objects image').count(),1);
await rm.locator('#undo').click();assert.equal(await rm.locator('#objects image').count(),0);await rm.locator('#redo').click();assert.equal(await rm.locator('#objects image').count(),1);
assert.equal((await rm.evaluate(()=>__workspaceDocument())).objects[0].image,asset);
assert.deepEqual(errors,[]);console.log('PASS all 10 languages, tab visibility, explicit light/dark, Mindmap typography/fill/zoom, image callbacks and reference-only undo, native export command');
}finally{await browser.close();fs.rmSync(imageDir,{recursive:true,force:true})}})().catch(e=>{console.error(e);process.exitCode=1});
