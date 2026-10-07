const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
const fs=require('node:fs'), os=require('node:os');
const {pathToFileURL}=require('node:url');

(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.SYNAPSE_TEST_CHROME?{executablePath:process.env.SYNAPSE_TEST_CHROME}:{})});
  try {
    const page=await browser.newPage({viewport:{width:390,height:600}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const source=execFileSync(process.env.SYNAPSE_TEST_PYTHON||'python3',['-c',
      "from celebration_preview import render_preview; print(render_preview({'rank':{'old_image':'rang10.png','new_image':'rang11.png','old_name':'Fact Ferret','new_name':'Focus Falcon','level':50},'challenge':{'text':'Review 50 cards today.','xp':195}}))"],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'});
    const directory=fs.mkdtempSync(path.join(os.tmpdir(),'synapse-celebration-'));
    const fixture=path.join(directory,'preview.html');
    fs.writeFileSync(fixture,source);
    const url=pathToFileURL(fixture).href;
    for(const dark of [false,true]){
      for(const width of [280,390]){
        await page.setViewportSize({width,height:640});
        await page.goto(url);
        await page.evaluate(dark=>document.documentElement.classList.toggle('dark',dark),dark);
        await page.waitForTimeout(1800);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        assert.equal(await page.locator('.old').count(),1);
        assert.equal(await page.locator('.new').count(),1);
        assert.ok(await page.locator('.new').evaluate(e=>e.complete&&e.naturalWidth>0));
        if(width===390 && process.env.SYNAPSE_TEST_SCREENSHOT_DIR){
          await page.screenshot({path:path.join(process.env.SYNAPSE_TEST_SCREENSHOT_DIR,dark?'celebration-dark.png':'celebration-light.png')});
        }
        await page.locator('.close').focus();await page.keyboard.press('Shift+Tab');
        assert.equal(await page.locator('.settings').evaluate(e=>e===document.activeElement),true);
        await page.keyboard.press('Tab');
        assert.equal(await page.locator('.close').evaluate(e=>e===document.activeElement),true);
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#preview').isVisible(),false);
      }
    }
    await page.goto(url);await page.locator('.continue').click();
    assert.equal(await page.locator('#preview').isVisible(),false);
    await page.emulateMedia({reducedMotion:'reduce'});await page.goto(url);
    assert.equal(await page.locator('.new').evaluate(e=>getComputedStyle(e).animationName),'none');
    await page.emulateMedia({reducedMotion:'no-preference'});
    for(const mode of ['level','challenge']){
      const html=execFileSync(process.env.SYNAPSE_TEST_PYTHON||'python3',['-c',
        "from celebration_preview import render_preview; import sys; print(render_preview({'level':{'new':50}} if sys.argv[1]=='level' else {'challenge':{'text':'Review 50 cards today.','xp':195}}))",mode],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'});
      fs.writeFileSync(fixture,html);
      for(const dark of [false,true]){
        await page.goto(url);
        await page.evaluate(dark=>document.documentElement.classList.toggle('dark',dark),dark);
        await page.waitForTimeout(1100);
        assert.equal(await page.locator('#title').count(),1);
        if(mode==='level')assert.equal((await page.locator('.card').innerText()).match(/50/g).length,1);
        else assert.equal(await page.locator('.goal-check').evaluate(e=>getComputedStyle(e).strokeDashoffset),'0px');
        assert.equal(await page.evaluate(()=>document.getAnimations().filter(a=>a.playState==='running').length),0);
        if(process.env.SYNAPSE_TEST_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.SYNAPSE_TEST_SCREENSHOT_DIR,mode+(dark?'-dark':'-light')+'.png')});
      }
      await page.emulateMedia({reducedMotion:'reduce'});await page.goto(url);
      assert.equal(await page.locator(mode==='level'?'.level-number':'.goal-check').evaluate(e=>getComputedStyle(e).animationName),'none');
      await page.emulateMedia({reducedMotion:'no-preference'});
    }
    const live=execFileSync(process.env.SYNAPSE_TEST_PYTHON||'python3',['-c',`
import sys, types, pathlib
p=types.ModuleType('fixture'); p.__path__=[str(pathlib.Path.cwd())]; sys.modules['fixture']=p
l=types.ModuleType('fixture.locales'); l._=lambda text:text; sys.modules[l.__name__]=l
a=types.ModuleType('aqt'); a.mw=types.SimpleNamespace(addonManager=types.SimpleNamespace(addonFromModule=lambda name:'fixture')); sys.modules['aqt']=a
t=types.ModuleType('aqt.theme'); t.theme_manager=types.SimpleNamespace(night_mode=False); sys.modules[t.__name__]=t
from fixture.theme import set_active_theme, set_custom_theme_colors
set_active_theme('custom')
set_custom_theme_colors({'blue':'#a83479'})
from fixture.celebration_live import render_celebration_modal
print(render_celebration_modal({'level':{'new':50}}))
`],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'});
    for(const action of ['.continue','.close','.settings','Escape']){
      await page.setContent('<button id="background">Background</button><script>window.commands=[];window.pycmd=c=>commands.push(c);</script>'+live);
      const frame=page.frameLocator('#synapse-celebration-frame');
      await frame.locator('.continue').waitFor();
      assert.equal(await frame.locator('.continue').evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(168, 52, 121)');
      assert.equal(await frame.locator('.level-number').evaluate(el=>getComputedStyle(el).color),'rgb(168, 52, 121)');
      assert.equal(await frame.locator('body').evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');
      assert.equal(await frame.locator('html').evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');
      assert.equal(await page.locator('#background').evaluate(el=>el.inert),true);
      if(action==='Escape'){await frame.locator('.continue').focus();await page.keyboard.press('Escape');}
      else await frame.locator(action).click();
      await page.locator('#synapse-celebration-frame').waitFor({state:'detached'});
      assert.equal(await page.locator('#background').evaluate(el=>el.inert),false);
      assert.deepEqual(await page.evaluate(()=>commands),action==='.settings'?['pycmd:synapsepro:celebration_settings']:[]);
    }
    const messages=[];page.on('console',m=>messages.push(m.text()));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../settings_web/settings.html')).href);
    // Real pointer clicks on both visible version labels, including navigation
    // from the sidebar logo to About, not synthetic clicks on a hidden node.
    for(let i=0;i<3;i++) await page.locator('#brandVer').click();
    assert.equal(await page.locator('#developerStatus').textContent(),'3 / 7');
    for(let i=0;i<3;i++) await page.locator('#aboutVersion').click();
    assert.equal(messages.filter(m=>m.includes('developerUnlock')).length,0);
    await page.locator('#aboutVersion').click();
    assert.equal(messages.filter(m=>m.includes('developerUnlock')).length,1);
    await page.evaluate(()=>developerConsoleStatus('Console unlocked',true));
    assert.equal(await page.locator('#developerOpen').isVisible(),true);
    await page.locator('#developerOpen').click();
    assert.equal(messages.filter(m=>m.includes('developerUnlock')).length,2);
    await page.evaluate(()=>initSettings({initialPage:'dashboard',initialSection:'celebrations',config:{gamification_popups_enabled:false}}));
    await page.waitForTimeout(100);
    assert.equal(await page.locator('.page.active').getAttribute('data-page'),'dashboard');
    assert.equal(await page.locator('[data-key="gamification_popups_enabled"]').evaluate(el=>el===document.activeElement),true);
    const box=await page.locator('[data-key="gamification_popups_enabled"]').boundingBox();
    assert.ok(box.y>0 && box.y+box.height<640);
    assert.equal(await page.locator('[data-key="gamification_popup_rank"] + .slider').isVisible(),false);
    await page.locator('[data-key="gamification_popups_enabled"] + .slider').click();
    assert.equal(await page.locator('[data-key="gamification_popup_rank"] + .slider').isVisible(),true);
    assert.deepEqual(errors,[]);
    console.log('PASS preview modes, narrow layouts, close during animation, keyboard focus, reduced motion, seven-click unlock');
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
