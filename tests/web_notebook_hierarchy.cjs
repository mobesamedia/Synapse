// Full stored-block equality checks. Synthetic notebooks and temporary browser profile only.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
const fixture={pages:[
 {id:'A',title:'Parent',icon:'',folderId:'f',updatedAt:101,extra:'preserve',blocks:[{type:'text',html:'<b>First</b>',id:'block1',extra:{keep:true}},{type:'toggle',html:'Title',body:'<b>Full body</b>',open:false,extra:'keep'},{type:'table',html:'<tbody><tr><td contenteditable="true">Cell</td></tr></tbody>',extra:'keep'},{type:'future-widget',html:'Future',payload:{keep:1}},{type:'text',html:'Last'},{type:'text',html:'<svg><text>Original SVG</text></svg>',extra:'safe original'}]},
 {id:'B',title:'Child',icon:'',folderId:'f',updatedAt:102,blocks:[{type:'text',html:'Child original'}]},
 {id:'C',title:'Grandchild',icon:'',updatedAt:103,blocks:[{type:'text',html:'Grandchild original'}]},
 {id:'D',title:'Another',icon:'',updatedAt:104,blocks:[{type:'text',html:'Other original'}]}
],folders:[{id:'f',name:'Original folder',open:true,custom:'keep'}],activePageId:'A',customRoot:{keep:true}};
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const page=await browser.newPage({viewport:{width:1100,height:850}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>window.pycmd=()=>{});await page.goto('file://'+path.resolve(__dirname,'../web_notebook/index.html'));
 const load=data=>page.evaluate(data=>loadContent(JSON.stringify(data)),data);
 const snapshot=()=>page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload()));
 await load(fixture);assert.deepEqual((await snapshot()).pages,fixture.pages);assert.deepEqual((await snapshot()).folders,fixture.folders);
 await page.evaluate(()=>toggleSidebar());
 const initialRows=await page.locator('.sidebar-item').count();assert.equal(initialRows,4);
 const initialBodies=fixture.pages.map(p=>p.blocks);
 assert.equal(await page.evaluate(()=>setNotebookParent('B','A')),true);
 assert.equal(await page.evaluate(()=>setNotebookParent('C','B')),true);
 assert.equal(await page.evaluate(()=>setNotebookParent('A','C')),false,'Cycle rejected');
 assert.equal(await page.evaluate(()=>setNotebookParent('A','A')),false,'Self-parent rejected');
 assert.equal(await page.evaluate(()=>setNotebookParent('A','missing')),false,'Missing parent rejected');
 assert.deepEqual((await snapshot()).pages.map(p=>p.blocks),initialBodies);
 assert.deepEqual((await snapshot()).pages.map(p=>p.folderId),fixture.pages.map(p=>p.folderId));
 assert.equal(await page.locator('.sidebar-item').count(),4);
 await page.evaluate(()=>loadPage('C'));
 assert.equal(await page.locator('#notebook-breadcrumbs').getAttribute('hidden'),null);
 assert.equal(await page.locator('#notebook-breadcrumbs').getAttribute('title'),'Original folder / Parent / Child / Grandchild');
 await page.locator('#notebook-breadcrumbs').getByRole('button',{name:'Parent',exact:true}).click();assert.equal((await snapshot()).activePageId,'A');
 await page.locator('.sidebar-item[data-page-id="A"] .nb-tree-toggle').click();
 assert.equal(await page.locator('.sidebar-item[data-page-id="B"]').count(),0);
 assert.equal((await snapshot()).pages.length,4);
 await page.locator('.sidebar-item[data-page-id="A"] .nb-tree-toggle').click();
 const nested=await snapshot();await load(nested);assert.deepEqual((await snapshot()).pages,nested.pages);
 // Removing the parent preserves and reparents its child, including all content.
 page.once('dialog',d=>d.accept());await page.evaluate(()=>deletePage({stopPropagation(){}},'B'));
 const afterDelete=await snapshot();assert.equal(afterDelete.pages.find(p=>p.id==='C').parentPageId,'A');assert.deepEqual(afterDelete.pages.find(p=>p.id==='C').blocks,fixture.pages[2].blocks);
 page.once('dialog',d=>d.accept());await page.evaluate(()=>deleteFolder({stopPropagation(){}},'f'));
 assert.equal((await snapshot()).pages.find(p=>p.id==='C').parentPageId,'A');
 assert.deepEqual((await snapshot()).pages.map(p=>p.blocks),[fixture.pages[0].blocks,fixture.pages[2].blocks,fixture.pages[3].blocks]);
 // Imported cycles and orphan relationships remain accessible and stored unchanged.
 const malformed=JSON.parse(JSON.stringify(fixture));malformed.pages[0].parentPageId='B';malformed.pages[1].parentPageId='A';malformed.pages[2].parentPageId='missing';
 await load(malformed);assert.equal(await page.locator('.sidebar-item').count(),4);assert.deepEqual((await snapshot()).pages,malformed.pages);
 await load(fixture);
 page.once('dialog',d=>d.accept('New section'));await page.evaluate(()=>addNotebookSection());
 const section=(await snapshot()).folders.find(folder=>folder.kind==='section');assert.ok(section);
 await page.evaluate(id=>movePageToFolder('A',id),section.id);await page.evaluate(()=>addNotebookSubpage('A'));
 const child=(await snapshot()).pages.find(p=>p.parentPageId==='A');assert.ok(child);assert.notEqual(child.id,'A');assert.deepEqual((await snapshot()).pages.find(p=>p.id==='A').blocks,fixture.pages[0].blocks);
 assert.match(await page.locator('#notebook-breadcrumbs').getAttribute('title'),/^New section \/ Parent \/ /);
 console.log('PASS legacy hierarchy unchanged, nested pages, section, breadcrumbs, reload, cycles/orphans, parent/section deletion');
 // Real pointer movement reorders DOM nodes; every full block stays identical.
 await load(fixture);if(await page.locator('#sidebar').evaluate(el=>!el.classList.contains('closed')))await page.evaluate(()=>toggleSidebar());
 await page.locator('#editor > :first-child').hover();
 const grip=await page.locator('#notebook-gutter [data-action="menu"]').boundingBox();
 const last=await page.locator('#editor > :last-child').boundingBox();
 await page.mouse.move(grip.x+grip.width/2,grip.y+grip.height/2);await page.mouse.down();
 await page.mouse.move(last.x+40,last.y+last.height-1,{steps:12});
 assert.equal(await page.locator('#notebook-drop-line').isVisible(),true);
 await page.mouse.up();
 const reordered=fixture.pages[0].blocks.slice(1).concat([fixture.pages[0].blocks[0]]);
 assert.deepEqual((await snapshot()).pages[0].blocks,reordered);
 assert.equal(await page.locator('#notebook-popup').isVisible(),false,'Drag must not open block menu');
 await page.keyboard.press('Control+z');assert.deepEqual((await snapshot()).pages[0].blocks,fixture.pages[0].blocks);
 await page.keyboard.press('Control+Shift+Z');assert.deepEqual((await snapshot()).pages[0].blocks,reordered);
 await page.locator('#editor > :last-child').hover();
 const source=await page.locator('#notebook-gutter [data-action="menu"]').boundingBox();
 const first=await page.locator('#editor > :first-child').boundingBox();
 await page.mouse.move(source.x+10,source.y+10);await page.mouse.down();await page.mouse.move(first.x+40,first.y+3,{steps:10});await page.keyboard.press('Escape');await page.mouse.up();
 assert.deepEqual((await snapshot()).pages[0].blocks,reordered,'Escape leaves original order');
 await page.locator('#editor > :first-child').hover();
 const source2=await page.locator('#notebook-gutter [data-action="menu"]').boundingBox();
 await page.mouse.move(source2.x+10,source2.y+10);await page.mouse.down();await page.mouse.move(1098,700,{steps:10});await page.mouse.up();
 assert.deepEqual((await snapshot()).pages[0].blocks,reordered,'Outside drop leaves original order');
 await page.locator('#editor > :first-child').hover();const source3=await page.locator('#notebook-gutter [data-action="menu"]').boundingBox();
 await page.mouse.move(source3.x+10,source3.y+10);await page.mouse.down();await page.mouse.move(first.x+50,first.y+40,{steps:5});await page.evaluate(()=>loadPage('B'));await page.mouse.up();
 assert.deepEqual((await snapshot()).pages[0].blocks,reordered,'Page change cancels drag');assert.deepEqual((await snapshot()).pages[1].blocks,fixture.pages[1].blocks);
 await load(fixture);await page.evaluate(()=>notebookShowGutter(editor.firstElementChild));await page.locator('#notebook-gutter [data-action="menu"]').focus();await page.keyboard.press('Alt+ArrowDown');
 assert.deepEqual((await snapshot()).pages[0].blocks,[fixture.pages[0].blocks[1],fixture.pages[0].blocks[0],...fixture.pages[0].blocks.slice(2)]);
 assert.deepEqual(errors,[]);console.log('PASS actual drag/drop, complete block data, undo/redo, Escape/outside/page-switch cancellation and keyboard reorder');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
