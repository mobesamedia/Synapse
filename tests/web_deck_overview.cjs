const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const {pathToFileURL}=require('node:url');const {execFileSync}=require('node:child_process');
(async()=>{
 const fixture=JSON.parse(execFileSync('python3',[path.join(__dirname,'deck_overview_fixture.py')],{encoding:'utf8'}));
 const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage();const errors=[],commands=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.text().startsWith('COMMAND:')||m.text().startsWith('SYNAPSEPRO_SETTINGS:'))commands.push(m.text())});
  for(const file of fixture.files){
   await page.goto(pathToFileURL(file).href);
   for(const width of [400,1000]){
    await page.setViewportSize({width,height:900});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),file+' overflow at '+width);
    if(file.includes('focus')){
     assert.equal(await page.locator('.focus-ring').count(),1);
     assert.deepEqual(await page.locator('.today-counts strong').allTextContents(),['12','8','40']);
     assert.equal(await page.locator('.widget,.diff-container,#brainstorm-btn,.deck-details').count(),0);
    }else{
     assert.equal(await page.locator('.today-counts').count(),0);
     assert.equal(await page.locator('.diff-container img').evaluate(e=>getComputedStyle(e).width),'50px');
     await page.locator('[data-info="diff"]').click();assert.ok((await page.locator('#info-content').textContent()).includes('85'));
     assert.equal(await page.locator('.smiley-choice[data-choice="auto"]').textContent(),'Auto');
     await page.locator('.deck-dot-option input').check();assert.ok(commands.some(c=>c.startsWith('COMMAND:deck_indicator:')&&c.endsWith(':1')));
     await page.locator('[data-info="diff"]').click();await page.locator('[data-info="diff"]').click();
     assert.equal(await page.locator('.deck-dot-option input').isChecked(),true);
     const face=await page.locator('.diff-container').boundingBox();assert.ok(Math.abs(face.width-face.height)<1);
     const label=await page.locator('.progress-row-label').first().boundingBox();const tile=await page.locator('.widget').first().boundingBox();assert.ok(Math.abs(label.x-tile.x)<1);
     await page.locator('.smiley-choice[data-choice="green"]').click();assert.ok(commands.some(c=>c.endsWith(':green')));

     await page.locator('[data-info="hard"]').click();assert.ok((await page.locator('#info-content').textContent()).includes('8'));
     await page.locator('[data-info="hard"]').click();
    }
    assert.equal(await page.locator('.white-box .deck-controls').count(),1);
    await page.screenshot({path:'/tmp/deck-'+path.basename(file,'.html')+'-'+width+'.png',fullPage:true});
   }
   await page.locator('.deck-header h1').click();
   const starts=commands.filter(c=>c==='COMMAND:start_study').length;await page.keyboard.press('Space');assert.equal(commands.filter(c=>c==='COMMAND:start_study').length,starts+1);
   await page.locator('.start-btn').click();assert.ok(commands.includes('COMMAND:start_study'));
   await page.locator('.deck-controls button').click();assert.ok(commands.includes('COMMAND:deck_overview_settings'));
   if(!file.includes('focus')){await page.locator('#brainstorm-btn').click();assert.ok(commands.includes('COMMAND:brainstorm'));await page.evaluate(()=>renderWordCloud([]));}
  }
  for(const file of fixture.cases){
   await page.goto(pathToFileURL(file).href);
   await page.locator('[data-info="hard"]').click();
   assert.ok((await page.locator('#info-content').textContent()).includes('8'));
   if(file.endsWith('hidden.html'))assert.equal(await page.locator('#brainstorm-btn').count(),0);
   else assert.equal(await page.locator('#brainstorm-btn').count(),1);
   await page.evaluate(()=>renderWordCloud([]));
  }
  await page.goto(pathToFileURL(path.resolve(__dirname,'../settings_web/settings.html')).href);
  await page.evaluate(deckOverview=>initSettings({config:{},deckOverview,initialPage:'deck',backgroundThemes:[],banner:{}}),fixture.settings);
  assert.equal(await page.locator('[data-page="deck"].page.active').count(),1);
  assert.equal(await page.locator('[data-deck-type]').count(),Object.keys(fixture.settings.config).length);
  assert.equal(await page.locator('#deckLayoutPreview').count(),0);
  const master=page.locator('.switch:has([data-key="deck_overview_enabled"])');
  await master.click();
  assert.equal(await page.locator('#deck_overview_green').isDisabled(),true);
  assert.equal(await page.locator('#deckOverviewOptions .dd-btn:enabled').count(),0);
  await master.click();
  assert.equal(await page.locator('#deck_overview_green').isEnabled(),true);
  await page.evaluate(()=>{setSelect('deck_overview_layout','focus');document.getElementById('deck_overview_layout').dispatchEvent(new Event('change'));});
  await page.locator('#deck_overview_green').fill('65');await page.locator('#deck_overview_orange').fill('70');
  assert.equal(await page.evaluate(()=>validateDeckOverviewSettings()),false);
  await page.locator('#deck_overview_green').fill('90');await page.locator('#deck_overview_orange').fill('75');
  assert.equal(await page.evaluate(()=>validateDeckOverviewSettings()),true);
  await page.locator('.switch:has(#deck_overview_indicators_all)').click();
  await page.evaluate(()=>{setSelect('deck_overview_title_color_mode','custom');document.getElementById('deck_overview_title_color_mode').dispatchEvent(new Event('change'));});
  assert.equal(await page.locator('#deck_overview_title_color').isVisible(),true);
  await page.locator('#deck_overview_title_color').fill('#abcdef');
  assert.equal(await page.evaluate(()=>collect().deck_overview_title_color),'#abcdef');
  const settings=await page.evaluate(()=>collect());assert.equal(settings.deck_overview_indicators_all,true);assert.equal(settings.deck_overview_layout,'focus');assert.equal(settings.deck_overview_green,90);
  await page.setViewportSize({width:1000,height:900});await page.screenshot({path:'/tmp/deck-settings.png',fullPage:true});
  await page.locator('#deckOverviewOptions').scrollIntoViewIfNeeded();
  await page.screenshot({path:'/tmp/deck-settings-preview.png'});
  await page.evaluate(()=>{document.documentElement.classList.add('dark');document.body.classList.add('dark');});
  await page.screenshot({path:'/tmp/deck-settings-dark.png'});
  await page.evaluate(()=>save());assert.ok(commands.some(c=>c.startsWith('SYNAPSEPRO_SETTINGS:save:')&&c.includes('"deck_overview_green":90')));
  assert.deepEqual(errors,[]);assert.ok(!commands.some(c=>c.startsWith('SYNAPSEPRO_SETTINGS:err:')),commands.join('\n'));
  console.log('PASS three layouts, light/dark, 400/1000 px, stats details, actions, cloud, simplified settings and master disable, threshold validation and save payload');
 }finally{await browser.close();fs.rmSync(fixture.output,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1)});
