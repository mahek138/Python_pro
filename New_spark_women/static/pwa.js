(function () {
  const STORAGE_KEYS = {
    largeText: 'a11yLargeText',
    highContrast: 'a11yHighContrast',
    voiceHints: 'a11yVoiceHints',
    signalAlerts: 'a11ySignalAlerts',
    disabilityProfile: 'a11yDisabilityProfile',
    voiceSOS: 'a11yVoiceSOS',
    appLanguage: 'appLanguage',
  };

  const LANGUAGE_OPTIONS = [
    { code: 'en', label: 'English' },
    { code: 'hi', label: 'Hindi' },
    { code: 'mr', label: 'Marathi' },
    { code: 'bn', label: 'Bengali' },
    { code: 'gu', label: 'Gujarati' },
    { code: 'kn', label: 'Kannada' },
    { code: 'ml', label: 'Malayalam' },
    { code: 'or', label: 'Odia' },
    { code: 'pa', label: 'Punjabi' },
    { code: 'ta', label: 'Tamil' },
    { code: 'te', label: 'Telugu' },
    { code: 'ur', label: 'Urdu' },
  ];

  const APP_TO_VIDEO_LANGUAGE = {
    en: 'english',
    hi: 'hindi',
    mr: 'marathi',
  };

  function resolveLanguageCode(rawLang) {
    const normalized = String(rawLang || '').toLowerCase();
    if (!normalized) return 'en';
    const exact = LANGUAGE_OPTIONS.find((item) => item.code === normalized);
    if (exact) return exact.code;
    const shortCode = normalized.split('-')[0];
    const byPrefix = LANGUAGE_OPTIONS.find((item) => item.code === shortCode);
    return byPrefix ? byPrefix.code : 'en';
  }

  function getPreferredAppLanguage() {
    const saved = localStorage.getItem(STORAGE_KEYS.appLanguage);
    if (saved) {
      return resolveLanguageCode(saved);
    }
    return resolveLanguageCode(navigator.language || navigator.userLanguage || 'en');
  }

  const PROFILE_PRESETS = {
    standard: { largeText: false, highContrast: false, voiceHints: false, signalAlerts: false, voiceSOS: false },
    blind_low_vision: { largeText: true, highContrast: true, voiceHints: true, signalAlerts: true, voiceSOS: true },
    deaf_nonverbal: { largeText: true, highContrast: true, voiceHints: false, signalAlerts: true, voiceSOS: false },
    speech_impairment: { largeText: true, highContrast: false, voiceHints: true, signalAlerts: true, voiceSOS: false },
    mobility_cognitive: { largeText: true, highContrast: true, voiceHints: true, signalAlerts: true, voiceSOS: false },
  };

  function isEnabled(key) {
    return localStorage.getItem(key) === 'true';
  }

  function setEnabled(key, enabled) {
    localStorage.setItem(key, enabled ? 'true' : 'false');
  }

  function injectAccessibilityStyles() {
    if (document.getElementById('a11yStyles')) return;
    const style = document.createElement('style');
    style.id = 'a11yStyles';
    style.textContent = `
      html.a11y-large-text { font-size: 112%; }
      html.a11y-high-contrast body { background: #111 !important; color: #fff !important; }
      html.a11y-high-contrast a, html.a11y-high-contrast button { outline-color: #ffd54f !important; }
      #a11yFab {
        position: fixed; right: 12px; bottom: 60px; z-index: 10001;
        border: none; border-radius: 999px; width: 48px; height: 48px;
        font-size: 22px; cursor: pointer; background: #111; color: #fff;
      }
      #a11yPanel {
        position: fixed; right: 12px; bottom: 116px; z-index: 10001;
        width: 280px; background: #fff; border: 1px solid #ddd; border-radius: 10px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.18); padding: 12px; font-family: 'Segoe UI', sans-serif;
      }
      #a11yPanel[hidden] { display: none; }
      #a11yPanel h4 { margin: 0 0 10px 0; font-size: 14px; color: #2f2f2f; }
      #a11yPanel .a11y-row { display: flex; align-items: center; gap: 8px; margin: 8px 0; }
      #a11yPanel .a11y-row.stacked { align-items: flex-start; flex-direction: column; gap: 6px; }
      #a11yPanel label { font-size: 13px; color: #444; }
      #a11yPanel select {
        border: 1px solid #cfcfcf; border-radius: 6px; padding: 6px; width: 100%; font-size: 13px;
      }
      #a11yPanel button { border: 0; background: #6200EE; color: #fff; border-radius: 6px; padding: 8px 10px; cursor: pointer; }
      #langQuickWrap {
        position: fixed;
        top: 12px;
        left: 12px;
        z-index: 10002;
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 8px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid #e5e5e5;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        font-family: 'Segoe UI', sans-serif;
      }
      #langQuickWrap label {
        font-size: 12px;
        color: #444;
        font-weight: 600;
      }
      #langQuickSelect {
        border: 1px solid #cfcfcf;
        border-radius: 8px;
        padding: 5px 8px;
        font-size: 12px;
        max-width: 130px;
        background: #fff;
      }
      @media (max-width: 640px) {
        #langQuickWrap {
          top: 10px;
          left: 10px;
          padding: 5px 7px;
        }
        #langQuickWrap label {
          display: none;
        }
        #langQuickSelect {
          max-width: 110px;
          font-size: 11px;
        }
      }
      #a11yFlash {
        position: fixed; inset: 0; background: rgba(255, 255, 0, 0.35); z-index: 10000;
        opacity: 0; pointer-events: none; transition: opacity 180ms ease;
      }
      #a11yFlash.active { opacity: 1; }
      .sr-only {
        position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
        overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
      }
    `;
    document.head.appendChild(style);
  }

  function applyModes() {
    document.documentElement.classList.toggle('a11y-large-text', isEnabled(STORAGE_KEYS.largeText));
    document.documentElement.classList.toggle('a11y-high-contrast', isEnabled(STORAGE_KEYS.highContrast));
  }

  function ensureWatermark() {
    if (document.getElementById('appWatermark')) return;

    const watermark = document.createElement('div');
    watermark.id = 'appWatermark';
    watermark.textContent = 'An Application created by Pallavi and Mahek';
    watermark.style.position = 'fixed';
    watermark.style.left = '10px';
    watermark.style.bottom = '10px';
    watermark.style.fontSize = '13px';
    watermark.style.fontWeight = '600';
    watermark.style.color = 'rgba(60, 60, 60, 0.42)';
    watermark.style.letterSpacing = '0.2px';
    watermark.style.lineHeight = '1.25';
    watermark.style.maxWidth = '220px';
    watermark.style.whiteSpace = 'normal';
    watermark.style.wordBreak = 'break-word';
    watermark.style.pointerEvents = 'none';
    watermark.style.userSelect = 'none';
    watermark.style.zIndex = '9999';
    document.body.appendChild(watermark);
  }

  function speak(text) {
    if (!('speechSynthesis' in window) || !text) return;
    window.speechSynthesis.cancel();
    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 0.95;
    window.speechSynthesis.speak(msg);
  }

  function readPageAloud() {
    const text = Array.from(document.querySelectorAll('h1,h2,h3,p,button,a'))
      .map((el) => (el.textContent || '').trim())
      .filter(Boolean)
      .join('. ')
      .slice(0, 1400);
    speak(text || 'No readable content found on this page.');
  }

  async function triggerEmergencySOS() {
    const panicForm = document.getElementById('panicForm');
    if (panicForm) {
      panicForm.submit();
      return { status: 'success', message: 'Emergency SOS triggered.' };
    }

    try {
      const response = await fetch('/panic', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      const data = await response.json();
      if (data.status === 'success' && data.sms_all_link) {
        window.location.href = data.sms_all_link;
      }
      return data;
    } catch (error) {
      return { status: 'error', message: 'Unable to trigger SOS right now.' };
    }
  }

  function ensureAccessibilityControls() {
    if (document.getElementById('a11yFab')) return;

    const flash = document.createElement('div');
    flash.id = 'a11yFlash';
    document.body.appendChild(flash);

    const liveRegion = document.createElement('div');
    liveRegion.id = 'a11yLive';
    liveRegion.className = 'sr-only';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('role', 'status');
    document.body.appendChild(liveRegion);

    const fab = document.createElement('button');
    fab.id = 'a11yFab';
    fab.type = 'button';
    fab.setAttribute('aria-label', 'Open accessibility settings');
    fab.textContent = 'A';

    const panel = document.createElement('div');
    panel.id = 'a11yPanel';
    panel.hidden = true;
    panel.innerHTML = `
      <h4>Accessibility</h4>
      <div class="a11y-row stacked">
        <label for="a11yLanguage">Language preference</label>
        <select id="a11yLanguage"></select>
      </div>
      <div class="a11y-row stacked">
        <label for="a11yProfile">Disability category</label>
        <select id="a11yProfile">
          <option value="standard">Standard mode</option>
          <option value="blind_low_vision">Blind or low vision</option>
          <option value="deaf_nonverbal">Deaf or non-verbal</option>
          <option value="speech_impairment">Speech impairment</option>
          <option value="mobility_cognitive">Mobility or cognitive support</option>
        </select>
      </div>
      <div class="a11y-row"><input id="a11yLargeText" type="checkbox"><label for="a11yLargeText">Large text</label></div>
      <div class="a11y-row"><input id="a11yHighContrast" type="checkbox"><label for="a11yHighContrast">High contrast</label></div>
      <div class="a11y-row"><input id="a11yVoiceHints" type="checkbox"><label for="a11yVoiceHints">Voice guidance</label></div>
      <div class="a11y-row"><input id="a11ySignalAlerts" type="checkbox"><label for="a11ySignalAlerts">Visual + vibration alerts</label></div>
      <div class="a11y-row"><input id="a11yVoiceSOS" type="checkbox"><label for="a11yVoiceSOS">Hands-free SOS: say help me</label></div>
      <div class="a11y-row"><button id="a11ySosNowBtn" type="button">Send SOS now</button></div>
      <div class="a11y-row"><button id="a11yReadPageBtn" type="button">Read page aloud</button></div>
    `;

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    const profileSelect = panel.querySelector('#a11yProfile');
    const languageSelect = panel.querySelector('#a11yLanguage');
    const largeTextInput = panel.querySelector('#a11yLargeText');
    const highContrastInput = panel.querySelector('#a11yHighContrast');
    const voiceHintsInput = panel.querySelector('#a11yVoiceHints');
    const signalAlertsInput = panel.querySelector('#a11ySignalAlerts');
    const voiceSOSInput = panel.querySelector('#a11yVoiceSOS');
    const sosNowBtn = panel.querySelector('#a11ySosNowBtn');
    const readPageBtn = panel.querySelector('#a11yReadPageBtn');
    let quickLanguageSelect = null;

    function ensureQuickLanguageSwitcher() {
      if (document.getElementById('langQuickWrap')) return;

      const wrap = document.createElement('div');
      wrap.id = 'langQuickWrap';
      wrap.innerHTML = `
        <label for="langQuickSelect">Language</label>
        <select id="langQuickSelect"></select>
      `;
      document.body.appendChild(wrap);

      quickLanguageSelect = wrap.querySelector('#langQuickSelect');
      quickLanguageSelect.innerHTML = LANGUAGE_OPTIONS.map(function (item) {
        return `<option value="${item.code}">${item.label}</option>`;
      }).join('');
      quickLanguageSelect.value = getPreferredAppLanguage();

      quickLanguageSelect.addEventListener('change', function () {
        languageSelect.value = quickLanguageSelect.value;
        languageSelect.dispatchEvent(new Event('change'));
      });
    }

    function setGoogleTranslateCookie(value) {
      document.cookie = `googtrans=${value};path=/`;
    }

    function applyGoogleTranslateCombo(selected) {
      const combo = document.querySelector('.goog-te-combo');
      if (!combo) return false;
      combo.value = selected;
      combo.dispatchEvent(new Event('change'));
      return true;
    }

    function waitAndApplyGoogleTranslateCombo(selected, triesLeft) {
      if (applyGoogleTranslateCombo(selected)) return;
      if (triesLeft <= 0) return;
      setTimeout(function () {
        waitAndApplyGoogleTranslateCombo(selected, triesLeft - 1);
      }, 250);
    }

    function loadGoogleTranslateScript() {
      if (document.getElementById('google_translate_element_script')) return;
      if (!document.getElementById('google_translate_element')) {
        const host = document.createElement('div');
        host.id = 'google_translate_element';
        host.style.display = 'none';
        document.body.appendChild(host);
      }

      window.googleTranslateElementInit = function () {
        if (!window.google || !window.google.translate || !window.google.translate.TranslateElement) return;
        new window.google.translate.TranslateElement(
          {
            pageLanguage: 'en',
            autoDisplay: false,
            includedLanguages: LANGUAGE_OPTIONS.map((item) => item.code).join(','),
          },
          'google_translate_element'
        );
      };

      const script = document.createElement('script');
      script.id = 'google_translate_element_script';
      script.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
      script.async = true;
      document.head.appendChild(script);
    }

    function applyLanguage(langCode, forceReload) {
      const selected = LANGUAGE_OPTIONS.some((item) => item.code === langCode) ? langCode : 'en';
      localStorage.setItem(STORAGE_KEYS.appLanguage, selected);
      document.documentElement.setAttribute('lang', selected);

      if (selected === 'en') {
        setGoogleTranslateCookie('/en/en');
        if (applyGoogleTranslateCombo('en')) {
          return;
        }
        if (forceReload) {
          window.location.reload();
        }
        return;
      }

      setGoogleTranslateCookie(`/en/${selected}`);
      if (applyGoogleTranslateCombo(selected)) {
        return;
      }

      loadGoogleTranslateScript();
      waitAndApplyGoogleTranslateCombo(selected, 16);
      if (forceReload) {
        setTimeout(function () {
          window.location.reload();
        }, 1200);
      }
    }

    languageSelect.innerHTML = LANGUAGE_OPTIONS.map(function (item) {
      return `<option value="${item.code}">${item.label}</option>`;
    }).join('');
    languageSelect.value = getPreferredAppLanguage();
    ensureQuickLanguageSwitcher();

    const savedProfile = localStorage.getItem(STORAGE_KEYS.disabilityProfile) || 'standard';
    profileSelect.value = PROFILE_PRESETS[savedProfile] ? savedProfile : 'standard';

    largeTextInput.checked = isEnabled(STORAGE_KEYS.largeText);
    highContrastInput.checked = isEnabled(STORAGE_KEYS.highContrast);
    voiceHintsInput.checked = isEnabled(STORAGE_KEYS.voiceHints);
    signalAlertsInput.checked = isEnabled(STORAGE_KEYS.signalAlerts);
    voiceSOSInput.checked = isEnabled(STORAGE_KEYS.voiceSOS);

    function syncInputsFromStorage() {
      largeTextInput.checked = isEnabled(STORAGE_KEYS.largeText);
      highContrastInput.checked = isEnabled(STORAGE_KEYS.highContrast);
      voiceHintsInput.checked = isEnabled(STORAGE_KEYS.voiceHints);
      signalAlertsInput.checked = isEnabled(STORAGE_KEYS.signalAlerts);
      voiceSOSInput.checked = isEnabled(STORAGE_KEYS.voiceSOS);
    }

    function applyProfilePreset(profileName) {
      const preset = PROFILE_PRESETS[profileName] || PROFILE_PRESETS.standard;
      setEnabled(STORAGE_KEYS.largeText, preset.largeText);
      setEnabled(STORAGE_KEYS.highContrast, preset.highContrast);
      setEnabled(STORAGE_KEYS.voiceHints, preset.voiceHints);
      setEnabled(STORAGE_KEYS.signalAlerts, preset.signalAlerts);
      setEnabled(STORAGE_KEYS.voiceSOS, preset.voiceSOS);
      localStorage.setItem(STORAGE_KEYS.disabilityProfile, profileName);
      syncInputsFromStorage();
      applyModes();
    }

    const SpeechRecognitionApi = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let recognitionRunning = false;
    let keepListening = false;

    function startVoiceSOSListening() {
      if (!voiceSOSInput.checked) return;
      if (!SpeechRecognitionApi) {
        liveRegion.textContent = 'Voice SOS not supported in this browser.';
        return;
      }
      if (recognitionRunning) return;

      if (!recognition) {
        recognition = new SpeechRecognitionApi();
        recognition.lang = 'en-IN';
        recognition.continuous = true;
        recognition.interimResults = false;

        recognition.onresult = function (event) {
          const transcript = (event.results[event.results.length - 1][0].transcript || '').toLowerCase().trim();
          const isSOSCommand = transcript.includes('help me') || transcript.includes('sos') || transcript.includes('emergency');
          if (!isSOSCommand) return;

          window.sparkAccessibility.signalAlert('Voice command detected. Sending SOS now.');
          triggerEmergencySOS().then(function (result) {
            if (result.status !== 'success') {
              window.sparkAccessibility.signalAlert(result.message || 'SOS could not be triggered.');
            }
          });
        };

        recognition.onend = function () {
          recognitionRunning = false;
          if (keepListening && voiceSOSInput.checked) {
            setTimeout(startVoiceSOSListening, 700);
          }
        };

        recognition.onerror = function () {
          recognitionRunning = false;
        };
      }

      keepListening = true;
      try {
        recognition.start();
        recognitionRunning = true;
        liveRegion.textContent = 'Voice SOS listening is active. Say help me.';
      } catch (error) {
        liveRegion.textContent = 'Voice SOS could not start. Try again.';
      }
    }

    function stopVoiceSOSListening() {
      keepListening = false;
      if (recognition && recognitionRunning) {
        recognition.stop();
      }
      recognitionRunning = false;
    }

    fab.addEventListener('click', function () {
      panel.hidden = !panel.hidden;
    });

    profileSelect.addEventListener('change', function () {
      applyProfilePreset(profileSelect.value);
      if (voiceSOSInput.checked) {
        startVoiceSOSListening();
      } else {
        stopVoiceSOSListening();
      }
      liveRegion.textContent = 'Disability category updated.';
      if (voiceHintsInput.checked) {
        speak('Disability category updated');
      }
    });

    languageSelect.addEventListener('change', function () {
      const nextLangCode = resolveLanguageCode(languageSelect.value);
      if (quickLanguageSelect) {
        quickLanguageSelect.value = nextLangCode;
      }
      applyLanguage(nextLangCode, true);

      if (window.location.pathname === '/self-defense') {
        const url = new URL(window.location.href);
        const mappedVideoLanguage = APP_TO_VIDEO_LANGUAGE[nextLangCode] || 'english';
        url.searchParams.set('lang', mappedVideoLanguage);
        window.location.replace(url.toString());
        return;
      }

      liveRegion.textContent = `Language changed to ${languageSelect.options[languageSelect.selectedIndex].text}.`;
      if (voiceHintsInput.checked) {
        speak('Language changed');
      }
    });

    largeTextInput.addEventListener('change', function () {
      setEnabled(STORAGE_KEYS.largeText, largeTextInput.checked);
      applyModes();
      liveRegion.textContent = largeTextInput.checked ? 'Large text enabled' : 'Large text disabled';
    });

    highContrastInput.addEventListener('change', function () {
      setEnabled(STORAGE_KEYS.highContrast, highContrastInput.checked);
      applyModes();
      liveRegion.textContent = highContrastInput.checked ? 'High contrast enabled' : 'High contrast disabled';
    });

    voiceHintsInput.addEventListener('change', function () {
      setEnabled(STORAGE_KEYS.voiceHints, voiceHintsInput.checked);
      if (voiceHintsInput.checked) {
        speak('Voice guidance enabled');
      }
    });

    signalAlertsInput.addEventListener('change', function () {
      setEnabled(STORAGE_KEYS.signalAlerts, signalAlertsInput.checked);
      liveRegion.textContent = signalAlertsInput.checked ? 'Signal alerts enabled' : 'Signal alerts disabled';
    });

    voiceSOSInput.addEventListener('change', function () {
      setEnabled(STORAGE_KEYS.voiceSOS, voiceSOSInput.checked);
      if (voiceSOSInput.checked) {
        startVoiceSOSListening();
      } else {
        stopVoiceSOSListening();
      }
      liveRegion.textContent = voiceSOSInput.checked
        ? 'Hands-free SOS enabled. Say help me.'
        : 'Hands-free SOS disabled.';
    });

    sosNowBtn.addEventListener('click', function () {
      window.sparkAccessibility.signalAlert('Sending SOS now.');
      triggerEmergencySOS().then(function (result) {
        if (result.status !== 'success') {
          window.sparkAccessibility.signalAlert(result.message || 'SOS could not be triggered.');
        }
      });
    });

    readPageBtn.addEventListener('click', function () {
      readPageAloud();
    });

    document.addEventListener('focusin', function (event) {
      if (!isEnabled(STORAGE_KEYS.voiceHints)) return;
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const label = (target.getAttribute('aria-label') || target.textContent || '').trim();
      if (label) speak(label);
    });

    window.sparkAccessibility = {
      announce: function (text) {
        liveRegion.textContent = text;
        if (isEnabled(STORAGE_KEYS.voiceHints)) {
          speak(text);
        }
      },
      signalAlert: function (text) {
        if (isEnabled(STORAGE_KEYS.signalAlerts)) {
          flash.classList.add('active');
          setTimeout(function () {
            flash.classList.remove('active');
          }, 500);

          if ('vibrate' in navigator) {
            navigator.vibrate([180, 80, 180]);
          }
        }

        liveRegion.textContent = text;
        if (isEnabled(STORAGE_KEYS.voiceHints)) {
          speak(text);
        }
      },
      triggerSOS: function () {
        return triggerEmergencySOS();
      },
    };

    applyProfilePreset(profileSelect.value);
    applyLanguage(languageSelect.value, false);
    if (voiceSOSInput.checked) {
      startVoiceSOSListening();
    }
  }

  function initInstallPrompt() {
    let deferredPrompt = null;
    const installBtn = document.getElementById('installAppBtn');

    window.addEventListener('beforeinstallprompt', function (event) {
      event.preventDefault();
      deferredPrompt = event;
      if (installBtn) {
        installBtn.style.display = 'inline-flex';
      }
    });

    if (installBtn) {
      installBtn.addEventListener('click', async function () {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        await deferredPrompt.userChoice;
        deferredPrompt = null;
        installBtn.style.display = 'none';
      });
    }

    window.addEventListener('appinstalled', function () {
      if (installBtn) {
        installBtn.style.display = 'none';
      }
    });
  }

  function initServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js').catch(function (error) {
        console.log('Service worker registration failed:', error);
      });
    });
  }

  function boot() {
    injectAccessibilityStyles();
    applyModes();
    ensureWatermark();
    ensureAccessibilityControls();
    initInstallPrompt();
    initServiceWorker();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
