function t(t,e,i,s){var n,r=arguments.length,o=r<3?e:null===s?s=Object.getOwnPropertyDescriptor(e,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)o=Reflect.decorate(t,e,i,s);else for(var a=t.length-1;a>=0;a--)(n=t[a])&&(o=(r<3?n(o):r>3?n(e,i,o):n(e,i))||o);return r>3&&o&&Object.defineProperty(e,i,o),o}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,i=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),n=new WeakMap;let r=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(i&&void 0===t){const i=void 0!==e&&1===e.length;i&&(t=n.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&n.set(e,t))}return t}toString(){return this.cssText}};const o=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,i,s)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[s+1],t[0]);return new r(i,t,s)},a=i?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new r("string"==typeof t?t:t+"",void 0,s))(e)})(t):t,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:h,getOwnPropertySymbols:u,getPrototypeOf:p}=Object,m=globalThis,_=m.trustedTypes,g=_?_.emptyScript:"",f=m.reactiveElementPolyfillSupport,$=(t,e)=>t,y={toAttribute(t,e){switch(e){case Boolean:t=t?g:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},v=(t,e)=>!l(t,e),b={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:v};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=b){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(t,i,e);void 0!==s&&c(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){const{get:s,set:n}=d(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:s,set(e){const r=s?.call(this);n?.call(this,e),this.requestUpdate(t,r,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??b}static _$Ei(){if(this.hasOwnProperty($("elementProperties")))return;const t=p(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty($("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty($("properties"))){const t=this.properties,e=[...h(t),...u(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,s)=>{if(i)t.adoptedStyleSheets=s.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const i of s){const s=document.createElement("style"),n=e.litNonce;void 0!==n&&s.setAttribute("nonce",n),s.textContent=i.cssText,t.appendChild(s)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(void 0!==s&&!0===i.reflect){const n=(void 0!==i.converter?.toAttribute?i.converter:y).toAttribute(e,i.type);this._$Em=t,null==n?this.removeAttribute(s):this.setAttribute(s,n),this._$Em=null}}_$AK(t,e){const i=this.constructor,s=i._$Eh.get(t);if(void 0!==s&&this._$Em!==s){const t=i.getPropertyOptions(s),n="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:y;this._$Em=s;const r=n.fromAttribute(e,t.type);this[s]=r??this._$Ej?.get(s)??r,this._$Em=null}}requestUpdate(t,e,i,s=!1,n){if(void 0!==t){const r=this.constructor;if(!1===s&&(n=this[t]),i??=r.getPropertyOptions(t),!((i.hasChanged??v)(n,e)||i.useDefault&&i.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:n},r){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),!0!==n||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===s&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,s=this[e];!0!==t||this._$AL.has(e)||void 0===s||this.C(e,void 0,i,s)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[$("elementProperties")]=new Map,w[$("finalized")]=new Map,f?.({ReactiveElement:w}),(m.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const A=globalThis,x=t=>t,E=A.trustedTypes,S=E?E.createPolicy("lit-html",{createHTML:t=>t}):void 0,z="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,k="?"+C,P=`<${k}>`,R=document,O=()=>R.createComment(""),U=t=>null===t||"object"!=typeof t&&"function"!=typeof t,H=Array.isArray,M="[ \t\n\f\r]",T=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,N=/-->/g,L=/>/g,I=RegExp(`>|${M}(?:([^\\s"'>=/]+)(${M}*=${M}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),D=/'/g,j=/"/g,W=/^(?:script|style|textarea|title)$/i,Z=(t=>(e,...i)=>({_$litType$:t,strings:e,values:i}))(1),q=Symbol.for("lit-noChange"),B=Symbol.for("lit-nothing"),V=new WeakMap,F=R.createTreeWalker(R,129);function G(t,e){if(!H(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(e):e}const K=(t,e)=>{const i=t.length-1,s=[];let n,r=2===e?"<svg>":3===e?"<math>":"",o=T;for(let e=0;e<i;e++){const i=t[e];let a,l,c=-1,d=0;for(;d<i.length&&(o.lastIndex=d,l=o.exec(i),null!==l);)d=o.lastIndex,o===T?"!--"===l[1]?o=N:void 0!==l[1]?o=L:void 0!==l[2]?(W.test(l[2])&&(n=RegExp("</"+l[2],"g")),o=I):void 0!==l[3]&&(o=I):o===I?">"===l[0]?(o=n??T,c=-1):void 0===l[1]?c=-2:(c=o.lastIndex-l[2].length,a=l[1],o=void 0===l[3]?I:'"'===l[3]?j:D):o===j||o===D?o=I:o===N||o===L?o=T:(o=I,n=void 0);const h=o===I&&t[e+1].startsWith("/>")?" ":"";r+=o===T?i+P:c>=0?(s.push(a),i.slice(0,c)+z+i.slice(c)+C+h):i+C+(-2===c?e:h)}return[G(t,r+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),s]};class J{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let n=0,r=0;const o=t.length-1,a=this.parts,[l,c]=K(t,e);if(this.el=J.createElement(l,i),F.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(s=F.nextNode())&&a.length<o;){if(1===s.nodeType){if(s.hasAttributes())for(const t of s.getAttributeNames())if(t.endsWith(z)){const e=c[r++],i=s.getAttribute(t).split(C),o=/([.?@])?(.*)/.exec(e);a.push({type:1,index:n,name:o[2],strings:i,ctor:"."===o[1]?et:"?"===o[1]?it:"@"===o[1]?st:tt}),s.removeAttribute(t)}else t.startsWith(C)&&(a.push({type:6,index:n}),s.removeAttribute(t));if(W.test(s.tagName)){const t=s.textContent.split(C),e=t.length-1;if(e>0){s.textContent=E?E.emptyScript:"";for(let i=0;i<e;i++)s.append(t[i],O()),F.nextNode(),a.push({type:2,index:++n});s.append(t[e],O())}}}else if(8===s.nodeType)if(s.data===k)a.push({type:2,index:n});else{let t=-1;for(;-1!==(t=s.data.indexOf(C,t+1));)a.push({type:7,index:n}),t+=C.length-1}n++}}static createElement(t,e){const i=R.createElement("template");return i.innerHTML=t,i}}function Q(t,e,i=t,s){if(e===q)return e;let n=void 0!==s?i._$Co?.[s]:i._$Cl;const r=U(e)?void 0:e._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),void 0===r?n=void 0:(n=new r(t),n._$AT(t,i,s)),void 0!==s?(i._$Co??=[])[s]=n:i._$Cl=n),void 0!==n&&(e=Q(t,n._$AS(t,e.values),n,s)),e}class X{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??R).importNode(e,!0);F.currentNode=s;let n=F.nextNode(),r=0,o=0,a=i[0];for(;void 0!==a;){if(r===a.index){let e;2===a.type?e=new Y(n,n.nextSibling,this,t):1===a.type?e=new a.ctor(n,a.name,a.strings,this,t):6===a.type&&(e=new nt(n,this,t)),this._$AV.push(e),a=i[++o]}r!==a?.index&&(n=F.nextNode(),r++)}return F.currentNode=R,s}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class Y{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=B,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Q(this,t,e),U(t)?t===B||null==t||""===t?(this._$AH!==B&&this._$AR(),this._$AH=B):t!==this._$AH&&t!==q&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>H(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==B&&U(this._$AH)?this._$AA.nextSibling.data=t:this.T(R.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,s="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=J.createElement(G(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{const t=new X(s,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=V.get(t.strings);return void 0===e&&V.set(t.strings,e=new J(t)),e}k(t){H(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,s=0;for(const n of t)s===e.length?e.push(i=new Y(this.O(O()),this.O(O()),this,this.options)):i=e[s],i._$AI(n),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=x(t).nextSibling;x(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,n){this.type=1,this._$AH=B,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=n,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=B}_$AI(t,e=this,i,s){const n=this.strings;let r=!1;if(void 0===n)t=Q(this,t,e,0),r=!U(t)||t!==this._$AH&&t!==q,r&&(this._$AH=t);else{const s=t;let o,a;for(t=n[0],o=0;o<n.length-1;o++)a=Q(this,s[i+o],e,o),a===q&&(a=this._$AH[o]),r||=!U(a)||a!==this._$AH[o],a===B?t=B:t!==B&&(t+=(a??"")+n[o+1]),this._$AH[o]=a}r&&!s&&this.j(t)}j(t){t===B?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===B?void 0:t}}class it extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==B)}}class st extends tt{constructor(t,e,i,s,n){super(t,e,i,s,n),this.type=5}_$AI(t,e=this){if((t=Q(this,t,e,0)??B)===q)return;const i=this._$AH,s=t===B&&i!==B||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,n=t!==B&&(i===B||s);s&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class nt{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){Q(this,t)}}const rt=A.litHtmlPolyfillSupport;rt?.(J,Y),(A.litHtmlVersions??=[]).push("3.3.3");const ot=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class at extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const s=i?.renderBefore??e;let n=s._$litPart$;if(void 0===n){const t=i?.renderBefore??null;s._$litPart$=n=new Y(e.insertBefore(O(),t),t,void 0,i??{})}return n._$AI(t),n})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return q}}at._$litElement$=!0,at.finalized=!0,ot.litElementHydrateSupport?.({LitElement:at});const lt=ot.litElementPolyfillSupport;lt?.({LitElement:at}),(ot.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ct=t=>(e,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},dt={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:v},ht=(t=dt,e,i)=>{const{kind:s,metadata:n}=i;let r=globalThis.litPropertyMetadata.get(n);if(void 0===r&&globalThis.litPropertyMetadata.set(n,r=new Map),"setter"===s&&((t=Object.create(t)).wrapped=!0),r.set(i.name,t),"accessor"===s){const{name:s}=i;return{set(i){const n=e.get.call(this);e.set.call(this,i),this.requestUpdate(s,n,t,!0,i)},init(e){return void 0!==e&&this.C(s,void 0,t,e),e}}}if("setter"===s){const{name:s}=i;return function(i){const n=this[s];e.call(this,i),this.requestUpdate(s,n,t,!0,i)}}throw Error("Unsupported decorator location: "+s)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return(e,i)=>"object"==typeof i?ht(t,e,i):((t,e,i)=>{const s=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),s?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return ut({...t,state:!0,attribute:!1})}function mt(t){if(null==t||""===t)return null;const e="number"==typeof t?t:Number(t);return Number.isFinite(e)?e:null}function _t(t){return void 0===t||"unavailable"===t.state||"unknown"===t.state}function gt(t,e){return t[e]}function ft(t){const e=t?.attributes?.unit_of_measurement;return"string"==typeof e?e:null}function $t(t,e){const i=t?.attributes?.friendly_name;return"string"==typeof i&&i.length>0?i:e}function yt(t,e,i){const s=gt(t,e);return s?{entityId:e,label:i,name:$t(s,e),state:_t(s)?null:s.state,unit:ft(s),available:!_t(s)}:null}function vt(t,e){const i=[],s=[["forecast_rain_amount","Rain forecast"],["forecast_rain_probability","Rain chance"],["observed_rain_amount","Observed rain"],["temperature_sensor","Temperature"],["humidity_sensor","Humidity"]],n=Array.isArray(t.moisture_sensors)?t.moisture_sensors:[];for(const t of n){const s=yt(e,t,"Moisture sensor");s&&i.push(s)}for(const[n,r]of s){const s=t[n];if("string"==typeof s&&s){const t=yt(e,s,r);t&&i.push(t)}}const r=Array.isArray(t.safety_blockers)?t.safety_blockers:[];for(const t of r){const s=yt(e,t,"Safety blocker");s&&i.push(s)}return i}const bt=[{key:"learned_moisture_gain_per_liter",label:"Moisture Gain per Liter"},{key:"learned_daily_drying_rate",label:"Daily Drying Rate"},{key:"learned_rain_efficiency",label:"Rain Efficiency"},{key:"learned_field_capacity",label:"Field Capacity"},{key:"learned_wilting_point",label:"Wilting Point"}];function wt(t,e){const i=[];for(const s of bt){const n=`sensor.${t}_${s.key}`,r=gt(e,n);if(!r)continue;const o=r.attributes?.samples;i.push({key:s.key,label:s.label,entityId:n,value:_t(r)?null:mt(r.state),unit:ft(r),samples:"number"==typeof o?o:null})}return i}function At(t,e){const i=[];for(const s of[1,2]){const n=`time.${t}_schedule_${s}_time`,r=`switch.${t}_schedule_${s}_active`,o=gt(e,n),a=gt(e,r);if(!o&&!a)continue;const l=o&&!_t(o)?o.state:null;i.push({index:s,timeEntity:n,time:l?l.slice(0,5):null,activeEntity:r,active:"on"===a?.state,available:!_t(o)})}return i}function xt(t,e,i){const s=gt(t,e);return s?{entityId:e,label:i,state:_t(s)?null:s.state,unit:ft(s),isOn:"on"===s.state,available:!_t(s)}:null}function Et(t,e){const i=t.decision_entity?e[t.decision_entity]:void 0,s=t.moisture_entity?e[t.moisture_entity]:void 0,n=t.status_entity?e[t.status_entity]:void 0,r=t.history_entity?e[t.history_entity]:void 0,o=i?.attributes??{},a=n?.attributes??{},l=r?.attributes??{},c=s&&!_t(s)?mt(s.state):mt(o.zone_moisture),d=t.decision_entity.replace(/^sensor\./,"").replace(/_irrigation_decision$/,"");const h=o.references??{},u=gt(e,`sensor.${d}_total_watering_volume`);return{name:t.name??o.friendly_name??"Irrigation Zone",moisture:c,target:mt(o.target_moisture),recommendedLiters:mt(o.recommended_liters),availableWater:mt(o.available_water),decision:_t(i)?null:i?.state??null,decisionReason:o.reason??null,wateringStatus:_t(n)?null:n?.state??null,isWatering:!0===a.is_watering,canStop:!0===a.can_stop,historyCount:mt(r?.state)??0,lastKind:l.last_kind??null,historyEntries:Array.isArray(l.entries)?l.entries:[],greenhouse:!0===o.greenhouse,protectedRain:!0===o.protected_rain,temperature:mt(o.temperature),humidity:mt(o.humidity),references:vt(h,e),schedule:At(d,e),learned:wt(d,e),totalVolume:u&&!_t(u)?mt(u.state):null,totalVolumeUnit:ft(u),targetControl:xt(e,`number.${d}_target_moisture`,"Target Moisture"),maxLitersControl:xt(e,`number.${d}_max_liters_per_run`,"Max Liters per Run"),enabledControl:xt(e,`switch.${d}_zone_enabled`,"Zone Enabled"),learningControl:xt(e,`switch.${d}_learning_enabled`,"Learning Enabled")}}function St(t){return t?Object.keys(t).filter(t=>t.startsWith("sensor.")&&t.endsWith("_irrigation_decision")).sort():[]}let zt=class extends at{static getStubConfig(t){return{zones:St(t?.states).map(t=>({decision_entity:t}))}}static async getConfigElement(){return document.createElement("amazing-irrigation-overview-card-editor")}setConfig(t){if(!t||!Array.isArray(t.zones)||0===t.zones.length)throw new Error("amazing-irrigation-overview-card: 'zones' must list at least one zone");for(const e of t.zones)if(!e.decision_entity)throw new Error("amazing-irrigation-overview-card: each zone needs 'decision_entity'");this._config=t}getCardSize(){return this._config?this._config.zones.length+1:1}render(){if(!this._config||!this.hass)return B;const t=(e=this._config,i=this.hass.states,(Array.isArray(e.zones)?e.zones:[]).map(t=>Et(t,i)));var e,i;return Z`
      <ha-card>
        ${this._config.title?Z`<div class="title">${this._config.title}</div>`:B}
        <div class="zones">
          ${t.map(t=>this._renderRow(t))}
        </div>
      </ha-card>
    `}_renderRow(t){return Z`
      <div class="zone">
        <div class="primary">
          <span class="name">
            ${t.greenhouse?Z`<span class="gh">🌱</span>`:B}
            ${t.name}
          </span>
          <span class="decision">${t.decision??"–"}</span>
        </div>
        <div class="secondary">
          <span
            >${null===t.moisture?"–":`${t.moisture}%`}
            ${null===t.target?"":`/ ${t.target}%`}</span
          >
          <span class="status ${t.isWatering?"active":""}">
            ${t.wateringStatus??"idle"}
          </span>
          ${t.greenhouse&&t.protectedRain?Z`<span class="ctx">rain-protected</span>`:B}
          ${t.greenhouse&&null!==t.temperature?Z`<span class="ctx">${t.temperature}°C</span>`:B}
          ${t.greenhouse&&null!==t.humidity?Z`<span class="ctx">${t.humidity}% RH</span>`:B}
        </div>
      </div>
    `}};zt.styles=o`
    ha-card {
      padding: 16px;
    }
    .title {
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 8px;
    }
    .zone {
      padding: 8px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .zone:last-child {
      border-bottom: none;
    }
    .primary {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .name {
      font-weight: 600;
    }
    .gh {
      margin-right: 4px;
    }
    .decision {
      text-transform: capitalize;
      color: var(--primary-color);
      font-size: 0.9rem;
    }
    .secondary {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 2px;
      font-size: 0.8rem;
      color: var(--secondary-text-color);
    }
    .status.active {
      color: var(--primary-color);
      font-weight: 600;
    }
    .ctx {
      padding: 1px 6px;
      border-radius: 6px;
      background: var(--secondary-background-color);
    }
  `,t([ut({attribute:!1})],zt.prototype,"hass",void 0),t([pt()],zt.prototype,"_config",void 0),zt=t([ct("amazing-irrigation-overview-card")],zt),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-overview-card",name:"Amazing Irrigation Overview",description:"Compact multi-zone overview for Amazing Irrigation."});const Ct="amazing_irrigation",kt=[{name:"decision_entity",required:!0,selector:{entity:{integration:Ct,domain:"sensor"}}},{name:"name",selector:{text:{}}},{name:"moisture_entity",selector:{entity:{domain:"sensor"}}},{name:"status_entity",selector:{entity:{integration:Ct,domain:"sensor"}}},{name:"history_entity",selector:{entity:{integration:Ct,domain:"sensor"}}}],Pt=[{name:"title",selector:{text:{}}}],Rt={decision_entity:"Decision sensor (required)",name:"Zone name (optional)",moisture_entity:"Soil moisture sensor (optional)",status_entity:"Status sensor (optional)",history_entity:"History sensor (optional)",title:"Card title (optional)"},Ot=t=>Rt[t.name]??t.name;function Ut(t,e){t.dispatchEvent(new CustomEvent("config-changed",{detail:{config:e},bubbles:!0,composed:!0}))}let Ht=class extends at{setConfig(t){this._config=t}render(){return this.hass&&this._config?Z`
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${kt}
        .computeLabel=${Ot}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `:B}_valueChanged(t){t.stopPropagation(),Ut(this,t.detail.value)}};t([ut({attribute:!1})],Ht.prototype,"hass",void 0),t([pt()],Ht.prototype,"_config",void 0),Ht=t([ct("amazing-irrigation-card-editor")],Ht);let Mt=class extends at{setConfig(t){this._config={...t,zones:Array.isArray(t.zones)?t.zones:[]}}get _zones(){return this._config?.zones??[]}render(){return this.hass&&this._config?Z`
      <div class="editor">
        <ha-form
          .hass=${this.hass}
          .data=${{title:this._config.title??""}}
          .schema=${Pt}
          .computeLabel=${Ot}
          @value-changed=${this._titleChanged}
        ></ha-form>

        <div class="zones">
          ${this._zones.map((t,e)=>this._renderZone(t,e))}
          ${0===this._zones.length?Z`<div class="hint">
                Add at least one zone (select its Decision sensor).
              </div>`:B}
        </div>

        <mwc-button outlined @click=${this._addZone}>+ Add zone</mwc-button>
      </div>
    `:B}_renderZone(t,e){return Z`
      <div class="zone">
        <div class="zone-head">
          <span class="zone-title">Zone ${e+1}</span>
          <mwc-button dense @click=${()=>this._removeZone(e)}>
            Remove
          </mwc-button>
        </div>
        <ha-form
          .hass=${this.hass}
          .data=${t}
          .schema=${kt}
          .computeLabel=${Ot}
          .index=${e}
          @value-changed=${this._zoneChanged}
        ></ha-form>
      </div>
    `}_titleChanged(t){t.stopPropagation();const e=t.detail.value.title,i={...this._config,title:e};e||delete i.title,this._emit(i)}_zoneChanged(t){t.stopPropagation();const e=t.currentTarget.index;if(void 0===e)return;const i=[...this._zones];i[e]=t.detail.value,this._emit({...this._config,zones:i})}_addZone(){const t=[...this._zones,{decision_entity:""}];this._emit({...this._config,zones:t})}_removeZone(t){const e=this._zones.filter((e,i)=>i!==t);this._emit({...this._config,zones:e})}_emit(t){this._config=t,Ut(this,t)}};Mt.styles=o`
    .editor {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .zones {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .zone {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 12px;
    }
    .zone-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .zone-title {
      font-weight: 600;
    }
    .hint {
      color: var(--secondary-text-color);
      font-size: 0.9rem;
    }
    mwc-button {
      align-self: flex-start;
    }
  `,t([ut({attribute:!1})],Mt.prototype,"hass",void 0),t([pt()],Mt.prototype,"_config",void 0),Mt=t([ct("amazing-irrigation-overview-card-editor")],Mt);const Tt={run_request:"Run requested",decision:"Decision",rain_event:"Rain",watering_event:"Watering"};let Nt=class extends at{static getStubConfig(t){const[e]=St(t?.states);return{decision_entity:e??""}}static async getConfigElement(){return document.createElement("amazing-irrigation-card-editor")}setConfig(t){if(!t||!t.decision_entity)throw new Error("amazing-irrigation-card: 'decision_entity' is required");this._config=t}getCardSize(){return 4}get _view(){if(this._config&&this.hass)return Et(this._config,this.hass.states)}_callZoneService(t,e=!1){if(!this.hass||!this._config)return;const i={entity_id:this._config.decision_entity};"run_zone"===t&&(i.force=e),this.hass.callService("amazing_irrigation",t,i)}_moreInfo(t){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:t},bubbles:!0,composed:!0}))}_toggleSwitch(t){this.hass&&this.hass.callService("switch","toggle",{entity_id:t})}render(){const t=this._view;return this._config?t?Z`
      <ha-card>
        <div class="header">
          <span class="name">${t.name}</span>
          <span class="status ${t.isWatering?"active":""}">
            ${t.wateringStatus??"idle"}
          </span>
        </div>

        <div class="grid">
          ${this._metric("Moisture",this._pct(t.moisture))}
          ${this._metric("Target",this._pct(t.target))}
          ${this._metric("Recommended",null===t.recommendedLiters?"–":`${t.recommendedLiters} L`)}
          ${null===t.availableWater?B:this._metric("Available water",`${Math.round(100*t.availableWater)}%`)}
          ${null===t.totalVolume?B:this._metric("Total water",`${t.totalVolume} ${t.totalVolumeUnit??"L"}`)}
        </div>

        <div class="decision">
          <span class="decision-action">${t.decision??"–"}</span>
          ${t.decisionReason?Z`<span class="decision-reason"
                >${t.decisionReason.replace(/_/g," ")}</span
              >`:B}
        </div>

        ${this._renderGreenhouse(t)}
        ${this._renderControls(t)}
        ${this._renderSchedule(t)}
        ${this._renderLearned(t)}
        ${this._renderReferences(t)}
        ${this._renderHistory(t)}

        <div class="actions">
          <mwc-button
            raised
            ?disabled=${!1}
            @click=${()=>this._callZoneService("run_zone")}
            >Run</mwc-button
          >
          <mwc-button
            ?disabled=${!1}
            @click=${()=>this._callZoneService("run_zone",!0)}
            >Force Water</mwc-button
          >
          ${function(t){return t.canStop&&t.isWatering}(t)?Z`<mwc-button
                class="stop"
                @click=${()=>this._callZoneService("stop_zone")}
                >Stop</mwc-button
              >`:B}
        </div>
      </ha-card>
    `:Z`<ha-card><div class="empty">Loading…</div></ha-card>`:B}_renderGreenhouse(t){return t.greenhouse?Z`
      <div class="greenhouse">
        <span class="badge">🌱 Greenhouse</span>
        <span class="ctx ${t.protectedRain?"on":""}">
          ${t.protectedRain?"Protected from rain":"Open to rain"}
        </span>
        ${null!==t.temperature?Z`<span class="ctx">${t.temperature}°C</span>`:B}
        ${null!==t.humidity?Z`<span class="ctx">${t.humidity}% RH</span>`:B}
      </div>
    `:B}_renderControls(t){const e=[t.targetControl,t.maxLitersControl].filter(t=>null!==t),i=[t.enabledControl,t.learningControl].filter(t=>null!==t);return e.length||i.length?Z`
      <div class="section">
        <div class="section-head">Settings</div>
        ${e.map(t=>Z`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(t.entityId)}
            >
              <span class="row-label">${t.label}</span>
              <span class="row-value"
                >${t.state??"–"} ${t.unit??""}</span
              >
            </div>
          `)}
        ${i.map(t=>Z`
            <div class="row">
              <span class="row-label">${t.label}</span>
              <button
                class="toggle ${t.isOn?"on":""}"
                @click=${()=>this._toggleSwitch(t.entityId)}
              >
                ${t.isOn?"On":"Off"}
              </button>
            </div>
          `)}
      </div>
    `:B}_renderSchedule(t){return t.schedule.length?Z`
      <div class="section">
        <div class="section-head">Schedule</div>
        ${t.schedule.map(t=>Z`
            <div class="row">
              <span
                class="row-label clickable"
                @click=${()=>this._moreInfo(t.timeEntity)}
                >Schedule ${t.index}</span
              >
              <span
                class="row-value clickable"
                @click=${()=>this._moreInfo(t.timeEntity)}
                >${t.time??"–"}</span
              >
              <button
                class="toggle ${t.active?"on":""}"
                @click=${()=>this._toggleSwitch(t.activeEntity)}
              >
                ${t.active?"Active":"Off"}
              </button>
            </div>
          `)}
      </div>
    `:B}_renderLearned(t){return t.learned.length?Z`
      <div class="section">
        <div class="section-head">Learned model</div>
        ${t.learned.map(t=>Z`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(t.entityId)}
            >
              <span class="row-label">${t.label}</span>
              <span class="row-value">
                ${null===t.value?"learning…":`${t.value} ${t.unit??""}`}
              </span>
            </div>
          `)}
      </div>
    `:B}_renderReferences(t){return t.references.length?Z`
      <div class="section">
        <div class="section-head">Sensors</div>
        ${t.references.map(t=>Z`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(t.entityId)}
            >
              <span class="row-label">${t.label}</span>
              <span class="row-value"
                >${t.state??"–"} ${t.unit??""}</span
              >
            </div>
          `)}
      </div>
    `:B}_renderHistory(t){if(!t.historyEntries.length)return B;const e=t.historyEntries.slice(0,5);return Z`
      <div class="history">
        <div class="history-head">
          History (${t.historyCount})
        </div>
        <ul>
          ${e.map(t=>{const e=String(t.kind??"");return Z`<li>
              <span class="kind">${Tt[e]??e}</span>
              <span class="detail">${this._historyDetail(t)}</span>
            </li>`})}
        </ul>
      </div>
    `}_historyDetail(t){if(t.action)return`${t.action} (${t.reason??""})`;if(t.status){const e=t.measured_liters??t.requested_liters;return null==e?String(t.status):`${t.status} · ${e} L`}return void 0!==t.delta_mm?`+${t.delta_mm} mm`:""}_metric(t,e){return Z`<div class="metric">
      <div class="metric-value">${e}</div>
      <div class="metric-label">${t}</div>
    </div>`}_pct(t){return null===t?"–":`${t}%`}};Nt.styles=o`
    ha-card {
      padding: 16px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .name {
      font-size: 1.2rem;
      font-weight: 600;
    }
    .status {
      text-transform: capitalize;
      font-size: 0.85rem;
      color: var(--secondary-text-color);
    }
    .status.active {
      color: var(--primary-color);
      font-weight: 600;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }
    .metric {
      text-align: center;
      padding: 8px 4px;
      background: var(--secondary-background-color);
      border-radius: 8px;
    }
    .metric-value {
      font-size: 1.1rem;
      font-weight: 600;
    }
    .metric-label {
      font-size: 0.75rem;
      color: var(--secondary-text-color);
    }
    .decision {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 12px;
    }
    .decision-action {
      text-transform: capitalize;
      font-weight: 600;
    }
    .decision-reason {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
    .greenhouse {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
      margin-bottom: 12px;
    }
    .greenhouse .badge {
      font-weight: 600;
      font-size: 0.85rem;
    }
    .greenhouse .ctx {
      font-size: 0.8rem;
      padding: 2px 6px;
      border-radius: 6px;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
    }
    .greenhouse .ctx.on {
      color: var(--primary-color);
    }
    .section {
      margin-bottom: 12px;
    }
    .section-head {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }
    .row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.85rem;
      padding: 4px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .row-label {
      flex: 1;
    }
    .row-value {
      color: var(--secondary-text-color);
      text-align: right;
    }
    .clickable {
      cursor: pointer;
    }
    .clickable:hover {
      color: var(--primary-color);
    }
    .toggle {
      border: 1px solid var(--divider-color);
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
      border-radius: 12px;
      padding: 2px 10px;
      font-size: 0.75rem;
      cursor: pointer;
    }
    .toggle.on {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-color: var(--primary-color);
    }
    .history {
      margin-bottom: 12px;
    }
    .history-head {
      font-size: 0.85rem;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }
    .history ul {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .history li {
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      padding: 2px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .history .detail {
      color: var(--secondary-text-color);
    }
    .actions {
      display: flex;
      gap: 8px;
    }
    .stop {
      --mdc-theme-primary: var(--error-color);
    }
    .empty {
      padding: 16px;
      color: var(--secondary-text-color);
    }
  `,t([ut({attribute:!1})],Nt.prototype,"hass",void 0),t([pt()],Nt.prototype,"_config",void 0),Nt=t([ct("amazing-irrigation-card")],Nt),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-card",name:"Amazing Irrigation Zone",description:"Display and control a single Amazing Irrigation zone."});export{Nt as AmazingIrrigationCard};
