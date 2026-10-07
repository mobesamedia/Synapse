/* Shared center artwork and tier-only rims keep every badge sharp at any size. */
(function () {
  'use strict';
  var badges = [], labels = {}, selected = null, nextGoalKey = null;
  var tierFiles = ['bronze','silver','gold','diamond'];
  function badgeFile(key, tier) {
    if (key === 'comeback') return tier >= 0 ? 'earned' : 'locked';
    return tierFiles[tier] || 'locked';
  }
  function badgeImage(key, tier, className) {
    var src = '../media/Achievements/' + encodeURIComponent(key) + '/' + badgeFile(key, tier) + '.svg';
    return '<img src="' + src + '" class="' + (className || '') + '" alt="" aria-hidden="true">';
  }
  function tierName(b) { return b.tier < 0 ? labels.locked : b.tiers[b.tier].name; }
  function earnedDate(value) {
    if (!value) return '';
    var parsed = new Date(value + 'T12:00:00');
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
  }
  function goalKey(b) { return b.id + ':' + b.target; }
  function goalProgress(b) {
    var value = Number(b.goalValue);
    return Number.isFinite(value) ? Math.max(0, value) : Math.max(0, Number(b.value) || 0);
  }
  function goalRemaining(b) {
    var remaining = Number(b.goalRemaining);
    return Number.isFinite(remaining) ? Math.max(0, remaining) : Math.max(0, Number(b.target) - goalProgress(b));
  }
  function markSeen(b) {
    if (!b || !b.isNew) return;
    b.isNew = false;
    var marker = document.querySelector('[data-badge="'+b.id+'"] .achievement-new');
    if (marker) marker.remove();
    bridge('achievementSeen:' + b.id);
  }
  function goalCandidates() {
    return badges.filter(function(b){
      return b.target != null && (b.id !== 'comeback' || goalProgress(b) > 0);
    });
  }
  function chooseNextGoal() {
    var candidates = goalCandidates();
    var retained = candidates.find(function(b){return goalKey(b) === nextGoalKey;});
    if (retained) return retained;
    var nearby = candidates.filter(function(b){
      var remaining = goalRemaining(b);
      return b.id === 'reviews' ? remaining <= 50 : remaining <= 3;
    });
    var pool = nearby.length ? nearby : candidates;
    pool.sort(function(a,b){
      var aProgress = goalProgress(a) / Math.max(1, Number(a.target));
      var bProgress = goalProgress(b) / Math.max(1, Number(b.target));
      return bProgress - aProgress || goalRemaining(a) - goalRemaining(b);
    });
    var chosen = pool[0] || null;
    nextGoalKey = chosen ? goalKey(chosen) : null;
    return chosen;
  }
  function renderNextGoal() {
    var goal = chooseNextGoal();
    var button = document.getElementById('achievementGoal');
    var hint = document.getElementById('achievementHint');
    button.hidden = !goal;
    hint.hidden = !!goal;
    if (!goal) return;
    var remaining = goalRemaining(goal);
    var tier = goal.tiers[goal.tier + 1].name;
    var unit = remaining === 1 ? goal.goalUnitOne : goal.goalUnitMany;
    document.getElementById('achievementGoalLabel').textContent = labels.nextGoal;
    document.getElementById('achievementGoalTitle').textContent = goal.name + ' · ' + tier;
    document.getElementById('achievementGoalProgress').textContent = remaining === 1
      ? fmt(labels.goalOne, unit, tier)
      : fmt(labels.goalMany, num(remaining), unit, tier);
    button.dataset.goalBadge = goal.id;
    button.setAttribute('aria-label', labels.nextGoal + ': ' + goal.name + '. ' + document.getElementById('achievementGoalProgress').textContent);
    button.setAttribute('aria-expanded', String(selected === goal.id));
  }
  function showDetail() {
    var panel = document.getElementById('achievementDetail');
    var b = badges.find(function(item){return item.id === selected;});
    panel.hidden = !b;
    document.querySelectorAll('.achievement-button').forEach(function(button){
      button.setAttribute('aria-expanded', String(button.dataset.badge === selected));
    });
    var goalButton = document.getElementById('achievementGoal');
    goalButton.setAttribute('aria-expanded', String(goalButton.dataset.goalBadge === selected));
    if (!b) return;
    document.getElementById('achievementArt').innerHTML = badgeImage(b.id, b.tier);
    document.getElementById('achievementName').textContent = b.name;
    document.getElementById('achievementTier').textContent = tierName(b);
    var earned = b.tier >= 0 ? b.tiers[b.tier].earnedAt : '';
    var earnedLine = document.getElementById('achievementEarnedDate');
    earnedLine.hidden = !earned;
    earnedLine.textContent = earned ? fmt(labels.earnedOn, earnedDate(earned)) : '';
    document.getElementById('achievementDescription').textContent = b.description;
    var favorite = document.getElementById('achievementFavorite');
    favorite.hidden = b.tier < 0;
    favorite.classList.toggle('active', !!b.isFavorite);
    favorite.textContent = b.isFavorite ? '★ ' + labels.favorite : '☆ ' + labels.chooseFavorite;
    favorite.setAttribute('aria-pressed', String(!!b.isFavorite));
    var value = b.id === 'comeback' && b.tier >= 0 ? 3 : b.value;
    document.getElementById('achievementValue').textContent = fmt(labels.value, num(value));
    var target = b.target;
    document.getElementById('achievementNext').textContent = target == null ? labels.complete : fmt(labels.next, b.tiers[b.tier+1].name);
    document.getElementById('achievementRemaining').textContent = target == null ? labels.permanent : fmt(labels.remaining, num(b.remaining));
    var progress = document.getElementById('achievementProgress');
    progress.max = target || 1;
    progress.value = target == null ? 1 : Math.min(value, target);
    progress.setAttribute('aria-label', b.name);
    document.getElementById('achievementSteps').innerHTML = b.tiers.map(function(t,index){
      return '<li class="'+(t.earned ? 'earned' : '')+'">'+badgeImage(b.id,index,'achievement-step-badge')+
        '<span class="achievement-step-rule" aria-hidden="true"></span><span>'+esc(t.name)+(t.earned ? ' ✓' : '')+'</span><span>'+num(t.target)+'</span></li>';
    }).join('');
  }
  window.renderAchievements = function(items, text) {
    badges = items || []; labels = text || {};
    document.getElementById('achievementsLabel').textContent = labels.title;
    document.getElementById('achievementHint').textContent = labels.hint;
    document.getElementById('achievementClose').setAttribute('aria-label', labels.close);
    document.getElementById('achievementCount').textContent = badges.reduce(function(n,b){return n+b.tiers.filter(function(t){return t.earned;}).length;},0) + ' / ' + badges.reduce(function(n,b){return n+b.tiers.length;},0);
    var grid = document.getElementById('achievementGrid');
    // Keep focused buttons in place when the Python payload refreshes.
    badges.forEach(function(b){
      var button = grid.querySelector('[data-badge="'+b.id+'"]');
      if (!button) {
        button = document.createElement('button');
        button.type = 'button'; button.className = 'achievement-button';
        button.dataset.badge = b.id; button.setAttribute('aria-controls', 'achievementDetail');
        button.addEventListener('click', function(){
          var badgeId = this.dataset.badge;
          selected = selected === badgeId ? null : badgeId;
          if (selected) markSeen(badges.find(function(item){return item.id === badgeId;}));
          showDetail();
        });
        grid.appendChild(button);
      }
      var label = b.name + ': ' + tierName(b);
      button.title = label; button.setAttribute('aria-label', label);
      button.classList.toggle('locked', b.tier < 0);
      var signature = b.id + ':' + b.tier + ':' + Number(!!b.isNew) + ':' + Number(!!b.isFavorite);
      if (button.dataset.signature !== signature) {
        button.dataset.signature = signature;
        button.innerHTML = badgeImage(b.id, b.tier) +
          (b.isNew ? '<span class="achievement-new">'+esc(labels.new)+'</span>' : '') +
          (b.isFavorite ? '<span class="achievement-favorite-mark" aria-hidden="true">★</span>' : '') +
          (b.tier < 0 ? '<span class="achievement-lock" aria-hidden="true">'+
          '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3.5" y="7" width="9" height="7" rx="2"/><path d="M5.5 7V4.5a2.5 2.5 0 0 1 5 0V7"/></svg></span>' : '');
      }
    });
    renderNextGoal();
    showDetail();
  };
  document.getElementById('achievementGoal').addEventListener('click', function(){
    selected = this.dataset.goalBadge || null;
    markSeen(badges.find(function(item){return item.id === selected;}));
    showDetail();
  });
  document.getElementById('achievementClose').addEventListener('click', function(){
    var button = document.querySelector('[data-badge="'+selected+'"]');
    selected = null; showDetail(); if(button) button.focus();
  });
  document.getElementById('achievementFavorite').addEventListener('click', function(){
    var b = badges.find(function(item){return item.id === selected;});
    if (!b || b.tier < 0) return;
    badges.forEach(function(item){item.isFavorite = item.id === b.id ? !b.isFavorite : false;});
    bridge('favoriteAchievement:' + b.id);
    renderAchievements(badges, labels);
  });
  document.getElementById('achievementsCard').addEventListener('keydown', function(e){
    if (e.key === 'Escape' && selected) {e.preventDefault(); document.getElementById('achievementClose').click();}
  });
})();
