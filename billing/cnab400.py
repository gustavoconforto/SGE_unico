"""Bradesco "Cobrança" CNAB 400: remittance (.REM) writer and return (.RET) reader.

Pure Python, no Django. Field positions are 1-based and inclusive, as in the
bank's layout manual. Fixed values that the manual leaves open (debit fields,
positions 94 and 106, no EOF byte) follow the files Bradesco already accepts
from the school.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256

RECORD_LENGTH = 400
BANK_CODE = "237"

SETTLEMENT_CODES = frozenset({"06", "15", "17"})
REVERSAL_CODES = frozenset({"22", "40"})


def _digits(value: object, size: int, *, field: str) -> str:
    raw = re.sub(r"\D", "", str(value)) or "0"
    if len(raw) > size:
        raise ValueError(f"{field}: excede {size} posições")
    return raw.zfill(size)


def _text(value: object, size: int, *, field: str, truncate: bool = False) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(char for char in raw if not unicodedata.combining(char))
    raw = re.sub(r"[^A-Za-z0-9 ./-]", " ", raw).upper()
    raw = re.sub(r"\s+", " ", raw).strip()
    if truncate:
        raw = raw[:size].rstrip()
    elif len(raw) > size:
        raise ValueError(f"{field}: excede {size} posições")
    return raw.ljust(size)


def _money(value: Decimal | str | int, size: int, *, field: str) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount < 0:
        raise ValueError(f"{field}: valor negativo")
    return _digits(int(amount * 100), size, field=field)


def _date(value: date | None) -> str:
    return "000000" if value is None else value.strftime("%d%m%y")


def _parse_date(raw: str) -> date | None:
    if raw.strip() in {"", "000000"}:
        return None
    if not re.fullmatch(r"\d{6}", raw):
        raise ValueError(f"data CNAB inválida: {raw!r}")
    return date(2000 + int(raw[4:]), int(raw[2:4]), int(raw[:2]))


def _parse_money(raw: str, *, field: str) -> Decimal:
    if not raw.isdigit():
        raise ValueError(f"{field}: valor numérico inválido")
    return Decimal(int(raw)) / Decimal(100)


class Record:
    """A 400-char line filled field by field; overlaps and gaps are errors."""

    def __init__(self) -> None:
        self._chars = [" "] * RECORD_LENGTH
        self._used: set[int] = set()

    def set(self, start: int, end: int, value: str) -> Record:
        if not (1 <= start <= end <= RECORD_LENGTH):
            raise ValueError(f"intervalo inválido: {start}-{end}")
        expected = end - start + 1
        if len(value) != expected:
            raise ValueError(
                f"campo {start}-{end}: esperado {expected}, recebido {len(value)}"
            )
        positions = set(range(start, end + 1))
        if positions & self._used:
            raise ValueError(f"campo sobreposto: {start}-{end}")
        self._chars[start - 1 : end] = value
        self._used |= positions
        return self

    def render(self) -> str:
        if len(self._used) != RECORD_LENGTH:
            raise ValueError("registro com posições não preenchidas")
        result = "".join(self._chars)
        result.encode("ascii")
        return result


def nosso_numero_dv(carteira: str, nosso_numero: str) -> str:
    """Check digit (modulo 11, base 7) of the Bradesco "nosso número".

    The wallet is used with two digits ("009" == "09"). Returns a digit or "P".
    """
    wallet = re.sub(r"\D", "", carteira)
    if len(wallet) == 3 and wallet.startswith("0"):
        wallet = wallet[1:]
    if len(wallet) != 2:
        raise ValueError("carteira deve ter 2 dígitos (ou 3 com zero inicial)")
    base = wallet + _digits(nosso_numero, 11, field="nosso_numero")
    weights = [2, 3, 4, 5, 6, 7]
    total = sum(
        int(digit) * weights[index % 6] for index, digit in enumerate(reversed(base))
    )
    remainder = total % 11
    if remainder == 0:
        return "0"
    if remainder == 1:
        return "P"
    return str(11 - remainder)


@dataclass(frozen=True)
class Beneficiary:
    company_code: str
    name: str
    carteira: str
    agency: str
    account: str
    account_digit: str

    @property
    def bank_identifier(self) -> str:
        """Positions 21-37: zero, wallet, agency, account and its digit."""
        return (
            "0"
            + _digits(self.carteira, 3, field="carteira")
            + _digits(self.agency, 5, field="agency")
            + _digits(self.account, 7, field="account")
            + _text(self.account_digit, 1, field="account_digit")
        )


@dataclass(frozen=True)
class Payer:
    tax_id: str
    name: str
    address: str
    zip_code: str

    @property
    def tax_id_type(self) -> str:
        length = len(re.sub(r"\D", "", self.tax_id))
        if length == 11:
            return "01"
        if length == 14:
            return "02"
        raise ValueError("CPF/CNPJ do pagador deve ter 11 ou 14 dígitos")


@dataclass(frozen=True)
class Title:
    participant_control: str
    document_number: str
    nosso_numero: str
    due_date: date
    amount: Decimal
    issue_date: date
    payer: Payer
    species: str = "12"
    emission_by: str = "2"
    movement_code: str = "01"
    daily_interest: Decimal = Decimal("0.00")
    fine_percent: Decimal = Decimal("0.00")
    discount_deadline: date | None = None
    discount_amount: Decimal = Decimal("0.00")
    first_instruction: str = "00"
    second_instruction: str = "00"
    message: str = ""


@dataclass(frozen=True)
class RemittanceConfig:
    beneficiary: Beneficiary
    remittance_number: int
    generation_date: date


def _header(config: RemittanceConfig) -> str:
    b = config.beneficiary
    return (
        Record()
        .set(1, 1, "0")
        .set(2, 9, "1REMESSA")
        .set(10, 26, "01COBRANCA".ljust(17))
        .set(27, 46, _digits(b.company_code, 20, field="company_code"))
        .set(47, 76, _text(b.name, 30, field="beneficiary_name", truncate=True))
        .set(77, 79, BANK_CODE)
        .set(80, 94, "BRADESCO".ljust(15))
        .set(95, 100, _date(config.generation_date))
        .set(101, 108, " " * 8)
        .set(109, 110, "MX")
        .set(111, 117, _digits(config.remittance_number, 7, field="remittance_number"))
        .set(118, 394, " " * 277)
        .set(395, 400, "000001")
        .render()
    )


def _detail(config: RemittanceConfig, title: Title, sequence: int) -> str:
    b = config.beneficiary
    number = _digits(title.nosso_numero, 11, field="nosso_numero")
    fine = Decimal(str(title.fine_percent)).quantize(Decimal("0.01"))
    if not Decimal(0) <= fine <= Decimal("99.99"):
        raise ValueError("fine_percent deve estar entre 0 e 99.99")
    zip_code = _digits(title.payer.zip_code, 8, field="zip_code")
    return (
        Record()
        .set(1, 1, "1")
        # Automatic debit agency/account: unused, as in the accepted files.
        .set(2, 20, "00000 000000000000 ")
        .set(21, 37, b.bank_identifier)
        .set(38, 62, _text(title.participant_control, 25, field="participant_control"))
        .set(63, 65, "000")
        .set(66, 66, "2" if fine else "0")
        .set(67, 70, _digits(int(fine * 100), 4, field="fine_percent"))
        .set(71, 81, number)
        .set(82, 82, nosso_numero_dv(b.carteira, number))
        .set(83, 92, "0" * 10)
        .set(93, 93, _digits(title.emission_by, 1, field="emission_by"))
        .set(94, 94, "N")
        .set(95, 104, " " * 10)
        .set(105, 105, " ")
        .set(106, 106, "2")
        .set(107, 108, " " * 2)
        .set(109, 110, _digits(title.movement_code, 2, field="movement_code"))
        .set(111, 120, _text(title.document_number, 10, field="document_number"))
        .set(121, 126, _date(title.due_date))
        .set(127, 139, _money(title.amount, 13, field="amount"))
        .set(140, 147, "0" * 8)
        .set(148, 149, _digits(title.species, 2, field="species"))
        .set(150, 150, "N")
        .set(151, 156, _date(title.issue_date))
        .set(157, 158, _digits(title.first_instruction, 2, field="first_instruction"))
        .set(159, 160, _digits(title.second_instruction, 2, field="second_instruction"))
        .set(161, 173, _money(title.daily_interest, 13, field="daily_interest"))
        .set(174, 179, _date(title.discount_deadline))
        .set(180, 192, _money(title.discount_amount, 13, field="discount_amount"))
        .set(193, 218, "0" * 26)
        .set(219, 220, title.payer.tax_id_type)
        .set(221, 234, _digits(title.payer.tax_id, 14, field="payer_tax_id"))
        .set(235, 274, _text(title.payer.name, 40, field="payer_name", truncate=True))
        .set(
            275,
            314,
            _text(title.payer.address, 40, field="payer_address", truncate=True),
        )
        .set(315, 326, _text(title.message, 12, field="message", truncate=True))
        .set(327, 334, zip_code)
        .set(335, 394, " " * 60)
        .set(395, 400, _digits(sequence, 6, field="sequence"))
        .render()
    )


def _trailer(sequence: int) -> str:
    return (
        Record()
        .set(1, 1, "9")
        .set(2, 394, " " * 393)
        .set(395, 400, _digits(sequence, 6, field="sequence"))
        .render()
    )


def generate_remittance(config: RemittanceConfig, titles: Iterable[Title]) -> bytes:
    title_list = list(titles)
    if not title_list:
        raise ValueError("a remessa deve conter pelo menos um título")
    lines = [_header(config)]
    lines.extend(
        _detail(config, title, index) for index, title in enumerate(title_list, 2)
    )
    lines.append(_trailer(len(lines) + 1))
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def remittance_filename(number: int) -> str:
    return f"{number:08d}.REM"


@dataclass(frozen=True)
class ReturnEvent:
    sequence: int
    occurrence_code: str
    occurrence_date: date | None
    participant_control: str
    nosso_numero: str
    document_number: str
    due_date: date | None
    title_amount: Decimal
    amount_paid: Decimal
    interest_amount: Decimal
    discount_amount: Decimal
    credit_date: date | None
    reason_codes: tuple[str, ...]
    fingerprint: str

    @property
    def is_settlement(self) -> bool:
        return self.occurrence_code in SETTLEMENT_CODES

    @property
    def is_reversal(self) -> bool:
        return self.occurrence_code in REVERSAL_CODES


@dataclass(frozen=True)
class ReturnData:
    company_code: str
    file_date: date | None
    events: list[ReturnEvent]


def _split_records(payload: bytes) -> list[bytes]:
    cleaned = payload.rstrip(b"\x1a")
    lines = [line for line in cleaned.splitlines() if line]
    if not lines:
        raise ValueError("arquivo vazio")
    for index, line in enumerate(lines, 1):
        if len(line) != RECORD_LENGTH:
            raise ValueError(
                f"registro {index}: esperado 400 caracteres, recebido {len(line)}"
            )
        try:
            line.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"registro {index}: arquivo não ASCII") from exc
    return lines


def parse_return(payload: bytes) -> ReturnData:
    lines = _split_records(payload)
    if lines[0][0:9] != b"02RETORNO" or lines[0][76:79] != BANK_CODE.encode():
        raise ValueError("o arquivo não é um retorno de Cobrança Bradesco CNAB 400")
    if lines[-1][0:1] != b"9":
        raise ValueError("trailer ausente")
    expected = [f"{index:06d}".encode() for index in range(1, len(lines) + 1)]
    if [line[394:400] for line in lines] != expected:
        raise ValueError("sequência de registros inválida")

    header = lines[0].decode("ascii")
    events: list[ReturnEvent] = []
    for line in lines[1:-1]:
        if line[0:1] != b"1":
            continue
        text = line.decode("ascii")
        reasons = text[318:328]
        nosso_numero = text[70:82].strip() or text[126:146].strip()
        events.append(
            ReturnEvent(
                sequence=int(text[394:400]),
                occurrence_code=text[108:110],
                occurrence_date=_parse_date(text[110:116]),
                participant_control=text[37:62].strip(),
                nosso_numero=nosso_numero,
                document_number=text[116:126].strip(),
                due_date=_parse_date(text[146:152]),
                title_amount=_parse_money(text[152:165], field="title_amount"),
                discount_amount=_parse_money(text[240:253], field="discount_amount"),
                amount_paid=_parse_money(text[253:266], field="amount_paid"),
                interest_amount=_parse_money(text[266:279], field="interest_amount"),
                credit_date=_parse_date(text[295:301]),
                reason_codes=tuple(
                    reasons[index : index + 2]
                    for index in range(0, len(reasons), 2)
                    if reasons[index : index + 2] not in {"00", "  "}
                ),
                fingerprint=sha256(line).hexdigest(),
            )
        )
    return ReturnData(
        company_code=header[26:46].strip(),
        file_date=_parse_date(header[94:100]),
        events=events,
    )
