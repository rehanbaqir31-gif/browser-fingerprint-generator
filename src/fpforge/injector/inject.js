// fpforge page-side overrides. Runs in every frame before any page script, and in
// dedicated workers (injected through CDP while the worker is paused at start).
// Receives one argument: the config built by fpforge.injector.core.js_config().
//
// Design rules:
//   * override on the *prototype* (like the real property), never on the instance
//   * keep the original getter call so invalid receivers still throw natively
//   * make patched functions report "[native code]" through Function.prototype.toString
//   * only override what the profile data actually contains
(function (cfg) {
  'use strict';

  const isWorker = typeof WorkerGlobalScope !== 'undefined' && self instanceof WorkerGlobalScope;

  // ---------------------------------------------------------------- toString masking
  const nativeSource = new WeakMap();
  const origToString = Function.prototype.toString;
  const patchedToString = function toString() {
    if (this === patchedToString) return 'function toString() { [native code] }';
    const s = nativeSource.get(this);
    return s !== undefined ? s : origToString.call(this);
  };
  Object.defineProperty(Function.prototype, 'toString', {
    value: patchedToString, writable: true, configurable: true, enumerable: false,
  });
  const mark = (fn, name) => { nativeSource.set(fn, 'function ' + name + '() { [native code] }'); return fn; };

  // ---------------------------------------------------------------- helpers
  function getterNamed(prop, impl) {
    // object-literal getters get the right "get <prop>" name and no prototype
    const holder = { get [prop]() { return impl.call(this); } };
    return mark(Object.getOwnPropertyDescriptor(holder, prop).get, 'get ' + prop);
  }

  // Replace an accessor (or data property) with a constant value.
  function overrideValue(target, prop, value) {
    const desc = Object.getOwnPropertyDescriptor(target, prop);
    if (!desc) return false;
    if (desc.get) {
      const orig = desc.get;
      const getter = getterNamed(prop, function () { orig.call(this); return value; });
      Object.defineProperty(target, prop, { get: getter, set: desc.set, enumerable: desc.enumerable, configurable: true });
    } else if ('value' in desc) {
      Object.defineProperty(target, prop, { value: value, writable: desc.writable, enumerable: desc.enumerable, configurable: true });
    } else {
      return false;
    }
    return true;
  }

  function overrideMethod(target, prop, make) {
    const desc = Object.getOwnPropertyDescriptor(target, prop);
    if (!desc || typeof desc.value !== 'function') return false;
    const orig = desc.value;
    const holder = { [prop]: make(orig) };
    const fn = mark(holder[prop], prop);
    Object.defineProperty(target, prop, { value: fn, writable: desc.writable, enumerable: desc.enumerable, configurable: true });
    return true;
  }

  const hash32 = (n, seed) => {
    let h = Math.imul((n | 0) ^ (seed | 0), 0x9E3779B1);
    h ^= h >>> 15; h = Math.imul(h, 0x85EBCA6B);
    h ^= h >>> 13; h = Math.imul(h, 0xC2B2AE35);
    return (h ^ (h >>> 16)) >>> 0;
  };

  // ---------------------------------------------------------------- navigator
  const N = isWorker ? WorkerNavigator.prototype : Navigator.prototype; // missing props are skipped
  if (cfg.platform != null) overrideValue(N, 'platform', cfg.platform);
  if (cfg.vendor != null) overrideValue(N, 'vendor', cfg.vendor);
  if (cfg.hardwareConcurrency != null) overrideValue(N, 'hardwareConcurrency', cfg.hardwareConcurrency);
  if (cfg.deviceMemory != null) overrideValue(N, 'deviceMemory', cfg.deviceMemory);
  if (cfg.maxTouchPoints != null) overrideValue(N, 'maxTouchPoints', cfg.maxTouchPoints);
  overrideValue(N, 'doNotTrack', cfg.doNotTrack == null ? null : String(cfg.doNotTrack));
  overrideValue(N, 'webdriver', false);
  if (cfg.languages && cfg.languages.length) {
    const langs = Object.freeze(cfg.languages.slice()); // Chrome returns the same frozen array each time
    overrideValue(N, 'languages', langs);
    overrideValue(N, 'language', langs[0]);
  }

  // ---------------------------------------------------------------- screen / window
  const S = cfg.screen || {};
  if (!isWorker) for (const k of ['width', 'height', 'availWidth', 'availHeight', 'availLeft', 'availTop', 'colorDepth', 'pixelDepth']) {
    if (S[k] != null) overrideValue(Screen.prototype, k, S[k]);
  }
  if (!isWorker && S.outerWidth) overrideValue(window, 'outerWidth', S.outerWidth);
  if (!isWorker && S.outerHeight) overrideValue(window, 'outerHeight', S.outerHeight);
  // exact dataset value (Chrome reports float32 artefacts such as 1.100000023841858)
  if (!isWorker && S.devicePixelRatio) overrideValue(window, 'devicePixelRatio', S.devicePixelRatio);

  // ---------------------------------------------------------------- WebGL
  if (cfg.webgl && cfg.webgl.unmaskedRenderer) {
    const UNMASKED_VENDOR = 0x9245, UNMASKED_RENDERER = 0x9246;
    const debugInfoRequested = new WeakSet();
    for (const Ctx of [self.WebGLRenderingContext, self.WebGL2RenderingContext]) {
      if (!Ctx) continue;
      overrideMethod(Ctx.prototype, 'getExtension', (orig) => function (name) {
        const ext = orig.apply(this, arguments);
        if (ext && String(name).toLowerCase() === 'webgl_debug_renderer_info') debugInfoRequested.add(this);
        return ext;
      });
      overrideMethod(Ctx.prototype, 'getParameter', (orig) => function (pname) {
        if (debugInfoRequested.has(this)) { // real Chrome only answers after the extension was requested
          if (pname === UNMASKED_VENDOR) return cfg.webgl.unmaskedVendor;
          if (pname === UNMASKED_RENDERER) return cfg.webgl.unmaskedRenderer;
        }
        return orig.apply(this, arguments);
      });
    }
  }

  // ---------------------------------------------------------------- canvas noise
  if (!isWorker && cfg.canvas && cfg.canvas.mode === 'noise') {
    const seed = cfg.canvas.noiseSeed | 0;
    const ctxType = new WeakMap();
    const createElement = Document.prototype.createElement;
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    const putImageData = CanvasRenderingContext2D.prototype.putImageData;
    const drawImage = CanvasRenderingContext2D.prototype.drawImage;

    // deterministic per pixel position: the same canvas always yields the same noise
    function noisify(img) {
      const d = img.data;
      for (let i = 0; i < d.length; i += 4) {
        if (d[i + 3] === 0) continue;
        const h = hash32(i >>> 2, seed);
        if ((h & 0xFF) < 6) { const c = (h >>> 8) % 3; d[i + c] = d[i + c] ^ 1; }
      }
    }
    function noisyCopy(canvas) {
      if (ctxType.get(canvas) !== '2d') return null;
      const w = canvas.width, h = canvas.height;
      if (!w || !h) return null;
      try {
        const tmp = createElement.call(document, 'canvas');
        tmp.width = w; tmp.height = h;
        const c = tmp.getContext('2d');
        drawImage.call(c, canvas, 0, 0);
        const img = origGetImageData.call(c, 0, 0, w, h);
        noisify(img);
        putImageData.call(c, img, 0, 0);
        return tmp;
      } catch (e) { return null; }
    }

    overrideMethod(HTMLCanvasElement.prototype, 'getContext', (orig) => function (type) {
      const ctx = orig.apply(this, arguments);
      if (ctx && !ctxType.has(this)) ctxType.set(this, String(type));
      return ctx;
    });
    overrideMethod(HTMLCanvasElement.prototype, 'toDataURL', (orig) => function () {
      return orig.apply(noisyCopy(this) || this, arguments);
    });
    overrideMethod(HTMLCanvasElement.prototype, 'toBlob', (orig) => function () {
      return orig.apply(noisyCopy(this) || this, arguments);
    });
    overrideMethod(CanvasRenderingContext2D.prototype, 'getImageData', (orig) => function () {
      const img = orig.apply(this, arguments);
      noisify(img);
      return img;
    });
  }

  // ---------------------------------------------------------------- audio noise
  if (!isWorker && cfg.audio && cfg.audio.mode === 'noise' && window.AudioBuffer) {
    const aseed = cfg.audio.noiseSeed | 0;
    const touched = new WeakMap();
    overrideMethod(AudioBuffer.prototype, 'getChannelData', (orig) => function (channel) {
      const data = orig.apply(this, arguments);
      let done = touched.get(this);
      if (!done) touched.set(this, (done = new Set()));
      if (!done.has(channel)) {
        done.add(channel);
        for (let i = 0; i < data.length; i += 100) {
          data[i] += ((hash32(i, aseed) & 0xFFFF) / 0xFFFF - 0.5) * 1e-7;
        }
      }
      return data;
    });
    if (window.AnalyserNode) {
      overrideMethod(AnalyserNode.prototype, 'getFloatFrequencyData', (orig) => function (array) {
        orig.apply(this, arguments);
        for (let i = 0; i < array.length; i++) array[i] += ((hash32(i, aseed) & 0xFFFF) / 0xFFFF - 0.5) * 0.1;
      });
    }
  }

  // ---------------------------------------------------------------- battery
  if (!isWorker && cfg.battery && typeof navigator.getBattery === 'function') {
    const num = (v) => (v === null || v === undefined ? Infinity : v);
    const manager = new EventTarget();
    if (window.BatteryManager) Object.setPrototypeOf(manager, BatteryManager.prototype);
    const values = {
      charging: !!cfg.battery.charging,
      chargingTime: num(cfg.battery.chargingTime),
      dischargingTime: num(cfg.battery.dischargingTime),
      level: cfg.battery.level,
    };
    for (const k of Object.keys(values)) {
      Object.defineProperty(manager, k, { get: () => values[k], enumerable: false, configurable: true });
    }
    overrideMethod(N, 'getBattery', () => function () { return Promise.resolve(manager); });
  }

  // ---------------------------------------------------------------- media devices
  if (!isWorker && cfg.mediaDevices && navigator.mediaDevices && window.MediaDeviceInfo) {
    const make = (d) => {
      const info = Object.create(MediaDeviceInfo.prototype);
      for (const k of ['deviceId', 'groupId', 'kind', 'label']) {
        Object.defineProperty(info, k, { value: d[k] || '', enumerable: false, configurable: true });
      }
      return info;
    };
    const all = [].concat(cfg.mediaDevices.micros || [], cfg.mediaDevices.webcams || [], cfg.mediaDevices.speakers || []);
    overrideMethod(MediaDevices.prototype, 'enumerateDevices', () => function () {
      return Promise.resolve(all.map(make));
    });
  }

  // ---------------------------------------------------------------- WebRTC
  if (!isWorker && cfg.webrtc && cfg.webrtc.mode === 'disabled') {
    for (const k of ['RTCPeerConnection', 'webkitRTCPeerConnection', 'RTCSessionDescription', 'RTCIceCandidate']) {
      try { delete window[k]; } catch (e) { /* non-configurable: ignore */ }
    }
  }
})
