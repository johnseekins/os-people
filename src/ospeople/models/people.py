import re
import typing
from enum import Enum
from pydantic import validator, root_validator
from .common import (
    BaseModel,
    TimeScoped,
    Link,
    OtherName,
    OtherIdentifier,
    validate_ocd_person,
    validate_url,
    validate_fuzzy_date,
    validate_ocd_jurisdiction,
    validate_str_no_newline,
)

SUFFIX_RE = re.compile(r"(iii?)|(i?v)|((ed|ph|m|o)\.?d\.?)|([sj]r\.?)|(esq\.?)", re.I)
PHONE_RE = re.compile(r"^(1-)?\d{3}-\d{3}-\d{4}( ext. \d+)?$")


def validate_phone(val: str) -> str:
    if not PHONE_RE.match(val):
        raise ValueError("invalid phone number")
    return val


class RoleType(str, Enum):
    UPPER = "upper"
    LOWER = "lower"
    JOINT = "legislature"
    GOVERNOR = "governor"
    LT_GOVERNOR = "lt_governor"
    MAYOR = "mayor"
    SOS = "secretary of state"
    CHIEF_ELECTION_OFFICER = "chief election officer"


class OfficeType(str, Enum):
    DISTRICT = "District Office"
    CAPITOL = "Capitol Office"
    PRIMARY = "Primary Office"


class PersonIdBlock(BaseModel):
    twitter: str = ""
    youtube: str = ""
    instagram: str = ""
    facebook: str = ""

    @validator("*")
    def validate_social(cls, val: str) -> str:
        validate_str_no_newline(val)
        if val.startswith(("http://", "https://", "@")):
            raise ValueError("invalid social media account name, drop URL or @")
        return val


class Party(TimeScoped):
    name: str

    _validate_strs = validator("name", allow_reuse=True)(validate_str_no_newline)


class Role(TimeScoped):
    type: RoleType
    district: str
    jurisdiction: str
    end_reason: str  # note: this field not imported to db

    _validate_strs = validator("district", "end_reason", allow_reuse=True)(validate_str_no_newline)
    _validate_jurisdiction = validator("jurisdiction", allow_reuse=True)(validate_ocd_jurisdiction)

    @root_validator
    def check_executives_have_end_date(cls, values):
        office_type = values.get("type")
        end_date = values.get("end_date")
        if (
            office_type
            in (
                OfficeType.GOVERNOR,
                OfficeType.LT_GOVERNOR,
                OfficeType.MAYOR,
                OfficeType.CHIEF_ELECTION_OFFICER,
                OfficeType.SOS,
            )
            and not end_date
        ):
            raise ValueError("end_date is required for executive roles")
        return values


class ContactDetail(BaseModel):
    note: OfficeType
    address: str = ""
    voice: str = ""
    fax: str = ""

    _validate_strs = validator("address", allow_reuse=True)(validate_str_no_newline)
    _validate_phones = validator("voice", "fax", allow_reuse=True)(validate_phone)


class Person(BaseModel):
    id: str
    name: str
    given_name: str = ""
    family_name: str = ""
    middle_name: str = ""
    suffix: str = ""
    gender: str = ""
    email: str = ""
    biography: str = ""
    birth_date: str = ""
    death_date: str = ""
    image: str = ""

    party: list[Party]
    roles: list[Role]

    contact_details: list[ContactDetail] = []
    links: list[Link] = []
    other_names: list[OtherName] = []
    ids: typing.Optional[PersonIdBlock] = None
    other_identifiers: list[OtherIdentifier] = []
    sources: list[Link] = []
    extras: dict = {}

    @validator("name")
    def no_bad_comma(val: str) -> str:
        pieces = val.split(",")
        if len(pieces) > 2:
            raise ValueError("too many commas, check if name is mangled")
        elif len(pieces) == 2 and not SUFFIX_RE.findall(pieces[1]):
            raise ValueError("invalid comma")
        return val

    _validate_person_id = validator("id", allow_reuse=True)(validate_ocd_person)
    _validate_dates = validator("birth_date", "death_date", allow_reuse=True)(validate_fuzzy_date)
    _validate_strings_no_newline = validator(
        # only biography is allowed newlines
        "name",
        "given_name",
        "family_name",
        "given_name",
        "middle_name",
        "email",
        "suffix",
        "gender",
        allow_reuse=True,
    )(validate_str_no_newline)
    _validate_image = validator("image", allow_reuse=True)(validate_url)
