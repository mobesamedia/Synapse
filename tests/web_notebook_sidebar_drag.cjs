// Real sidebar pointer drags and empty-list interaction; synthetic data only.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const page=await browser.newPage({viewport:{width:1100,height:800}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.addInitScript(()=>window.pycmd=()=>{});await page.goto('file://'+path.resolve(__dirname,'../web_notebook/index.html'));
 const original={pages:[{id:'A',title:'Parent',icon:'',custom:'keep',pinned:true,blocks:[{type:'callout',html:'<b>Callout</b>',extra:'keep'}]},{id:'B',title:'Child',icon:'',blocks:[{type:'text',html:'<em>Original</em>',extra:'keep'}]}],activePageId:'A',folders:[{id:'f',name:'Folder',open:false,custom:'keep'}],extra:'keep'};
 const load=async data=>{await page.evaluate(data=>{loadContent(JSON.stringify(data));if(!appState.sidebarOpen)toggleSidebar();},data);await page.waitForTimeout(350);};
 const state=()=>page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload()));
 for(const nested of [false,true]){
  const data=structuredClone(original);data.pages[1].pinned=true;if(nested)data.pages[1].parentPageId='A';await load(data);
  const source=page.locator('.sidebar-item[data-page-id="B"]').first(),folder=page.locator('.folder-row[data-folder-id="f"]');
  // A cancelled drag must not change a notebook.
  await source.hover();await page.mouse.down();const sr=await source.boundingBox();await page.mouse.move(sr.x+30,sr.y+60,{steps:8});await page.keyboard.press('Escape');await page.mouse.up();assert.deepEqual((await state()).pages,data.pages);
  await source.dragTo(folder);const saved=await state();assert.equal(saved.pages[1].folderId,'f');assert.equal(saved.pages[1].parentPageId,undefined);assert.deepEqual(saved.pages[1].blocks,data.pages[1].blocks);assert.deepEqual(saved.pages[0],data.pages[0]);assert.deepEqual(saved.folders,[{...data.folders[0],open:true}]);
  await page.locator('#notebook-back').click();assert.deepEqual((await state()).pages,data.pages);assert.deepEqual((await state()).folders,data.folders);await page.locator('#notebook-forward').click();assert.deepEqual((await state()).pages,saved.pages);
  // External ID payloads do not authorize an internal move.
  await page.evaluate(()=>{const transfer=new DataTransfer();transfer.setData('application/x-synapse-notebook-page','A');document.querySelector('.folder-row').dispatchEvent(new DragEvent('drop',{bubbles:true,dataTransfer:transfer}));});assert.deepEqual((await state()).pages,saved.pages);
 }
 await load(original);assert.deepEqual((await state()).pages,original.pages);assert.equal(await page.locator('.callout-icon svg').count(),1);
 await page.locator('.sidebar-item[data-page-id="A"]').hover();assert.equal(await page.locator('.sidebar-item[data-page-id="A"] .pin-btn svg').count(),1);assert.equal(await page.locator('.sidebar-item[data-page-id="A"] .del-btn svg').count(),1);
 await page.locator('.sidebar-item[data-page-id="A"]').click({button:'right'});assert.equal(await page.locator('#page-ctx-menu .danger svg').count(),1);await page.keyboard.press('Escape');
 for(const type of ['bullet','todo']){
  await page.evaluate(type=>{loadContent(JSON.stringify({pages:[{id:'list',title:'List',icon:'',blocks:[{type,html:''}]}],activePageId:'list'}));},type);
  const editable=()=>page.locator(type==='todo'?'#editor .todo-content':'#editor .bullet').last();await editable().focus();
  if(type==='bullet'){assert.equal(await editable().evaluate(el=>getComputedStyle(el,'::before').content),'"•"');assert.equal(await editable().evaluate(el=>getComputedStyle(el,'::before').position),'absolute');}
  else assert.equal(await page.locator('#editor .todo-check').count(),1);
  await editable().fill('First item');await page.keyboard.press('Enter');assert.equal(await page.locator(type==='todo'?'#editor .todo-check':'#editor .bullet').count(),2);
  if(type==='bullet')assert.equal(await editable().evaluate(el=>getComputedStyle(el,'::before').content),'"•"');
  await page.keyboard.press('Enter');assert.equal(await page.locator('#editor > :last-child').getAttribute('class'),'block ');assert.equal((await state()).pages[0].blocks[0].html,'First item');
 }
 assert.deepEqual(errors,[]);console.log('PASS actual sidebar drag/drop and cancel, nested pages, undo/redo, external-drop protection, raw content preservation, SVG chrome and immediate list/todo markers with empty Enter exit');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
