// Synthetic notes only. No live Anki profile or collection is accessed.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const fixture={pages:[{id:'A',title:'Layout fixture',icon:'📄',updatedAt:1234,custom:'keep',blocks:[
 {type:'text',html:'<b>Rich text</b> and <a href="https://example.org">link</a><br>A longer paragraph '.repeat(8),id:'stable',extra:{keep:true}},
 {type:'h1',html:'Heading one'}, {type:'h2',html:'Heading two'},
 {type:'todo',html:'Task',checked:true}, {type:'quote',html:'Quote'}, {type:'callout',html:'Callout'},
 {type:'toggle',html:'Toggle title',body:'<b>Body preserved</b>',open:true},
 {type:'table',html:'<tbody><tr><td contenteditable="true">Cell</td><td contenteditable="true">Other</td></tr></tbody>'},
 {type:'divider',html:''},{type:'code',html:'const x = 1;'},
 {type:'text',html:'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j9a8AAAAASUVORK5CYII=" style="width:50px">'}
]},{id:'B',title:'Destination',icon:'',blocks:[{type:'text',html:'Destination original'}]}],activePageId:'A'};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try {
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>window.pycmd=()=>{});
  const load=async data=>page.evaluate(data=>loadContent(JSON.stringify(data)),data);
  const snapshot=()=>page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload()));
  const html='file://'+root+'/web_notebook/index.html';await page.goto(html);await load(fixture);
  assert.deepEqual((await snapshot()).pages,fixture.pages);
  await page.evaluate(()=>{notebookShowGutter(editor.firstElementChild);notebookOpenActions();});
  assert.deepEqual((await snapshot()).pages,fixture.pages,'Opening block UI must not mutate notes');
  await page.evaluate(()=>loadPage('B'));await page.evaluate(()=>loadPage('A'));
  assert.deepEqual((await snapshot()).pages,fixture.pages,'Switching pages preserves raw blocks');
  for(const block of [
   {type:'future-widget',html:'Unknown',body:'More',custom:'preserve'},
   {type:'text',html:'<B data-extra="1">Raw HTML</B>'},
   {type:'text',html:'Before <svg><text>Original</text></svg><math><mi>x</mi></math> After'},
   {type:'text',html:'<img src="file:///synthetic.png">'}
  ]){
   await load({pages:[{id:'A',title:'',icon:'',blocks:[block]}],activePageId:'A'});
   assert.deepEqual((await snapshot()).pages[0].blocks,[block]);
  }
  await load({pages:[{id:'A',title:'',icon:'',blocks:[]}],activePageId:'A'});
  assert.deepEqual((await snapshot()).pages[0].blocks,[]);
  await load([{type:'text',html:'<b>Legacy</b>',extra:'keep'}]);
  assert.deepEqual((await snapshot()).pages[0].blocks,[{type:'text',html:'<b>Legacy</b>',extra:'keep'}]);
  await load({pages:[{id:'A',title:'',icon:'',blocks:[{type:'text',html:'<B>Canonicalized</B>'}]}],activePageId:'A'});
  assert.equal(await page.locator('#editor > :first-child').getAttribute('contenteditable'),'true');
  await load(fixture);
  await page.evaluate(()=>{replaceWithType(editor.firstElementChild,'h1');});
  assert.equal((await snapshot()).pages[0].blocks[0].html,fixture.pages[0].blocks[0].html);
  assert.deepEqual((await snapshot()).pages[0].blocks[0].extra,{keep:true});
  await page.keyboard.press('Control+z');assert.deepEqual((await snapshot()).pages[0].blocks,fixture.pages[0].blocks);
  await page.evaluate(()=>{selectedBlocks.add(6);convertSelectedBlocks('text');});
  assert.ok((await snapshot()).pages[0].blocks[6].html.includes('<b>Body preserved</b>'));
  await page.keyboard.press('Control+z');assert.deepEqual((await snapshot()).pages[0].blocks,fixture.pages[0].blocks);
  console.log('PASS unchanged raw notes, unknown fields/types, sanitization protection, conversion and Undo');
  // Selection survives the color popup and only deliberately selected text changes.
  await load({pages:[{id:'A',title:'',icon:'',blocks:[{type:'text',html:'Selected text untouched tail'}]}],activePageId:'A'});
  await page.evaluate(()=>{const range=document.createRange();range.setStart(editor.firstChild.firstChild,0);range.setEnd(editor.firstChild.firstChild,13);const s=window.getSelection();s.removeAllRanges();s.addRange(range);});
  await page.locator('#format-toolbar button[title="Color"]').click();
  await page.locator('#notebook-popup button[aria-label="Background: Yellow"]').click();
  assert.match((await snapshot()).pages[0].blocks[0].html,/background-color/);
  assert.equal(await page.locator('#editor').innerText(),'Selected text untouched tail');
  await page.keyboard.press('Control+z');assert.equal((await snapshot()).pages[0].blocks[0].html,'Selected text untouched tail');
  // Menus are usable via actual clicks; duplicate and move preserve the full block.
  await load(fixture);await page.locator('#editor > :first-child').hover();
  await page.locator('#notebook-gutter [data-action="menu"]').click();
  await page.locator('#notebook-popup').getByRole('button',{name:'Duplicate',exact:true}).click();
  const duplicate=(await snapshot()).pages[0].blocks[1];assert.equal(duplicate.html,fixture.pages[0].blocks[0].html);assert.deepEqual(duplicate.extra,{keep:true});assert.notEqual(duplicate.id,'stable');
  await page.keyboard.press('Control+z');assert.deepEqual((await snapshot()).pages[0].blocks,fixture.pages[0].blocks);
  await page.locator('#editor > :first-child').hover();await page.locator('#notebook-gutter [data-action="menu"]').click();
  await page.locator('#notebook-popup').getByRole('button',{name:'Move to page ›',exact:true}).click();
  page.once('dialog',d=>d.accept());await page.locator('#notebook-popup').getByRole('button',{name:'Destination',exact:true}).click();
  const moved=await snapshot();assert.deepEqual(moved.pages[1].blocks[1],fixture.pages[0].blocks[0]);assert.equal(moved.pages[0].blocks.length,fixture.pages[0].blocks.length-1);
  // Clicking between blocks never inserts; the single gutter + remains available.
  await load({pages:[{id:'A',title:'',icon:'',blocks:[{type:'text',html:'First'},{type:'text',html:'Second'}]}],activePageId:'A'});
  const box=await page.locator('#editor > :first-child').boundingBox();
  await page.mouse.move(box.x+20,box.y+box.height);await page.mouse.down();await page.mouse.up();
  assert.equal(await page.locator('#editor > *').count(),2);
  await page.locator('#editor > :first-child').hover();await page.locator('#notebook-gutter [data-action="add"]').click();
  await page.locator('#notebook-popup').getByRole('button',{name:'Heading 3',exact:true}).click();
  assert.equal((await snapshot()).pages[0].blocks[1].type,'h3');
  console.log('PASS selection color dropdown, duplicate/move, explicit insertion and H3');
  assert.equal(await page.locator('#line-insert-indicator').count(),0);
  await page.locator('#editor > :first-child').hover();
  assert.equal(await page.locator('#editor > :first-child').evaluate(el=>getComputedStyle(el).outlineStyle),'none');
  const navigationFixture = JSON.parse(JSON.stringify(fixture));
  navigationFixture.pages.push({id:'C',title:'Third page',icon:'',blocks:[{type:'text',html:'Third original'}]});
  await load(navigationFixture);
  assert.equal(await page.locator('#notebook-back').isDisabled(),true);
  assert.equal(await page.locator('#notebook-forward').isDisabled(),true);
  await page.evaluate(()=>{loadPage('B');loadPage('C');});
  await page.locator('#notebook-back').click();
  assert.equal((await snapshot()).activePageId,'B');
  await page.locator('#notebook-back').click();
  assert.equal((await snapshot()).activePageId,'A');
  await page.locator('#notebook-forward').click();
  assert.equal((await snapshot()).activePageId,'B');
  await page.evaluate(()=>loadPage('A'));
  assert.equal(await page.locator('#notebook-forward').isDisabled(),true,'New visit discards the forward branch');
  assert.deepEqual((await snapshot()).pages,navigationFixture.pages,'Browsing leaves note content and timestamps intact');
  await page.evaluate(()=>loadPage('C'));
  page.once('dialog',d=>d.accept());
  await page.evaluate(()=>deletePage({stopPropagation(){}},'B'));
  await page.locator('#notebook-back').click();
  assert.equal((await snapshot()).activePageId,'C','Undo deletion keeps the active page');
  assert.deepEqual((await snapshot()).pages,navigationFixture.pages,'Undo deletion restores the complete page');
  await page.locator('#notebook-back').click();
  assert.equal((await snapshot()).activePageId,'A','The next undo reverses the preceding page switch');
  assert.equal((await snapshot()).notebookHistory,undefined);
  await load(fixture);
  assert.equal(await page.locator('#notebook-back').isDisabled(),true,'Loading another notebook resets session history');
  for (const width of [320,400,1100]) {
   await page.setViewportSize({width,height:850});
   const header = await page.evaluate(()=>{const nav=document.querySelector('.notebook-navigation').getBoundingClientRect(),search=searchInput.getBoundingClientRect(),toggle=document.querySelector('.toggle-btn').getBoundingClientRect();return {gap:search.left-nav.right,width:search.width,right:toggle.right}});
   assert.ok(header.gap <= 12 && header.gap >= 0);
   assert.ok(header.width <= 330 && header.width > 0);
   assert.ok(header.right <= width);
  }
  console.log('PASS history back/forward, branching, deletion, reset; removed insertion indicator and hover borders');

  // Compare old and new block geometry. Supply NOTEBOOK_BASELINE only for an update audit.
  if(process.env.NOTEBOOK_BASELINE){
   const geometry=()=>page.evaluate(()=>Array.from(editor.children).map(el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {x:r.x,y:r.y-document.querySelector('.header-bar').getBoundingClientRect().bottom,w:r.width,h:r.height,font:s.fontSize,line:s.lineHeight,margin:s.margin,padding:s.padding}}));
   for(const width of [400,1100])for(const dark of [false,true]){
    await page.setViewportSize({width,height:850});
    await page.goto('file://'+process.env.NOTEBOOK_BASELINE);await load(fixture);if(dark)await page.evaluate(()=>document.body.classList.add('nightMode'));
    const before=await geometry();await page.goto(html);await load(fixture);if(dark)await page.evaluate(()=>document.body.classList.add('nightMode'));
    assert.deepEqual(await geometry(),before,`Layout changed at ${width}, dark=${dark}`);
   }
   console.log('PASS identical existing block geometry relative to the resized header at 400/1100px, light/dark');
  }
  assert.deepEqual(errors,[]);await page.close();
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
