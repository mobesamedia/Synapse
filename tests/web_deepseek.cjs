const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file://'+path.resolve(__dirname,'../chat_ui.html'));
 await page.evaluate(()=>{window.sent=[];window.sendToPython=(action,data)=>sent.push({action,data});document.getElementById('settings-panel').classList.add('open');});
 await page.selectOption('#s-provider','deepseek');
 assert.equal(await page.inputValue('#s-model'),'deepseek-flash');
 assert.deepEqual(await page.locator('#s-model-list option').evaluateAll(opts=>opts.map(o=>o.value)),['deepseek-flash','deepseek-v4-pro']);
 assert(await page.locator('#s-apikey').isVisible());
 await page.evaluate(()=>openKeyHelp());
 assert.match(await page.locator('#kh-title').textContent(),/DeepSeek/);
 await page.locator('#kh-open-btn').click();
 assert.equal(await page.evaluate(()=>sent.at(-1).data.url),'https://platform.deepseek.com/api_keys');
 await page.evaluate(()=>{document.getElementById('s-apikey').value='fake-deepseek-key';saveSettings();});
 const saved=await page.evaluate(()=>sent.find(x=>x.action==='save_settings').data);
 assert.equal(saved.provider,'deepseek');assert.equal(saved.model,'deepseek-flash');assert.equal(saved.apiKey,'fake-deepseek-key');
 for(const isDark of [false,true]){
 await page.evaluate(cfg=>init(cfg),{...saved,isDark,isConfigured:true});
 assert.equal(await page.inputValue('#s-provider'),'deepseek');assert.equal(await page.inputValue('#s-apikey'),'fake-deepseek-key');
 await page.evaluate(()=>{startAIBubble();appendThinking('Reasoning');appendChunk('DeepSeek answer');finalizeResponse();});
 assert.match(await page.locator('#chat').innerText(),/DeepSeek answer/);
 }
 assert.deepEqual(errors,[]);console.log('PASS DeepSeek provider, models, key help link, save/reload and answer streaming in both themes');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
