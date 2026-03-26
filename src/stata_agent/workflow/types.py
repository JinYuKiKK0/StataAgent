from enum import Enum


class RunStage(str, Enum):
    REQUESTED = "requested"
    SPECIFIED = "specified"
    MAPPED = "mapped"
    PROBED = "probed"
    FETCHED = "fetched"
    STANDARDIZED = "standardized"
    VALIDATED = "validated"
    MODELED = "modeled"
    EXECUTED = "executed"
    JUDGED = "judged"
    COMPLETED = "completed"
    FAILED = "failed"
