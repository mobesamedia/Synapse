"""Shared display-only review-activity chart for dashboard and deck overview."""
from html import escape
import uuid


def render_activity_chart(labels, values, *, width=300.0, height=62.0, padding=4.0,
                          color='--main-blue', axis_color='--gray',
                          css_class='spark', dot_class='spark-today', description=None):
    if not values:
        return ''
    maximum = max(values) or 1
    right_inset = 5.0
    step = (width-right_inset)/max(1,len(values)-1)
    low, high = height-padding,padding
    points = [(i*step,low-value/maximum*(low-high)) for i,value in enumerate(values)]
    clamp=lambda y:max(high,min(low,y))
    if len(points)<3:
        line='M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in points)
    else:
        line=f'M{points[0][0]:.1f},{points[0][1]:.1f}'
        for i in range(len(points)-1):
            p0=points[i-1] if i>0 else points[i]
            p1,p2=points[i],points[i+1]
            p3=points[i+2] if i+2<len(points) else p2
            line+=(f' C{p1[0]+(p2[0]-p0[0])/6:.1f},{clamp(p1[1]+(p2[1]-p0[1])/6):.1f}'
                   f' {p2[0]-(p3[0]-p1[0])/6:.1f},{clamp(p2[1]-(p3[1]-p1[1])/6):.1f}'
                   f' {p2[0]:.1f},{p2[1]:.1f}')
    area=line+f' L{points[-1][0]:.1f},{low:.1f} L0,{low:.1f} Z'
    gradient='consistency-fill-'+uuid.uuid4().hex
    axes=(f'<line x1="0.5" y1="{high:.1f}" x2="0.5" y2="{low:.1f}" stroke="var({axis_color})" stroke-width="1" vector-effect="non-scaling-stroke"/>'
          f'<line x1="0" y1="{low:.1f}" x2="{width:.1f}" y2="{low:.1f}" stroke="var({axis_color})" stroke-width="1" vector-effect="non-scaling-stroke"/>')
    hover=''.join(f'<rect x="{i*step-step/2:.1f}" y="0" width="{step:.1f}" height="{height:.0f}" fill="transparent"><title>{escape(str(label))}: {value}</title></rect>' for i,(label,value) in enumerate(zip(labels,values)))
    aria=f' role="img" aria-label="{escape(description,quote=True)}"' if description else ''
    return (f'<svg class="{css_class}" viewBox="0 0 {width:.0f} {height:.0f}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"{aria}>'
            f'<defs><linearGradient id="{gradient}" x1="0" y1="{high}" x2="0" y2="{low}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="var({color})" stop-opacity="0.24"/><stop offset="1" stop-color="var({color})" stop-opacity="0"/></linearGradient></defs>'
            f'{axes}<path d="{area}" fill="url(#{gradient})" stroke="none"/><path d="{line}" fill="none" stroke="var({color})" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>{hover}</svg>'
            f'<span class="{dot_class}" aria-hidden="true" style="left:{points[-1][0]/width*100:.6f}%;top:{points[-1][1]/height*100:.6f}%;"></span>')
