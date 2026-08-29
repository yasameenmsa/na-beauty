/* NA BEAUTY — single master video scroll (v7) */
(function () {
  'use strict';
  window.__MAINJS_VER = 'v7-single-master';

  var MASTER = window.NA_MASTER || { dur: 30.67, src: 'assets/clips/master.mp4', poster: 'assets/scenes/master/poster.jpg' };
  var QA = new URLSearchParams((location.search.slice(1) || '').replace(/;/g, '&'));
  var QA_ON = QA.get('qa') === '1';
  var QA_P = QA_ON ? Math.min(0.99, Math.max(0.01, parseFloat(QA.get('p') || '0.5'))) : null;

  // Chapters mapped to video time (0..1 progress)
  var CHAPTERS = [
    { at: 0.00, kicker: 'NA BEAUTY', title: 'حيث يُولَد الجمال', text: 'مرّري للأسفل وابدئي الرحلة — فيديو واحد يأخذكِ عبر كل الأقسام.', dur: 0.12 },
    { at: 0.10, kicker: '٠١ — الواجهة', title: 'واجهة فاخرة', text: 'حجر طبيعي، زجاج ضخم، وشعار NA BEAUTY يرحّب بكِ.', dur: 0.14 },
    { at: 0.24, kicker: '٠٢ — الاستقبال', title: 'الاستقبال والدرج', text: 'رخام، إضاءة دافئة، ودرج يقودكِ للطابق الثاني.', dur: 0.15 },
    { at: 0.39, kicker: '٠٣ — قسم الشعر', title: 'HAIR COLOR', text: 'كراسي خضراء، مرايا مضيئة، وـ IT\'S YOUR DAY TO SHINE.', dur: 0.16 },
    { at: 0.55, kicker: '٠٤ — المكتب الخاص', title: 'مساحة للاستشارة', text: 'أجواء هادئة للتخطيط لإطلالتكِ.', dur: 0.14 },
    { at: 0.69, kicker: '٠٥ — المنتجع', title: 'السبا والحمّام', text: 'روب معلق، زجاج مُصنفر، وطقوس عناية تُجدّد الروح.', dur: 0.16 },
    { at: 0.85, kicker: '٠٦ — الختام', title: 'تجربة تُشبهكِ', text: 'كل التفاصيل تحمل بصمة NA BEAUTY — احجزي الآن.', dur: 0.15 }
  ];

  var world = document.getElementById('world');
  var dotsWrap = document.getElementById('dots');
  var loader = document.getElementById('loader');
  var loaderBar = document.querySelector('#loader .loader-bar i');

  // Build single tall scene
  var vh = window.innerHeight;
  var section = document.createElement('section');
  section.id = 'master-wrap';
  section.style.height = '520vh';
  section.style.position = 'relative';
  world.appendChild(section);

  var sticky = document.createElement('div');
  sticky.className = 'master-sticky';
  section.appendChild(sticky);

  var video = document.createElement('video');
  video.id = 'master-video';
  video.muted = true;
  video.playsInline = true;
  video.preload = 'auto';
  video.setAttribute('muted', '');
  video.setAttribute('playsinline', '');
  video.poster = MASTER.poster;
  video.src = MASTER.src;
  sticky.appendChild(video);

  // intro overlay (fades on scroll)
  var intro = document.createElement('div');
  intro.className = 'intro';
  intro.innerHTML = '<p class="tag">صالون نسائي فاخر · NA BEAUTY</p><h1>NA <b>BEAUTY</b></h1><p class="lead">حيث يُولَد الجمال… وجهتكِ الأولى للدلال والأناقة</p><p class="scroll-hint">مرّري للأسفل ↓</p>';
  sticky.appendChild(intro);

  // captions
  var copies = [];
  CHAPTERS.forEach(function (c, i) {
    if (i === 0) return; // intro covers first
    var el = document.createElement('div');
    el.className = 'copy';
    el.innerHTML = '<span class="kicker">' + c.kicker + '</span><h2>' + c.title + '</h2><p>' + c.text + '</p>';
    el.style.opacity = '0';
    sticky.appendChild(el);
    copies.push({ at: c.at, dur: c.dur, el: el });
  });

  // hairline
  var hairline = document.createElement('div');
  hairline.className = 'hairline';
  hairline.innerHTML = '<i></i>';
  sticky.appendChild(hairline);
  var hair = hairline.firstChild;

  // dots
  CHAPTERS.forEach(function (c, i) {
    var b = document.createElement('button');
    b.title = c.title;
    b.addEventListener('click', function () { scrollToProgress(c.at + c.dur / 2); });
    dotsWrap.appendChild(b);
  });
  var dots = Array.from(dotsWrap.children);

  function scrollToProgress(p) {
    var target = section.offsetTop + (section.offsetHeight - vh) * p;
    window.scrollTo({ top: target, behavior: 'smooth' });
  }

  function masterProgress() {
    var rect = section.getBoundingClientRect();
    var total = section.offsetHeight - vh;
    return Math.max(0, Math.min(0.9999, -rect.top / Math.max(1, total)));
  }

  var boot = Date.now();
  var SEEK_THRESHOLD = 0.06;

  function tick() {
    vh = window.innerHeight;
    var p = masterProgress();
    // drive video
    if (video.readyState >= 1 && !video.seeking && video.duration) {
      var t = p * video.duration;
      if (Math.abs(video.currentTime - t) > SEEK_THRESHOLD) {
        try { video.currentTime = t; } catch (e) {}
      }
    }
    if (hair) hair.style.width = (p * 100).toFixed(2) + '%';
    // intro fade
    intro.style.opacity = Math.max(0, 1 - p * 8).toFixed(3);
    intro.style.visibility = p > 0.16 ? 'hidden' : 'visible';
    // captions
    var active = -1;
    for (var i = 0; i < copies.length; i++) {
      var c = copies[i];
      var show = p >= c.at && p < c.at + c.dur;
      c.el.style.opacity = show ? '1' : '0';
      c.el.style.transform = 'translateY(' + (show ? 0 : 26) + 'px)';
      c.el.style.transition = 'opacity .45s ease, transform .45s ease';
      if (show) active = i;
    }
    dots.forEach(function (d, i) { d.classList.toggle('active', i === (active + 1)); });
    if (!QA_ON && active === -1 && p < 0.08) dots[0]?.classList.add('active');

    // QA
    if (QA_ON) {
      if (loader) loader.classList.add('done');
      if (video.readyState >= 2 && !video.seeking) {
        var target = section.offsetTop + (section.offsetHeight - vh) * QA_P;
        if (Math.abs(window.scrollY - target) > 2) {
          window.scrollTo(0, target);
        } else {
          var want = QA_P * (video.duration || MASTER.dur);
          if (Math.abs(video.currentTime - want) < 0.25) document.title = 'QA_READY';
        }
      }
    } else if (loader && !loader.classList.contains('done')) {
      var ready = video.readyState >= 2 || Date.now() - boot > 8000;
      if (ready) loader.classList.add('done');
      else loaderBar.style.width = video.readyState >= 1 ? '70%' : '25%';
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    var p = masterProgress();
    var step = e.key === 'ArrowDown' ? 0.12 : -0.12;
    scrollToProgress(Math.max(0, Math.min(0.99, p + step)));
  });
})();
