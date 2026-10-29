// Actual pointer paths and focus changes. Only synthetic notes are used.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const page=await browser.newPage({viewport:{width:900,height:700}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.addInitScript(()=>window.pycmd=()=>{});
 await page.goto('file://'+path.resolve(__dirname,'../web_notebook/index.html'));
 const original={pages:[{id:'A',title:'Gutter test',icon:'',blocks:[{type:'bullet',html:'First bullet',extra:'keep'},{type:'text',html:'Second block'}]},{id:'B',title:'Other page',icon:'',blocks:[{type:'text',html:'Other content'}]}],activePageId:'A'};
 await page.evaluate(data=>loadContent(JSON.stringify(data)),original);
 const first=page.locator('#editor > :first-child'),second=page.locator('#editor > :nth-child(2)'),gutter=page.locator('#notebook-gutter');
 await first.hover();const rect=await first.boundingBox();
 // Pause halfway across the gap: the old editor mouseleave hid the controls here.
 await page.mouse.move(rect.x-1,rect.y+15);await page.waitForTimeout(250);assert.equal(await gutter.isVisible(),true);
 const grip=await page.locator('#notebook-gutter [data-action="menu"]').boundingBox();
 await page.mouse.move(grip.x+grip.width/2,grip.y+grip.height/2,{steps:10});assert.equal(await gutter.isVisible(),true);
 await page.mouse.click(grip.x+grip.width/2,grip.y+grip.height/2);assert.equal(await page.locator('#notebook-popup').isVisible(),true);
 await page.keyboard.press('Escape');await first.click();
 const pinned=await gutter.boundingBox();await page.mouse.move(890,650);assert.equal(await gutter.isVisible(),true);assert.deepEqual(await gutter.boundingBox(),pinned);
 await second.click();const next=await gutter.boundingBox();assert.ok(next.y>pinned.y);await page.mouse.move(890,650);assert.equal(await gutter.isVisible(),true);assert.deepEqual(await gutter.boundingBox(),next);
 // Text selection must not hide the active block's controls either.
 await page.evaluate(()=>{const node=editor.children[1].firstChild,range=document.createRange();range.selectNodeContents(node);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);});
 await page.waitForTimeout(50);assert.equal(await gutter.isVisible(),true);
 await page.locator('#searchInput').click();assert.equal(await gutter.isVisible(),false);
 await first.click();await page.evaluate(()=>loadPage('B'));assert.equal(await gutter.isVisible(),false);
 assert.deepEqual(await page.evaluate(()=>JSON.parse(__synapseSnapshotForUnload()).pages),original.pages);
 assert.deepEqual(errors,[]);console.log('PASS hover corridor, clickable grip, persistent editing controls, block switch, selection, outside focus and page reset; note data unchanged');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
