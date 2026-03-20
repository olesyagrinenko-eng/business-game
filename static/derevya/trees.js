/* Данные страницы: inline-скрипт вызывает Object.assign(window, { ROUND, ROUND_INTRO, AOV, INITIAL, SCENARIOS }) */
(function () {
  'use strict';

  var ROUND = window.ROUND;
  var ROUND_INTRO = window.ROUND_INTRO;
  var INITIAL = window.INITIAL;
  var SCENARIOS = window.SCENARIOS;
  /**
   * Раунды 3–6: одна топология дерева (фоллбэк, «Общий CPO») и те же ортогональные маршруты стрелок,
   * что настроены для раунда 3: левые «автобусы» Заказы→OPH/DCPO/DC, OPH→Общий CPO, разведение AOV/маржа→DCPO.
   */
  var FULL_TREE = ROUND >= 3;

  document.getElementById('roundNum').textContent = ROUND;
  document.getElementById('roundIntro').textContent = ROUND_INTRO;

  function fmt(x) {
    if (x == null) return '—';
    if (typeof x === 'number' && x === Math.round(x)) return String(Math.round(x));
    return typeof x === 'number' ? x.toLocaleString('ru', { maximumFractionDigits: 2 }) : String(x);
  }
  /** Одинаковый формат дробей: всегда запятая и один знак (3,5) */
  function fmtDec1(x) {
    if (x == null || typeof x !== 'number' || !isFinite(x)) return '—';
    return x.toLocaleString('ru', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  }
  function placeStatus(place) {
    if (place == null) return '';
    if (place <= 4) return 'status-green';
    if (place <= 8) return 'status-yellow';
    return 'status-red';
  }
  function cteStatus(ok) {
    return ok ? 'status-green' : 'status-red';
  }
  /** Как в app.py `_enrich_side_sh_orders_oph`: если SH нет в сценарии — исходные часы смены из INITIAL, не 300+600*коэф. */
  function defaultSh(teamNum) {
    var t = INITIAL['team' + teamNum];
    if (t && t.SH != null && t.SH !== '') return Number(t.SH);
    return 300;
  }
  function pctChange(prev, curr) {
    if (prev == null || prev === 0 || curr == null) return null;
    return Math.round(((curr - prev) / prev) * 100);
  }
  function pctStr(pct) {
    if (pct == null) return '—';
    var n = typeof pct === 'number' ? pct : parseFloat(pct);
    if (!isFinite(n)) return '—';
    var r = Math.round(n);
    var s = Math.abs(n - r) < 0.001 ? String(r) : String(n).replace('.', ',');
    return (n > 0 ? '+' : '') + s + '%';
  }
  function pctPlain(pct) {
    if (pct == null) return '—';
    var n = typeof pct === 'number' ? pct : parseFloat(pct);
    if (!isFinite(n)) return '—';
    return Math.round(n) + '%';
  }
  /** Сурж: число из JSON = уже проценты (0, 15, 100); строки нет/да — устаревший формат */
  function fmtSurgePct(x) {
    if (x == null) return '—';
    if (typeof x === 'string') {
      if (x === 'нет') return '0%';
      if (x === 'да') return '—';
      var ps = parseFloat(String(x).replace(',', '.'));
      if (isFinite(ps)) return fmtSurgePct(ps);
      return x;
    }
    var n = Number(x);
    if (!isFinite(n)) return '—';
    if (n === 0) return '0%';
    if (n > 0 && n < 1) return pctPlain(Math.round(n * 100));
    if (n >= 1 && n <= 100) {
      if (Math.abs(n - Math.round(n)) < 1e-6) return pctPlain(Math.round(n));
      return n.toLocaleString('ru', { maximumFractionDigits: 1, minimumFractionDigits: 0 }) + '%';
    }
    return fmt(n) + '%';
  }
  /** Доля фоллбэка из Excel: 0–1 как доля, иначе как проценты (5 → 5%); 0 — валидное значение */
  function fmtFallbackShare(x) {
    if (x == null || typeof x !== 'number' || !isFinite(x)) return '—';
    if (x >= 0 && x <= 1) return pctPlain(x * 100);
    return fmt(x) + '%';
  }
  /** Списания в процентах: доля 0…1 из Excel → «2%»; уже в % (5) → «5%»; −1…0 — доля отрицательная */
  function fmtWriteoffsPct(x) {
    if (x == null || typeof x !== 'number' || !isFinite(x)) return '—';
    if (x >= 0 && x <= 1) return pctPlain(x * 100);
    if (x < 0 && x >= -1) return pctPlain(x * 100);
    return fmt(x) + '%';
  }
  /** Роялти в процентах для отображения (число в JSON — как в СВОД: 5 или 0,05) */
  function fmtRoyaltyPct(x) {
    if (x == null || typeof x !== 'number' || !isFinite(x)) return '—';
    if (x >= 0 && x <= 1) return pctPlain(Math.round(x * 100));
    return pctPlain(Math.round(x));
  }
  function set(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
  }
  function setDot(id, status) {
    var el = document.getElementById(id);
    if (!el) return;
    el.className = 'dot ' + (status || '');
  }
  function setPlashka(id, status) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('status-green', 'status-yellow', 'status-red');
    var s = (status || '').replace('status-', '');
    if (s === 'green' || s === 'yellow' || s === 'red') el.classList.add('status-' + s);
  }
  function metricStatus(improved) {
    if (improved === true) return 'green';
    if (improved === false) return 'red';
    return 'yellow';
  }
  function numericOrNull(v) {
    if (v == null) return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }
  /**
   * Ком. маржа текущей недели (доля 0–1), если в сценарии нет поля margin (слоты 38–39 СВОД).
   * Иначе «текущая» копировалась с «прошлой» и на раунде 6 получалось 33% / 33%.
   * Оценка по DCPO и среднему чеку текущей недели (как в AOV: из сценария или прошлой недели);
   * коэффициенты подогнаны под исходные метрики (33%) и лист «Деревья» (−10%/0 → ~29%).
   * Явное scenario.margin в JSON имеет приоритет.
   */
  function inferredMarginFraction(prev, curr) {
    if (ROUND < 5 || !curr) return null;
    var ac = numericOrNull(
      curr.avg_check != null && curr.avg_check !== '' ? curr.avg_check : prev.avg_check
    );
    var dcpo = numericOrNull(curr.DCPO);
    if (ac == null || ac === 0 || dcpo == null) return null;
    var k = 0.225;
    var b = 0.278;
    var m = k * (dcpo / ac) + b;
    if (!isFinite(m)) return null;
    if (m > 0.999) m = 0.999;
    if (m < -0.999) m = -0.999;
    return m;
  }
  function fillTeam(team, prev, curr, shCurr) {
    var prefix = team === 1 ? 't1' : 't2';
    var ordersCurr = (curr && curr.orders != null) ? curr.orders : (curr && curr.DCPO ? curr.DC / curr.DCPO : null);
    /* Как app.py: заказы из DC/DCPO — целые; OPH = round(заказы/SH, 1) */
    if (ordersCurr != null && curr && curr.orders == null) ordersCurr = Math.round(Number(ordersCurr));
    if (curr && curr.SH != null) shCurr = curr.SH;
    var ophCurr = (curr && curr.OPH != null) ? curr.OPH : (shCurr > 0 && ordersCurr != null ? Math.round((Number(ordersCurr) / shCurr) * 10) / 10 : null);
    /* Текущий AOV: только из сценария или «как на прошлой неделе»; глобальный AOV раунда не подставляем (ломает команды с разным чеком). */
    var aovCurr = (curr && curr.avg_check != null) ? curr.avg_check : prev.avg_check;
    var ordPrev = prev.orders, shPrev = prev.SH;
    var ordPct = pctChange(ordPrev, ordersCurr); var ordOk = ordPct == null ? null : (ordPct > 0 ? true : ordPct < 0 ? false : null);
    var shPct = pctChange(shPrev, shCurr); var shOk = shPct == null ? null : (shPct > 0 ? true : shPct < 0 ? false : null);
    var ophPct = pctChange(prev.OPH, ophCurr); var ophOk = ophPct == null ? null : (ophPct > 0 ? true : ophPct < 0 ? false : null);
    var ctePct = curr ? pctChange(prev.CTE, curr.CTE) : null; var cteOk = curr ? curr.CTE_in_target : null;
    var cteAtTarget = curr && prev && curr.CTE != null && prev.CTE != null && Math.abs(Number(curr.CTE) - Number(prev.CTE)) < 0.01;
    var cteTraffic = cteAtTarget ? 'yellow' : metricStatus(cteOk);
    var aovPct = pctChange(prev.avg_check, aovCurr); var aovOk = aovPct == null ? null : (aovPct === 0 ? null : aovPct > 0 ? true : false);
    var cpoPct = curr ? pctChange(prev.CPO, curr.CPO) : null; var cpoOk = cpoPct == null ? null : (cpoPct < 0 ? true : cpoPct > 0 ? false : null);
    var dcpoPct = curr ? pctChange(prev.DCPO, curr.DCPO) : null; var dcpoOk = dcpoPct == null ? null : (dcpoPct > 0 ? true : dcpoPct < 0 ? false : null);
    var dcPct = curr ? pctChange(prev.DC, curr.DC) : null; var dcOk = dcPct == null ? null : (dcPct > 0 ? true : dcPct < 0 ? false : null);
    set(prefix + 'SH_prev', fmt(prev.SH)); set(prefix + 'SH_curr', fmt(shCurr)); setDot(prefix + 'SH_dot', metricStatus(shOk)); set(prefix + 'SH_pct', pctStr(shPct)); setPlashka('p' + team + '_sh', 'status-' + metricStatus(shOk));
    set(prefix + 'Orders_prev', fmt(prev.orders)); set(prefix + 'Orders_curr', ordersCurr != null ? fmt(Math.round(ordersCurr)) : '—'); setDot(prefix + 'Orders_dot', metricStatus(ordOk)); set(prefix + 'Orders_pct', pctStr(ordPct)); setPlashka('p' + team + '_orders', 'status-' + metricStatus(ordOk));
    set(prefix + 'OPH_prev', fmtDec1(prev.OPH)); set(prefix + 'OPH_curr', ophCurr != null ? fmtDec1(Number(ophCurr)) : '—'); setDot(prefix + 'OPH_dot', metricStatus(ophOk)); set(prefix + 'OPH_pct', pctStr(ophPct)); setPlashka('p' + team + '_oph', 'status-' + metricStatus(ophOk));
    set(prefix + 'CTE_prev', prev.CTE != null ? fmtDec1(Number(prev.CTE)) : '—'); set(prefix + 'CTE_curr', curr ? fmtDec1(Number(curr.CTE)) : '—'); setDot(prefix + 'CTE_dot', cteTraffic); set(prefix + 'CTE_pct', pctStr(ctePct)); setPlashka('p' + team + '_cte', 'status-' + cteTraffic);
    set(prefix + 'AOV_prev', fmt(prev.avg_check)); set(prefix + 'AOV_curr', fmt(aovCurr)); setDot(prefix + 'AOV_dot', metricStatus(aovOk)); set(prefix + 'AOV_pct', pctStr(aovPct)); setPlashka('p' + team + '_aov', 'status-' + metricStatus(aovOk));
    var woPrev = prev.writeoffs;
    /* null в JSON → показываем 0 (иначе прочерк при writeoffs: null) */
    var woCurr = curr == null ? null : (curr.writeoffs != null ? curr.writeoffs : 0);
    var woPct = pctChange(woPrev, woCurr);
    var woOk = woPct == null ? null : (woPct < 0 ? true : woPct > 0 ? false : null);
    set(prefix + 'Writeoffs_prev', woPrev != null && woPrev !== undefined ? fmtWriteoffsPct(Number(woPrev)) : '—');
    set(prefix + 'Writeoffs_curr', woCurr != null && woCurr !== undefined ? fmtWriteoffsPct(Number(woCurr)) : '—');
    setDot(prefix + 'Writeoffs_dot', woOk == null ? 'yellow' : metricStatus(woOk));
    set(prefix + 'Writeoffs_pct', pctStr(woPct));
    setPlashka('p' + team + '_writeoffs', woOk == null ? 'status-yellow' : 'status-' + metricStatus(woOk));
    var marginPrev = prev.margin != null && prev.margin !== '' ? Number(prev.margin) : null;
    var marginCurr;
    if (curr && curr.margin != null && curr.margin !== '') {
      marginCurr = Number(curr.margin);
    } else if (curr && ROUND >= 5) {
      marginCurr = inferredMarginFraction(prev, curr);
    }
    if (marginCurr == null) marginCurr = marginPrev;
    var marginPct = pctChange(marginPrev, marginCurr);
    var marginOk = marginPct == null ? null : (marginPct > 0 ? true : marginPct < 0 ? false : null);
    set(prefix + 'Margin_prev', marginPrev != null ? pctPlain(marginPrev * 100) : '—');
    set(prefix + 'Margin_curr', marginCurr != null ? pctPlain(marginCurr * 100) : '—');
    setDot(prefix + 'Margin_dot', marginOk == null ? 'yellow' : metricStatus(marginOk));
    set(prefix + 'Margin_pct', pctStr(marginPct));
    setPlashka('p' + team + '_margin', marginOk == null ? 'status-yellow' : 'status-' + metricStatus(marginOk));
    set(prefix + 'DCPO_prev', String(Math.round(prev.DCPO))); set(prefix + 'DCPO_curr', curr ? String(Math.round(curr.DCPO)) : '—');
    var dcpoTraffic = (curr && curr.CTE_in_target === false) ? 'red' : metricStatus(dcpoOk);
    setDot(prefix + 'DCPO_dot', 'status-' + dcpoTraffic); set(prefix + 'DCPO_pct', pctStr(dcpoPct)); setPlashka('p' + team + '_dcpo', 'status-' + dcpoTraffic);
    set(prefix + 'DC_prev', fmt(prev.DC)); set(prefix + 'DC_curr', curr ? fmt(curr.DC) : '—'); setDot(prefix + 'DC_dot', metricStatus(dcOk)); set(prefix + 'DC_pct', pctStr(dcPct)); setPlashka('p' + team + '_dc', 'status-' + metricStatus(dcOk));
    set(prefix + 'CPO_prev', fmt(prev.CPO)); set(prefix + 'CPO_curr', curr ? String(Math.round(curr.CPO)) : '—'); setDot(prefix + 'CPO_dot', metricStatus(cpoOk)); set(prefix + 'CPO_pct', pctStr(cpoPct)); setPlashka('p' + team + '_cpo', 'status-' + metricStatus(cpoOk));
  }
  function scenarioKey(c1, c2) {
    return (c1 === 0 ? '0.0' : String(c1)) + '_' + (c2 === 0 ? '0.0' : String(c2));
  }

  /** Больше механик в mid-stack — больше min-height (для FULL_TREE в т.ч. вертикали левых автобусов Заказы→…) */
  function applyDiagramMinHeight() {
    var h = 320;
    if (ROUND >= 6) h = 620;
    else if (ROUND >= 5) h = 500;
    else if (ROUND >= 4) h = 420;
    else if (ROUND >= 2) h = 360;
    ['diag1', 'diag2'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.minHeight = h + 'px';
    });
  }

  function update() {
    var c1 = parseFloat(document.getElementById('coef1').value);
    var c2 = parseFloat(document.getElementById('coef2').value);
    var key = scenarioKey(c1, c2);
    var sc = SCENARIOS[key] || SCENARIOS[String(c1) + '_' + String(c2)];
    var coefLabels = { '-0.1': '-10%', '0': '0%', '0.2': '+20%', '0.4': '+40%' };
    document.getElementById('vCoef1').textContent = coefLabels[String(c1)] || c1;
    document.getElementById('vCoef2').textContent = coefLabels[String(c2)] || c2;
    var diffPct = Math.round((c2 - c1) * 100);
    document.getElementById('vDiff').textContent = (diffPct > 0 ? '+' : '') + diffPct + '%';
    var prev1 = INITIAL.team1, prev2 = INITIAL.team2;
    fillTeam(1, prev1, sc ? sc.team1 : null, defaultSh(1));
    fillTeam(2, prev2, sc ? sc.team2 : null, defaultSh(2));
    fillMechanics(1, sc);
    fillMechanics(2, sc);
    applyDiagramMinHeight();
    requestAnimationFrame(function () { requestAnimationFrame(redrawAllArrows); });
  }
  /** Плашки механик: сурж из слотов сценария (%). «Вывоз» не на листе «Деревья» — в диаграмме не показываем. */
  function fillMechanics(teamNum, sc) {
    var prefix = teamNum === 1 ? 't1' : 't2';
    var pid = teamNum === 1 ? 'p1' : 'p2';
    var teamData = sc && (teamNum === 1 ? sc.team1 : sc.team2);
    function vis(id, on) {
      var el = document.getElementById(id);
      if (el) el.style.display = on ? '' : 'none';
    }
    vis(pid + '_surge', ROUND >= 2);
    vis(pid + '_delivery', false);
    vis(pid + '_stock', false);
    vis(pid + '_writeoffs', ROUND >= 5);
    vis(pid + '_fallback', FULL_TREE);
    vis(pid + '_cpo_total', FULL_TREE);
    vis(pid + '_royalty', ROUND >= 6);
    if (ROUND >= 2) {
      var prevSurgeNum = teamData && teamData.surge_prev != null ? numericOrNull(teamData.surge_prev) : (ROUND === 2 ? 0 : null);
      var currSurgeNum = teamData && teamData.surge_curr != null ? numericOrNull(teamData.surge_curr) : null;
      var sp = prevSurgeNum != null ? fmtSurgePct(prevSurgeNum) : '—';
      var scurr = currSurgeNum != null ? fmtSurgePct(currSurgeNum) : '—';
      var surgeOk = null;
      if (prevSurgeNum != null && currSurgeNum != null) {
        // Для суржа рост = ухудшение (красный), снижение = улучшение (зеленый)
        if (currSurgeNum > prevSurgeNum) surgeOk = false;
        else if (currSurgeNum < prevSurgeNum) surgeOk = true;
      }
      set(prefix + 'Surge_prev', sp);
      set(prefix + 'Surge_curr', scurr);
      setDot(prefix + 'Surge_dot', metricStatus(surgeOk));
      setPlashka(pid + '_surge', 'status-' + metricStatus(surgeOk));
    }
    if (ROUND >= 6) {
      var roy = document.querySelector('#' + pid + '_royalty .name');
      if (roy) roy.textContent = 'Роялти, %';
      var initR = INITIAL['team' + teamNum];
      /* Прошлая неделя — из INITIAL; текущая — из сценария (как фоллбэк/CPO total) */
      var rpv = numericOrNull(initR && initR.royalty_prev != null ? initR.royalty_prev : 0);
      var rcv = numericOrNull(teamData && teamData.royalty_curr != null ? teamData.royalty_curr : 0);
      set(prefix + 'Royalty_prev', rpv != null ? fmtRoyaltyPct(rpv) : '—');
      set(prefix + 'Royalty_curr', rcv != null ? fmtRoyaltyPct(rcv) : '—');
      var royOk = null;
      if (rpv != null && rcv != null) {
        if (rcv > rpv) royOk = false;
        else if (rcv < rpv) royOk = true;
      }
      setDot(prefix + 'Royalty_dot', royOk == null ? 'yellow' : metricStatus(royOk));
      setPlashka(pid + '_royalty', royOk == null ? 'status-yellow' : 'status-' + metricStatus(royOk));
    }
    if (FULL_TREE) {
      var init = INITIAL['team' + teamNum];
      var fbPrev = init && init.fallback_share != null ? Number(init.fallback_share) : null;
      var ctotPrev = init && init.cpo_total != null ? Number(init.cpo_total) : null;
      set(prefix + 'Fallback_prev', fbPrev != null ? fmtFallbackShare(fbPrev) : '—');
      set(prefix + 'CpoTotal_prev', ctotPrev != null ? fmt(ctotPrev) : '—');
      set(prefix + 'Fallback_curr', teamData && teamData.fallback_share != null ? fmtFallbackShare(Number(teamData.fallback_share)) : '—');
      set(prefix + 'CpoTotal_curr', teamData && teamData.cpo_total != null ? fmt(Number(teamData.cpo_total)) : '—');
    }
  }
  function getArrowLinks() {
    /* Точки крепления и route — см. drawArrows; для FULL_TREE (раунды 3–6) маршруты как в раунде 3. */
    var L = [
      { from: 'orders', to: 'oph', fromSide: 'bottom', toSide: 'left', route: 'orders-oph-left' },
      { from: 'orders', to: 'dcpo', fromSide: 'bottom', toSide: 'left', route: 'orders-dcpo-leftbus' },
      { from: 'orders', to: 'dc', fromSide: 'bottom', toSide: 'left', route: 'orders-dc-leftbus' },
      { from: 'aov', to: 'dcpo', fromSide: 'right', toSide: 'leftUpper', route: 'aov-dcpo-h' },
      { from: 'margin', to: 'dcpo', fromSide: 'right', toSide: 'leftLower', route: 'margin-dcpo-edge' },
      { from: 'dcpo', to: 'dc', fromSide: 'bottom', toSide: 'top', route: 'stack-v' }
    ];
    if (FULL_TREE) {
      L.splice(3, 0, { from: 'oph', to: 'cpo_total', fromSide: 'right', toSide: 'left', route: 'oph-cpo-total-h' });
    } else {
      L.splice(3, 0, { from: 'oph', to: 'cpo', fromSide: 'right', toSide: 'left', route: 'oph-cpo-h' });
    }
    if (ROUND <= 2) {
      L.push({ from: 'cpo', to: 'dcpo', fromSide: 'bottom', toSide: 'top', route: 'stack-v' });
    }
    if (ROUND >= 2) {
      L.push({ from: 'sh', to: 'orders', fromSide: 'left', toSide: 'right', route: 'sh-orders-h' });
      L.push({ from: 'surge', to: 'aov', fromSide: 'bottom', toSide: 'top', route: 'stack-v' });
    }
    if (FULL_TREE) {
      L.push({ from: 'oph', to: 'fallback', fromSide: 'right', toSide: 'left', route: 'oph-fallback-h' });
      L.push({ from: 'cpo', to: 'fallback', fromSide: 'bottom', toSide: 'top', route: 'stack-v' });
      L.push({ from: 'fallback', to: 'cpo_total', fromSide: 'bottom', toSide: 'top', route: 'stack-v' });
      L.push({ from: 'cpo_total', to: 'dcpo', fromSide: 'bottom', toSide: 'top', route: 'cpo-total-dcpo-v' });
      L.push({ from: 'cpo_total', to: 'dc', fromSide: 'right', toSide: 'left', route: 'col3' });
    }
    if (ROUND >= 5) {
      L.push({ from: 'writeoffs', to: 'margin', fromSide: 'right', toSide: 'left', route: 'elbow' });
    }
    if (ROUND >= 6) {
      L.push({ from: 'royalty', to: 'margin', fromSide: 'bottom', toSide: 'top', route: 'stack-v' });
    }
    return L;
  }
  /** Минимум отступа линии от границы блока / края коридора (px) */
  var AR_PAD = 10;
  function pointOnRect(r, side, refPoint) {
    var cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
    var pad = 0;
    if (side === 'topUnderStart' && refPoint) return { x: refPoint.x, y: r.top + pad };
    if (side === 'left') return { x: r.left + pad, y: cy };
    if (side === 'right') return { x: r.right - pad, y: cy };
    if (side === 'top') return { x: cx, y: r.top + pad };
    if (side === 'bottom') return { x: cx, y: r.bottom - pad };
    if (side === 'leftBottom') return { x: r.left + pad, y: r.bottom - pad };
    /* Верхняя / нижняя часть левого края (разведение стрелок к DCPO) */
    if (side === 'leftUpper') {
      var hu = r.bottom - r.top;
      return { x: r.left + pad, y: r.top + pad + hu * 0.22 };
    }
    if (side === 'leftLower') {
      var hl = r.bottom - r.top;
      return { x: r.left + pad, y: r.bottom - pad - hl * 0.22 };
    }
    return { x: cx, y: cy };
  }
  function getMaxPlashkaBottomRel(diag, dr) {
    var maxB = 0;
    var pls = diag.querySelectorAll('.plashka');
    for (var i = 0; i < pls.length; i++) {
      var el = pls[i];
      if (el.offsetParent === null) continue;
      var r = el.getBoundingClientRect();
      var bot = r.bottom - dr.top;
      if (isFinite(bot) && bot > maxB) maxB = bot;
    }
    return maxB;
  }

  /** Реальные границы плашек mid (контейнер .mid-stack может быть уже детей из-за flex) */
  function midPlashkaExtents(mid, dr) {
    var minL = Infinity, maxR = -Infinity, minT = Infinity, maxB = -Infinity;
    var pls = mid.querySelectorAll('.plashka');
    var n = 0;
    for (var i = 0; i < pls.length; i++) {
      if (pls[i].offsetParent === null) continue;
      n++;
      var r = pls[i].getBoundingClientRect();
      minL = Math.min(minL, r.left - dr.left);
      maxR = Math.max(maxR, r.right - dr.left);
      minT = Math.min(minT, r.top - dr.top);
      maxB = Math.max(maxB, r.bottom - dr.top);
    }
    var box = mid.getBoundingClientRect();
    if (n === 0) {
      return { mL: box.left - dr.left, mR: box.right - dr.left, midTop: box.top - dr.top, midBottom: box.bottom - dr.top };
    }
    return { mL: minL, mR: maxR, midTop: minT, midBottom: maxB };
  }

  /** Коридоры: g12 строго слева от плашек, g23 у левого края CPO (не середина зазора — стабильнее) */
  function getColumnGutters(diag, dr) {
    var orders = diag.querySelector('.col-left');
    var mid = diag.querySelector('.mid-stack');
    var stack = diag.querySelector('.cpo-stack');
    var cpo = stack ? stack.querySelector('.block-cpo') : diag.querySelector('.block-cpo');
    if (!orders || !mid || !stack || !cpo) return null;
    var o = orders.getBoundingClientRect();
    var c = cpo.getBoundingClientRect();
    var stackBox = stack.getBoundingClientRect();
    var ext = midPlashkaExtents(mid, dr);
    var mL = ext.mL;
    var mR = ext.mR;
    var oR = o.right - dr.left;
    var cL = c.left - dr.left;
    var cR = c.right - dr.left;
    var sL = stackBox.left - dr.left;
    var sR = stackBox.right - dr.left;
    var gStack = (sL + sR) / 2;
    function clampGap(x, lo, hi, margin) {
      margin = margin == null ? AR_PAD : margin;
      if (hi - lo < margin * 2 + 2) return (lo + hi) / 2;
      return Math.max(lo + margin, Math.min(x, hi - margin));
    }
    var g12ideal = (oR + mL) / 2;
    var g12 = clampGap(g12ideal, oR, mL, AR_PAD);
    g12 = Math.min(g12, mL - AR_PAD);
    g12 = Math.max(g12, oR + AR_PAD);
    var g23 = cL - 14;
    if (g23 < mR + AR_PAD + 2) g23 = mR + AR_PAD + 8;
    if (g23 > cL - AR_PAD) g23 = Math.max(mR + AR_PAD, (mR + cL) / 2);
    var g34 = clampGap((cR + sR) / 2, cR, sR, AR_PAD);
    var oL = o.left - dr.left;
    /* Левый автобус (Заказы→OPH и др.) */
    var gLeft = Math.max(AR_PAD + 4, oL - 16);
    /* Правое поле: вертикаль справа от cpo-stack; горизонталь «над» SH и CPO до фоллбэка */
    var cTop = c.top - dr.top;
    var yTopBand = Math.min(ext.midTop, cTop) - AR_PAD - 10;
    if (!isFinite(yTopBand) || yTopBand < AR_PAD + 4) yTopBand = AR_PAD + 8;
    var gRight = Math.min(dr.width - AR_PAD - 4, sR + 22);
    return {
      g12: g12, g23: g23, g34: g34, gStack: gStack, gLeft: gLeft, gRight: gRight, yTopBand: yTopBand,
      oBottom: o.bottom - dr.top, mR: mR, mL: mL, midTop: ext.midTop, midBottom: ext.midBottom
    };
  }
  function linkColumn(nodeId) {
    if (nodeId === 'orders') return 1;
    if (nodeId === 'cpo' || nodeId === 'fallback' || nodeId === 'cpo_total' || nodeId === 'dcpo' || nodeId === 'dc') return 3;
    return 2;
  }
  /** Разнесение параллельных линий в вертикальных коридорах (смещение от базовой линии, px) */
  var laneNext = { g12: 0, g23: 0, g34: 0 };
  var LANE_STEP = 5;
  var LANE_MAX = 6;
  function laneOffset(gutterId) {
    var n = laneNext[gutterId]++;
    var k = n % LANE_MAX;
    return (k - (LANE_MAX - 1) / 2) * LANE_STEP;
  }
  function resetLanes() {
    laneNext.g12 = 0;
    laneNext.g23 = 0;
    laneNext.g34 = 0;
  }

  /** Mid → Заказы: ортогонально по коридору g12 */
  function pathMidLeftToOrdersRight(p1, p2, g12, midTop) {
    var yEsc = Math.max(AR_PAD, (isFinite(midTop) ? midTop : p1.y) - AR_PAD - 4);
    return 'M' + p1.x + ',' + p1.y + ' L' + p1.x + ',' + yEsc + ' L' + g12 + ',' + yEsc + ' L' + g12 + ',' + p2.y + ' L' + p2.x + ',' + p2.y;
  }

  /** Вертикаль в одной колонке: общая ось X по центрам блоков, без диагоналей */
  function pathStackVerticalStrictBetween(fromRect, toRect, stub) {
    stub = stub || AR_PAD;
    var xc = ((fromRect.left + fromRect.right) + (toRect.left + toRect.right)) / 4;
    var y1 = fromRect.bottom - stub;
    var y2 = toRect.top + stub;
    return 'M' + xc + ',' + y1 + ' L' + xc + ',' + y2;
  }

  /** SH → Заказы: одна горизонталь на общей высоте (между блоками, без петель) */
  function pathSHtoOrdersHorizontal(fromRect, toRect) {
    var cy = ((fromRect.top + fromRect.bottom) + (toRect.top + toRect.bottom)) / 4;
    var x1 = fromRect.left;
    var x2 = toRect.right;
    return 'M' + x1 + ',' + cy + ' L' + x2 + ',' + cy;
  }

  /** Заказы → OPH / DCPO / DC: низ заказов → влево на «автобус» xBus → вниз → в цель слева (xBus_OPH правее xBus_DCPO правее xBus_DC) */
  function pathOrdersBottomLeftBus(p1, p2, xBus, stub) {
    stub = stub || AR_PAD;
    var xin = p2.x - stub;
    return 'M' + p1.x + ',' + p1.y + ' L' + xBus + ',' + p1.y + ' L' + xBus + ',' + p2.y + ' L' + xin + ',' + p2.y + ' L' + p2.x + ',' + p2.y;
  }

  /** Горизонталь на y пересекает осью X отрезок [xl, xr] прямоугольник rect */
  function horizontalHitsRect(y, xl, xr, rect) {
    if (!rect || !isFinite(y)) return false;
    if (y < rect.top || y > rect.bottom) return false;
    var lo = Math.min(xl, xr);
    var hi = Math.max(xl, xr);
    return hi > rect.left && lo < rect.right;
  }

  /** Заказы → DCPO: как left bus, но горизонталь к левому краю DCPO не режет AOV — сначала ниже AOV */
  function pathOrdersDcpoLeftBusAvoidAov(p1, p2, xBus, aovRect, stub) {
    stub = stub || AR_PAD;
    var xin = p2.x - stub;
    if (!aovRect || !horizontalHitsRect(p2.y, xBus, xin, aovRect)) {
      return pathOrdersBottomLeftBus(p1, p2, xBus, stub);
    }
    var yDown = aovRect.bottom + stub;
    if (yDown < p1.y) yDown = p1.y + stub;
    return 'M' + p1.x + ',' + p1.y +
      ' L' + xBus + ',' + p1.y +
      ' L' + xBus + ',' + yDown +
      ' L' + xin + ',' + yDown +
      ' L' + xin + ',' + p2.y +
      ' L' + p2.x + ',' + p2.y;
  }

  /** Заказы → DC: левее автобуса DCPO; сначала ниже AOV и DCPO, затем вправо и вверх к левому краю DC */
  function pathOrdersDcLeftBusAvoidMid(p1, p2, xBus, aovRect, dcpoRect, stub) {
    stub = stub || AR_PAD;
    var xin = p2.x - stub;
    if (!aovRect && !dcpoRect) return pathOrdersBottomLeftBus(p1, p2, xBus, stub);
    var yLow = p2.y;
    if (aovRect) yLow = Math.max(yLow, aovRect.bottom + stub);
    if (dcpoRect) yLow = Math.max(yLow, dcpoRect.bottom + stub);
    if (yLow < p1.y) yLow = p1.y + stub;
    return 'M' + p1.x + ',' + p1.y +
      ' L' + xBus + ',' + p1.y +
      ' L' + xBus + ',' + yLow +
      ' L' + xin + ',' + yLow +
      ' L' + xin + ',' + p2.y +
      ' L' + p2.x + ',' + p2.y;
  }

  /** AOV → DCPO: к верхней части левого края DCPO (сначала по вертикали у правого края AOV, затем горизонталь); p2 = leftUpper */
  function pathAovToDcpoUpper(fromRect, p2, stub) {
    stub = stub || AR_PAD;
    var x1 = fromRect.right;
    var y1 = (fromRect.top + fromRect.bottom) / 2;
    return 'M' + x1 + ',' + y1 + ' L' + x1 + ',' + p2.y + ' L' + (p2.x - stub) + ',' + p2.y + ' L' + p2.x + ',' + p2.y;
  }

  /** Коридор между OPH и CTE — одна горизонталь OPH → Общий CPO */
  function yCorridorOphCte(fromRect, dr, cteEl) {
    var ophBtm = fromRect.bottom;
    var cteTop = cteEl && cteEl.offsetParent !== null
      ? (cteEl.getBoundingClientRect().top - dr.top)
      : ophBtm + 28;
    var y = (ophBtm + cteTop) / 2;
    return Math.max(ophBtm + 3, Math.min(cteTop - 3, y));
  }

  /** OPH → Доля фоллбэка: ниже полосы OPH–CTE, чтобы не дублировать линию к Общему CPO */
  function yCorridorOphToFallback(ophRect, dr, cteEl, aovEl) {
    var cteB = cteEl && cteEl.offsetParent !== null
      ? (cteEl.getBoundingClientRect().bottom - dr.top)
      : ophRect.bottom + 24;
    var aovT = aovEl && aovEl.offsetParent !== null
      ? (aovEl.getBoundingClientRect().top - dr.top)
      : cteB + 48;
    var y = (cteB + aovT) / 2;
    return Math.max(cteB + AR_PAD, Math.min(aovT - AR_PAD, y));
  }

  /** Одна горизонталь (коридор между строками или к col3) */
  function pathHorizontalStraight(p1, p2) {
    return 'M' + p1.x + ',' + p1.y + ' L' + p2.x + ',' + p2.y;
  }

  /**
   * Стрелка строго между точками крепления на плашках (p1, p2 из getBoundingClientRect).
   * Без отдельных «висящих» отрезков в фиксированных коридорах — при смещении плашек линия остаётся с ними.
   */
  function pathAnchoredToPlashkas(p1, p2) {
    var x1 = p1.x, y1 = p1.y, x2 = p2.x, y2 = p2.y;
    if (Math.abs(x1 - x2) < 2 && Math.abs(y1 - y2) < 2) {
      return 'M' + x1 + ',' + y1 + ' L' + x2 + ',' + y2;
    }
    if (Math.abs(x2 - x1) >= Math.abs(y2 - y1)) {
      return 'M' + x1 + ',' + y1 + ' L' + x2 + ',' + y1 + ' L' + x2 + ',' + y2;
    }
    return 'M' + x1 + ',' + y1 + ' L' + x1 + ',' + y2 + ' L' + x2 + ',' + y2;
  }

  /** Правая колонка cpo-stack: обход по внешнему коридору g34 (ортогонально) */
  function pathCol3RightCorridor(p1, p2, xg, stub) {
    stub = stub || AR_PAD;
    var x1 = p1.x, y1 = p1.y, x2 = p2.x, y2 = p2.y;
    var xa = Math.min(x1 + stub, xg - AR_PAD);
    return 'M' + x1 + ',' + y1 + ' L' + xa + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + x2 + ',' + y2;
  }

  /** Одна вертикаль в коридоре xg */
  function pathViaOneGutter(p1, p2, xg, stub) {
    stub = stub || AR_PAD;
    var gap = AR_PAD;
    var x1 = p1.x, y1 = p1.y, x2 = p2.x, y2 = p2.y;
    if (Math.abs(x1 - x2) < 5 && Math.abs(y1 - y2) < 5) return 'M' + x1 + ',' + y1 + ' L' + x2 + ',' + y2;
    if (xg >= Math.max(x1, x2) - 0.5) {
      var xa = Math.min(x1 + stub, xg - gap);
      return 'M' + x1 + ',' + y1 + ' L' + xa + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + x2 + ',' + y2;
    }
    if (xg <= Math.min(x1, x2) + 0.5) {
      var xaL = Math.max(x1 - stub, xg + gap);
      return 'M' + x1 + ',' + y1 + ' L' + xaL + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + x2 + ',' + y2;
    }
    if (x2 > x1) {
      var xb = Math.min(x1 + stub, xg - gap);
      var xc = Math.max(x2 - stub, xg + gap);
      return 'M' + x1 + ',' + y1 + ' L' + xb + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + xc + ',' + y2 + ' L' + x2 + ',' + y2;
    }
    var xb2 = Math.max(x1 - stub, xg + gap);
    var xc2 = Math.min(x2 + stub, xg - gap);
    return 'M' + x1 + ',' + y1 + ' L' + xb2 + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + xc2 + ',' + y2 + ' L' + x2 + ',' + y2;
  }

  /** Ком.маржа → DCPO: вправо в коридор g23 (между mid и CPO), по вертикали к leftLower DCPO */
  function pathMarginToDcpoViaG23(p1, p2, g23, mR, stub) {
    stub = stub || AR_PAD;
    var xG = (isFinite(g23) && g23 > mR + stub * 2) ? g23 : (mR + stub + 6);
    xG = Math.max(xG, mR + stub + 2);
    return 'M' + p1.x + ',' + p1.y + ' L' + xG + ',' + p1.y + ' L' + xG + ',' + p2.y + ' L' + p2.x + ',' + p2.y;
  }

  /** Колонка 1 -> 3: коридоры g12 и g23, полоса над/под mid */
  function pathCol1to3OutsideMid(p1, p2, g12, g23, midTop, midBottom, drH) {
    var pad = AR_PAD + 4;
    var yAbove = Math.max(AR_PAD, (isFinite(midTop) ? midTop : p1.y) - pad);
    var yBelow = Math.min(drH - AR_PAD, (isFinite(midBottom) ? midBottom : p1.y) + pad);
    function score(y) { return Math.abs(p1.y - y) + Math.abs(p2.y - y); }
    var yLane = score(yAbove) <= score(yBelow) ? yAbove : yBelow;
    return 'M' + p1.x + ',' + p1.y +
      ' L' + g12 + ',' + p1.y +
      ' L' + g12 + ',' + yLane +
      ' L' + g23 + ',' + yLane +
      ' L' + g23 + ',' + p2.y +
      ' L' + p2.x + ',' + p2.y;
  }

  function drawArrows(diagId, arrowsGroupId, markerUrl, prefix) {
    var diag = document.getElementById(diagId);
    var g = document.getElementById(arrowsGroupId);
    var svg = g && g.parentNode;
    if (!diag || !g || !svg) return;
    var dr = diag.getBoundingClientRect();
    /* Если контент высокий, под нижние плашки не помещается «полоса» — расширяем min-height и перерисовываем */
    var maxPlB = getMaxPlashkaBottomRel(diag, dr);
    var needBelow = 26;
    if (maxPlB > 0 && maxPlB + needBelow > dr.height - 8) {
      var needMinH = maxPlB + needBelow + 48;
      var prevMin = parseFloat(diag.style.minHeight) || 0;
      if (needMinH > prevMin) {
        diag.style.minHeight = needMinH + 'px';
        requestAnimationFrame(function () { drawArrows(diagId, arrowsGroupId, markerUrl, prefix); });
        return;
      }
    }
    dr = diag.getBoundingClientRect();
    svg.setAttribute('viewBox', '0 0 ' + dr.width + ' ' + dr.height);
    g.innerHTML = '';
    getArrowLinks().forEach(function (link) {
      var fromEl = document.getElementById(prefix + link.from);
      var toEl = document.getElementById(prefix + link.to);
      if (!fromEl || !toEl) return;
      if (fromEl.offsetParent === null || toEl.offsetParent === null) return;
      var fr = fromEl.getBoundingClientRect();
      var tr = toEl.getBoundingClientRect();
      var toRect = { left: tr.left - dr.left, right: tr.right - dr.left, top: tr.top - dr.top, bottom: tr.bottom - dr.top };
      var fromRect = { left: fr.left - dr.left, right: fr.right - dr.left, top: fr.top - dr.top, bottom: fr.bottom - dr.top };
      var p1 = pointOnRect(fromRect, link.fromSide);
      var p2 = pointOnRect(toRect, link.toSide);
      var d;
      var route = link.route;
      /* Вертикаль в одной колонке и SH→Заказы — только по прямоугольникам блоков; остальное — ортогональ между p1 и p2 */
      if (route === 'stack-v' || route === 'cpo-total-dcpo-v') {
        d = pathStackVerticalStrictBetween(fromRect, toRect, AR_PAD);
      } else if (route === 'sh-orders-h') {
        d = pathSHtoOrdersHorizontal(fromRect, toRect);
      } else {
        d = pathAnchoredToPlashkas(p1, p2);
      }
      var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', d);
      path.setAttribute('class', 'link-path');
      path.setAttribute('fill', 'none');
      path.setAttribute('marker-end', markerUrl);
      g.appendChild(path);
    });
  }
  function redrawAllArrows() {
    drawArrows('diag1', 'arrows1', 'url(#arr1)', 'p1_');
    drawArrows('diag2', 'arrows2', 'url(#arr2)', 'p2_');
  }

  /** Сохранённые смещения плашек (localStorage) — стрелки пересчитываются по getBoundingClientRect */
  function layoutStorageKey(diagId) {
    return 'derevyaDragLayout_r' + ROUND + '_' + diagId;
  }
  function loadLayoutMap(diagId) {
    try {
      var raw = localStorage.getItem(layoutStorageKey(diagId));
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }
  function saveLayoutMap(diagId, map) {
    try {
      localStorage.setItem(layoutStorageKey(diagId), JSON.stringify(map));
    } catch (e) {}
  }
  function setPlashkaOffset(el, tx, ty) {
    el.dataset.tx = String(tx);
    el.dataset.ty = String(ty);
    el.style.transform = 'translate(' + tx + 'px,' + ty + 'px)';
  }
  function applyLayoutToDiagram(diagEl, map) {
    if (!diagEl) return;
    var pls = diagEl.querySelectorAll('.plashka');
    for (var i = 0; i < pls.length; i++) {
      var el = pls[i];
      var id = el.id;
      if (!id) continue;
      var o = map[id];
      if (o && (o.tx || o.ty)) {
        setPlashkaOffset(el, Number(o.tx) || 0, Number(o.ty) || 0);
      } else {
        el.style.transform = '';
        delete el.dataset.tx;
        delete el.dataset.ty;
      }
    }
  }
  function collectLayoutFromDiagram(diagEl) {
    var map = {};
    var pls = diagEl.querySelectorAll('.plashka');
    for (var i = 0; i < pls.length; i++) {
      var el = pls[i];
      if (!el.id) continue;
      var tx = parseFloat(el.dataset.tx || '0', 10) || 0;
      var ty = parseFloat(el.dataset.ty || '0', 10) || 0;
      if (tx !== 0 || ty !== 0) map[el.id] = { tx: tx, ty: ty };
    }
    return map;
  }
  function applySavedLayouts() {
    applyLayoutToDiagram(document.getElementById('diag1'), loadLayoutMap('diag1'));
    applyLayoutToDiagram(document.getElementById('diag2'), loadLayoutMap('diag2'));
  }
  var rafDragArrows = null;
  function redrawAllArrowsThrottledDrag() {
    if (rafDragArrows) cancelAnimationFrame(rafDragArrows);
    rafDragArrows = requestAnimationFrame(function () {
      rafDragArrows = null;
      redrawAllArrows();
    });
  }
  function initDragLayout() {
    var modeChk = document.getElementById('dragLayoutMode');
    var resetBtn = document.getElementById('dragLayoutReset');
    if (!modeChk || !resetBtn) return;

    function setDiagramMode(on) {
      var d1 = document.getElementById('diag1');
      var d2 = document.getElementById('diag2');
      if (d1) d1.classList.toggle('drag-layout-active', on);
      if (d2) d2.classList.toggle('drag-layout-active', on);
    }
    modeChk.addEventListener('change', function () {
      setDiagramMode(modeChk.checked);
    });

    resetBtn.addEventListener('click', function () {
      try {
        localStorage.removeItem(layoutStorageKey('diag1'));
        localStorage.removeItem(layoutStorageKey('diag2'));
      } catch (e) {}
      applyLayoutToDiagram(document.getElementById('diag1'), {});
      applyLayoutToDiagram(document.getElementById('diag2'), {});
      redrawAllArrows();
    });

    var wrap = document.querySelector('.trees-wrapper');
    if (!wrap) return;

    var dragState = null;

    function onMove(e) {
      if (!dragState) return;
      var tx = dragState.origTx + (e.clientX - dragState.startX);
      var ty = dragState.origTy + (e.clientY - dragState.startY);
      setPlashkaOffset(dragState.el, tx, ty);
      redrawAllArrowsThrottledDrag();
    }
    function onUp(e) {
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      document.removeEventListener('pointercancel', onUp);
      if (!dragState) return;
      dragState.el.classList.remove('is-dragging');
      var diag = document.getElementById(dragState.diagId);
      if (diag) saveLayoutMap(dragState.diagId, collectLayoutFromDiagram(diag));
      dragState = null;
      redrawAllArrows();
    }

    wrap.addEventListener('pointerdown', function (e) {
      if (!modeChk.checked) return;
      var pl = e.target.closest('.plashka');
      if (!pl || !pl.id) return;
      var diag = pl.closest('.diagram');
      if (!diag || !diag.id) return;
      if (e.target.closest('a, button, input, select, textarea')) return;
      e.preventDefault();
      dragState = {
        el: pl,
        diagId: diag.id,
        startX: e.clientX,
        startY: e.clientY,
        origTx: parseFloat(pl.dataset.tx || '0', 10) || 0,
        origTy: parseFloat(pl.dataset.ty || '0', 10) || 0
      };
      pl.classList.add('is-dragging');
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', onUp);
      document.addEventListener('pointercancel', onUp);
    });
  }

  applySavedLayouts();
  document.getElementById('coef1').addEventListener('change', update);
  document.getElementById('coef2').addEventListener('change', update);
  update();
  setTimeout(redrawAllArrows, 0);
  window.addEventListener('resize', redrawAllArrows);
  initDragLayout();
})();
