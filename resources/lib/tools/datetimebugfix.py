
import datetime

def datetime_bug_workaround():

    try:
        throwaway = datetime.datetime.strptime("20110101", "%Y%m%d")
    except:
        pass