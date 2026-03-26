import enum


class UpgradeCategory(str, enum.Enum):
    AERO = "Aero"
    MECHANICAL = "Mechanical"
    COOLING = "Cooling"
    FLOOR = "Floor"
    SUSPENSION = "Suspension"
    POWER_UNIT = "Power Unit"
    OTHER = "Other"


class EventStatus(str, enum.Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    ANNOTATING = "annotating"
    RECONSTRUCTING = "reconstructing"
    PUBLISHED = "published"


class AssetType(str, enum.Enum):
    GLB = "glb"
    PLY = "ply"
    SPLAT = "splat"
    IMAGE = "image"
    VIDEO = "video"
    HEATMAP = "heatmap"


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
