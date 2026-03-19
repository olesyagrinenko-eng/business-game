/* Данные страницы: inline-скрипт вызывает Object.assign(window, { ROUND, ROUND_INTRO, AOV, INITIAL, SCENARIOS }) */
(function () {
  'use strict';

  var ROUND = window.ROUND;
  var ROUND_INTRO = window.ROUND_INTRO;
  var INITIAL = window.INITIAL;
  var SCENARIOS = window.SCENARIOS;

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
  function computeSH(c1, c2) {
    var sh1 = Math.max(0, 300 + 600 * c1);
    var sh2 = Math.max(0, 300 - 600 * c1);
    return { sh1: Math.round(sh1 * 10) / 10, sh2: Math.round(sh2 * 10) / 10 };
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
  /** Доля фоллбэка из Excel: 0–1 как доля, иначе как проценты (5 → 5%) */
  function fmtFallbackShare(x) {
    if (x == null || typeof x !== 'number' || !isFinite(x)) return '—';
    if (x >= 0 && x <= 1) return pctPlain(x * 100);
    return fmt(x) + '%';
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
  function fillTeam(team, prev, curr, shCurr) {
    var prefix = team === 1 ? 't1' : 't2';
    var ordersCurr = (curr && curr.orders != null) ? curr.orders : (curr && curr.DCPO ? curr.DC / curr.DCPO : null);
    if (curr && curr.SH != null) shCurr = curr.SH;
    var ophCurr = (curr && curr.OPH != null) ? curr.OPH : (shCurr > 0 && ordersCurr != null ? ordersCurr / shCurr : null);
    /* Текущий AOV: только из сценария или «как на прошлой неделе»; глобальный AOV раунда не подставляем (ломает команды с разным чеком). */
    var aovCurr = (curr && curr.avg_check != null) ? curr.avg_check : prev.avg_check;
    var ordPrev = prev.orders, shPrev = prev.SH;
    var ordPct = pctChange(ordPrev, ordersCurr); var ordOk = ordPct == null ? null : (ordPct > 0 ? true : ordPct < 0 ? false : null);
    var shPct = pctChange(shPrev, shCurr); var shOk = shPct == null ? null : (shPct > 0 ? true : shPct < 0 ? false : null);
    var ophPct = pctChange(prev.OPH, ophCurr); var ophOk = ophPct == null ? null : (ophPct > 0 ? true : ophPct < 0 ? false : null);
    var ctePct = curr ? pctChange(prev.CTE, curr.CTE) : null; var cteOk = curr ? curr.CTE_in_target : null;
    var aovPct = pctChange(prev.avg_check, aovCurr); var aovOk = aovPct == null ? null : (aovPct === 0 ? null : aovPct > 0 ? true : false);
    var marginPct = 0; var marginOk = null;
    var cpoPct = curr ? pctChange(prev.CPO, curr.CPO) : null; var cpoOk = cpoPct == null ? null : (cpoPct < 0 ? true : cpoPct > 0 ? false : null);
    var dcpoPct = curr ? pctChange(prev.DCPO, curr.DCPO) : null; var dcpoOk = dcpoPct == null ? null : (dcpoPct > 0 ? true : dcpoPct < 0 ? false : null);
    var dcPct = curr ? pctChange(prev.DC, curr.DC) : null; var dcOk = dcPct == null ? null : (dcPct > 0 ? true : dcPct < 0 ? false : null);
    set(prefix + 'SH_prev', fmt(prev.SH)); set(prefix + 'SH_curr', fmt(shCurr)); setDot(prefix + 'SH_dot', metricStatus(shOk)); set(prefix + 'SH_pct', pctStr(shPct)); setPlashka('p' + team + '_sh', 'status-' + metricStatus(shOk));
    set(prefix + 'Orders_prev', fmt(prev.orders)); set(prefix + 'Orders_curr', ordersCurr != null ? fmt(Math.round(ordersCurr)) : '—'); setDot(prefix + 'Orders_dot', metricStatus(ordOk)); set(prefix + 'Orders_pct', pctStr(ordPct)); setPlashka('p' + team + '_orders', 'status-' + metricStatus(ordOk));
    set(prefix + 'OPH_prev', fmtDec1(prev.OPH)); set(prefix + 'OPH_curr', ophCurr != null ? fmtDec1(Number(ophCurr)) : '—'); setDot(prefix + 'OPH_dot', metricStatus(ophOk)); set(prefix + 'OPH_pct', pctStr(ophPct)); setPlashka('p' + team + '_oph', 'status-' + metricStatus(ophOk));
    set(prefix + 'CTE_prev', prev.CTE != null ? fmtDec1(Number(prev.CTE)) : '—'); set(prefix + 'CTE_curr', curr ? fmtDec1(Number(curr.CTE)) : '—'); setDot(prefix + 'CTE_dot', metricStatus(cteOk)); set(prefix + 'CTE_pct', pctStr(ctePct)); setPlashka('p' + team + '_cte', 'status-' + metricStatus(cteOk));
    set(prefix + 'AOV_prev', fmt(prev.avg_check)); set(prefix + 'AOV_curr', fmt(aovCurr)); setDot(prefix + 'AOV_dot', metricStatus(aovOk)); set(prefix + 'AOV_pct', pctStr(aovPct)); setPlashka('p' + team + '_aov', 'status-' + metricStatus(aovOk));
    set(prefix + 'Margin_prev', prev.margin != null ? pctPlain(prev.margin * 100) : '—'); set(prefix + 'Margin_curr', prev.margin != null ? pctPlain(prev.margin * 100) : '—'); setDot(prefix + 'Margin_dot', 'yellow'); set(prefix + 'Margin_pct', '0%'); setPlashka('p' + team + '_margin', 'status-yellow');
    set(prefix + 'DCPO_prev', String(Math.round(prev.DCPO))); set(prefix + 'DCPO_curr', curr ? String(Math.round(curr.DCPO)) : '—');
    var dcpoTraffic = (curr && curr.CTE_in_target === false) ? 'red' : metricStatus(dcpoOk);
    setDot(prefix + 'DCPO_dot', 'status-' + dcpoTraffic); set(prefix + 'DCPO_pct', pctStr(dcpoPct)); setPlashka('p' + team + '_dcpo', 'status-' + dcpoTraffic);
    set(prefix + 'DC_prev', fmt(prev.DC)); set(prefix + 'DC_curr', curr ? fmt(curr.DC) : '—'); setDot(prefix + 'DC_dot', metricStatus(dcOk)); set(prefix + 'DC_pct', pctStr(dcPct)); setPlashka('p' + team + '_dc', 'status-' + metricStatus(dcOk));
    set(prefix + 'CPO_prev', fmt(prev.CPO)); set(prefix + 'CPO_curr', curr ? String(Math.round(curr.CPO)) : '—'); setDot(prefix + 'CPO_dot', metricStatus(cpoOk)); set(prefix + 'CPO_pct', pctStr(cpoPct)); setPlashka('p' + team + '_cpo', 'status-' + metricStatus(cpoOk));
  }
  function scenarioKey(c1, c2) {
    return (c1 === 0 ? '0.0' : String(c1)) + '_' + (c2 === 0 ? '0.0' : String(c2));
  }

  /** Больше механик в mid-stack — больше min-height, чтобы полоса orders→DC не наезжала на блоки */
  function applyDiagramMinHeight() {
    var h = 320;
    if (ROUND >= 6) h = 580;
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
    var sh = computeSH(c1, c2);
    var prev1 = INITIAL.team1, prev2 = INITIAL.team2;
    fillTeam(1, prev1, sc ? sc.team1 : null, sh.sh1);
    fillTeam(2, prev2, sc ? sc.team2 : null, sh.sh2);
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
    /* Раунд 6: упрощённое дерево — без суржа/вывоза/перетока/склада; блок «роялти» без старого подзаголовка */
    if (ROUND >= 6) {
      vis(pid + '_surge', false);
      vis(pid + '_delivery', false);
      vis(pid + '_churn', false);
      vis(pid + '_stock', false);
      vis(pid + '_royalty', true);
      vis(pid + '_fallback', true);
      vis(pid + '_cpo_total', true);
      var roy = document.querySelector('#' + pid + '_royalty .name');
      if (roy) roy.textContent = 'Роялти';
      var royRows = document.querySelectorAll('#' + pid + '_royalty .row');
      for (var ri = 0; ri < royRows.length; ri++) {
        if (royRows[ri].textContent.indexOf('Зависят') >= 0) royRows[ri].style.display = 'none';
      }
      set(prefix + 'Royalty_prev', teamData && teamData.royalty_prev != null ? String(teamData.royalty_prev) : 'нет');
      set(prefix + 'Royalty_curr', teamData && teamData.royalty_curr != null ? String(teamData.royalty_curr) : 'да');
      set(prefix + 'Fallback_curr', teamData && teamData.fallback_share != null ? fmtFallbackShare(Number(teamData.fallback_share)) : '—');
      set(prefix + 'CpoTotal_curr', teamData && teamData.cpo_total != null ? fmt(Number(teamData.cpo_total)) : '—');
      return;
    }
    vis(pid + '_surge', ROUND >= 2);
    vis(pid + '_delivery', false);
    vis(pid + '_churn', ROUND >= 4);
    vis(pid + '_stock', ROUND >= 5);
    vis(pid + '_royalty', false);
    if (ROUND >= 2) {
      var sp = teamData && teamData.surge_prev != null ? fmtSurgePct(teamData.surge_prev) : (ROUND === 2 ? '0%' : '—');
      var scurr = teamData && teamData.surge_curr != null ? fmtSurgePct(teamData.surge_curr) : '—';
      set(prefix + 'Surge_prev', sp);
      set(prefix + 'Surge_curr', scurr);
    }
    if (ROUND >= 4) {
      set(prefix + 'Churn_prev', ROUND === 4 ? 'нет' : 'да');
      set(prefix + 'Churn_curr', 'да');
    }
    if (ROUND >= 5) {
      set(prefix + 'Stock_prev', ROUND === 5 ? 'нет' : 'да');
      set(prefix + 'Stock_curr', 'да');
    }
  }
  function getArrowLinks() {
    var L = [
      { from: 'orders', to: 'oph', fromSide: 'right', toSide: 'left', route: 'elbow' },
      { from: 'orders', to: 'dc', fromSide: 'bottom', toSide: 'top', route: 'ordersToDc', toOffsetY: -12 },
      { from: 'aov', to: 'dcpo', fromSide: 'right', toSide: 'left', route: 'elbow' },
      { from: 'oph', to: 'cpo', fromSide: 'right', toSide: 'left', route: 'elbow' },
      { from: 'cpo', to: 'dcpo', fromSide: 'right', toSide: 'left', route: 'elbow' },
      { from: 'margin', to: 'dcpo', fromSide: 'right', toSide: 'left', route: 'elbow' },
      { from: 'dcpo', to: 'dc', fromSide: 'bottom', toSide: 'top', route: 'elbow-v', toOffsetY: 8 }
    ];
    if (ROUND >= 2) {
      /* toSide: top — у mid-колонки общий левый край; вход слева давал вертикаль через весь столбец (CTE, AOV…) */
      L.push({ from: 'surge', to: 'aov', fromSide: 'right', toSide: 'top', route: 'elbow' });
      L.push({ from: 'surge', to: 'orders', fromSide: 'left', toSide: 'right', route: 'elbow' });
    }
    if (ROUND >= 4) L.push({ from: 'churn', to: 'orders', fromSide: 'left', toSide: 'right', route: 'elbow' });
    if (ROUND >= 5) L.push({ from: 'stock', to: 'orders', fromSide: 'left', toSide: 'right', route: 'elbow' });
    if (ROUND >= 6) {
      L.push({ from: 'cte', to: 'royalty', fromSide: 'right', toSide: 'top', route: 'elbow' });
      L.push({ from: 'royalty', to: 'margin', fromSide: 'right', toSide: 'top', route: 'elbow' });
      L.push({ from: 'royalty', to: 'dcpo', fromSide: 'right', toSide: 'left', route: 'elbow' });
    }
    return L;
  }
  function pointOnRect(r, side, refPoint) {
    var cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
    var pad = 5;
    if (side === 'topUnderStart' && refPoint) return { x: refPoint.x, y: r.top + pad };
    if (side === 'left') return { x: r.left + pad, y: cy };
    if (side === 'right') return { x: r.right - pad, y: cy };
    if (side === 'top') return { x: cx, y: r.top + pad };
    if (side === 'bottom') return { x: cx, y: r.bottom - pad };
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

  /** Нижняя горизонталь «Заказы→DC»: строго ниже всех видимых плашек */
  function getOrdersToDcLaneY(diag, dr) {
    var maxB = getMaxPlashkaBottomRel(diag, dr);
    var gap = 22;
    var y = maxB > 0 ? maxB + gap : dr.height - 16;
    var floor = dr.height - 9;
    if (y > floor) y = floor;
    return y;
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
    var cpo = diag.querySelector('.block-cpo');
    var rs = diag.querySelector('.right-stack');
    if (!orders || !mid || !cpo || !rs) return null;
    var o = orders.getBoundingClientRect();
    var c = cpo.getBoundingClientRect();
    var r = rs.getBoundingClientRect();
    var ext = midPlashkaExtents(mid, dr);
    var mL = ext.mL;
    var mR = ext.mR;
    var oR = o.right - dr.left;
    var cL = c.left - dr.left;
    var cR = c.right - dr.left;
    var rL = r.left - dr.left;
    function clampGap(x, lo, hi, margin) {
      margin = margin || 4;
      if (hi - lo < margin * 2 + 2) return (lo + hi) / 2;
      return Math.max(lo + margin, Math.min(x, hi - margin));
    }
    var g12ideal = (oR + mL) / 2;
    var g34ideal = (cR + rL) / 2;
    var g12 = clampGap(g12ideal, oR, mL, 5);
    g12 = Math.min(g12, mL - 6);
    g12 = Math.max(g12, oR + 4);
    var g23 = cL - 8;
    if (g23 < mR + 8) g23 = mR + 12;
    if (g23 > cL - 3) g23 = Math.max(mR + 10, (mR + cL) / 2);
    var g34 = clampGap(g34ideal, cR, rL, 5);
    return { g12: g12, g23: g23, g34: g34, mR: mR, mL: mL, midTop: ext.midTop, midBottom: ext.midBottom };
  }
  function linkColumn(nodeId) {
    if (nodeId === 'orders') return 1;
    if (nodeId === 'cpo') return 3;
    if (nodeId === 'dcpo' || nodeId === 'dc') return 4;
    return 2;
  }
  /** Mid → Заказы с левого края механики: вверх по левому краю, полоса над всем столбцом, затем к заказам (не режем соседние плашки) */
  function pathMidLeftToOrdersRight(p1, p2, g12, midTop) {
    var yEsc = Math.max(8, (isFinite(midTop) ? midTop : p1.y) - 14);
    return 'M' + p1.x + ',' + p1.y + ' L' + p1.x + ',' + yEsc + ' L' + g12 + ',' + yEsc + ' L' + g12 + ',' + p2.y + ' L' + p2.x + ',' + p2.y;
  }

  /**
   * Стебель справа → вход в цель сверху (toSide top): горизонталь только над верхом mid / целей,
   * короткий спуск по центру верха — не делит общий левый край со всем столбцом.
   */
  function pathSpineToTopMid(p1, p2, xg, stub, fromRect, toRect, drH, fromSide, midTop) {
    stub = stub || 10;
    var x1 = p1.x, y1 = p1.y, x2 = p2.x, y2 = p2.y;
    var yEsc = Math.min(toRect.top - 7, fromRect.top - 7);
    if (isFinite(midTop)) yEsc = Math.min(yEsc, midTop - 12);
    yEsc = Math.max(6, yEsc);
    var xa;
    if (fromSide === 'right') {
      xa = Math.min(x1 + stub, xg - 2);
    } else if (fromSide === 'left') {
      xa = Math.max(x1 - stub, xg + 2);
    } else {
      xa = x1;
    }
    return 'M' + x1 + ',' + y1 + ' L' + xa + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + yEsc + ' L' + x2 + ',' + yEsc + ' L' + x2 + ',' + y2;
  }

  /**
   * Вход на левый край плашки mid-stack без горизонтали через середину блока (CTE, AOV и т.д.):
   * стебель xg → yJoin над/под блоком → коротко влево → вниз/вверх по левому краю к точке входа.
   */
  function pathSpineToLeftEdgeMid(p1, p2, xg, stub, toRect, drH, fromSide, fromRect) {
    stub = stub || 10;
    var x1 = p1.x, y1 = p1.y, x2 = p2.x, y2 = p2.y;
    var margin = 12;
    var yJoin;
    if (fromRect && fromRect.bottom < toRect.top - 2) {
      yJoin = (fromRect.bottom + toRect.top) / 2;
    } else if (fromRect && toRect.bottom < fromRect.top - 2) {
      yJoin = (toRect.bottom + fromRect.top) / 2;
    } else if (y2 < y1 - 4) {
      yJoin = Math.max(8, toRect.top - margin);
    } else if (y2 > y1 + 4) {
      yJoin = Math.min(drH - 8, toRect.bottom + margin);
    } else {
      var yAb = Math.max(8, toRect.top - margin);
      var yBe = Math.min(drH - 8, toRect.bottom + margin);
      var c1 = Math.abs(y1 - yAb) + Math.abs(y2 - yAb);
      var c2 = Math.abs(y1 - yBe) + Math.abs(y2 - yBe);
      yJoin = c1 <= c2 ? yAb : yBe;
    }
    yJoin = Math.max(8, Math.min(drH - 8, yJoin));
    var xa;
    if (fromSide === 'right') {
      xa = Math.min(x1 + stub, xg - 2);
    } else if (fromSide === 'left') {
      xa = Math.max(x1 - stub, xg + 2);
    } else {
      xa = x1;
    }
    return 'M' + x1 + ',' + y1 + ' L' + xa + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + yJoin + ' L' + x2 + ',' + yJoin + ' L' + x2 + ',' + y2;
  }
  /** Одна вертикаль в коридоре xg; не пересекает блоки колонок */
  function pathViaOneGutter(p1, p2, xg, stub) {
    stub = stub || 10;
    var x1 = p1.x, y1 = p1.y, x2 = p2.x, y2 = p2.y;
    if (Math.abs(x1 - x2) < 5 && Math.abs(y1 - y2) < 5) return 'M' + x1 + ',' + y1 + ' L' + x2 + ',' + y2;
    if (xg >= Math.max(x1, x2) - 0.5) {
      var xa = Math.min(x1 + stub, xg - 2);
      return 'M' + x1 + ',' + y1 + ' L' + xa + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + x2 + ',' + y2;
    }
    if (xg <= Math.min(x1, x2) + 0.5) {
      var xaL = Math.max(x1 - stub, xg + 2);
      return 'M' + x1 + ',' + y1 + ' L' + xaL + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + x2 + ',' + y2;
    }
    if (x2 > x1) {
      var xb = Math.min(x1 + stub, xg - 2);
      var xc = Math.max(x2 - stub, xg + 2);
      return 'M' + x1 + ',' + y1 + ' L' + xb + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + xc + ',' + y2 + ' L' + x2 + ',' + y2;
    }
    var xb2 = Math.max(x1 - stub, xg + 2);
    var xc2 = Math.min(x2 + stub, xg - 2);
    return 'M' + x1 + ',' + y1 + ' L' + xb2 + ',' + y1 + ' L' + xg + ',' + y1 + ' L' + xg + ',' + y2 + ' L' + xc2 + ',' + y2 + ' L' + x2 + ',' + y2;
  }
  /** Кол. 2 → 4: два коридора + обход CPO; горизонталь yLane не проводим «на уровне середины» mid, если можно ниже/выше */
  function pathViaGutters2to4(p1, p2, g23, g34, cpoRel, drH, stub, midBand) {
    stub = stub || 10;
    var yTop = Math.max(8, cpoRel.top - 8);
    var yBot = Math.min(drH - 8, cpoRel.bottom + 8);
    var yBelowMid = midBand && isFinite(midBand.bottom) ? Math.min(drH - 8, midBand.bottom + 20) : null;
    var yAboveMid = midBand && isFinite(midBand.top) ? Math.max(8, midBand.top - 14) : null;
    var candidates = [yTop, yBot];
    if (yBelowMid != null) candidates.push(yBelowMid);
    if (yAboveMid != null) candidates.push(yAboveMid);
    function manhattan(yc) {
      return Math.abs(p1.y - yc) + Math.abs(p2.y - yc);
    }
    var yLane = yTop;
    var best = Infinity;
    for (var ci = 0; ci < candidates.length; ci++) {
      var yc = candidates[ci];
      if (!isFinite(yc)) continue;
      var sc = manhattan(yc);
      if (sc < best) {
        best = sc;
        yLane = yc;
      }
    }
    var xa = Math.min(p1.x + stub, g23 - 2);
    var xb = Math.max(p2.x - stub, g34 + 2);
    return 'M' + p1.x + ',' + p1.y + ' L' + xa + ',' + p1.y + ' L' + g23 + ',' + p1.y + ' L' + g23 + ',' + yLane + ' L' + g34 + ',' + yLane + ' L' + g34 + ',' + p2.y + ' L' + xb + ',' + p2.y + ' L' + p2.x + ',' + p2.y;
  }
  /** DCPO → DC: только в правой колонке, излом по середине по Y */
  function pathElbowVerticalCol4(p1, p2) {
    var ym = (p1.y + p2.y) / 2;
    var xc = (p1.x + p2.x) / 2;
    return 'M' + p1.x + ',' + p1.y + ' L' + xc + ',' + p1.y + ' L' + xc + ',' + ym + ' L' + xc + ',' + p2.y + ' L' + p2.x + ',' + p2.y;
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
    var gutters = getColumnGutters(diag, dr);
    var cpoEl = diag.querySelector('.block-cpo');
    var cpoRel = cpoEl ? { top: cpoEl.getBoundingClientRect().top - dr.top, bottom: cpoEl.getBoundingClientRect().bottom - dr.top } : { top: dr.height * 0.35, bottom: dr.height * 0.55 };
    var midBand = gutters ? { top: gutters.midTop, bottom: gutters.midBottom } : null;
    getArrowLinks().forEach(function (link, idx) {
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
      if (link.toOffsetY) p2 = { x: p2.x, y: p2.y + link.toOffsetY };
      var d;
      if (link.route === 'ordersToDc') {
        var pathY = getOrdersToDcLaneY(diag, dr);
        var dcCx = (toRect.left + toRect.right) / 2;
        var endY = Math.max(pathY + 8, p2.y - 6);
        d = 'M' + p1.x + ',' + p1.y + ' L' + p1.x + ',' + pathY + ' L' + dcCx + ',' + pathY + ' L' + dcCx + ',' + endY + ' L' + p2.x + ',' + p2.y;
      } else if (link.route === 'elbow-v') {
        d = pathElbowVerticalCol4(p1, p2);
      } else if (link.route === 'elbow' && gutters) {
        var cf = linkColumn(link.from);
        var ct = linkColumn(link.to);
        if (cf === 2 && ct === 1 && link.fromSide === 'left' && link.toSide === 'right') {
          d = pathMidLeftToOrdersRight(p1, p2, gutters.g12, gutters.midTop);
        } else if (cf === ct) {
          var xgSame = cf === 2 ? gutters.g23 : (cf === 4 ? gutters.g34 : gutters.g12);
          if (cf === 2 && gutters.mR != null) xgSame = Math.max(xgSame, gutters.mR + 12);
          if (cf === 2 && link.toSide === 'top') {
            d = pathSpineToTopMid(p1, p2, xgSame, 10, fromRect, toRect, dr.height, link.fromSide, gutters.midTop);
          } else if (cf === 2 && link.toSide === 'left') {
            d = pathSpineToLeftEdgeMid(p1, p2, xgSame, 10, toRect, dr.height, link.fromSide, fromRect);
          } else {
            d = pathViaOneGutter(p1, p2, xgSame, 10);
          }
        } else if (Math.abs(cf - ct) === 1) {
          var lo = Math.min(cf, ct), hi = Math.max(cf, ct);
          var xgOne = (lo === 1 && hi === 2) ? gutters.g12 : (lo === 2 && hi === 3) ? Math.max(gutters.g23, (gutters.mR != null ? gutters.mR : 0) + 12) : gutters.g34;
          d = pathViaOneGutter(p1, p2, xgOne, 10);
        } else if (cf === 2 && ct === 4) {
          d = pathViaGutters2to4(p1, p2, gutters.g23, gutters.g34, cpoRel, dr.height, 10, midBand);
        } else {
          d = pathViaOneGutter(p1, p2, gutters.g12, 10);
        }
      } else {
        d = pathViaOneGutter(p1, p2, (p1.x + p2.x) / 2, 10);
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

  document.getElementById('coef1').addEventListener('change', update);
  document.getElementById('coef2').addEventListener('change', update);
  update();
  setTimeout(redrawAllArrows, 0);
  window.addEventListener('resize', redrawAllArrows);
})();
