from django.core.management.base import BaseCommand

from apps.shared.models import District, Region


class Command(BaseCommand):
    help = 'Loads Ghana regions and districts into database'

    def handle(self, *args, **options):
        data = [
            {
                "region": "Ahafo",
                "code": "AH",
                "districts": [
                    "Asunafo North Municipal",
                    "Asunafo South District",
                    "Asutifi North District",
                    "Asutifi South District",
                    "Tano North Municipal",
                    "Tano South Municipal"
                ]
            },
            {
                "region": "Ashanti",
                "code": "AS",
                "districts": [
                    "Adansi North District",
                    "Adansi South District",
                    "Afigya Kwabre District",
                    "Ahafo Ano North Municipal",
                    "Ahafo Ano South West District",
                    "Amansie Central District",
                    "Amansie West District",
                    "Asante Akim Central Municipal",
                    "Asante Akim North District",
                    "Asante Akim South Municipal",
                    "Asokore Mampong Municipal",
                    "Atwima Kwanwoma District",
                    "Atwima Mponua District",
                    "Atwima Nwabiagya Municipal",
                    "Bekwai Municipal",
                    "Bosome Freho District",
                    "Bosomtwe District",
                    "Ejisu Municipal",
                    "Ejura-Sekyedumase Municipal",
                    "Kumasi Metropolitan",
                    "Kwabre East Municipal",
                    "Mampong Municipal",
                    "Obuasi Municipal",
                    "Offinso Municipal",
                    "Offinso North District",
                    "Sekyere Afram Plains District",
                    "Sekyere Central District",
                    "Sekyere East District",
                    "Sekyere Kumawu District",
                    "Sekyere South District",
                    "Oforikrom Municipal",
                    "Kwadaso Municipal",
                    "Old Tafo Municipal",
                    "Asokwa Municipal",
                    "Suame Municipal",
                    "Juaben Municipal",
                    "Ahafo Ano South East District",
                    "Amansie South District",
                    "Atwima Nwabiagya North District",
                    "Akrofuom District",
                    "Adansi Asokwa District",
                    "Obuasi East District",
                    "Afigya Kwabre North District"
                ]
            },
            {
                "region": "Bono",
                "code": "BR",
                "districts": [
                    "Banda District",
                    "Berekum Municipal",
                    "Dormaa Central Municipal",
                    "Dormaa East District",
                    "Dormaa West District",
                    "Jaman North District",
                    "Jaman South Municipal",
                    "Sunyani Municipal",
                    "Sunyani West District",
                    "Tain District",
                    "Wenchi Municipal",
                    "Berekum West District"
                ]
            },
            {
                "region": "Bono East",
                "code": "BE",
                "districts": [
                    "Atebubu Amantin Municipal",
                    "Kintampo North Municipal",
                    "Kintampo South District",
                    "Nkoranza North District",
                    "Nkoranza South Municipal",
                    "Pru East District",
                    "Sene East District",
                    "Sene West District",
                    "Techiman Municipal",
                    "Techiman North District",
                    "Pru West District"
                ]
            },
            {
                "region": "Central",
                "code": "CR",
                "districts": [
                    "Abura Asebu Kwamankese District",
                    "Agona East District",
                    "Agona West Municipal",
                    "Ajumako Enyan Essiam District",
                    "Asikuma Odoben Brakwa District",
                    "Assin Central Municipal",
                    "Assin South District",
                    "Awutu Senya East Municipal",
                    "Awutu Senya West District",
                    "Cape Coast Metropolitan",
                    "Effutu Municipal",
                    "Ekumfi District",
                    "Gomoa Central District",
                    "Gomoa West District",
                    "Komenda Edina Eguafo Abirem Municipal",
                    "Mfantseman Municipal",
                    "Twifo Atti Morkwa District",
                    "Twifo Heman Lower Denkyira District",
                    "Upper Denkyira East Municipal",
                    "Upper Denkyira West District",
                    "Assin North District",
                    "Gomoa East District"
                ]
            },
            {
                "region": "Eastern",
                "code": "ER",
                "districts": [
                    "Akwapim North Municipal",
                    "Akwapim South District",
                    "Akyemansa District",
                    "Asuogyaman District",
                    "Atiwa West District",
                    "Ayensuano District",
                    "Birim Central Municipal",
                    "Birim North District",
                    "Birim South District",
                    "Denkyembour District",
                    "Achiase District",
                    "Fanteakwa North District",
                    "Kwaebibirem Municipal",
                    "Kwahu Afram Plains North District",
                    "Kwahu Afram Plains South District",
                    "Kwahu East District",
                    "Kwahu South District",
                    "Kwahu West Municipal",
                    "Lower Manya Krobo Municipal",
                    "New Juaben South Municipal",
                    "Nsawam Adoagyiri Municipal",
                    "Suhum Municipal",
                    "Upper Manya Krobo District",
                    "Upper West Akim District",
                    "West Akim Municipal",
                    "Yilo Krobo Municipal",
                    "Abuakwa South Municipal",
                    "New Juaben North Municipal",
                    "Abuakwa North Municipal",
                    "Asene Manso Akroso District",
                    "Okore District",
                    "Atiwa East District",
                    "Fanteakwa South District"
                ]
            },
            {
                "region": "Greater Accra",
                "code": "GA",
                "districts": [
                    "Accra Metropolitan",
                    "Ada East District",
                    "Ada West District",
                    "Adentan Municipal",
                    "Ashaiman Municipal",
                    "Ga Central Municipal",
                    "Ga East Municipal",
                    "Ga South Municipal ",
                    "Ga West Municipal ",
                    "Kpone Katamanso Municipal",
                    "La Dade Kotopon Municipal",
                    "La Nkwantanang Madina Municipal",
                    "Ledzekuku Municipal ",
                    "Ningo Prampram District",
                    "Shai Osudoku District",
                    "Tema Metropolitan",
                    "Korle Klottey Municipal",
                    "Ablekuma Central Municipal",
                    "Ayawaso Central Municipal",
                    "Okaikwei North Municipal",
                    "Ablekuma North Municipal ",
                    "Ablekuma West Municipal ",
                    "Ayawaso East Municipal",
                    "Ga North Municipal",
                    "Ayawaso West Municipal",
                    "Ayawaso North Municipal",
                    "Weija Gbawe Municipal",
                    "Tema West Municipal",
                    "Krowor Municipal"
                ]
            },
            {
                "region": "North East",
                "code": "NE",
                "districts": [
                    "Bunkpurugu Nyakpanduri District",
                    "Chereponi District",
                    "East Mamprusi Municipal",
                    "Mamprugu Moagduri District",
                    "West Mamprusi Municipal",
                    "Yunyoo-Nasuan District"
                ]
            },
            {
                "region": "Northern",
                "code": "NR",
                "districts": [
                    "Gushegu Municipal ",
                    "Karaga District",
                    "Kpandai District",
                    "Kumbungu District",
                    "Mion District",
                    "Nanumba North Municipal",
                    "Nanumba South District",
                    "Saboba District",
                    "Sagnarigu Municipal",
                    "Savelugu Municipal",
                    "Tamale Metropolitan",
                    "Tatale/Sanguli District",
                    "Tolon District",
                    "Yendi Municipal",
                    "Zabzugu District",
                    "Nanton District"
                ]
            },
            {
                "region": "Oti",
                "code": "OR",
                "districts": [
                    "Biakoye District",
                    "Jasikan District",
                    "Kadjebi District",
                    "Krachi East Municipal",
                    "Krachi Nchumuru District",
                    "Krachi West District",
                    "Nkwanta North District",
                    "Nkwanta South Municipal"
                ]
            },
            {
                "region": "Savanna",
                "code": "SR",
                "districts": [
                    "Bole District",
                    "Central Gonja District",
                    "East Gonja Municipal ",
                    "North Gonja District",
                    "Sawla-Tuna-Kalba District",
                    "West Gonja District",
                    "North East Gonja District"
                ]
            },
            {
                "region": "Upper East",
                "code": "UE",
                "districts": [
                    "Bawku Municipal",
                    "Bawku West District",
                    "Binduri District",
                    "Bolgatanga Municipal",
                    "Bongo District",
                    "Builsa North Municipal",
                    "Builsa South District",
                    "Garu District",
                    "Kassena Nankana Municipal",
                    "Kassena Nankana West District",
                    "Nabdam District",
                    "Pusiga District",
                    "Talensi District",
                    "Bolgatanga East District",
                    "Tempane District"
                ]
            },
            {
                "region": "Upper West",
                "code": "UW",
                "districts": [
                    "Daffiama Bussie Issa District",
                    "Jirapa Municipal",
                    "Lambussie Karni District",
                    "Lawra Municipal",
                    "Nadowli Kaleo District",
                    "Nandom District",
                    "Sissala East Municipal",
                    "Sissala West District",
                    "Wa East District",
                    "Wa Municipal",
                    "Wa West District"
                ]
            },
            {
                "region": "Volta",
                "code": "VR",
                "districts": [
                    "Adaklu District",
                    "Afadzato South District",
                    "Agotime Ziope District",
                    "Akatsi North District",
                    "Akatsi South District",
                    "Central Tongu District",
                    "Hohoe Municipal",
                    "Ho Municipal",
                    "Ho West District",
                    "Keta Municipal",
                    "Ketu North Municipal",
                    "Ketu South Municipal",
                    "Kpando Municipal",
                    "North Dayi District",
                    "North Tongu District",
                    "South Dayi District",
                    "South Tongu District",
                    "Anloga District"
                ]
            },
            {
                "region": "Western",
                "code": "WR",
                "districts": [
                    "Ahanta West Municipal",
                    "Ellembelle Municipal",
                    "Jomoro Municipal",
                    "Mpohor District",
                    "Nzema East Municipal",
                    "Prestea-Huni Valley Municipal",
                    "Sekondi Takoradi Metropolitan",
                    "Shama District",
                    "Tarkwa Nsuaem Municipal",
                    "Amenfi Central District",
                    "Wassa Amenfi East Municipal",
                    "Amenfi West Municipal",
                    "Wassa East District",
                    "Effia Kwesimintsim Municipal"
                ]
            },
            {
                "region": "Western North",
                "code": "WN",
                "districts": [
                    "Aowin Municipal",
                    "Bia East District",
                    "Bia West District",
                    "Bibiani-Ahwiaso Bekwai Municipal",
                    "Bodi District",
                    "Juaboso District",
                    "Sefwi Akontombra District",
                    "Sefwi Wiawso Municipal",
                    "Suaman District"
                ]
            }
        ]

        for region_data in data:
            region, created = Region.objects.get_or_create(
                name=region_data['region'],
                code=region_data['code']
            )

            for district_name in region_data['districts']:
                District.objects.get_or_create(
                    name=district_name.strip(),
                    region=region
                )

        self.stdout.write(self.style.SUCCESS('Successfully loaded regions and districts'))
