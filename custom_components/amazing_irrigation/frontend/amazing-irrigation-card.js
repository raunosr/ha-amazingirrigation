function e(e,t,i,r){var n,s=arguments.length,o=s<3?t:null===r?r=Object.getOwnPropertyDescriptor(t,i):r;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)o=Reflect.decorate(e,t,i,r);else for(var a=e.length-1;a>=0;a--)(n=e[a])&&(o=(s<3?n(o):s>3?n(t,i,o):n(t,i))||o);return s>3&&o&&Object.defineProperty(t,i,o),o}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,r=Symbol(),n=new WeakMap;let s=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==r)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=n.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&n.set(t,e))}return e}toString(){return this.cssText}};const o=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,r)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[r+1],e[0]);return new s(i,e,r)},a=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new s("string"==typeof e?e:e+"",void 0,r))(t)})(e):e,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:p,getOwnPropertySymbols:h,getPrototypeOf:u}=Object,g=globalThis,m=g.trustedTypes,v=m?m.emptyScript:"",f=g.reactiveElementPolyfillSupport,_=(e,t)=>e,y={toAttribute(e,t){switch(t){case Boolean:e=e?v:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},$=(e,t)=>!l(e,t),b={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:$};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),g.litPropertyMetadata??=new WeakMap;let x=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=b){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),r=this.getPropertyDescriptor(e,i,t);void 0!==r&&c(this.prototype,e,r)}}static getPropertyDescriptor(e,t,i){const{get:r,set:n}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:r,set(t){const s=r?.call(this);n?.call(this,t),this.requestUpdate(e,s,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??b}static _$Ei(){if(this.hasOwnProperty(_("elementProperties")))return;const e=u(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(_("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_("properties"))){const e=this.properties,t=[...p(e),...h(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(a(e))}else void 0!==e&&t.push(a(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,r)=>{if(i)e.adoptedStyleSheets=r.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of r){const r=document.createElement("style"),n=t.litNonce;void 0!==n&&r.setAttribute("nonce",n),r.textContent=i.cssText,e.appendChild(r)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),r=this.constructor._$Eu(e,i);if(void 0!==r&&!0===i.reflect){const n=(void 0!==i.converter?.toAttribute?i.converter:y).toAttribute(t,i.type);this._$Em=e,null==n?this.removeAttribute(r):this.setAttribute(r,n),this._$Em=null}}_$AK(e,t){const i=this.constructor,r=i._$Eh.get(e);if(void 0!==r&&this._$Em!==r){const e=i.getPropertyOptions(r),n="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:y;this._$Em=r;const s=n.fromAttribute(t,e.type);this[r]=s??this._$Ej?.get(r)??s,this._$Em=null}}requestUpdate(e,t,i,r=!1,n){if(void 0!==e){const s=this.constructor;if(!1===r&&(n=this[e]),i??=s.getPropertyOptions(e),!((i.hasChanged??$)(n,t)||i.useDefault&&i.reflect&&n===this._$Ej?.get(e)&&!this.hasAttribute(s._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:r,wrapped:n},s){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,s??t??this[e]),!0!==n||void 0!==s)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===r&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,r=this[t];!0!==e||this._$AL.has(t)||void 0===r||this.C(t,void 0,i,r)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[_("elementProperties")]=new Map,x[_("finalized")]=new Map,f?.({ReactiveElement:x}),(g.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const w=globalThis,k=e=>e,A=w.trustedTypes,z=A?A.createPolicy("lit-html",{createHTML:e=>e}):void 0,S="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,C="?"+E,P=`<${C}>`,M=document,R=()=>M.createComment(""),T=e=>null===e||"object"!=typeof e&&"function"!=typeof e,O=Array.isArray,H="[ \t\n\f\r]",L=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,I=/-->/g,U=/>/g,j=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),D=/'/g,B=/"/g,Z=/^(?:script|style|textarea|title)$/i,N=(e=>(t,...i)=>({_$litType$:e,strings:t,values:i}))(1),W=Symbol.for("lit-noChange"),q=Symbol.for("lit-nothing"),V=new WeakMap,F=M.createTreeWalker(M,129);function G(e,t){if(!O(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==z?z.createHTML(t):t}const K=(e,t)=>{const i=e.length-1,r=[];let n,s=2===t?"<svg>":3===t?"<math>":"",o=L;for(let t=0;t<i;t++){const i=e[t];let a,l,c=-1,d=0;for(;d<i.length&&(o.lastIndex=d,l=o.exec(i),null!==l);)d=o.lastIndex,o===L?"!--"===l[1]?o=I:void 0!==l[1]?o=U:void 0!==l[2]?(Z.test(l[2])&&(n=RegExp("</"+l[2],"g")),o=j):void 0!==l[3]&&(o=j):o===j?">"===l[0]?(o=n??L,c=-1):void 0===l[1]?c=-2:(c=o.lastIndex-l[2].length,a=l[1],o=void 0===l[3]?j:'"'===l[3]?B:D):o===B||o===D?o=j:o===I||o===U?o=L:(o=j,n=void 0);const p=o===j&&e[t+1].startsWith("/>")?" ":"";s+=o===L?i+P:c>=0?(r.push(a),i.slice(0,c)+S+i.slice(c)+E+p):i+E+(-2===c?t:p)}return[G(e,s+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),r]};class J{constructor({strings:e,_$litType$:t},i){let r;this.parts=[];let n=0,s=0;const o=e.length-1,a=this.parts,[l,c]=K(e,t);if(this.el=J.createElement(l,i),F.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(r=F.nextNode())&&a.length<o;){if(1===r.nodeType){if(r.hasAttributes())for(const e of r.getAttributeNames())if(e.endsWith(S)){const t=c[s++],i=r.getAttribute(e).split(E),o=/([.?@])?(.*)/.exec(t);a.push({type:1,index:n,name:o[2],strings:i,ctor:"."===o[1]?te:"?"===o[1]?ie:"@"===o[1]?re:ee}),r.removeAttribute(e)}else e.startsWith(E)&&(a.push({type:6,index:n}),r.removeAttribute(e));if(Z.test(r.tagName)){const e=r.textContent.split(E),t=e.length-1;if(t>0){r.textContent=A?A.emptyScript:"";for(let i=0;i<t;i++)r.append(e[i],R()),F.nextNode(),a.push({type:2,index:++n});r.append(e[t],R())}}}else if(8===r.nodeType)if(r.data===C)a.push({type:2,index:n});else{let e=-1;for(;-1!==(e=r.data.indexOf(E,e+1));)a.push({type:7,index:n}),e+=E.length-1}n++}}static createElement(e,t){const i=M.createElement("template");return i.innerHTML=e,i}}function X(e,t,i=e,r){if(t===W)return t;let n=void 0!==r?i._$Co?.[r]:i._$Cl;const s=T(t)?void 0:t._$litDirective$;return n?.constructor!==s&&(n?._$AO?.(!1),void 0===s?n=void 0:(n=new s(e),n._$AT(e,i,r)),void 0!==r?(i._$Co??=[])[r]=n:i._$Cl=n),void 0!==n&&(t=X(e,n._$AS(e,t.values),n,r)),t}class Q{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,r=(e?.creationScope??M).importNode(t,!0);F.currentNode=r;let n=F.nextNode(),s=0,o=0,a=i[0];for(;void 0!==a;){if(s===a.index){let t;2===a.type?t=new Y(n,n.nextSibling,this,e):1===a.type?t=new a.ctor(n,a.name,a.strings,this,e):6===a.type&&(t=new ne(n,this,e)),this._$AV.push(t),a=i[++o]}s!==a?.index&&(n=F.nextNode(),s++)}return F.currentNode=M,r}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class Y{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,r){this.type=2,this._$AH=q,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=r,this._$Cv=r?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=X(this,e,t),T(e)?e===q||null==e||""===e?(this._$AH!==q&&this._$AR(),this._$AH=q):e!==this._$AH&&e!==W&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>O(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==q&&T(this._$AH)?this._$AA.nextSibling.data=e:this.T(M.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,r="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=J.createElement(G(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===r)this._$AH.p(t);else{const e=new Q(r,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=V.get(e.strings);return void 0===t&&V.set(e.strings,t=new J(e)),t}k(e){O(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,r=0;for(const n of e)r===t.length?t.push(i=new Y(this.O(R()),this.O(R()),this,this.options)):i=t[r],i._$AI(n),r++;r<t.length&&(this._$AR(i&&i._$AB.nextSibling,r),t.length=r)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,r,n){this.type=1,this._$AH=q,this._$AN=void 0,this.element=e,this.name=t,this._$AM=r,this.options=n,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=q}_$AI(e,t=this,i,r){const n=this.strings;let s=!1;if(void 0===n)e=X(this,e,t,0),s=!T(e)||e!==this._$AH&&e!==W,s&&(this._$AH=e);else{const r=e;let o,a;for(e=n[0],o=0;o<n.length-1;o++)a=X(this,r[i+o],t,o),a===W&&(a=this._$AH[o]),s||=!T(a)||a!==this._$AH[o],a===q?e=q:e!==q&&(e+=(a??"")+n[o+1]),this._$AH[o]=a}s&&!r&&this.j(e)}j(e){e===q?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===q?void 0:e}}class ie extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==q)}}class re extends ee{constructor(e,t,i,r,n){super(e,t,i,r,n),this.type=5}_$AI(e,t=this){if((e=X(this,e,t,0)??q)===W)return;const i=this._$AH,r=e===q&&i!==q||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,n=e!==q&&(i===q||r);r&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ne{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){X(this,e)}}const se=w.litHtmlPolyfillSupport;se?.(J,Y),(w.litHtmlVersions??=[]).push("3.3.3");const oe=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class ae extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const r=i?.renderBefore??t;let n=r._$litPart$;if(void 0===n){const e=i?.renderBefore??null;r._$litPart$=n=new Y(t.insertBefore(R(),e),e,void 0,i??{})}return n._$AI(e),n})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}}ae._$litElement$=!0,ae.finalized=!0,oe.litElementHydrateSupport?.({LitElement:ae});const le=oe.litElementPolyfillSupport;le?.({LitElement:ae}),(oe.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ce=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},de={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:$},pe=(e=de,t,i)=>{const{kind:r,metadata:n}=i;let s=globalThis.litPropertyMetadata.get(n);if(void 0===s&&globalThis.litPropertyMetadata.set(n,s=new Map),"setter"===r&&((e=Object.create(e)).wrapped=!0),s.set(i.name,e),"accessor"===r){const{name:r}=i;return{set(i){const n=t.get.call(this);t.set.call(this,i),this.requestUpdate(r,n,e,!0,i)},init(t){return void 0!==t&&this.C(r,void 0,e,t),t}}}if("setter"===r){const{name:r}=i;return function(i){const n=this[r];t.call(this,i),this.requestUpdate(r,n,e,!0,i)}}throw Error("Unsupported decorator location: "+r)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function he(e){return(t,i)=>"object"==typeof i?pe(e,t,i):((e,t,i)=>{const r=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),r?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ue(e){return he({...e,state:!0,attribute:!1})}function ge(e){if(null==e||""===e)return null;const t="number"==typeof e?e:Number(e);return Number.isFinite(t)?t:null}function me(e){return void 0===e||"unavailable"===e.state||"unknown"===e.state}function ve(e,t){return e[t]}function fe(e){const t=e?.attributes?.unit_of_measurement;return"string"==typeof t?t:null}function _e(e,t){const i=e?.attributes?.friendly_name;return"string"==typeof i&&i.length>0?i:t}function ye(e,t,i){const r=ve(e,t);return r?{entityId:t,label:i,name:_e(r,t),state:me(r)?null:r.state,unit:fe(r),available:!me(r)}:null}function $e(e,t){const i=[],r=[["forecast_rain_amount","Rain forecast"],["forecast_rain_probability","Rain chance"],["weather_forecast_entity","Weather forecast"],["observed_rain_amount","Observed rain"],["temperature_sensor","Temperature"],["humidity_sensor","Humidity"],["observed_air_temperature","Air temperature"],["observed_air_humidity","Air humidity"],["forecast_air_temperature","Forecast air temp"],["forecast_air_humidity","Forecast air humidity"],["wind_speed","Wind speed"],["solar_radiation","Solar"]],n=Array.isArray(e.moisture_sensors)?e.moisture_sensors:[];for(const e of n){const r=ye(t,e,"Moisture sensor");r&&i.push(r)}for(const[n,s]of r){const r=e[n];if("string"==typeof r&&r){const e=ye(t,r,s);e&&i.push(e)}}const s=Array.isArray(e.safety_blockers)?e.safety_blockers:[];for(const e of s){const r=ye(t,e,"Safety blocker");r&&i.push(r)}return i}const be=[{key:"learned_moisture_gain_per_liter",label:"Moisture Gain per Liter"},{key:"learned_daily_drying_rate",label:"Daily Drying Rate"},{key:"learned_rain_efficiency",label:"Rain Efficiency"},{key:"learned_field_capacity",label:"Field Capacity"},{key:"learned_wilting_point",label:"Wilting Point"}],xe=[{key:"eta_irr",label:"Irrigation Efficiency"},{key:"eta_rain",label:"Rain Efficiency"},{key:"k_et",label:"ET Coefficient"},{key:"drain_rate",label:"Drainage Rate"},{key:"field_capacity",label:"Field Capacity"},{key:"wilting_point",label:"Wilting Point"}],we={irrigation:"Irrigation added",rain:"Rain added",et:"Evapotranspiration loss",drainage:"Drainage loss"};function ke(e){return null===e||"object"!=typeof e||Array.isArray(e)?null:e}function Ae(e,t){const i=[];for(const r of be){const n=`sensor.${e}_${r.key}`,s=ve(t,n);if(!s)continue;const o=s.attributes?.samples;i.push({key:r.key,label:r.label,entityId:n,value:me(s)?null:ge(s.state),unit:fe(s),samples:"number"==typeof o?o:null})}return i}function ze(e){return Array.isArray(e)?e.map(ge).filter(e=>null!==e):[]}function Se(e,t){const i=ke(e.decision_explanation)??ke(t.explanation),r=function(e){const t=ke(e?.water_balance_terms)??ke(e?.terms);return t?Object.entries(t).map(([e,t])=>{const i=ge(t);return null===i?null:{key:e,label:we[e]??e.replace(/_/g," "),value:i,unit:"%"}}).filter(e=>null!==e):[]}({...i??{},...e}),n=ze(e.predicted_trajectory).length>0?ze(e.predicted_trajectory):ze(t.predicted_trajectory).length>0?ze(t.predicted_trajectory):ze(i?.predicted_trajectory),s=ge(e.horizon_hours)??ge(t.horizon_hours)??ge(i?.horizon_hours),o=ge(e.chosen_liters)??ge(i?.chosen_liters)??ge(t.recommended_liters),a=ge(e.predicted_critical_theta)??ge(i?.predicted_critical_theta_with_water)??ge(i?.predicted_critical_theta_without_water),l=ge(e.predicted_peak_theta)??ge(i?.predicted_peak_theta);return r.length||n.length||null!==s||null!==o?{terms:r,predictedTrajectory:n,horizonHours:s,predictiveReason:t.reason??null,chosenLiters:o,predictedCriticalTheta:a,predictedPeakTheta:l}:null}function Ee(e,t,i){const r=`sensor.${e}_model_insight`,n=ve(t,r),s=n?.attributes??{},o=function(e){const t=ke(e.parameters),i=ke(e.confidence);return t?xe.map(e=>{const r=ke(t[e.key]);return r?{key:e.key,label:"string"==typeof r.name?r.name:e.label,value:ge(r.value),unit:"string"==typeof r.unit?r.unit:null,confidence:ge(r.confidence)??ge(i?.[e.key])}:null}).filter(e=>null!==e&&(null!==e.value||null!==e.confidence)):[]}(s),a=Se(s,i),l=ge(s.bootstrapped_days),c="string"==typeof s.bootstrap_summary?s.bootstrap_summary:null;return o.length||null!==a||null!==l?{entityId:r,status:me(n)?null:n?.state??null,parameters:o,overallConfidence:ge(s.overall_confidence),bootstrappedDays:l,bootstrapSummary:c,modelUpdated:"string"==typeof s.model_updated?s.model_updated:null,totalLiters:ge(s.total_liters),decisionExplanation:a}:null}function Ce(e,t){const i=[];for(const r of[1,2]){const n=`time.${e}_schedule_${r}_time`,s=`switch.${e}_schedule_${r}_active`,o=ve(t,n),a=ve(t,s);if(!o&&!a)continue;const l=o&&!me(o)?o.state:null;i.push({index:r,timeEntity:n,time:l?l.slice(0,5):null,activeEntity:s,active:"on"===a?.state,available:!me(o)})}return i}function Pe(e,t,i){const r=ve(e,t);return r?{entityId:t,label:i,state:me(r)?null:r.state,unit:fe(r),isOn:"on"===r.state,available:!me(r)}:null}function Me(e,t){const i=e.decision_entity?t[e.decision_entity]:void 0,r=e.moisture_entity?t[e.moisture_entity]:void 0,n=e.status_entity?t[e.status_entity]:void 0,s=e.history_entity?t[e.history_entity]:void 0,o=i?.attributes??{},a=n?.attributes??{},l=s?.attributes??{},c=r&&!me(r)?ge(r.state):ge(o.zone_moisture),d=e.decision_entity.replace(/^sensor\./,"").replace(/_irrigation_decision$/,"");const p=o.references??{},h=ve(t,`sensor.${d}_total_watering_volume`);return{name:e.name??o.friendly_name??"Irrigation Zone",moisture:c,target:ge(o.target_moisture),recommendedLiters:ge(o.recommended_liters),availableWater:ge(o.available_water),decision:me(i)?null:i?.state??null,decisionReason:o.reason??null,wateringStatus:me(n)?null:n?.state??null,isWatering:!0===a.is_watering,canStop:!0===a.can_stop,historyCount:ge(s?.state)??0,lastKind:l.last_kind??null,historyEntries:Array.isArray(l.entries)?l.entries:[],greenhouse:!0===o.greenhouse,protectedRain:!0===o.protected_rain,temperature:ge(o.temperature),humidity:ge(o.humidity),targetMode:"string"==typeof o.target_mode?o.target_mode:null,demandProfile:"string"==typeof o.demand_profile?o.demand_profile:null,targetBandLow:ge(o.target_band_low),targetBandHigh:ge(o.target_band_high),references:$e(p,t),schedule:Ce(d,t),learned:Ae(d,t),totalVolume:h&&!me(h)?ge(h.state):null,totalVolumeUnit:fe(h),targetControl:Pe(t,`number.${d}_target_moisture`,"Target Moisture"),autoTargetControl:Pe(t,`switch.${d}_target_automatic`,"Automatic Target"),maxLitersControl:Pe(t,`number.${d}_max_liters_per_run`,"Max Liters per Run"),enabledControl:Pe(t,`switch.${d}_zone_enabled`,"Zone Enabled"),learningControl:Pe(t,`switch.${d}_learning_enabled`,"Learning Enabled"),modelInsight:Ee(d,t,o)}}function Re(e){return e.canStop&&e.isWatering}function Te(e){return e?Object.keys(e).filter(e=>e.startsWith("sensor.")&&e.endsWith("_irrigation_decision")).sort():[]}const Oe={run_request:"Run requested",decision:"Decision",rain_event:"Rain",watering_event:"Watering"},He="mdi:sprinkler-variant";let Le=class extends ae{constructor(){super(...arguments),this._activeZoneIndex=null}static getStubConfig(e){return{zones:Te(e?.states).map(e=>({decision_entity:e}))}}static async getConfigElement(){return document.createElement("amazing-irrigation-overview-card-editor")}setConfig(e){if(!e||!Array.isArray(e.zones)||0===e.zones.length)throw new Error("amazing-irrigation-overview-card: 'zones' must list at least one zone");for(const t of e.zones)if(!t.decision_entity)throw new Error("amazing-irrigation-overview-card: each zone needs 'decision_entity'");this._config=e}getCardSize(){return this._config?Math.ceil(this._config.zones.length/2)+2:3}_openZone(e){this._activeZoneIndex=e}_closeZone(){this._activeZoneIndex=null}_callZoneService(e,t,i=!1){if(!this.hass)return;const r={entity_id:e};"run_zone"===t&&(r.force=i),this.hass.callService("amazing_irrigation",t,r)}_moreInfo(e){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:e},bubbles:!0,composed:!0}))}_toggleSwitch(e){this.hass&&this.hass.callService("switch","toggle",{entity_id:e})}render(){if(!this._config||!this.hass)return q;if(null!==this._activeZoneIndex){const e=this._config.zones[this._activeZoneIndex];if(!e)return this._activeZoneIndex=null,q;const t=Me(e,this.hass.states);return this._renderDetail(t,e)}return this._renderOverview()}_renderOverview(){const e=(t=this._config,i=this.hass.states,(Array.isArray(t.zones)?t.zones:[]).map(e=>Me(e,i)));var t,i;return N`
      <ha-card>
        ${this._config.title?N`<div class="card-header">${this._config.title}</div>`:q}
        <div class="zone-grid">
          ${e.map((e,t)=>this._renderZoneTile(e,t))}
        </div>
      </ha-card>
    `}_renderZoneTile(e,t){const i=this._config.zones[t].icon||He,r=null!==e.moisture&&null!==e.target&&e.target>0?Math.min(100,Math.round(e.moisture/e.target*100)):e.moisture??0,n=e.isWatering?"watering":"skip"===e.decision?"skip":"water"===e.decision?"pending-water":"";return N`
      <button
        class="zone-tile ${n}"
        @click=${()=>this._openZone(t)}
      >
        <div class="tile-icon-wrap">
          <ha-icon .icon=${i}></ha-icon>
          ${e.isWatering?N`<span class="tile-pulse"></span>`:q}
        </div>
        <span class="tile-name">${e.name}</span>
        <div class="tile-bar-track">
          <div
            class="tile-bar-fill"
            style="width: ${r}%"
          ></div>
          ${null!==e.target?N`<div
                class="tile-bar-target"
                style="left: ${Math.min(100,e.target)}%"
              ></div>`:q}
        </div>
        <div class="tile-stats">
          <span class="tile-moisture"
            >${null!==e.moisture?`${e.moisture}%`:"–"}</span
          >
          ${null!==e.target?N`<span class="tile-target">/ ${e.target}%</span>`:q}
        </div>
      </button>
    `}_renderDetail(e,t){return N`
      <ha-card class="detail-card">
        <div class="detail-header">
          <button class="back-btn" @click=${this._closeZone}>
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
            ?disabled=${!1}
            @click=${()=>this._callZoneService(t.decision_entity,"run_zone")}
          >
            <ha-icon icon="mdi:play" slot="icon"></ha-icon>
            Run
          </mwc-button>
          <mwc-button
            ?disabled=${!1}
            @click=${()=>this._callZoneService(t.decision_entity,"run_zone",!0)}
          >
            <ha-icon icon="mdi:water" slot="icon"></ha-icon>
            Force
          </mwc-button>
          ${Re(e)?N`<mwc-button
                class="stop-btn"
                @click=${()=>this._callZoneService(t.decision_entity,"stop_zone")}
              >
                <ha-icon icon="mdi:stop" slot="icon"></ha-icon>
                Stop
              </mwc-button>`:q}
        </div>
      </ha-card>
    `}_renderMoistureSection(e){const t=e.targetBandLow??e.target??0,i=e.targetBandHigh??e.target??100,r=e.moisture??0,n=Math.min(100,Math.max(0,r));return N`
      <div class="moisture-section">
        <div class="moisture-gauge">
          <div class="gauge-labels">
            <span class="gauge-current">${e.moisture??"–"}%</span>
            <span class="gauge-sublabel">Zone Moisture</span>
          </div>
          <div class="gauge-bar-wrap">
            <div class="gauge-bar-track">
              ${null!==e.targetBandLow&&null!==e.targetBandHigh?N`<div
                    class="gauge-target-band"
                    style="left: ${t}%; width: ${i-t}%"
                  ></div>`:null!==e.target?N`<div
                      class="gauge-target-line"
                      style="left: ${e.target}%"
                    ></div>`:q}
              <div class="gauge-fill" style="width: ${n}%"></div>
              <div class="gauge-marker" style="left: ${n}%"></div>
            </div>
            <div class="gauge-ticks">
              <span>0%</span>
              ${null!==e.targetBandLow?N`<span style="left:${t}%">${Math.round(t)}</span>`:q}
              ${null!==e.targetBandHigh?N`<span style="left:${i}%">${Math.round(i)}</span>`:q}
              <span>100%</span>
            </div>
          </div>
        </div>

        <div class="metric-row">
          ${this._metric("Target","auto"===e.targetMode&&null!==e.targetBandLow&&null!==e.targetBandHigh?`${Math.round(e.targetBandLow)}–${Math.round(e.targetBandHigh)}%`:null!==e.target?`${e.target}%`:"–")}
          ${null!==e.recommendedLiters?this._metric("Recommended",`${e.recommendedLiters} L`):q}
          ${null!==e.availableWater?this._metric("Available",`${Math.round(100*e.availableWater)}%`):q}
          ${null!==e.totalVolume?this._metric("Total Used",`${e.totalVolume} ${e.totalVolumeUnit??"L"}`):q}
        </div>
      </div>
    `}_renderDecisionBanner(e){if(!e.decision)return q;const t="water"===e.decision?"water":"skip"===e.decision?"skip":"neutral";return N`
      <div class="decision-banner ${t}">
        <span class="decision-label">${e.decision}</span>
        ${e.decisionReason?N`<span class="decision-reason"
              >${e.decisionReason.replace(/_/g," ")}</span
            >`:q}
      </div>
    `}_renderPrediction(e){const t=e.modelInsight?.decisionExplanation;if(!t||!t.predictedTrajectory.length)return q;const i=t.predictedTrajectory,r=Math.max(...i,e.targetBandHigh??e.target??60),n=Math.min(...i,e.targetBandLow??20),s=r-n||1,o=i.map((e,t)=>`${t/(i.length-1)*100},${60-(e-n)/s*60}`).join(" "),a=null!==e.target?60-(e.target-n)/s*60:null;return N`
      <div class="prediction-section">
        <div class="section-label">
          Predicted Trajectory
          ${null!==t.horizonHours?N`<span class="sublabel">${t.horizonHours}h horizon</span>`:q}
        </div>
        <svg
          class="sparkline"
          viewBox="0 0 ${100} ${60}"
          preserveAspectRatio="none"
        >
          ${null!==a?N`<line
                x1="0"
                y1="${a}"
                x2="${100}"
                y2="${a}"
                class="spark-target"
              />`:q}
          <polyline points="${o}" class="spark-line" />
        </svg>
        ${null!==t.chosenLiters?N`<div class="prediction-note">
              Chosen: ${t.chosenLiters} L
              ${null!==t.predictedCriticalTheta?N` · Low: ${t.predictedCriticalTheta}%`:q}
              ${null!==t.predictedPeakTheta?N` · Peak: ${t.predictedPeakTheta}%`:q}
            </div>`:q}
      </div>
    `}_renderGreenhouse(e){return e.greenhouse?N`
      <div class="info-row greenhouse-row">
        <ha-icon icon="mdi:greenhouse"></ha-icon>
        <span>Greenhouse</span>
        <span class="chip ${e.protectedRain?"on":""}">
          ${e.protectedRain?"Rain protected":"Open to rain"}
        </span>
        ${null!==e.temperature?N`<span class="chip">${e.temperature}°C</span>`:q}
        ${null!==e.humidity?N`<span class="chip">${e.humidity}% RH</span>`:q}
      </div>
    `:q}_renderControls(e){const t=[e.autoTargetControl?.isOn??"auto"===e.targetMode?null:e.targetControl,e.maxLitersControl].filter(e=>null!==e),i=[e.enabledControl,e.learningControl,e.autoTargetControl].filter(e=>null!==e);return t.length||i.length?N`
      <div class="section">
        <div class="section-label">Settings</div>
        ${t.map(e=>N`
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
        ${i.map(e=>N`
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
    `:q}_renderSchedule(e){return e.schedule.length?N`
      <div class="section">
        <div class="section-label">Schedule</div>
        ${e.schedule.map(e=>N`
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
    `:q}_renderModelInsight(e){const t=e.modelInsight;if(!t)return q;const i=t.decisionExplanation;return N`
      <details class="section collapsible">
        <summary class="section-label">
          <span>Model Insight</span>
          ${null!==t.overallConfidence?N`<span class="confidence-badge"
                >${Math.round(100*t.overallConfidence)}%</span
              >`:q}
        </summary>
        ${t.bootstrapSummary?N`<div class="note">${t.bootstrapSummary}</div>`:q}
        ${i?.terms.length?N`
              <div class="terms-grid">
                ${i.terms.map(e=>N`
                    <div class="term ${e.value>0?"gain":"loss"}">
                      <span class="term-label">${e.label}</span>
                      <span class="term-value"
                        >${e.value>0?"+":""}${e.value}${e.unit}</span
                      >
                    </div>
                  `)}
              </div>
            `:q}
        ${t.parameters.length?N`
              <div class="params-section">
                ${t.parameters.map(e=>this._renderParam(e))}
              </div>
            `:q}
        ${t.modelUpdated?N`<div class="note">
              Updated ${new Date(t.modelUpdated).toLocaleString()}
            </div>`:q}
      </details>
    `}_renderParam(e){return N`
      <div class="row param-row">
        <span class="row-label">${e.label}</span>
        <span class="row-value">
          ${null===e.value?"learning…":`${e.value} ${e.unit??""}`}
          ${null!==e.confidence?N`<span class="conf-bar">
                <span style="width:${Math.round(100*e.confidence)}%"></span>
              </span>`:q}
        </span>
      </div>
    `}_renderReferences(e){return e.references.length?N`
      <details class="section collapsible">
        <summary class="section-label">Sensors</summary>
        ${e.references.map(e=>N`
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
    `:q}_renderHistory(e){if(!e.historyEntries.length)return q;const t=e.historyEntries.slice(0,5);return N`
      <details class="section collapsible">
        <summary class="section-label">
          History
          <span class="badge-count">${e.historyCount}</span>
        </summary>
        <div class="history-list">
          ${t.map(e=>{const t=String(e.kind??"");return N`
              <div class="history-entry">
                <span class="history-kind">${Oe[t]??t}</span>
                <span class="history-detail">${this._historyDetail(e)}</span>
              </div>
            `})}
        </div>
      </details>
    `}_historyDetail(e){if(e.action)return`${e.action} (${e.reason??""})`;if(e.status){const t=e.measured_liters??e.requested_liters;return null==t?String(e.status):`${e.status} · ${t} L`}return void 0!==e.delta_mm?`+${e.delta_mm} mm`:""}_metric(e,t){return N`<div class="metric">
      <span class="metric-value">${t}</span>
      <span class="metric-label">${e}</span>
    </div>`}};Le.styles=o`
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

    /* ── Prediction Sparkline ──────────────────────── */
    .prediction-section {
      padding: 8px 16px 12px;
    }
    .sparkline {
      width: 100%;
      height: 48px;
      display: block;
    }
    .spark-line {
      fill: none;
      stroke: var(--primary-color);
      stroke-width: 1.5;
      vector-effect: non-scaling-stroke;
    }
    .spark-target {
      stroke: var(--secondary-text-color);
      stroke-width: 0.5;
      stroke-dasharray: 3 2;
      vector-effect: non-scaling-stroke;
    }
    .prediction-note {
      font-size: 0.75rem;
      color: var(--secondary-text-color);
      margin-top: 4px;
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
      font-size: 0.72rem;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 8px;
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }
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
    }
    .stop-btn {
      --mdc-theme-primary: var(--error-color);
    }
  `,e([he({attribute:!1})],Le.prototype,"hass",void 0),e([ue()],Le.prototype,"_config",void 0),e([ue()],Le.prototype,"_activeZoneIndex",void 0),Le=e([ce("amazing-irrigation-overview-card")],Le),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-overview-card",name:"Amazing Irrigation",description:"Professional irrigation dashboard with zone overview and detail drill-down."});const Ie="amazing_irrigation",Ue=[{name:"decision_entity",required:!0,selector:{entity:{integration:Ie,domain:"sensor"}}},{name:"name",selector:{text:{}}},{name:"icon",selector:{icon:{}}},{name:"moisture_entity",selector:{entity:{domain:"sensor"}}},{name:"status_entity",selector:{entity:{integration:Ie,domain:"sensor"}}},{name:"history_entity",selector:{entity:{integration:Ie,domain:"sensor"}}}],je=[{name:"title",selector:{text:{}}}],De={decision_entity:"Decision sensor (required)",name:"Zone name (optional)",icon:"Zone icon (optional)",moisture_entity:"Soil moisture sensor (optional)",status_entity:"Status sensor (optional)",history_entity:"History sensor (optional)",title:"Card title (optional)"},Be=e=>De[e.name]??e.name;function Ze(e,t){e.dispatchEvent(new CustomEvent("config-changed",{detail:{config:t},bubbles:!0,composed:!0}))}let Ne=class extends ae{setConfig(e){this._config=e}render(){return this.hass&&this._config?N`
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${Ue}
        .computeLabel=${Be}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `:q}_valueChanged(e){e.stopPropagation(),Ze(this,e.detail.value)}};e([he({attribute:!1})],Ne.prototype,"hass",void 0),e([ue()],Ne.prototype,"_config",void 0),Ne=e([ce("amazing-irrigation-card-editor")],Ne);let We=class extends ae{setConfig(e){this._config={...e,zones:Array.isArray(e.zones)?e.zones:[]}}get _zones(){return this._config?.zones??[]}render(){return this.hass&&this._config?N`
      <div class="editor">
        <ha-form
          .hass=${this.hass}
          .data=${{title:this._config.title??""}}
          .schema=${je}
          .computeLabel=${Be}
          @value-changed=${this._titleChanged}
        ></ha-form>

        <div class="zones">
          ${this._zones.map((e,t)=>this._renderZone(e,t))}
          ${0===this._zones.length?N`<div class="hint">
                Add at least one zone (select its Decision sensor).
              </div>`:q}
        </div>

        <mwc-button outlined @click=${this._addZone}>+ Add zone</mwc-button>
      </div>
    `:q}_renderZone(e,t){return N`
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
          .schema=${Ue}
          .computeLabel=${Be}
          .index=${t}
          @value-changed=${this._zoneChanged}
        ></ha-form>
      </div>
    `}_titleChanged(e){e.stopPropagation();const t=e.detail.value.title,i={...this._config,title:t};t||delete i.title,this._emit(i)}_zoneChanged(e){e.stopPropagation();const t=e.currentTarget.index;if(void 0===t)return;const i=[...this._zones];i[t]=e.detail.value,this._emit({...this._config,zones:i})}_addZone(){const e=[...this._zones,{decision_entity:""}];this._emit({...this._config,zones:e})}_removeZone(e){const t=this._zones.filter((t,i)=>i!==e);this._emit({...this._config,zones:t})}_emit(e){this._config=e,Ze(this,e)}};We.styles=o`
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
  `,e([he({attribute:!1})],We.prototype,"hass",void 0),e([ue()],We.prototype,"_config",void 0),We=e([ce("amazing-irrigation-overview-card-editor")],We);const qe={run_request:"Run requested",decision:"Decision",rain_event:"Rain",watering_event:"Watering"};let Ve=class extends ae{static getStubConfig(e){const[t]=Te(e?.states);return{decision_entity:t??""}}static async getConfigElement(){return document.createElement("amazing-irrigation-card-editor")}setConfig(e){if(!e||!e.decision_entity)throw new Error("amazing-irrigation-card: 'decision_entity' is required");this._config=e}getCardSize(){return 4}get _view(){if(this._config&&this.hass)return Me(this._config,this.hass.states)}_callZoneService(e,t=!1){if(!this.hass||!this._config)return;const i={entity_id:this._config.decision_entity};"run_zone"===e&&(i.force=t),this.hass.callService("amazing_irrigation",e,i)}_moreInfo(e){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:e},bubbles:!0,composed:!0}))}_toggleSwitch(e){this.hass&&this.hass.callService("switch","toggle",{entity_id:e})}render(){const e=this._view;return this._config?e?N`
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
          ${null===e.demandProfile?q:this._metric("Demand",e.demandProfile.charAt(0).toUpperCase()+e.demandProfile.slice(1))}
          ${this._metric("Recommended",null===e.recommendedLiters?"–":`${e.recommendedLiters} L`)}
          ${null===e.availableWater?q:this._metric("Available water",`${Math.round(100*e.availableWater)}%`)}
          ${null===e.totalVolume?q:this._metric("Total water",`${e.totalVolume} ${e.totalVolumeUnit??"L"}`)}
        </div>

        <div class="decision">
          <span class="decision-action">${e.decision??"–"}</span>
          ${e.decisionReason?N`<span class="decision-reason"
                >${e.decisionReason.replace(/_/g," ")}</span
              >`:q}
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
            ?disabled=${!1}
            @click=${()=>this._callZoneService("run_zone")}
            >Run</mwc-button
          >
          <mwc-button
            ?disabled=${!1}
            @click=${()=>this._callZoneService("run_zone",!0)}
            >Force Water</mwc-button
          >
          ${Re(e)?N`<mwc-button
                class="stop"
                @click=${()=>this._callZoneService("stop_zone")}
                >Stop</mwc-button
              >`:q}
        </div>
      </ha-card>
    `:N`<ha-card><div class="empty">Loading…</div></ha-card>`:q}_renderGreenhouse(e){return e.greenhouse?N`
      <div class="greenhouse">
        <span class="badge">🌱 Greenhouse</span>
        <span class="ctx ${e.protectedRain?"on":""}">
          ${e.protectedRain?"Protected from rain":"Open to rain"}
        </span>
        ${null!==e.temperature?N`<span class="ctx">${e.temperature}°C</span>`:q}
        ${null!==e.humidity?N`<span class="ctx">${e.humidity}% RH</span>`:q}
      </div>
    `:q}_renderControls(e){const t=e.autoTargetControl?.isOn??"auto"===e.targetMode,i=[t?null:e.targetControl,e.maxLitersControl].filter(e=>null!==e),r=[e.enabledControl,e.learningControl,e.autoTargetControl].filter(e=>null!==e),n=t&&null!==e.targetBandLow&&null!==e.targetBandHigh;return i.length||r.length||n?N`
      <div class="section">
        <div class="section-head">Settings</div>
        ${n?N`
              <div class="row">
                <span class="row-label">Target band (auto)</span>
                <span class="row-value"
                  >${Math.round(e.targetBandLow)}–${Math.round(e.targetBandHigh)} %</span
                >
              </div>
            `:q}
        ${i.map(e=>N`
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
        ${r.map(e=>N`
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
    `:q}_renderSchedule(e){return e.schedule.length?N`
      <div class="section">
        <div class="section-head">Schedule</div>
        ${e.schedule.map(e=>N`
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
    `:q}_renderLearned(e){return e.learned.length?N`
      <div class="section">
        <div class="section-head">Learned model</div>
        ${e.learned.map(e=>N`
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
    `:q}_renderReferences(e){return e.references.length?N`
      <div class="section">
        <div class="section-head">Sensors</div>
        ${e.references.map(e=>N`
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
    `:q}_renderModelInsight(e){const t=e.modelInsight;if(!t)return q;const i=t.decisionExplanation;return N`
      <details class="section model-insight">
        <summary>
          <span>Why this decision</span>
          ${t.status?N`<span>${t.status}</span>`:q}
        </summary>
        ${t.bootstrapSummary?N`<div class="model-note">${t.bootstrapSummary}</div>`:q}
        ${i?this._renderDecisionExplanation(i):q}
        ${t.parameters.length?N`
              <div class="section-head">Model parameters</div>
              ${t.parameters.map(e=>this._renderModelParameter(e))}
            `:q}
        ${t.modelUpdated?N`<div class="model-note">
              Updated ${new Date(t.modelUpdated).toLocaleString()}
            </div>`:q}
      </details>
    `}_renderDecisionExplanation(e){return N`
      <div class="model-note">
        ${e.predictiveReason?`Reason: ${e.predictiveReason.replace(/_/g," ")}`:"Predictive water-balance decision"}
        ${null===e.horizonHours?"":` over ${e.horizonHours} h`}
        ${null===e.chosenLiters?"":` · chosen ${e.chosenLiters} L`}
      </div>
      ${e.predictedTrajectory.length?N`
            <div class="section-head">Predicted moisture trajectory</div>
            <div class="trajectory">
              ${e.predictedTrajectory.map((e,t)=>N`<span>Step ${t+1}: ${e}%</span>`)}
            </div>
          `:q}
      ${null!==e.predictedCriticalTheta||null!==e.predictedPeakTheta?N`<div class="model-note">
            ${null===e.predictedCriticalTheta?"":`Lowest predicted moisture: ${e.predictedCriticalTheta}%`}
            ${null===e.predictedPeakTheta?"":` Peak: ${e.predictedPeakTheta}%`}
          </div>`:q}
      ${e.terms.length?N`
            <div class="section-head">Water-balance terms</div>
            ${e.terms.map(e=>this._renderTerm(e))}
          `:q}
    `}_renderTerm(e){const t=e.value>0?"+":"";return N`
      <div class="row">
        <span class="row-label">${e.label}</span>
        <span class="row-value">${t}${e.value} ${e.unit}</span>
      </div>
    `}_renderModelParameter(e){return N`
      <div class="row model-param">
        <span class="row-label">${e.label}</span>
        <span class="row-value">
          ${null===e.value?"learning…":`${e.value} ${e.unit??""}`}
          ${null===e.confidence?q:N`<span class="confidence">
                <span
                  style="width: ${Math.round(100*e.confidence)}%"
                ></span>
              </span>
              ${Math.round(100*e.confidence)}%`}
        </span>
      </div>
    `}_renderHistory(e){if(!e.historyEntries.length)return q;const t=e.historyEntries.slice(0,5);return N`
      <div class="history">
        <div class="history-head">
          History (${e.historyCount})
        </div>
        <ul>
          ${t.map(e=>{const t=String(e.kind??"");return N`<li>
              <span class="kind">${qe[t]??t}</span>
              <span class="detail">${this._historyDetail(e)}</span>
            </li>`})}
        </ul>
      </div>
    `}_historyDetail(e){if(e.action)return`${e.action} (${e.reason??""})`;if(e.status){const t=e.measured_liters??e.requested_liters;return null==t?String(e.status):`${e.status} · ${t} L`}return void 0!==e.delta_mm?`+${e.delta_mm} mm`:""}_metric(e,t){return N`<div class="metric">
      <div class="metric-value">${t}</div>
      <div class="metric-label">${e}</div>
    </div>`}_pct(e){return null===e?"–":`${e}%`}};Ve.styles=o`
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
  `,e([he({attribute:!1})],Ve.prototype,"hass",void 0),e([ue()],Ve.prototype,"_config",void 0),Ve=e([ce("amazing-irrigation-card")],Ve),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-card",name:"Amazing Irrigation Zone",description:"Display and control a single Amazing Irrigation zone."});export{Ve as AmazingIrrigationCard};
