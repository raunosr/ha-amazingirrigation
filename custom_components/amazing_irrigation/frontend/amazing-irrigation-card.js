function e(e,t,i,r){var n,o=arguments.length,a=o<3?t:null===r?r=Object.getOwnPropertyDescriptor(t,i):r;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,i,r);else for(var s=e.length-1;s>=0;s--)(n=e[s])&&(a=(o<3?n(a):o>3?n(t,i,a):n(t,i))||a);return o>3&&a&&Object.defineProperty(t,i,a),a}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,r=Symbol(),n=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==r)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=n.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&n.set(t,e))}return e}toString(){return this.cssText}};const a=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,r)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[r+1],e[0]);return new o(i,e,r)},s=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,r))(t)})(e):e,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:p,getOwnPropertySymbols:h,getPrototypeOf:u}=Object,m=globalThis,g=m.trustedTypes,f=g?g.emptyScript:"",v=m.reactiveElementPolyfillSupport,_=(e,t)=>e,y={toAttribute(e,t){switch(t){case Boolean:e=e?f:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},b=(e,t)=>!l(e,t),$={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:b};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let x=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=$){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),r=this.getPropertyDescriptor(e,i,t);void 0!==r&&c(this.prototype,e,r)}}static getPropertyDescriptor(e,t,i){const{get:r,set:n}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:r,set(t){const o=r?.call(this);n?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??$}static _$Ei(){if(this.hasOwnProperty(_("elementProperties")))return;const e=u(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(_("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_("properties"))){const e=this.properties,t=[...p(e),...h(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(s(e))}else void 0!==e&&t.push(s(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,r)=>{if(i)e.adoptedStyleSheets=r.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of r){const r=document.createElement("style"),n=t.litNonce;void 0!==n&&r.setAttribute("nonce",n),r.textContent=i.cssText,e.appendChild(r)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),r=this.constructor._$Eu(e,i);if(void 0!==r&&!0===i.reflect){const n=(void 0!==i.converter?.toAttribute?i.converter:y).toAttribute(t,i.type);this._$Em=e,null==n?this.removeAttribute(r):this.setAttribute(r,n),this._$Em=null}}_$AK(e,t){const i=this.constructor,r=i._$Eh.get(e);if(void 0!==r&&this._$Em!==r){const e=i.getPropertyOptions(r),n="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:y;this._$Em=r;const o=n.fromAttribute(t,e.type);this[r]=o??this._$Ej?.get(r)??o,this._$Em=null}}requestUpdate(e,t,i,r=!1,n){if(void 0!==e){const o=this.constructor;if(!1===r&&(n=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??b)(n,t)||i.useDefault&&i.reflect&&n===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:r,wrapped:n},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==n||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===r&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,r=this[t];!0!==e||this._$AL.has(t)||void 0===r||this.C(t,void 0,i,r)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[_("elementProperties")]=new Map,x[_("finalized")]=new Map,v?.({ReactiveElement:x}),(m.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const w=globalThis,k=e=>e,z=w.trustedTypes,A=z?z.createPolicy("lit-html",{createHTML:e=>e}):void 0,S="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,E="?"+C,R=`<${E}>`,P=document,T=()=>P.createComment(""),M=e=>null===e||"object"!=typeof e&&"function"!=typeof e,L=Array.isArray,O="[ \t\n\f\r]",I=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,H=/-->/g,U=/>/g,D=RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),j=/'/g,B=/"/g,Z=/^(?:script|style|textarea|title)$/i,F=(e=>(t,...i)=>({_$litType$:e,strings:t,values:i}))(1),N=Symbol.for("lit-noChange"),W=Symbol.for("lit-nothing"),q=new WeakMap,V=P.createTreeWalker(P,129);function G(e,t){if(!L(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==A?A.createHTML(t):t}const Y=(e,t)=>{const i=e.length-1,r=[];let n,o=2===t?"<svg>":3===t?"<math>":"",a=I;for(let t=0;t<i;t++){const i=e[t];let s,l,c=-1,d=0;for(;d<i.length&&(a.lastIndex=d,l=a.exec(i),null!==l);)d=a.lastIndex,a===I?"!--"===l[1]?a=H:void 0!==l[1]?a=U:void 0!==l[2]?(Z.test(l[2])&&(n=RegExp("</"+l[2],"g")),a=D):void 0!==l[3]&&(a=D):a===D?">"===l[0]?(a=n??I,c=-1):void 0===l[1]?c=-2:(c=a.lastIndex-l[2].length,s=l[1],a=void 0===l[3]?D:'"'===l[3]?B:j):a===B||a===j?a=D:a===H||a===U?a=I:(a=D,n=void 0);const p=a===D&&e[t+1].startsWith("/>")?" ":"";o+=a===I?i+R:c>=0?(r.push(s),i.slice(0,c)+S+i.slice(c)+C+p):i+C+(-2===c?t:p)}return[G(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),r]};class K{constructor({strings:e,_$litType$:t},i){let r;this.parts=[];let n=0,o=0;const a=e.length-1,s=this.parts,[l,c]=Y(e,t);if(this.el=K.createElement(l,i),V.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(r=V.nextNode())&&s.length<a;){if(1===r.nodeType){if(r.hasAttributes())for(const e of r.getAttributeNames())if(e.endsWith(S)){const t=c[o++],i=r.getAttribute(e).split(C),a=/([.?@])?(.*)/.exec(t);s.push({type:1,index:n,name:a[2],strings:i,ctor:"."===a[1]?te:"?"===a[1]?ie:"@"===a[1]?re:ee}),r.removeAttribute(e)}else e.startsWith(C)&&(s.push({type:6,index:n}),r.removeAttribute(e));if(Z.test(r.tagName)){const e=r.textContent.split(C),t=e.length-1;if(t>0){r.textContent=z?z.emptyScript:"";for(let i=0;i<t;i++)r.append(e[i],T()),V.nextNode(),s.push({type:2,index:++n});r.append(e[t],T())}}}else if(8===r.nodeType)if(r.data===E)s.push({type:2,index:n});else{let e=-1;for(;-1!==(e=r.data.indexOf(C,e+1));)s.push({type:7,index:n}),e+=C.length-1}n++}}static createElement(e,t){const i=P.createElement("template");return i.innerHTML=e,i}}function X(e,t,i=e,r){if(t===N)return t;let n=void 0!==r?i._$Co?.[r]:i._$Cl;const o=M(t)?void 0:t._$litDirective$;return n?.constructor!==o&&(n?._$AO?.(!1),void 0===o?n=void 0:(n=new o(e),n._$AT(e,i,r)),void 0!==r?(i._$Co??=[])[r]=n:i._$Cl=n),void 0!==n&&(t=X(e,n._$AS(e,t.values),n,r)),t}class J{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,r=(e?.creationScope??P).importNode(t,!0);V.currentNode=r;let n=V.nextNode(),o=0,a=0,s=i[0];for(;void 0!==s;){if(o===s.index){let t;2===s.type?t=new Q(n,n.nextSibling,this,e):1===s.type?t=new s.ctor(n,s.name,s.strings,this,e):6===s.type&&(t=new ne(n,this,e)),this._$AV.push(t),s=i[++a]}o!==s?.index&&(n=V.nextNode(),o++)}return V.currentNode=P,r}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,r){this.type=2,this._$AH=W,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=r,this._$Cv=r?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=X(this,e,t),M(e)?e===W||null==e||""===e?(this._$AH!==W&&this._$AR(),this._$AH=W):e!==this._$AH&&e!==N&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>L(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==W&&M(this._$AH)?this._$AA.nextSibling.data=e:this.T(P.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,r="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=K.createElement(G(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===r)this._$AH.p(t);else{const e=new J(r,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=q.get(e.strings);return void 0===t&&q.set(e.strings,t=new K(e)),t}k(e){L(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,r=0;for(const n of e)r===t.length?t.push(i=new Q(this.O(T()),this.O(T()),this,this.options)):i=t[r],i._$AI(n),r++;r<t.length&&(this._$AR(i&&i._$AB.nextSibling,r),t.length=r)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,r,n){this.type=1,this._$AH=W,this._$AN=void 0,this.element=e,this.name=t,this._$AM=r,this.options=n,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=W}_$AI(e,t=this,i,r){const n=this.strings;let o=!1;if(void 0===n)e=X(this,e,t,0),o=!M(e)||e!==this._$AH&&e!==N,o&&(this._$AH=e);else{const r=e;let a,s;for(e=n[0],a=0;a<n.length-1;a++)s=X(this,r[i+a],t,a),s===N&&(s=this._$AH[a]),o||=!M(s)||s!==this._$AH[a],s===W?e=W:e!==W&&(e+=(s??"")+n[a+1]),this._$AH[a]=s}o&&!r&&this.j(e)}j(e){e===W?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===W?void 0:e}}class ie extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==W)}}class re extends ee{constructor(e,t,i,r,n){super(e,t,i,r,n),this.type=5}_$AI(e,t=this){if((e=X(this,e,t,0)??W)===N)return;const i=this._$AH,r=e===W&&i!==W||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,n=e!==W&&(i===W||r);r&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ne{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){X(this,e)}}const oe=w.litHtmlPolyfillSupport;oe?.(K,Q),(w.litHtmlVersions??=[]).push("3.3.3");const ae=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class se extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const r=i?.renderBefore??t;let n=r._$litPart$;if(void 0===n){const e=i?.renderBefore??null;r._$litPart$=n=new Q(t.insertBefore(T(),e),e,void 0,i??{})}return n._$AI(e),n})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return N}}se._$litElement$=!0,se.finalized=!0,ae.litElementHydrateSupport?.({LitElement:se});const le=ae.litElementPolyfillSupport;le?.({LitElement:se}),(ae.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ce=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},de={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:b},pe=(e=de,t,i)=>{const{kind:r,metadata:n}=i;let o=globalThis.litPropertyMetadata.get(n);if(void 0===o&&globalThis.litPropertyMetadata.set(n,o=new Map),"setter"===r&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===r){const{name:r}=i;return{set(i){const n=t.get.call(this);t.set.call(this,i),this.requestUpdate(r,n,e,!0,i)},init(t){return void 0!==t&&this.C(r,void 0,e,t),t}}}if("setter"===r){const{name:r}=i;return function(i){const n=this[r];t.call(this,i),this.requestUpdate(r,n,e,!0,i)}}throw Error("Unsupported decorator location: "+r)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function he(e){return(t,i)=>"object"==typeof i?pe(e,t,i):((e,t,i)=>{const r=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),r?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ue(e){return he({...e,state:!0,attribute:!1})}function me(e){if(null==e||""===e)return null;const t="number"==typeof e?e:Number(e);return Number.isFinite(t)?t:null}function ge(e){return void 0===e||"unavailable"===e.state||"unknown"===e.state}function fe(e,t){return e[t]}function ve(e){const t=e?.attributes?.unit_of_measurement;return"string"==typeof t?t:null}function _e(e,t){const i=e?.attributes?.friendly_name;return"string"==typeof i&&i.length>0?i:t}function ye(e,t,i){const r=fe(e,t);return r?{entityId:t,label:i,name:_e(r,t),state:ge(r)?null:r.state,unit:ve(r),available:!ge(r)}:null}function be(e,t){const i=[],r=[["forecast_rain_amount","Rain forecast"],["forecast_rain_probability","Rain chance"],["weather_forecast_entity","Weather forecast"],["observed_rain_amount","Observed rain"],["temperature_sensor","Temperature"],["humidity_sensor","Humidity"],["observed_air_temperature","Air temperature"],["observed_air_humidity","Air humidity"],["forecast_air_temperature","Forecast air temp"],["forecast_air_humidity","Forecast air humidity"],["wind_speed","Wind speed"],["solar_radiation","Solar"]],n=Array.isArray(e.moisture_sensors)?e.moisture_sensors:[];for(const e of n){const r=ye(t,e,"Moisture sensor");r&&i.push(r)}for(const[n,o]of r){const r=e[n];if("string"==typeof r&&r){const e=ye(t,r,o);e&&i.push(e)}}const o=Array.isArray(e.safety_blockers)?e.safety_blockers:[];for(const e of o){const r=ye(t,e,"Safety blocker");r&&i.push(r)}return i}const $e=[{key:"learned_moisture_gain_per_liter",label:"Moisture Gain per Liter"},{key:"learned_daily_drying_rate",label:"Daily Drying Rate"},{key:"learned_rain_efficiency",label:"Rain Efficiency"},{key:"learned_field_capacity",label:"Field Capacity"},{key:"learned_wilting_point",label:"Wilting Point"}],xe=[{key:"eta_irr",label:"Irrigation Efficiency"},{key:"eta_rain",label:"Rain Efficiency"},{key:"k_et",label:"ET Coefficient"},{key:"drain_rate",label:"Drainage Rate"},{key:"field_capacity",label:"Field Capacity"},{key:"wilting_point",label:"Wilting Point"}],we={irrigation:"Irrigation added",rain:"Rain added",et:"Evapotranspiration loss",drainage:"Drainage loss"};function ke(e){return null===e||"object"!=typeof e||Array.isArray(e)?null:e}function ze(e,t){const i=[];for(const r of $e){const n=`sensor.${e}_${r.key}`,o=fe(t,n);if(!o)continue;const a=o.attributes?.samples;i.push({key:r.key,label:r.label,entityId:n,value:ge(o)?null:me(o.state),unit:ve(o),samples:"number"==typeof a?a:null})}return i}function Ae(e){return Array.isArray(e)?e.map(me).filter(e=>null!==e):[]}function Se(e,t){const i=ke(e.decision_explanation)??ke(t.explanation),r=function(e){const t=ke(e?.water_balance_terms)??ke(e?.terms);return t?Object.entries(t).map(([e,t])=>{const i=me(t);return null===i?null:{key:e,label:we[e]??e.replace(/_/g," "),value:i,unit:"%"}}).filter(e=>null!==e):[]}({...i??{},...e}),n=Ae(e.predicted_trajectory).length>0?Ae(e.predicted_trajectory):Ae(t.predicted_trajectory).length>0?Ae(t.predicted_trajectory):Ae(i?.predicted_trajectory),o=me(e.horizon_hours)??me(t.horizon_hours)??me(i?.horizon_hours),a=me(e.chosen_liters)??me(i?.chosen_liters)??me(t.recommended_liters),s=me(e.predicted_critical_theta)??me(i?.predicted_critical_theta_with_water)??me(i?.predicted_critical_theta_without_water),l=me(e.predicted_peak_theta)??me(i?.predicted_peak_theta);return r.length||n.length||null!==o||null!==a?{terms:r,predictedTrajectory:n,horizonHours:o,predictiveReason:t.reason??null,chosenLiters:a,predictedCriticalTheta:s,predictedPeakTheta:l}:null}function Ce(e,t,i){const r=`sensor.${e}_model_insight`,n=fe(t,r),o=n?.attributes??{},a=function(e){const t=ke(e.parameters),i=ke(e.confidence);return t?xe.map(e=>{const r=ke(t[e.key]);return r?{key:e.key,label:"string"==typeof r.name?r.name:e.label,value:me(r.value),unit:"string"==typeof r.unit?r.unit:null,confidence:me(r.confidence)??me(i?.[e.key])}:null}).filter(e=>null!==e&&(null!==e.value||null!==e.confidence)):[]}(o),s=Se(o,i),l=me(o.bootstrapped_days),c="string"==typeof o.bootstrap_summary?o.bootstrap_summary:null;return a.length||null!==s||null!==l?{entityId:r,status:ge(n)?null:n?.state??null,parameters:a,overallConfidence:me(o.overall_confidence),bootstrappedDays:l,bootstrapSummary:c,modelUpdated:"string"==typeof o.model_updated?o.model_updated:null,totalLiters:me(o.total_liters),decisionExplanation:s}:null}function Ee(e,t){const i=[];for(const r of[1,2]){const n=`time.${e}_schedule_${r}_time`,o=`switch.${e}_schedule_${r}_active`,a=fe(t,n),s=fe(t,o);if(!a&&!s)continue;const l=a&&!ge(a)?a.state:null;i.push({index:r,timeEntity:n,time:l?l.slice(0,5):null,activeEntity:o,active:"on"===s?.state,available:!ge(a)})}return i}function Re(e,t,i){const r=fe(e,t);return r?{entityId:t,label:i,state:ge(r)?null:r.state,unit:ve(r),isOn:"on"===r.state,available:!ge(r)}:null}function Pe(e,t){const i=e.decision_entity?t[e.decision_entity]:void 0,r=e.moisture_entity?t[e.moisture_entity]:void 0,n=e.status_entity?t[e.status_entity]:void 0,o=e.history_entity?t[e.history_entity]:void 0,a=i?.attributes??{},s=n?.attributes??{},l=o?.attributes??{},c=r&&!ge(r)?me(r.state):me(a.zone_moisture),d=e.decision_entity.replace(/^sensor\./,"").replace(/_irrigation_decision$/,"");const p=a.references??{},h=fe(t,`sensor.${d}_total_watering_volume`);return{name:e.name??a.friendly_name??"Irrigation Zone",moisture:c,target:me(a.target_moisture),recommendedLiters:me(a.recommended_liters),availableWater:me(a.available_water),decision:ge(i)?null:i?.state??null,decisionReason:a.reason??null,wateringStatus:ge(n)?null:n?.state??null,isWatering:!0===s.is_watering,canStop:!0===s.can_stop,historyCount:me(o?.state)??0,lastKind:l.last_kind??null,historyEntries:Array.isArray(l.entries)?l.entries:[],greenhouse:!0===a.greenhouse,protectedRain:!0===a.protected_rain,temperature:me(a.temperature),humidity:me(a.humidity),targetMode:"string"==typeof a.target_mode?a.target_mode:null,demandProfile:"string"==typeof a.demand_profile?a.demand_profile:null,targetBandLow:me(a.target_band_low),targetBandHigh:me(a.target_band_high),references:be(p,t),schedule:Ee(d,t),learned:ze(d,t),totalVolume:h&&!ge(h)?me(h.state):null,totalVolumeUnit:ve(h),targetControl:Re(t,`number.${d}_target_moisture`,"Target Moisture"),autoTargetControl:Re(t,`switch.${d}_target_automatic`,"Automatic Target"),maxLitersControl:Re(t,`number.${d}_max_liters_per_run`,"Max Liters per Run"),soilTypeControl:Re(t,`select.${d}_soil_type`,"Soil Type"),plantProfileControl:Re(t,`select.${d}_plant_profile`,"Plant Profile"),sensorDepthControl:Re(t,`number.${d}_sensor_depth`,"Sensor Depth"),rainFractionControl:Re(t,`number.${d}_rain_fraction`,"Rain Fraction"),minApplicationControl:Re(t,`number.${d}_minimum_application`,"Minimum Application"),sensorDepthShallow:!0===a.sensor_depth_shallow,enabledControl:Re(t,`switch.${d}_zone_enabled`,"Zone Enabled"),learningControl:Re(t,`switch.${d}_learning_enabled`,"Learning Enabled"),modelInsight:Ce(d,t,a)}}function Te(e){return e.canStop&&e.isWatering}function Me(e){return e?Object.keys(e).filter(e=>e.startsWith("sensor.")&&e.endsWith("_irrigation_decision")).sort():[]}const Le={run_request:"Run requested",decision:"Decision",rain_event:"Rain",watering_event:"Watering"},Oe={predicted_sufficient_moisture:"Soil moisture is on track",sufficient_moisture:"Soil moisture is on track",rain_expected:"Rain expected, holding off",rain_protected:"Sheltered from rain",below_target:"Below target, watering needed",schedule:"On schedule",manual:"Manual run",forced:"Forced by you",learning:"Still learning this zone"};function Ie(e){return Oe[e]??e.replace(/_/g," ")}const He="mdi:sprinkler-variant";let Ue=class extends se{constructor(){super(...arguments),this._activeZoneIndex=null,this._actionPending=null,this._actionResult=null,this._forceArmed=!1}static getStubConfig(e){return{zones:Me(e?.states).map(e=>({decision_entity:e}))}}static async getConfigElement(){return document.createElement("amazing-irrigation-overview-card-editor")}setConfig(e){if(!e||!Array.isArray(e.zones)||0===e.zones.length)throw new Error("amazing-irrigation-overview-card: 'zones' must list at least one zone");for(const t of e.zones)if(!t.decision_entity)throw new Error("amazing-irrigation-overview-card: each zone needs 'decision_entity'");this._config=e}getCardSize(){return this._config?Math.ceil(this._config.zones.length/2)+2:3}_openZone(e){this._activeZoneIndex=e,this._disarmForce(),this._actionResult=null}_closeZone(){this._activeZoneIndex=null,this._disarmForce()}_disarmForce(){this._forceArmed=!1,this._forceArmTimer&&clearTimeout(this._forceArmTimer)}_armForce(){this._forceArmed=!0,this._forceArmTimer&&clearTimeout(this._forceArmTimer),this._forceArmTimer=setTimeout(()=>{this._forceArmed=!1},5e3)}async _callZoneService(e,t,i=!1){if(!this.hass||this._actionPending)return;const r="stop_zone"===t?"stop":i?"force":"run";this._actionPending=r,this._actionResult=null,this._disarmForce(),this._actionResultTimer&&clearTimeout(this._actionResultTimer);const n={entity_id:e};"run_zone"===t&&(n.force=i);try{await this.hass.callService("amazing_irrigation",t,n);const e="stop"===r?"Stop sent":i?"Force sent":"Run sent";this._actionResult={kind:"ok",text:e},this._lastFailed=void 0,this._actionResultTimer=setTimeout(()=>{this._actionResult=null},4e3)}catch(r){const n=r instanceof Error&&r.message?r.message:"Service unavailable";this._actionResult={kind:"error",text:n},this._lastFailed={entity:e,service:t,force:i},this._actionResultTimer=setTimeout(()=>{this._actionResult=null},8e3)}finally{this._actionPending=null}}_retryLast(){if(this._lastFailed){const{entity:e,service:t,force:i}=this._lastFailed;this._callZoneService(e,t,i)}}async _runAll(){if(!this.hass||!this._config||this._actionPending)return;this._actionPending="all",this._actionResult=null,this._actionResultTimer&&clearTimeout(this._actionResultTimer);let e=0,t=0;for(const i of this._config.zones)try{await this.hass.callService("amazing_irrigation","run_zone",{entity_id:i.decision_entity,force:!1}),e+=1}catch{t+=1}this._actionResult={kind:t?"error":"ok",text:t?`${e} run, ${t} failed`:`Run sent to ${e} zones`},this._actionPending=null,this._actionResultTimer=setTimeout(()=>{this._actionResult=null},t?8e3:4e3)}_quickRun(e,t){e.stopPropagation();const i=this._config?.zones[t];i&&this._callZoneService(i.decision_entity,"run_zone")}disconnectedCallback(){super.disconnectedCallback(),this._actionResultTimer&&clearTimeout(this._actionResultTimer),this._forceArmTimer&&clearTimeout(this._forceArmTimer)}_moreInfo(e){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:e},bubbles:!0,composed:!0}))}_toggleSwitch(e){this.hass&&this.hass.callService("switch","toggle",{entity_id:e})}render(){if(!this._config||!this.hass)return W;if(null!==this._activeZoneIndex){const e=this._config.zones[this._activeZoneIndex];if(!e)return this._activeZoneIndex=null,W;const t=Pe(e,this.hass.states);return this._renderDetail(t,e)}return this._renderOverview()}_renderOverview(){const e=(t=this._config,i=this.hass.states,(Array.isArray(t.zones)?t.zones:[]).map(e=>Pe(e,i)));var t,i;const r=e.length>1;return F`
      <ha-card>
        <div class="overview-header">
          ${this._config.title?F`<div class="card-header">${this._config.title}</div>`:F`<span></span>`}
          ${r?F`<button
                class="run-all-btn"
                title="Run every zone the model allows"
                ?disabled=${!!this._actionPending}
                @click=${this._runAll}
              >
                ${"all"===this._actionPending?F`<ha-circular-progress
                      indeterminate
                      size="small"
                    ></ha-circular-progress>`:F`<ha-icon icon="mdi:play-circle-outline"></ha-icon>`}
                Run all
              </button>`:W}
        </div>
        ${this._actionResult?F`<div class="action-feedback overview ${this._actionResult.kind}">
              <ha-icon
                icon=${"ok"===this._actionResult.kind?"mdi:check-circle-outline":"mdi:alert-circle-outline"}
              ></ha-icon>
              ${this._actionResult.text}
            </div>`:W}
        <div class="zone-grid">
          ${e.map((e,t)=>this._renderZoneTile(e,t))}
        </div>
      </ha-card>
    `}_renderZoneTile(e,t){const i=this._config.zones[t].icon||He,r=null===e.moisture&&null===e.decision,n=null!==e.moisture&&null!==e.target&&e.target>0?Math.min(100,Math.round(e.moisture/e.target*100)):e.moisture??0,o=r?"setup":e.isWatering?"watering":"skip"===e.decision?"skip":"water"===e.decision?"pending-water":"";return F`
      <button
        class="zone-tile ${o}"
        title="Open ${e.name}"
        @click=${()=>this._openZone(t)}
      >
        <div class="tile-icon-wrap">
          <ha-icon .icon=${i}></ha-icon>
          ${e.isWatering?F`<span class="tile-pulse"></span>`:W}
        </div>
        <span class="tile-name">${e.name}</span>
        ${r?F`<span class="tile-setup">Setting up…</span>`:F`
              <div class="tile-bar-track">
                <div class="tile-bar-fill" style="width: ${n}%"></div>
                ${null!==e.target?F`<div
                      class="tile-bar-target"
                      style="left: ${Math.min(100,e.target)}%"
                    ></div>`:W}
              </div>
              <div class="tile-stats">
                <span class="tile-moisture"
                  >${null!==e.moisture?`${e.moisture}%`:"–"}</span
                >
                ${null!==e.target?F`<span class="tile-target">/ ${e.target}%</span>`:W}
              </div>
            `}
        ${r?W:F`<span
              class="tile-run"
              title="Run ${e.name} now"
              ?disabled=${!!this._actionPending}
              @click=${e=>this._quickRun(e,t)}
            >
              <ha-icon icon="mdi:play"></ha-icon>
            </span>`}
      </button>
    `}_renderDetail(e,t){const i=null===e.moisture&&null===e.decision&&!e.modelInsight?.decisionExplanation?.predictedTrajectory.length;return F`
      <ha-card class="detail-card">
        <div class="detail-header">
          <button class="back-btn" title="Back to all zones" @click=${this._closeZone}>
            <ha-icon icon="mdi:arrow-left"></ha-icon>
          </button>
          <ha-icon
            class="detail-icon"
            .icon=${t.icon||He}
          ></ha-icon>
          <div class="detail-title">
            <span class="detail-name">${e.name}</span>
            <span class="detail-status ${e.isWatering?"active":""}">
              ${e.wateringStatus??"idle"}
            </span>
          </div>
        </div>

        ${i?F`<div class="onboarding">
              <ha-icon icon="mdi:leaf-circle-outline"></ha-icon>
              <div class="onboarding-text">
                <strong>Getting to know this zone</strong>
                <span
                  >No moisture data yet. The model needs a few days of readings
                  before it can predict and schedule. You can still
                  <em>Run</em> the zone manually below.</span
                >
              </div>
            </div>`:W}

        ${this._renderMoistureSection(e)}
        ${this._renderDecisionBanner(e)}
        ${this._renderPrediction(e)}
        ${this._renderGreenhouse(e)}
        ${this._renderControls(e)}
        ${this._renderSchedule(e)}
        ${this._renderModelInsight(e)}
        ${this._renderReferences(e)}
        ${this._renderHistory(e)}

        <div class="detail-actions">
          <mwc-button
            raised
            title="Water now, respecting the model's recommended amount"
            ?disabled=${!!this._actionPending}
            @click=${()=>this._callZoneService(t.decision_entity,"run_zone")}
          >
            ${"run"===this._actionPending?F`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`:F`<ha-icon icon="mdi:play" slot="icon"></ha-icon>`}
            Run
          </mwc-button>
          <mwc-button
            class="force-btn ${this._forceArmed?"armed":""}"
            title="Override the model and water regardless of conditions"
            ?disabled=${!!this._actionPending}
            @click=${()=>{this._forceArmed?this._callZoneService(t.decision_entity,"run_zone",!0):this._armForce()}}
          >
            ${"force"===this._actionPending?F`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`:F`<ha-icon
                  icon=${this._forceArmed?"mdi:alert":"mdi:water"}
                  slot="icon"
                ></ha-icon>`}
            ${this._forceArmed?"Confirm Force":"Force"}
          </mwc-button>
          ${Te(e)?F`<mwc-button
                class="stop-btn"
                title="Stop the current watering run"
                ?disabled=${!!this._actionPending}
                @click=${()=>this._callZoneService(t.decision_entity,"stop_zone")}
              >
                ${"stop"===this._actionPending?F`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`:F`<ha-icon icon="mdi:stop" slot="icon"></ha-icon>`}
                Stop
              </mwc-button>`:W}
          ${this._actionResult?F`<span class="action-feedback ${this._actionResult.kind}">
                <ha-icon
                  icon=${"ok"===this._actionResult.kind?"mdi:check-circle-outline":"mdi:alert-circle-outline"}
                ></ha-icon>
                ${this._actionResult.text}
                ${"error"===this._actionResult.kind&&this._lastFailed?F`<button class="retry-btn" @click=${this._retryLast}>
                      Retry
                    </button>`:W}
              </span>`:W}
        </div>
      </ha-card>
    `}_renderMoistureSection(e){const t=e.targetBandLow??e.target??0,i=e.targetBandHigh??e.target??100,r=e.moisture??0,n=Math.min(100,Math.max(0,r));return F`
      <div class="moisture-section">
        <div class="moisture-gauge">
          <div class="gauge-labels">
            <span class="gauge-current">${e.moisture??"–"}%</span>
            <span class="gauge-sublabel">Zone Moisture</span>
          </div>
          <div class="gauge-bar-wrap">
            <div class="gauge-bar-track">
              ${null!==e.targetBandLow&&null!==e.targetBandHigh?F`<div
                    class="gauge-target-band"
                    style="left: ${t}%; width: ${i-t}%"
                  ></div>`:null!==e.target?F`<div
                      class="gauge-target-line"
                      style="left: ${e.target}%"
                    ></div>`:W}
              <div class="gauge-fill" style="width: ${n}%"></div>
              <div class="gauge-marker" style="left: ${n}%"></div>
            </div>
            <div class="gauge-ticks">
              <span>0%</span>
              ${null!==e.targetBandLow?F`<span style="left:${t}%">${Math.round(t)}</span>`:W}
              ${null!==e.targetBandHigh?F`<span style="left:${i}%">${Math.round(i)}</span>`:W}
              <span>100%</span>
            </div>
          </div>
        </div>

        <div class="metric-row">
          ${this._metric("Target","auto"===e.targetMode&&null!==e.targetBandLow&&null!==e.targetBandHigh?`${Math.round(e.targetBandLow)}–${Math.round(e.targetBandHigh)}%`:null!==e.target?`${e.target}%`:"–")}
          ${null!==e.recommendedLiters?this._metric("Recommended",`${e.recommendedLiters} L`):W}
          ${null!==e.availableWater?this._metric("Available",`${Math.round(100*e.availableWater)}%`):W}
          ${null!==e.totalVolume?this._metric("Total Used",`${e.totalVolume} ${e.totalVolumeUnit??"L"}`):W}
        </div>
      </div>
    `}_renderDecisionBanner(e){if(!e.decision)return W;const t="water"===e.decision?"water":"skip"===e.decision?"skip":"neutral";return F`
      <div class="decision-banner ${t}">
        <span class="decision-label">${e.decision}</span>
        ${e.decisionReason?F`<span class="decision-reason"
              >${Ie(e.decisionReason)}</span
            >`:W}
      </div>
    `}_renderPrediction(e){const t=e.modelInsight?.decisionExplanation;if(!t||!t.predictedTrajectory.length)return W;const i=t.predictedTrajectory,r=t.horizonHours??i.length,n=i.length>1?r/(i.length-1):1,o=e.targetBandLow??(null!==e.target?e.target-2:null),a=e.targetBandHigh??(null!==e.target?e.target+2:null),s=Math.min(...i),l=Math.max(...i),c=5*Math.floor(Math.min(s,o??s,0)/5),d=5*Math.ceil(Math.max(l,a??l,e.target??0)/5)+5,p=d-c||1,h=32,u=300,m=100,g=e=>h+e/(i.length-1)*u,f=e=>112-(e-c)/p*m,v=i.map((e,t)=>`${0===t?"M":"L"}${g(t).toFixed(1)},${f(e).toFixed(1)}`).join(" "),_=v+` L${g(i.length-1).toFixed(1)},${f(c).toFixed(1)}`+` L${g(0).toFixed(1)},${f(c).toFixed(1)} Z`,y=[],b=p<=30?5:p<=60?10:20;for(let e=c;e<=d;e+=b)y.push(e);const $=[],x=i.length<=8?1:i.length<=16?2:Math.ceil(i.length/8);for(let e=0;e<i.length;e+=x)$.push({i:e,label:`+${Math.round(e*n)}h`});$[$.length-1]?.i!==i.length-1&&$.push({i:i.length-1,label:`+${Math.round(r)}h`});const w=t.predictedCriticalTheta,k=t.predictedPeakTheta,z=null!==w?i.indexOf(Math.min(...i)):null,A=null!==k?i.indexOf(Math.max(...i)):null;return F`
      <div class="prediction-section">
        <div class="section-label">
          Moisture Prediction
          <ha-icon
            class="help-dot"
            icon="mdi:help-circle-outline"
            title="Forecast soil moisture over the coming hours. Shaded band is the target range; dots are the critical low and peak."
          ></ha-icon>
          ${null!==t.horizonHours?F`<span class="sublabel">${t.horizonHours}h horizon</span>`:W}
        </div>

        <svg
          class="prediction-chart"
          viewBox="0 0 ${340} ${136}"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <linearGradient id="pred-fill-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--primary-color)" stop-opacity="0.18" />
              <stop offset="100%" stop-color="var(--primary-color)" stop-opacity="0.02" />
            </linearGradient>
          </defs>

          <!-- Y-axis gridlines + labels -->
          ${y.map(e=>F`
              <line
                x1="${h}" y1="${f(e)}" x2="${332}" y2="${f(e)}"
                class="pred-grid"
              />
              <text x="${28}" y="${f(e)+3}" class="pred-y-label">${e}</text>
            `)}

          <!-- Target band shading -->
          ${null!==o&&null!==a?F`<rect
                x="${h}" y="${f(a)}"
                width="${u}" height="${Math.abs(f(o)-f(a))}"
                class="pred-target-band"
              />`:W}

          <!-- Target line -->
          ${null!==e.target?F`<line
                x1="${h}" y1="${f(e.target)}"
                x2="${332}" y2="${f(e.target)}"
                class="pred-target-line"
              />`:W}

          <!-- Area fill -->
          <path d="${_}" class="pred-area" />

          <!-- Line -->
          <path d="${v}" class="pred-line" />

          <!-- Data points -->
          ${i.map((e,t)=>F`
              <circle
                cx="${g(t)}" cy="${f(e)}" r="2.5"
                class="pred-dot"
              />
            `)}

          <!-- Critical / Peak markers -->
          ${null!==z&&null!==w?F`<circle
                cx="${g(z)}" cy="${f(i[z])}" r="4"
                class="pred-marker-critical"
              />`:W}
          ${null!==A&&null!==k?F`<circle
                cx="${g(A)}" cy="${f(i[A])}" r="4"
                class="pred-marker-peak"
              />`:W}

          <!-- X-axis labels -->
          ${$.map(({i:e,label:t})=>F`
              <text
                x="${g(e)}" y="${128}"
                class="pred-x-label"
              >${t}</text>
            `)}

          <!-- Current moisture marker (first point) -->
          <text
            x="${g(0)+4}" y="${f(i[0])-6}"
            class="pred-value-label"
          >${Math.round(i[0])}%</text>

          <!-- End value label -->
          <text
            x="${g(i.length-1)-4}" y="${f(i[i.length-1])-6}"
            class="pred-value-label end"
          >${Math.round(i[i.length-1])}%</text>
        </svg>

        <div class="pred-legend">
          ${null!==e.target?F`<span class="pred-legend-item">
                <span class="pred-swatch target"></span>Target ${e.target}%
              </span>`:W}
          ${null!==w?F`<span class="pred-legend-item">
                <span class="pred-swatch critical"></span>Low ${w}%
              </span>`:W}
          ${null!==k?F`<span class="pred-legend-item">
                <span class="pred-swatch peak"></span>Peak ${k}%
              </span>`:W}
          ${null!==t.chosenLiters?F`<span class="pred-legend-item">
                <ha-icon icon="mdi:water" style="--mdc-icon-size:14px"></ha-icon>
                ${t.chosenLiters} L
              </span>`:W}
        </div>

        <!-- Water balance terms breakdown -->
        ${t.terms.length?F`<div class="pred-terms">
              ${t.terms.map(e=>F`
                  <div class="pred-term">
                    <span class="pred-term-label">${e.label}</span>
                    <span class="pred-term-value ${e.value>=0?"positive":"negative"}">
                      ${e.value>=0?"+":""}${e.value.toFixed(1)}${e.unit}
                    </span>
                  </div>
                `)}
            </div>`:W}
      </div>
    `}_renderGreenhouse(e){return e.greenhouse?F`
      <div class="info-row greenhouse-row">
        <ha-icon icon="mdi:greenhouse"></ha-icon>
        <span>Greenhouse</span>
        <span class="chip ${e.protectedRain?"on":""}">
          ${e.protectedRain?"Rain protected":"Open to rain"}
        </span>
        ${null!==e.temperature?F`<span class="chip">${e.temperature}°C</span>`:W}
        ${null!==e.humidity?F`<span class="chip">${e.humidity}% RH</span>`:W}
      </div>
    `:W}_renderControls(e){const t=[e.autoTargetControl?.isOn??"auto"===e.targetMode?null:e.targetControl,e.maxLitersControl,e.sensorDepthControl,e.rainFractionControl,e.minApplicationControl].filter(e=>null!==e),i=[e.soilTypeControl,e.plantProfileControl].filter(e=>null!==e),r=[e.enabledControl,e.learningControl,e.autoTargetControl].filter(e=>null!==e);return t.length||r.length||i.length?F`
      <div class="section">
        <div class="section-label">Settings</div>
        ${i.map(e=>{return F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value">${t=e.state,t?t.split("_").map(e=>e.charAt(0).toUpperCase()+e.slice(1)).join(" "):"–"}</span>
            </div>
          `;var t})}
        ${t.map(e=>F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value"
                >${e.state??"–"} ${e.unit??""}</span
              >
            </div>
          `)}
        ${e.sensorDepthShallow?F`
              <div class="row warning">
                <ha-icon icon="mdi:alert-outline"></ha-icon>
                <span class="row-label"
                  >Sensor sits well above the root zone — moisture may read low
                  and over-trigger watering.</span
                >
              </div>
            `:W}
        ${r.map(e=>F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value"
                >${e.state??"–"} ${e.unit??""}</span
              >
            </div>
          `)}
        ${r.map(e=>F`
            <div class="row">
              <span class="row-label">${e.label}</span>
              <button
                class="toggle ${e.isOn?"on":""}"
                @click=${()=>this._toggleSwitch(e.entityId)}
              >
                ${e.isOn?"On":"Off"}
              </button>
            </div>
          `)}
      </div>
    `:W}_renderSchedule(e){return e.schedule.length?F`
      <div class="section">
        <div class="section-label">Schedule</div>
        ${e.schedule.map(e=>F`
            <div class="row">
              <span
                class="row-label clickable"
                @click=${()=>this._moreInfo(e.timeEntity)}
              >
                <ha-icon icon="mdi:clock-outline" class="row-icon"></ha-icon>
                Slot ${e.index}
              </span>
              <span
                class="row-value clickable"
                @click=${()=>this._moreInfo(e.timeEntity)}
                >${e.time??"–"}</span
              >
              <button
                class="toggle ${e.active?"on":""}"
                @click=${()=>this._toggleSwitch(e.activeEntity)}
              >
                ${e.active?"Active":"Off"}
              </button>
            </div>
          `)}
      </div>
    `:W}_renderModelInsight(e){const t=e.modelInsight;if(!t)return W;const i=t.decisionExplanation;return F`
      <details class="section collapsible">
        <summary class="section-label">
          <span>Model Insight</span>
          ${null!==t.overallConfidence?F`<span
                class="confidence-badge ${this._confLevel(t.overallConfidence)}"
                title="How confident the model is in its prediction for this zone"
                ><span class="conf-meter" aria-hidden="true"
                  ><i></i><i></i><i></i
                ></span>
                <span class="conf-word"
                  >${this._confWord(t.overallConfidence)}</span
                >
                <span class="conf-pct"
                  >${Math.round(100*t.overallConfidence)}%</span
                ></span
              >`:W}
        </summary>
        ${t.bootstrapSummary?F`<div class="note">${t.bootstrapSummary}</div>`:W}
        ${i?.terms.length?F`
              <div class="terms-grid">
                ${i.terms.map(e=>F`
                    <div class="term ${e.value>0?"gain":"loss"}">
                      <span class="term-label">${e.label}</span>
                      <span class="term-value"
                        >${e.value>0?"+":""}${e.value}${e.unit}</span
                      >
                    </div>
                  `)}
              </div>
            `:W}
        ${t.parameters.length?F`
              <div class="params-section">
                ${t.parameters.map(e=>this._renderParam(e))}
              </div>
            `:W}
        ${t.modelUpdated?F`<div class="note">
              Updated ${new Date(t.modelUpdated).toLocaleString()}
            </div>`:W}
      </details>
    `}_confLevel(e){return e>=.8?"conf-high":e>=.5?"conf-med":"conf-low"}_confWord(e){return e>=.8?"High":e>=.5?"Medium":"Low"}_renderParam(e){return F`
      <div class="row param-row">
        <span class="row-label">${e.label}</span>
        <span class="row-value">
          ${null===e.value?"learning…":`${e.value} ${e.unit??""}`}
          ${null!==e.confidence?F`<span class="conf-bar ${this._confLevel(e.confidence)}">
                <span style="width:${Math.round(100*e.confidence)}%"></span>
              </span>`:W}
        </span>
      </div>
    `}_renderReferences(e){return e.references.length?F`
      <details class="section collapsible">
        <summary class="section-label">Sensors</summary>
        ${e.references.map(e=>F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value"
                >${e.state??"–"} ${e.unit??""}</span
              >
            </div>
          `)}
      </details>
    `:W}_renderHistory(e){if(!e.historyEntries.length)return W;const t=e.historyEntries.slice(0,5);return F`
      <details class="section collapsible">
        <summary class="section-label">
          History
          <span class="badge-count">${e.historyCount}</span>
        </summary>
        <div class="history-list">
          ${t.map(e=>{const t=String(e.kind??""),i=function(e){if(null==e)return null;const t="number"==typeof e?e*(e<1e12?1e3:1):Date.parse(String(e));if(!Number.isFinite(t))return null;const i=Date.now()-t;if(i<0)return"soon";const r=Math.round(i/6e4);if(r<1)return"just now";if(r<60)return`${r}m ago`;const n=Math.round(r/60);if(n<24)return`${n}h ago`;const o=Math.round(n/24);return o<7?`${o}d ago`:new Date(t).toLocaleDateString()}(e.timestamp??e.ts??e.time??e.when);return F`
              <div class="history-entry">
                <span class="history-kind">${Le[t]??t}</span>
                <span class="history-detail">${this._historyDetail(e)}</span>
                ${i?F`<span class="history-time">${i}</span>`:W}
              </div>
            `})}
        </div>
      </details>
    `}_historyDetail(e){if(e.action)return`${e.action} (${Ie(String(e.reason??""))})`;if(e.status){const t=e.measured_liters??e.requested_liters;return null==t?String(e.status):`${e.status} · ${t} L`}return void 0!==e.delta_mm?`+${e.delta_mm} mm`:""}_metric(e,t){return F`<div class="metric">
      <span class="metric-value">${t}</span>
      <span class="metric-label">${e}</span>
    </div>`}};Ue.styles=a`
    /* ── Card base ──────────────────────────────────── */
    ha-card {
      padding: 16px;
      overflow: hidden;
    }
    .card-header {
      font-size: 1.1rem;
      font-weight: 600;
      padding-bottom: 12px;
    }

    /* ── Overview Grid ─────────────────────────────── */
    .zone-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }
    .zone-tile {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      padding: 16px 12px 12px;
      border-radius: 12px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color, var(--ha-card-background, #fff));
      cursor: pointer;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
      position: relative;
      overflow: hidden;
      font-family: inherit;
      font-size: inherit;
      color: inherit;
      text-align: center;
    }
    .zone-tile:hover {
      border-color: var(--primary-color);
      box-shadow: 0 2px 8px rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
    }
    .zone-tile:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
    .zone-tile.watering {
      border-color: var(--state-active-color, var(--primary-color));
    }
    .zone-tile.skip {
      opacity: 0.7;
    }
    .tile-icon-wrap {
      position: relative;
      --mdc-icon-size: 28px;
      color: var(--primary-text-color);
    }
    .zone-tile.watering .tile-icon-wrap {
      color: var(--state-active-color, var(--primary-color));
    }
    .tile-pulse {
      position: absolute;
      inset: -4px;
      border-radius: 50%;
      border: 2px solid var(--state-active-color, var(--primary-color));
      animation: pulse 1.5s ease-out infinite;
    }
    @keyframes pulse {
      0% { transform: scale(0.8); opacity: 1; }
      100% { transform: scale(1.4); opacity: 0; }
    }
    @media (prefers-reduced-motion: reduce) {
      .tile-pulse { animation: none; opacity: 0.5; }
    }
    .tile-name {
      font-size: 0.8rem;
      font-weight: 600;
      line-height: 1.2;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .tile-bar-track {
      width: 100%;
      height: 4px;
      border-radius: 2px;
      background: var(--divider-color);
      position: relative;
      overflow: visible;
    }
    .tile-bar-fill {
      height: 100%;
      border-radius: 2px;
      background: var(--primary-color);
      transition: width 0.4s ease;
    }
    .zone-tile.watering .tile-bar-fill {
      background: var(--state-active-color, var(--primary-color));
    }
    .tile-bar-target {
      position: absolute;
      top: -2px;
      width: 2px;
      height: 8px;
      background: var(--secondary-text-color);
      border-radius: 1px;
      transform: translateX(-50%);
    }
    .tile-stats {
      display: flex;
      gap: 3px;
      font-size: 0.75rem;
      color: var(--secondary-text-color);
    }
    .tile-moisture {
      font-weight: 600;
      color: var(--primary-text-color);
    }

    /* ── Detail View ───────────────────────────────── */
    .detail-card {
      padding: 0;
    }
    .detail-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .back-btn {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--primary-text-color);
      padding: 4px;
      border-radius: 50%;
      display: flex;
      --mdc-icon-size: 20px;
    }
    .back-btn:hover {
      background: var(--secondary-background-color);
    }
    .detail-icon {
      --mdc-icon-size: 24px;
      color: var(--primary-color);
    }
    .detail-title {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
    }
    .detail-name {
      font-size: 1rem;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .detail-status {
      font-size: 0.8rem;
      color: var(--secondary-text-color);
      text-transform: capitalize;
    }
    .detail-status.active {
      color: var(--state-active-color, var(--primary-color));
      font-weight: 600;
    }

    /* ── Moisture Section ──────────────────────────── */
    .moisture-section {
      padding: 16px;
    }
    .moisture-gauge {
      margin-bottom: 12px;
    }
    .gauge-labels {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;
    }
    .gauge-current {
      font-size: 1.8rem;
      font-weight: 700;
      line-height: 1;
    }
    .gauge-sublabel {
      font-size: 0.8rem;
      color: var(--secondary-text-color);
    }
    .gauge-bar-wrap {
      position: relative;
    }
    .gauge-bar-track {
      width: 100%;
      height: 8px;
      border-radius: 4px;
      background: var(--divider-color);
      position: relative;
      overflow: visible;
    }
    .gauge-fill {
      height: 100%;
      border-radius: 4px;
      background: var(--primary-color);
      transition: width 0.5s ease;
    }
    .gauge-target-band {
      position: absolute;
      top: 0;
      height: 100%;
      background: var(--primary-color);
      opacity: 0.15;
      border-radius: 4px;
    }
    .gauge-target-line {
      position: absolute;
      top: -3px;
      width: 2px;
      height: 14px;
      background: var(--secondary-text-color);
      border-radius: 1px;
      transform: translateX(-50%);
    }
    .gauge-marker {
      position: absolute;
      top: -4px;
      width: 10px;
      height: 10px;
      background: var(--primary-color);
      border: 2px solid var(--card-background-color, #fff);
      border-radius: 50%;
      transform: translate(-50%, 3px);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }
    .gauge-ticks {
      display: flex;
      justify-content: space-between;
      font-size: 0.65rem;
      color: var(--secondary-text-color);
      margin-top: 4px;
      position: relative;
    }
    .gauge-ticks span {
      position: relative;
    }

    .metric-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .metric {
      display: flex;
      flex-direction: column;
      align-items: center;
      flex: 1;
      min-width: 70px;
      padding: 8px 6px;
      background: var(--secondary-background-color);
      border-radius: 8px;
    }
    .metric-value {
      font-size: 0.9rem;
      font-weight: 600;
    }
    .metric-label {
      font-size: 0.7rem;
      color: var(--secondary-text-color);
    }

    /* ── Decision Banner ───────────────────────────── */
    .decision-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      font-size: 0.85rem;
    }
    .decision-banner.water {
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
    }
    .decision-banner.skip {
      background: var(--secondary-background-color);
    }
    .decision-label {
      font-weight: 600;
      text-transform: capitalize;
    }
    .decision-reason {
      color: var(--secondary-text-color);
      font-size: 0.8rem;
    }

    /* ── Prediction Chart ─────────────────────────── */
    .prediction-section {
      padding: 8px 16px 12px;
    }
    .prediction-chart {
      width: 100%;
      height: auto;
      max-height: 160px;
      display: block;
    }
    .pred-grid {
      stroke: var(--divider-color, rgba(255,255,255,0.08));
      stroke-width: 0.5;
      vector-effect: non-scaling-stroke;
    }
    .pred-y-label {
      font-size: 7px;
      fill: var(--secondary-text-color);
      text-anchor: end;
      dominant-baseline: middle;
    }
    .pred-x-label {
      font-size: 7px;
      fill: var(--secondary-text-color);
      text-anchor: middle;
    }
    .pred-target-band {
      fill: var(--primary-color);
      opacity: 0.08;
    }
    .pred-target-line {
      stroke: var(--primary-color);
      stroke-width: 0.8;
      stroke-dasharray: 4 2;
      vector-effect: non-scaling-stroke;
      opacity: 0.5;
    }
    .pred-area {
      fill: url(#pred-fill-grad);
    }
    .pred-line {
      fill: none;
      stroke: var(--primary-color);
      stroke-width: 1.8;
      stroke-linejoin: round;
      stroke-linecap: round;
      vector-effect: non-scaling-stroke;
    }
    .pred-dot {
      fill: var(--card-background-color, var(--primary-background-color));
      stroke: var(--primary-color);
      stroke-width: 1;
      vector-effect: non-scaling-stroke;
    }
    .pred-marker-critical {
      fill: none;
      stroke: var(--error-color, #db4437);
      stroke-width: 1.5;
      vector-effect: non-scaling-stroke;
    }
    .pred-marker-peak {
      fill: none;
      stroke: var(--success-color, #43a047);
      stroke-width: 1.5;
      vector-effect: non-scaling-stroke;
    }
    .pred-value-label {
      font-size: 7px;
      font-weight: 600;
      fill: var(--primary-text-color);
      text-anchor: start;
    }
    .pred-value-label.end {
      text-anchor: end;
    }

    .pred-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 4px 0 0;
      font-size: 0.72rem;
      color: var(--secondary-text-color);
    }
    .pred-legend-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .pred-swatch {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .pred-swatch.target {
      background: var(--primary-color);
      opacity: 0.5;
    }
    .pred-swatch.critical {
      border: 1.5px solid var(--error-color, #db4437);
      background: none;
    }
    .pred-swatch.peak {
      border: 1.5px solid var(--success-color, #43a047);
      background: none;
    }

    .pred-terms {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 4px 12px;
      padding: 8px 0 0;
      font-size: 0.75rem;
    }
    .pred-term {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .pred-term-label {
      color: var(--secondary-text-color);
    }
    .pred-term-value {
      font-weight: 500;
      font-variant-numeric: tabular-nums;
    }
    .pred-term-value.positive {
      color: var(--success-color, #43a047);
    }
    .pred-term-value.negative {
      color: var(--error-color, #db4437);
    }

    /* ── Sections ──────────────────────────────────── */
    .section {
      padding: 0 16px 12px;
    }
    .section-label {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--secondary-text-color);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .sublabel {
      font-weight: 400;
      opacity: 0.7;
    }
    .collapsible {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      margin: 0 16px 12px;
      padding: 10px 12px;
    }
    .collapsible summary {
      cursor: pointer;
      list-style: none;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .collapsible summary::-webkit-details-marker { display: none; }
    .collapsible[open] summary {
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--divider-color);
    }

    /* ── Shared Rows ───────────────────────────────── */
    .row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
      padding: 5px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .row:last-child { border-bottom: none; }
    .row-label { flex: 1; display: flex; align-items: center; gap: 4px; }
    .row-icon { --mdc-icon-size: 16px; opacity: 0.6; }
    .row-value { color: var(--secondary-text-color); text-align: right; }
    .row.warning { color: var(--warning-color, #ff9800); font-size: 0.78rem; align-items: flex-start; }
    .row.warning ha-icon { --mdc-icon-size: 18px; flex: 0 0 auto; }
    .clickable { cursor: pointer; }
    .clickable:hover { color: var(--primary-color); }
    .toggle {
      border: 1px solid var(--divider-color);
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
      border-radius: 12px;
      padding: 2px 10px;
      font-size: 0.72rem;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
    }
    .toggle.on {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-color: var(--primary-color);
    }

    /* ── Info Row (greenhouse) ─────────────────────── */
    .info-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      font-size: 0.82rem;
      --mdc-icon-size: 18px;
    }
    .chip {
      font-size: 0.72rem;
      padding: 2px 8px;
      border-radius: 10px;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
    }
    .chip.on { color: var(--primary-color); font-weight: 600; }

    /* ── Model Insight ─────────────────────────────── */
    .confidence-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      font-variant-numeric: tabular-nums;
      --conf: var(--primary-color);
      background: color-mix(in srgb, var(--conf) 16%, transparent);
      color: color-mix(in srgb, var(--conf) 72%, var(--primary-text-color));
    }
    .confidence-badge.conf-high { --conf: var(--success-color, #43a047); }
    .confidence-badge.conf-med  { --conf: var(--warning-color, #ff9800); }
    .confidence-badge.conf-low  { --conf: var(--error-color, #db4437); }
    .conf-word { letter-spacing: 0.01em; }
    .conf-pct { opacity: 0.75; font-weight: 700; }
    .conf-meter { display: inline-flex; gap: 2px; }
    .conf-meter i {
      width: 4px; height: 9px; border-radius: 1px;
      background: color-mix(in srgb, var(--conf) 22%, var(--divider-color));
    }
    .confidence-badge.conf-low .conf-meter i:nth-child(1),
    .confidence-badge.conf-med .conf-meter i:nth-child(-n + 2),
    .confidence-badge.conf-high .conf-meter i { background: var(--conf); }
    .note {
      font-size: 0.75rem;
      color: var(--secondary-text-color);
      margin: 4px 0;
    }
    .terms-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
      margin: 6px 0;
    }
    .term {
      display: flex;
      justify-content: space-between;
      font-size: 0.78rem;
      padding: 4px 8px;
      border-radius: 6px;
      background: var(--secondary-background-color);
    }
    .term.gain .term-value { color: var(--label-badge-green, #4caf50); }
    .term.loss .term-value { color: var(--error-color, #db4437); }
    .conf-bar {
      display: inline-block;
      width: 36px;
      height: 5px;
      background: var(--divider-color);
      border-radius: 3px;
      overflow: hidden;
      vertical-align: middle;
      margin-left: 4px;
    }
    .conf-bar span {
      display: block;
      height: 100%;
      background: var(--primary-color);
    }
    .conf-bar.conf-high span { background: var(--success-color, #43a047); }
    .conf-bar.conf-med span  { background: var(--warning-color, #ff9800); }
    .conf-bar.conf-low span  { background: var(--error-color, #db4437); }
    .badge-count {
      font-size: 0.7rem;
      background: var(--secondary-background-color);
      padding: 1px 6px;
      border-radius: 8px;
    }

    /* ── History ────────────────────────────────────── */
    .history-list {
      display: flex;
      flex-direction: column;
    }
    .history-entry {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      padding: 4px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .history-entry:last-child { border-bottom: none; }
    .history-kind { font-weight: 500; }
    .history-detail { color: var(--secondary-text-color); }

    /* ── Actions ────────────────────────────────────── */
    .detail-actions {
      display: flex;
      gap: 8px;
      padding: 12px 16px;
      border-top: 1px solid var(--divider-color);
      align-items: center;
      flex-wrap: wrap;
    }
    .detail-actions mwc-button[disabled] {
      opacity: 0.5;
      pointer-events: none;
    }
    .detail-actions ha-circular-progress {
      --mdc-theme-primary: currentColor;
      margin-inline-end: 4px;
    }
    .stop-btn {
      --mdc-theme-primary: var(--error-color);
    }
    .action-feedback {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.82rem;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 12px;
      animation: feedback-in 200ms ease-out;
    }
    .action-feedback.ok {
      color: var(--success-color, #4caf50);
    }
    .action-feedback.error {
      color: var(--error-color, #f44336);
    }
    .action-feedback ha-icon {
      --mdc-icon-size: 16px;
    }
    @keyframes feedback-in {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @media (prefers-reduced-motion: reduce) {
      .action-feedback { animation: none; }
    }
    .action-feedback.overview {
      margin-top: 12px;
    }
    .retry-btn {
      --mdc-theme-primary: var(--error-color);
    }

    /* ── Overview header / Run-All ──────────────────── */
    .overview-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding-bottom: 12px;
    }
    .run-all-btn {
      --mdc-theme-primary: var(--primary-color);
    }
    .run-all-btn ha-circular-progress {
      --mdc-theme-primary: currentColor;
      margin-inline-end: 4px;
    }

    /* ── Tile quick-run ─────────────────────────────── */
    .tile-run {
      position: absolute;
      top: 6px;
      right: 6px;
      --mdc-icon-button-size: 28px;
      --mdc-icon-size: 18px;
      color: var(--secondary-text-color);
      opacity: 0;
      transition: opacity 0.15s ease, color 0.15s ease;
    }
    .zone-tile:hover .tile-run,
    .zone-tile:focus-within .tile-run {
      opacity: 1;
    }
    .tile-run:hover {
      color: var(--primary-color);
    }
    .tile-setup {
      font-size: 0.72rem;
      color: var(--secondary-text-color);
    }

    /* ── Onboarding banner ──────────────────────────── */
    .onboarding {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 12px 14px;
      margin: 12px 16px;
      border-radius: 12px;
      border: 1px solid var(--divider-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.06);
      font-size: 0.85rem;
      line-height: 1.4;
    }
    .onboarding ha-icon {
      color: var(--primary-color);
      flex-shrink: 0;
    }
    .onboarding b { font-weight: 600; }

    /* ── Force two-tap ──────────────────────────────── */
    .force-btn.armed {
      --mdc-theme-primary: var(--warning-color, #ff9800);
    }
    .help-dot {
      --mdc-icon-size: 15px;
      color: var(--secondary-text-color);
      cursor: help;
      margin-inline-start: 4px;
      vertical-align: middle;
    }
    .history-time {
      color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums;
    }
  `,e([he({attribute:!1})],Ue.prototype,"hass",void 0),e([ue()],Ue.prototype,"_config",void 0),e([ue()],Ue.prototype,"_activeZoneIndex",void 0),e([ue()],Ue.prototype,"_actionPending",void 0),e([ue()],Ue.prototype,"_actionResult",void 0),e([ue()],Ue.prototype,"_forceArmed",void 0),Ue=e([ce("amazing-irrigation-overview-card")],Ue),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-overview-card",name:"Amazing Irrigation",description:"Professional irrigation dashboard with zone overview and detail drill-down."});const De="amazing_irrigation",je=[{name:"decision_entity",required:!0,selector:{entity:{integration:De,domain:"sensor"}}},{name:"name",selector:{text:{}}},{name:"icon",selector:{icon:{}}},{name:"moisture_entity",selector:{entity:{domain:"sensor"}}},{name:"status_entity",selector:{entity:{integration:De,domain:"sensor"}}},{name:"history_entity",selector:{entity:{integration:De,domain:"sensor"}}}],Be=[{name:"title",selector:{text:{}}}],Ze={decision_entity:"Decision sensor (required)",name:"Zone name (optional)",icon:"Zone icon (optional)",moisture_entity:"Soil moisture sensor (optional)",status_entity:"Status sensor (optional)",history_entity:"History sensor (optional)",title:"Card title (optional)"},Fe=e=>Ze[e.name]??e.name;function Ne(e,t){e.dispatchEvent(new CustomEvent("config-changed",{detail:{config:t},bubbles:!0,composed:!0}))}let We=class extends se{setConfig(e){this._config=e}render(){return this.hass&&this._config?F`
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${je}
        .computeLabel=${Fe}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `:W}_valueChanged(e){e.stopPropagation(),Ne(this,e.detail.value)}};e([he({attribute:!1})],We.prototype,"hass",void 0),e([ue()],We.prototype,"_config",void 0),We=e([ce("amazing-irrigation-card-editor")],We);let qe=class extends se{setConfig(e){this._config={...e,zones:Array.isArray(e.zones)?e.zones:[]}}get _zones(){return this._config?.zones??[]}render(){return this.hass&&this._config?F`
      <div class="editor">
        <ha-form
          .hass=${this.hass}
          .data=${{title:this._config.title??""}}
          .schema=${Be}
          .computeLabel=${Fe}
          @value-changed=${this._titleChanged}
        ></ha-form>

        <div class="zones">
          ${this._zones.map((e,t)=>this._renderZone(e,t))}
          ${0===this._zones.length?F`<div class="hint">
                Add at least one zone (select its Decision sensor).
              </div>`:W}
        </div>

        <mwc-button outlined @click=${this._addZone}>+ Add zone</mwc-button>
      </div>
    `:W}_renderZone(e,t){return F`
      <div class="zone">
        <div class="zone-head">
          <span class="zone-title">Zone ${t+1}</span>
          <mwc-button dense @click=${()=>this._removeZone(t)}>
            Remove
          </mwc-button>
        </div>
        <ha-form
          .hass=${this.hass}
          .data=${e}
          .schema=${je}
          .computeLabel=${Fe}
          .index=${t}
          @value-changed=${this._zoneChanged}
        ></ha-form>
      </div>
    `}_titleChanged(e){e.stopPropagation();const t=e.detail.value.title,i={...this._config,title:t};t||delete i.title,this._emit(i)}_zoneChanged(e){e.stopPropagation();const t=e.currentTarget.index;if(void 0===t)return;const i=[...this._zones];i[t]=e.detail.value,this._emit({...this._config,zones:i})}_addZone(){const e=[...this._zones,{decision_entity:""}];this._emit({...this._config,zones:e})}_removeZone(e){const t=this._zones.filter((t,i)=>i!==e);this._emit({...this._config,zones:t})}_emit(e){this._config=e,Ne(this,e)}};qe.styles=a`
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
  `,e([he({attribute:!1})],qe.prototype,"hass",void 0),e([ue()],qe.prototype,"_config",void 0),qe=e([ce("amazing-irrigation-overview-card-editor")],qe);const Ve={run_request:"Run requested",decision:"Decision",rain_event:"Rain",watering_event:"Watering"};let Ge=class extends se{constructor(){super(...arguments),this._actionPending=null,this._actionResult=null}static getStubConfig(e){const[t]=Me(e?.states);return{decision_entity:t??""}}static async getConfigElement(){return document.createElement("amazing-irrigation-card-editor")}setConfig(e){if(!e||!e.decision_entity)throw new Error("amazing-irrigation-card: 'decision_entity' is required");this._config=e}getCardSize(){return 4}get _view(){if(this._config&&this.hass)return Pe(this._config,this.hass.states)}async _callZoneService(e,t=!1){if(!this.hass||!this._config||this._actionPending)return;const i="stop_zone"===e?"stop":t?"force":"run";this._actionPending=i,this._actionResult=null,this._actionResultTimer&&clearTimeout(this._actionResultTimer);const r={entity_id:this._config.decision_entity};"run_zone"===e&&(r.force=t);try{await this.hass.callService("amazing_irrigation",e,r);const n="stop"===i?"Stop sent":t?"Force sent":"Run sent";this._actionResult={kind:"ok",text:n}}catch{this._actionResult={kind:"error",text:"Service call failed"}}finally{this._actionPending=null,this._actionResultTimer=setTimeout(()=>{this._actionResult=null},4e3)}}disconnectedCallback(){super.disconnectedCallback(),this._actionResultTimer&&clearTimeout(this._actionResultTimer)}_moreInfo(e){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:e},bubbles:!0,composed:!0}))}_toggleSwitch(e){this.hass&&this.hass.callService("switch","toggle",{entity_id:e})}render(){const e=this._view;return this._config?e?F`
      <ha-card>
        <div class="header">
          <span class="name">${e.name}</span>
          <span class="status ${e.isWatering?"active":""}">
            ${e.wateringStatus??"idle"}
          </span>
        </div>

        <div class="grid">
          ${this._metric("Moisture",this._pct(e.moisture))}
          ${"auto"===e.targetMode&&null!==e.targetBandLow&&null!==e.targetBandHigh?this._metric("Target band",`${Math.round(e.targetBandLow)}–${Math.round(e.targetBandHigh)}%`):this._metric("Target",this._pct(e.target))}
          ${null===e.demandProfile?W:this._metric("Demand",e.demandProfile.charAt(0).toUpperCase()+e.demandProfile.slice(1))}
          ${this._metric("Recommended",null===e.recommendedLiters?"–":`${e.recommendedLiters} L`)}
          ${null===e.availableWater?W:this._metric("Available water",`${Math.round(100*e.availableWater)}%`)}
          ${null===e.totalVolume?W:this._metric("Total water",`${e.totalVolume} ${e.totalVolumeUnit??"L"}`)}
        </div>

        <div class="decision">
          <span class="decision-action">${e.decision??"–"}</span>
          ${e.decisionReason?F`<span class="decision-reason"
                >${e.decisionReason.replace(/_/g," ")}</span
              >`:W}
        </div>

        ${this._renderGreenhouse(e)}
        ${this._renderControls(e)}
        ${this._renderSchedule(e)}
        ${this._renderLearned(e)}
        ${this._renderModelInsight(e)}
        ${this._renderReferences(e)}
        ${this._renderHistory(e)}

        <div class="actions">
          <mwc-button
            raised
            ?disabled=${!!this._actionPending}
            @click=${()=>this._callZoneService("run_zone")}
          >
            ${"run"===this._actionPending?F`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`:W}
            Run
          </mwc-button>
          <mwc-button
            ?disabled=${!!this._actionPending}
            @click=${()=>this._callZoneService("run_zone",!0)}
          >
            ${"force"===this._actionPending?F`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`:W}
            Force Water
          </mwc-button>
          ${Te(e)?F`<mwc-button
                class="stop"
                ?disabled=${!!this._actionPending}
                @click=${()=>this._callZoneService("stop_zone")}
              >
                ${"stop"===this._actionPending?F`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`:W}
                Stop
              </mwc-button>`:W}
          ${this._actionResult?F`<span class="action-feedback ${this._actionResult.kind}">
                <ha-icon
                  icon=${"ok"===this._actionResult.kind?"mdi:check-circle-outline":"mdi:alert-circle-outline"}
                ></ha-icon>
                ${this._actionResult.text}
              </span>`:W}
        </div>
      </ha-card>
    `:F`<ha-card><div class="empty">Loading…</div></ha-card>`:W}_renderGreenhouse(e){return e.greenhouse?F`
      <div class="greenhouse">
        <span class="badge">🌱 Greenhouse</span>
        <span class="ctx ${e.protectedRain?"on":""}">
          ${e.protectedRain?"Protected from rain":"Open to rain"}
        </span>
        ${null!==e.temperature?F`<span class="ctx">${e.temperature}°C</span>`:W}
        ${null!==e.humidity?F`<span class="ctx">${e.humidity}% RH</span>`:W}
      </div>
    `:W}_renderControls(e){const t=e.autoTargetControl?.isOn??"auto"===e.targetMode,i=[t?null:e.targetControl,e.maxLitersControl,e.sensorDepthControl,e.rainFractionControl,e.minApplicationControl].filter(e=>null!==e),r=[e.soilTypeControl,e.plantProfileControl].filter(e=>null!==e),n=[e.enabledControl,e.learningControl,e.autoTargetControl].filter(e=>null!==e),o=t&&null!==e.targetBandLow&&null!==e.targetBandHigh;return i.length||n.length||r.length||o?F`
      <div class="section">
        <div class="section-head">Settings</div>
        ${o?F`
              <div class="row">
                <span class="row-label">Target band (auto)</span>
                <span class="row-value"
                  >${Math.round(e.targetBandLow)}–${Math.round(e.targetBandHigh)} %</span
                >
              </div>
            `:W}
        ${r.map(e=>{return F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value">${t=e.state,t?t.split("_").map(e=>e.charAt(0).toUpperCase()+e.slice(1)).join(" "):"–"}</span>
            </div>
          `;var t})}
        ${i.map(e=>F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value"
                >${e.state??"–"} ${e.unit??""}</span
              >
            </div>
          `)}
        ${e.sensorDepthShallow?F`
              <div class="row warning">
                <ha-icon icon="mdi:alert-outline"></ha-icon>
                <span class="row-label"
                  >Sensor sits well above the root zone — moisture may read low
                  and over-trigger watering.</span
                >
              </div>
            `:W}
        ${n.map(e=>F`
            <div class="row">
              <span class="row-label">${e.label}</span>
              <button
                class="toggle ${e.isOn?"on":""}"
                @click=${()=>this._toggleSwitch(e.entityId)}
              >
                ${e.isOn?"On":"Off"}
              </button>
            </div>
          `)}
      </div>
    `:W}_renderSchedule(e){return e.schedule.length?F`
      <div class="section">
        <div class="section-head">Schedule</div>
        ${e.schedule.map(e=>F`
            <div class="row">
              <span
                class="row-label clickable"
                @click=${()=>this._moreInfo(e.timeEntity)}
                >Schedule ${e.index}</span
              >
              <span
                class="row-value clickable"
                @click=${()=>this._moreInfo(e.timeEntity)}
                >${e.time??"–"}</span
              >
              <button
                class="toggle ${e.active?"on":""}"
                @click=${()=>this._toggleSwitch(e.activeEntity)}
              >
                ${e.active?"Active":"Off"}
              </button>
            </div>
          `)}
      </div>
    `:W}_renderLearned(e){return e.learned.length?F`
      <div class="section">
        <div class="section-head">Learned model</div>
        ${e.learned.map(e=>F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value">
                ${null===e.value?"learning…":`${e.value} ${e.unit??""}`}
              </span>
            </div>
          `)}
      </div>
    `:W}_renderReferences(e){return e.references.length?F`
      <div class="section">
        <div class="section-head">Sensors</div>
        ${e.references.map(e=>F`
            <div
              class="row clickable"
              @click=${()=>this._moreInfo(e.entityId)}
            >
              <span class="row-label">${e.label}</span>
              <span class="row-value"
                >${e.state??"–"} ${e.unit??""}</span
              >
            </div>
          `)}
      </div>
    `:W}_renderModelInsight(e){const t=e.modelInsight;if(!t)return W;const i=t.decisionExplanation;return F`
      <details class="section model-insight">
        <summary>
          <span>Why this decision</span>
          ${t.status?F`<span>${t.status}</span>`:W}
        </summary>
        ${t.bootstrapSummary?F`<div class="model-note">${t.bootstrapSummary}</div>`:W}
        ${i?this._renderDecisionExplanation(i):W}
        ${t.parameters.length?F`
              <div class="section-head">Model parameters</div>
              ${t.parameters.map(e=>this._renderModelParameter(e))}
            `:W}
        ${t.modelUpdated?F`<div class="model-note">
              Updated ${new Date(t.modelUpdated).toLocaleString()}
            </div>`:W}
      </details>
    `}_renderDecisionExplanation(e){return F`
      <div class="model-note">
        ${e.predictiveReason?`Reason: ${e.predictiveReason.replace(/_/g," ")}`:"Predictive water-balance decision"}
        ${null===e.horizonHours?"":` over ${e.horizonHours} h`}
        ${null===e.chosenLiters?"":` · chosen ${e.chosenLiters} L`}
      </div>
      ${e.predictedTrajectory.length?F`
            <div class="section-head">Predicted moisture trajectory</div>
            <div class="trajectory">
              ${e.predictedTrajectory.map((e,t)=>F`<span>Step ${t+1}: ${e}%</span>`)}
            </div>
          `:W}
      ${null!==e.predictedCriticalTheta||null!==e.predictedPeakTheta?F`<div class="model-note">
            ${null===e.predictedCriticalTheta?"":`Lowest predicted moisture: ${e.predictedCriticalTheta}%`}
            ${null===e.predictedPeakTheta?"":` Peak: ${e.predictedPeakTheta}%`}
          </div>`:W}
      ${e.terms.length?F`
            <div class="section-head">Water-balance terms</div>
            ${e.terms.map(e=>this._renderTerm(e))}
          `:W}
    `}_renderTerm(e){const t=e.value>0?"+":"";return F`
      <div class="row">
        <span class="row-label">${e.label}</span>
        <span class="row-value">${t}${e.value} ${e.unit}</span>
      </div>
    `}_renderModelParameter(e){return F`
      <div class="row model-param">
        <span class="row-label">${e.label}</span>
        <span class="row-value">
          ${null===e.value?"learning…":`${e.value} ${e.unit??""}`}
          ${null===e.confidence?W:F`<span class="confidence">
                <span
                  style="width: ${Math.round(100*e.confidence)}%"
                ></span>
              </span>
              ${Math.round(100*e.confidence)}%`}
        </span>
      </div>
    `}_renderHistory(e){if(!e.historyEntries.length)return W;const t=e.historyEntries.slice(0,5);return F`
      <div class="history">
        <div class="history-head">
          History (${e.historyCount})
        </div>
        <ul>
          ${t.map(e=>{const t=String(e.kind??"");return F`<li>
              <span class="kind">${Ve[t]??t}</span>
              <span class="detail">${this._historyDetail(e)}</span>
            </li>`})}
        </ul>
      </div>
    `}_historyDetail(e){if(e.action)return`${e.action} (${e.reason??""})`;if(e.status){const t=e.measured_liters??e.requested_liters;return null==t?String(e.status):`${e.status} · ${t} L`}return void 0!==e.delta_mm?`+${e.delta_mm} mm`:""}_metric(e,t){return F`<div class="metric">
      <div class="metric-value">${t}</div>
      <div class="metric-label">${e}</div>
    </div>`}_pct(e){return null===e?"–":`${e}%`}};Ge.styles=a`
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
    details.model-insight {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 8px;
    }
    details.model-insight summary {
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--secondary-text-color);
    }
    .model-note {
      color: var(--secondary-text-color);
      font-size: 0.8rem;
      margin: 6px 0;
    }
    .trajectory {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin: 4px 0 8px;
    }
    .trajectory span {
      background: var(--secondary-background-color);
      border-radius: 10px;
      font-size: 0.75rem;
      padding: 2px 6px;
    }
    .confidence {
      display: inline-block;
      width: 40px;
      height: 6px;
      background: var(--divider-color);
      border-radius: 6px;
      margin-left: 6px;
      overflow: hidden;
      vertical-align: middle;
    }
    .confidence span {
      display: block;
      height: 100%;
      background: var(--primary-color);
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
    .row.warning {
      color: var(--warning-color, #ff9800);
      font-size: 0.78rem;
      align-items: flex-start;
    }
    .row.warning ha-icon {
      --mdc-icon-size: 18px;
      flex: 0 0 auto;
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
      align-items: center;
      flex-wrap: wrap;
    }
    .actions mwc-button[disabled] {
      opacity: 0.5;
      pointer-events: none;
    }
    .actions ha-circular-progress {
      --mdc-theme-primary: currentColor;
      margin-inline-end: 4px;
    }
    .stop {
      --mdc-theme-primary: var(--error-color);
    }
    .action-feedback {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.82rem;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 12px;
      animation: feedback-in 200ms ease-out;
    }
    .action-feedback.ok {
      color: var(--success-color, #4caf50);
    }
    .action-feedback.error {
      color: var(--error-color, #f44336);
    }
    .action-feedback ha-icon {
      --mdc-icon-size: 16px;
    }
    @keyframes feedback-in {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @media (prefers-reduced-motion: reduce) {
      .action-feedback { animation: none; }
    }
    .empty {
      padding: 16px;
      color: var(--secondary-text-color);
    }
  `,e([he({attribute:!1})],Ge.prototype,"hass",void 0),e([ue()],Ge.prototype,"_config",void 0),e([ue()],Ge.prototype,"_actionPending",void 0),e([ue()],Ge.prototype,"_actionResult",void 0),Ge=e([ce("amazing-irrigation-card")],Ge),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-card",name:"Amazing Irrigation Zone",description:"Display and control a single Amazing Irrigation zone."});export{Ge as AmazingIrrigationCard};
