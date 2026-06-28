function t(t,e,s,i){var r,n=arguments.length,o=n<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,s):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)o=Reflect.decorate(t,e,s,i);else for(var a=t.length-1;a>=0;a--)(r=t[a])&&(o=(n<3?r(o):n>3?r(e,s,o):r(e,s))||o);return n>3&&o&&Object.defineProperty(e,s,o),o}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,s=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),r=new WeakMap;let n=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(s&&void 0===t){const s=void 0!==e&&1===e.length;s&&(t=r.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&r.set(e,t))}return t}toString(){return this.cssText}};const o=(t,...e)=>{const s=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new n(s,t,i)},a=s?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new n("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:c,defineProperty:l,getOwnPropertyDescriptor:h,getOwnPropertyNames:d,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,m=globalThis,g=m.trustedTypes,$=g?g.emptyScript:"",_=m.reactiveElementPolyfillSupport,f=(t,e)=>t,y={toAttribute(t,e){switch(e){case Boolean:t=t?$:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},v=(t,e)=>!c(t,e),A={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:v};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let b=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=A){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&l(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:r}=h(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const n=i?.call(this);r?.call(this,e),this.requestUpdate(t,n,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??A}static _$Ei(){if(this.hasOwnProperty(f("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(f("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(f("properties"))){const t=this.properties,e=[...d(t),...p(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(s)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const s of i){const i=document.createElement("style"),r=e.litNonce;void 0!==r&&i.setAttribute("nonce",r),i.textContent=s.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const r=(void 0!==s.converter?.toAttribute?s.converter:y).toAttribute(e,s.type);this._$Em=t,null==r?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),r="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:y;this._$Em=i;const n=r.fromAttribute(e,t.type);this[i]=n??this._$Ej?.get(i)??n,this._$Em=null}}requestUpdate(t,e,s,i=!1,r){if(void 0!==t){const n=this.constructor;if(!1===i&&(r=this[t]),s??=n.getPropertyOptions(t),!((s.hasChanged??v)(r,e)||s.useDefault&&s.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(n._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:r},n){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,n??e??this[t]),!0!==r||void 0!==n)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};b.elementStyles=[],b.shadowRootOptions={mode:"open"},b[f("elementProperties")]=new Map,b[f("finalized")]=new Map,_?.({ReactiveElement:b}),(m.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const w=globalThis,x=t=>t,E=w.trustedTypes,S=E?E.createPolicy("lit-html",{createHTML:t=>t}):void 0,C="$lit$",z=`lit$${Math.random().toFixed(9).slice(2)}$`,P="?"+z,R=`<${P}>`,O=document,U=()=>O.createComment(""),H=t=>null===t||"object"!=typeof t&&"function"!=typeof t,M=Array.isArray,T="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,k=/-->/g,j=/>/g,D=RegExp(`>|${T}(?:([^\\s"'>=/]+)(${T}*=${T}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),L=/'/g,I=/"/g,W=/^(?:script|style|textarea|title)$/i,q=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),B=Symbol.for("lit-noChange"),Z=Symbol.for("lit-nothing"),V=new WeakMap,F=O.createTreeWalker(O,129);function G(t,e){if(!M(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(e):e}const K=(t,e)=>{const s=t.length-1,i=[];let r,n=2===e?"<svg>":3===e?"<math>":"",o=N;for(let e=0;e<s;e++){const s=t[e];let a,c,l=-1,h=0;for(;h<s.length&&(o.lastIndex=h,c=o.exec(s),null!==c);)h=o.lastIndex,o===N?"!--"===c[1]?o=k:void 0!==c[1]?o=j:void 0!==c[2]?(W.test(c[2])&&(r=RegExp("</"+c[2],"g")),o=D):void 0!==c[3]&&(o=D):o===D?">"===c[0]?(o=r??N,l=-1):void 0===c[1]?l=-2:(l=o.lastIndex-c[2].length,a=c[1],o=void 0===c[3]?D:'"'===c[3]?I:L):o===I||o===L?o=D:o===k||o===j?o=N:(o=D,r=void 0);const d=o===D&&t[e+1].startsWith("/>")?" ":"";n+=o===N?s+R:l>=0?(i.push(a),s.slice(0,l)+C+s.slice(l)+z+d):s+z+(-2===l?e:d)}return[G(t,n+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class J{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let r=0,n=0;const o=t.length-1,a=this.parts,[c,l]=K(t,e);if(this.el=J.createElement(c,s),F.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=F.nextNode())&&a.length<o;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(C)){const e=l[n++],s=i.getAttribute(t).split(z),o=/([.?@])?(.*)/.exec(e);a.push({type:1,index:r,name:o[2],strings:s,ctor:"."===o[1]?et:"?"===o[1]?st:"@"===o[1]?it:tt}),i.removeAttribute(t)}else t.startsWith(z)&&(a.push({type:6,index:r}),i.removeAttribute(t));if(W.test(i.tagName)){const t=i.textContent.split(z),e=t.length-1;if(e>0){i.textContent=E?E.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],U()),F.nextNode(),a.push({type:2,index:++r});i.append(t[e],U())}}}else if(8===i.nodeType)if(i.data===P)a.push({type:2,index:r});else{let t=-1;for(;-1!==(t=i.data.indexOf(z,t+1));)a.push({type:7,index:r}),t+=z.length-1}r++}}static createElement(t,e){const s=O.createElement("template");return s.innerHTML=t,s}}function Q(t,e,s=t,i){if(e===B)return e;let r=void 0!==i?s._$Co?.[i]:s._$Cl;const n=H(e)?void 0:e._$litDirective$;return r?.constructor!==n&&(r?._$AO?.(!1),void 0===n?r=void 0:(r=new n(t),r._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=r:s._$Cl=r),void 0!==r&&(e=Q(t,r._$AS(t,e.values),r,i)),e}class X{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??O).importNode(e,!0);F.currentNode=i;let r=F.nextNode(),n=0,o=0,a=s[0];for(;void 0!==a;){if(n===a.index){let e;2===a.type?e=new Y(r,r.nextSibling,this,t):1===a.type?e=new a.ctor(r,a.name,a.strings,this,t):6===a.type&&(e=new rt(r,this,t)),this._$AV.push(e),a=s[++o]}n!==a?.index&&(r=F.nextNode(),n++)}return F.currentNode=O,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class Y{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=Z,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Q(this,t,e),H(t)?t===Z||null==t||""===t?(this._$AH!==Z&&this._$AR(),this._$AH=Z):t!==this._$AH&&t!==B&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>M(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==Z&&H(this._$AH)?this._$AA.nextSibling.data=t:this.T(O.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=J.createElement(G(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new X(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=V.get(t.strings);return void 0===e&&V.set(t.strings,e=new J(t)),e}k(t){M(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const r of t)i===e.length?e.push(s=new Y(this.O(U()),this.O(U()),this,this.options)):s=e[i],s._$AI(r),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=x(t).nextSibling;x(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,r){this.type=1,this._$AH=Z,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=r,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=Z}_$AI(t,e=this,s,i){const r=this.strings;let n=!1;if(void 0===r)t=Q(this,t,e,0),n=!H(t)||t!==this._$AH&&t!==B,n&&(this._$AH=t);else{const i=t;let o,a;for(t=r[0],o=0;o<r.length-1;o++)a=Q(this,i[s+o],e,o),a===B&&(a=this._$AH[o]),n||=!H(a)||a!==this._$AH[o],a===Z?t=Z:t!==Z&&(t+=(a??"")+r[o+1]),this._$AH[o]=a}n&&!i&&this.j(t)}j(t){t===Z?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===Z?void 0:t}}class st extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==Z)}}class it extends tt{constructor(t,e,s,i,r){super(t,e,s,i,r),this.type=5}_$AI(t,e=this){if((t=Q(this,t,e,0)??Z)===B)return;const s=this._$AH,i=t===Z&&s!==Z||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,r=t!==Z&&(s===Z||i);i&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class rt{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){Q(this,t)}}const nt=w.litHtmlPolyfillSupport;nt?.(J,Y),(w.litHtmlVersions??=[]).push("3.3.3");const ot=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class at extends b{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let r=i._$litPart$;if(void 0===r){const t=s?.renderBefore??null;i._$litPart$=r=new Y(e.insertBefore(U(),t),t,void 0,s??{})}return r._$AI(t),r})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return B}}at._$litElement$=!0,at.finalized=!0,ot.litElementHydrateSupport?.({LitElement:at});const ct=ot.litElementPolyfillSupport;ct?.({LitElement:at}),(ot.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const lt=t=>(e,s)=>{void 0!==s?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},ht={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:v},dt=(t=ht,e,s)=>{const{kind:i,metadata:r}=s;let n=globalThis.litPropertyMetadata.get(r);if(void 0===n&&globalThis.litPropertyMetadata.set(r,n=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),n.set(s.name,t),"accessor"===i){const{name:i}=s;return{set(s){const r=e.get.call(this);e.set.call(this,s),this.requestUpdate(i,r,t,!0,s)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=s;return function(s){const r=this[i];e.call(this,s),this.requestUpdate(i,r,t,!0,s)}}throw Error("Unsupported decorator location: "+i)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return(e,s)=>"object"==typeof s?dt(t,e,s):((t,e,s)=>{const i=e.hasOwnProperty(s);return e.constructor.createProperty(s,t),i?Object.getOwnPropertyDescriptor(e,s):void 0})(t,e,s)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return pt({...t,state:!0,attribute:!1})}function mt(t){if(null==t||""===t)return null;const e="number"==typeof t?t:Number(t);return Number.isFinite(e)?e:null}function gt(t){return void 0===t||"unavailable"===t.state||"unknown"===t.state}function $t(t,e){const s=t.decision_entity?e[t.decision_entity]:void 0,i=t.moisture_entity?e[t.moisture_entity]:void 0,r=t.status_entity?e[t.status_entity]:void 0,n=t.history_entity?e[t.history_entity]:void 0,o=s?.attributes??{},a=r?.attributes??{},c=n?.attributes??{},l=i&&!gt(i)?mt(i.state):mt(o.zone_moisture);return{name:t.name??o.friendly_name??"Irrigation Zone",moisture:l,target:mt(o.target_moisture),recommendedLiters:mt(o.recommended_liters),availableWater:mt(o.available_water),decision:gt(s)?null:s?.state??null,decisionReason:o.reason??null,wateringStatus:gt(r)?null:r?.state??null,isWatering:!0===a.is_watering,canStop:!0===a.can_stop,historyCount:mt(n?.state)??0,lastKind:c.last_kind??null,historyEntries:Array.isArray(c.entries)?c.entries:[],greenhouse:!0===o.greenhouse,protectedRain:!0===o.protected_rain,temperature:mt(o.temperature),humidity:mt(o.humidity)}}let _t=class extends at{static getStubConfig(){return{zones:[]}}setConfig(t){if(!t||!Array.isArray(t.zones)||0===t.zones.length)throw new Error("amazing-irrigation-overview-card: 'zones' must list at least one zone");for(const e of t.zones)if(!e.decision_entity)throw new Error("amazing-irrigation-overview-card: each zone needs 'decision_entity'");this._config=t}getCardSize(){return this._config?this._config.zones.length+1:1}render(){if(!this._config||!this.hass)return Z;const t=(e=this._config,s=this.hass.states,(Array.isArray(e.zones)?e.zones:[]).map(t=>$t(t,s)));var e,s;return q`
      <ha-card>
        ${this._config.title?q`<div class="title">${this._config.title}</div>`:Z}
        <div class="zones">
          ${t.map(t=>this._renderRow(t))}
        </div>
      </ha-card>
    `}_renderRow(t){return q`
      <div class="zone">
        <div class="primary">
          <span class="name">
            ${t.greenhouse?q`<span class="gh">🌱</span>`:Z}
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
          ${t.greenhouse&&t.protectedRain?q`<span class="ctx">rain-protected</span>`:Z}
          ${t.greenhouse&&null!==t.temperature?q`<span class="ctx">${t.temperature}°C</span>`:Z}
          ${t.greenhouse&&null!==t.humidity?q`<span class="ctx">${t.humidity}% RH</span>`:Z}
        </div>
      </div>
    `}};_t.styles=o`
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
  `,t([pt({attribute:!1})],_t.prototype,"hass",void 0),t([ut()],_t.prototype,"_config",void 0),_t=t([lt("amazing-irrigation-overview-card")],_t),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-overview-card",name:"Amazing Irrigation Overview",description:"Compact multi-zone overview for Amazing Irrigation."});const ft={run_request:"Run requested",decision:"Decision",rain_event:"Rain",watering_event:"Watering"};let yt=class extends at{static getStubConfig(){return{decision_entity:""}}setConfig(t){if(!t||!t.decision_entity)throw new Error("amazing-irrigation-card: 'decision_entity' is required");this._config=t}getCardSize(){return 4}get _view(){if(this._config&&this.hass)return $t(this._config,this.hass.states)}_callZoneService(t,e=!1){if(!this.hass||!this._config)return;const s={entity_id:this._config.decision_entity};"run_zone"===t&&(s.force=e),this.hass.callService("amazing_irrigation",t,s)}render(){const t=this._view;return this._config?t?q`
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
          ${null===t.availableWater?Z:this._metric("Available water",`${Math.round(100*t.availableWater)}%`)}
        </div>

        <div class="decision">
          <span class="decision-action">${t.decision??"–"}</span>
          ${t.decisionReason?q`<span class="decision-reason"
                >${t.decisionReason.replace(/_/g," ")}</span
              >`:Z}
        </div>

        ${this._renderGreenhouse(t)}
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
          ${function(t){return t.canStop&&t.isWatering}(t)?q`<mwc-button
                class="stop"
                @click=${()=>this._callZoneService("stop_zone")}
                >Stop</mwc-button
              >`:Z}
        </div>
      </ha-card>
    `:q`<ha-card><div class="empty">Loading…</div></ha-card>`:Z}_renderGreenhouse(t){return t.greenhouse?q`
      <div class="greenhouse">
        <span class="badge">🌱 Greenhouse</span>
        <span class="ctx ${t.protectedRain?"on":""}">
          ${t.protectedRain?"Protected from rain":"Open to rain"}
        </span>
        ${null!==t.temperature?q`<span class="ctx">${t.temperature}°C</span>`:Z}
        ${null!==t.humidity?q`<span class="ctx">${t.humidity}% RH</span>`:Z}
      </div>
    `:Z}_renderHistory(t){if(!t.historyEntries.length)return Z;const e=t.historyEntries.slice(0,5);return q`
      <div class="history">
        <div class="history-head">
          History (${t.historyCount})
        </div>
        <ul>
          ${e.map(t=>{const e=String(t.kind??"");return q`<li>
              <span class="kind">${ft[e]??e}</span>
              <span class="detail">${this._historyDetail(t)}</span>
            </li>`})}
        </ul>
      </div>
    `}_historyDetail(t){if(t.action)return`${t.action} (${t.reason??""})`;if(t.status){const e=t.measured_liters??t.requested_liters;return null==e?String(t.status):`${t.status} · ${e} L`}return void 0!==t.delta_mm?`+${t.delta_mm} mm`:""}_metric(t,e){return q`<div class="metric">
      <div class="metric-value">${e}</div>
      <div class="metric-label">${t}</div>
    </div>`}_pct(t){return null===t?"–":`${t}%`}};yt.styles=o`
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
  `,t([pt({attribute:!1})],yt.prototype,"hass",void 0),t([ut()],yt.prototype,"_config",void 0),yt=t([lt("amazing-irrigation-card")],yt),window.customCards=window.customCards||[],window.customCards.push({type:"amazing-irrigation-card",name:"Amazing Irrigation Zone",description:"Display and control a single Amazing Irrigation zone."});export{yt as AmazingIrrigationCard};
