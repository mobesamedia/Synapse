const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),payloads=JSON.parse(fs.readFileSync('/tmp/synapse-translation-payloads.json','utf8'));
(async()=>{const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});try{
 for(const [lang,p] of Object.entries(payloads)){
  const page=await browser.newPage({viewport:{width:400,height:850}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file://'+root+'/chat_ui.html');
  await page.evaluate(translations=>init({provider:'openai',translations,fontSize:'13px',isDark:true}),p.ai);
  await page.evaluate(()=>{document.getElementById('settings-panel').classList.add('open');setSettingsTab('layout');});
  assert.equal(await page.locator('label[for="s-lineheight"]').textContent(),p.ai['Line spacing']);
  if(['de','hi','ko','pl'].includes(lang))await page.screenshot({path:'/tmp/ai-i18n-'+lang+'.png'});
  await page.goto('file://'+root+'/settings_web/settings.html');await page.evaluate(translations=>initSettings({config:{},translations,isDark:true,initialPage:'about',backgroundThemes:[],banner:{}}),p.settings);
  assert.equal(await page.locator('[data-page="about"] .page-title').textContent(),p.settings['About Synapse']);
  const context=await browser.newContext({viewport:{width:400,height:850}});await context.addInitScript(data=>{window.__SYNAPSE_I18N__=data;window.pycmd=()=>{};},p.pdf);
  const pdf=await context.newPage();pdf.on('pageerror',e=>errors.push(e.message));await pdf.goto('file://'+root+'/web_notebook/pdf_viewer.html');
  await pdf.evaluate(()=>{showViewer('User PDF name','/tmp/example.pdf');openCardCreator();});await pdf.selectOption('#creator-type','cloze');
  assert.equal(await pdf.locator('label[for="creator-front"]').textContent(),p.pdf.creator_text);
  assert.equal(await pdf.locator('[data-i18n="creator_new_cloze"]').textContent(),p.pdf.creator_new_cloze);
  assert.equal(await pdf.locator('#viewer-filename').textContent(),'User PDF name');
  for(const [tool,file] of [['notebook','index.html'],['todo','todo.html']]){
   const nested=await browser.newContext({viewport:{width:400,height:850}});
   await nested.addInitScript(data=>{window.__SYNAPSE_I18N__=data;window.pycmd=()=>{};},p[tool]);
   const view=await nested.newPage();view.on('pageerror',e=>errors.push(e.message));
   await view.goto('file://'+root+'/web_notebook/'+file);
   if(tool==='todo')assert.equal(await view.locator('[data-i18n="repeat_title"]').first().textContent(),p.todo.repeat_title);
   else assert.equal(await view.locator('[data-i18n-placeholder="search_placeholder"]').first().getAttribute('placeholder'),p.notebook.search_placeholder);
   await nested.close();
  }
  assert.deepEqual(errors,[],lang);await context.close();await page.close();
 }
 console.log('PASS 10 languages: actual AI, settings/About and PDF Cloze translations, no JS errors, user filename preserved');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
