import enum


class UpgradeCategory(str, enum.Enum):
    AERO = "Aero"
    MECHANICAL = "Mechanical"
    COOLING = "Cooling"
    FLOOR = "Floor"
    SUSPENSION = "Suspension"
    POWER_UNIT = "Power Unit"
    OTHER = "Other"


class ComponentZone(str, enum.Enum):
    FRONT_WING = "Front Wing"
    REAR_WING = "Rear Wing"
    FLOOR = "Floor"
    FLOOR_EDGE = "Floor Edge"
    SIDEPOD = "Sidepod"
    DIFFUSER = "Diffuser"
    BARGEBOARD = "Bargeboard"
    ENGINE_COVER = "Engine Cover"
    BRAKE_DUCT = "Brake Duct"
    SUSPENSION_ARM = "Suspension Arm"
    HALO = "Halo"
    NOSE = "Nose"
    OTHER = "Other"
