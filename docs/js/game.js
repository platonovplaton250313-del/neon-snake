/* NEON SNAKE — мобильная версия.
   Чистый JavaScript без сборки: Canvas 2D, WebAudio, MQTT over WebSocket.
   Все режимы ПК-версии, кроме совместимости сети с .exe. */
(() => {
  'use strict';

  /* ================================================================ константы */
  const COLS = 26;
  const ROWS = 20;
  const CELL = 26;
  const FIELD_W = COLS * CELL;
  const FIELD_H = ROWS * CELL;
  const NET_TIME = 90;
  const STORAGE_KEY = 'neon-snake-mobile-v1';

  const MODES = [
    { id: 'classic', name: 'КЛАССИКА', hint: 'СОБИРАЙ ЯБЛОКИ' },
    { id: 'maze', name: 'ЛАБИРИНТ', hint: 'ИЩИ ОБХОД' },
    { id: 'blitz', name: 'БЛИЦ 60', hint: 'УСПЕЙ ДО 0:00' },
    { id: 'chaos', name: 'ХАОС', hint: 'ВЫЖИВИ' },
    { id: 'bots', name: 'ПРОТИВ БОТОВ', hint: 'ОБГОНИ БОТОВ' },
    { id: 'net', name: 'СЕТЕВАЯ ИГРА', hint: 'ПОБЕДИ СОПЕРНИКА' }
  ];
  const MODE_BY_ID = Object.fromEntries(MODES.map((m) => [m.id, m]));

  /* ---------------------------------------------------------------- магазин */
  const SKINS = [
    { id: 'classic', name: 'НЕОН', desc: 'Фирменный бирюзовый градиент', price: 0,
      colors: ['#a8fbff', '#3fd0ff', '#9a6cff'] },
    { id: 'magma', name: 'МАГМА', desc: 'Раскалённый закат', price: 600,
      colors: ['#ffe0a8', '#ff8a3d', '#b51b4b'] },
    { id: 'toxic', name: 'ТОКСИН', desc: 'Кислотный лайм', price: 800,
      colors: ['#eaffb0', '#8dff4d', '#1fbf6b'] },
    { id: 'ice', name: 'ЛЁД', desc: 'Ледяная сталь', price: 900,
      colors: ['#ffffff', '#9fe8ff', '#4a7dff'] },
    { id: 'royal', name: 'ЗОЛОТО', desc: 'Королевский металл', price: 1200,
      colors: ['#fff4c2', '#ffd24a', '#b0720e'] },
    { id: 'void', name: 'ПУСТОТА', desc: 'Фиолетовая бездна', price: 1500,
      colors: ['#e3c8ff', '#b06bff', '#3d1a7a'] },
    { id: 'pixel', name: 'ПИКСЕЛЬ', desc: 'Ретро-аркадный неон', price: 1800,
      colors: ['#c8ff8a', '#39ff88', '#0e7a5a'] },
    { id: 'rainbow', name: 'РАДУГА', desc: 'Переливается прямо в игре', price: 2500,
      colors: ['#ff9ad0', '#ffd24a', '#39ff88'], special: 'rainbow' }
  ];
  const SKIN_BY_ID = Object.fromEntries(SKINS.map((s) => [s.id, s]));
  const RAINBOW_PALETTES = [
    ['#ff9ad0', '#ff4d9d', '#8f2a66'],
    ['#ffe9a0', '#ffb347', '#7a4a16'],
    ['#eaffb0', '#8dff4d', '#1fbf6b'],
    ['#c8f7ff', '#3fd0ff', '#4a7dff'],
    ['#e3c8ff', '#b06bff', '#5a2a9a'],
    ['#ffd0dd', '#ff4d9d', '#b06bff']
  ];

  const CHEATS = [
    { id: 'ghost', name: 'ФАНТОМ', chip: 'ФАНТОМ', icon: '◈', price: 2200,
      desc: 'Проходить сквозь стены, метеориты и соперников. Своё тело всё ещё опасно.' },
    { id: 'x2', name: 'ДВОЙНЫЕ ОЧКИ', chip: '×2', icon: '×2', price: 2600,
      desc: 'Все очки удваиваются. Работает во всех режимах, включая сеть.' },
    { id: 'revive', name: 'ВТОРОЙ ШАНС', chip: 'ШАНС', icon: '↺', price: 2400,
      desc: 'Одно автоматическое возрождение за игру. В сети тоже срабатывает.' },
    { id: 'lucky', name: 'ЗВЕЗДОПАД', chip: 'ЗВЁЗДЫ', icon: '★', price: 1800,
      desc: 'Золотые звёзды появляются заметно чаще. В сети помогает обоим.' },
    { id: 'rich', name: 'ЗОЛОТАЯ ЖИЛА', chip: '+50%', icon: '◆', price: 2000,
      desc: '+50% неонов после каждой игры. Рекорды и награды сохраняются.' }
  ];
  const CHEAT_BY_ID = Object.fromEntries(CHEATS.map((c) => [c.id, c]));

  const PROMO_CODES = {
    NEON2026: { coins: 500 },
    SNAKE777: { coins: 777 },
    NEONRICH: { coins: 1000 },
    GOLDSTAR: { skin: 'royal' },
    HAPPYSNAKE: { coins: 300, skin: 'toxic' },
    PIXELPOWER: { skin: 'pixel' },
    RAINBOWCODE: { skin: 'rainbow' },
    GHOSTMODE: { cheat: 'ghost' },
    DOUBLEUP: { cheat: 'x2' },
    SECONDSHOT: { cheat: 'revive' },
    LUCKYSTAR: { cheat: 'lucky' },
    GOLDDIGGER: { cheat: 'rich' }
  };

  const SPEEDS = {
    slow: { base: 0.185, min: 0.095, ramp: 0.0028 },
    normal: { base: 0.155, min: 0.075, ramp: 0.0032 },
    fast: { base: 0.125, min: 0.060, ramp: 0.0038 }
  };
  const SPECIAL_EVERY = { rare: 6, normal: 4, often: 2 };
  const POWER_EVERY = { classic: 4, maze: 5, blitz: 3, chaos: 3, bots: 4 };
  const POWER_KINDS = ['shield', 'double', 'slow'];
  const POWER_DURATION = { shield: 7, double: 10, slow: 8 };
  const POWER_TEXT = { shield: 'ЩИТ!', double: '×2 ОЧКИ!', slow: 'ЗАМЕДЛЕНИЕ!' };
  const EFFECT_INFO = {
    shield: { label: 'ЩИТ', color: '#7ef9ff' },
    double: { label: '×2', color: '#ff4d9d' },
    slow: { label: 'ЗАМЕДЛ', color: '#b06bff' },
    surge: { label: 'ТУРБО', color: '#ffd24a' }
  };

  const HEAD_C = '#a8fbff';
  const MID_C = '#3fd0ff';
  const TAIL_C = '#9a6cff';
  const CYAN = '#7ef9ff';
  const VIOLET = '#b06bff';
  const MAGENTA = '#ff4d9d';
  const GOLD = '#ffd24a';
  const ORANGE = '#ff9a4d';
  const GREEN = '#39ff88';

  const PLAYER_COLORS = [HEAD_C, MID_C, TAIL_C];
  const NET_HOST_COLORS = [HEAD_C, MID_C, TAIL_C];
  const NET_GUEST_COLORS = ['#ffb3d9', '#ff4d9d', '#8f2a66'];
  const BOT_STYLES = [
    { name: 'НИО', colors: ['#ff9ad0', '#ff4d9d', '#7a1f52'] },
    { name: 'ВОЛЬТ', colors: ['#ffe9a0', '#ffb347', '#7a4a16'] }
  ];

  const DEFAULT_SETTINGS = {
    speed: 'normal',
    wrap: false,
    grid: true,
    particles: true,
    shake: true,
    sound: false,
    specials: 'normal'
  };
  const DIRS = {
    up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0]
  };
  const ROOM_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  /* Сеть работает через публичные MQTT-брокеры поверх WebSocket.
     Первый символ кода комнаты выбирает брокер: A — EMQX, B — HiveMQ. */
  const BROKERS = {
    A: { url: 'wss://broker.emqx.io:8084/mqtt', name: 'EMQX' },
    B: { url: 'wss://broker.hivemq.com:8884/mqtt', name: 'HiveMQ' }
  };
  const NET_TOPIC_ROOT = 'neonsnake/v1/';
  const NET_KEEPALIVE = 30;
  const NET_PEER_TIMEOUT = 12000;

  /* ================================================================ утилиты */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const rnd = (a, b) => a + Math.random() * (b - a);
  const rndInt = (a, b) => Math.floor(rnd(a, b + 1));
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const same = (a, b) => a && b && a[0] === b[0] && a[1] === b[1];
  const opposite = (a, b) => a[0] === -b[0] && a[1] === -b[1];
  const pad2 = (n) => String(n).padStart(2, '0');

  function hexRgb(hex) {
    return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16),
      parseInt(hex.slice(5, 7), 16)];
  }
  function mix(c1, c2, t) {
    t = clamp(t, 0, 1);
    const a = hexRgb(c1);
    const b = hexRgb(c2);
    return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * t) + ',' +
      Math.round(a[1] + (b[1] - a[1]) * t) + ',' +
      Math.round(a[2] + (b[2] - a[2]) * t) + ')';
  }
  function rgba(hex, alpha) {
    const c = hexRgb(hex);
    return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + alpha + ')';
  }

  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function centerOf(cell) {
    return [cell[0] * CELL + CELL / 2, cell[1] * CELL + CELL / 2];
  }

  function code5() {
    /* Первый символ задаёт брокера, поэтому он всегда A или B. */
    let out = Math.random() < 0.5 ? 'A' : 'B';
    for (let i = 1; i < 5; i += 1) {
      out += ROOM_ALPHABET[Math.floor(Math.random() * ROOM_ALPHABET.length)];
    }
    return out;
  }

  function randomId(len) {
    const alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let out = '';
    for (let i = 0; i < (len || 8); i += 1) {
      out += alphabet[Math.floor(Math.random() * alphabet.length)];
    }
    return out;
  }

  function brokerFor(code) {
    return BROKERS[String(code || '').charAt(0).toUpperCase()] || BROKERS.A;
  }

  function hostTopic(code) {
    return NET_TOPIC_ROOT + code + '/h';
  }

  function guestTopic(code) {
    return NET_TOPIC_ROOT + code + '/g';
  }

  /* ================================================================ MQTT 3.1.1
     Минимальный клиент поверх WebSocket: CONNECT, SUBSCRIBE, PUBLISH QoS 0,
     PINGREQ, DISCONNECT и Last Will. Этого достаточно для обмена сообщениями
     между двумя браузерами через публичный брокер. */
  const mqttUtf8 = new TextDecoder('utf-8');
  const mqttEncoder = new TextEncoder();

  function mqttString(text) {
    const bytes = mqttEncoder.encode(String(text));
    const out = new Uint8Array(2 + bytes.length);
    out[0] = (bytes.length >> 8) & 0xff;
    out[1] = bytes.length & 0xff;
    out.set(bytes, 2);
    return out;
  }

  function mqttJoin(parts) {
    let total = 0;
    for (const part of parts) total += part.length;
    const out = new Uint8Array(total);
    let offset = 0;
    for (const part of parts) {
      out.set(part, offset);
      offset += part.length;
    }
    return out;
  }

  function mqttLength(value) {
    const bytes = [];
    let rest = value;
    do {
      let byte = rest % 128;
      rest = Math.floor(rest / 128);
      if (rest > 0) byte |= 0x80;
      bytes.push(byte);
    } while (rest > 0);
    return Uint8Array.from(bytes);
  }

  class MqttClient {
    constructor(url, options) {
      const opts = options || {};
      this.url = url;
      this.clientId = opts.clientId || ('neon-' + randomId(10));
      this.keepalive = opts.keepalive || NET_KEEPALIVE;
      this.will = opts.will || null;
      this.onconnect = null;
      this.onmessage = null;
      this.onclose = null;

      this.ws = null;
      this.buffer = new Uint8Array(0);
      this.connected = false;
      this.closedByUser = false;
      this.failed = false;
      this.packetId = 1;
      this.pingTimer = 0;
      this.lastPing = 0;
      this.lastPong = 0;
      this.connectTimer = 0;
      this.watchdog = 0;
      this.subscriptions = [];
      this.rxCount = 0;
      this.txCount = 0;
    }

    nextPacketId() {
      this.packetId = this.packetId >= 65535 ? 1 : this.packetId + 1;
      return this.packetId;
    }

    packet(header, body) {
      const length = mqttLength(body.length);
      const out = new Uint8Array(1 + length.length + body.length);
      out[0] = header;
      out.set(length, 1);
      out.set(body, 1 + length.length);
      return out;
    }

    raw(bytes) {
      if (!this.ws || this.ws.readyState !== 1) return false;
      try {
        this.ws.send(bytes);
        return true;
      } catch (err) {
        return false;
      }
    }

    buildConnect() {
      let flags = 0x02; /* clean session */
      const payload = [mqttString(this.clientId)];
      if (this.will && this.will.topic) {
        flags |= 0x04; /* will flag, will QoS 0 */
        payload.push(mqttString(this.will.topic));
        payload.push(mqttString(this.will.payload || ''));
      }
      const header = mqttJoin([
        mqttString('MQTT'),
        Uint8Array.from([4, flags, (this.keepalive >> 8) & 0xff, this.keepalive & 0xff])
      ]);
      return this.packet(0x10, mqttJoin([header].concat(payload)));
    }

    connect() {
      this.closedByUser = false;
      this.failed = false;
      let ws;
      try {
        ws = new WebSocket(this.url, ['mqtt']);
      } catch (err) {
        this.fail();
        return;
      }
      this.ws = ws;
      ws.binaryType = 'arraybuffer';
      this.connectTimer = setTimeout(() => {
        if (this.ws === ws && !this.connected) {
          try { ws.close(); } catch (err) { /* уже закрыт */ }
          this.fail();
        }
      }, 10000);
      ws.onopen = () => {
        if (this.ws !== ws) return;
        this.lastPing = Date.now();
        this.lastPong = Date.now();
        this.raw(this.buildConnect());
      };
      ws.onmessage = (event) => {
        if (this.ws !== ws) return;
        const data = event.data;
        if (typeof data === 'string') {
          this.feed(mqttEncoder.encode(data));
        } else if (data instanceof ArrayBuffer) {
          this.feed(new Uint8Array(data));
        } else if (data && typeof data.arrayBuffer === 'function') {
          data.arrayBuffer().then((buf) => {
            if (this.ws === ws) this.feed(new Uint8Array(buf));
          }).catch(() => {});
        }
      };
      ws.onerror = () => { /* за нами придёт onclose */ };
      ws.onclose = () => {
        if (this.ws !== ws) return;
        this.teardown();
        if (this.onclose) this.onclose(this.closedByUser ? 'user' : 'lost');
      };
    }

    fail() {
      if (this.failed) return;
      this.failed = true;
      this.teardown();
      if (this.onclose) this.onclose('failed');
    }

    teardown() {
      clearTimeout(this.connectTimer);
      clearInterval(this.pingTimer);
      clearInterval(this.watchdog);
      this.connectTimer = 0;
      this.pingTimer = 0;
      this.watchdog = 0;
      this.connected = false;
      this.ws = null;
      this.buffer = new Uint8Array(0);
    }

    startTimers() {
      clearInterval(this.pingTimer);
      clearInterval(this.watchdog);
      this.lastPing = Date.now();
      this.lastPong = Date.now();
      this.pingTimer = setInterval(() => {
        if (!this.connected) return;
        this.lastPing = Date.now();
        this.raw(Uint8Array.from([0xc0, 0x00]));
      }, Math.max(5000, (this.keepalive * 1000) / 2));
      this.watchdog = setInterval(() => {
        if (this.connected && Date.now() - this.lastPong > this.keepalive * 2500) {
          try { if (this.ws) this.ws.close(); } catch (err) { /* уже закрыт */ }
        }
      }, 5000);
    }

    subscribe(topic) {
      if (!this.subscriptions.includes(topic)) this.subscriptions.push(topic);
      if (!this.connected) return;
      const id = this.nextPacketId();
      const body = mqttJoin([
        Uint8Array.from([(id >> 8) & 0xff, id & 0xff]),
        mqttString(topic),
        Uint8Array.from([0])
      ]);
      this.raw(this.packet(0x82, body));
    }

    publish(topic, message) {
      if (!this.connected) return false;
      const body = mqttJoin([mqttString(topic), mqttEncoder.encode(String(message))]);
      const ok = this.raw(this.packet(0x30, body));
      if (ok) this.txCount += 1;
      return ok;
    }

    feed(chunk) {
      if (!chunk || !chunk.length) return;
      const joined = new Uint8Array(this.buffer.length + chunk.length);
      joined.set(this.buffer, 0);
      joined.set(chunk, this.buffer.length);
      this.buffer = joined;
      this.parse();
    }

    parse() {
      while (this.buffer.length >= 2) {
        let multiplier = 1;
        let length = 0;
        let offset = 1;
        let byte = 0;
        do {
          if (offset >= this.buffer.length) return;
          byte = this.buffer[offset];
          offset += 1;
          length += (byte & 0x7f) * multiplier;
          multiplier *= 128;
          if (multiplier > 128 * 128 * 128 * 128) return;
        } while (byte & 0x80);
        if (this.buffer.length < offset + length) return;
        const packet = this.buffer.subarray(0, offset + length);
        this.buffer = this.buffer.subarray(offset + length);
        this.handle(packet, offset, length);
      }
    }

    handle(packet, offset, length) {
      if (!length) return;
      const type = packet[0] >> 4;
      const flags = packet[0] & 0x0f;
      if (type === 2) { /* CONNACK */
        const rc = packet[offset + 1];
        if (rc !== 0) {
          this.fail();
          return;
        }
        clearTimeout(this.connectTimer);
        this.connectTimer = 0;
        this.connected = true;
        this.startTimers();
        for (const topic of this.subscriptions) {
          const id = this.nextPacketId();
          const body = mqttJoin([
            Uint8Array.from([(id >> 8) & 0xff, id & 0xff]),
            mqttString(topic),
            Uint8Array.from([0])
          ]);
          this.raw(this.packet(0x82, body));
        }
        if (this.onconnect) this.onconnect();
      } else if (type === 3) { /* PUBLISH */
        const topicLen = (packet[offset] << 8) | packet[offset + 1];
        const topicStart = offset + 2;
        const topicEnd = topicStart + topicLen;
        if (topicEnd > packet.length) return;
        const topic = mqttUtf8.decode(packet.subarray(topicStart, topicEnd));
        const qos = (flags >> 1) & 0x03;
        let start = topicEnd;
        if (qos > 0) start += 2;
        if (start > packet.length) return;
        const message = mqttUtf8.decode(packet.subarray(start));
        if (qos === 1) {
          const id = (packet[topicEnd] << 8) | packet[topicEnd + 1];
          this.raw(Uint8Array.from([0x40, 0x02, (id >> 8) & 0xff, id & 0xff]));
        }
        this.rxCount += 1;
        if (this.onmessage) this.onmessage(topic, message);
      } else if (type === 13) { /* PINGRESP */
        this.lastPong = Date.now();
      }
    }

    close(graceful) {
      this.closedByUser = true;
      clearTimeout(this.connectTimer);
      clearInterval(this.pingTimer);
      clearInterval(this.watchdog);
      const ws = this.ws;
      this.connected = false;
      if (ws) {
        if (graceful) {
          try {
            if (ws.readyState === 1) ws.send(Uint8Array.from([0xe0, 0x00]));
          } catch (err) { /* уже закрыт */ }
        }
        this.ws = null;
        try { ws.close(); } catch (err) { /* уже закрыт */ }
      }
      this.onclose = null;
      this.onconnect = null;
      this.onmessage = null;
    }
  }

  /* ================================================================ хранилище */
  function defaultCheatFlags() {
    const flags = {};
    for (const cheat of CHEATS) flags[cheat.id] = false;
    return flags;
  }

  function validSkinId(id) {
    return typeof id === 'string' && !!SKIN_BY_ID[id] ? id : 'classic';
  }

  function validCheatIds(list) {
    if (!Array.isArray(list)) return [];
    const out = [];
    for (const id of list) {
      if (CHEAT_BY_ID[id] && !out.includes(id)) out.push(id);
    }
    return out;
  }

  function loadStore() {
    const data = {
      settings: Object.assign({}, DEFAULT_SETTINGS),
      bests: { classic: 0, maze: 0, blitz: 0, chaos: 0, bots: 0, net: 0 },
      coins: 0,
      skin: 'classic',
      skins: ['classic'],
      ownedCheats: [],
      cheats: defaultCheatFlags(),
      usedCodes: [],
      daily: { last: '', streak: 0 }
    };
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved && saved.settings) {
          for (const key of Object.keys(DEFAULT_SETTINGS)) {
            if (typeof saved.settings[key] === typeof DEFAULT_SETTINGS[key]) {
              data.settings[key] = saved.settings[key];
            }
          }
        }
        if (saved && saved.bests) {
          for (const mode of Object.keys(data.bests)) {
            const value = Number(saved.bests[mode]);
            if (Number.isFinite(value) && value >= 0) data.bests[mode] = Math.floor(value);
          }
        }
        if (saved) {
          const coins = Number(saved.coins);
          if (Number.isFinite(coins) && coins >= 0) data.coins = Math.floor(coins);
          data.skin = validSkinId(saved.skin);
          if (Array.isArray(saved.skins)) {
            for (const id of saved.skins) {
              const clean = validSkinId(id);
              if (SKIN_BY_ID[id] && !data.skins.includes(clean)) data.skins.push(clean);
            }
          }
          data.ownedCheats = validCheatIds(saved.ownedCheats);
          if (saved.cheats && typeof saved.cheats === 'object') {
            for (const id of data.ownedCheats) data.cheats[id] = !!saved.cheats[id];
          }
          if (Array.isArray(saved.usedCodes)) {
            for (const code of saved.usedCodes) {
              if (typeof code === 'string' && code.length <= 24) {
                const clean = code.toUpperCase();
                if (!data.usedCodes.includes(clean)) data.usedCodes.push(clean);
              }
            }
          }
          if (saved.daily && typeof saved.daily === 'object') {
            if (typeof saved.daily.last === 'string') {
              data.daily.last = saved.daily.last.slice(0, 10);
            }
            const streak = Number(saved.daily.streak);
            if (Number.isFinite(streak) && streak >= 0) {
              data.daily.streak = Math.min(7, Math.floor(streak));
            }
          }
        }
      }
    } catch (err) {
      /* приватный режим или повреждённые данные — играем на значениях по умолчанию */
    }
    if (!data.skins.includes(data.skin)) data.skin = 'classic';
    if (!data.skins.includes('classic')) data.skins.push('classic');
    return data;
  }

  const store = loadStore();
  let saveTimer = 0;
  function saveStore() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      } catch (err) {
        /* переполнение или приватный режим: молча пропускаем */
      }
    }, 120);
  }

  /* ---------------------------------------------------------------- экономика */
  function activeCheatFlags() {
    const flags = defaultCheatFlags();
    for (const id of store.ownedCheats) flags[id] = !!store.cheats[id];
    return flags;
  }

  function activeCheatIds() {
    return CHEATS.filter((cheat) => store.ownedCheats.includes(cheat.id) &&
      store.cheats[cheat.id]).map((cheat) => cheat.id);
  }

  function cheatFlagsFromIds(list) {
    const flags = defaultCheatFlags();
    for (const id of validCheatIds(list)) flags[id] = true;
    return flags;
  }

  function equippedSkin() {
    return SKIN_BY_ID[store.skin] || SKINS[0];
  }

  function skinColorsAt(skinOrId, time) {
    const skin = typeof skinOrId === 'string' ? SKIN_BY_ID[skinOrId] : skinOrId;
    if (!skin) return SKINS[0].colors.slice();
    if (skin.special === 'rainbow') {
      const index = Math.floor((time || 0) * 1.7) % RAINBOW_PALETTES.length;
      return RAINBOW_PALETTES[index].slice();
    }
    return skin.colors.slice();
  }

  function localDateKey(date) {
    const d = date || new Date();
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
  }

  function dailyStatus() {
    const today = localDateKey();
    const yesterday = localDateKey(new Date(Date.now() - 86400000));
    const daily = store.daily || { last: '', streak: 0 };
    const claimedToday = daily.last === today;
    let nextStreak;
    if (claimedToday) nextStreak = Math.max(1, daily.streak || 1);
    else if (daily.last === yesterday) nextStreak = Math.min(7, (daily.streak || 0) + 1);
    else nextStreak = 1;
    return {
      claimedToday,
      streak: daily.streak || 0,
      nextStreak,
      reward: 40 + (nextStreak - 1) * 10
    };
  }

  function addCoins(amount) {
    const value = Math.floor(Number(amount));
    if (!Number.isFinite(value) || value <= 0) return 0;
    store.coins += value;
    saveStore();
    ui.refreshWallet();
    return value;
  }

  function unlockSkin(id) {
    if (!SKIN_BY_ID[id] || store.skins.includes(id)) return false;
    store.skins.push(id);
    saveStore();
    return true;
  }

  function unlockCheat(id) {
    if (!CHEAT_BY_ID[id] || store.ownedCheats.includes(id)) return false;
    store.ownedCheats.push(id);
    store.cheats[id] = true;
    saveStore();
    return true;
  }

  function loadoutPayload() {
    return { skin: store.skin, cheats: activeCheatIds() };
  }

  function parseLoadout(data) {
    const source = data && typeof data === 'object' ? data : {};
    return {
      skin: validSkinId(source.skin),
      cheats: validCheatIds(source.cheats)
    };
  }

  /* ================================================================ звук */
  const Sfx = {
    ctx: null,
    master: null,
    unlock() {
      if (this.ctx) {
        if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => {});
        return;
      }
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      try {
        this.ctx = new AC();
        this.master = this.ctx.createGain();
        this.master.gain.value = 0.5;
        this.master.connect(this.ctx.destination);
      } catch (err) {
        this.ctx = null;
      }
    },
    tone(freq, dur, type, delay, gain) {
      if (!this.ctx || !this.master) return;
      const t0 = this.ctx.currentTime + (delay || 0);
      const osc = this.ctx.createOscillator();
      const env = this.ctx.createGain();
      osc.type = type || 'sine';
      osc.frequency.setValueAtTime(freq, t0);
      env.gain.setValueAtTime(0.0001, t0);
      env.gain.exponentialRampToValueAtTime(gain || 0.18, t0 + 0.012);
      env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      osc.connect(env);
      env.connect(this.master);
      osc.start(t0);
      osc.stop(t0 + dur + 0.03);
    },
    play(name) {
      if (!store.settings.sound) return;
      this.unlock();
      if (!this.ctx) return;
      if (name === 'eat') {
        this.tone(660, 0.09, 'triangle', 0, 0.16);
        this.tone(990, 0.07, 'triangle', 0.05, 0.12);
      } else if (name === 'special') {
        this.tone(880, 0.14, 'sine', 0, 0.16);
        this.tone(1174, 0.14, 'sine', 0.09, 0.14);
        this.tone(1568, 0.22, 'sine', 0.18, 0.12);
      } else if (name === 'power') {
        this.tone(520, 0.1, 'square', 0, 0.08);
        this.tone(780, 0.16, 'triangle', 0.07, 0.12);
      } else if (name === 'die') {
        this.tone(320, 0.34, 'sawtooth', 0, 0.16);
        this.tone(120, 0.45, 'sawtooth', 0.08, 0.12);
      } else if (name === 'win') {
        this.tone(660, 0.13, 'sine', 0, 0.15);
        this.tone(990, 0.13, 'sine', 0.1, 0.14);
        this.tone(1320, 0.3, 'sine', 0.2, 0.12);
      } else if (name === 'count') {
        this.tone(520, 0.07, 'square', 0, 0.07);
      } else if (name === 'go') {
        this.tone(1040, 0.16, 'square', 0, 0.09);
      } else {
        this.tone(440, 0.04, 'sine', 0, 0.06);
      }
    }
  };

  function haptic(ms) {
    if (navigator.vibrate) {
      try { navigator.vibrate(ms); } catch (err) { /* не поддерживается */ }
    }
  }

  /* ================================================================ эффекты */
  const fx = {
    particles: [],
    rings: [],
    floats: [],
    reset() {
      this.particles.length = 0;
      this.rings.length = 0;
      this.floats.length = 0;
    },
    burst(cell, color, count) {
      if (!store.settings.particles) return;
      const [x, y] = centerOf(cell);
      for (let i = 0; i < (count || 12); i += 1) {
        const a = Math.random() * Math.PI * 2;
        const speed = rnd(24, 150);
        this.particles.push({
          x, y,
          vx: Math.cos(a) * speed,
          vy: Math.sin(a) * speed,
          life: rnd(0.32, 0.85),
          max: 0.85,
          size: rnd(1.4, 3.8),
          color
        });
      }
    },
    ring(cell, color, rmax, ttl) {
      if (!store.settings.particles) return;
      const [x, y] = centerOf(cell);
      this.rings.push({ x, y, color, rmax: rmax || 44, ttl: ttl || 0.45, life: ttl || 0.45 });
    },
    text(cell, text, color) {
      const [x, y] = centerOf(cell);
      this.floats.push({ x, y: y - 10, text, color, life: 1.05, max: 1.05 });
    },
    banner(text, color) {
      this.floats.push({ x: FIELD_W / 2, y: 44, text, color, life: 1.7, max: 1.7, big: true });
    },
    update(dt) {
      const parts = this.particles;
      for (let i = parts.length - 1; i >= 0; i -= 1) {
        const p = parts[i];
        p.life -= dt;
        if (p.life <= 0) { parts.splice(i, 1); continue; }
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vx *= 1 - 2.6 * dt;
        p.vy *= 1 - 2.6 * dt;
        p.vy += 30 * dt;
      }
      for (let i = this.rings.length - 1; i >= 0; i -= 1) {
        const r = this.rings[i];
        r.life -= dt;
        if (r.life <= 0) this.rings.splice(i, 1);
      }
      for (let i = this.floats.length - 1; i >= 0; i -= 1) {
        const f = this.floats[i];
        f.life -= dt;
        if (f.life <= 0) this.floats.splice(i, 1);
        else f.y -= (f.big ? 16 : 30) * dt;
      }
    }
  };

  /* ================================================================ игра */
  class Game {
    constructor() {
      this.canvas = $('#game-canvas');
      this.ctx = this.canvas.getContext('2d');
      this.wrapEl = $('#field-wrap');

      this.mode = 'classic';
      this.state = 'idle';
      this.time = 0;
      this.session = 0;
      this.overlayToken = 0;
      this.lastCountdown = 0;
      this.settings = store.settings;
      this.queue = [];
      this.rivals = [];
      this.netRole = null;
      this.broker = null;
      this.roomCode = '';
      this.netClientId = '';
      this.netBrokerName = '';
      this.netActive = false;
      this.netGuestLinked = false;
      this.netHostLinked = false;
      this.netGuestSeen = 0;
      this.netHostSeen = 0;
      this.netGuestId = '';
      this.netGuestSkin = 'classic';
      this.netGuestCheats = [];
      this.netHostSkin = 'classic';
      this.netHostCheats = [];
      this.netJoinAttempts = 0;
      this.netReconnects = 0;
      this.netJoinTimer = 0;
      this.netRetryTimer = 0;
      this.netHeartbeat = 0;
      this.netOver = false;
      this.netHaveState = false;
      this.netSendTimer = 0;
      this.netInterval = 0.15;
      this.netWinner = 0;
      this.netLost = false;
      this.deathReason = 'crash';
      this.newRecord = false;

      this.dpadPressed = null;
      this.swipe = null;
      this.swipeHintPlayed = false;
      this.lastHud = {};

      this.resizeObserver = null;
      this.bindResize();
      this.resetGame('classic');
      this.state = 'idle';
    }

    /* ---------------------------------------------------------- подготовка */
    resetGame(mode) {
      this.mode = mode;
      const settings = store.settings;
      this.wrap = !!settings.wrap;
      const speed = SPEEDS[settings.speed] || SPEEDS.normal;
      this.baseInt = speed.base;
      this.minInt = speed.min;
      this.ramp = speed.ramp;
      if (mode === 'blitz') {
        this.baseInt *= 0.88;
        this.minInt *= 0.90;
      } else if (mode === 'chaos') {
        this.baseInt *= 0.94;
        this.minInt *= 0.94;
      }
      this.interval = this.baseInt;
      this.powerEvery = POWER_EVERY[mode] || 4;
      this.cheats = activeCheatFlags();
      this.scoreMult = this.cheats.x2 ? 2 : 1;
      this.revives = this.cheats.revive ? 1 : 0;
      this.coinMult = this.cheats.rich ? 1.5 : 1;
      let specialEvery = SPECIAL_EVERY[settings.specials] || 4;
      if (this.cheats.lucky) specialEvery = Math.max(2, specialEvery - 2);
      if (mode === 'net' && this.netRole === 'host' && !this.cheats.lucky &&
          this.netGuestCheats.includes('lucky')) {
        specialEvery = Math.max(2, specialEvery - 2);
      }
      this.specialEvery = specialEvery;

      const cy = Math.floor(ROWS / 2);
      const cx = Math.floor(COLS / 2);
      if (mode === 'net' && this.netRole === 'guest') {
        this.snake = [[COLS - 6, cy], [COLS - 7, cy], [COLS - 8, cy], [COLS - 9, cy]];
        this.dir = [-1, 0];
      } else if (mode === 'net') {
        this.snake = [[5, cy], [4, cy], [3, cy], [2, cy]];
        this.dir = [1, 0];
      } else {
        this.snake = [[cx + 1, cy], [cx, cy], [cx - 1, cy], [cx - 2, cy]];
        this.dir = [1, 0];
      }
      this.prevSnake = this.snake.map((c) => c.slice());
      this.queue = [];
      this.score = 0;
      this.combo = 1;
      this.comboTimer = 0;
      this.apples = 0;
      this.stars = 0;
      this.powers = 0;
      this.maxCombo = 1;
      this.special = null;
      this.powerup = null;
      this.effects = { shield: 0, double: 0, slow: 0, surge: 0 };
      this.meteors = new Map();
      this.eventTimer = mode === 'chaos' ? 7.5 : null;
      this.runTime = 0;
      this.acc = 0;
      this.tRender = 0;
      this.scorePulse = 0;
      this.flash = 0;
      this.shake = 0;
      this.deadAt = 0;
      this.deadTimer = 0;
      this.netOver = false;
      this.netHaveState = false;
      this.netWinner = 0;
      this.netLost = false;
      this.deathReason = 'crash';
      this.newRecord = false;
      this.rewarded = false;
      this.rewardCoins = 0;
      this.rewardRecordBonus = 0;
      this.timeLeft = mode === 'blitz' ? 60 : (mode === 'net' ? NET_TIME : null);
      this.walls = new Set();
      if (mode === 'maze') this.buildWalls();
      this.rivals = [];
      this.playerSkin = equippedSkin();
      this.playerColors = skinColorsAt(this.playerSkin, 0);
      if (mode === 'bots') this.spawnBots();
      if (mode === 'net' && this.netRole === 'host') this.spawnNetGuest();
      this.food = null;
      this.pendingEats = [];
      this.newFood();
      this.countdown = 0;
      this.swipe = null;
      fx.reset();
    }

    key(cell) {
      return cell[0] + ',' + cell[1];
    }

    inside(x, y) {
      return x >= 0 && y >= 0 && x < COLS && y < ROWS;
    }

    buildWalls() {
      this.walls = new Set();
      const cx = Math.floor(COLS / 2);
      const cy = Math.floor(ROWS / 2);
      const safe = new Set();
      for (let x = cx - 5; x <= cx + 5; x += 1) {
        for (let y = cy - 2; y <= cy + 2; y += 1) safe.add(x + ',' + y);
      }
      const target = rndInt(48, 66);
      for (let attempt = 0; attempt < 240 && this.walls.size < target; attempt += 1) {
        const horizontal = Math.random() < 0.5;
        const length = rndInt(3, 7);
        const x = rndInt(1, COLS - 2);
        const y = rndInt(1, ROWS - 2);
        const seg = [];
        let ok = true;
        for (let i = 0; i < length; i += 1) {
          const nx = x + (horizontal ? i : 0);
          const ny = y + (horizontal ? 0 : i);
          if (!this.inside(nx, ny) || safe.has(nx + ',' + ny)) {
            ok = false;
            break;
          }
          seg.push(nx + ',' + ny);
        }
        if (ok && seg.length >= 3) {
          for (const cell of seg) this.walls.add(cell);
        }
      }
      for (let i = 0; i < 4; i += 1) {
        const x = rndInt(1, COLS - 2);
        const y = rndInt(1, ROWS - 2);
        if (!safe.has(x + ',' + y)) this.walls.add(x + ',' + y);
      }
    }

    reachable(start) {
      const seen = new Set([this.key(start)]);
      const stack = [start];
      while (stack.length) {
        const [x, y] = stack.pop();
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          let nx = x + dx;
          let ny = y + dy;
          if (this.wrap) {
            nx = (nx + COLS) % COLS;
            ny = (ny + ROWS) % ROWS;
          } else if (!this.inside(nx, ny)) {
            continue;
          }
          const key = nx + ',' + ny;
          if (seen.has(key) || this.walls.has(key)) continue;
          seen.add(key);
          stack.push([nx, ny]);
        }
      }
      return seen;
    }

    freeCells() {
      const blocked = new Set();
      for (const c of this.snake) blocked.add(this.key(c));
      for (const key of this.walls) blocked.add(key);
      for (const key of this.meteors.keys()) blocked.add(key);
      for (const rival of this.rivals) {
        if (rival.alive) for (const c of rival.body) blocked.add(this.key(c));
      }
      if (this.food) blocked.add(this.key(this.food));
      if (this.special) blocked.add(this.key(this.special.pos));
      if (this.powerup) blocked.add(this.key(this.powerup.pos));
      const cells = [];
      for (let y = 0; y < ROWS; y += 1) {
        for (let x = 0; x < COLS; x += 1) {
          if (!blocked.has(x + ',' + y)) cells.push([x, y]);
        }
      }
      if (!this.snake.length) return cells;
      const reach = this.reachable(this.snake[0]);
      const good = cells.filter((c) => reach.has(this.key(c)));
      return good.length ? good : cells;
    }

    newFood() {
      const cells = this.freeCells();
      this.food = cells.length ? pick(cells) : null;
    }

    newSpecial() {
      const cells = this.freeCells();
      if (!cells.length) return;
      this.special = { pos: pick(cells), left: 7.5, ttl: 7.5 };
    }

    newPower() {
      const cells = this.freeCells();
      if (!cells.length) return;
      const free = POWER_KINDS.filter((k) => (this.effects[k] || 0) <= 0);
      const kind = pick(free.length ? free : POWER_KINDS.slice());
      this.powerup = { pos: pick(cells), kind, left: 9, ttl: 9 };
    }

    /* ---------------------------------------------------------- соперники */
    makeRival(name, colors, body, dir) {
      return {
        name, colors, body: body.map((c) => c.slice()),
        prev: body.map((c) => c.slice()), dir: dir.slice(), queue: [],
        score: 0, alive: true, respawn: 0, ai: true,
        apples: 0, stars: 0, powers: 0,
        skin: 'classic', cheats: defaultCheatFlags(), revives: 0
      };
    }

    spawnBots() {
      const cy = Math.floor(ROWS / 2);
      const y1 = clamp(cy - 5, 2, ROWS - 3);
      const y2 = clamp(cy + 5, 2, ROWS - 3);
      this.rivals = [
        this.makeRival(BOT_STYLES[0].name, BOT_STYLES[0].colors,
          [[3, y1], [2, y1], [1, y1], [0, y1]], [1, 0]),
        this.makeRival(BOT_STYLES[1].name, BOT_STYLES[1].colors,
          [[COLS - 4, y2], [COLS - 3, y2], [COLS - 2, y2], [COLS - 1, y2]], [-1, 0])
      ];
    }

    spawnNetGuest() {
      const cy = Math.floor(ROWS / 2);
      const skin = SKIN_BY_ID[this.netGuestSkin] || SKINS[0];
      const rival = this.makeRival('ГОСТЬ', skinColorsAt(skin, 0),
        [[COLS - 6, cy], [COLS - 5, cy], [COLS - 4, cy], [COLS - 3, cy]], [-1, 0]);
      rival.ai = false;
      rival.skin = skin.id;
      rival.cheats = cheatFlagsFromIds(this.netGuestCheats);
      rival.revives = rival.cheats.revive ? 1 : 0;
      this.rivals = [rival];
    }

    rivalCells(exclude) {
      const cells = new Set();
      for (const rival of this.rivals) {
        if (rival !== exclude && rival.alive) {
          for (const c of rival.body) cells.add(this.key(c));
        }
      }
      return cells;
    }

    otherRivalCells(rival) {
      return this.rivalCells(rival);
    }

    respawnRival(rival) {
      const cells = this.freeCells();
      for (let i = cells.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [cells[i], cells[j]] = [cells[j], cells[i]];
      }
      for (const cell of cells) {
        for (const d of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const body = [];
          let ok = true;
          for (let i = 0; i < 4; i += 1) {
            let c = [cell[0] - d[0] * i, cell[1] - d[1] * i];
            if (this.wrap) c = [(c[0] + COLS) % COLS, (c[1] + ROWS) % ROWS];
            else if (!this.inside(c[0], c[1])) { ok = false; break; }
            const key = this.key(c);
            if (this.walls.has(key) || this.snake.some((s) => same(s, c)) ||
                this.otherRivalCells(rival).has(key)) {
              ok = false;
              break;
            }
            body.push(c);
          }
          if (ok) {
            rival.body = body;
            rival.prev = body.map((c) => c.slice());
            rival.dir = d.slice();
            rival.queue = [];
            rival.alive = true;
            rival.respawn = 0;
            return true;
          }
        }
      }
      return false;
    }

    killRival(rival) {
      if (!rival.alive) return;
      if (this.mode === 'net' && (rival.revives || 0) > 0) {
        rival.revives -= 1;
        const oldBody = rival.body;
        rival.alive = false;
        rival.body = [];
        if (this.respawnRival(rival)) {
          fx.banner('ВТОРОЙ ШАНС!', GOLD);
          return;
        }
        rival.body = oldBody;
      }
      rival.alive = false;
      rival.respawn = this.mode === 'bots' ? 2.6 : 0;
      if (rival.body.length) {
        const head = rival.body[0];
        fx.ring(head, rival.colors[1], 66, 0.5);
        for (const seg of rival.body) fx.burst(seg, rival.colors[1], 5);
      }
      if (this.mode === 'net' && this.netRole === 'host') {
        this.endNet(1, 'rival');
      }
    }

    stepRival(rival) {
      if (!rival.alive) return;
      if (rival.ai) {
        const d = this.botDir(rival);
        if (d) rival.dir = d;
      } else if (rival.queue.length) {
        rival.dir = rival.queue.shift();
      }
      const [dx, dy] = rival.dir;
      const cheats = rival.cheats || {};
      const ghost = !!cheats.ghost;
      const scoreMult = cheats.x2 ? 2 : 1;
      let head = [rival.body[0][0] + dx, rival.body[0][1] + dy];
      let outside = !this.inside(head[0], head[1]);
      if (outside && (this.wrap || ghost)) {
        head = [(head[0] + COLS) % COLS, (head[1] + ROWS) % ROWS];
        outside = false;
      }
      const eat = this.food && same(head, this.food);
      const eatSpecial = this.special && same(head, this.special.pos);
      const eatPower = this.powerup && same(head, this.powerup.pos);
      const body = eat ? rival.body : rival.body.slice(0, -1);
      const bodyBlocked = body.some((c) => same(c, head));
      const worldBlocked = this.walls.has(this.key(head)) ||
        this.meteors.has(this.key(head)) ||
        this.snake.some((c) => same(c, head)) ||
        this.otherRivalCells(rival).has(this.key(head));
      if (outside || bodyBlocked || (worldBlocked && !ghost)) {
        this.killRival(rival);
        return;
      }
      rival.prev = rival.body.map((c) => c.slice());
      rival.body.unshift(head);
      if (!eat) rival.body.pop();
      if (eat) {
        rival.score += 10 * scoreMult;
        rival.apples += 1;
        this.newFood();
        fx.burst(head, rival.colors[1], 7);
      }
      if (eatSpecial) {
        rival.score += 30 * scoreMult;
        rival.stars += 1;
        this.special = null;
        fx.ring(head, GOLD, 40, 0.45);
      }
      if (eatPower) {
        rival.score += 15 * scoreMult;
        rival.powers += 1;
        this.powerup = null;
        fx.ring(head, VIOLET, 40, 0.45);
      }
    }

    stepRivals() {
      for (const rival of this.rivals) {
        if (this.state !== 'playing') return;
        if (rival.alive) this.stepRival(rival);
      }
    }

    updateRespawns(dt) {
      for (const rival of this.rivals) {
        if (!rival.alive && rival.respawn > 0) {
          rival.respawn -= dt;
          if (rival.respawn <= 0) this.respawnRival(rival);
        }
      }
    }

    aiBlocked(rival) {
      const blocked = new Set(this.walls);
      for (const key of this.meteors.keys()) blocked.add(key);
      for (const c of this.snake) blocked.add(this.key(c));
      for (const other of this.rivals) {
        if (other !== rival && other.alive) {
          for (const c of other.body) blocked.add(this.key(c));
        }
      }
      if (rival.body.length) blocked.delete(this.key(rival.body[rival.body.length - 1]));
      if (this.snake.length) blocked.delete(this.key(this.snake[this.snake.length - 1]));
      return blocked;
    }

    bfsMap(start, blocked) {
      const dist = new Map([[this.key(start), 0]]);
      const queue = [start];
      let head = 0;
      while (head < queue.length) {
        const [x, y] = queue[head++];
        const nd = dist.get(this.key([x, y])) + 1;
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          let nx = x + dx;
          let ny = y + dy;
          if (this.wrap) {
            nx = (nx + COLS) % COLS;
            ny = (ny + ROWS) % ROWS;
          } else if (!this.inside(nx, ny)) continue;
          const key = nx + ',' + ny;
          if (dist.has(key) || blocked.has(key)) continue;
          dist.set(key, nd);
          queue.push([nx, ny]);
        }
      }
      return dist;
    }

    openArea(start, blocked, limit) {
      const seen = new Set([this.key(start)]);
      const queue = [start];
      let head = 0;
      let count = 0;
      const max = limit || 48;
      while (head < queue.length && count < max) {
        const [x, y] = queue[head++];
        count += 1;
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          let nx = x + dx;
          let ny = y + dy;
          if (this.wrap) {
            nx = (nx + COLS) % COLS;
            ny = (ny + ROWS) % ROWS;
          } else if (!this.inside(nx, ny)) continue;
          const key = nx + ',' + ny;
          if (seen.has(key) || blocked.has(key)) continue;
          seen.add(key);
          queue.push([nx, ny]);
        }
      }
      return count;
    }

    botDir(rival) {
      if (!rival.body.length) return rival.dir;
      const head = rival.body[0];
      const blocked = this.aiBlocked(rival);
      const dist = this.food ? this.bfsMap(this.food, blocked) : new Map();
      let best = null;
      let bestScore = -1e9;
      for (const d of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        if (opposite(d, rival.dir)) continue;
        let nx = head[0] + d[0];
        let ny = head[1] + d[1];
        if (this.wrap) {
          nx = (nx + COLS) % COLS;
          ny = (ny + ROWS) % ROWS;
        } else if (!this.inside(nx, ny)) continue;
        const key = nx + ',' + ny;
        if (blocked.has(key)) continue;
        let score = 0;
        if (this.food) {
          const fd = dist.get(key);
          if (fd !== undefined) score += 260 - fd * 5;
          else score -= 90;
        }
        score += this.openArea([nx, ny], blocked, 48) * 1.2;
        if (same(d, rival.dir)) score += 3;
        score += Math.random() * 4;
        if (score > bestScore) {
          bestScore = score;
          best = d;
        }
      }
      return best || rival.dir;
    }

    /* ---------------------------------------------------------- ход */
    turn(d) {
      if (!d || (d[0] === 0 && d[1] === 0)) return;
      if (this.state !== 'playing' && this.state !== 'countdown') return;
      if (this.mode === 'net' && this.netRole === 'guest') {
        if (this.dir && opposite(d, this.dir)) return;
        this.netSend({ t: 'input', d: [d[0], d[1]] });
        haptic(6);
        return;
      }
      const last = this.queue.length ? this.queue[this.queue.length - 1] : this.dir;
      if (same(d, last) || opposite(d, last)) return;
      if (this.queue.length >= 2) return;
      this.queue.push([d[0], d[1]]);
      Sfx.play('menu');
      haptic(6);
    }

    pendingEat(cell, color, text, tcolor) {
      this.pendingEats.push({
        cell, color, text, tcolor,
        delay: Math.max(0.08, this.interval)
      });
    }

    step() {
      if (this.queue.length) this.dir = this.queue.shift();
      const [dx, dy] = this.dir;
      const [hx, hy] = this.snake[0];
      let head = [hx + dx, hy + dy];
      let outside = !this.inside(head[0], head[1]);
      const shield = (this.effects.shield || 0) > 0;
      const ghost = !!this.cheats.ghost;
      if (outside && (this.wrap || shield || ghost)) {
        head = [(head[0] + COLS) % COLS, (head[1] + ROWS) % ROWS];
        outside = false;
      }
      const eatNormal = this.food && same(head, this.food);
      const eatSpecial = this.special && same(head, this.special.pos);
      const eatPower = this.powerup && same(head, this.powerup.pos);
      const grow = (eatNormal ? 1 : 0) + (eatSpecial ? 2 : 0);
      const body = grow ? this.snake : this.snake.slice(0, -1);
      const bodyBlocked = body.some((c) => same(c, head));
      const worldBlocked = this.walls.has(this.key(head)) ||
        this.meteors.has(this.key(head)) ||
        this.rivalCells().has(this.key(head));
      if (outside || (bodyBlocked && !shield) || (worldBlocked && !shield && !ghost)) {
        this.die('crash');
        return;
      }
      this.prevSnake = this.snake.map((c) => c.slice());
      this.snake.unshift(head);
      if (grow) {
        for (let i = 0; i < grow - 1; i += 1) {
          this.snake.push(this.snake[this.snake.length - 1].slice());
        }
      } else {
        this.snake.pop();
      }
      if (eatNormal) this.eatFood(head);
      if (eatSpecial) this.eatSpecial(head);
      if (eatPower) this.eatPower(head);
      const base = Math.max(this.minInt, this.baseInt - this.ramp * (this.snake.length - 4));
      let scale = 1;
      if ((this.effects.slow || 0) > 0) scale *= 1.42;
      if ((this.effects.surge || 0) > 0) scale *= 0.78;
      this.interval = clamp(base * scale, 0.062, 0.38);
    }

    eatFood(cell) {
      if (this.comboTimer > 0) this.combo = Math.min(5, this.combo + 1);
      else this.combo = 1;
      this.comboTimer = (this.mode === 'blitz' || this.mode === 'chaos') ? 2.5 : 3.0;
      this.maxCombo = Math.max(this.maxCombo, this.combo);
      const mult = (this.effects.double || 0) > 0 ? 2 : 1;
      const gain = 10 * this.combo * mult * this.scoreMult;
      this.score += gain;
      this.scorePulse = 1;
      this.apples += 1;
      this.newFood();
      if (this.apples % this.specialEvery === 0 && !this.special) this.newSpecial();
      if (this.mode !== 'net' && this.apples % this.powerEvery === 0 && !this.powerup) {
        this.newPower();
      }
      this.pendingEat(cell, '#ff5d8f',
        '+' + gain + (this.combo > 1 ? '  x' + this.combo : ''), '#ffd0dd');
      Sfx.play('eat');
      if (this.settings.shake) this.shake = Math.max(this.shake, 1.4);
    }

    eatSpecial(cell) {
      const mult = (this.effects.double || 0) > 0 ? 2 : 1;
      const gain = 30 * Math.max(1, this.combo) * mult * this.scoreMult;
      this.score += gain;
      this.scorePulse = 1;
      this.stars += 1;
      this.special = null;
      if (this.settings.shake) this.shake = Math.max(this.shake, 5);
      this.pendingEat(cell, GOLD, '+' + gain + '  ★', '#fff0b8');
      Sfx.play('special');
      haptic(16);
    }

    eatPower(cell) {
      const kind = this.powerup ? this.powerup.kind : 'shield';
      this.powerup = null;
      const duration = POWER_DURATION[kind] || 8;
      this.effects[kind] = Math.max(this.effects[kind] || 0, duration);
      const gain = 15 * this.scoreMult;
      this.score += gain;
      this.scorePulse = 1;
      this.powers += 1;
      const color = EFFECT_INFO[kind].color;
      if (this.settings.shake) this.shake = Math.max(this.shake, 3);
      this.pendingEat(cell, color, POWER_TEXT[kind] + '  +' + gain, mix(color, '#ffffff', 0.45));
      Sfx.play('power');
      haptic(12);
    }

    spawnMeteors(count) {
      const head = this.snake[0];
      const blocked = new Set();
      for (const c of this.snake) blocked.add(this.key(c));
      for (const key of this.walls) blocked.add(key);
      for (const key of this.meteors.keys()) blocked.add(key);
      if (this.food) blocked.add(this.key(this.food));
      if (this.special) blocked.add(this.key(this.special.pos));
      if (this.powerup) blocked.add(this.key(this.powerup.pos));
      let placed = 0;
      for (let attempt = 0; attempt < 140 && placed < count; attempt += 1) {
        const cell = [rndInt(0, COLS - 1), rndInt(0, ROWS - 1)];
        const key = this.key(cell);
        if (blocked.has(key)) continue;
        if (Math.abs(cell[0] - head[0]) + Math.abs(cell[1] - head[1]) < 5) continue;
        this.meteors.set(key, rnd(7, 9.5));
        blocked.add(key);
        placed += 1;
      }
    }

    chaosEvent() {
      const kind = pick(['meteor', 'surge', 'star']);
      if (kind === 'meteor') {
        this.spawnMeteors(rndInt(3, 5));
        fx.banner('МЕТЕОРИТЫ!', ORANGE);
        if (this.settings.shake) this.shake = Math.max(this.shake, 5);
        Sfx.play('special');
      } else if (kind === 'surge') {
        this.effects.surge = Math.max(this.effects.surge || 0, 5);
        fx.banner('ТУРБО!', GOLD);
        Sfx.play('menu');
      } else if (!this.special) {
        this.newSpecial();
        fx.banner('ЗВЕЗДОПАД!', GOLD);
        Sfx.play('menu');
      } else {
        this.spawnMeteors(2);
        fx.banner('МЕТЕОРИТЫ!', ORANGE);
        Sfx.play('menu');
      }
    }

    puff(cell, color) {
      fx.burst(cell, color, 10);
    }

    update(dt) {
      this.time += dt;
      this.shake = Math.max(0, this.shake - dt * 42);
      this.flash = Math.max(0, this.flash - dt * 2);
      this.scorePulse = Math.max(0, this.scorePulse - dt * 3.5);
      fx.update(dt);

      if (this.state === 'countdown') {
        this.countdown -= dt;
        if (this.mode === 'net' && this.netRole === 'host') {
          if (this.state === 'countdown') this.netHostSend(dt);
        }
        if (this.countdown <= 0) {
          this.state = 'playing';
          this.acc = 0;
          this.tRender = 0;
          Sfx.play('go');
          haptic(20);
        }
        this.updateHud();
        return;
      }
      if (this.state !== 'playing') {
        this.updateHud();
        return;
      }

      if (this.mode === 'net') {
        if (this.netRole === 'guest') {
          this.netClientFrame(dt);
          this.updateHud();
          return;
        }
      }

      if (this.timeLeft !== null) {
        this.timeLeft = Math.max(0, this.timeLeft - dt);
        if (this.timeLeft <= 0) {
          if (this.mode === 'net' && this.netRole === 'host') {
            const opp = this.rivals[0] ? this.rivals[0].score : 0;
            this.endNet(this.score >= opp ? 1 : 2, 'time');
          } else {
            this.die('time');
          }
          this.updateHud();
          return;
        }
      }
      this.runTime += dt;

      for (const key of Object.keys(this.effects)) {
        if (this.effects[key] > 0) {
          this.effects[key] = Math.max(0, this.effects[key] - dt);
          if (this.effects[key] === 0 && this.snake.length) {
            this.puff(this.snake[0], EFFECT_INFO[key] ? EFFECT_INFO[key].color : CYAN);
          }
        }
      }
      if (this.comboTimer > 0) {
        this.comboTimer -= dt;
        if (this.comboTimer <= 0) this.combo = 1;
      }
      if (this.special) {
        this.special.left -= dt;
        if (this.special.left <= 0) {
          this.puff(this.special.pos, GOLD);
          this.special = null;
        }
      }
      if (this.powerup) {
        this.powerup.left -= dt;
        if (this.powerup.left <= 0) {
          this.puff(this.powerup.pos, EFFECT_INFO[this.powerup.kind].color);
          this.powerup = null;
        }
      }
      if (this.meteors.size) {
        const gone = [];
        for (const [key, left] of this.meteors) {
          const next = left - dt;
          if (next <= 0) gone.push(key);
          else this.meteors.set(key, next);
        }
        for (const key of gone) {
          this.meteors.delete(key);
          this.puff(key.split(',').map(Number), ORANGE);
        }
      }
      if (this.mode === 'chaos' && this.eventTimer !== null) {
        this.eventTimer -= dt;
        if (this.eventTimer <= 0) {
          this.eventTimer = rnd(7, 10.5);
          this.chaosEvent();
        }
      }
      if (this.pendingEats.length) {
        const waiting = [];
        for (const pe of this.pendingEats) {
          pe.delay -= dt;
          if (pe.delay <= 0) {
            fx.burst(pe.cell, pe.color, 16);
            fx.ring(pe.cell, pe.color, pe.color === GOLD ? 54 : 44, 0.5);
            fx.text(pe.cell, pe.text, pe.tcolor);
            this.flash = Math.max(this.flash, 0.75);
          } else {
            waiting.push(pe);
          }
        }
        this.pendingEats = waiting;
      }

      this.acc += dt;
      let steps = 0;
      while (this.acc >= this.interval && steps < 4 && this.state === 'playing') {
        this.acc -= this.interval;
        this.step();
        if ((this.mode === 'bots' || (this.mode === 'net' && this.netRole === 'host')) &&
            this.state === 'playing') {
          this.stepRivals();
        }
        steps += 1;
      }
      if (this.state === 'playing') {
        this.tRender = clamp(this.acc / this.interval, 0, 1);
        if (this.mode === 'bots') this.updateRespawns(dt);
        else if (this.mode === 'net' && this.netRole === 'host') this.netHostSend(dt);
      }
      this.updateHud();
    }

    die(reason) {
      if (this.state !== 'playing') return;
      if ((this.revives || 0) > 0 && reason !== 'time') {
        this.revives -= 1;
        if (this.reviveSnake()) return;
      }
      this.state = 'dead';
      this.deathReason = reason || 'crash';
      this.deadAt = this.time;
      this.deadTimer = 0.7;
      this.prevSnake = this.snake.map((c) => c.slice());
      this.tRender = 0;
      if (this.settings.shake) this.shake = 15;
      this.flash = 1;
      this.combo = 1;
      this.comboTimer = 0;
      this.effects = { shield: 0, double: 0, slow: 0, surge: 0 };
      if (this.snake.length) {
        const [hx, hy] = centerOf(this.snake[0]);
        if (this.settings.particles) {
          for (const seg of this.snake) {
            const [x, y] = centerOf(seg);
            this.particlesBurstAt(x, y, mix(CYAN, VIOLET, Math.random()));
          }
          for (let i = 0; i < 24; i += 1) this.particlesBurstAt(hx, hy, MAGENTA);
        }
        fx.ring(this.snake[0], MAGENTA, 95, 0.6);
      }
      for (const pe of this.pendingEats) {
        fx.burst(pe.cell, pe.color, 10);
        fx.text(pe.cell, pe.text, pe.tcolor);
      }
      this.pendingEats = [];
      this.commitBest();
      Sfx.play('die');
      haptic([18, 40, 24]);
      if (this.mode === 'net' && this.netRole === 'host') this.endNet(2, reason || 'crash');
      else this.scheduleDeathOverlay(700);
    }

    reviveSnake() {
      const cells = this.freeCells();
      const free = new Set(cells.map((c) => this.key(c)));
      for (let i = cells.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [cells[i], cells[j]] = [cells[j], cells[i]];
      }
      for (const cell of cells) {
        for (const d of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const body = [];
          let ok = true;
          for (let i = 0; i < 4; i += 1) {
            let c = [cell[0] - d[0] * i, cell[1] - d[1] * i];
            if (this.wrap) c = [(c[0] + COLS) % COLS, (c[1] + ROWS) % ROWS];
            else if (!this.inside(c[0], c[1])) { ok = false; break; }
            if (!free.has(this.key(c))) { ok = false; break; }
            body.push(c);
          }
          if (!ok) continue;
          this.snake = body;
          this.prevSnake = body.map((c) => c.slice());
          this.dir = d.slice();
          this.queue = [];
          this.state = 'playing';
          this.deadTimer = 0;
          this.acc = 0;
          this.tRender = 0;
          this.combo = 1;
          this.comboTimer = 0;
          this.effects.shield = Math.max(this.effects.shield || 0, 3);
          this.pendingEats = [];
          this.flash = 0.8;
          if (this.settings.shake) this.shake = Math.max(this.shake, 6);
          fx.banner('ВТОРОЙ ШАНС!', GOLD);
          Sfx.play('special');
          haptic(24);
          return true;
        }
      }
      return false;
    }

    particlesBurstAt(x, y, color) {
      if (!this.settings.particles) return;
      const a = Math.random() * Math.PI * 2;
      const speed = rnd(30, 170);
      fx.particles.push({
        x, y, vx: Math.cos(a) * speed, vy: Math.sin(a) * speed,
        life: rnd(0.4, 1.0), max: 1.0, size: rnd(1.6, 4), color
      });
    }

    commitBest() {
      const best = store.bests[this.mode] || 0;
      if (this.score > best) {
        store.bests[this.mode] = Math.floor(this.score);
        saveStore();
        this.newRecord = true;
        this.refreshBests();
      } else {
        this.newRecord = false;
      }
      this.grantCoins();
    }

    grantCoins() {
      if (this.rewarded) return;
      this.rewarded = true;
      const base = Math.floor(this.score / 5) + this.apples * 3 +
        this.stars * 6 + this.powers * 4;
      const recordBonus = this.newRecord ? 150 : 0;
      let netBonus = 0;
      if (this.mode === 'net') {
        netBonus = 15;
        const myWinner = this.netRole === 'guest' ? 2 : 1;
        if (this.netWinner === myWinner) netBonus += 30;
      }
      const total = Math.max(1, Math.round((base + recordBonus + netBonus) * this.coinMult));
      this.rewardCoins = total;
      this.rewardRecordBonus = recordBonus;
      store.coins += total;
      saveStore();
      ui.refreshWallet();
    }

    /* ---------------------------------------------------------- сеть */
    netCreateRoom() {
      this.closeNet();
      this.netRole = 'host';
      this.netOver = false;
      this.netLost = false;
      this.netActive = false;
      this.netGuestLinked = false;
      this.netGuestSeen = 0;
      this.netReconnects = 0;
      this.roomCode = code5();
      this.netClientId = 'ns-h-' + randomId(8);
      ui.setRoomCode(this.roomCode);
      ui.setHostStatus('ПОДКЛЮЧАЕМСЯ К СЕРВЕРУ…');
      ui.enableHost(false);
      ui.setShare(false);
      this.openHostBroker();
    }

    openHostBroker() {
      this.closeBrokerOnly(false);
      const code = this.roomCode;
      if (!code) return;
      clearTimeout(this.netRetryTimer);
      const broker = brokerFor(code);
      const client = new MqttClient(broker.url, {
        clientId: this.netClientId || ('ns-h-' + randomId(8)),
        keepalive: NET_KEEPALIVE,
        will: {
          topic: hostTopic(code),
          payload: JSON.stringify({ t: 'bye', role: 'host' })
        }
      });
      this.broker = client;
      this.netBrokerName = broker.name;
      client.onconnect = () => {
        if (this.broker !== client || this.netRole !== 'host') return;
        this.netReconnects = 0;
        client.subscribe(guestTopic(code));
        ui.setHostStatus('КОМНАТА ГОТОВА · ЖДЁМ ИГРОКА', 'ok');
        ui.enableHost(false, 'КОМНАТА СОЗДАНА');
        ui.setShare(true);
        this.startNetHeartbeat();
      };
      client.onmessage = (topic, message) => {
        if (this.broker !== client) return;
        this.onNetMessage(message);
      };
      client.onclose = () => {
        if (this.broker !== client) return;
        this.onBrokerLost();
      };
      client.connect();
    }

    netJoinRoom(rawCode) {
      const code = sanitizeRoom(rawCode);
      if (code.length !== 5) {
        ui.setJoinStatus('НУЖНО РОВНО 5 СИМВОЛОВ', 'err');
        return;
      }
      this.closeNet();
      this.netRole = 'guest';
      this.netOver = false;
      this.netLost = false;
      this.netActive = false;
      this.netHostLinked = false;
      this.netHostSeen = 0;
      this.netReconnects = 0;
      this.roomCode = code;
      this.netClientId = 'ns-g-' + randomId(8);
      ui.setJoinStatus('ПОДКЛЮЧАЕМСЯ…', '');
      ui.enableJoin(false);
      this.startGuestConnection();
    }

    startGuestConnection() {
      this.closeBrokerOnly(false);
      const code = this.roomCode;
      if (!code) return;
      clearTimeout(this.netRetryTimer);
      const broker = brokerFor(code);
      const client = new MqttClient(broker.url, {
        clientId: this.netClientId || ('ns-g-' + randomId(8)),
        keepalive: NET_KEEPALIVE,
        will: {
          topic: guestTopic(code),
          payload: JSON.stringify({ t: 'bye', role: 'guest' })
        }
      });
      this.broker = client;
      this.netBrokerName = broker.name;
      this.netJoinAttempts = 0;
      client.onconnect = () => {
        if (this.broker !== client || this.netRole !== 'guest') return;
        this.netReconnects = 0;
        client.subscribe(hostTopic(code));
        ui.setJoinStatus('ИЩЕМ КОМНАТУ ' + code + '…', '');
        this.sendNetJoin();
        this.startNetHeartbeat();
      };
      client.onmessage = (topic, message) => {
        if (this.broker !== client) return;
        this.onNetMessage(message);
      };
      client.onclose = () => {
        if (this.broker !== client) return;
        this.onBrokerLost();
      };
      client.connect();
    }

    sendNetJoin() {
      if (this.netRole !== 'guest' || this.netHostLinked) return;
      const payload = Object.assign({ t: 'join', v: 1, id: this.netClientId }, loadoutPayload());
      if (!this.netSend(payload)) return;
      this.netJoinAttempts += 1;
      if (this.netJoinAttempts >= 8) {
        ui.setJoinStatus('ХОСТ НЕ ОТВЕЧАЕТ · ПРОВЕРЬТЕ КОД', 'err');
        ui.enableJoin(true);
        this.closeNet();
        return;
      }
      clearTimeout(this.netJoinTimer);
      this.netJoinTimer = setTimeout(() => {
        if (this.netRole === 'guest' && this.broker && this.broker.connected &&
            !this.netHostLinked) {
          this.sendNetJoin();
        }
      }, 3200);
    }

    startNetHeartbeat() {
      clearInterval(this.netHeartbeat);
      this.netHeartbeat = setInterval(() => {
        if (!this.broker || !this.broker.connected) return;
        if (this.netRole === 'guest') {
          this.netSend({ t: 'ping' });
          if (this.netActive && this.netHostSeen &&
              performance.now() - this.netHostSeen > NET_PEER_TIMEOUT) {
            this.onHostLeft();
          }
        } else if (this.netRole === 'host' && this.netActive) {
          if (this.netGuestLinked && this.netGuestSeen &&
              performance.now() - this.netGuestSeen > NET_PEER_TIMEOUT) {
            this.onGuestLeft();
          }
        }
      }, 3000);
    }

    closeBrokerOnly(sendBye) {
      clearTimeout(this.netJoinTimer);
      clearTimeout(this.netRetryTimer);
      clearInterval(this.netHeartbeat);
      this.netJoinTimer = 0;
      this.netRetryTimer = 0;
      this.netHeartbeat = 0;
      if (!this.broker) return;
      const broker = this.broker;
      this.broker = null;
      if (sendBye && broker.connected) {
        try {
          const topic = this.netRole === 'host' ? hostTopic(this.roomCode) : guestTopic(this.roomCode);
          broker.publish(topic, JSON.stringify({ t: 'bye', role: this.netRole }));
        } catch (err) { /* связь уже пропала */ }
      }
      try { broker.close(true); } catch (err) { /* уже закрыт */ }
    }

    closeNet() {
      const wasLinked = this.netActive ||
        (this.netRole === 'host' ? this.netGuestLinked : this.netHostLinked);
      this.closeBrokerOnly(!!wasLinked);
      this.netActive = false;
      this.netGuestLinked = false;
      this.netHostLinked = false;
      this.netGuestSeen = 0;
      this.netHostSeen = 0;
      this.netGuestId = '';
      this.netJoinAttempts = 0;
      this.netRole = null;
      this.netHaveState = false;
      this.netSendTimer = 0;
      this.netCountdown = 0;
      this.netGuestSkin = 'classic';
      this.netGuestCheats = [];
      this.netHostSkin = 'classic';
      this.netHostCheats = [];
      this.playerColors = null;
    }

    netSend(msg) {
      if (!this.broker || !this.broker.connected) return false;
      const topic = this.netRole === 'host' ? hostTopic(this.roomCode) : guestTopic(this.roomCode);
      try {
        return this.broker.publish(topic, JSON.stringify(msg));
      } catch (err) {
        return false;
      }
    }

    canReachPeer() {
      if (!this.broker || !this.broker.connected) return false;
      return this.netRole === 'host' ? !!this.netGuestLinked : !!this.netHostLinked;
    }

    beginNetMatch() {
      this.session += 1;
      this.netOver = false;
      this.netLost = false;
      this.netActive = true;
      this.netSendTimer = 0;
      this.resetGame('net');
      ui.showScreen('game');
      ui.hideOverlay();
      this.resizeCanvas();
      this.netHaveState = this.netRole === 'host';
      this.countdown = this.netRole === 'host' ? 3.2 : 0;
      this.netCountdown = this.netRole === 'guest' ? 3.2 : 0;
      this.state = this.netRole === 'host' ? 'countdown' : 'playing';
      this.deadTimer = 0;
      if (this.netRole === 'host') this.netGuestSeen = performance.now();
      else this.netHostSeen = performance.now();
      ui.setHudMode('СЕТЕВАЯ ИГРА');
      ui.showTimer(true);
      ui.setSub(this.netRole === 'host' ? 'ЖДЁМ СОПЕРНИКА…' : 'СОЕДИНЕНИЕ…');
      this.updateHud();
      Sfx.play('menu');
      haptic(20);
      if (this.netRole === 'host') this.netHostSend(0, true);
    }

    onNetMessage(text) {
      if (typeof text !== 'string' || text.length > 9000) return;
      let data;
      try {
        data = JSON.parse(text);
      } catch (err) {
        return;
      }
      if (!data || typeof data !== 'object') return;
      const now = performance.now();
      if (this.netRole === 'host') {
        if (data.t === 'join') {
          const id = typeof data.id === 'string' ? data.id.slice(0, 24) : '';
          if (this.netGuestLinked && id && this.netGuestId && id !== this.netGuestId) return;
          if (id) this.netGuestId = id;
          const loadout = parseLoadout(data);
          this.netGuestSkin = loadout.skin;
          this.netGuestCheats = loadout.cheats;
          this.netGuestSeen = now;
          this.onGuestJoin(data);
          return;
        }
        if (data.t === 'bye') {
          this.onGuestLeft();
          return;
        }
        if (!this.netGuestLinked) return;
        this.netGuestSeen = now;
        if (data.t === 'input') this.netApplyInput(data);
        else if (data.t === 'rematch' && this.netOver) {
          const loadout = parseLoadout(data);
          this.netGuestSkin = loadout.skin;
          this.netGuestCheats = loadout.cheats;
          this.netSend({ t: 'again' });
          this.beginNetMatch();
        }
      } else if (this.netRole === 'guest') {
        if (data.t === 'bye') {
          this.onHostLeft();
          return;
        }
        this.netHostSeen = now;
        if (data.t === 'welcome') this.onHostWelcome(data);
        else if (data.t === 'state') this.applyNetState(data);
        else if (data.t === 'over') this.applyNetOver(data);
        else if (data.t === 'again' && this.netHostLinked) this.beginNetMatch();
      }
    }

    onGuestJoin() {
      if (this.netRole !== 'host' || !this.broker || !this.broker.connected) return;
      this.netGuestLinked = true;
      this.netGuestSeen = performance.now();
      const welcome = Object.assign({ t: 'welcome', v: 1 }, loadoutPayload());
      this.netSend(welcome);
      if (this.netActive && !this.netOver &&
          (this.state === 'playing' || this.state === 'countdown')) {
        this.netHostSend(0, true);
        return;
      }
      this.beginNetMatch();
    }

    onHostWelcome(data) {
      if (this.netRole !== 'guest' || this.netHostLinked) return;
      const loadout = parseLoadout(data);
      this.netHostSkin = loadout.skin;
      this.netHostCheats = loadout.cheats;
      this.netHostLinked = true;
      this.netHostSeen = performance.now();
      clearTimeout(this.netJoinTimer);
      this.netJoinTimer = 0;
      ui.setJoinStatus('СОЕДИНЕНО', 'ok');
      this.beginNetMatch();
    }

    onGuestLeft() {
      if (this.netRole !== 'host') return;
      this.netGuestLinked = false;
      this.netGuestSeen = 0;
      if (this.netActive && !this.netOver) {
        this.endNet(1, 'lost');
      }
    }

    onHostLeft() {
      if (this.netRole !== 'guest') return;
      this.netHostLinked = false;
      this.netHostSeen = 0;
      clearTimeout(this.netJoinTimer);
      this.netJoinTimer = 0;
      if (this.netOver && this.netLost) return;
      const inMatch = this.netActive || this.netHaveState;
      this.netOver = true;
      this.netLost = true;
      this.netActive = false;
      this.deathReason = 'lost';
      if (inMatch) {
        this.state = 'dead';
        this.deadAt = this.time;
        this.prevSnake = this.snake.map((c) => c.slice());
        this.commitBest();
        this.scheduleNetOverlay(400);
      } else {
        ui.setJoinStatus('ХОСТ ЗАКРЫЛ КОМНАТУ', 'err');
        ui.enableJoin(true);
      }
    }

    onBrokerLost() {
      this.broker = null;
      clearTimeout(this.netJoinTimer);
      clearTimeout(this.netRetryTimer);
      clearInterval(this.netHeartbeat);
      this.netJoinTimer = 0;
      this.netRetryTimer = 0;
      this.netHeartbeat = 0;
      if (this.netRole === 'host') {
        if (this.netActive && !this.netOver) {
          this.netActive = false;
          this.netOver = true;
          this.netLost = true;
          if (this.state === 'playing' || this.state === 'countdown') {
            this.state = 'dead';
            this.deadAt = this.time;
            this.prevSnake = this.snake.map((c) => c.slice());
            this.commitBest();
            this.scheduleNetOverlay(400);
          }
          return;
        }
        this.netReconnects = (this.netReconnects || 0) + 1;
        if (this.netReconnects > 3) {
          ui.setHostStatus('НЕТ СВЯЗИ С СЕРВЕРОМ · ПРОВЕРЬТЕ ИНТЕРНЕТ', 'err');
          ui.enableHost(true);
          this.netRole = null;
          return;
        }
        ui.setHostStatus('СВЯЗЬ С СЕРВЕРОМ ПОТЕРЯНА · ПЕРЕПОДКЛЮЧАЕМСЯ', 'err');
        this.netRetryTimer = setTimeout(() => {
          if (this.netRole === 'host' && this.roomCode) this.openHostBroker();
        }, 1200);
        return;
      }
      if (this.netRole !== 'guest') return;
      if (this.netActive || this.netHostLinked) {
        this.onHostLeft();
        return;
      }
      this.netReconnects = (this.netReconnects || 0) + 1;
      if (this.netReconnects > 3) {
        ui.setJoinStatus('НЕТ СВЯЗИ С СЕРВЕРОМ · ПРОВЕРЬТЕ ИНТЕРНЕТ', 'err');
        ui.enableJoin(true);
        this.netRole = null;
        return;
      }
      ui.setJoinStatus('СВЯЗЬ С СЕРВЕРОМ ПОТЕРЯНА · ПЕРЕПОДКЛЮЧАЕМСЯ', 'err');
      this.netRetryTimer = setTimeout(() => {
        if (this.netRole === 'guest' && this.roomCode) this.startGuestConnection();
      }, 1200);
    }

    netApplyInput(msg) {
      if (this.netRole !== 'host' || this.mode !== 'net') return;
      const d = msg.d;
      if (!Array.isArray(d) || d.length !== 2) return;
      const dx = Number(d[0]);
      const dy = Number(d[1]);
      if (!Number.isInteger(dx) || !Number.isInteger(dy)) return;
      if (Math.abs(dx) + Math.abs(dy) !== 1) return;
      const guest = this.rivals.find((r) => !r.ai);
      if (!guest) return;
      const last = guest.queue.length ? guest.queue[guest.queue.length - 1] : guest.dir;
      if (same([dx, dy], last) || opposite([dx, dy], last)) return;
      if (guest.queue.length < 2) guest.queue.push([dx, dy]);
    }

    static parseCells(list) {
      if (!Array.isArray(list)) return [];
      const out = [];
      for (const c of list) {
        if (!Array.isArray(c) || c.length !== 2) continue;
        const x = Number(c[0]);
        const y = Number(c[1]);
        if (Number.isInteger(x) && Number.isInteger(y) && x >= 0 && y >= 0 &&
            x < COLS && y < ROWS) {
          out.push([x, y]);
        }
      }
      return out;
    }

    static validCell(c) {
      if (!Array.isArray(c) || c.length !== 2) return null;
      const x = Number(c[0]);
      const y = Number(c[1]);
      if (!Number.isInteger(x) || !Number.isInteger(y)) return null;
      if (x < 0 || y < 0 || x >= COLS || y >= ROWS) return null;
      return [x, y];
    }

    netHostSend(dt, force) {
      if (this.netRole !== 'host' || !this.netGuestLinked) return;
      if (!this.broker || !this.broker.connected) return;
      this.netSendTimer -= dt;
      if (this.netSendTimer > 0 && !force) return;
      this.netSendTimer = 0.1;
      const guest = this.rivals.find((r) => !r.ai);
      const p2 = guest ? {
        b: guest.body, pv: guest.prev, d: guest.dir, s: guest.score,
        a: guest.apples, st: guest.stars, pw: guest.powers
      } : { b: [], pv: [], d: [1, 0], s: 0, a: 0, st: 0, pw: 0 };
      const eff = {};
      for (const key of Object.keys(this.effects)) {
        if (this.effects[key] > 0) eff[key] = Math.round(this.effects[key] * 100) / 100;
      }
      this.netSend({
        t: 'state',
        p1: {
          b: this.snake, pv: this.prevSnake, d: this.dir, s: this.score,
          a: this.apples, st: this.stars, pw: this.powers
        },
        p2,
        food: this.food,
        sp: this.special ? {
          pos: this.special.pos,
          left: Math.round(this.special.left * 100) / 100,
          ttl: this.special.ttl
        } : null,
        pu: this.powerup ? {
          pos: this.powerup.pos, kind: this.powerup.kind,
          left: Math.round(this.powerup.left * 100) / 100,
          ttl: this.powerup.ttl
        } : null,
        eff,
        tl: this.timeLeft === null ? null : Math.round(this.timeLeft * 100) / 100,
        rt: Math.round(this.runTime * 100) / 100,
        iv: Math.round(this.interval * 10000) / 10000,
        cd: Math.max(0, Math.round(this.countdown * 10) / 10)
      });
    }

    applyNetState(msg) {
      if (this.netRole !== 'guest' || this.mode !== 'net' || this.state === 'dead') return;
      const p2 = msg.p2 && typeof msg.p2 === 'object' ? msg.p2 : {};
      const body = Game.parseCells(p2.b);
      const prev = Game.parseCells(p2.pv);
      if (body.length) {
        this.snake = body;
        this.prevSnake = prev.length ? prev : body.map((c) => c.slice());
      }
      const d2 = Game.validCell(Array.isArray(p2.d) ? p2.d : null);
      if (d2) this.dir = d2;
      this.score = Number.isFinite(Number(p2.s)) ? Number(p2.s) : this.score;
      this.apples = Number.isFinite(Number(p2.a)) ? Number(p2.a) : this.apples;
      this.stars = Number.isFinite(Number(p2.st)) ? Number(p2.st) : this.stars;
      this.powers = Number.isFinite(Number(p2.pw)) ? Number(p2.pw) : this.powers;

      const p1 = msg.p1 && typeof msg.p1 === 'object' ? msg.p1 : {};
      const hostBody = Game.parseCells(p1.b);
      const hostPrev = Game.parseCells(p1.pv);
      const hostSkin = SKIN_BY_ID[this.netHostSkin] || SKINS[0];
      if (!this.rivals.length) {
        this.rivals = [this.makeRival('ХОСТ', skinColorsAt(hostSkin, this.time), hostBody, [1, 0])];
        this.rivals[0].ai = false;
      }
      const rival = this.rivals[0];
      rival.skin = hostSkin.id;
      rival.cheats = cheatFlagsFromIds(this.netHostCheats);
      if (hostBody.length) {
        rival.body = hostBody;
        rival.prev = hostPrev.length ? hostPrev : hostBody.map((c) => c.slice());
      }
      const d1 = Game.validCell(Array.isArray(p1.d) ? p1.d : null);
      if (d1) rival.dir = d1;
      rival.score = Number.isFinite(Number(p1.s)) ? Number(p1.s) : rival.score;
      rival.apples = Number.isFinite(Number(p1.a)) ? Number(p1.a) : rival.apples;
      rival.stars = Number.isFinite(Number(p1.st)) ? Number(p1.st) : rival.stars;
      rival.powers = Number.isFinite(Number(p1.pw)) ? Number(p1.pw) : rival.powers;
      rival.alive = true;

      this.food = Game.validCell(msg.food);
      const sp = msg.sp;
      this.special = sp && Game.validCell(sp.pos) ? {
        pos: Game.validCell(sp.pos),
        left: Math.max(0, Number(sp.left) || 0),
        ttl: Number(sp.ttl) || 7.5
      } : null;
      const pu = msg.pu;
      this.powerup = pu && Game.validCell(pu.pos) ? {
        pos: Game.validCell(pu.pos),
        kind: POWER_KINDS.includes(pu.kind) ? pu.kind : 'shield',
        left: Math.max(0, Number(pu.left) || 0),
        ttl: Number(pu.ttl) || 9
      } : null;
      const tl = Number(msg.tl);
      this.timeLeft = Number.isFinite(tl) ? Math.max(0, tl) : null;
      const iv = Number(msg.iv);
      if (Number.isFinite(iv) && iv > 0.03) this.netInterval = clamp(iv, 0.05, 0.4);
      const cd = Number(msg.cd);
      this.netCountdown = Number.isFinite(cd) ? Math.max(0, cd) : 0;
      this.netHaveState = true;
      this.tRender = 0;
      this.updateHud();
    }

    applyNetOver(msg) {
      if (this.netRole !== 'guest' || this.state === 'dead') return;
      const winner = Number(msg.winner);
      this.netWinner = winner === 1 || winner === 2 ? winner : 0;
      this.netOver = true;
      this.netActive = false;
      this.score = Number.isFinite(Number(msg.s2)) ? Number(msg.s2) : this.score;
      if (this.rivals[0] && Number.isFinite(Number(msg.s1))) {
        this.rivals[0].score = Number(msg.s1);
      }
      this.deathReason = typeof msg.reason === 'string' ? msg.reason : 'crash';
      this.state = 'dead';
      this.deadAt = this.time;
      this.prevSnake = this.snake.map((c) => c.slice());
      this.tRender = 0;
      if (this.settings.shake) this.shake = 12;
      this.flash = 0.9;
      this.commitBest();
      if (this.netWinner === 2) { Sfx.play('win'); haptic([20, 50, 30, 50, 40]); }
      else { Sfx.play('die'); haptic([18, 40, 24]); }
      this.scheduleNetOverlay(500);
    }

    endNet(winner, reason) {
      if (this.mode !== 'net' || this.netRole !== 'host' || this.netOver) return;
      this.netOver = true;
      this.netActive = false;
      this.netWinner = winner;
      this.deathReason = reason || 'crash';
      const guest = this.rivals.find((r) => !r.ai);
      const s2 = guest ? guest.score : 0;
      if (this.state === 'playing' || this.state === 'countdown') this.state = 'dead';
      this.deadTimer = 0.7;
      if (winner === 1) { Sfx.play('win'); haptic([20, 50, 30, 50, 40]); }
      else { Sfx.play('die'); haptic([18, 40, 24]); }
      this.commitBest();
      this.netSend({
        t: 'over', winner, reason: this.deathReason,
        s1: this.score, s2
      });
      this.scheduleNetOverlay(750);
    }

    netClientFrame(dt) {
      this.tRender = Math.min(1, this.tRender + dt / Math.max(0.05, this.netInterval));
    }

    scheduleDeathOverlay(delay) {
      const token = ++this.overlayToken;
      setTimeout(() => {
        if (this.state === 'dead' && this.overlayToken === token && !this.netOver) {
          this.showDeathOverlay();
        }
      }, delay);
    }

    scheduleNetOverlay(delay) {
      const token = ++this.overlayToken;
      setTimeout(() => {
        if (this.state === 'dead' && this.overlayToken === token) {
          this.showNetOverlay();
        }
      }, delay);
    }

    /* ---------------------------------------------------------- отрисовка */
    bindResize() {
      const handler = () => this.resizeCanvas();
      window.addEventListener('resize', handler);
      window.addEventListener('orientationchange', () => setTimeout(handler, 120));
      if (window.ResizeObserver) {
        this.resizeObserver = new ResizeObserver(handler);
        this.resizeObserver.observe(this.wrapEl);
      }
    }

    resizeCanvas() {
      const rect = this.canvas.getBoundingClientRect();
      const w = Math.max(1, rect.width || this.wrapEl.clientWidth);
      const h = Math.max(1, rect.height || this.wrapEl.clientHeight);
      const dpr = Math.min(3, window.devicePixelRatio || 1);
      const pw = Math.round(w * dpr);
      const ph = Math.round(h * dpr);
      if (this.canvas.width !== pw || this.canvas.height !== ph) {
        this.canvas.width = pw;
        this.canvas.height = ph;
      }
      this.viewW = w;
      this.viewH = h;
    }

    render() {
      const ctx = this.ctx;
      const dpr = Math.min(3, window.devicePixelRatio || 1);
      if (!this.viewW) this.resizeCanvas();
      const w = this.viewW || 1;
      const h = this.viewH || 1;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const scale = Math.min(w / FIELD_W, h / FIELD_H) * 0.985;
      const shake = this.settings.shake ? this.shake : 0;
      const sx = shake ? rnd(-shake, shake) : 0;
      const sy = shake ? rnd(-shake, shake) : 0;
      const ox = (w - FIELD_W * scale) / 2 + sx;
      const oy = (h - FIELD_H * scale) / 2 + sy;
      ctx.setTransform(dpr * scale, 0, 0, dpr * scale, dpr * ox, dpr * oy);
      this.drawField(ctx);
      this.drawWalls(ctx);
      this.drawMeteors(ctx);
      this.drawFood(ctx);
      this.drawSpecial(ctx);
      this.drawPower(ctx);
      if (this.mode === 'bots' || this.mode === 'net') {
        for (const rival of this.rivals) this.drawRival(ctx, rival);
      }
      this.drawSnake(ctx);
      this.drawParticles(ctx);
      this.drawFloats(ctx);
      if (this.flash > 0) {
        ctx.fillStyle = 'rgba(255,220,255,' + (this.flash * 0.16).toFixed(3) + ')';
        roundRect(ctx, 0, 0, FIELD_W, FIELD_H, 10);
        ctx.fill();
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
    }

    drawField(ctx) {
      const outer = ctx.createLinearGradient(0, 0, FIELD_W, FIELD_H);
      outer.addColorStop(0, '#0a1528');
      outer.addColorStop(0.5, '#070e1b');
      outer.addColorStop(1, '#0a0d1f');
      ctx.save();
      ctx.shadowColor = 'rgba(63,208,255,0.20)';
      ctx.shadowBlur = 22;
      roundRect(ctx, 0, 0, FIELD_W, FIELD_H, 10);
      ctx.fillStyle = outer;
      ctx.fill();
      ctx.restore();

      if (this.settings.grid) {
        ctx.save();
        ctx.strokeStyle = 'rgba(126,249,255,0.055)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = 1; x < COLS; x += 1) {
          ctx.moveTo(x * CELL, 0);
          ctx.lineTo(x * CELL, FIELD_H);
        }
        for (let y = 1; y < ROWS; y += 1) {
          ctx.moveTo(0, y * CELL);
          ctx.lineTo(FIELD_W, y * CELL);
        }
        ctx.stroke();
        ctx.strokeStyle = 'rgba(126,249,255,0.08)';
        ctx.beginPath();
        for (let y = 0; y <= ROWS; y += 4) {
          ctx.moveTo(0, y * CELL);
          ctx.lineTo(FIELD_W, y * CELL);
        }
        for (let x = 0; x <= COLS; x += 4) {
          ctx.moveTo(x * CELL, 0);
          ctx.lineTo(x * CELL, FIELD_H);
        }
        ctx.stroke();
        ctx.restore();
      }

      const vignette = ctx.createRadialGradient(FIELD_W / 2, FIELD_H / 2, FIELD_H * 0.25,
        FIELD_W / 2, FIELD_H / 2, FIELD_W * 0.72);
      vignette.addColorStop(0, 'rgba(0,0,0,0)');
      vignette.addColorStop(1, 'rgba(0,0,0,0.38)');
      ctx.fillStyle = vignette;
      roundRect(ctx, 0, 0, FIELD_W, FIELD_H, 10);
      ctx.fill();

      ctx.save();
      ctx.translate(0.5, 0.5);
      roundRect(ctx, 0, 0, FIELD_W - 1, FIELD_H - 1, 10);
      ctx.strokeStyle = 'rgba(126,249,255,0.24)';
      ctx.lineWidth = 1.5;
      ctx.shadowColor = 'rgba(63,208,255,0.5)';
      ctx.shadowBlur = 12;
      ctx.stroke();
      ctx.restore();

      const corner = 16;
      ctx.strokeStyle = 'rgba(126,249,255,0.55)';
      ctx.lineWidth = 2;
      ctx.shadowColor = 'rgba(126,249,255,0.8)';
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.moveTo(4, 4 + corner); ctx.lineTo(4, 4); ctx.lineTo(4 + corner, 4);
      ctx.moveTo(FIELD_W - 4 - corner, 4); ctx.lineTo(FIELD_W - 4, 4); ctx.lineTo(FIELD_W - 4, 4 + corner);
      ctx.moveTo(4, FIELD_H - 4 - corner); ctx.lineTo(4, FIELD_H - 4); ctx.lineTo(4 + corner, FIELD_H - 4);
      ctx.moveTo(FIELD_W - 4 - corner, FIELD_H - 4); ctx.lineTo(FIELD_W - 4, FIELD_H - 4); ctx.lineTo(FIELD_W - 4, FIELD_H - 4 - corner);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    drawWalls(ctx) {
      if (!this.walls.size) return;
      ctx.save();
      ctx.shadowColor = 'rgba(176,107,255,0.55)';
      ctx.shadowBlur = 9;
      for (const key of this.walls) {
        const [x, y] = key.split(',').map(Number);
        const px = x * CELL + 2;
        const py = y * CELL + 2;
        roundRect(ctx, px, py, CELL - 4, CELL - 4, 4);
        ctx.fillStyle = 'rgba(52,26,92,0.85)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(176,107,255,0.8)';
        ctx.lineWidth = 1.2;
        ctx.stroke();
        ctx.strokeStyle = 'rgba(210,170,255,0.35)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(px + 4, py + CELL - 7);
        ctx.lineTo(px + CELL - 7, py + 4);
        ctx.stroke();
      }
      ctx.restore();
    }

    drawFood(ctx) {
      if (!this.food) return;
      const [x, y] = centerOf(this.food);
      const pulse = 0.86 + 0.14 * Math.sin(this.time * 5.2);
      ctx.save();
      const glow = ctx.createRadialGradient(x, y, 1, x, y, 19);
      glow.addColorStop(0, 'rgba(255,93,143,0.55)');
      glow.addColorStop(1, 'rgba(255,93,143,0)');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(x, y, 19, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowColor = 'rgba(255,77,157,0.9)';
      ctx.shadowBlur = 14;
      const body = ctx.createRadialGradient(x - 2.5, y - 3, 1, x, y, 9 * pulse);
      body.addColorStop(0, '#ffc2d8');
      body.addColorStop(0.45, '#ff5d8f');
      body.addColorStop(1, '#b3174f');
      ctx.fillStyle = body;
      ctx.beginPath();
      ctx.arc(x, y + 0.5, 8.2 * pulse, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = 'rgba(90,220,120,0.95)';
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(x + 1, y - 7);
      ctx.quadraticCurveTo(x + 5, y - 12, x + 8, y - 10);
      ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.beginPath();
      ctx.arc(x - 3, y - 2.5, 1.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    drawSpecial(ctx) {
      if (!this.special) return;
      const [x, y] = centerOf(this.special.pos);
      const pulse = 1 + 0.12 * Math.sin(this.time * 7);
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(this.time * 0.9);
      ctx.scale(pulse, pulse);
      const glow = ctx.createRadialGradient(0, 0, 2, 0, 0, 24);
      glow.addColorStop(0, 'rgba(255,210,74,0.55)');
      glow.addColorStop(1, 'rgba(255,210,74,0)');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(0, 0, 24, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowColor = 'rgba(255,210,74,0.95)';
      ctx.shadowBlur = 16;
      ctx.beginPath();
      for (let i = 0; i < 10; i += 1) {
        const r = i % 2 === 0 ? 10.5 : 4.6;
        const a = -Math.PI / 2 + i * Math.PI / 5;
        const px = Math.cos(a) * r;
        const py = Math.sin(a) * r;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      const grad = ctx.createLinearGradient(-8, -8, 8, 8);
      grad.addColorStop(0, '#fff6c8');
      grad.addColorStop(0.5, '#ffd24a');
      grad.addColorStop(1, '#ff9a4d');
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,240,180,0.9)';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }

    drawPower(ctx) {
      if (!this.powerup) return;
      const [x, y] = centerOf(this.powerup.pos);
      const info = EFFECT_INFO[this.powerup.kind] || EFFECT_INFO.shield;
      const pulse = 1 + 0.1 * Math.sin(this.time * 6);
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(pulse, pulse);
      const glow = ctx.createRadialGradient(0, 0, 2, 0, 0, 21);
      glow.addColorStop(0, rgba(info.color, 0.5));
      glow.addColorStop(1, rgba(info.color, 0));
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(0, 0, 21, 0, Math.PI * 2);
      ctx.fill();
      ctx.rotate(this.time * 0.6);
      ctx.beginPath();
      for (let i = 0; i < 6; i += 1) {
        const a = -Math.PI / 2 + i * Math.PI / 3;
        const px = Math.cos(a) * 9.5;
        const py = Math.sin(a) * 9.5;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = rgba(info.color, 0.22);
      ctx.strokeStyle = info.color;
      ctx.lineWidth = 1.6;
      ctx.shadowColor = info.color;
      ctx.shadowBlur = 12;
      ctx.fill();
      ctx.stroke();
      ctx.rotate(-this.time * 0.6);
      ctx.shadowBlur = 5;
      ctx.fillStyle = '#ffffff';
      ctx.font = '700 9px "Cascadia Mono", Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const letter = this.powerup.kind === 'shield' ? 'S' : (this.powerup.kind === 'double' ? '2' : 'M');
      ctx.fillText(letter, 0, 0.5);
      ctx.restore();
    }

    drawMeteors(ctx) {
      if (!this.meteors.size) return;
      ctx.save();
      for (const [key, left] of this.meteors) {
        const [x, y] = key.split(',').map(Number);
        const cx = x * CELL + CELL / 2;
        const cy = y * CELL + CELL / 2;
        const fading = left < 1.2;
        const alpha = fading ? 0.35 + 0.65 * Math.abs(Math.sin(left * 12)) : 1;
        ctx.globalAlpha = alpha;
        const glow = ctx.createRadialGradient(cx, cy, 2, cx, cy, 22);
        glow.addColorStop(0, 'rgba(255,154,77,0.55)');
        glow.addColorStop(1, 'rgba(255,154,77,0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(cx, cy, 22, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowColor = 'rgba(255,120,40,0.9)';
        ctx.shadowBlur = 12;
        ctx.beginPath();
        const spin = this.time * 1.8;
        for (let i = 0; i < 9; i += 1) {
          const a = spin + i * Math.PI * 2 / 9;
          const r = i % 2 === 0 ? 9.5 : 7;
          const px = cx + Math.cos(a) * r;
          const py = cy + Math.sin(a) * r;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        const grad = ctx.createRadialGradient(cx - 2, cy - 2, 1, cx, cy, 10);
        grad.addColorStop(0, '#ffe0b0');
        grad.addColorStop(0.5, '#ff9a4d');
        grad.addColorStop(1, '#7d2a0c');
        ctx.fillStyle = grad;
        ctx.fill();
      }
      ctx.restore();
    }

    lerpCell(from, to, t) {
      if (!from) return to;
      const dx = to[0] - from[0];
      const dy = to[1] - from[1];
      if (Math.abs(dx) > 1 || Math.abs(dy) > 1) return to;
      return [from[0] + dx * t, from[1] + dy * t];
    }

    snakePoints(prev, body, alpha) {
      const points = [];
      for (let i = 0; i < body.length; i += 1) {
        const from = prev[i] || prev[prev.length - 1] || body[i];
        const cell = this.lerpCell(from, body[i], alpha);
        points.push([cell[0] * CELL + CELL / 2, cell[1] * CELL + CELL / 2]);
      }
      return points;
    }

    drawSnake(ctx) {
      if (!this.snake.length) return;
      const alpha = this.state === 'playing' ? this.tRender : (this.state === 'dead' ? 1 : 0);
      const pts = this.snakePoints(this.prevSnake, this.snake, alpha);
      const colors = this.playerSkin
        ? skinColorsAt(this.playerSkin, this.time)
        : (this.playerColors || PLAYER_COLORS);
      this.playerColors = colors;
      this.drawSnakePath(ctx, pts, colors, this.dir, true,
        this.state === 'playing' || this.state === 'countdown');
    }

    drawRival(ctx, rival) {
      if (!rival.body.length) return;
      const alpha = this.state === 'playing' ? this.tRender : 1;
      const pts = this.snakePoints(rival.prev, rival.body, alpha);
      const colors = rival.skin ? skinColorsAt(rival.skin, this.time) : rival.colors;
      rival.colors = colors;
      this.drawSnakePath(ctx, pts, colors, rival.dir, false, rival.alive);
      if (!rival.alive) {
        ctx.save();
        ctx.globalAlpha = 0.55;
        ctx.fillStyle = rival.colors[1];
        ctx.font = '700 9px "Cascadia Mono", Consolas, monospace';
        ctx.textAlign = 'center';
        const [x, y] = pts[0];
        ctx.fillText('×', x, y + 3);
        ctx.restore();
      }
    }

    drawSnakePath(ctx, pts, colors, dir, isPlayer, alive) {
      if (!pts.length) return;
      const head = pts[0];
      const tail = pts[pts.length - 1];
      ctx.save();
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      if (!alive) ctx.globalAlpha = 0.45;
      const grad = ctx.createLinearGradient(head[0], head[1], tail[0], tail[1]);
      grad.addColorStop(0, colors[0]);
      grad.addColorStop(0.45, colors[1]);
      grad.addColorStop(1, colors[2]);

      ctx.strokeStyle = grad;
      ctx.shadowColor = colors[1];
      ctx.shadowBlur = isPlayer ? 18 : 14;
      ctx.lineWidth = CELL * 0.72;
      ctx.globalAlpha *= 0.28;
      this.strokePoints(ctx, pts);
      ctx.globalAlpha = alive ? 1 : 0.4;
      ctx.shadowBlur = isPlayer ? 10 : 7;
      ctx.lineWidth = CELL * 0.48;
      this.strokePoints(ctx, pts);

      ctx.globalAlpha = alive ? 1 : 0.4;
      ctx.shadowBlur = 0;
      ctx.lineWidth = CELL * 0.16;
      ctx.strokeStyle = rgba(colors[0], 0.55);
      this.strokePoints(ctx, pts);

      const r = CELL * 0.36;
      const headGrad = ctx.createRadialGradient(head[0] - 2, head[1] - 2, 1, head[0], head[1], r);
      headGrad.addColorStop(0, '#ffffff');
      headGrad.addColorStop(0.25, colors[0]);
      headGrad.addColorStop(1, colors[1]);
      ctx.fillStyle = headGrad;
      ctx.shadowColor = colors[0];
      ctx.shadowBlur = isPlayer ? 16 : 11;
      ctx.beginPath();
      ctx.arc(head[0], head[1], r, 0, Math.PI * 2);
      ctx.fill();

      const d = dir || [1, 0];
      const eyeBack = 2.6;
      const eyeSide = 4.1;
      const ex = head[0] + d[0] * eyeBack;
      const ey = head[1] + d[1] * eyeBack;
      const px = -d[1] * eyeSide;
      const py = d[0] * eyeSide;
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#04101c';
      ctx.beginPath();
      ctx.arc(ex + px, ey + py, 2.15, 0, Math.PI * 2);
      ctx.arc(ex - px, ey - py, 2.15, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.beginPath();
      ctx.arc(ex + px + 0.7, ey + py - 0.7, 0.8, 0, Math.PI * 2);
      ctx.arc(ex - px + 0.7, ey - py - 0.7, 0.8, 0, Math.PI * 2);
      ctx.fill();

      if (isPlayer && (this.effects.shield || 0) > 0) {
        ctx.strokeStyle = rgba(CYAN, 0.75);
        ctx.lineWidth = 1.6;
        ctx.shadowColor = CYAN;
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(head[0], head[1], r + 5.5 + Math.sin(this.time * 7) * 1.2, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();
    }

    strokePoints(ctx, pts) {
      if (pts.length === 1) {
        ctx.beginPath();
        ctx.arc(pts[0][0], pts[0][1], CELL * 0.24, 0, Math.PI * 2);
        ctx.fillStyle = ctx.strokeStyle;
        ctx.fill();
        return;
      }
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length; i += 1) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.stroke();
    }

    drawParticles(ctx) {
      if (!fx.particles.length) return;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (const p of fx.particles) {
        const alpha = clamp(p.life / p.max, 0, 1);
        ctx.globalAlpha = alpha;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (0.4 + alpha * 0.6), 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    drawFloats(ctx) {
      if (!fx.rings.length && !fx.floats.length) return;
      ctx.save();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      for (const r of fx.rings) {
        const p = 1 - r.life / r.max;
        ctx.globalAlpha = 1 - p;
        ctx.strokeStyle = r.color;
        ctx.lineWidth = 2.2;
        ctx.shadowColor = r.color;
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(r.x, r.y, 6 + r.rmax * p, 0, Math.PI * 2);
        ctx.stroke();
      }
      for (const f of fx.floats) {
        const alpha = clamp(f.life / f.max, 0, 1);
        ctx.globalAlpha = Math.min(1, alpha * 1.5);
        ctx.fillStyle = f.color;
        ctx.shadowColor = f.color;
        ctx.shadowBlur = f.big ? 18 : 10;
        ctx.font = (f.big ? '800 20px' : '700 14px') +
          ' "Cascadia Mono", Consolas, monospace';
        ctx.fillText(f.text, f.x, f.y);
      }
      ctx.restore();
    }

    /* ---------------------------------------------------------- HUD и экраны */
    updateHud() {
      const score = Math.max(0, Math.floor(this.score));
      const stored = store.bests[this.mode] || 0;
      const shownBest = Math.max(stored, score);
      ui.setText($('#hud-score'), String(score));
      ui.setText($('#hud-best'), String(shownBest));
      ui.setText($('#hud-mode'), this.mode === 'net' ? 'СЕТЬ' : MODE_BY_ID[this.mode].name);

      let timerText = '';
      if (this.timeLeft !== null) {
        const secs = Math.max(0, Math.ceil(this.timeLeft));
        timerText = Math.floor(secs / 60) + ':' + pad2(secs % 60);
      }
      ui.setTimer(timerText, this.timeLeft !== null && this.timeLeft <= 10);

      let sub = MODE_BY_ID[this.mode].hint;
      if (this.state === 'countdown') sub = 'ПРИГОТОВЬСЯ';
      else if (this.state === 'dead') sub = this.deathReason === 'time' ? 'ВРЕМЯ ВЫШЛО' : 'ИГРА ОКОНЧЕНА';
      else if (this.mode === 'net' && this.netRole === 'guest' && !this.netHaveState) {
        sub = 'СОЕДИНЕНИЕ…';
      } else if (this.mode === 'net' && this.netRole === 'host' && !this.netGuestLinked) {
        sub = 'ЖДЁМ СОПЕРНИКА';
      }
      ui.setText($('#hud-sub'), sub);

      let countdown = '';
      if (this.state === 'countdown') countdown = String(Math.max(1, Math.ceil(this.countdown)));
      else if (this.mode === 'net' && this.netRole === 'guest' && this.netCountdown > 0) {
        countdown = String(Math.max(1, Math.ceil(this.netCountdown)));
      }
      ui.showCountdown(countdown);
      if (countdown) {
        const value = Number(countdown);
        if (value !== this.lastCountdown) {
          this.lastCountdown = value;
          if (value <= 3) { Sfx.play('count'); haptic(8); }
        }
      } else {
        this.lastCountdown = 0;
      }

      this.updateRivalsBar();
      this.updateFxChips();
    }

    updateRivalsBar() {
      const bar = $('#rivals-bar');
      const show = this.mode === 'bots' || this.mode === 'net';
      if (!show) {
        bar.classList.add('hidden');
        this._rivalSig = '';
        return;
      }
      bar.classList.remove('hidden');
      const entries = [{
        name: 'ВЫ', score: Math.floor(this.score), colors: this.playerColors || PLAYER_COLORS,
        me: true, alive: this.state !== 'dead'
      }];
      for (const rival of this.rivals) {
        entries.push({
          name: rival.name, score: Math.floor(rival.score), colors: rival.colors,
          me: false, alive: rival.alive
        });
      }
      const sig = this.mode + '|' + entries.map((e) => e.name + ':' + e.score + ':' + (e.alive ? 1 : 0)).join('|');
      if (sig === this._rivalSig) return;
      this._rivalSig = sig;
      bar.innerHTML = entries.map((e) => (
        '<div class="rival-chip' + (e.me ? ' me' : '') + (e.alive ? '' : ' dead') +
        '" style="--c:' + e.colors[1] + '">' +
        '<span class="rname">' + (e.me ? 'ВЫ' : e.name) + '</span>' +
        '<span class="rscore">' + e.score + '</span></div>'
      )).join('');
    }

    updateFxChips() {
      const box = $('#fx-chips');
      const showEffects = this.mode !== 'net' || this.netRole !== 'guest';
      const active = [];
      if (showEffects) {
        for (const key of Object.keys(EFFECT_INFO)) {
          const value = this.effects[key] || 0;
          if (value > 0) active.push({ key, value, info: EFFECT_INFO[key] });
        }
      }
      for (const cheat of CHEATS) {
        if (this.cheats && this.cheats[cheat.id]) {
          active.push({
            key: 'cheat-' + cheat.id, value: 0, cheat: true,
            info: { label: cheat.chip, color: GOLD }
          });
        }
      }
      const sig = active.map((e) => e.key + Math.ceil(e.value)).join('|');
      if (sig === this._fxSig) return;
      this._fxSig = sig;
      box.innerHTML = active.map((e) => (
        '<span class="fx-chip' + (e.cheat ? ' fx-cheat' : '') +
        '" style="--c:' + e.info.color + '">' +
        (e.cheat ? 'ЧИТ ' : '') + e.info.label +
        (e.cheat ? '' : ' <b>' + Math.ceil(e.value) + '</b>') + '</span>'
      )).join('');
    }

    refreshBests() {
      for (const el of $$('[data-best]')) {
        const mode = el.dataset.best;
        if (mode && store.bests[mode] !== undefined) {
          el.textContent = String(store.bests[mode]);
        }
      }
    }

    startMode(mode) {
      this.session += 1;
      this.overlayToken = (this.overlayToken || 0) + 1;
      this.netOver = false;
      if (mode === 'net') {
        ui.openNetScreen();
        return;
      }
      this.closeNet();
      ui.hideOverlay();
      this.resetGame(mode);
      ui.showScreen('game');
      this.resizeCanvas();
      this.countdown = 3;
      this.state = 'countdown';
      this.deadTimer = 0;
      this.lastCountdown = 0;
      this.tRender = 0;
      this.acc = 0;
      ui.setHudMode(MODE_BY_ID[mode].name);
      ui.showTimer(mode === 'blitz');
      ui.setSub('ПРИГОТОВЬСЯ');
      this.updateHud();
      Sfx.play('menu');
      haptic(12);
      setTimeout(() => this.resizeCanvas(), 60);
    }

    pause() {
      if (this.mode === 'net') {
        if (this.state === 'playing' || this.state === 'countdown') this.showNetLeaveOverlay();
        return;
      }
      if (this.state !== 'playing' && this.state !== 'countdown') return;
      this.resumeState = this.state;
      this.state = 'paused';
      this.showPauseOverlay();
      Sfx.play('menu');
    }

    resume() {
      if (this.state !== 'paused') return;
      this.state = this.resumeState || 'playing';
      if (this.state === 'countdown') this.countdown = Math.max(0.6, this.countdown);
      ui.hideOverlay();
      Sfx.play('menu');
    }

    showPauseOverlay() {
      ui.showOverlay(
        '<p class="overlay-kicker">ПАУЗА</p>' +
        '<h3>ПЕРЕДЫШКА</h3>' +
        '<div class="overlay-score">' + Math.floor(this.score) + '<small>ОЧКОВ</small></div>' +
        '<p class="overlay-text">' + MODE_BY_ID[this.mode].name + ' · ' +
        Math.floor(this.runTime) + ' СЕК</p>' +
        '<div class="overlay-actions">' +
        '<button class="btn btn-primary" id="ov-resume">ПРОДОЛЖИТЬ</button>' +
        '<button class="btn" id="ov-restart">ЗАНОВО</button>' +
        '<button class="btn btn-ghost" id="ov-menu">В МЕНЮ</button>' +
        '</div>'
      );
      $('#ov-resume').addEventListener('click', () => this.resume());
      $('#ov-restart').addEventListener('click', () => this.startMode(this.mode));
      $('#ov-menu').addEventListener('click', () => {
        this.closeNet();
        this.state = 'idle';
        ui.hideOverlay();
        ui.showScreen('menu');
      });
    }

    showDeathOverlay() {
      const timeUp = this.deathReason === 'time';
      const title = timeUp ? 'ВРЕМЯ ВЫШЛО' : 'ЗМЕЙКА РАЗБИЛАСЬ';
      const kicker = MODE_BY_ID[this.mode].name;
      const record = this.newRecord ? '<span class="overlay-record">НОВЫЙ РЕКОРД!</span>' : '';
      const reward = this.rewardCoins
        ? '<p class="overlay-reward">+ ' + this.rewardCoins + ' ◆ НЕОНОВ' +
          (this.rewardRecordBonus ? ' · РЕКОРД +' + this.rewardRecordBonus : '') + '</p>'
        : '';
      const stats = 'ЯБЛОК: ' + this.apples + ' · ЗВЁЗД: ' + this.stars +
        ' · БОНУСОВ: ' + this.powers + ' · КОМБО ×' + this.maxCombo;
      ui.showOverlay(
        '<p class="overlay-kicker">' + kicker + '</p>' +
        '<h3>' + title + '</h3>' +
        record +
        '<div class="overlay-score">' + Math.floor(this.score) + '<small>ОЧКОВ</small></div>' +
        '<p class="overlay-text">' + stats + '</p>' +
        '<p class="overlay-text">РЕКОРД: ' + (store.bests[this.mode] || 0) + '</p>' +
        reward +
        '<div class="overlay-actions">' +
        '<button class="btn btn-primary" id="ov-again">ЕЩЁ РАЗ</button>' +
        '<button class="btn" id="ov-modes">СМЕНИТЬ РЕЖИМ</button>' +
        '<button class="btn btn-ghost" id="ov-menu">В МЕНЮ</button>' +
        '</div>'
      );
      $('#ov-again').addEventListener('click', () => this.startMode(this.mode));
      $('#ov-modes').addEventListener('click', () => {
        ui.hideOverlay();
        this.state = 'idle';
        ui.showScreen('modes');
      });
      $('#ov-menu').addEventListener('click', () => {
        ui.hideOverlay();
        this.state = 'idle';
        ui.showScreen('menu');
      });
    }

    showNetOverlay() {
      const guest = this.netRole === 'guest';
      const myWinner = guest ? 2 : 1;
      const opp = this.rivals[0];
      const myScore = Math.floor(this.score);
      const oppScore = opp ? Math.floor(opp.score) : 0;
      const won = this.netWinner === myWinner;
      let title;
      let kicker = 'СЕТЕВОЙ МАТЧ';
      if (this.netLost) {
        title = 'СВЯЗЬ ПОТЕРЯНА';
        kicker = 'СЕТЬ';
      } else if (!this.netWinner) {
        title = 'МАТЧ ОКОНЧЕН';
      } else {
        title = won ? 'ПОБЕДА' : 'ПОРАЖЕНИЕ';
      }
      const reasons = {
        time: 'ВРЕМЯ ВЫШЛО',
        crash: guest ? 'ХОСТ РАЗБИЛСЯ' : 'ВЫ РАЗБИЛИСЬ',
        rival: guest ? 'ВЫ РАЗБИЛИСЬ' : 'СОПЕРНИК РАЗБИЛСЯ',
        lost: guest ? 'СВЯЗЬ ПОТЕРЯНА' : 'СОПЕРНИК ОТКЛЮЧИЛСЯ'
      };
      let reasonText = reasons[this.deathReason] || '';
      if (!this.netLost && !this.netWinner) reasonText = '';
      const record = this.newRecord ? '<span class="overlay-record">НОВЫЙ РЕКОРД!</span>' : '';
      const reward = this.rewardCoins
        ? '<p class="overlay-reward">+ ' + this.rewardCoins + ' ◆ НЕОНОВ' +
          (this.rewardRecordBonus ? ' · РЕКОРД +' + this.rewardRecordBonus : '') + '</p>'
        : '';
      const canRematch = !this.netLost && this.canReachPeer();
      const again = canRematch ? '<button class="btn btn-primary" id="ov-again">ЕЩЁ РАЗ</button>' : '';
      ui.showOverlay(
        '<p class="overlay-kicker">' + kicker + '</p>' +
        '<h3>' + title + '</h3>' +
        '<p class="overlay-text">' + reasonText + '</p>' +
        record +
        reward +
        '<div class="overlay-vs">' +
        '<div><span>ВЫ</span><b>' + myScore + '</b></div>' +
        '<span class="vs-sign">VS</span>' +
        '<div><span>' + (guest ? 'ХОСТ' : 'ГОСТЬ') + '</span><b>' + oppScore + '</b></div>' +
        '</div>' +
        '<div class="overlay-actions">' +
        again +
        '<button class="btn' + (canRematch ? '' : ' btn-primary') + '" id="ov-modes">СМЕНИТЬ РЕЖИМ</button>' +
        '<button class="btn btn-ghost" id="ov-menu">В МЕНЮ</button>' +
        '</div>'
      );
      if (canRematch) {
        $('#ov-again').addEventListener('click', () => {
          if (!this.canReachPeer()) {
            ui.toast('СОПЕРНИК УЖЕ ОТКЛЮЧИЛСЯ');
            return;
          }
          if (guest) {
            this.netSend(Object.assign({ t: 'rematch' }, loadoutPayload()));
            ui.toast('ОЖИДАЕМ ХОСТА…');
          } else {
            this.netSend({ t: 'again' });
            this.beginNetMatch();
          }
        });
      }
      $('#ov-modes').addEventListener('click', () => {
        this.closeNet();
        this.state = 'idle';
        ui.hideOverlay();
        ui.showScreen('modes');
      });
      $('#ov-menu').addEventListener('click', () => {
        this.closeNet();
        this.state = 'idle';
        ui.hideOverlay();
        ui.showScreen('menu');
      });
    }

    showNetLeaveOverlay() {
      ui.showOverlay(
        '<p class="overlay-kicker">СЕТЕВОЙ МАТЧ</p>' +
        '<h3>ВЫЙТИ ИЗ ИГРЫ?</h3>' +
        '<p class="overlay-text">В сети нет паузы. Соединение закроется, соперник получит техническое поражение.</p>' +
        '<div class="overlay-actions">' +
        '<button class="btn btn-primary" id="ov-resume">ПРОДОЛЖИТЬ</button>' +
        '<button class="btn btn-ghost" id="ov-leave">ВЫЙТИ В МЕНЮ</button>' +
        '</div>'
      );
      $('#ov-resume').addEventListener('click', () => ui.hideOverlay());
      $('#ov-leave').addEventListener('click', () => {
        this.closeNet();
        this.state = 'idle';
        ui.hideOverlay();
        ui.showScreen('menu');
      });
    }



  }

  /* ================================================================ интерфейс */
  const ui = {
    screen: 'menu',
    roomCode: '',
    toastTimer: 0,
    overlay: $('#overlay'),
    overlayCard: $('#overlay-card'),
    toastEl: $('#toast'),

    showScreen(name) {
      for (const screen of $$('.screen')) {
        screen.classList.toggle('active', screen.dataset.screen === name);
      }
      this.screen = name;
      if (name === 'menu') {
        game.refreshBests();
        this.refreshWallet();
      } else if (name === 'shop') {
        this.renderShop();
      }
    },

    refreshWallet() {
      const coins = String(store.coins);
      const menuCoins = $('#coin-balance');
      const shopCoins = $('#shop-coins');
      if (menuCoins) menuCoins.textContent = coins;
      if (shopCoins) shopCoins.textContent = coins;
      const dot = $('#daily-dot');
      if (dot) dot.classList.toggle('hidden', dailyStatus().claimedToday);
      if (this.screen === 'shop') this.renderDailyCard();
    },

    renderDailyCard() {
      const card = $('#daily-card');
      if (!card) return;
      const daily = dailyStatus();
      const note = $('#daily-note');
      const btn = $('#daily-btn');
      if (daily.claimedToday) {
        if (note) note.textContent = 'Серия: ' + daily.streak + ' дн. Следующий бонус — завтра.';
        if (btn) {
          btn.disabled = true;
          btn.textContent = 'ПОЛУЧЕНО';
        }
      } else {
        if (note) {
          note.textContent = 'Серия: ' + daily.nextStreak +
            ' дн. · награда ' + daily.reward + ' ◆';
        }
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'ЗАБРАТЬ ' + daily.reward + ' ◆';
        }
      }
    },

    claimDaily() {
      const daily = dailyStatus();
      if (daily.claimedToday) {
        this.toast('БОНУС УЖЕ ПОЛУЧЕН СЕГОДНЯ');
        return;
      }
      store.daily = { last: localDateKey(), streak: daily.nextStreak };
      addCoins(daily.reward);
      Sfx.play('special');
      haptic(20);
      this.toast('ЕЖЕДНЕВНЫЙ БОНУС +' + daily.reward + ' ◆', 3000);
      this.renderShop();
    },

    renderShop() {
      this.renderDailyCard();
      this.renderShopSkins();
      this.renderShopCheats();
      this.refreshWallet();
      this.setShopTab(this.shopTab || 'skins');
    },

    renderShopSkins() {
      const list = $('#skin-list');
      if (!list) return;
      list.innerHTML = SKINS.map((skin) => {
        const owned = store.skins.includes(skin.id);
        const equipped = store.skin === skin.id;
        let label;
        let cls = 'shop-buy';
        let attr;
        if (equipped) {
          label = 'ВЫБРАН';
          cls += ' equipped';
          attr = 'data-equip-skin="' + skin.id + '" disabled';
        } else if (owned) {
          label = 'ВЫБРАТЬ';
          cls += ' owned';
          attr = 'data-equip-skin="' + skin.id + '"';
        } else {
          label = 'КУПИТЬ · ' + skin.price + ' ◆';
          cls += ' buy';
          attr = 'data-buy-skin="' + skin.id + '"';
        }
        return '<article class="shop-item' + (equipped ? ' equipped' : (owned ? ' owned' : '')) + '">' +
          '<div class="skin-preview" style="--s0:' + skin.colors[0] +
          ';--s1:' + skin.colors[1] + ';--s2:' + skin.colors[2] + '"></div>' +
          '<div class="shop-item-body"><b>' + skin.name + '</b><small>' + skin.desc + '</small></div>' +
          '<button class="' + cls + '" ' + attr + '>' + label + '</button></article>';
      }).join('');
    },

    renderShopCheats() {
      const list = $('#cheat-list');
      if (!list) return;
      list.innerHTML = CHEATS.map((cheat) => {
        const owned = store.ownedCheats.includes(cheat.id);
        const active = owned && !!store.cheats[cheat.id];
        let label;
        let cls = 'shop-buy';
        let attr;
        if (!owned) {
          label = 'КУПИТЬ · ' + cheat.price + ' ◆';
          cls += ' buy';
          attr = 'data-buy-cheat="' + cheat.id + '"';
        } else if (active) {
          label = 'ВКЛ';
          cls += ' cheat-on';
          attr = 'data-toggle-cheat="' + cheat.id + '"';
        } else {
          label = 'ВЫКЛ';
          cls += ' cheat-off';
          attr = 'data-toggle-cheat="' + cheat.id + '"';
        }
        return '<article class="shop-item' + (owned ? ' owned' : '') + '">' +
          '<div class="cheat-icon">' + cheat.icon + '</div>' +
          '<div class="shop-item-body"><b>' + cheat.name + '</b><small>' +
          cheat.desc + '</small></div>' +
          '<button class="' + cls + '" ' + attr + '>' + label + '</button></article>';
      }).join('');
    },

    setShopTab(tab) {
      this.shopTab = tab;
      for (const btn of $$('.shop-tab')) {
        btn.classList.toggle('active', btn.dataset.shoptab === tab);
      }
      $('#shop-skins-panel').classList.toggle('hidden', tab !== 'skins');
      $('#shop-cheats-panel').classList.toggle('hidden', tab !== 'cheats');
      $('#shop-codes-panel').classList.toggle('hidden', tab !== 'codes');
    },

    buySkin(id) {
      const skin = SKIN_BY_ID[id];
      if (!skin) return;
      if (store.skins.includes(id)) {
        store.skin = id;
        saveStore();
        this.renderShop();
        this.toast('СКИН: ' + skin.name);
        return;
      }
      if (store.coins < skin.price) {
        this.toast('НЕ ХВАТАЕТ НЕОНОВ: НУЖНО ' + skin.price + ' ◆', 3000);
        return;
      }
      store.coins -= skin.price;
      store.skins.push(id);
      store.skin = id;
      saveStore();
      this.renderShop();
      Sfx.play('special');
      haptic(16);
      this.toast('КУПЛЕНО: ' + skin.name, 2600);
    },

    buyCheat(id) {
      const cheat = CHEAT_BY_ID[id];
      if (!cheat) return;
      if (store.ownedCheats.includes(id)) {
        store.cheats[id] = !store.cheats[id];
        saveStore();
        this.renderShopCheats();
        this.toast(store.cheats[id] ? 'ЧИТ ВКЛЮЧЁН: ' + cheat.name : 'ЧИТ ВЫКЛЮЧЕН');
        return;
      }
      if (store.coins < cheat.price) {
        this.toast('НЕ ХВАТАЕТ НЕОНОВ: НУЖНО ' + cheat.price + ' ◆', 3000);
        return;
      }
      store.coins -= cheat.price;
      store.ownedCheats.push(id);
      store.cheats[id] = true;
      saveStore();
      this.renderShop();
      Sfx.play('special');
      haptic(16);
      this.toast('ЧИТ ОТКРЫТ: ' + cheat.name, 2800);
    },

    redeemCode() {
      const input = $('#promo-input');
      const status = $('#code-status');
      if (!input) return;
      const code = String(input.value || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 24);
      input.value = code;
      if (status) status.className = 'code-status';
      if (code.length < 3) {
        if (status) {
          status.textContent = 'ВВЕДИТЕ КОД';
          status.className = 'code-status err';
        }
        return;
      }
      if (store.usedCodes.includes(code)) {
        if (status) {
          status.textContent = 'ЭТОТ КОД УЖЕ ИСПОЛЬЗОВАН';
          status.className = 'code-status err';
        }
        return;
      }
      const promo = PROMO_CODES[code];
      if (!promo) {
        if (status) {
          status.textContent = 'НЕВЕРНЫЙ КОД';
          status.className = 'code-status err';
        }
        haptic(10);
        return;
      }
      const rewards = [];
      let coinsGain = Number(promo.coins) || 0;
      if (promo.skin) {
        const skin = SKIN_BY_ID[promo.skin];
        if (unlockSkin(promo.skin)) {
          rewards.push('СКИН ' + skin.name);
        } else {
          coinsGain += Math.max(50, Math.floor(skin.price / 2));
          rewards.push('КОМПЕНСАЦИЯ ' + Math.max(50, Math.floor(skin.price / 2)) + ' ◆');
        }
      }
      if (promo.cheat) {
        const cheat = CHEAT_BY_ID[promo.cheat];
        if (unlockCheat(promo.cheat)) {
          rewards.push('ЧИТ ' + cheat.name);
        } else {
          coinsGain += Math.max(50, Math.floor(cheat.price / 2));
          rewards.push('КОМПЕНСАЦИЯ ' + Math.max(50, Math.floor(cheat.price / 2)) + ' ◆');
        }
      }
      if (coinsGain > 0) {
        store.coins += coinsGain;
        rewards.unshift('+' + coinsGain + ' ◆');
      }
      store.usedCodes.push(code);
      saveStore();
      input.value = '';
      this.renderShop();
      Sfx.play('special');
      haptic(20);
      if (status) {
        status.textContent = 'КОД АКТИВИРОВАН: ' + rewards.join(' · ');
        status.className = 'code-status ok';
      }
      this.toast('КОД АКТИВИРОВАН', 2600);
    },

    showOverlay(html) {
      this.overlayCard.innerHTML = html;
      this.overlay.classList.remove('hidden');
    },

    hideOverlay() {
      this.overlay.classList.add('hidden');
      this.overlayCard.innerHTML = '';
    },

    setText(el, text) {
      if (el && el.textContent !== text) el.textContent = text;
    },

    setHudMode(text) {
      this.setText($('#hud-mode'), text);
    },

    setSub(text) {
      this.setText($('#hud-sub'), text);
    },

    setTimer(text, low) {
      const el = $('#hud-timer');
      if (!el) return;
      if (!text) {
        el.classList.add('hidden');
        el.classList.remove('low');
        return;
      }
      el.classList.remove('hidden');
      el.classList.toggle('low', !!low);
      this.setText(el, text);
    },

    showTimer(show) {
      const el = $('#hud-timer');
      if (!show) { el.classList.add('hidden'); el.classList.remove('low'); }
    },

    showCountdown(value) {
      const el = $('#countdown');
      if (!el) return;
      if (!value) {
        el.classList.add('hidden');
        el.textContent = '';
        return;
      }
      el.classList.remove('hidden');
      if (el.textContent !== value) {
        el.textContent = value;
        el.style.animation = 'none';
        void el.offsetWidth;
        el.style.animation = '';
      }
    },

    setRoomCode(code) {
      this.roomCode = code || '';
      this.setText($('#room-code'), code || '•••••');
    },

    setHostStatus(text, cls) {
      const el = $('#host-status');
      el.textContent = text;
      el.className = 'net-status' + (cls ? ' ' + cls : '');
    },

    setJoinStatus(text, cls) {
      const el = $('#join-status');
      el.textContent = text;
      el.className = 'net-status' + (cls ? ' ' + cls : '');
    },

    enableHost(enabled, label) {
      const btn = $('#net-host-btn');
      if (!btn) return;
      btn.disabled = !enabled;
      btn.textContent = label || (enabled ? 'СОЗДАТЬ КОМНАТУ' : 'СОЗДАНИЕ…');
    },

    enableJoin(enabled, label) {
      const btn = $('#net-join-btn');
      if (!btn) return;
      btn.disabled = !enabled;
      btn.textContent = label || (enabled ? 'ПОДКЛЮЧИТЬСЯ' : 'ПОДКЛЮЧЕНИЕ…');
    },

    setShare(enabled) {
      const btn = $('#net-share');
      if (btn) btn.disabled = !enabled;
    },

    showNetTab(tab) {
      $$('.net-tab').forEach((btn) => btn.classList.toggle('active', btn.dataset.nettab === tab));
      $('#net-host-panel').classList.toggle('hidden', tab !== 'host');
      $('#net-join-panel').classList.toggle('hidden', tab !== 'join');
      if (tab === 'join') setTimeout(() => $('#room-input').focus(), 120);
    },

    resetNet() {
      this.setRoomCode('');
      this.setHostStatus('Нажмите «Создать комнату»', '');
      this.enableHost(true);
      this.setShare(false);
      const input = $('#room-input');
      if (input) input.value = '';
      this.setJoinStatus('Пять символов: буквы и цифры', '');
      this.enableJoin(true);
      this.showNetTab('host');
    },

    openNetScreen() {
      game.closeNet();
      game.state = 'idle';
      this.resetNet();
      this.showScreen('net');
    },

    toast(text, ms) {
      clearTimeout(this.toastTimer);
      this.toastEl.textContent = text;
      this.toastEl.classList.remove('hidden');
      this.toastTimer = setTimeout(() => this.toastEl.classList.add('hidden'), ms || 2200);
    },

    shareRoom() {
      const code = this.roomCode;
      if (!code) return;
      const url = location.href.split('#')[0].split('?')[0];
      const text = 'NEON SNAKE · код комнаты ' + code + '\n' + url;
      if (navigator.share) {
        navigator.share({ title: 'NEON SNAKE', text }).catch((err) => {
          if (err && err.name === 'AbortError') return;
          this.copyCode(text);
        });
        return;
      }
      this.copyCode(text);
    },

    copyCode(text) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
          this.toast('КОД СКОПИРОВАН');
        }).catch(() => {
          this.toast('КОД: ' + this.roomCode, 4000);
        });
      } else {
        this.toast('КОД: ' + this.roomCode, 4000);
      }
    },

    showHowTo() {
      this.showOverlay(
        '<p class="overlay-kicker">NEON SNAKE</p>' +
        '<h3>КАК ИГРАТЬ</h3>' +
        '<p class="overlay-text" style="text-align:left">' +
        '<b style="color:#bff6ff">УПРАВЛЕНИЕ</b><br>' +
        'Свайп по полю или стрелки D-pad. На клавиатуре — стрелки, WASD или ЦФЫВ.<br>' +
        'Пауза — кнопка Ⅱ, клавиши P или ПРОБЕЛ.' +
        '</p>' +
        '<p class="overlay-text" style="text-align:left">' +
        '<b style="color:#ffd0dd">ЯБЛОКИ И КОМБО</b><br>' +
        'Каждое яблоко даёт очки и растит змейку. Успевай есть подряд — множитель комбо до ×5.' +
        '</p>' +
        '<p class="overlay-text" style="text-align:left">' +
        '<b style="color:#ffd24a">ЗОЛОТАЯ ЗВЕЗДА</b><br>' +
        'Редкий бонус: много очков и мгновенный рост. Появляется после серии яблок и исчезает через несколько секунд.' +
        '</p>' +
        '<p class="overlay-text" style="text-align:left">' +
        '<b style="color:#7ef9ff">БОНУСЫ</b><br>' +
        'S — щит: проходишь сквозь стены и хвост. 2 — двойные очки. M — замедление.' +
        '</p>' +
        '<p class="overlay-text" style="text-align:left">' +
        '<b style="color:#b06bff">РЕЖИМЫ</b><br>' +
        'Классика, лабиринт, блиц 60 секунд, хаос с метеоритами, два бота-соперника и сеть по коду комнаты.' +
        '</p>' +
        '<p class="overlay-text" style="text-align:left">' +
        '<b style="color:#ffd24a">НЕОНЫ И МАГАЗИН</b><br>' +
        'Играй, ставь рекорды, побеждай в сети и забирай ежедневный бонус. На неоны покупай скины, читы и открывай секретные коды.' +
        '</p>' +
        '<div class="overlay-actions">' +
        '<button class="btn btn-primary" id="ov-close">ПОНЯТНО</button>' +
        '</div>'
      );
      $('#ov-close').addEventListener('click', () => this.hideOverlay());
    },

    showInstall() {
      const ios = isIos();
      const steps = ios
        ? 'В Safari нажмите «Поделиться» (квадрат со стрелкой), затем «На экран „Домой“» и «Добавить».'
        : 'В Chrome нажмите ⋮ в правом верхнем углу, выберите «Установить приложение» или «Добавить на главный экран».';
      this.showOverlay(
        '<p class="overlay-kicker">УСТАНОВКА</p>' +
        '<h3>НА ТЕЛЕФОН</h3>' +
        '<p class="overlay-text">' + steps + '</p>' +
        '<p class="overlay-text">После установки игра открывается с домашнего экрана и работает без интернета.</p>' +
        '<div class="overlay-actions">' +
        '<button class="btn btn-primary" id="ov-close">ПОНЯТНО</button>' +
        '</div>'
      );
      $('#ov-close').addEventListener('click', () => this.hideOverlay());
    }
  };

  const game = new Game();

  const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: fullscreen)').matches ||
      navigator.standalone === true;
  }

  function renderSettings() {
    for (const row of $$('.setting-row')) {
      const key = row.dataset.setting;
      const value = store.settings[key];
      const switches = $('.switch', row);
      if (switches) {
        switches.setAttribute('aria-checked', value ? 'true' : 'false');
      }
      for (const btn of $$('.segment button', row)) {
        btn.classList.toggle('active', btn.dataset.value === value);
      }
    }
  }

  /* ================================================================ события */
  const sanitizeRoom = (value) => String(value || '').toUpperCase()
    .split('').filter((ch) => ROOM_ALPHABET.includes(ch)).join('').slice(0, 5);

  function goMenu() {
    game.closeNet();
    game.state = 'idle';
    ui.hideOverlay();
    ui.showScreen('menu');
  }

  document.addEventListener('pointerdown', () => Sfx.unlock(), { passive: true });
  document.addEventListener('keydown', () => Sfx.unlock(), { once: true });

  for (const el of $$('[data-action]')) {
    el.addEventListener('click', () => {
      const action = el.dataset.action;
      Sfx.play('menu');
      haptic(6);
      if (action === 'play') {
        ui.showScreen('modes');
      } else if (action === 'shop') {
        ui.showScreen('shop');
      } else if (action === 'settings') {
        renderSettings();
        ui.showScreen('settings');
      } else if (action === 'howto') {
        ui.showHowTo();
      } else if (action === 'menu') {
        goMenu();
      } else if (action === 'net-cancel') {
        game.closeNet();
        game.state = 'idle';
        ui.resetNet();
        ui.showScreen('modes');
      }
    });
  }

  for (const card of $$('.mode-card')) {
    card.addEventListener('click', () => {
      Sfx.unlock();
      Sfx.play('menu');
      haptic(8);
      game.startMode(card.dataset.mode);
    });
  }

  for (const tab of $$('.net-tab')) {
    tab.addEventListener('click', () => {
      Sfx.play('menu');
      ui.showNetTab(tab.dataset.nettab);
    });
  }

  for (const tab of $$('.shop-tab')) {
    tab.addEventListener('click', () => {
      Sfx.play('menu');
      ui.setShopTab(tab.dataset.shoptab);
    });
  }

  $('#daily-btn').addEventListener('click', () => {
    Sfx.unlock();
    ui.claimDaily();
  });

  $('#promo-btn').addEventListener('click', () => {
    Sfx.unlock();
    ui.redeemCode();
  });

  const promoInput = $('#promo-input');
  promoInput.addEventListener('input', () => {
    promoInput.value = promoInput.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 24);
  });
  promoInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      ui.redeemCode();
    }
  });

  document.addEventListener('click', (event) => {
    const buySkin = event.target.closest('[data-buy-skin], [data-equip-skin]');
    if (buySkin) {
      ui.buySkin(buySkin.dataset.buySkin || buySkin.dataset.equipSkin);
      return;
    }
    const cheatBtn = event.target.closest('[data-buy-cheat], [data-toggle-cheat]');
    if (cheatBtn) {
      ui.buyCheat(cheatBtn.dataset.buyCheat || cheatBtn.dataset.toggleCheat);
    }
  });

  document.addEventListener('click', (event) => {
    const segment = event.target.closest('.segment button');
    if (segment) {
      const row = segment.closest('[data-setting]');
      if (row && store.settings[row.dataset.setting] !== undefined) {
        store.settings[row.dataset.setting] = segment.dataset.value;
        saveStore();
        renderSettings();
        Sfx.play('menu');
      }
      return;
    }
    const toggle = event.target.closest('.switch');
    if (toggle) {
      const row = toggle.closest('[data-setting]');
      if (row && store.settings[row.dataset.setting] !== undefined) {
        const key = row.dataset.setting;
        store.settings[key] = !store.settings[key];
        saveStore();
        renderSettings();
        if (key === 'sound' && store.settings.sound) Sfx.play('special');
        else Sfx.play('menu');
      }
    }
  });

  $('#reset-records').addEventListener('click', () => {
    ui.showOverlay(
      '<p class="overlay-kicker">РЕКОРДЫ</p>' +
      '<h3>СБРОСИТЬ ВСЁ?</h3>' +
      '<p class="overlay-text">Все рекорды шести режимов будут удалены. Настройки, неоны и покупки останутся.</p>' +
      '<div class="overlay-actions">' +
      '<button class="btn btn-primary" id="ov-reset-ok">СБРОСИТЬ</button>' +
      '<button class="btn btn-ghost" id="ov-close">ОТМЕНА</button>' +
      '</div>'
    );
    $('#ov-close').addEventListener('click', () => ui.hideOverlay());
    $('#ov-reset-ok').addEventListener('click', () => {
      for (const key of Object.keys(store.bests)) store.bests[key] = 0;
      saveStore();
      game.refreshBests();
      ui.hideOverlay();
      ui.toast('РЕКОРДЫ СБРОШЕНЫ');
    });
  });

  $('#net-host-btn').addEventListener('click', () => {
    Sfx.unlock();
    game.netCreateRoom();
  });

  $('#net-join-btn').addEventListener('click', () => {
    Sfx.unlock();
    game.netJoinRoom($('#room-input').value);
  });

  $('#net-share').addEventListener('click', () => ui.shareRoom());

  const roomInput = $('#room-input');
  roomInput.addEventListener('input', () => {
    const clean = sanitizeRoom(roomInput.value);
    if (roomInput.value !== clean) roomInput.value = clean;
  });
  roomInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      game.netJoinRoom(roomInput.value);
    }
  });

  $('#pause-btn').addEventListener('click', () => {
    Sfx.play('menu');
    game.pause();
  });

  /* ---------------------------------------------------------- свайпы и D-pad */
  document.addEventListener('pointerdown', (event) => {
    const btn = event.target.closest('.dpad-btn');
    if (!btn) return;
    event.preventDefault();
    game.turn(DIRS[btn.dataset.dir]);
    btn.classList.add('pressed');
  });
  const releaseDpad = () => {
    for (const btn of $$('.dpad-btn.pressed')) btn.classList.remove('pressed');
  };
  document.addEventListener('pointerup', releaseDpad);
  document.addEventListener('pointercancel', releaseDpad);

  game.canvas.addEventListener('pointerdown', (event) => {
    if (ui.screen !== 'game') return;
    game.swipe = { x: event.clientX, y: event.clientY, id: event.pointerId };
    if (game.canvas.setPointerCapture) {
      try { game.canvas.setPointerCapture(event.pointerId); } catch (err) { /* не вышло */ }
    }
  });
  game.canvas.addEventListener('pointerup', (event) => {
    const swipe = game.swipe;
    game.swipe = null;
    if (!swipe) return;
    const dx = event.clientX - swipe.x;
    const dy = event.clientY - swipe.y;
    const ax = Math.abs(dx);
    const ay = Math.abs(dy);
    if (Math.max(ax, ay) < 16) return;
    if (ax > ay) game.turn(dx > 0 ? DIRS.right : DIRS.left);
    else game.turn(dy > 0 ? DIRS.down : DIRS.up);
  });
  game.canvas.addEventListener('pointercancel', () => { game.swipe = null; });

  document.addEventListener('contextmenu', (event) => {
    if (event.target.closest('#game-canvas, #touch-controls')) event.preventDefault();
  });

  /* ---------------------------------------------------------- клавиатура */
  const KEY_DIRS = {
    arrowup: 'up', w: 'up', 'ц': 'up',
    arrowdown: 'down', s: 'down', 'ы': 'down',
    arrowleft: 'left', a: 'left', 'ф': 'left',
    arrowright: 'right', d: 'right', 'в': 'right'
  };
  window.addEventListener('keydown', (event) => {
    const key = event.key.toLowerCase();
    if (ui.screen === 'game') {
      const dir = KEY_DIRS[key];
      if (dir) {
        event.preventDefault();
        game.turn(DIRS[dir]);
        return;
      }
      if (key === ' ' || key === 'p' || key === 'з') {
        event.preventDefault();
        if (game.state === 'paused') game.resume();
        else game.pause();
        return;
      }
      if (key === 'r' || key === 'к') {
        if (game.state === 'dead' || game.state === 'paused') {
          event.preventDefault();
          game.startMode(game.mode);
        }
        return;
      }
      if (key === 'escape') {
        if (game.state === 'paused') game.resume();
        else if (game.state === 'playing' || game.state === 'countdown') game.pause();
      }
      return;
    }
    if (key === 'escape') {
      if (!ui.overlay.classList.contains('hidden')) {
        ui.hideOverlay();
        return;
      }
      if (ui.screen !== 'menu') goMenu();
    }
  });

  /* ---------------------------------------------------------- установка PWA */
  const installBtn = $('#install-btn');
  let deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
    if (!isStandalone()) installBtn.classList.remove('hidden');
  });

  installBtn.addEventListener('click', () => {
    Sfx.unlock();
    if (deferredPrompt) {
      const prompt = deferredPrompt;
      deferredPrompt = null;
      installBtn.classList.add('hidden');
      prompt.prompt().catch(() => {}).finally(() => {
        prompt.userChoice.catch(() => {}).finally(() => {
          if (!isStandalone()) installBtn.classList.remove('hidden');
        });
      });
    } else {
      ui.showInstall();
    }
  });

  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    installBtn.classList.add('hidden');
    ui.toast('ПРИЛОЖЕНИЕ УСТАНОВЛЕНО');
  });

  if (isIos() && !isStandalone()) {
    installBtn.classList.remove('hidden');
    installBtn.textContent = 'УСТАНОВИТЬ НА IPHONE';
  }

  /* ---------------------------------------------------------- жизненный цикл */
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      if (ui.screen === 'game' && game.mode !== 'net' &&
          (game.state === 'playing' || game.state === 'countdown')) {
        game.pause();
      }
    } else {
      lastFrame = performance.now();
    }
  });

  window.addEventListener('pagehide', () => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(store)); } catch (err) { /* нет места */ }
    if (game.broker) game.closeNet();
  });

  if ('serviceWorker' in navigator && /^https?:/.test(location.protocol)) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => {
        /* офлайн-режим недоступен, игра продолжает работать */
      });
    });
  }

  /* ---------------------------------------------------------- цикл игры */
  let lastFrame = performance.now();
  function loop(now) {
    const dt = Math.min(0.05, Math.max(0, (now - lastFrame) / 1000));
    lastFrame = now;
    if (ui.screen === 'game') {
      game.update(dt);
      game.render();
    }
    requestAnimationFrame(loop);
  }

  game.refreshBests();
  renderSettings();
  saveStore();
  ui.showScreen('menu');
  requestAnimationFrame(loop);


})();
