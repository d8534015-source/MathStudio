"""Studio wall-clock scheduling using IANA timezones, independent of OS zone."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TimezoneDataError(RuntimeError):
    pass


def studio_zone(name='America/Edmonton'):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as ex:
        raise TimezoneDataError('Time zone data is unavailable. Run py -m pip install -r requirements.txt.') from ex


def resolve_wall(value, name='America/Edmonton'):
    """Reject DST gaps; choose the earlier occurrence for a repeated local time."""
    zone=studio_zone(name)
    local=value.replace(tzinfo=zone,fold=0)
    if datetime.fromtimestamp(local.timestamp(),zone).replace(tzinfo=None)!=value:
        raise ValueError('This time does not exist in the studio timezone. Choose another time.')
    return local


def parse_local(date_text, time_text, name='America/Edmonton'):
    value=datetime.strptime(date_text+' '+time_text,'%Y-%m-%d %H:%M')
    return resolve_wall(value,name).timestamp()


def weekly_timestamp(timestamp, weeks, name='America/Edmonton'):
    if weeks==0:
        return timestamp
    value=datetime.fromtimestamp(timestamp,studio_zone(name)).replace(tzinfo=None)
    return resolve_wall(value+timedelta(weeks=weeks),name).timestamp()


@lru_cache(maxsize=8)
def timezone_rules(name, year):
    """Compact authoritative offsets for the booking/recurrence horizon.

    Browsers can have an older IANA database (notably Vancouver in 2026).
    Supported studio zones have at most one offset change per UTC day.
    """
    zone=studio_zone(name)
    start=int(datetime(year-1,1,1,tzinfo=timezone.utc).timestamp())
    end=int(datetime(year+3,1,1,tzinfo=timezone.utc).timestamp())
    def offset(stamp):
        return int(datetime.fromtimestamp(stamp,zone).utcoffset().total_seconds())
    previous=offset(start); transitions=[{'at':start,'offset':previous}]
    cursor=start
    while cursor<end:
        sample=min(cursor+86400,end)
        current=offset(sample)
        if current!=previous:
            low,high=cursor,sample
            while high-low>1:
                middle=(low+high)//2
                if offset(middle)==previous: low=middle
                else: high=middle
            transitions.append({'at':high,'offset':current})
            previous=current
        cursor=sample
    return {'zone':name,'start':start,'end':end,'transitions':transitions}
