const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const onboarding=JSON.parse(fs.readFileSync('/tmp/synapse-onboarding-payload.json','utf8'));
const payloads=JSON.parse(fs.readFileSync('/tmp/synapse-translation-payloads.json','utf8'));
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 try{
  for(const isDark of [false,true]){
   const page=await browser.newPage({viewport:{width:860,height:540}}),errors=[],completed=[];
   page.on('pageerror',e=>errors.push(e.message));
   page.on('console',m=>{if(m.text().startsWith('SYNAPSEPRO_COMPLETE:'))completed.push(JSON.parse(m.text().slice('SYNAPSEPRO_COMPLETE:'.length)));});
   await page.goto('file://'+root+'/onboarding/onboarding.html');
   await page.evaluate(p=>initOnboarding(p),{...onboarding,isDark});
   assert.deepEqual(await page.evaluate(()=>Object.keys(T.pl).sort()),await page.evaluate(()=>Object.keys(T.en).sort()));
   await page.check('#tos-check');await page.click('#btn-welcome');
   assert.equal(await page.locator('[data-lang]').count(),10);
   await page.click('[data-lang="pl"]');
   assert.equal(await page.locator('html').getAttribute('lang'),'pl');
   assert.equal(await page.locator('#screen-1 .screen-title').textContent(),'Wybierz język');
   const clipped = await page.locator('#screen-1 .opt').evaluateAll(buttons=>buttons.filter(b=>b.scrollWidth>b.clientWidth+1 || b.scrollHeight>b.clientHeight+1).map(b=>b.textContent));
   assert.deepEqual(clipped, [], 'language labels must fit at the minimum dialog size');
   await page.screenshot({path:`/tmp/onboarding-pl-${isDark?'dark':'light'}.png`});
   await page.click('#btn-next-1');
   await page.click('[data-group="role"][data-value="medical"]');await page.click('#btn-next-2');
   await page.click('[data-group="source"][data-value="friends"]');await page.click('#btn-next-3');
   await page.locator('[data-group="theme"]').nth(2).click();await page.click('#btn-next-4');
   assert.match(await page.locator('#screen-5').innerText(),/ustawienia/);
   await page.locator('#screen-5 .btn-cta').click();
   await page.waitForFunction(()=>!document.getElementById('btn-start').disabled);
   await page.click('#btn-start');
   assert.deepEqual(completed,[{lang:'pl',themeNumber:3,roleKey:'medical',source:'friends'}]);
   await page.evaluate(()=>openTos({preventDefault(){}}));
   assert.equal(await page.locator('#tos-title').textContent(),'Warunki korzystania i prywatność');
   assert.equal(await page.locator('#tos-content h4').count(),8);
   assert.deepEqual(errors,[]);
   await page.close();
  }
  const page=await browser.newPage({viewport:{width:960,height:700}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file://'+root+'/settings_web/settings.html');
  await page.evaluate(translations=>initSettings({config:{language:'pl'},translations,isDark:true,initialPage:'general',backgroundThemes:[],banner:{}}),payloads.pl.settings);
  assert.equal(await page.locator('#language').inputValue(),'pl');
  assert.equal(await page.evaluate(()=>collect().language),'pl');
  assert.equal(await page.locator('#language option[value="pl"]').textContent(),'Polski');
  assert.equal(await page.locator('#language option').count(),11); // 10 languages + Auto
  await page.screenshot({path:'/tmp/settings-pl.png'});
  assert.deepEqual(errors,[]);
  await page.goto('file://'+root+'/chat_ui.html');
  await page.evaluate(translations=>init({provider:'openai',translations,language:'Polish',isDark:true}),payloads.pl.ai);
  assert.equal(await page.locator('#s-language').inputValue(),'Polish');
  assert.equal(await page.locator('#s-language option[value="Polish"]').textContent(),'Polski');
  await page.close();
  console.log('PASS Polish onboarding full flow at 860×540 in both modes, terms, 10-language Settings and AI response language');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
