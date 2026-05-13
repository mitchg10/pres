from __future__ import annotations

import re
from textwrap import dedent

from presentation_maker.models import (
    PartialType,
    PresentationConfig,
    SlideCount,
    SlideType,
)

_PARTIAL_ORDER = [PartialType.INTRO, PartialType.AGENDA, PartialType.CREDITS, PartialType.THANK_YOU]

_PARTIAL_PATHS: dict[PartialType, str] = {
    PartialType.INTRO: "../../partials/_intro.qmd",
    PartialType.AGENDA: "../../partials/_agenda.qmd",
    PartialType.CREDITS: "../../partials/_credits.qmd",
    PartialType.THANK_YOU: "../../partials/_thank-you.qmd",
}


def slug_from_title(title: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", title.lower().strip()).strip("-")


def render_quarto_yml(config: PresentationConfig) -> str:
    safe_footer = config.title.replace('"', '\\"')
    return dedent(f"""\
        format:
          revealjs:
            theme: [default, brand, ../../styles/components.scss]
            logo: "images/ideeas_icon_only_color.png"
            include-after-body: logo-inject.html
            include-in-header:
              - text: |
                  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
                  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
            center-title-slide: false
            height: 1080
            width: 1920
            slide-number: "c/t"
            chalkboard: true
            preview-links: auto
            footer: "{safe_footer}"
            transition: slide
            background-transition: fade
            code-copy: true
            code-overflow: wrap
            highlight-style: a11y
    """)


def render_logo_inject_html(config: PresentationConfig) -> str:
    dept = config.department.value
    logo_script = dedent(f"""\
        <script>
        (function () {{
          function init() {{
            var revealEl = Reveal.getRevealElement();
            var logoImg = revealEl.querySelector('.slide-logo');
            if (!logoImg) return;
            var bar = document.createElement('div');
            bar.id = 'logo-bar';
            revealEl.insertBefore(bar, logoImg);
            bar.appendChild(logoImg);
            var colorImg = document.createElement('img');
            colorImg.src = 'images/{dept}_color.png';
            colorImg.alt = '{dept} logo';
            var whiteImg = document.createElement('img');
            whiteImg.src = 'images/{dept}_white.png';
            whiteImg.alt = '{dept} logo';
            whiteImg.style.display = 'none';
            bar.appendChild(colorImg);
            bar.appendChild(whiteImg);
            function sync(slide) {{
              var bg = Reveal.getSlideBackground(slide);
              var dark = bg && bg.classList.contains('has-dark-background');
              colorImg.style.display = dark ? 'none' : '';
              whiteImg.style.display = dark ? '' : 'none';
            }}
            Reveal.on('slidechanged', function(ev) {{ sync(ev.currentSlide); }});
            sync(Reveal.getCurrentSlide());
          }}
          function attach() {{
            if (window.Reveal && Reveal.isReady()) {{ init(); }}
            else if (window.Reveal) {{ Reveal.on('ready', init); }}
            else {{ setTimeout(attach, 50); }}
          }}
          if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', attach);
          }} else {{ attach(); }}
        }})();
        </script>
    """)
    if not config.show_section_header:
        return logo_script
    return logo_script + _render_section_header_script()


def _render_section_header_script() -> str:
    return dedent("""\
        <script>
        (function () {
          function init() {
            var revealEl = Reveal.getRevealElement();
            var allSlides = Reveal.getSlides();
            var sections = [];
            allSlides.forEach(function (slide, index) {
              var hasBg = slide.hasAttribute('data-background-color');
              var isTitle = slide.classList.contains('quarto-title-block');
              var isConclusion = slide.classList.contains('conclusion');
              if (hasBg && !isTitle && !isConclusion) {
                var h2 = slide.querySelector('h2');
                sections.push({
                  name: h2 ? h2.textContent.trim() : ('Section ' + (sections.length + 1)),
                  slideIndex: index
                });
              }
            });
            sections.unshift({ name: 'Intro', slideIndex: 1 });
            var header = document.createElement('div');
            header.id = 'section-nav-header';
            header.classList.add('hidden');
            var nameEls = [];
            sections.forEach(function (sec, i) {
              if (i > 0) {
                var sep = document.createElement('span');
                sep.className = 'section-sep';
                sep.textContent = '·';
                header.appendChild(sep);
              }
              var span = document.createElement('span');
              span.className = 'section-name';
              span.textContent = sec.name;
              header.appendChild(span);
              nameEls.push(span);
            });
            revealEl.insertBefore(header, revealEl.firstChild);
            function getCurrentSectionIdx(slideIndex) {
              var current = -1;
              for (var i = 0; i < sections.length; i++) {
                if (sections[i].slideIndex <= slideIndex) { current = i; }
                else { break; }
              }
              return current;
            }
            function sync(slide) {
              var slideIndex = allSlides.indexOf(slide);
              if (slide.hasAttribute('data-background-color') || slide.classList.contains('conclusion')) {
                header.classList.add('hidden');
                return;
              }
              var activeSectionIdx = getCurrentSectionIdx(slideIndex);
              if (activeSectionIdx === -1) {
                header.classList.add('hidden');
                return;
              }
              header.classList.remove('hidden');
              var bg = Reveal.getSlideBackground(slide);
              var isDark = bg && bg.classList.contains('has-dark-background');
              header.classList.toggle('dark-bg', !!isDark);
              nameEls.forEach(function (el, i) {
                el.classList.toggle('active', i === activeSectionIdx);
              });
            }
            Reveal.on('slidechanged', function (ev) { sync(ev.currentSlide); });
            sync(Reveal.getCurrentSlide());
          }
          function attach() {
            if (window.Reveal && Reveal.isReady()) { init(); }
            else if (window.Reveal) { Reveal.on('ready', init); }
            else { setTimeout(attach, 50); }
          }
          if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', attach);
          } else { attach(); }
        })();
        </script>
    """)


def render_index_qmd(config: PresentationConfig) -> str:
    sections: list[str] = [_render_frontmatter(config)]

    pre_partials = [p for p in _PARTIAL_ORDER if p in config.partials and p != PartialType.THANK_YOU]
    post_partials = [p for p in _PARTIAL_ORDER if p in config.partials and p == PartialType.THANK_YOU]

    if pre_partials:
        sections.append(_render_partial_includes(pre_partials))

    content = _render_content_slides(config.slides)
    if content:
        sections.append(content)

    if post_partials:
        sections.append(_render_partial_includes(post_partials))

    return "\n\n".join(sections) + "\n"


def _render_frontmatter(config: PresentationConfig) -> str:
    lines = [
        "---",
        f'title: "{config.title}"',
    ]
    if config.subtitle:
        lines.append(f'subtitle: "{config.subtitle}"')
    lines += [
        f'author: "{config.author}"',
        'institute: "IDEEAS Lab"',
        f'date: "{config.date.isoformat()}"',
        "title-slide-attributes:",
        '  data-background-color: "#861F41"',
        "---",
    ]
    return "\n".join(lines)


def _render_partial_includes(partials: list[PartialType]) -> str:
    return "\n\n".join(
        f"{{{{< include {_PARTIAL_PATHS[p]} >}}}}" for p in partials
    )


def _render_bullet_list_slide(index: int) -> str:
    return dedent(f"""\
        ## Slide Title {index}

        - Point one
        - Point two
        - Point three
    """).rstrip()


def _render_text_with_image_slide(index: int) -> str:
    return dedent(f"""\
        ## Slide Title {index}

        :::: {{.columns}}

        ::: {{.column width="60%"}}
        Text content goes here.
        :::

        ::: {{.column width="40%"}}
        ![Image caption](images/placeholder.png){{fig-alt="Descriptive alt text"}}
        :::

        ::::
    """).rstrip()


def _render_section_divider_slide(index: int) -> str:
    return dedent(f"""\
        ## Section Title {index} {{background-color="#E5751F"}}
    """).rstrip()


def _render_three_cards_slide(index: int) -> str:
    return dedent(f"""\
        ## Slide Title {index}

        :::: {{.columns}}

        ::: {{.column width="33%"}}
        ::: {{.card}}
        **Card One**

        Supporting detail goes here.
        :::
        :::

        ::: {{.column width="33%"}}
        ::: {{.card}}
        **Card Two**

        Supporting detail goes here.
        :::
        :::

        ::: {{.column width="33%"}}
        ::: {{.card}}
        **Card Three**

        Supporting detail goes here.
        :::
        :::

        ::::
    """).rstrip()


def _render_text_with_question_slide(index: int) -> str:
    return dedent(f"""\
        ## Slide Title {index}

        Main content text goes here. Explain the concept, finding, or idea
        you want to share with the audience.

        ::: {{.discussion-box}}
        **Discussion:** What are your thoughts on this? What questions does it raise?
        :::
    """).rstrip()


def _render_content_slides(slides: list[SlideCount]) -> str:
    _renderers = {
        SlideType.BULLET_LIST: _render_bullet_list_slide,
        SlideType.TEXT_WITH_IMAGE: _render_text_with_image_slide,
        SlideType.SECTION_DIVIDER: _render_section_divider_slide,
        SlideType.THREE_CARDS: _render_three_cards_slide,
        SlideType.TEXT_WITH_QUESTION: _render_text_with_question_slide,
    }
    rendered: list[str] = []
    global_index = 1
    for slide_count in slides:
        renderer = _renderers[slide_count.slide_type]
        for _ in range(slide_count.count):
            rendered.append(renderer(global_index))
            global_index += 1
    return "\n\n".join(rendered)
