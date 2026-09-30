"""Visible paper, real font loading, and disjoint touch controls."""

import base64

import pytest
from playwright.sync_api import Browser, Page


@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize(
    "selector",
    [
        "#inner-body",
        ".mewbo-header",
        ".ms-header-tabs",
        '[data-slot="sidebar-wrapper"]::before',
        ".ms-card",
        ".mewbo-footer",
        ".ms-mobile-nav__panel",
        "#mewbo-modal",
    ],
)
def test_paper_has_visible_fibres(
    page: Page, local_deployment: str, dark: bool, selector: str
):
    page.goto(
        local_deployment + "/display_face_regression/",
        wait_until="networkidle",
    )
    # Sample the actual surface paint without content or shadow contaminating
    # the measurement. A declared URL alone says nothing about visible grain.
    page.evaluate(
        """({dark, selector}) => {
      document.documentElement.classList.toggle('dark', dark);
      const [element, pseudo] = selector.split('::');
      const surface = getComputedStyle(document.querySelector(element), pseudo ? '::'+pseudo : null);
      const patch = document.createElement('div');
      patch.id = 'paper-patch';
      Object.assign(patch.style, {
        position: 'fixed', top: '200px', left: '400px', width: '160px', height: '160px',
        zIndex: '9999', backgroundColor: surface.backgroundColor,
        backgroundImage: surface.backgroundImage, backgroundSize: surface.backgroundSize
      });
      document.body.append(patch);
    }""",
        {"dark": dark, "selector": selector},
    )
    png = base64.b64encode(page.locator("#paper-patch").screenshot()).decode()
    deviation = page.evaluate(
        """async png => {
      const image=new Image(); image.src='data:image/png;base64,'+png;
      await image.decode();
      const canvas=document.createElement('canvas');
      canvas.width=image.width; canvas.height=image.height;
      const ctx=canvas.getContext('2d'); ctx.drawImage(image,0,0);
      const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
      const values=[];
      for(let i=0;i<data.length;i+=4) values.push((data[i]+data[i+1]+data[i+2])/3);
      const mean=values.reduce((a,b)=>a+b,0)/values.length;
      return Math.sqrt(values.reduce((sum,x)=>sum+(x-mean)**2,0)/values.length);
    }""",
        png,
    )
    # The reference stock is attenuated by 25%. Keep measurable fibres,
    # allowing a little rounding variance between rendering engines.
    assert 1.25 <= deviation <= 3.75, (selector, dark, deviation)


def test_reading_face_is_loaded_and_has_editorial_leading(
    page: Page, local_deployment: str
):
    page.goto(
        local_deployment + "/display_face_regression/",
        wait_until="networkidle",
    )
    metrics = page.locator("article .typography > p").first.evaluate("""async el => {
      await document.fonts.ready;
      const c = getComputedStyle(el);
      return {family:c.fontFamily, size:parseFloat(c.fontSize),
        leading:parseFloat(c.lineHeight)/parseFloat(c.fontSize),
        loaded:[...document.fonts].some(f=>f.family.includes('Newsreader') && f.status==='loaded')};
    }""")
    assert "Newsreader" in metrics["family"], metrics
    assert metrics["loaded"], metrics
    assert metrics["size"] >= 17, metrics
    assert 1.45 <= metrics["leading"] <= 1.65, metrics


def test_touch_halves_do_not_steal_each_others_edges(
    browser: Browser, local_deployment: str
):
    with browser.new_context(
        viewport={"width": 390, "height": 844}, has_touch=True
    ) as context:
        page = context.new_page()
        page.goto(local_deployment + "/", wait_until="networkidle")
        for selector in (
            "[data-copy-markdown]",
            "[data-mewbo-page-actions-toggle]",
            "#next-button",
        ):
            hit = page.locator(selector).evaluate("""el => {
              const r=el.getBoundingClientRect();
              const left=document.elementFromPoint(r.left+2, r.top+r.height/2);
              const right=document.elementFromPoint(r.right-2, r.top+r.height/2);
              return {own:el.contains(left)&&el.contains(right), height:r.height, width:r.width};
            }""")
            assert hit["own"], (selector, hit)
            assert hit["height"] >= 44 and hit["width"] >= 44, (selector, hit)


@pytest.mark.parametrize("dark", [False, True])
def test_ink_is_legible_on_each_stock(
    page: Page, local_deployment: str, dark: bool
):
    page.goto(local_deployment + "/", wait_until="networkidle")
    ratios = page.evaluate(
        """dark => {
      document.documentElement.classList.toggle('dark',dark);
      const css=getComputedStyle(document.documentElement);
      const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
      const ctx=canvas.getContext('2d');
      const rgb=(token, backdrop) => {
        ctx.clearRect(0,0,1,1);
        if(backdrop){ctx.fillStyle=css.getPropertyValue(backdrop);ctx.fillRect(0,0,1,1)}
        ctx.fillStyle=css.getPropertyValue(token);ctx.fillRect(0,0,1,1);
        return [...ctx.getImageData(0,0,1,1).data].slice(0,3);
      };
      const lum=rgb=>rgb.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4)
        .reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
      const contrast=(a,b)=>{const l=[lum(a),lum(b)].sort((x,y)=>x-y);return (l[1]+.05)/(l[0]+.05)};
      const result={};
      for(const bg of ['--background','--card','--nav-background','--sidebar']){
        for(const ink of ['--foreground','--muted-foreground','--primary-text'])
          result[ink+' on '+bg]=contrast(rgb(ink,bg),rgb(bg));
      }
      result.button=contrast(rgb('--primary-foreground'),rgb('--primary'));
      return result;
    }""",
        dark,
    )
    assert min(ratios.values()) >= 4.5, ratios
