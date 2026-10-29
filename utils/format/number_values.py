def clean_cpf(cpf: str) -> str:
    formatted_cpf = cpf.strip().replace(".", "").replace("-", "")

    return formatted_cpf


def format_cpf(cpf: str) -> str:
    if len(cpf) != 11:
        raise TypeError
    formatted_cpf = f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    return formatted_cpf


def clean_zip_code(zip_code: str) -> str:
    formatted_zip_code = zip_code.strip().replace(".", "").replace("-", "")

    return formatted_zip_code


def format_zip_code(zip_code: str) -> str:
    formatted_zip_code = f"{zip_code[:-3]}-{zip_code[-3:]}"

    return formatted_zip_code


UNITS = [
    "zero",
    "um",
    "dois",
    "três",
    "quatro",
    "cinco",
    "seis",
    "sete",
    "oito",
    "nove",
    "dez",
    "onze",
    "doze",
    "treze",
    "quatorze",
    "quinze",
    "dezesseis",
    "dezessete",
    "dezoito",
    "dezenove",
]
TENS = [
    "_",
    "_",
    "vinte",
    "trinta",
    "quarenta",
    "cinquenta",
    "sessenta",
    "setenta",
    "oitenta",
    "noventa",
]
HUNDREDS = [
    "_",
    "cento",
    "duzentos",
    "trezentos",
    "quatrocentos",
    "quinhentos",
    "seiscentos",
    "setecentos",
    "oitocentos",
    "novecentos",
]


def _below_thousand(n: int) -> str:
    if n == 100:
        return "cem"
    parts = []
    if n >= 100:
        parts.append(HUNDREDS[n // 100])
        n %= 100
    if n >= 20:
        parts.append(TENS[n // 10])
        n %= 10
    if n:
        parts.append(UNITS[n])
    return " e ".join(parts)


def _integer_in_words(n: int) -> str:
    if n == 0:
        return "zero"
    # (value, singular, plural); shortcut: stops at billions, fine for receipts.
    scales = (
        (10**9, "bilhão", "bilhões"),
        (10**6, "milhão", "milhões"),
        (1000, "mil", "mil"),
    )
    groups = []
    for value, singular, plural in scales:
        count, n = divmod(n, value)
        if count:
            name = singular if count == 1 else plural
            text = (
                name
                if value == 1000 and count == 1
                else f"{_below_thousand(count)} {name}"
            )
            groups.append((count, text))
    if n:
        groups.append((n, _below_thousand(n)))
    texts = [text for _, text in groups]
    # "e" joins the last group when its count is below 100 or a round hundred.
    last_count = groups[-1][0]
    if len(groups) > 1 and (last_count < 100 or last_count % 100 == 0):
        return " ".join(texts[:-1]) + " e " + texts[-1]
    return " ".join(texts)


def amount_in_words(value) -> str:
    """Brazilian currency in words: 7530.16 -> 'sete mil quinhentos e trinta reais e dezesseis centavos'."""
    cents_total = round(value * 100)
    reais, cents = divmod(cents_total, 100)
    parts = []
    if reais:
        words = _integer_in_words(reais)
        # "um milhão de reais", "dois milhões de reais"
        suffix = (
            " de reais" if reais % 10**6 == 0 else (" real" if reais == 1 else " reais")
        )
        parts.append(words + suffix)
    if cents:
        parts.append(
            _integer_in_words(cents) + (" centavo" if cents == 1 else " centavos")
        )
    return " e ".join(parts) or "zero reais"
