import configs
from p0f_wrapper import get_p0f_data
from utils import *
from configs import *
from time import sleep
from asn_checker import get_asn
import time
import calendar


def do_checks(request):
    """
    Main routine for sending to the different checks
    :param request:
    :return: True iff request matches blacklist patterns
    """
    client_ip = request['client_ip_address']

    formal_print('Getting asn data...')
    try:
        request['asn'] = get_asn(client_ip)
        formal_print('asn data received!')

    except:
        request['asn'] = 'No ASN data is available'
        formal_print('Failed getting asn data')

    # configurable, due to the fact that it does perform somewhat active fingerprinting
    if allow_reverse_dns:
        formal_print('Getting reverse DNS data...')
        request['ptr_record'] = get_ptr_record(client_ip)
        formal_print('Reverse DNS data received!')

    formal_print('Getting p0f data...')
    p0f_data = {}

    # polling and waiting to get p0f data
    while p0f_data == {} or p0f_data is None:
        p0f_data = get_p0f_data(client_ip)
        sleep(0.01)

    formal_print('p0f data received!')

    for key in p0f_data:
        if p0f_data[key]:
            val = p0f_data[key]
            if type(val) == bytes:
                val = val.decode("utf-8").rstrip('\x00')
            p0f_data[key] = str(val).lower()

    request['p0f_data'] = p0f_data

    if any([
        # add vendor specific tests here, e.g.
        
        # check_vendor_a(reqeust)
        # check_vendor_b(reqeust)

        # generic tests
        check_last_sec_service_observed_timeout(),
        check_obsolete_browser_version(request),
        check_os_mismatches(request)
    ]):
        # reset timer and return True
        reset_last_time_service_observed()
        return True
    else:
        return False


'''
Specific fingerprint detection

See commented out functions for examples
'''


# def check_vendor_a(request):
#     if 'vendor_a_name' in request['ptr_record'].lower() and check_os_mismatches(request):
#         return True
#     else:
#         return False


# def check_vendor_b(request):
#     if 'vendor_b_name' in request['user_agent'].lower() and \
#             check_os_mismatches(request):
#         return True
#     else:
#         return False

'''
Generic fingerprint detection
'''


def check_os_mismatches(request):
    """
    Compare the declared OS and TCP metadata OS
    Uses get_os_string to transform to a canonical form
    :param request: the HTTP GET headers
    :return: True iff UA and TCP disagree on the client's OS
    """
    p0f_os = get_os_string(request['p0f_data']['os_name'])
    ua_os = get_os_string(request['parsed_ua']['os']['family'])

    return p0f_os != ua_os


def check_obsolete_browser_version(request):
    """
    Detect implementations where developers neglected to update their code to reflect contemporary browser versions
    :param request:
    :return: True iff the version in the request is less than the one defined in the configuration
    """
    try:
        browser_type = request['parsed_ua']['user_agent']['family']
        request_version = int(request['parsed_ua']['user_agent']['major'])
        min_allowed_version = min_browser_versions_allowed[browser_type]

        return request_version < min_allowed_version
    except:
        # catch errors on UA parsing or illegal major versions
        return False


def check_last_sec_service_observed_timeout():
    """

    :return: True iff we've recently seen a service checking our server
    """
    current_time = calendar.timegm(time.gmtime())
    return current_time < last_time_service_observed + blacklist_service_observed_timeout
