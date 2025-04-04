# Dictionaries to represent the mappings
from enum import Enum


class JobCode(Enum):
    CONTRACT = 1
    OWNER_COMPANY = 2
    PERMANENT = 3
    RETIRED = 4


class MaritalStatus(Enum):
    SINGLE = 1
    DIVORCED = 2
    WIDOWED = 3
    MARRIED = 4


class Homes(Enum):
    WITH_PARENTS = 1
    RENTAL = 2
    OWNER = 3


class City(Enum):
    SMALL = 1
    MEDIUM = 2
    BIG = 3
    LARGE = 4


class Cars(Enum):
    NO = 1
    OWNER = 2


class Gender(Enum):
    MALE = 1
    FEMALE = 2


class Branch(Enum):
    COMPUTERS = 1
    RADIO_TV = 2
    FURNITURE = 3
    DIY = 4
    OTHER = "other"


class CollStat(Enum):
    GOOD_PAYER = 1
    AMICABLE = 2
    PRE_LEGAL = 3
    LEGAL = 4
    EXECUTION = 5
    POST_EXECUTION = 6
    CURED = 7
    WRITE_OFF = 8


class Status(Enum):
    A = 1
    B = 2
    C = 3
