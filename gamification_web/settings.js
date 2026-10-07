/* Sidebar-local Gamification dialogs. */
(function () {
  window.initGamificationSettings = function () {};
  const reviews = document.getElementById('streakReviews');
  if (!reviews || !document.getElementById('gamificationSettings')) return;
  const cards = document.getElementById('streakCards');
  const allow = document.getElementById('streakAllowCards');
  let lastCards = 1;
  ['Settings', 'Info'].forEach(kind => {
    const button = document.getElementById('gamification' + kind);
    const dialog = document.getElementById('gamification' + kind + 'Overlay');
    button.addEventListener('click', () => {
      dialog.showModal();
      document.body.classList.add('gami-dialog-open');
    });
    dialog.querySelector('.gami-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => {
      document.body.classList.remove('gami-dialog-open');
      button.focus();
    });
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const r = dialog.getBoundingClientRect();
      if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
    });
  });
  function save() {
    cards.disabled = !allow.checked;
    if (!reviews.reportValidity() || (allow.checked && !cards.reportValidity())) return;
    bridge('streakRules:' + JSON.stringify({reviews:Number(reviews.value), cards:allow.checked ? Number(cards.value) : lastCards, allowCards:allow.checked}));
  }
  [reviews, cards, allow].forEach(input => input.addEventListener('change', save));
  window.initGamificationSettings = function (d) {
    const labels = d.streakLabels || {};
    const copy = {
      settingsTitle:['settings','Settings'],
      streakSettingsTitle:['title','Streak sensitivity'], streakReviewsLabel:['reviews','Minimum reviews per day'],
      streakAllowCardsLabel:['allowCards','Creating cards can also count'], streakCardsLabel:['cards','Minimum new cards per day'],
      streakSettingsHint:['hint',''], streakCreationHint:['creationHint',''], streakInfo:['info','']
    };
    Object.entries(copy).forEach(([id, pair]) => { document.getElementById(id).textContent = labels[pair[0]] || pair[1]; });
    document.querySelectorAll('.gami-close').forEach(button => button.setAttribute('aria-label', labels.close || 'Close'));
    [['gamificationSettings', labels.settings || 'Settings'], ['gamificationInfo', (d.labels || {}).how || 'How it works']].forEach(([id, label]) => {
      const button = document.getElementById(id);
      button.setAttribute('aria-label', label);
      button.title = label;
    });
    const rules = d.streakRules || {};
    lastCards = rules.cards || 1;
    // A celebration toggle can refresh the payload while a number is being edited.
    if (document.activeElement !== reviews) reviews.value = rules.reviews || 1;
    if (document.activeElement !== cards) cards.value = rules.cards || 1;
    allow.checked = !!rules.allowCards;
    cards.disabled = !allow.checked;
  };
})();
