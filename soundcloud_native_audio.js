/* Native HLS audio for Qt builds without AAC in Chromium. Installed only in
 * the SoundCloud view, before its scripts. The official widget still owns
 * track selection, authorization, metadata, controls and playlist navigation.
 * No stream resolution, private API calls or downloaded media are involved. */
(function () {
  'use strict';
  if (location.hostname !== 'w.soundcloud.com' || location.pathname !== '/player/') return;
  var proto = HTMLMediaElement.prototype;
  if (document.createElement('audio').canPlayType('audio/mp4; codecs="mp4a.40.2"')) return;
  var token = __SYNAPSE_AUDIO_TOKEN__;
  var session = crypto.randomUUID();
  var elements = new Map(), states = new WeakMap(), nextId = 0;
  function send(command, state, extra) {
    console.log('SCNATIVE:' + JSON.stringify(Object.assign({token:token, session:session,
      command:command, id:state ? state.id : 0}, extra || {})));
  }
  function emit(state, event) { state.element.dispatchEvent(new Event(event)); }
  function later(state, event) { queueMicrotask(function () { emit(state, event); }); }
  function allowed(value) {
    if (value.length > 16384 || /[\r\n\t]/.test(value)) return false;
    try {
      var u = new URL(value);
      return u.protocol === 'https:' && !u.username && !u.password && (!u.port || u.port === '443') &&
        (u.hostname === 'sndcdn.com' || u.hostname.endsWith('.sndcdn.com') ||
         u.hostname === 'soundcloud.cloud' || u.hostname.endsWith('.soundcloud.cloud')) &&
        u.pathname.endsWith('.m3u8');
    } catch (_) { return false; }
  }
  function active(element) { return states.get(element); }
  function release(element) {
    var state = active(element);
    if (!state) return;
    send('dispose', state);
    elements.delete(state.id); states.delete(element);
    state.pending.forEach(function (p) { p.reject(new DOMException('Source changed', 'AbortError')); });
    later(state, 'emptied');
  }
  var descriptors = {};
  ['src','currentSrc','paused','ended','duration','currentTime','readyState','networkState',
   'error','buffered','seekable','seeking','volume','muted'].forEach(function (name) {
    descriptors[name] = Object.getOwnPropertyDescriptor(proto, name);
  });
  function start(element, url) {
    release(element);
    var state = {id:++nextId, element:element, url:url, paused:true, ended:false,
      duration:NaN, position:0, ready:0, seeking:false, error:null, pending:[], buffered:[]};
    states.set(element, state); elements.set(state.id, state);
    send('load', state, {url:url, volume:descriptors.volume.get.call(element),
      muted:descriptors.muted.get.call(element)});
    later(state, 'loadstart');
  }
  Object.defineProperty(proto, 'src', {
    configurable:true, enumerable:true,
    get:function () { var s=active(this); return s ? s.url : descriptors.src.get.call(this); },
    set:function (value) {
      if (this instanceof HTMLAudioElement && allowed(String(value))) start(this, String(value));
      else { release(this); descriptors.src.set.call(this, value); }
    }
  });
  var setAttribute = Element.prototype.setAttribute, removeAttribute = Element.prototype.removeAttribute;
  Element.prototype.setAttribute = function (name, value) {
    if (this instanceof HTMLAudioElement && String(name).toLowerCase()==='src' && allowed(String(value))) {
      this.src=value; return;
    }
    if (this instanceof HTMLMediaElement && String(name).toLowerCase()==='src') release(this);
    return setAttribute.call(this, name, value);
  };
  Element.prototype.removeAttribute = function (name) {
    if (this instanceof HTMLMediaElement && String(name).toLowerCase()==='src') release(this);
    return removeAttribute.call(this, name);
  };
  function ranges(values) {
    function check(i) { if (!Number.isInteger(i) || i<0 || i>=values.length) throw new DOMException('Index', 'IndexSizeError'); }
    return {length:values.length,
      start:function(i){check(i);return values[i][0];},
      end:function(i){check(i);return values[i][1];}};
  }
  var getters = {currentSrc:function(s){return s.url;}, paused:function(s){return s.paused;},
    ended:function(s){return s.ended;}, duration:function(s){return s.duration;},
    currentTime:function(s){return s.position;}, readyState:function(s){return s.ready;},
    networkState:function(s){return s.ready ? 1 : 2;}, error:function(s){return s.error;},
    seeking:function(s){return s.seeking;}, buffered:function(s){return ranges(s.buffered);},
    seekable:function(s){return ranges(s.ready && isFinite(s.duration) ? [[0,s.duration]] : []);}};
  Object.keys(getters).forEach(function (name) {
    var original=descriptors[name];
    Object.defineProperty(proto,name,{configurable:true,enumerable:true,
      get:function(){var s=active(this);return s ? getters[name](s) : original.get.call(this);},
      set: name==='currentTime' ? function(value){var s=active(this);if(!s)return original.set.call(this,value);
        var position=Number(value);if(!isFinite(position)||position<0)return;
        s.position=position;s.seeking=true;emit(s,'seeking');send('seek',s,{position:position});} : original.set});
  });
  ['volume','muted'].forEach(function(name){var original=descriptors[name];
    Object.defineProperty(proto,name,{configurable:true,enumerable:true,get:original.get,
      set:function(value){original.set.call(this,value);var s=active(this);
        if(s)send('volume',s,{volume:descriptors.volume.get.call(this),muted:descriptors.muted.get.call(this)});}});
  });
  var play=proto.play,pause=proto.pause,load=proto.load;
  proto.play=function(){var s=active(this);if(!s)return play.call(this);
    s.ended=false;send('play',s);return new Promise(function(resolve,reject){s.pending.push({resolve:resolve,reject:reject});});};
  proto.pause=function(){var s=active(this);if(!s)return pause.call(this);send('pause',s);};
  proto.load=function(){var s=active(this);if(!s)return load.call(this);send('reload',s);};
  window.addEventListener('message',function(event){
    var data=event.data;
    if(event.source!==parent || !data || data.token!==token || data.session!==session || data.type!=='synapse-native-audio')return;
    var s=elements.get(data.id);if(!s)return;
    if(data.event==='metadata'){
      var first=!s.ready;s.duration=data.duration;s.ready=4;
      if(first){emit(s,'loadedmetadata');emit(s,'loadeddata');}
      emit(s,'durationchange');emit(s,'progress');emit(s,'canplay');emit(s,'canplaythrough');
    }else if(data.event==='playing'){
      var wasPaused=s.paused;s.paused=false;s.ended=false;
      if(wasPaused)emit(s,'play');emit(s,'playing');
      s.pending.splice(0).forEach(function(p){p.resolve();});
    }else if(data.event==='pause'){
      if(!s.paused){s.paused=true;emit(s,'pause');}
      s.pending.splice(0).forEach(function(p){p.reject(new DOMException('Playback paused','AbortError'));});
    }else if(data.event==='buffer'){
      s.buffered=data.ranges;emit(s,'progress');
    }else if(data.event==='position'){
      s.position=data.position;emit(s,'timeupdate');
      if(s.seeking){s.seeking=false;emit(s,'seeked');}
    }else if(data.event==='ended'){
      s.paused=true;s.ended=true;
      if(isFinite(s.duration))s.position=s.duration;
      emit(s,'timeupdate');emit(s,'ended');
    }else if(data.event==='error'){
      s.error={code:4,message:'Native SoundCloud audio playback failed'};s.paused=true;
      s.pending.splice(0).forEach(function(p){p.reject(new DOMException(s.error.message,'NotSupportedError'));});emit(s,'error');
    }
  });
  // SoundCloud's native HLS path is selected on iOS Safari. Advertise that
  // media environment only inside this widget, backed by Anki's native mpv audio engine.
  Object.defineProperty(navigator,'userAgent',{configurable:true,get:function(){
    return 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';}});
  var canPlayType=proto.canPlayType;
  proto.canPlayType=function(type){return /mpegurl|mp4a|audio\/mp4|audio\/aac/i.test(type) ? 'probably' : canPlayType.call(this,type);};
  send('init');
})();
