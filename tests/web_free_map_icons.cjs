const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),{pathToFileURL}=require('node:url');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const p=await browser.newPage({viewport:{width:400,height:780}}),errors=[],network=[];p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
 await p.goto(pathToFileURL(path.resolve(__dirname,'../web_roadmap/index.html')).href);await p.waitForFunction(()=>window.FreeMapIcons);
 assert.equal(await p.evaluate(()=>FREE_MAP_ICON_CATALOG.icons.length),208);
 assert.equal(await p.evaluate(()=>FreeMapIcons.search('medicine').length),await p.evaluate(()=>FreeMapIcons.search('','Medicine').length));
 assert.ok(await p.evaluate(()=>FreeMapIcons.search('cardiology').some(i=>i.id==='lucide-heart-pulse')));
 assert.ok(await p.evaluate(()=>FreeMapIcons.search('neurons').some(i=>i.id==='lucide-brain-circuit')));
 assert.equal(await p.evaluate(()=>FreeMapIcons.search('medcine').length),await p.evaluate(()=>FreeMapIcons.search('medicine').length));
 assert.equal(await p.evaluate(()=>FreeMapIcons.search('cooking','Medicine').length),0);
 for(const dark of [false,true]){
  await p.evaluate(d=>document.documentElement.classList.toggle('dark',d),dark);
  await p.locator('#add-menu summary').click();await p.locator('#add-icon').click();await p.locator('#icon-search').fill('medicine');await p.waitForTimeout(100);
  let r=await p.locator('#icon-picker').boundingBox();assert.ok(r.x>=0&&r.x+r.width<=400&&r.y+r.height<=780);
  await p.screenshot({path:'/tmp/free-map-icons-'+(dark?'dark':'light')+'.png'});await p.keyboard.press('Escape');
 }
 async function pick(name,color){await p.locator('#add-menu summary').click();await p.locator('#add-icon').click();await p.locator('#icon-search').fill(name);await p.waitForTimeout(100);await p.locator('#icon-insert-color').evaluate((e,c)=>{e.value=c;e.dispatchEvent(new Event('input'))},color);await p.locator('.icon-choice[data-icon="lucide-'+name+'"]').click();}
 await pick('heart-pulse','#cc3355');let doc=await p.evaluate(()=>__workspaceDocument());let object=doc.objects.find(o=>o.kind==='icon');assert.equal(object.stroke,'#cc3355');assert.ok(doc.iconAssets[object.icon].nodes.length);assert.ok(doc.iconLicense.includes('ISC License'));
 await p.locator('#object-toolbar input[type=color]').evaluate(e=>{e.value='#22aa66';e.dispatchEvent(new Event('change'))});assert.equal((await p.evaluate(()=>__workspaceDocument())).objects[0].stroke,'#22aa66');
 await p.locator('#undo').click();assert.equal((await p.evaluate(()=>__workspaceDocument())).objects[0].stroke,'#cc3355');await p.locator('#redo').click();
 // Replacing a motif starts with the selected object's color and is undoable.
 await p.locator('#objects [data-id]').first().click();await p.getByRole('button',{name:'Change icon',exact:true}).click();
 assert.equal(await p.locator('#icon-insert-color').inputValue(),'#22aa66');
 await p.locator('#icon-search').fill('');await p.locator('#icon-categories button').filter({hasText:/^Medicine$/}).click();
 assert.equal(await p.locator('.icon-choice').count(),await p.evaluate(()=>FreeMapIcons.search('','Medicine').length));
 await p.locator('[data-icon=lucide-brain]').click();assert.equal((await p.evaluate(()=>__workspaceDocument())).objects[0].icon,'lucide-brain');
 assert.equal((await p.evaluate(()=>__workspaceDocument())).objects[0].stroke,'#22aa66');
 await p.locator('#undo').click();assert.equal((await p.evaluate(()=>__workspaceDocument())).objects[0].icon,'lucide-heart-pulse');
 // Repeated instances reuse one definition; copying to another map brings the geometry.
 await p.locator('#objects [data-id]').first().click();await p.keyboard.press('ControlOrMeta+c');await p.keyboard.press('ControlOrMeta+v');
 doc=await p.evaluate(()=>__workspaceDocument());assert.equal(doc.objects.filter(o=>o.kind==='icon').length,2);assert.equal(Object.keys(doc.iconAssets).length,1);
 p.once('dialog',d=>d.accept('Second map'));await p.locator('#new-map').click();await p.keyboard.press('ControlOrMeta+v');doc=await p.evaluate(()=>__workspaceDocument());assert.equal(doc.objects.length,1);assert.equal(Object.keys(doc.iconAssets).length,1);
 await pick('brain','#0071d3');doc=await p.evaluate(()=>__workspaceDocument());assert.equal(Object.keys(doc.iconAssets).length,2);
 // Self-contained export/import works even when the target has an empty catalog.
 const bundle={version:1,active:doc.id,maps:[doc]};fs.writeFileSync('/tmp/free-map-icons-export.json',JSON.stringify(bundle));
 const q=await browser.newPage();q.on('pageerror',e=>errors.push(e.message));await q.addInitScript(data=>{window.__ROADMAP_DATA__=data;const empty={icons:[],license:''};Object.defineProperty(window,'FREE_MAP_ICON_CATALOG',{get:()=>empty,set:()=>{}})},bundle);await q.route('**/icons/catalog.js',r=>r.fulfill({contentType:'application/javascript',body:'window.FREE_MAP_ICON_CATALOG={icons:[],license:""};'}));
 await q.goto(pathToFileURL(path.resolve(__dirname,'../web_roadmap/index.html')).href);assert.equal(await q.evaluate(()=>FREE_MAP_ICON_CATALOG.icons.length),0);assert.equal(await q.locator('#objects > g svg').count(),2);assert.deepEqual(await q.evaluate(()=>__workspaceDocument().iconAssets),doc.iconAssets);
 const attacks=[{name:'Bad',nodes:[['script',{}]]},{name:'Bad',nodes:[['path',{d:'M0 0',onclick:'alert(1)'}]]},{name:'Bad',nodes:[['image',{href:'https://bad.example/a.svg'}]]},{name:'Bad',nodes:[['path',{d:'M0 0',fill:'url(https://bad.example)'}]]}];
 for(const attack of attacks)assert.equal(await q.evaluate(d=>FreeMapIcons.valid(d),attack),false);
 assert.deepEqual(network,[]);assert.deepEqual(errors,[]);console.log('PASS 208 local SVGs, English category/synonym/typo search, modal light/dark, recolor/undo, copy across maps, deduplicated export, import without catalog, unsafe SVG rejection, no network');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
