# cleaning.py


def clean_text_safe(text):
    if not isinstance(text, str):
        return ""
    return text.replace("\xa0", " ").strip()
