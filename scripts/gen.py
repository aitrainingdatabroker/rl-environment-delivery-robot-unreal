import json, math, pathlib
FPS=30
OUT=pathlib.Path(__file__).parent / 'work'
OUT.mkdir(exist_ok=True)
def cr(p0,p1,p2,p3,t):
    return 0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
def path(wps):
    # wps: (t,x,y,yaw); returns f(t)->(x,y,yaw) Catmull-Rom on xy, smoothstep yaw
    def f(t):
        if t<=wps[0][0]: return wps[0][1:]
        if t>=wps[-1][0]: return wps[-1][1:]
        for i in range(len(wps)-1):
            if wps[i][0]<=t<=wps[i+1][0]:
                a=wps[i]; b=wps[i+1]; u=(t-a[0])/(b[0]-a[0]) if b[0]>a[0] else 1
                p0=wps[max(i-1,0)]; p3=wps[min(i+2,len(wps)-1)]
                x=cr(p0[1],a[1],b[1],p3[1],u); y=cr(p0[2],a[2],b[2],p3[2],u)
                s=u*u*(3-2*u); yaw=a[3]+(b[3]-a[3])*s
                return (x,y,yaw)
    return f
beg=path([(0,-900,-480,0),(1.0,-820,-475,5),(2.0,-720,-458,-6),(2.8,-655,-449,8),(3.0,-645,-447,10),(3.3,-665,-452,25),(4.3,-680,-430,70),(5.5,-640,-320,85),(7.0,-630,70,95),(7.4,-632,98,92),(7.7,-636,80,120),(9.0,-640,60,300)])
pro_w=[(0,-900,-480,0),(5,-120,-480,0),(6,-45,-430,80),(6.5,-40,-340,90),(10.5,-40,340,90),(11.2,-30,430,60),(12,20,480,0),(13,200,480,0),(17.5,1000,480,0),(19.5,1380,515,15),(20,1400,520,20)]
pro=path(pro_w)
att1=path([(0,-900,-480,0),(1.2,-700,-470,10),(2.2,-560,-250,60),(3.0,-450,0,40)])
att2=path([(0,-900,-480,0),(1.2,-120,-480,0),(1.6,-40,-330,90),(2.8,-40,380,90),(3.5,-300,480,180)])
att3=path([(w[0]*4.5/20.0,)+w[1:] for w in pro_w])
def robot(t):
    if t<9: return beg(t)
    if t<17: return (-900,-480,0)
    if t<20: return att1(t-17)
    if t<24.5: return att2(t-20)
    if t<29: return att3(t-24.5)
    if t<49: return pro(t-29)
    return pro(20)
def rz(x,y):
    a=abs(y)
    if a<340: return 48.0
    if a>360: return 61.0
    return 48+(a-340)/20*13
# chase camera with smoothed yaw
def chase(seg_start, seg_end, dist=300, up=150, side=0):
    keys={}
    yaw_s=None; pos_s=None
    t=seg_start
    while t<=seg_end+1e-6:
        x,y,yaw=robot(t)
        if yaw_s is None: yaw_s=yaw
        yaw_s+= (yaw-yaw_s)*(1-math.exp(-(1/FPS)/0.7))
        r=math.radians(yaw_s)
        cx=x-math.cos(r)*dist; cy=y-math.sin(r)*dist-math.copysign(side,y) if abs(y)>200 else y-math.sin(r)*dist; cz=rz(x,y)+up
        if pos_s is None: pos_s=[cx,cy,cz]
        k=1-math.exp(-(1/FPS)/0.25)
        pos_s=[pos_s[i]+([cx,cy,cz][i]-pos_s[i])*k for i in range(3)]
        tx=x+math.cos(r)*90; ty=y+math.sin(r)*90; tz=rz(x,y)+20
        keys[round(t*FPS)]=look(pos_s,(tx,ty,tz))
        t+=1/FPS
    return keys
def look(p,tg):
    dx,dy,dz=tg[0]-p[0],tg[1]-p[1],tg[2]-p[2]
    yaw=math.degrees(math.atan2(dy,dx)); pitch=math.degrees(math.atan2(dz,math.hypot(dx,dy)))
    return (p[0],p[1],p[2],pitch,yaw)
def ease(u): return u*u*(3-2*u)
cam={}
cam.update(chase(0,8.99,dist=330,up=200,side=170))
for f in range(9*FPS,17*FPS):
    u=ease((f/FPS-9)/8)
    p=[0+(-900-0)*u, 1300+(170-1300)*u, 1500+(250-1500)*u]
    cam[f]=look(p,(-900,-660,170+40*(1-u)))
for f in range(17*FPS,29*FPS):
    cam[f]=(0,0,3700,-89.9,-90)
cam.update(chase(29,48.99,dist=340,up=190,side=170))
for f in range(49*FPS,55*FPS+1):
    u=ease((f/FPS-49)/6)
    p=[1230+400*u,300,150+20*u]
    cam[f]=look(p,(1440,530,90))
# sample keys every 3 frames, plus both sides of cuts
cuts=[9*FPS,17*FPS,24.5*FPS,20*FPS,29*FPS,49*FPS]
frames=set(range(0,55*FPS+1,6))
for c in cuts:
    c=int(c); frames|={c-1,c}
frames=sorted(f for f in frames if 0<=f<=55*FPS)
cutset=set(int(c)-1 for c in cuts)
R={'Location.X':[],'Location.Y':[],'Location.Z':[],'Rotation.Z':[]}
C={'Location.X':[],'Location.Y':[],'Location.Z':[],'Rotation.Y':[],'Rotation.Z':[]}
prev_ryaw=None
for f in frames:
    t=f/FPS
    x,y,yaw=robot(t)
    interp='constant' if f in cutset else 'auto'
    R['Location.X'].append([f,round(x,2),interp]); R['Location.Y'].append([f,round(y,2),interp]); R['Location.Z'].append([f,round(rz(x,y),2),interp]); R['Rotation.Z'].append([f,round(yaw,2),interp])
    c=cam.get(f) or cam[min(cam,key=lambda k:abs(k-f))]
    C['Location.X'].append([f,round(c[0],1),interp]); C['Location.Y'].append([f,round(c[1],1),interp]); C['Location.Z'].append([f,round(c[2],1),interp]); C['Rotation.Y'].append([f,round(c[3],2),interp]); C['Rotation.Z'].append([f,round(c[4],2),interp])
# unwrap camera yaw
prev=None
for k in C['Rotation.Z']:
    if prev is not None:
        while k[1]-prev>180: k[1]-=360
        while k[1]-prev<-180: k[1]+=360
    prev=k[1]
json.dump({'R':R,'C':C},open(OUT/'keys.json','w'))
print(len(frames),'frames', sum(len(v) for v in R.values())+sum(len(v) for v in C.values()),'keys')
