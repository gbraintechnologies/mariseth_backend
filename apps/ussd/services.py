import datetime
from attr import dataclass
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import re

from django.db.models import Model

from apps.shared.models import Region, District
from apps.ussd.enums import UssdSteps, UssdFlowType
from apps.ussd.models import UssdSession


@dataclass
class ModalValue:
    id:str
    name:str
@dataclass
class UssdResult:
    message: str
    continue_session: bool
class UssdSessionService:
    page_size = 10
    def __init__(self):
         self.payload = {
             'id_type': "" ,
             'id_number': "",
             'phone_number': "",
             'dob':"",
             'first_name': "",
             'last_name': "",
             "region_id": "",
             'region': "",
             "district_id": "",
             'district': "",
         }


    def ussd_callback(self,session_id:str
                          , user_id:str
                          , new_session:bool
                          , phone_number:str
                          , user_data:str):
        user_data = (user_data or "").strip()
        session = UssdSession.objects.filter(session_id=session_id).first()
        if new_session or not session:
            UssdSession.objects.filter(phone_number=phone_number).delete()
            session = UssdSession.objects.create(
                phone_number=phone_number,
                session_id = session_id,
                payload={},
                current_step=UssdSteps.USSD_INIT.value,
                flow_type=UssdFlowType.USSD_INIT.value,
                history = [],
                page_number = 1
            )
            return UssdResult(self.get_step_message(session), True)
        flow_type = UssdFlowType(session.flow_type)
        if flow_type == UssdFlowType.USSD_INIT:
            menu_choices = {
                "1": "Farmer Registration / Update Profile",
                "2": "Submit a Request",
                "3": "Check Market Prices",
                "4": "My Account",
                "5": "Exit"
            }
            selected_choice = menu_choices.get(user_data)
            if not selected_choice:
                return self.get_step_error("Invalid Choice",session)
            if selected_choice == "Farmer Registration / Update Profile":
                return self.move_forward(session,UssdSteps.FARM_REG_U_INIT,UssdFlowType.FARM_REG_U,0)
            elif selected_choice == "Submit a Request":
                return self.exit(session)
            elif selected_choice == "Check Market Prices":
                return self.exit(session)
            elif selected_choice == "My Account":
                return self.exit(session)
            else:
                return self.exit(session)
        elif flow_type == UssdFlowType.FARM_REG_U:
            menu_choices = {
                "1": "Farmer Registration",
                "2": "Update Profile",
                "0": "Back"
            }
            selected_choice = menu_choices.get(user_data)
            if not selected_choice:
                return self.get_step_error("Invalid Choice",session)
            if selected_choice == "Farmer Registration":
                return self.move_forward(session,UssdSteps.FARM_REG_INIT,UssdFlowType.FARM_REG,0)
            elif selected_choice == "Back":
                return self.go_back(session)
            else:
                return self.exit(session)
        elif flow_type == UssdFlowType.FARM_REG:
            return self.handle_farm_reg_flow(session , user_data)
        else:
            return self.exit(session)


    def exit(self,session:UssdSession):
        session.delete()
        return UssdResult("Thank You", False)


    def get_step_error(self, message: str, session:UssdSession) -> UssdResult:
        return UssdResult(f"{message}\n{self.get_step_message(session)}",True)


    def handle_farm_reg_flow(self,session: UssdSession, user_data:str) -> UssdResult:
        if user_data == "0":
            return self.go_back(session)
        current_step = UssdSteps(session.current_step)
        payload = {
            "first_name": session.payload.get("first_name", ""),
            "last_name": session.payload.get("last_name", ""),
            "dob": session.payload.get("dob", ""),
            "id_type": session.payload.get("id_type", ""),
            "id_number": session.payload.get("id_number", ""),
            "region_id": session.payload.get("region_id", ""),
            "district_id": session.payload.get("district_id", ""),
            "region": session.payload.get("region", ""),
            "district": session.payload.get("district", ""),
        }
        if current_step == UssdSteps.FARM_REG_INIT:
            card_choices = {
                "1" : "Ghana Card",
                "2" : "NHIS",
                "3" : "Driver's License",
                "4" : "Voter's Card",
                "5" : "Passport ID",
                "6" : "No ID",
            }
            selected_choice = card_choices.get(user_data)
            if not selected_choice:
                return self.get_step_error("Invalid Choice",session)
            payload["id_type"] = selected_choice
            session.payload = payload
            if selected_choice == "No ID":
                payload.pop("id_number")
                return self.move_forward(session,UssdSteps.FIRST_NAME, UssdFlowType.FARM_REG)
            return self.move_forward(session,UssdSteps.ID_NUMBER, UssdFlowType.FARM_REG)
        elif current_step == UssdSteps.ID_NUMBER:
            if not re.fullmatch("[aA-zZ\\-\\d]{4,}", user_data):
                return self.get_step_error("Invalid ID Number",session)
            payload["id_number"] = user_data
            session.payload = payload
            return self.move_forward(session,UssdSteps.FIRST_NAME, UssdFlowType.FARM_REG)
        elif current_step == UssdSteps.FIRST_NAME:
            if not re.fullmatch("[aA-zZ]+", user_data):
                return self.get_step_error("Invalid First Name",session)
            payload["first_name"] = user_data
            session.payload = payload
            return self.move_forward(session, UssdSteps.LAST_NAME, UssdFlowType.FARM_REG)
        elif current_step == UssdSteps.LAST_NAME:
            if not re.fullmatch("[aA-zZ]+", user_data):
                return self.get_step_error("Invalid Last Name",session)
            payload["last_name"] = user_data
            session.payload = payload
            return self.move_forward(session,UssdSteps.DOB, UssdFlowType.FARM_REG)
        elif current_step == UssdSteps.DOB:
            try:
                date_of_birth = datetime.date.fromisoformat(user_data)
                payload["dob"] = date_of_birth.isoformat()
                session.payload = payload
                return self.move_forward(session,UssdSteps.REGION, UssdFlowType.FARM_REG)
            except ValueError:
                return self.get_step_error("Invalid Date Format",session)
        elif current_step == UssdSteps.REGION:
            page_number = session.page_number
            if user_data == "99":
                if not self.is_valid_for_next(Region, page_number, "name"):
                    return self.get_step_error("Invalid Choice",session)
                return self.next_page(session)
            else:
                if not user_data.isdigit():
                    return self.get_step_error("Invalid Choice", session)
                value = self.get_page_item_selected(Region, user_data,"name", page_number)
                if value is None or value.id == "":
                    return self.get_step_error("Invalid Choice",session)
                payload["region_id"] = value.id
                payload["region"] = value.name
                session.payload = payload
                return self.move_forward(session,UssdSteps.DISTRICT, UssdFlowType.FARM_REG)
        elif current_step == UssdSteps.DISTRICT:
            page_number = session.page_number
            if user_data == "99":
                if not self.is_valid_for_next(District, page_number,"name", region_id = payload["region_id"]):
                    return self.get_step_error("Invalid Choice",session)
                return self.next_page(session)
            else:
                if not user_data.isdigit():
                    return self.get_step_error("Invalid Choice", session)
                value = self.get_page_item_selected(District, user_data,"name", page_number, region_id = payload["region_id"])
                if value is None or value.id == "":
                    return self.get_step_error("Invalid Choice",session)
                payload["district_id"] = value.id
                payload["district"] = value.name
                session.payload = payload
                return self.move_forward(session,UssdSteps.CONFIRM_FARM_REG, UssdFlowType.FARM_REG)
        elif current_step == UssdSteps.CONFIRM_FARM_REG:
            confirm_choices = {
                "1" : "Confirm",
                "2" : "Exit",
            }
            selected_choice = confirm_choices.get(user_data)
            if not selected_choice:
                return self.get_step_error("Invalid Choice",session)
            if selected_choice == "Exit":
                return self.exit(session)
            session.current_step = UssdSteps.USSD_END
            history = session.history or []
            history.append({
                "current_step": UssdSteps.CONFIRM_FARM_REG,
                "flow_type": UssdFlowType.FARM_REG,
            })
            session.history = history
            session.save(update_fields=["current_step", "history"])
            return UssdResult("""Thank you
            Registration has been forward for approval""", False)
        else:
            return UssdResult(self.get_step_message(session),True)

    def get_page_item_selected(self,model:Region | District, user_data:str, sort:str, page_number:int = 1, **kwargs) -> ModalValue:
        try:
            inp = int(user_data)
            start = (page_number - 1) * self.page_size
            end = start + self.page_size
            if kwargs:
                query = model.objects.filter(**kwargs).order_by(sort)
            else:
                query = model.objects.order_by(sort)
            page_items = list(query[start:end])
            if len(page_items) <= inp:
                return ModalValue("", "")
            query_list = page_items[inp - 1]
            return ModalValue(str(query_list.id), query_list.name)
        except (PageNotAnInteger, EmptyPage):
            return ModalValue("", "")

    def is_valid_for_next(self, model, page_number:int,sort:str, *args, **kwargs) -> bool:
        if kwargs or args:
            value_set = model.objects.filter(**kwargs).order_by(sort)
        else:
            value_set = model.objects.order_by(sort)
        try:
            paginator = Paginator(value_set, self.page_size)
            page_obj = paginator.page(page_number)
            return page_obj.has_next()
        except (PageNotAnInteger, EmptyPage):
            return False


    def go_back(self, session: UssdSession) -> UssdResult:
        page_number = session.page_number
        if page_number > 1:
            page_number -= 1
            session.page_number = page_number
            session.save(update_fields=["page_number"])
            return UssdResult(self.get_step_message(session),True)
        history = session.history or []
        previous = history.pop(-1)
        if not previous:
            previous = {
                "flow_type": UssdFlowType.USSD_INIT.value,
                "current_step": UssdSteps.USSD_INIT.value
            }
        flow_type = previous["flow_type"]
        current_step = previous["current_step"]

        session.history = history
        session.flow_type = flow_type
        session.current_step = current_step

        session.save(update_fields=["flow_type", "current_step","history"])
        return UssdResult(self.get_step_message(session),True)


    def move_forward(self, session: UssdSession
                     , next_step: UssdSteps
                     , next_flow: UssdFlowType, idx: int = 0) -> UssdResult:
        current_step = UssdSteps(session.current_step)
        if not next_step:
            return UssdResult(self.get_step_message(session),True)
        if isinstance(next_step, list):
            next_step = next_step[idx]
        history = session.history or []
        history.append({
            "flow_type": session.flow_type,
            "current_step": current_step.value,
        })
        session.history = history
        session.current_step = next_step.value
        session.flow_type = next_flow.value
        session.page_number = 1
        session.save(update_fields=["flow_type", "current_step","history","payload","page_number"])
        return UssdResult(self.get_step_message(session),True)


    def next_page(self, session: UssdSession) -> UssdResult:
        page_number = session.page_number + 1
        session.page_number = page_number
        session.save(update_fields=["page_number"])
        return UssdResult(self.get_step_message(session),True)


    def get_step_message(self, session: UssdSession) -> str:
        current_step = UssdSteps(session.current_step)
        page_number = session.page_number
        payload = session.payload
        if current_step == UssdSteps.USSD_INIT:
            return """Welcome to Mariseth Farms
1. New Registration/ Update Profile
2. Submit a Request
3. Check Market Prices
4. My Account
5. Exit"""
        elif current_step == UssdSteps.FARM_REG_U_INIT:
            return """1. New Registration
2. Update Profile
0. Back"""
        elif current_step == UssdSteps.FARM_REG_INIT:
            return """Choose ID Type
1. Ghana Card
2. NHIS
3. Driver's License
4. Voter's Card
5. Passport ID
6. No ID
0. Back"""
        elif current_step == UssdSteps.ID_NUMBER:
            return """Enter ID Number (Do not include hyphen)
0. Back"""
        elif current_step == UssdSteps.FIRST_NAME:
            return """Please Enter First Name
0. Back"""
        elif current_step == UssdSteps.LAST_NAME:
            return """Please Enter Last Name
0. Back"""
        elif current_step == UssdSteps.DOB:
            return """Please Enter Date of Birth (YYYY-MM-DD)
0. Back"""
        elif current_step == UssdSteps.REGION:
            ussd_string = """Location
Please select your region"""
            query_set = Region.objects.order_by("name")
            paginator = Paginator(query_set, self.page_size)
            page_obj = paginator.get_page(page_number)
            regions = page_obj.object_list
            for index, region in enumerate(regions,start=1):
                ussd_string += f"\n{index}. {region.name}"
            if page_obj.has_next():
                ussd_string += "\n99. Next"
            ussd_string += "\n0. Back"
            return ussd_string
        elif current_step == UssdSteps.DISTRICT:
            ussd_string = """Location
Please select your district"""
            query_set = District.objects.filter(region_id=payload["region_id"]).order_by("name")
            paginator = Paginator(query_set, self.page_size)
            page_obj = paginator.get_page(page_number)
            districts = page_obj.object_list
            for index, district in enumerate(districts,start=1):
                ussd_string += f"\n{index}. {district.name}"
            if page_obj.has_next():
                ussd_string += "\n99. Next"
            ussd_string += "\n0. Back"
            return ussd_string
        elif current_step == UssdSteps.CONFIRM_FARM_REG:
            ussd_string = f"""Thank you
Summary Detail
Name: {payload["last_name"]} {payload["first_name"]}
Date of Birth: {payload["dob"]}
Location: {payload["district"]}, {payload["region"]}
1.Confirm
2. Exit
0. Back"""
            return ussd_string
        else:
            return ""