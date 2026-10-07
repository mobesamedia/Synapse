const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const {pathToFileURL}=require('node:url');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
try {
 const catalog=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../workspace_translations.json'),'utf8'));
 const translations=Object.fromEntries(Object.entries(catalog).map(([k,v])=>[k,v.de||k]));
 const url=pathToFileURL(path.resolve(__dirname,'../web_roadmap/index.html')).href;
 async function open(options={}){
  const page=await browser.newPage({viewport:{width:options.width||400,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(({options,translations})=>{window.__ROADMAP_FIRST_RUN__=options.first!==false;window.__WORKSPACE_I18N__=translations;if(options.data)window.__ROADMAP_DATA__=options.data;if(options.error)window.__ROADMAP_ERROR__='Read failed';}, {options,translations});
  await page.goto(url);await page.waitForFunction(()=>window.__roadmapSnapshot);return {page,errors};
 }
 const {page,errors}=await open();let data=await page.evaluate(()=>__roadmapSnapshot().data);
 assert.equal(data.maps.length,1);assert.equal(data.maps[0].name,'FreeMap-Tutorial');assert.ok(data.maps[0].objects.length>=20);
 assert.equal(data.maps[0].objects.filter(o=>o.kind==='arrow'&&o.a.node&&o.b.node).length,6);
 for(const width of [400,900])for(const dark of [false,true]){
  const preview=await open({width});
  await preview.page.evaluate(d=>document.documentElement.classList.toggle('dark',d),dark);
  assert.ok(await preview.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await preview.page.screenshot({path:`/tmp/roadmap-tutorial-${width}-${dark?'dark':'light'}.png`});
  assert.deepEqual(preview.errors,[]);await preview.page.close();
 }
 // Tutorial nodes are ordinary editable objects, with normal undo support.
 await page.locator('#objects [data-id="tutorial-shapes"]').dblclick();await page.locator('[contenteditable="true"]').fill('My own plan');await page.locator('#text-done').click();
 assert.equal((await page.evaluate(()=>__roadmapSnapshot().data)).maps[0].objects[0].html,'<b>Deine Ideen, ohne Vorlage</b>');
 assert.equal((await page.evaluate(()=>__roadmapSnapshot().data)).maps[0].objects.find(o=>o.id==='tutorial-shapes').html.replace(/<[^>]*>/g,''),'My own plan');
 await page.locator('#undo').click();
 page.once('dialog',d=>d.accept());await page.locator('#document-menu summary').click();await page.locator('[data-doc="delete"]').click();
 const deleted=await page.evaluate(()=>__roadmapSnapshot().data);assert.equal(deleted.maps[0].objects.length,0);
 const reopened=await open({data:deleted,first:false});assert.equal((await reopened.page.evaluate(()=>__roadmapSnapshot().data)).maps[0].objects.length,0);
 await reopened.page.locator('#document-menu summary').click();await reopened.page.locator('[data-doc="tutorial"]').click();
 assert.equal((await reopened.page.evaluate(()=>__roadmapSnapshot().data)).maps.length,2);
 const existing=await open({data});assert.deepEqual((await existing.page.evaluate(()=>__roadmapSnapshot().data)).maps,data.maps);
 const blocked=await open({error:true});assert.equal(await blocked.page.evaluate(()=>__roadmapSnapshot()),null);assert.equal(await blocked.page.locator('#objects > g').count(),0);
 for(const list of [errors,reopened.errors,existing.errors,blocked.errors])assert.deepEqual(list,[]);
 fs.writeFileSync('/tmp/roadmap-tutorial-snapshot.json',JSON.stringify(data));
 console.log('PASS translated first-use map, arrows, editing/undo, deletion/reload, manual recreation, existing-map preservation, read-only barrier, narrow/wide light/dark');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
