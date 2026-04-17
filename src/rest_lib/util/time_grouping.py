import datetime
from enum import Enum

class TimeGrouping(Enum):
    WEEK_OF_YEAR = "week"
    MONTH_OF_YEAR = "month"


def get_time_grouping(grouping: TimeGrouping):
    today = datetime.date.today()

    if grouping == TimeGrouping.WEEK_OF_YEAR.name:
        year, week, _ = today.isocalendar()
        return f"{week}_{year}"
    elif grouping == TimeGrouping.MONTH_OF_YEAR.name:
        month = today.strftime("%m")
        year = today.strftime("%Y")
        return f"{month}_{year}"
    return None
