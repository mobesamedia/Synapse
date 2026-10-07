const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
try {
 const page=await browser.newPage();const errors=[],commands=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.text().startsWith('SYNAPSEPRO_GAMI:'))commands.push(m.text());});
 await page.goto(pathToFileURL(path.resolve(__dirname,'../gamification_web/sidebar.html')).href);
 assert.equal(await page.locator('#friendsSummary,#friendsOverlay,#cheersOverlay').count(),0);
 assert.equal(await page.evaluate(()=>typeof window.initFriends),'undefined');
 for(const width of [300,360,900]) for(const isDark of [false,true]) {
  await page.setViewportSize({width,height:640});
  await page.evaluate(isDark=>initGamification({isDark,level:15,rankName:'Deck Diver',badgeStatic:new URL('../media/rang4.png',location.href).href,xp:120,xpNeeded:250,progressPct:48,streak:12,streakXp:240,challenge:{text:'Review 50 cards.',cur:35,target:50,xpReward:195},ranks:[],guideHtml:'<p>Earn XP, level up, and climb the ranks while studying!</p><p>Study time, daily challenges and streaks earn XP.</p>',streakLabels:{hint:'A day counts when either enabled goal is reached. Changes recalculate your current streak; earned XP and badges stay yours.',creationHint:'Uses creation dates of cards still in your collection, including imported cards.',info:'Your streak counts consecutive qualifying Anki days. Choose your daily criteria in Settings.'}}),isDark);
  assert.equal(await page.locator('#popupsCard').isVisible(),false);
  await page.locator('#gamificationSettings').click();
  assert.equal(await page.locator('#popupsCard').isVisible(),true);
  await page.locator('#streakReviews').fill('100');await page.locator('#streakReviews').press('Tab');
  await page.locator('#streakAllowCards').check();await page.locator('#streakCards').fill('3');await page.locator('#streakCards').press('Tab');
  assert.ok(commands.some(x=>x.includes('"reviews":100,"cards":3,"allowCards":true')));
  const before=commands.length;await page.locator('#streakReviews').fill('0');await page.locator('#streakReviews').press('Tab');assert.equal(commands.length,before);
  await page.locator('#streakReviews').fill('100');await page.locator('#streakReviews').press('Tab');
  await page.locator('#popupsToggle').uncheck();assert.equal(await page.locator('[data-popup-type="rank"]').isDisabled(),true);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(width===360)await page.screenshot({path:'/tmp/gamification-settings-'+(isDark?'dark':'light')+'.png'});
  await page.keyboard.press('Escape');assert.equal(await page.locator('#gamificationSettingsOverlay').isVisible(),false);
  assert.equal(await page.locator('#gamificationSettings').evaluate(e=>e===document.activeElement),true);
  await page.locator('#gamificationInfo').click();assert.equal(await page.locator('#guideBody').isVisible(),true);
  await page.locator('#gamificationInfoOverlay .gami-close').click();
  if(width===360)await page.screenshot({path:'/tmp/gamification-hero-'+(isDark?'dark':'light')+'.png'});
 }
 assert.deepEqual(errors,[]);console.log('PASS dialogs, focus, Escape, bridge, validation, popup toggles, widths 300/360/900, light/dark');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
