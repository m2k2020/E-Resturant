from django import template
from core.translations import t

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, text):
    lang = context.get('current_lang', 'en')
    from core.translations import t as translate
    return translate(text, lang)
