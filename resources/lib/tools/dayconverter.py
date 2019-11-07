from .datetimebugfix import datetime_bug_workaround
import datetime
import re
import time


def day_conv(date_string=None):
    """ If supplied with a date_string, it converts it to a time,
		otherwise it returns the current time as a float. """

    # there is a common bug with this call which results in an
    # ImportError: Failed to import _strptime because the import lockis held by another thread.
    # This throw away line should eliminate it. It doesnt need to be run every time, but it cant hurt.
    datetime_bug_workaround()

    if date_string is not None:

        # op_format = '%Y-%m-%d %H:%M:%S'

        # time.strptime is not threadsafe
        # this is a workaround, and probably not robust
        pattern = "(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)"

        m = re.match(pattern, date_string)

        extract = (int(x) for x in m.groups())

        lw_max = datetime.datetime(*extract)

        date_num = time.mktime(lw_max.timetuple())

    else:
        now = datetime.datetime.now()

        date_num = time.mktime(now.timetuple())

    return date_num