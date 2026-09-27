var AlvoraaMcu=(()=>{var ft=Object.defineProperty;var Wt=Object.getOwnPropertyDescriptor;var $t=Object.getOwnPropertyNames,Ht=Object.getOwnPropertySymbols;var Et=Object.prototype.hasOwnProperty,Kt=Object.prototype.propertyIsEnumerable;var Ot=(t,e,r)=>e in t?ft(t,e,{enumerable:!0,configurable:!0,writable:!0,value:r}):t[e]=r,ot=(t,e)=>{for(var r in e||(e={}))Et.call(e,r)&&Ot(t,r,e[r]);if(Ht)for(var r of Ht(e))Kt.call(e,r)&&Ot(t,r,e[r]);return t};var Jt=(t,e)=>{for(var r in e)ft(t,r,{get:e[r],enumerable:!0})},Xt=(t,e,r,o)=>{if(e&&typeof e=="object"||typeof e=="function")for(let a of $t(e))!Et.call(t,a)&&a!==r&&ft(t,a,{get:()=>e[a],enumerable:!(o=Wt(e,a))||o.enumerable});return t};var Zt=t=>Xt(ft({},"__esModule",{value:!0}),t);var le={};Jt(le,{Hct:()=>I,MaterialDynamicColors:()=>n,SchemeMonochrome:()=>Ct,SchemeTonalSpot:()=>bt,argbFromHex:()=>Gt,hexFromArgb:()=>Ft});/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function E(t){return t<0?-1:t===0?0:1}function Z(t,e,r){return(1-r)*t+r*e}function vt(t,e,r){return r<t?t:r>e?e:r}function et(t,e,r){return r<t?t:r>e?e:r}function gt(t){return t=t%360,t<0&&(t=t+360),t}function z(t){return t=t%360,t<0&&(t=t+360),t}function Dt(t,e){return 180-Math.abs(Math.abs(t-e)-180)}function at(t,e){let r=t[0]*e[0][0]+t[1]*e[0][1]+t[2]*e[0][2],o=t[0]*e[1][0]+t[1]*e[1][1]+t[2]*e[1][2],a=t[0]*e[2][0]+t[1]*e[2][1]+t[2]*e[2][2];return[r,o,a]}/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var Qt=[[.41233895,.35762064,.18051042],[.2126,.7152,.0722],[.01932141,.11916382,.95034478]],te=[[3.2413774792388685,-1.5376652402851851,-.49885366846268053],[-.9691452513005321,1.8758853451067872,.04156585616912061],[.05562093689691305,-.20395524564742123,1.0571799111220335]],ee=[95.047,100,108.883];function pt(t,e,r){return(255<<24|(t&255)<<16|(e&255)<<8|r&255)>>>0}function Tt(t){let e=tt(t[0]),r=tt(t[1]),o=tt(t[2]);return pt(e,r,o)}function dt(t){return t>>16&255}function yt(t){return t>>8&255}function Pt(t){return t&255}function Lt(t,e,r){let o=te,a=o[0][0]*t+o[0][1]*e+o[0][2]*r,i=o[1][0]*t+o[1][1]*e+o[1][2]*r,s=o[2][0]*t+o[2][1]*e+o[2][2]*r,c=tt(a),l=tt(i),m=tt(s);return pt(c,l,m)}function re(t){let e=Q(dt(t)),r=Q(yt(t)),o=Q(Pt(t));return at([e,r,o],Qt)}function Vt(t){let e=G(t),r=tt(e);return pt(r,r,r)}function xt(t){let e=re(t)[1];return 116*Nt(e/100)-16}function G(t){return 100*ne((t+16)/116)}function st(t){return Nt(t/100)*116-16}function Q(t){let e=t/255;return e<=.040449936?e/12.92*100:Math.pow((e+.055)/1.055,2.4)*100}function tt(t){let e=t/100,r=0;return e<=.0031308?r=e*12.92:r=1.055*Math.pow(e,1/2.4)-.055,vt(0,255,Math.round(r*255))}function zt(){return ee}function Nt(t){let e=.008856451679035631,r=24389/27;return t>e?Math.pow(t,1/3):(r*t+16)/116}function ne(t){let e=.008856451679035631,r=24389/27,o=t*t*t;return o>e?o:(116*t-16)/r}/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var N=class t{static make(e=zt(),r=200/Math.PI*G(50)/100,o=50,a=2,i=!1){let s=e,c=s[0]*.401288+s[1]*.650173+s[2]*-.051461,l=s[0]*-.250268+s[1]*1.204414+s[2]*.045854,m=s[0]*-.002079+s[1]*.048952+s[2]*.953127,h=.8+a/10,p=h>=.9?Z(.59,.69,(h-.9)*10):Z(.525,.59,(h-.8)*10),y=i?1:h*(1-1/3.6*Math.exp((-r-42)/92));y=y>1?1:y<0?0:y;let f=h,P=[y*(100/c)+1-y,y*(100/l)+1-y,y*(100/m)+1-y],d=1/(5*r+1),x=d*d*d*d,T=1-x,M=x*r+.1*T*T*Math.cbrt(5*r),C=G(o)/e[1],v=1.48+Math.sqrt(C),b=.725/Math.pow(C,.2),R=b,k=[Math.pow(M*P[0]*c/100,.42),Math.pow(M*P[1]*l/100,.42),Math.pow(M*P[2]*m/100,.42)],F=[400*k[0]/(k[0]+27.13),400*k[1]/(k[1]+27.13),400*k[2]/(k[2]+27.13)],H=(2*F[0]+F[1]+.05*F[2])*b;return new t(C,H,b,R,p,f,P,M,Math.pow(M,.25),v)}constructor(e,r,o,a,i,s,c,l,m,h){this.n=e,this.aw=r,this.nbb=o,this.ncb=a,this.c=i,this.nc=s,this.rgbD=c,this.fl=l,this.fLRoot=m,this.z=h}};N.DEFAULT=N.make();/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var j=class t{constructor(e,r,o,a,i,s,c,l,m){this.hue=e,this.chroma=r,this.j=o,this.q=a,this.m=i,this.s=s,this.jstar=c,this.astar=l,this.bstar=m}distance(e){let r=this.jstar-e.jstar,o=this.astar-e.astar,a=this.bstar-e.bstar,i=Math.sqrt(r*r+o*o+a*a);return 1.41*Math.pow(i,.63)}static fromInt(e){return t.fromIntInViewingConditions(e,N.DEFAULT)}static fromIntInViewingConditions(e,r){let o=(e&16711680)>>16,a=(e&65280)>>8,i=e&255,s=Q(o),c=Q(a),l=Q(i),m=.41233895*s+.35762064*c+.18051042*l,h=.2126*s+.7152*c+.0722*l,p=.01932141*s+.11916382*c+.95034478*l,y=.401288*m+.650173*h-.051461*p,f=-.250268*m+1.204414*h+.045854*p,P=-.002079*m+.048952*h+.953127*p,d=r.rgbD[0]*y,x=r.rgbD[1]*f,T=r.rgbD[2]*P,M=Math.pow(r.fl*Math.abs(d)/100,.42),C=Math.pow(r.fl*Math.abs(x)/100,.42),v=Math.pow(r.fl*Math.abs(T)/100,.42),b=E(d)*400*M/(M+27.13),R=E(x)*400*C/(C+27.13),k=E(T)*400*v/(v+27.13),F=(11*b+-12*R+k)/11,H=(b+R-2*k)/9,w=(20*b+20*R+21*k)/20,W=(40*b+20*R+k)/20,Y=Math.atan2(H,F)*180/Math.PI,U=Y<0?Y+360:Y>=360?Y-360:Y,lt=U*Math.PI/180,ht=W*r.nbb,X=100*Math.pow(ht/r.aw,r.c*r.z),ut=4/r.c*Math.sqrt(X/100)*(r.aw+4)*r.fLRoot,At=U<20.14?U+360:U,kt=.25*(Math.cos(At*Math.PI/180+2)+3.8),It=5e4/13*kt*r.nc*r.ncb*Math.sqrt(F*F+H*H)/(w+.305),mt=Math.pow(It,.9)*Math.pow(1.64-Math.pow(.29,r.n),.73),Bt=mt*Math.sqrt(X/100),St=Bt*r.fLRoot,qt=50*Math.sqrt(mt*r.c/(r.aw+4)),_t=(1+100*.007)*X/(1+.007*X),Rt=1/.0228*Math.log(1+.0228*St),Yt=Rt*Math.cos(lt),jt=Rt*Math.sin(lt);return new t(U,Bt,X,ut,St,qt,_t,Yt,jt)}static fromJch(e,r,o){return t.fromJchInViewingConditions(e,r,o,N.DEFAULT)}static fromJchInViewingConditions(e,r,o,a){let i=4/a.c*Math.sqrt(e/100)*(a.aw+4)*a.fLRoot,s=r*a.fLRoot,c=r/Math.sqrt(e/100),l=50*Math.sqrt(c*a.c/(a.aw+4)),m=o*Math.PI/180,h=(1+100*.007)*e/(1+.007*e),p=1/.0228*Math.log(1+.0228*s),y=p*Math.cos(m),f=p*Math.sin(m);return new t(o,r,e,i,s,l,h,y,f)}static fromUcs(e,r,o){return t.fromUcsInViewingConditions(e,r,o,N.DEFAULT)}static fromUcsInViewingConditions(e,r,o,a){let i=r,s=o,c=Math.sqrt(i*i+s*s),m=(Math.exp(c*.0228)-1)/.0228/a.fLRoot,h=Math.atan2(s,i)*(180/Math.PI);h<0&&(h+=360);let p=e/(1-(e-100)*.007);return t.fromJchInViewingConditions(p,m,h,a)}toInt(){return this.viewed(N.DEFAULT)}viewed(e){let r=this.chroma===0||this.j===0?0:this.chroma/Math.sqrt(this.j/100),o=Math.pow(r/Math.pow(1.64-Math.pow(.29,e.n),.73),1/.9),a=this.hue*Math.PI/180,i=.25*(Math.cos(a+2)+3.8),s=e.aw*Math.pow(this.j/100,1/e.c/e.z),c=i*(5e4/13)*e.nc*e.ncb,l=s/e.nbb,m=Math.sin(a),h=Math.cos(a),p=23*(l+.305)*o/(23*c+11*o*h+108*o*m),y=p*h,f=p*m,P=(460*l+451*y+288*f)/1403,d=(460*l-891*y-261*f)/1403,x=(460*l-220*y-6300*f)/1403,T=Math.max(0,27.13*Math.abs(P)/(400-Math.abs(P))),M=E(P)*(100/e.fl)*Math.pow(T,1/.42),C=Math.max(0,27.13*Math.abs(d)/(400-Math.abs(d))),v=E(d)*(100/e.fl)*Math.pow(C,1/.42),b=Math.max(0,27.13*Math.abs(x)/(400-Math.abs(x))),R=E(x)*(100/e.fl)*Math.pow(b,1/.42),k=M/e.rgbD[0],F=v/e.rgbD[1],H=R/e.rgbD[2],w=1.86206786*k-1.01125463*F+.14918677*H,W=.38752654*k+.62144744*F-.00897398*H,J=-.0158415*k-.03412294*F+1.04996444*H;return Lt(w,W,J)}static fromXyzInViewingConditions(e,r,o,a){let i=.401288*e+.650173*r-.051461*o,s=-.250268*e+1.204414*r+.045854*o,c=-.002079*e+.048952*r+.953127*o,l=a.rgbD[0]*i,m=a.rgbD[1]*s,h=a.rgbD[2]*c,p=Math.pow(a.fl*Math.abs(l)/100,.42),y=Math.pow(a.fl*Math.abs(m)/100,.42),f=Math.pow(a.fl*Math.abs(h)/100,.42),P=E(l)*400*p/(p+27.13),d=E(m)*400*y/(y+27.13),x=E(h)*400*f/(f+27.13),T=(11*P+-12*d+x)/11,M=(P+d-2*x)/9,C=(20*P+20*d+21*x)/20,v=(40*P+20*d+x)/20,R=Math.atan2(M,T)*180/Math.PI,k=R<0?R+360:R>=360?R-360:R,F=k*Math.PI/180,H=v*a.nbb,w=100*Math.pow(H/a.aw,a.c*a.z),W=4/a.c*Math.sqrt(w/100)*(a.aw+4)*a.fLRoot,J=k<20.14?k+360:k,Y=1/4*(Math.cos(J*Math.PI/180+2)+3.8),lt=5e4/13*Y*a.nc*a.ncb*Math.sqrt(T*T+M*M)/(C+.305),ht=Math.pow(lt,.9)*Math.pow(1.64-Math.pow(.29,a.n),.73),X=ht*Math.sqrt(w/100),ut=X*a.fLRoot,At=50*Math.sqrt(ht*a.c/(a.aw+4)),kt=(1+100*.007)*w/(1+.007*w),Mt=Math.log(1+.0228*ut)/.0228,It=Mt*Math.cos(F),mt=Mt*Math.sin(F);return new t(k,X,w,W,ut,At,kt,It,mt)}xyzInViewingConditions(e){let r=this.chroma===0||this.j===0?0:this.chroma/Math.sqrt(this.j/100),o=Math.pow(r/Math.pow(1.64-Math.pow(.29,e.n),.73),1/.9),a=this.hue*Math.PI/180,i=.25*(Math.cos(a+2)+3.8),s=e.aw*Math.pow(this.j/100,1/e.c/e.z),c=i*(5e4/13)*e.nc*e.ncb,l=s/e.nbb,m=Math.sin(a),h=Math.cos(a),p=23*(l+.305)*o/(23*c+11*o*h+108*o*m),y=p*h,f=p*m,P=(460*l+451*y+288*f)/1403,d=(460*l-891*y-261*f)/1403,x=(460*l-220*y-6300*f)/1403,T=Math.max(0,27.13*Math.abs(P)/(400-Math.abs(P))),M=E(P)*(100/e.fl)*Math.pow(T,1/.42),C=Math.max(0,27.13*Math.abs(d)/(400-Math.abs(d))),v=E(d)*(100/e.fl)*Math.pow(C,1/.42),b=Math.max(0,27.13*Math.abs(x)/(400-Math.abs(x))),R=E(x)*(100/e.fl)*Math.pow(b,1/.42),k=M/e.rgbD[0],F=v/e.rgbD[1],H=R/e.rgbD[2],w=1.86206786*k-1.01125463*F+.14918677*H,W=.38752654*k+.62144744*F-.00897398*H,J=-.0158415*k-.03412294*F+1.04996444*H;return[w,W,J]}};/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var _=class t{static sanitizeRadians(e){return(e+Math.PI*8)%(Math.PI*2)}static trueDelinearized(e){let r=e/100,o=0;return r<=.0031308?o=r*12.92:o=1.055*Math.pow(r,1/2.4)-.055,o*255}static chromaticAdaptation(e){let r=Math.pow(Math.abs(e),.42);return E(e)*400*r/(r+27.13)}static hueOf(e){let r=at(e,t.SCALED_DISCOUNT_FROM_LINRGB),o=t.chromaticAdaptation(r[0]),a=t.chromaticAdaptation(r[1]),i=t.chromaticAdaptation(r[2]),s=(11*o+-12*a+i)/11,c=(o+a-2*i)/9;return Math.atan2(c,s)}static areInCyclicOrder(e,r,o){let a=t.sanitizeRadians(r-e),i=t.sanitizeRadians(o-e);return a<i}static intercept(e,r,o){return(r-e)/(o-e)}static lerpPoint(e,r,o){return[e[0]+(o[0]-e[0])*r,e[1]+(o[1]-e[1])*r,e[2]+(o[2]-e[2])*r]}static setCoordinate(e,r,o,a){let i=t.intercept(e[a],r,o[a]);return t.lerpPoint(e,i,o)}static isBounded(e){return 0<=e&&e<=100}static nthVertex(e,r){let o=t.Y_FROM_LINRGB[0],a=t.Y_FROM_LINRGB[1],i=t.Y_FROM_LINRGB[2],s=r%4<=1?0:100,c=r%2===0?0:100;if(r<4){let l=s,m=c,h=(e-l*a-m*i)/o;return t.isBounded(h)?[h,l,m]:[-1,-1,-1]}else if(r<8){let l=s,m=c,h=(e-m*o-l*i)/a;return t.isBounded(h)?[m,h,l]:[-1,-1,-1]}else{let l=s,m=c,h=(e-l*o-m*a)/i;return t.isBounded(h)?[l,m,h]:[-1,-1,-1]}}static bisectToSegment(e,r){let o=[-1,-1,-1],a=o,i=0,s=0,c=!1,l=!0;for(let m=0;m<12;m++){let h=t.nthVertex(e,m);if(h[0]<0)continue;let p=t.hueOf(h);if(!c){o=h,a=h,i=p,s=p,c=!0;continue}(l||t.areInCyclicOrder(i,p,s))&&(l=!1,t.areInCyclicOrder(i,r,p)?(a=h,s=p):(o=h,i=p))}return[o,a]}static midpoint(e,r){return[(e[0]+r[0])/2,(e[1]+r[1])/2,(e[2]+r[2])/2]}static criticalPlaneBelow(e){return Math.floor(e-.5)}static criticalPlaneAbove(e){return Math.ceil(e-.5)}static bisectToLimit(e,r){let o=t.bisectToSegment(e,r),a=o[0],i=t.hueOf(a),s=o[1];for(let c=0;c<3;c++)if(a[c]!==s[c]){let l=-1,m=255;a[c]<s[c]?(l=t.criticalPlaneBelow(t.trueDelinearized(a[c])),m=t.criticalPlaneAbove(t.trueDelinearized(s[c]))):(l=t.criticalPlaneAbove(t.trueDelinearized(a[c])),m=t.criticalPlaneBelow(t.trueDelinearized(s[c])));for(let h=0;h<8&&!(Math.abs(m-l)<=1);h++){let p=Math.floor((l+m)/2),y=t.CRITICAL_PLANES[p],f=t.setCoordinate(a,y,s,c),P=t.hueOf(f);t.areInCyclicOrder(i,r,P)?(s=f,m=p):(a=f,i=P,l=p)}}return t.midpoint(a,s)}static inverseChromaticAdaptation(e){let r=Math.abs(e),o=Math.max(0,27.13*r/(400-r));return E(e)*Math.pow(o,1/.42)}static findResultByJ(e,r,o){let a=Math.sqrt(o)*11,i=N.DEFAULT,s=1/Math.pow(1.64-Math.pow(.29,i.n),.73),l=.25*(Math.cos(e+2)+3.8)*(5e4/13)*i.nc*i.ncb,m=Math.sin(e),h=Math.cos(e);for(let p=0;p<5;p++){let y=a/100,f=r===0||a===0?0:r/Math.sqrt(y),P=Math.pow(f*s,1/.9),x=i.aw*Math.pow(y,1/i.c/i.z)/i.nbb,T=23*(x+.305)*P/(23*l+11*P*h+108*P*m),M=T*h,C=T*m,v=(460*x+451*M+288*C)/1403,b=(460*x-891*M-261*C)/1403,R=(460*x-220*M-6300*C)/1403,k=t.inverseChromaticAdaptation(v),F=t.inverseChromaticAdaptation(b),H=t.inverseChromaticAdaptation(R),w=at([k,F,H],t.LINRGB_FROM_SCALED_DISCOUNT);if(w[0]<0||w[1]<0||w[2]<0)return 0;let W=t.Y_FROM_LINRGB[0],J=t.Y_FROM_LINRGB[1],Y=t.Y_FROM_LINRGB[2],U=W*w[0]+J*w[1]+Y*w[2];if(U<=0)return 0;if(p===4||Math.abs(U-o)<.002)return w[0]>100.01||w[1]>100.01||w[2]>100.01?0:Tt(w);a=a-(U-o)*a/(2*U)}return 0}static solveToInt(e,r,o){if(r<1e-4||o<1e-4||o>99.9999)return Vt(o);e=z(e);let a=e/180*Math.PI,i=G(o),s=t.findResultByJ(a,r,i);if(s!==0)return s;let c=t.bisectToLimit(i,a);return Tt(c)}static solveToCam(e,r,o){return j.fromInt(t.solveToInt(e,r,o))}};_.SCALED_DISCOUNT_FROM_LINRGB=[[.001200833568784504,.002389694492170889,.0002795742885861124],[.0005891086651375999,.0029785502573438758,.0003270666104008398],[.00010146692491640572,.0005364214359186694,.0032979401770712076]];_.LINRGB_FROM_SCALED_DISCOUNT=[[1373.2198709594231,-1100.4251190754821,-7.278681089101213],[-271.815969077903,559.6580465940733,-32.46047482791194],[1.9622899599665666,-57.173814538844006,308.7233197812385]];_.Y_FROM_LINRGB=[.2126,.7152,.0722];_.CRITICAL_PLANES=[.015176349177441876,.045529047532325624,.07588174588720938,.10623444424209313,.13658714259697685,.16693984095186062,.19729253930674434,.2276452376616281,.2579979360165119,.28835063437139563,.3188300904430532,.350925934958123,.3848314933096426,.42057480301049466,.458183274052838,.4976837250274023,.5391024159806381,.5824650784040898,.6277969426914107,.6751227633498623,.7244668422128921,.775853049866786,.829304845476233,.8848452951698498,.942497089126609,1.0022825574869039,1.0642236851973577,1.1283421258858297,1.1946592148522128,1.2631959812511864,1.3339731595349034,1.407011200216447,1.4823302800086415,1.5599503113873272,1.6398909516233677,1.7221716113234105,1.8068114625156377,1.8938294463134073,1.9832442801866852,2.075074464868551,2.1693382909216234,2.2660538449872063,2.36523901573795,2.4669114995532007,2.5710888059345764,2.6777882626779785,2.7870270208169257,2.898822059350997,3.0131901897720907,3.1301480604002863,3.2497121605402226,3.3718988244681087,3.4967242352587946,3.624204428461639,3.754355295633311,3.887192587735158,4.022731918402185,4.160988767090289,4.301978482107941,4.445716283538092,4.592217266055746,4.741496401646282,4.893568542229298,5.048448422192488,5.20615066083972,5.3666897647573375,5.5300801301023865,5.696336044816294,5.865471690767354,6.037501145825082,6.212438385869475,6.390297286737924,6.571091626112461,6.7548350853498045,6.941541251256611,7.131223617812143,7.323895587840543,7.5195704746346665,7.7182615035334345,7.919981813454504,8.124744458384042,8.332562408825165,8.543448553206703,8.757415699253682,8.974476575321063,9.194643831691977,9.417930041841839,9.644347703669503,9.873909240696694,10.106627003236781,10.342513269534024,10.58158024687427,10.8238400726681,11.069304815507364,11.317986476196008,11.569896988756009,11.825048221409341,12.083451977536606,12.345119996613247,12.610063955123938,12.878295467455942,13.149826086772048,13.42466730586372,13.702830557985108,13.984327217668513,14.269168601521828,14.55736596900856,14.848930523210871,15.143873411576273,15.44220572664832,15.743938506781891,16.04908273684337,16.35764934889634,16.66964922287304,16.985093187232053,17.30399201960269,17.62635644741625,17.95219714852476,18.281524751807332,18.614349837764564,18.95068293910138,19.290534541298456,19.633915083172692,19.98083495742689,20.331304511189067,20.685334046541502,21.042933821039977,21.404114048223256,21.76888489811322,22.137256497705877,22.50923893145328,22.884842241736916,23.264076429332462,23.6469514538663,24.033477234264016,24.42366364919083,24.817520537484558,25.21505769858089,25.61628489293138,26.021211842414342,26.429848230738664,26.842203703840827,27.258287870275353,27.678110301598522,28.10168053274597,28.529008062403893,28.96010235337422,29.39497283293396,29.83362889318845,30.276079891419332,30.722335150426627,31.172403958865512,31.62629557157785,32.08401920991837,32.54558406207592,33.010999283389665,33.4802739966603,33.953417292456834,34.430438229418264,34.911345834551085,35.39614910352207,35.88485700094671,36.37747846067349,36.87402238606382,37.37449765026789,37.87891309649659,38.38727753828926,38.89959975977785,39.41588851594697,39.93615253289054,40.460400508064545,40.98864111053629,41.520882981230194,42.05713473317016,42.597404951718396,43.141702194811224,43.6900349931913,44.24241185063697,44.798841244188324,45.35933162437017,45.92389141541209,46.49252901546552,47.065252796817916,47.64207110610409,48.22299226451468,48.808024568002054,49.3971762874833,49.9904556690408,50.587870934119984,51.189430279724725,51.79514187861014,52.40501387947288,53.0190544071392,53.637271562750364,54.259673423945976,54.88626804504493,55.517063457223934,56.15206766869424,56.79128866487574,57.43473440856916,58.08241284012621,58.734331877617365,59.39049941699807,60.05092333227251,60.715611475655585,61.38457167773311,62.057811747619894,62.7353394731159,63.417162620860914,64.10328893648692,64.79372614476921,65.48848194977529,66.18756403501224,66.89098006357258,67.59873767827808,68.31084450182222,69.02730813691093,69.74813616640164,70.47333615344107,71.20291564160104,71.93688215501312,72.67524319850172,73.41800625771542,74.16517879925733,74.9167682708136,75.67278210128072,76.43322770089146,77.1981124613393,77.96744375590167,78.74122893956174,79.51947534912904,80.30219030335869,81.08938110306934,81.88105503125999,82.67721935322541,83.4778813166706,84.28304815182372,85.09272707154808,85.90692527145302,86.72564993000343,87.54890820862819,88.3767072518277,89.2090541872801,90.04595612594655,90.88742016217518,91.73345337380438,92.58406282226491,93.43925555268066,94.29903859396902,95.16341895893969,96.03240364439274,96.9059996312159,97.78421388448044,98.6670533535366,99.55452497210776];/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var I=class t{static from(e,r,o){return new t(_.solveToInt(e,r,o))}static fromInt(e){return new t(e)}toInt(){return this.argb}get hue(){return this.internalHue}set hue(e){this.setInternalState(_.solveToInt(e,this.internalChroma,this.internalTone))}get chroma(){return this.internalChroma}set chroma(e){this.setInternalState(_.solveToInt(this.internalHue,e,this.internalTone))}get tone(){return this.internalTone}set tone(e){this.setInternalState(_.solveToInt(this.internalHue,this.internalChroma,e))}constructor(e){this.argb=e;let r=j.fromInt(e);this.internalHue=r.hue,this.internalChroma=r.chroma,this.internalTone=xt(e),this.argb=e}setInternalState(e){let r=j.fromInt(e);this.internalHue=r.hue,this.internalChroma=r.chroma,this.internalTone=xt(e),this.argb=e}inViewingConditions(e){let o=j.fromInt(this.toInt()).xyzInViewingConditions(e),a=j.fromXyzInViewingConditions(o[0],o[1],o[2],N.make());return t.from(a.hue,a.chroma,st(o[1]))}};/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var V=class t{static ratioOfTones(e,r){return e=et(0,100,e),r=et(0,100,r),t.ratioOfYs(G(e),G(r))}static ratioOfYs(e,r){let o=e>r?e:r,a=o===r?e:r;return(o+5)/(a+5)}static lighter(e,r){if(e<0||e>100)return-1;let o=G(e),a=r*(o+5)-5,i=t.ratioOfYs(a,o),s=Math.abs(i-r);if(i<r&&s>.04)return-1;let c=st(a)+.4;return c<0||c>100?-1:c}static darker(e,r){if(e<0||e>100)return-1;let o=G(e),a=(o+5)/r-5,i=t.ratioOfYs(o,a),s=Math.abs(i-r);if(i<r&&s>.04)return-1;let c=st(a)-.4;return c<0||c>100?-1:c}static lighterUnsafe(e,r){let o=t.lighter(e,r);return o<0?100:o}static darkerUnsafe(e,r){let o=t.darker(e,r);return o<0?0:o}};/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var rt=class t{static isDisliked(e){let r=Math.round(e.hue)>=90&&Math.round(e.hue)<=111,o=Math.round(e.chroma)>16,a=Math.round(e.tone)<65;return r&&o&&a}static fixIfDisliked(e){return t.isDisliked(e)?I.from(e.hue,e.chroma,70):e}};/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var u=class t{static fromPalette(e){var r,o;return new t((r=e.name)!=null?r:"",e.palette,e.tone,(o=e.isBackground)!=null?o:!1,e.background,e.secondBackground,e.contrastCurve,e.toneDeltaPair)}constructor(e,r,o,a,i,s,c,l){if(this.name=e,this.palette=r,this.tone=o,this.isBackground=a,this.background=i,this.secondBackground=s,this.contrastCurve=c,this.toneDeltaPair=l,this.hctCache=new Map,!i&&s)throw new Error(`Color ${e} has secondBackgrounddefined, but background is not defined.`);if(!i&&c)throw new Error(`Color ${e} has contrastCurvedefined, but background is not defined.`);if(i&&!c)throw new Error(`Color ${e} has backgrounddefined, but contrastCurve is not defined.`)}getArgb(e){return this.getHct(e).toInt()}getHct(e){let r=this.hctCache.get(e);if(r!=null)return r;let o=this.getTone(e),a=this.palette(e).getHct(o);return this.hctCache.size>4&&this.hctCache.clear(),this.hctCache.set(e,a),a}getTone(e){let r=e.contrastLevel<0;if(this.toneDeltaPair){let o=this.toneDeltaPair(e),a=o.roleA,i=o.roleB,s=o.delta,c=o.polarity,l=o.stayTogether,h=this.background(e).getTone(e),p=c==="nearer"||c==="lighter"&&!e.isDark||c==="darker"&&e.isDark,y=p?a:i,f=p?i:a,P=this.name===y.name,d=e.isDark?1:-1,x=y.contrastCurve.get(e.contrastLevel),T=f.contrastCurve.get(e.contrastLevel),M=y.tone(e),C=V.ratioOfTones(h,M)>=x?M:t.foregroundTone(h,x),v=f.tone(e),b=V.ratioOfTones(h,v)>=T?v:t.foregroundTone(h,T);return r&&(C=t.foregroundTone(h,x),b=t.foregroundTone(h,T)),(b-C)*d>=s||(b=et(0,100,C+s*d),(b-C)*d>=s||(C=et(0,100,b-s*d))),50<=C&&C<60?d>0?(C=60,b=Math.max(b,C+s*d)):(C=49,b=Math.min(b,C+s*d)):50<=b&&b<60&&(l?d>0?(C=60,b=Math.max(b,C+s*d)):(C=49,b=Math.min(b,C+s*d)):d>0?b=60:b=49),P?C:b}else{let o=this.tone(e);if(this.background==null)return o;let a=this.background(e).getTone(e),i=this.contrastCurve.get(e.contrastLevel);if(V.ratioOfTones(a,o)>=i||(o=t.foregroundTone(a,i)),r&&(o=t.foregroundTone(a,i)),this.isBackground&&50<=o&&o<60&&(V.ratioOfTones(49,a)>=i?o=49:o=60),this.secondBackground){let[s,c]=[this.background,this.secondBackground],[l,m]=[s(e).getTone(e),c(e).getTone(e)],[h,p]=[Math.max(l,m),Math.min(l,m)];if(V.ratioOfTones(h,o)>=i&&V.ratioOfTones(p,o)>=i)return o;let y=V.lighter(h,i),f=V.darker(p,i),P=[];return y!==-1&&P.push(y),f!==-1&&P.push(f),t.tonePrefersLightForeground(l)||t.tonePrefersLightForeground(m)?y<0?100:y:P.length===1?P[0]:f<0?0:f}return o}}static foregroundTone(e,r){let o=V.lighterUnsafe(e,r),a=V.darkerUnsafe(e,r),i=V.ratioOfTones(o,e),s=V.ratioOfTones(a,e);if(t.tonePrefersLightForeground(e)){let l=Math.abs(i-s)<.1&&i<r&&s<r;return i>=r||i>=s||l?o:a}else return s>=r||s>=i?a:o}static tonePrefersLightForeground(e){return Math.round(e)<60}static toneAllowsLightForeground(e){return Math.round(e)<=49}static enableLightForeground(e){return t.tonePrefersLightForeground(e)&&!t.toneAllowsLightForeground(e)?49:e}};/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var A=class t{static fromInt(e){let r=I.fromInt(e);return t.fromHct(r)}static fromHct(e){return new t(e.hue,e.chroma,e)}static fromHueAndChroma(e,r){let o=new wt(e,r).create();return new t(e,r,o)}constructor(e,r,o){this.hue=e,this.chroma=r,this.keyColor=o,this.cache=new Map}tone(e){let r=this.cache.get(e);return r===void 0&&(r=I.from(this.hue,this.chroma,e).toInt(),this.cache.set(e,r)),r}getHct(e){return I.fromInt(this.tone(e))}},wt=class{constructor(e,r){this.hue=e,this.requestedChroma=r,this.chromaCache=new Map,this.maxChromaValue=200}create(){let a=0,i=100;for(;a<i;){let s=Math.floor((a+i)/2),c=this.maxChroma(s)<this.maxChroma(s+1);if(this.maxChroma(s)>=this.requestedChroma-.01)if(Math.abs(a-50)<Math.abs(i-50))i=s;else{if(a===s)return I.from(this.hue,this.requestedChroma,a);a=s}else c?a=s+1:i=s}return I.from(this.hue,this.requestedChroma,a)}maxChroma(e){if(this.chromaCache.has(e))return this.chromaCache.get(e);let r=I.from(this.hue,this.maxChromaValue,e).chroma;return this.chromaCache.set(e,r),r}};/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var g=class{constructor(e,r,o,a){this.low=e,this.normal=r,this.medium=o,this.high=a}get(e){return e<=-1?this.low:e<0?Z(this.low,this.normal,(e- -1)/1):e<.5?Z(this.normal,this.medium,(e-0)/.5):e<1?Z(this.medium,this.high,(e-.5)/.5):this.high}};/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var O=class{constructor(e,r,o,a,i){this.roleA=e,this.roleB=r,this.delta=o,this.polarity=a,this.stayTogether=i}};/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var B;(function(t){t[t.MONOCHROME=0]="MONOCHROME",t[t.NEUTRAL=1]="NEUTRAL",t[t.TONAL_SPOT=2]="TONAL_SPOT",t[t.VIBRANT=3]="VIBRANT",t[t.EXPRESSIVE=4]="EXPRESSIVE",t[t.FIDELITY=5]="FIDELITY",t[t.CONTENT=6]="CONTENT",t[t.RAINBOW=7]="RAINBOW",t[t.FRUIT_SALAD=8]="FRUIT_SALAD"})(B||(B={}));/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function nt(t){return t.variant===B.FIDELITY||t.variant===B.CONTENT}function D(t){return t.variant===B.MONOCHROME}function oe(t,e,r,o){let a=r,i=I.from(t,e,r);if(i.chroma<e){let s=i.chroma;for(;i.chroma<e;){a+=o?-1:1;let c=I.from(t,e,a);if(s>c.chroma||Math.abs(c.chroma-e)<.4)break;let l=Math.abs(c.chroma-e),m=Math.abs(i.chroma-e);l<m&&(i=c),s=Math.max(s,c.chroma)}}return a}var n=class t{static highestSurface(e){return e.isDark?t.surfaceBright:t.surfaceDim}};n.contentAccentToneDelta=15;n.primaryPaletteKeyColor=u.fromPalette({name:"primary_palette_key_color",palette:t=>t.primaryPalette,tone:t=>t.primaryPalette.keyColor.tone});n.secondaryPaletteKeyColor=u.fromPalette({name:"secondary_palette_key_color",palette:t=>t.secondaryPalette,tone:t=>t.secondaryPalette.keyColor.tone});n.tertiaryPaletteKeyColor=u.fromPalette({name:"tertiary_palette_key_color",palette:t=>t.tertiaryPalette,tone:t=>t.tertiaryPalette.keyColor.tone});n.neutralPaletteKeyColor=u.fromPalette({name:"neutral_palette_key_color",palette:t=>t.neutralPalette,tone:t=>t.neutralPalette.keyColor.tone});n.neutralVariantPaletteKeyColor=u.fromPalette({name:"neutral_variant_palette_key_color",palette:t=>t.neutralVariantPalette,tone:t=>t.neutralVariantPalette.keyColor.tone});n.background=u.fromPalette({name:"background",palette:t=>t.neutralPalette,tone:t=>t.isDark?6:98,isBackground:!0});n.onBackground=u.fromPalette({name:"on_background",palette:t=>t.neutralPalette,tone:t=>t.isDark?90:10,background:t=>n.background,contrastCurve:new g(3,3,4.5,7)});n.surface=u.fromPalette({name:"surface",palette:t=>t.neutralPalette,tone:t=>t.isDark?6:98,isBackground:!0});n.surfaceDim=u.fromPalette({name:"surface_dim",palette:t=>t.neutralPalette,tone:t=>t.isDark?6:new g(87,87,80,75).get(t.contrastLevel),isBackground:!0});n.surfaceBright=u.fromPalette({name:"surface_bright",palette:t=>t.neutralPalette,tone:t=>t.isDark?new g(24,24,29,34).get(t.contrastLevel):98,isBackground:!0});n.surfaceContainerLowest=u.fromPalette({name:"surface_container_lowest",palette:t=>t.neutralPalette,tone:t=>t.isDark?new g(4,4,2,0).get(t.contrastLevel):100,isBackground:!0});n.surfaceContainerLow=u.fromPalette({name:"surface_container_low",palette:t=>t.neutralPalette,tone:t=>t.isDark?new g(10,10,11,12).get(t.contrastLevel):new g(96,96,96,95).get(t.contrastLevel),isBackground:!0});n.surfaceContainer=u.fromPalette({name:"surface_container",palette:t=>t.neutralPalette,tone:t=>t.isDark?new g(12,12,16,20).get(t.contrastLevel):new g(94,94,92,90).get(t.contrastLevel),isBackground:!0});n.surfaceContainerHigh=u.fromPalette({name:"surface_container_high",palette:t=>t.neutralPalette,tone:t=>t.isDark?new g(17,17,21,25).get(t.contrastLevel):new g(92,92,88,85).get(t.contrastLevel),isBackground:!0});n.surfaceContainerHighest=u.fromPalette({name:"surface_container_highest",palette:t=>t.neutralPalette,tone:t=>t.isDark?new g(22,22,26,30).get(t.contrastLevel):new g(90,90,84,80).get(t.contrastLevel),isBackground:!0});n.onSurface=u.fromPalette({name:"on_surface",palette:t=>t.neutralPalette,tone:t=>t.isDark?90:10,background:t=>n.highestSurface(t),contrastCurve:new g(4.5,7,11,21)});n.surfaceVariant=u.fromPalette({name:"surface_variant",palette:t=>t.neutralVariantPalette,tone:t=>t.isDark?30:90,isBackground:!0});n.onSurfaceVariant=u.fromPalette({name:"on_surface_variant",palette:t=>t.neutralVariantPalette,tone:t=>t.isDark?80:30,background:t=>n.highestSurface(t),contrastCurve:new g(3,4.5,7,11)});n.inverseSurface=u.fromPalette({name:"inverse_surface",palette:t=>t.neutralPalette,tone:t=>t.isDark?90:20});n.inverseOnSurface=u.fromPalette({name:"inverse_on_surface",palette:t=>t.neutralPalette,tone:t=>t.isDark?20:95,background:t=>n.inverseSurface,contrastCurve:new g(4.5,7,11,21)});n.outline=u.fromPalette({name:"outline",palette:t=>t.neutralVariantPalette,tone:t=>t.isDark?60:50,background:t=>n.highestSurface(t),contrastCurve:new g(1.5,3,4.5,7)});n.outlineVariant=u.fromPalette({name:"outline_variant",palette:t=>t.neutralVariantPalette,tone:t=>t.isDark?30:80,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5)});n.shadow=u.fromPalette({name:"shadow",palette:t=>t.neutralPalette,tone:t=>0});n.scrim=u.fromPalette({name:"scrim",palette:t=>t.neutralPalette,tone:t=>0});n.surfaceTint=u.fromPalette({name:"surface_tint",palette:t=>t.primaryPalette,tone:t=>t.isDark?80:40,isBackground:!0});n.primary=u.fromPalette({name:"primary",palette:t=>t.primaryPalette,tone:t=>D(t)?t.isDark?100:0:t.isDark?80:40,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(3,4.5,7,7),toneDeltaPair:t=>new O(n.primaryContainer,n.primary,10,"nearer",!1)});n.onPrimary=u.fromPalette({name:"on_primary",palette:t=>t.primaryPalette,tone:t=>D(t)?t.isDark?10:90:t.isDark?20:100,background:t=>n.primary,contrastCurve:new g(4.5,7,11,21)});n.primaryContainer=u.fromPalette({name:"primary_container",palette:t=>t.primaryPalette,tone:t=>nt(t)?t.sourceColorHct.tone:D(t)?t.isDark?85:25:t.isDark?30:90,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.primaryContainer,n.primary,10,"nearer",!1)});n.onPrimaryContainer=u.fromPalette({name:"on_primary_container",palette:t=>t.primaryPalette,tone:t=>nt(t)?u.foregroundTone(n.primaryContainer.tone(t),4.5):D(t)?t.isDark?0:100:t.isDark?90:30,background:t=>n.primaryContainer,contrastCurve:new g(3,4.5,7,11)});n.inversePrimary=u.fromPalette({name:"inverse_primary",palette:t=>t.primaryPalette,tone:t=>t.isDark?40:80,background:t=>n.inverseSurface,contrastCurve:new g(3,4.5,7,7)});n.secondary=u.fromPalette({name:"secondary",palette:t=>t.secondaryPalette,tone:t=>t.isDark?80:40,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(3,4.5,7,7),toneDeltaPair:t=>new O(n.secondaryContainer,n.secondary,10,"nearer",!1)});n.onSecondary=u.fromPalette({name:"on_secondary",palette:t=>t.secondaryPalette,tone:t=>D(t)?t.isDark?10:100:t.isDark?20:100,background:t=>n.secondary,contrastCurve:new g(4.5,7,11,21)});n.secondaryContainer=u.fromPalette({name:"secondary_container",palette:t=>t.secondaryPalette,tone:t=>{let e=t.isDark?30:90;return D(t)?t.isDark?30:85:nt(t)?oe(t.secondaryPalette.hue,t.secondaryPalette.chroma,e,!t.isDark):e},isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.secondaryContainer,n.secondary,10,"nearer",!1)});n.onSecondaryContainer=u.fromPalette({name:"on_secondary_container",palette:t=>t.secondaryPalette,tone:t=>D(t)?t.isDark?90:10:nt(t)?u.foregroundTone(n.secondaryContainer.tone(t),4.5):t.isDark?90:30,background:t=>n.secondaryContainer,contrastCurve:new g(3,4.5,7,11)});n.tertiary=u.fromPalette({name:"tertiary",palette:t=>t.tertiaryPalette,tone:t=>D(t)?t.isDark?90:25:t.isDark?80:40,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(3,4.5,7,7),toneDeltaPair:t=>new O(n.tertiaryContainer,n.tertiary,10,"nearer",!1)});n.onTertiary=u.fromPalette({name:"on_tertiary",palette:t=>t.tertiaryPalette,tone:t=>D(t)?t.isDark?10:90:t.isDark?20:100,background:t=>n.tertiary,contrastCurve:new g(4.5,7,11,21)});n.tertiaryContainer=u.fromPalette({name:"tertiary_container",palette:t=>t.tertiaryPalette,tone:t=>{if(D(t))return t.isDark?60:49;if(!nt(t))return t.isDark?30:90;let e=t.tertiaryPalette.getHct(t.sourceColorHct.tone);return rt.fixIfDisliked(e).tone},isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.tertiaryContainer,n.tertiary,10,"nearer",!1)});n.onTertiaryContainer=u.fromPalette({name:"on_tertiary_container",palette:t=>t.tertiaryPalette,tone:t=>D(t)?t.isDark?0:100:nt(t)?u.foregroundTone(n.tertiaryContainer.tone(t),4.5):t.isDark?90:30,background:t=>n.tertiaryContainer,contrastCurve:new g(3,4.5,7,11)});n.error=u.fromPalette({name:"error",palette:t=>t.errorPalette,tone:t=>t.isDark?80:40,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(3,4.5,7,7),toneDeltaPair:t=>new O(n.errorContainer,n.error,10,"nearer",!1)});n.onError=u.fromPalette({name:"on_error",palette:t=>t.errorPalette,tone:t=>t.isDark?20:100,background:t=>n.error,contrastCurve:new g(4.5,7,11,21)});n.errorContainer=u.fromPalette({name:"error_container",palette:t=>t.errorPalette,tone:t=>t.isDark?30:90,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.errorContainer,n.error,10,"nearer",!1)});n.onErrorContainer=u.fromPalette({name:"on_error_container",palette:t=>t.errorPalette,tone:t=>D(t)?t.isDark?90:10:t.isDark?90:30,background:t=>n.errorContainer,contrastCurve:new g(3,4.5,7,11)});n.primaryFixed=u.fromPalette({name:"primary_fixed",palette:t=>t.primaryPalette,tone:t=>D(t)?40:90,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.primaryFixed,n.primaryFixedDim,10,"lighter",!0)});n.primaryFixedDim=u.fromPalette({name:"primary_fixed_dim",palette:t=>t.primaryPalette,tone:t=>D(t)?30:80,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.primaryFixed,n.primaryFixedDim,10,"lighter",!0)});n.onPrimaryFixed=u.fromPalette({name:"on_primary_fixed",palette:t=>t.primaryPalette,tone:t=>D(t)?100:10,background:t=>n.primaryFixedDim,secondBackground:t=>n.primaryFixed,contrastCurve:new g(4.5,7,11,21)});n.onPrimaryFixedVariant=u.fromPalette({name:"on_primary_fixed_variant",palette:t=>t.primaryPalette,tone:t=>D(t)?90:30,background:t=>n.primaryFixedDim,secondBackground:t=>n.primaryFixed,contrastCurve:new g(3,4.5,7,11)});n.secondaryFixed=u.fromPalette({name:"secondary_fixed",palette:t=>t.secondaryPalette,tone:t=>D(t)?80:90,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.secondaryFixed,n.secondaryFixedDim,10,"lighter",!0)});n.secondaryFixedDim=u.fromPalette({name:"secondary_fixed_dim",palette:t=>t.secondaryPalette,tone:t=>D(t)?70:80,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.secondaryFixed,n.secondaryFixedDim,10,"lighter",!0)});n.onSecondaryFixed=u.fromPalette({name:"on_secondary_fixed",palette:t=>t.secondaryPalette,tone:t=>10,background:t=>n.secondaryFixedDim,secondBackground:t=>n.secondaryFixed,contrastCurve:new g(4.5,7,11,21)});n.onSecondaryFixedVariant=u.fromPalette({name:"on_secondary_fixed_variant",palette:t=>t.secondaryPalette,tone:t=>D(t)?25:30,background:t=>n.secondaryFixedDim,secondBackground:t=>n.secondaryFixed,contrastCurve:new g(3,4.5,7,11)});n.tertiaryFixed=u.fromPalette({name:"tertiary_fixed",palette:t=>t.tertiaryPalette,tone:t=>D(t)?40:90,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.tertiaryFixed,n.tertiaryFixedDim,10,"lighter",!0)});n.tertiaryFixedDim=u.fromPalette({name:"tertiary_fixed_dim",palette:t=>t.tertiaryPalette,tone:t=>D(t)?30:80,isBackground:!0,background:t=>n.highestSurface(t),contrastCurve:new g(1,1,3,4.5),toneDeltaPair:t=>new O(n.tertiaryFixed,n.tertiaryFixedDim,10,"lighter",!0)});n.onTertiaryFixed=u.fromPalette({name:"on_tertiary_fixed",palette:t=>t.tertiaryPalette,tone:t=>D(t)?100:10,background:t=>n.tertiaryFixedDim,secondBackground:t=>n.tertiaryFixed,contrastCurve:new g(4.5,7,11,21)});n.onTertiaryFixedVariant=u.fromPalette({name:"on_tertiary_fixed_variant",palette:t=>t.tertiaryPalette,tone:t=>D(t)?90:30,background:t=>n.tertiaryFixedDim,secondBackground:t=>n.tertiaryFixed,contrastCurve:new g(3,4.5,7,11)});/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var S=class{constructor(e){this.sourceColorArgb=e.sourceColorArgb,this.variant=e.variant,this.contrastLevel=e.contrastLevel,this.isDark=e.isDark,this.sourceColorHct=I.fromInt(e.sourceColorArgb),this.primaryPalette=e.primaryPalette,this.secondaryPalette=e.secondaryPalette,this.tertiaryPalette=e.tertiaryPalette,this.neutralPalette=e.neutralPalette,this.neutralVariantPalette=e.neutralVariantPalette,this.errorPalette=A.fromHueAndChroma(25,84)}static getRotatedHue(e,r,o){let a=e.hue;if(r.length!==o.length)throw new Error(`mismatch between hue length ${r.length} & rotations ${o.length}`);if(o.length===1)return z(e.hue+o[0]);let i=r.length;for(let s=0;s<=i-2;s++){let c=r[s],l=r[s+1];if(c<a&&a<l)return z(a+o[s])}return a}getArgb(e){return e.getArgb(this)}getHct(e){return e.getHct(this)}get primaryPaletteKeyColor(){return this.getArgb(n.primaryPaletteKeyColor)}get secondaryPaletteKeyColor(){return this.getArgb(n.secondaryPaletteKeyColor)}get tertiaryPaletteKeyColor(){return this.getArgb(n.tertiaryPaletteKeyColor)}get neutralPaletteKeyColor(){return this.getArgb(n.neutralPaletteKeyColor)}get neutralVariantPaletteKeyColor(){return this.getArgb(n.neutralVariantPaletteKeyColor)}get background(){return this.getArgb(n.background)}get onBackground(){return this.getArgb(n.onBackground)}get surface(){return this.getArgb(n.surface)}get surfaceDim(){return this.getArgb(n.surfaceDim)}get surfaceBright(){return this.getArgb(n.surfaceBright)}get surfaceContainerLowest(){return this.getArgb(n.surfaceContainerLowest)}get surfaceContainerLow(){return this.getArgb(n.surfaceContainerLow)}get surfaceContainer(){return this.getArgb(n.surfaceContainer)}get surfaceContainerHigh(){return this.getArgb(n.surfaceContainerHigh)}get surfaceContainerHighest(){return this.getArgb(n.surfaceContainerHighest)}get onSurface(){return this.getArgb(n.onSurface)}get surfaceVariant(){return this.getArgb(n.surfaceVariant)}get onSurfaceVariant(){return this.getArgb(n.onSurfaceVariant)}get inverseSurface(){return this.getArgb(n.inverseSurface)}get inverseOnSurface(){return this.getArgb(n.inverseOnSurface)}get outline(){return this.getArgb(n.outline)}get outlineVariant(){return this.getArgb(n.outlineVariant)}get shadow(){return this.getArgb(n.shadow)}get scrim(){return this.getArgb(n.scrim)}get surfaceTint(){return this.getArgb(n.surfaceTint)}get primary(){return this.getArgb(n.primary)}get onPrimary(){return this.getArgb(n.onPrimary)}get primaryContainer(){return this.getArgb(n.primaryContainer)}get onPrimaryContainer(){return this.getArgb(n.onPrimaryContainer)}get inversePrimary(){return this.getArgb(n.inversePrimary)}get secondary(){return this.getArgb(n.secondary)}get onSecondary(){return this.getArgb(n.onSecondary)}get secondaryContainer(){return this.getArgb(n.secondaryContainer)}get onSecondaryContainer(){return this.getArgb(n.onSecondaryContainer)}get tertiary(){return this.getArgb(n.tertiary)}get onTertiary(){return this.getArgb(n.onTertiary)}get tertiaryContainer(){return this.getArgb(n.tertiaryContainer)}get onTertiaryContainer(){return this.getArgb(n.onTertiaryContainer)}get error(){return this.getArgb(n.error)}get onError(){return this.getArgb(n.onError)}get errorContainer(){return this.getArgb(n.errorContainer)}get onErrorContainer(){return this.getArgb(n.onErrorContainer)}get primaryFixed(){return this.getArgb(n.primaryFixed)}get primaryFixedDim(){return this.getArgb(n.primaryFixedDim)}get onPrimaryFixed(){return this.getArgb(n.onPrimaryFixed)}get onPrimaryFixedVariant(){return this.getArgb(n.onPrimaryFixedVariant)}get secondaryFixed(){return this.getArgb(n.secondaryFixed)}get secondaryFixedDim(){return this.getArgb(n.secondaryFixedDim)}get onSecondaryFixed(){return this.getArgb(n.onSecondaryFixed)}get onSecondaryFixedVariant(){return this.getArgb(n.onSecondaryFixedVariant)}get tertiaryFixed(){return this.getArgb(n.tertiaryFixed)}get tertiaryFixedDim(){return this.getArgb(n.tertiaryFixedDim)}get onTertiaryFixed(){return this.getArgb(n.onTertiaryFixed)}get onTertiaryFixedVariant(){return this.getArgb(n.onTertiaryFixedVariant)}};/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var it=class t extends S{constructor(e,r,o){super({sourceColorArgb:e.toInt(),variant:B.EXPRESSIVE,contrastLevel:o,isDark:r,primaryPalette:A.fromHueAndChroma(z(e.hue+240),40),secondaryPalette:A.fromHueAndChroma(S.getRotatedHue(e,t.hues,t.secondaryRotations),24),tertiaryPalette:A.fromHueAndChroma(S.getRotatedHue(e,t.hues,t.tertiaryRotations),32),neutralPalette:A.fromHueAndChroma(e.hue+15,8),neutralVariantPalette:A.fromHueAndChroma(e.hue+15,12)})}};it.hues=[0,21,51,121,151,191,271,321,360];it.secondaryRotations=[45,95,45,20,45,90,45,45,45];it.tertiaryRotations=[120,120,20,45,20,15,20,120,120];/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var Ct=class extends S{constructor(e,r,o){super({sourceColorArgb:e.toInt(),variant:B.MONOCHROME,contrastLevel:o,isDark:r,primaryPalette:A.fromHueAndChroma(e.hue,0),secondaryPalette:A.fromHueAndChroma(e.hue,0),tertiaryPalette:A.fromHueAndChroma(e.hue,0),neutralPalette:A.fromHueAndChroma(e.hue,0),neutralVariantPalette:A.fromHueAndChroma(e.hue,0)})}};/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var bt=class extends S{constructor(e,r,o){super({sourceColorArgb:e.toInt(),variant:B.TONAL_SPOT,contrastLevel:o,isDark:r,primaryPalette:A.fromHueAndChroma(e.hue,36),secondaryPalette:A.fromHueAndChroma(e.hue,16),tertiaryPalette:A.fromHueAndChroma(z(e.hue+60),24),neutralPalette:A.fromHueAndChroma(e.hue,6),neutralVariantPalette:A.fromHueAndChroma(e.hue,8)})}};/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var ct=class t extends S{constructor(e,r,o){super({sourceColorArgb:e.toInt(),variant:B.VIBRANT,contrastLevel:o,isDark:r,primaryPalette:A.fromHueAndChroma(e.hue,200),secondaryPalette:A.fromHueAndChroma(S.getRotatedHue(e,t.hues,t.secondaryRotations),24),tertiaryPalette:A.fromHueAndChroma(S.getRotatedHue(e,t.hues,t.tertiaryRotations),32),neutralPalette:A.fromHueAndChroma(e.hue,10),neutralVariantPalette:A.fromHueAndChroma(e.hue,12)})}};ct.hues=[0,41,61,101,131,181,251,301,360];ct.secondaryRotations=[18,15,10,12,15,18,15,12,12];ct.tertiaryRotations=[35,30,20,25,30,35,30,25,25];/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var ie={desired:4,fallbackColorARGB:4282549748,filter:!0};function ce(t,e){return t.score>e.score?-1:t.score<e.score?1:0}var $=class t{constructor(){}static score(e,r){let{desired:o,fallbackColorARGB:a,filter:i}=ot(ot({},ie),r),s=[],c=new Array(360).fill(0),l=0;for(let[f,P]of e.entries()){let d=I.fromInt(f);s.push(d);let x=Math.floor(d.hue);c[x]+=P,l+=P}let m=new Array(360).fill(0);for(let f=0;f<360;f++){let P=c[f]/l;for(let d=f-14;d<f+16;d++){let x=gt(d);m[x]+=P}}let h=new Array;for(let f of s){let P=gt(Math.round(f.hue)),d=m[P];if(i&&(f.chroma<t.CUTOFF_CHROMA||d<=t.CUTOFF_EXCITED_PROPORTION))continue;let x=d*100*t.WEIGHT_PROPORTION,T=f.chroma<t.TARGET_CHROMA?t.WEIGHT_CHROMA_BELOW:t.WEIGHT_CHROMA_ABOVE,M=(f.chroma-t.TARGET_CHROMA)*T,C=x+M;h.push({hct:f,score:C})}h.sort(ce);let p=[];for(let f=90;f>=15;f--){p.length=0;for(let{hct:P}of h)if(p.find(x=>Dt(P.hue,x.hue)<f)||p.push(P),p.length>=o)break;if(p.length>=o)break}let y=[];p.length===0&&y.push(a);for(let f of p)y.push(f.toInt());return y}};$.TARGET_CHROMA=48;$.WEIGHT_PROPORTION=.7;$.WEIGHT_CHROMA_ABOVE=.3;$.WEIGHT_CHROMA_BELOW=.1;$.CUTOFF_CHROMA=5;$.CUTOFF_EXCITED_PROPORTION=.01;/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function Ft(t){let e=dt(t),r=yt(t),o=Pt(t),a=[e.toString(16),r.toString(16),o.toString(16)];for(let[i,s]of a.entries())s.length===1&&(a[i]="0"+s);return"#"+a.join("")}function Gt(t){t=t.replace("#","");let e=t.length===3,r=t.length===6,o=t.length===8;if(!e&&!r&&!o)throw new Error("unexpected hex "+t);let a=0,i=0,s=0;return e?(a=K(t.slice(0,1).repeat(2)),i=K(t.slice(1,2).repeat(2)),s=K(t.slice(2,3).repeat(2))):r?(a=K(t.slice(0,2)),i=K(t.slice(2,4)),s=K(t.slice(4,6))):o&&(a=K(t.slice(2,4)),i=K(t.slice(4,6)),s=K(t.slice(6,8))),(255<<24|(a&255)<<16|(i&255)<<8|s&255)>>>0}function K(t){return parseInt(t,16)}/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */return Zt(le);})();
