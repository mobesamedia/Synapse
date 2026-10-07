const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),{pathToFileURL}=require('node:url');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const p=await browser.newPage({viewport:{width:900,height:800}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{window.__ROADMAP_DATA__={version:1,active:'map',maps:[{id:'map',name:'My map',objects:[{id:'shape',kind:'shape',shape:'rounded',x:220,y:220,w:320,h:160,rotation:0,html:'Alpha Beta Gamma',fontSize:24,fill:'#ffffff',stroke:'#252525'}],view:{x:0,y:0,scale:1}}]}});
 await p.goto(pathToFileURL(path.resolve(__dirname,'../web_roadmap/index.html')).href);
 await p.locator('#objects [data-id=shape]').dblclick();
 await p.evaluate(()=>{const e=document.querySelector('.editing'),r=document.createRange();r.setStart(e.firstChild,6);r.setEnd(e.firstChild,10);getSelection().removeAllRanges();getSelection().addRange(r)});
 await p.locator('[data-format=bold]').click();assert.match(await p.locator('.editing').innerHTML(),/font-weight|<b>/);assert.equal(await p.evaluate(()=>getSelection().toString()),'Beta');
 await p.locator('#text-size').fill('32');await p.locator('#text-size').press('Tab');assert.match(await p.locator('.editing').innerHTML(),/32px/);
 await p.locator('#text-align').selectOption('justifyRight');assert.equal(await p.evaluate(()=>getSelection().toString()),'Beta');
 await p.locator('#text-color').evaluate(e=>{e.value='#cc3355';e.dispatchEvent(new Event('change',{bubbles:true}))});assert.match(await p.locator('.editing').innerHTML(),/204, 51, 85|#cc3355/);
 await p.locator('#text-done').click();let html=await p.evaluate(()=>__roadmapSnapshot().data.maps[0].objects[0].html);assert.match(html,/text-align: right/);assert.match(html,/32px/);
 // Resize acknowledgements preserve zoom and match Center View in both directions.
 for(const [width,active]of [[1100,true],[400,false]]){
  const before=await p.evaluate(()=>__roadmapSnapshot().data.maps[0].view.scale);await p.setViewportSize({width,height:800});await p.evaluate(a=>__synapseSetWindow(a),active);await p.waitForTimeout(750);
  const auto=await p.evaluate(()=>__roadmapSnapshot().data.maps[0].view);await p.locator('#center').click();const manual=await p.evaluate(()=>__roadmapSnapshot().data.maps[0].view);assert.equal(auto.scale,before);assert.deepEqual(auto,manual);
 }
 for(const dark of [false,true]){
  await p.evaluate(d=>document.documentElement.classList.toggle('dark',d),dark);await p.locator('#add-menu summary').click();
  let r=await p.locator('#add-menu .popover').boundingBox();assert.ok(r.x>=0&&r.x+r.width<=400);
  await p.screenshot({path:'/tmp/free-map-add-'+(dark?'dark':'light')+'.png'});await p.locator('#add-menu summary').click();
  await p.locator('#objects [data-id=shape]').dblclick();r=await p.locator('#text-toolbar').boundingBox();assert.ok(r.x>=0&&r.x+r.width<=400);
  await p.screenshot({path:'/tmp/free-map-text-'+(dark?'dark':'light')+'.png'});await p.locator('#text-done').click();
 }
 const mm=await browser.newPage({viewport:{width:400,height:800}});mm.on('pageerror',e=>errors.push(e.message));
 await mm.addInitScript(()=>{localStorage.setItem('mindmaps',JSON.stringify({test:{name:'Existing map',nodes:[{id:1,text:'Root',parent:null,x:170,y:130,width:154,height:60}],view:{x:0,y:0,scale:.7}}}));});
 await mm.goto(pathToFileURL(path.resolve(__dirname,'../index.html')).href);await mm.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});
 for(const [width,active]of [[1100,true],[400,false]]){
  const zoom=await mm.locator('#mindmap-zoom-label').innerText();await mm.setViewportSize({width,height:800});await mm.evaluate(a=>__synapseSetWindow(a),active);await mm.waitForTimeout(750);
  assert.equal(await mm.locator('#mindmap-zoom-label').innerText(),zoom);
  const delta=await mm.evaluate(()=>{let a=document.querySelector('#node-1').getBoundingClientRect(),b=document.querySelector('#mindmap-container').getBoundingClientRect();return [Math.abs(a.x+a.width/2-b.x-b.width/2),Math.abs(a.y+a.height/2-b.y-b.height/2)]});assert.ok(delta.every(v=>v<2),JSON.stringify(delta));
 }
 assert.deepEqual(errors,[]);console.log('PASS Free Map selection preserved through bold/size/alignment/color, persisted formatting, compact menus light/dark, center + zoom preserved both resize directions for both maps');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
