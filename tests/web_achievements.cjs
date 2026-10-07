const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const fs = require('node:fs');
const {execFileSync} = require('node:child_process');

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.SYNAPSE_TEST_CHROME ? {executablePath:process.env.SYNAPSE_TEST_CHROME} : {})});
  try {
    const page = await browser.newPage({viewport:{width:300,height:1100}});
    const errors = [], commands = [];
    page.on('pageerror', e=>errors.push(e.message));
    page.on('console', m=>{if(m.text().startsWith('SYNAPSEPRO_GAMI:'))commands.push(m.text())});
    await page.goto(pathToFileURL(path.resolve(__dirname,'../gamification_web/sidebar.html')).href);
    const ids = ['streak','reviews','days','challenges','comeback'];
    const names = ['Lernserie','Wiederholungen','Lerntage','Tagesziele','Wiedereinstieg'];
    const tierNames = ['Bronze','Silber','Gold','Diamant'];
    const payload = {
      level:15,rankName:'Deck Diver',xp:120,xpNeeded:250,progressPct:48,streak:12,streakXp:240,
      challenge:{text:'Wiederhole heute 50 Karten.',cur:35,target:50,xpReward:195},
      ranks:[], labels:{challenge:'Daily Challenge',allRanks:'Alle Ränge'},
      achievementLabels:{title:'Abzeichen',hint:'Klicke auf ein Abzeichen, um deinen Fortschritt zu sehen.',locked:'Noch nicht verdient',close:'Schließen',value:'Erfasster Fortschritt: {}',next:'Nächste Stufe: {}',remaining:'Noch benötigt: {}',complete:'Alle Stufen verdient',permanent:'Dieses Abzeichen bleibt dir erhalten.',nextGoal:'Dein nächstes Abzeichen',goalOne:'Noch 1 {} bis {}.',goalMany:'Noch {} {} bis {}.',new:'Neu',earnedOn:'Erreicht am {}',chooseFavorite:'Als Lieblingsabzeichen wählen',favorite:'Lieblingsabzeichen'},
      achievements:ids.map((id,i)=>({id,name:names[i],tier:[0,1,2,3,-1][i],isNew:i===0,isFavorite:i===1,value:[12,6200,120,365,2][i],goalValue:[4,6200,120,365,2][i],target:[30,25000,365,null,3][i],remaining:[18,18800,245,0,1][i],goalRemaining:[26,18800,245,0,1][i],goalUnitOne:['Serientag','Wiederholung','Lerntag','Tagesziel','Lerntag'][i],goalUnitMany:['Serientage','Wiederholungen','Lerntage','Tagesziele','Lerntage'][i],description: i===4 ? 'Lerne nach mindestens sieben vollen Tagen ohne Wiederholungen an drei aufeinanderfolgenden Anki-Tagen. Dieses Abzeichen wird einmalig vergeben.' : 'Lerne an aufeinanderfolgenden Anki-Tagen. Deine längste erfasste Serie zählt, auch nach einer Pause.',tiers:(i===4?[3]:i===1?[500,5000,25000,100000]:[7,30,100,365]).map((target,t)=>({target,name:i===4?'Verdient':tierNames[t],earned:t <= [0,1,2,3,-1][i],earnedAt:t <= [0,1,2,3,-1][i]?'2026-09-09':null}))}))
    };
    await page.evaluate(d=>{window.testPayload=d;initGamification(d)},payload);
    assert.equal(await page.locator('.achievement-button').count(),5);
    await page.waitForFunction(()=>[...document.querySelectorAll('.achievement-button>img')].every(img=>img.complete&&img.naturalWidth>0));
    const lockedStyle=await page.locator('[data-badge="comeback"]>img').evaluate(e=>({opacity:getComputedStyle(e).opacity,filter:getComputedStyle(e).filter}));
    assert.ok(Number(lockedStyle.opacity)<.4,lockedStyle.opacity);
    assert.ok(lockedStyle.filter.includes('grayscale'),lockedStyle.filter);
    assert.equal(await page.locator('#achievementCount').textContent(),'10 / 17');
    assert.equal(await page.locator('.achievement-new').textContent(),'Neu');
    assert.equal(await page.locator('[data-badge="reviews"] .achievement-favorite-mark').textContent(),'★');
    assert.equal(await page.locator('#achievementGoalTitle').textContent(),'Wiedereinstieg · Verdient');
    assert.equal(await page.locator('#achievementGoalProgress').textContent(),'Noch 1 Lerntag bis Verdient.');
    assert.equal(await page.locator('#achievementHint').isHidden(),true);
    await page.locator('#achievementGoal').click();
    assert.equal(await page.locator('#achievementName').textContent(),'Wiedereinstieg');
    await page.locator('#achievementClose').click();
    assert.ok(await page.locator('#achievementsCard').evaluate(e=>e.previousElementSibling.id==='challengeCard'));
    await page.setViewportSize({width:900,height:1100});
    const badgeWidths=await page.locator('.achievement-button').evaluateAll(buttons=>buttons.map(button=>button.getBoundingClientRect().width));
    assert.ok(badgeWidths.every(width=>width<=54.1),badgeWidths.join(','));
    if(process.env.SYNAPSE_TEST_SCREENSHOT_DIR) await page.locator('#achievementsCard').screenshot({path:path.join(process.env.SYNAPSE_TEST_SCREENSHOT_DIR,'badges-wide.png')});
    for (const dark of [false,true]) {
      for (const width of [240,300,420]) {
        await page.setViewportSize({width,height:1100});
        await page.evaluate(dark=>{testPayload.isDark=dark;initGamification(testPayload)},dark);
        await page.locator('[data-badge="streak"]').click();
        if (!await page.locator('#achievementDetail').isVisible()) await page.locator('[data-badge="streak"]').click();
        assert.equal(await page.locator('#achievementRemaining').textContent(),'Noch benötigt: 18');
        assert.match(await page.locator('#achievementEarnedDate').textContent(),/^Erreicht am /);
        assert.equal(await page.locator('#achievementProgress').evaluate(e=>[e.value,e.max].join('/')),'12/30');
        assert.equal(await page.locator('#achievementSteps .achievement-step-badge').count(),4);
        assert.ok(await page.locator('#achievementSteps li:not(.earned) .achievement-step-badge').first().evaluate(e=>Number(getComputedStyle(e).opacity)<.4));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        if (width===300 && process.env.SYNAPSE_TEST_SCREENSHOT_DIR) {
          await page.locator('#achievementsCard').screenshot({path:path.join(process.env.SYNAPSE_TEST_SCREENSHOT_DIR, dark?'badges-dark.png':'badges-light.png')});
        }
        await page.locator('[data-badge="challenges"]').click();
        assert.equal(await page.locator('#achievementNext').textContent(),'Alle Stufen verdient');
        await page.locator('[data-badge="comeback"]').click();
        assert.equal(await page.locator('#achievementRemaining').textContent(),'Noch benötigt: 1');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#achievementDetail').isVisible(),false);
        assert.equal(await page.locator('[data-badge="comeback"]').evaluate(e=>e===document.activeElement),true);
      }
    }
    const nextPayload = structuredClone(payload);
    nextPayload.achievements[1].goalValue = 24970;
    nextPayload.achievements[1].goalRemaining = 30;
    nextPayload.achievements[2].goalValue = 363;
    nextPayload.achievements[2].goalRemaining = 2;
    nextPayload.achievements[4].goalValue = 0;
    nextPayload.achievements[4].goalRemaining = 3;
    await page.evaluate(d=>initGamification(d),nextPayload);
    assert.equal(await page.locator('#achievementGoalTitle').textContent(),'Wiederholungen · Gold');
    nextPayload.achievements[2].goalValue = 364;
    nextPayload.achievements[2].goalRemaining = 1;
    await page.evaluate(d=>initGamification(d),nextPayload);
    assert.equal(await page.locator('#achievementGoalTitle').textContent(),'Wiederholungen · Gold');
    await page.locator('[data-badge="reviews"]').focus();
    await page.keyboard.press('Enter');
    await page.evaluate(()=>initGamification(testPayload));
    assert.equal(await page.locator('[data-badge="reviews"]').evaluate(e=>e===document.activeElement),true);
    assert.equal(await page.locator('#achievementDetail').isVisible(),true);
    assert.equal(commands.filter(c=>c==='SYNAPSEPRO_GAMI:achievementSeen:streak').length,1);
    assert.ok(commands.every(c=>c==='SYNAPSEPRO_GAMI:ready'||c==='SYNAPSEPRO_GAMI:achievementSeen:streak'),commands.join('\n'));
    // Individual preferences use one listener each, even after reinjection.
    await page.locator('#achievementClose').click();
    await page.evaluate(()=>initGamification(window.testPayload));
    assert.equal(await page.locator('[data-popup-type="level"]').isChecked(),false);
    assert.equal(await page.locator('[data-popup-type="rank"]').isChecked(),true);
    await page.locator('#gamificationSettings').click();
    await page.locator('[data-popup-type="level"]').check();
    assert.equal(commands.filter(c=>c==='SYNAPSEPRO_GAMI:popupType:level:1').length,1);
    await page.locator('#popupsToggle').uncheck();
    assert.equal(await page.locator('[data-popup-type="rank"]').isDisabled(),true);
    await page.locator('#popupsToggle').check();
    assert.equal(await page.locator('[data-popup-type="level"]').isChecked(),true);
    await page.evaluate(()=>initGamification({...window.testPayload,popupTypes:{rank:false,level:true,challenge:false}}));
    assert.equal(await page.locator('[data-popup-type="rank"]').isChecked(),false);
    assert.equal(await page.locator('[data-popup-type="level"]').isChecked(),true);
    assert.equal(await page.locator('[data-popup-type="challenge"]').isChecked(),false);
    await page.locator('#gamificationSettingsOverlay .gami-close').click();
    await page.locator('[data-badge="days"]').click();
    await page.locator('#achievementFavorite').click();
    assert.equal(commands.filter(c=>c==='SYNAPSEPRO_GAMI:favoriteAchievement:days').length,1);
    assert.equal(await page.locator('[data-badge="days"] .achievement-favorite-mark').textContent(),'★');
    const promotedPayload=structuredClone(payload);
    promotedPayload.achievements[0].tier=1;
    promotedPayload.achievements[0].isNew=true;
    promotedPayload.achievements[0].tiers[1].earned=true;
    promotedPayload.achievements[0].tiers[1].earnedAt='2026-09-10';
    await page.evaluate(d=>initGamification(d),promotedPayload);
    await page.locator('[data-badge="streak"]').click();
    assert.equal(commands.filter(c=>c==='SYNAPSEPRO_GAMI:achievementSeen:streak').length,2);
    assert.deepEqual(errors,[]);
    if(process.env.SYNAPSE_TEST_SCREENSHOT_DIR){
      for(const dark of [false,true]){
        await page.setViewportSize({width:300,height:700});
        await page.evaluate(dark=>initGamification({...window.testPayload,isDark:dark}),dark);
        await page.locator('#gamificationSettings').click();
        await page.locator('#popupsCard').screenshot({path:path.join(process.env.SYNAPSE_TEST_SCREENSHOT_DIR,dark?'popup-settings-dark.png':'popup-settings-light.png')});
        await page.keyboard.press('Escape');
      }
    }
    const previewSource=execFileSync(process.env.SYNAPSE_TEST_PYTHON||'python3',[
      '-c',"from developer_console import _achievement_preview_document; print(_achievement_preview_document('near'))"
    ],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'});
    const achievementsSource=fs.readFileSync(path.resolve(__dirname,'../gamification_web/achievements.js'),'utf8');
    const localBase='<base href="'+pathToFileURL(path.resolve(__dirname,'../gamification_web')+path.sep).href+'">';
    const previewHtml=previewSource.replace('<head>','<head>'+localBase).replace('<script src="achievements.js"></script>','<script>'+achievementsSource+'</script>');
    await page.setContent(previewHtml);
    await page.waitForSelector('body.ready');
    assert.equal(await page.locator('#achievementGoalTitle').textContent(),'Reviews · Bronze');
    assert.equal(await page.locator('#wrap > section').count(),1);
    assert.equal(await page.locator('#achievementsCard').isVisible(),true);
    assert.deepEqual(errors,[]);
    if(process.env.SYNAPSE_TEST_SCREENSHOT_DIR) await page.locator('#achievementsCard').screenshot({path:path.join(process.env.SYNAPSE_TEST_SCREENSHOT_DIR,'developer-achievements.png')});
    const gallerySource=execFileSync(process.env.SYNAPSE_TEST_PYTHON||'python3',[
      '-c',"from developer_console import _achievement_gallery_document; print(_achievement_gallery_document('gold'))"
    ],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'});
    const galleryHtml=gallerySource.replace('<head>','<head>'+localBase).replace('<script src="achievements.js"></script>','<script>'+achievementsSource+'</script>');
    await page.setContent(galleryHtml);
    await page.waitForSelector('body.ready');
    assert.equal(await page.locator('#achievementsLabel').textContent(),'Badge gallery: Gold');
    assert.equal(await page.locator('.achievement-button>img').count(),5);
    assert.equal(await page.locator('.achievement-button>img').nth(0).getAttribute('src'),'../media/Achievements/streak/gold.svg');
    assert.equal(await page.locator('.achievement-button>img').nth(4).getAttribute('src'),'../media/Achievements/comeback/earned.svg');
    assert.equal(await page.locator('#achievementGoal').isHidden(),true);
    await page.waitForFunction(()=>[...document.querySelectorAll('.achievement-button>img')].every(img=>img.complete&&img.naturalWidth>0));
    if(process.env.SYNAPSE_TEST_SCREENSHOT_DIR) await page.locator('#achievementsCard').screenshot({path:path.join(process.env.SYNAPSE_TEST_SCREENSHOT_DIR,'developer-gallery-gold.png')});
    console.log('PASS badge assets and sizing, keyboard, light/dark, goal selection, developer scenarios and popup settings');
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
