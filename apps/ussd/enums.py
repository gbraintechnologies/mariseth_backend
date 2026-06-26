from enum import Enum


class UssdSteps(str, Enum):
    USSD_INIT = "USSD_INIT"
    FARM_REG_U_INIT = "FARM_REG_U_INIT"
    FARM_REG_INIT = "FARM_REG_INIT"
    ID_NUMBER = "ID_NUMBER"
    FIRST_NAME = "FIRST_NAME"
    LAST_NAME = "LAST_NAME"
    DOB = "DOB"
    REGION = "REGION"
    DISTRICT = "DISTRICT"
    FARM_SIZE = "FARM_SIZE"
    CONFIRM_FARM_REG = "CONFIRM_FARM_REG"
    USSD_END = "USSD_END"

    @classmethod
    def ordered_steps(cls):
        return {
            cls.USSD_INIT:[
                cls.FARM_REG_U_INIT
            ],
            cls.FARM_REG_U_INIT:[
                cls.FARM_REG_INIT,
            ],
            cls.FARM_REG_INIT:cls.ID_NUMBER,
            cls.ID_NUMBER:cls.FIRST_NAME,
            cls.FIRST_NAME:cls.LAST_NAME,
            cls.LAST_NAME:cls.DOB,
            cls.DOB:cls.REGION,
            cls.REGION:cls.DISTRICT,
            cls.DISTRICT:cls.CONFIRM_FARM_REG,
        }

    def next_step(self):
        steps = self.ordered_steps()
        return steps.get(self) or self.USSD_INIT
class UssdFlowType(str, Enum):
    USSD_INIT = "USSD_INIT"
    FARM_REG_U = "FARM_REG_U"
    FARM_REG = "FARM_REG"
