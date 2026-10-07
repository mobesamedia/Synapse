const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),{pathToFileURL}=require('node:url');
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.SYNAPSE_TEST_CHROME?{executablePath:process.env.SYNAPSE_TEST_CHROME}:{})});try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const dark of [false,true])for(const width of [360,430,700]){
  await page.setViewportSize({width,height:600});await page.goto(pathToFileURL(path.join(__dirname,'../settings_web/pomodoro.html')).href);
  await page.evaluate(dark=>{window.calls=[];window.bridge=(action,payload)=>calls.push({action,payload});init({isDark:dark,stats:{week:[{label:'Mon',count:2},{label:'Tue',count:4}]}})},dark);
  await page.waitForTimeout(80);
  const settingsHeight=await page.evaluate(()=>Number(calls.filter(c=>c.action==='resize').at(-1).payload));
  assert.equal(await page.evaluate(()=>calls.some(c=>c.action==='analytics')),false);
  await page.locator('#work').fill('42');await page.locator('#tab-statistics').click();await page.waitForTimeout(80);
  const statsHeight=await page.evaluate(()=>Number(calls.filter(c=>c.action==='resize').at(-1).payload));assert.notEqual(statsHeight,settingsHeight);
  await page.locator('#tab-analytics').click();
  await page.evaluate(()=>updateAnalytics({milliseconds:7200000,expanded:['Study'],decks:[{key:'Study',name:'Study',milliseconds:7200000,children:[{key:'Study::<b>Anatomy</b>',name:'<b>Anatomy</b>',milliseconds:7200000,children:[{key:'Study::<b>Anatomy</b>::Bones',name:'Bones',milliseconds:7200000,children:[]}]}]}]}));
  assert.equal(await page.locator('.deck-row').count(),2);assert.equal(await page.locator('.deck-name b').count(),0);
  await page.locator('button[aria-label="Study::<b>Anatomy</b>"]').click();assert.equal(await page.locator('.deck-row').count(),3);
  assert.equal(await page.evaluate(()=>calls.filter(c=>c.action==='expanded').length),1);
  await page.locator('#tab-settings').click();assert.equal(await page.locator('#work').inputValue(),'42');
  await page.locator('#tab-analytics').click();assert.equal(await page.evaluate(()=>calls.filter(c=>c.action==='analytics').length),1);
  await page.locator('#tab-analytics').press('Home');assert.equal(await page.locator('#tab-settings').getAttribute('aria-selected'),'true');
  await page.locator('#saveBtn').click();assert.equal(await page.evaluate(()=>JSON.parse(calls.find(c=>c.action==='save').payload).work),42);
  await page.locator('#tab-analytics').click();await page.waitForTimeout(80);const height=await page.evaluate(()=>Number(calls.filter(c=>c.action==='resize').at(-1).payload));await page.setViewportSize({width,height});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  if(width===430)await page.screenshot({path:'/tmp/timer-analytics-'+(dark?'dark':'light')+'.png'});
  await page.evaluate(()=>updateAnalytics({milliseconds:1000000,expanded:[],decks:Array.from({length:100},(_,i)=>({key:'Deck'+i,name:'Long deck name '+i,milliseconds:10000,children:[]}))}));
  await page.setViewportSize({width,height:600});
  assert.equal(await page.locator('.deck-row').count(),100);
  assert.equal(await page.locator('.content').evaluate(e=>e.scrollHeight>e.clientHeight),true);
  assert.ok(await page.locator('.footer').evaluate(e=>e.getBoundingClientRect().bottom<=innerHeight));
  await page.evaluate(()=>updateAnalytics({milliseconds:0,decks:[],expanded:[]}));assert.match(await page.locator('#analyticsBody').innerText(),/No recorded/);
  await page.evaluate(()=>analyticsFailed());await page.locator('#analyticsBody button').click();assert.equal(await page.evaluate(()=>calls.filter(c=>c.action==='analytics').length),2);
 }
 assert.deepEqual(errors,[]);console.log('PASS Timer tabs, responsive content heights, lazy analytics, hierarchy, escaped names, settings preservation, keyboard, retry, light/dark at 360/430/700px');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
