# Dictionaries to represent the mappings
from enum import Enum, IntEnum


class JobCode(int, Enum):
    CONTRACT = 1
    OWNER_COMPANY = 2
    PERMANENT = 3
    RETIRED = 4


class MaritalStatus(int, Enum):
    SINGLE = 1
    DIVORCED = 2
    WIDOWED = 3
    MARRIED = 4


class Homes(int, Enum):
    WITH_PARENTS = 1
    RENTAL = 2
    OWNER = 3


class City(int, Enum):
    SMALL = 1
    MEDIUM = 2
    BIG = 3
    LARGE = 4


class Cars(int, Enum):
    NO = 1
    OWNER = 2


class Gender(int, Enum):
    MALE = 0
    FEMALE = 1


class Branch(int, Enum):
    OTHER = 0
    COMPUTERS = 1
    RADIO_TV = 2
    FURNITURE = 3
    DIY = 4


class CollStat(int, Enum):
    GOOD_PAYER = 1
    AMICABLE = 2
    PRE_LEGAL = 3
    LEGAL = 4
    EXECUTION = 5
    POST_EXECUTION = 6
    CURED = 7
    WRITE_OFF = 8


class Status(int, Enum):
    A = 1
    B = 2
    C = 3
